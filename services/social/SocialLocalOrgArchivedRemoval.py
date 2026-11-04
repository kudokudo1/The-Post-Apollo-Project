#!/usr/bin/env python3
"""Archived-only owner-local record removal with seven-store reference guards.

No cascading deletion, credential actions, restoration, or remote company access.
The last source revision is checked while all original writer locks are held.
"""
from __future__ import annotations

from contextlib import ExitStack
import json
import sys
from typing import Any

import SocialLocalOrgBackup as backups

KIND_TO_SOURCE = {
    "organization": ("directory", "organizations"),
    "branch": ("directory", "organizations"),
    "portfolio": ("portfolios", "portfolios"),
    "unit": ("structure", "units"),
}
MAX_REQUEST = 2048


class RemovalError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _record(documents: dict[str, Any], kind: str, ident: str, org_id: str):
    if kind == "branch":
        owner = next((o for o in documents["directory"]["organizations"]
                      if o["id"] == org_id), None)
        if owner is None:
            raise RemovalError("ORGANIZATION_NOT_FOUND")
        record = next((b for b in owner["branches"] if b["id"] == ident), None)
        return record, owner["branches"]
    key, container = KIND_TO_SOURCE[kind]
    records = documents[key][container]
    return next((x for x in records if x["id"] == ident), None), records


def _has_backup(kind: str, ident: str, org_id: str, record: dict[str, Any]) -> bool:
    # A snapshot must actually include the exact archived record. Backing up
    # an empty directory yesterday does not protect a record created today.
    for filename in backups.names():
        bundle = backups.read_backup(filename)
        other, _ = _record(bundle["documents"], kind, ident, org_id)
        if other == record:
            return True
    return False


def _check_references(documents: dict[str, Any], kind: str, ident: str, org_id: str,
                      record: dict[str, Any]) -> None:
    if kind == "organization":
        if record["branches"]:
            raise RemovalError("REMOVE_BRANCHES_FIRST")
        if any(u["orgId"] == ident for u in documents["structure"]["units"]):
            raise RemovalError("REMOVE_UNITS_FIRST")
        if any(ident in p["orgIds"] for p in documents["portfolios"]["portfolios"]):
            raise RemovalError("DETACH_PORTFOLIOS_FIRST")
        if any(link["orgId"] == ident for section in
               ("unitLocations", "branchLocations", "reporting", "socialLinks")
               for link in documents[section]["links"]):
            raise RemovalError("UNLINK_ORGANIZATION_FIRST")
    elif kind == "branch":
        if any(x["orgId"] == org_id and x["branchId"] == ident
               for x in documents["branchLocations"]["links"]):
            raise RemovalError("UNLINK_BRANCH_LOCATION_FIRST")
        if any(x["orgId"] == org_id and x["branchId"] == ident
               for x in documents["socialLinks"]["links"]):
            raise RemovalError("UNLINK_BRANCH_SOCIAL_FIRST")
    elif kind == "unit":
        if any(x["functionId"] == ident or x["locationId"] == ident
               for x in documents["unitLocations"]["links"]):
            raise RemovalError("UNLINK_UNIT_LOCATION_FIRST")
        if any(x["locationId"] == ident
               for x in documents["branchLocations"]["links"]):
            raise RemovalError("UNLINK_BRANCH_LOCATION_FIRST")
        if any(x["parentId"] == ident or x["childId"] == ident
               for x in documents["reporting"]["links"]):
            raise RemovalError("UNLINK_REPORTING_FIRST")
    elif kind == "portfolio":
        if record["orgIds"]:
            raise RemovalError("DETACH_PORTFOLIO_MEMBERS_FIRST")


def remove(request: Any) -> dict[str, Any]:
    if (type(request) is not dict
            or set(request) != {"action", "kind", "id", "orgId",
                                "expectedName", "expectedRevision"}
            or request["action"] != "remove"):
        raise RemovalError("INVALID_REQUEST")
    kind = request["kind"]
    if type(kind) is not str or kind not in KIND_TO_SOURCE:
        raise RemovalError("INVALID_REQUEST")
    if (type(request["id"]) is not str or type(request["orgId"]) is not str
            or type(request["expectedName"]) is not str
            or type(request["expectedRevision"]) is not int
            or request["expectedRevision"] < 0):
        raise RemovalError("INVALID_REQUEST")
    ident = request["id"]
    org_id = request["orgId"]
    if (kind == "organization" and (not ident.startswith("org-") or org_id != ident)
            or kind == "branch" and
                (not ident.startswith("branch-") or not org_id.startswith("org-"))
            or kind == "portfolio" and
                (not ident.startswith("portfolio-") or org_id != "")
            or kind == "unit" and
                (not ident.startswith("unit-") or not org_id.startswith("org-"))):
        raise RemovalError("INVALID_REQUEST")

    with ExitStack() as stack:
        backups.lock_sources(stack)  # Nonblocking all-seven lock preflight.
        documents = {
            key: module.validate(module.load())
            for key, module, _, _ in backups.SOURCES
        }
        source, _ = KIND_TO_SOURCE[kind]
        doc = documents[source]
        if doc["revision"] != request["expectedRevision"]:
            raise RemovalError("REVISION_CONFLICT")
        record, records = _record(documents, kind, ident, org_id)
        if record is None:
            raise RemovalError("RECORD_NOT_FOUND")
        if not record["archived"]:
            raise RemovalError("ARCHIVE_BEFORE_REMOVE")
        if record["name"] != request["expectedName"]:
            raise RemovalError("RECORD_CHANGED")
        if kind == "unit" and record["orgId"] != org_id:
            raise RemovalError("WRONG_ORGANIZATION")
        _check_references(documents, kind, ident, org_id, record)
        if not _has_backup(kind, ident, org_id, record):
            raise RemovalError("BACKUP_REQUIRED")
        records.remove(record)
        doc["revision"] += 1  # Never reuse IDs. nextId remains monotonic.
        module = next(module for key, module, _, _ in backups.SOURCES
                      if key == source)
        module.save(module.validate(doc))
        return {"ok": True, "kind": kind, "id": ident,
                "source": source, "revision": doc["revision"]}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args != ["remove"]:
            raise RemovalError("INVALID_REQUEST")
        raw = sys.stdin.buffer.readline(MAX_REQUEST + 1)
        if not raw or len(raw) > MAX_REQUEST or not raw.endswith(b"\n"):
            raise RemovalError("INVALID_REQUEST")
        data = backups.parse(raw)
        result = remove(data)
        code = 0
    except Exception as exc:
        # Never echo names, internal paths, documents or request payloads.
        result = {"ok": False, "error": getattr(exc, "code", "REMOVE_UNAVAILABLE")}
        code = 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
