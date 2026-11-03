#!/usr/bin/env python3
"""Manual branch-to-location associations. Local directory metadata, never grants.

Branches remain in the accepted organization directory; locations remain in
the independent structure catalog. This file stores only opaque local IDs.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

from SocialAccountDetails import (
    StoreError as StorageError, _assert_secure_dir, _assert_secure_file, root_path,
)
import SocialLocalOrganizationStructure as structure
import SocialOrganizationDirectory as directory

SCHEMA = "post-apollo.social-local-branch-location-links.v1"
FILE_NAME = "local-branch-location-links-v1.json"
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 2048
MAX_LINKS = 400
ORG_ID = re.compile(r"^org-[1-9][0-9]{0,8}$")
BRANCH_ID = re.compile(r"^branch-[1-9][0-9]{0,8}$")
UNIT_ID = re.compile(r"^unit-[1-9][0-9]{0,8}$")
LINK_ID = re.compile(r"^branch-placement-[1-9][0-9]{0,8}$")
FIELDS = {
    "add": {"orgId", "branchId", "locationId"},
    "remove": {"linkId"},
}


class BranchLocationError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def storage_path() -> Path:
    return root_path() / FILE_NAME


def initial() -> dict[str, Any]:
    return {"schema": SCHEMA, "revision": 0, "nextId": 1, "links": []}


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BranchLocationError("INVALID_JSON")
        result[key] = value
    return result


def _bad_constant(_value: str) -> None:
    raise BranchLocationError("INVALID_JSON")


def decode(data: bytes) -> Any:
    try:
        return json.loads(data, object_pairs_hook=_pairs,
                          parse_constant=_bad_constant)
    except (UnicodeError, ValueError):
        raise BranchLocationError("INVALID_JSON") from None


def _id(value: Any, regex: re.Pattern[str]) -> str:
    if type(value) is not str or not regex.fullmatch(value):
        raise BranchLocationError("INVALID_ID")
    return value


def validate(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or raw.get("schema") != SCHEMA:
        raise BranchLocationError("UNSUPPORTED_VERSION")
    if set(raw) != {"schema", "revision", "nextId", "links"}:
        raise BranchLocationError("INVALID_DOCUMENT")
    revision, next_id, links = raw["revision"], raw["nextId"], raw["links"]
    if (type(revision) is not int or not 0 <= revision < 1_000_000_000
            or type(next_id) is not int or not 1 <= next_id < 1_000_000_000
            or type(links) is not list or len(links) > MAX_LINKS):
        raise BranchLocationError("INVALID_DOCUMENT")
    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str, str]] = set()
    max_id = 0
    clean: list[dict[str, str]] = []
    for item in links:
        if (type(item) is not dict or
                set(item) != {"id", "orgId", "branchId", "locationId"}):
            raise BranchLocationError("INVALID_DOCUMENT")
        ident = _id(item["id"], LINK_ID)
        org_id = _id(item["orgId"], ORG_ID)
        branch_id = _id(item["branchId"], BRANCH_ID)
        location_id = _id(item["locationId"], UNIT_ID)
        pair = (org_id, branch_id, location_id)
        if ident in seen_ids or pair in seen_pairs:
            raise BranchLocationError("DUPLICATE_LINK")
        max_id = max(max_id, int(ident[len("branch-placement-"):]))
        seen_ids.add(ident)
        seen_pairs.add(pair)
        clean.append({"id": ident, "orgId": org_id,
                      "branchId": branch_id, "locationId": location_id})
    if max_id >= next_id:
        raise BranchLocationError("INVALID_DOCUMENT")
    return {"schema": SCHEMA, "revision": revision,
            "nextId": next_id, "links": clean}


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return initial()
    path = storage_path()
    if not _assert_secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        st = os.fstat(stream.fileno())
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077):
            raise BranchLocationError("UNSAFE_FILE")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise BranchLocationError("FILE_TOO_LARGE")
    return validate(decode(raw))


def _check_active_local_target(org_id: str, branch_id: str,
                               location_id: str) -> None:
    # Local reference consistency ONLY. Identity Center never reads this as a grant.
    d = directory.load()
    parent = next((org for org in d["organizations"]
                   if org["id"] == org_id and not org["archived"]), None)
    if parent is None:
        raise BranchLocationError("ORGANIZATION_UNAVAILABLE")
    if not any(b["id"] == branch_id and not b["archived"]
               for b in parent["branches"]):
        raise BranchLocationError("BRANCH_UNAVAILABLE")
    s = structure.load()
    if not any(unit["id"] == location_id
               and unit["kind"] == "location"
               and unit["orgId"] == org_id and not unit["archived"]
               for unit in s["units"]):
        raise BranchLocationError("LOCATION_UNAVAILABLE")


def apply(current: Any, request: Any) -> dict[str, Any]:
    doc = validate(current)
    if type(request) is not dict or type(request.get("action")) is not str:
        raise BranchLocationError("INVALID_REQUEST")
    action = request["action"]
    if action not in FIELDS or set(request) != FIELDS[action] | {
            "action", "expectedRevision"}:
        raise BranchLocationError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != doc["revision"]):
        raise BranchLocationError("REVISION_CONFLICT")

    if action == "add":
        if len(doc["links"]) >= MAX_LINKS:
            raise BranchLocationError("LINK_CAPACITY")
        org_id = _id(request["orgId"], ORG_ID)
        branch_id = _id(request["branchId"], BRANCH_ID)
        location_id = _id(request["locationId"], UNIT_ID)
        _check_active_local_target(org_id, branch_id, location_id)
        if any(entry["orgId"] == org_id and
               entry["branchId"] == branch_id and
               entry["locationId"] == location_id
               for entry in doc["links"]):
            raise BranchLocationError("DUPLICATE_LINK")
        doc["links"].append({
            "id": f'branch-placement-{doc["nextId"]}',
            "orgId": org_id, "branchId": branch_id, "locationId": location_id,
        })
        doc["nextId"] += 1
    else:
        ident = _id(request["linkId"], LINK_ID)
        index = next((i for i, item in enumerate(doc["links"])
                      if item["id"] == ident), -1)
        if index < 0:
            raise BranchLocationError("LINK_NOT_FOUND")
        # Historical associations remain removable after an archive.
        doc["links"].pop(index)
    doc["revision"] += 1
    return validate(doc)


def save(document: Any) -> None:
    clean = validate(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    path = storage_path()
    _assert_secure_file(path)
    raw = (json.dumps(clean, ensure_ascii=True, separators=(",", ":"))
           + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise BranchLocationError("FILE_TOO_LARGE")
    fd, temp = tempfile.mkstemp(prefix=".branch-location-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as writer:
            fd = -1
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temp, path)
        directory_fd = os.open(root, os.O_RDONLY
                               | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temp):
            os.unlink(temp)


def run(action: str) -> dict[str, Any]:
    if action == "read":
        return {"ok": True, "document": load()}
    if action != "update":
        raise BranchLocationError("INVALID_REQUEST")
    data = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not data or len(data) > MAX_REQUEST_BYTES or not data.endswith(b"\n"):
        raise BranchLocationError("INVALID_REQUEST")
    request = decode(data)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock = root / ".branch-location.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077):
            raise BranchLocationError("UNSAFE_LOCK")
        fcntl.flock(fd, fcntl.LOCK_EX)
        updated = apply(load(), request)
        save(updated)
    finally:
        os.close(fd)
    return {"ok": True, "document": updated}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args not in (["read"], ["update"]):
            raise BranchLocationError("INVALID_REQUEST")
        result = run(args[0])
        code = 0
    except (BranchLocationError, StorageError, directory.DirectoryError,
            structure.StructureError, OSError) as e:
        code = 2
        result = {"ok": False, "error": e.code if isinstance(
            e, (BranchLocationError, StorageError, directory.DirectoryError,
                structure.StructureError)) else "STORAGE_UNAVAILABLE"}
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
