#!/usr/bin/env python3
"""Local organization structure labels, not verified Identity Center scopes.

Divisions, departments and teams are functional labels; locations are a
separate geographic label type. No employee assignments, tenancy or grants.
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
import SocialOrganizationDirectory as local_directory

SCHEMA = "post-apollo.social-local-org-structure.v1"
FILE_NAME = "local-org-structure-v1.json"
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 2048
MAX_UNITS = 400
MAX_UNITS_PER_ORG_KIND = 60
NAME_LIMIT = 80
TYPES = ("division", "department", "location", "team")
ORG_ID = re.compile(r"^org-[1-9][0-9]{0,8}$")
UNIT_ID = re.compile(r"^unit-[1-9][0-9]{0,8}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
FIELDS = {
    "create": {"orgId", "kind", "name"},
    "rename": {"unitId", "name"},
    "archive": {"unitId"},
    "restore": {"unitId"},
}


class StructureError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def storage_path() -> Path:
    return root_path() / FILE_NAME


def initial() -> dict[str, Any]:
    return {"schema": SCHEMA, "revision": 0, "nextId": 1, "units": []}


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        if key in out:
            raise StructureError("INVALID_JSON")
        out[key] = value
    return out


def _constant(_value: str) -> None:
    raise StructureError("INVALID_JSON")


def decode(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, ValueError):
        raise StructureError("INVALID_JSON") from None


def _id(value: Any, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise StructureError("INVALID_ID")
    return value


def _name(value: Any) -> str:
    if (type(value) is not str or len(value) > NAME_LIMIT
            or CONTROL.search(value)):
        raise StructureError("INVALID_NAME")
    clean = value.strip()
    if not clean:
        raise StructureError("INVALID_NAME")
    return clean


def _kind(value: Any) -> str:
    if type(value) is not str or value not in TYPES:
        raise StructureError("INVALID_KIND")
    return value


def validate(document: Any) -> dict[str, Any]:
    if type(document) is not dict or document.get("schema") != SCHEMA:
        raise StructureError("UNSUPPORTED_VERSION")
    if set(document) != {"schema", "revision", "nextId", "units"}:
        raise StructureError("INVALID_DOCUMENT")
    rev, next_id, records = (
        document["revision"], document["nextId"], document["units"]
    )
    if (type(rev) is not int or not 0 <= rev < 1_000_000_000
            or type(next_id) is not int or not 1 <= next_id < 1_000_000_000
            or type(records) is not list or len(records) > MAX_UNITS):
        raise StructureError("INVALID_DOCUMENT")
    seen_ids: set[str] = set()
    seen_names: set[tuple[str, str, str]] = set()
    counts: dict[tuple[str, str], int] = {}
    max_id = 0
    clean: list[dict[str, Any]] = []
    for record in records:
        if (type(record) is not dict or
                set(record) != {"id", "orgId", "kind", "name", "archived"}):
            raise StructureError("INVALID_DOCUMENT")
        unit_id = _id(record["id"], UNIT_ID)
        org_id = _id(record["orgId"], ORG_ID)
        kind = _kind(record["kind"])
        name = _name(record["name"])
        archived = record["archived"]
        if unit_id in seen_ids or type(archived) is not bool:
            raise StructureError("INVALID_DOCUMENT")
        seen_ids.add(unit_id)
        max_id = max(max_id, int(unit_id[len("unit-"):]))
        key = (org_id, kind)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > MAX_UNITS_PER_ORG_KIND:
            raise StructureError("UNIT_CAPACITY")
        if not archived:
            scoped_name = (org_id, kind, name.casefold())
            if scoped_name in seen_names:
                raise StructureError("DUPLICATE_NAME")
            seen_names.add(scoped_name)
        clean.append({
            "id": unit_id, "orgId": org_id, "kind": kind,
            "name": name, "archived": archived,
        })
    if max_id >= next_id:
        raise StructureError("INVALID_DOCUMENT")
    return {"schema": SCHEMA, "revision": rev,
            "nextId": next_id, "units": clean}


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return initial()
    path = storage_path()
    if not _assert_secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as reader:
        info = os.fstat(reader.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise StructureError("UNSAFE_FILE")
        raw = reader.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise StructureError("FILE_TOO_LARGE")
    return validate(decode(raw))


def _active_org(ident: Any) -> str:
    org_id = _id(ident, ORG_ID)
    doc = local_directory.load()
    if not any(item["id"] == org_id and not item["archived"]
               for item in doc["organizations"]):
        raise StructureError("ORGANIZATION_UNAVAILABLE")
    return org_id


def _unit(document: dict[str, Any], ident: Any) -> dict[str, Any]:
    unit_id = _id(ident, UNIT_ID)
    for record in document["units"]:
        if record["id"] == unit_id:
            return record
    raise StructureError("UNIT_NOT_FOUND")


def _no_duplicate(records: list[dict[str, Any]], unit: dict[str, Any] | None,
                  org_id: str, kind: str, name: str) -> None:
    if any((record is not unit and not record["archived"]
            and record["orgId"] == org_id and record["kind"] == kind
            and record["name"].casefold() == name.casefold())
           for record in records):
        raise StructureError("DUPLICATE_NAME")


def apply(document: Any, request: Any) -> dict[str, Any]:
    doc = validate(document)
    if type(request) is not dict or type(request.get("action")) is not str:
        raise StructureError("INVALID_REQUEST")
    action = request["action"]
    if action not in FIELDS or set(request) != (FIELDS[action] |
                                               {"action", "expectedRevision"}):
        raise StructureError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != doc["revision"]):
        raise StructureError("REVISION_CONFLICT")
    units = doc["units"]
    if action == "create":
        if len(units) >= MAX_UNITS:
            raise StructureError("UNIT_CAPACITY")
        org_id = _active_org(request["orgId"])
        kind = _kind(request["kind"])
        name = _name(request["name"])
        if sum(1 for u in units if u["orgId"] == org_id
               and u["kind"] == kind) >= MAX_UNITS_PER_ORG_KIND:
            raise StructureError("UNIT_CAPACITY")
        _no_duplicate(units, None, org_id, kind, name)
        units.append({
            "id": f'unit-{doc["nextId"]}', "orgId": org_id,
            "kind": kind, "name": name, "archived": False,
        })
        doc["nextId"] += 1
    else:
        unit = _unit(doc, request["unitId"])
        if action == "archive":
            if unit["archived"]:
                raise StructureError("NO_CHANGE")
            unit["archived"] = True
        elif action == "restore":
            if not unit["archived"]:
                raise StructureError("NO_CHANGE")
            _active_org(unit["orgId"])
            _no_duplicate(units, unit, unit["orgId"], unit["kind"], unit["name"])
            unit["archived"] = False
        else:
            if unit["archived"]:
                raise StructureError("UNIT_ARCHIVED")
            _active_org(unit["orgId"])
            name = _name(request["name"])
            if name == unit["name"]:
                raise StructureError("NO_CHANGE")
            _no_duplicate(units, unit, unit["orgId"], unit["kind"], name)
            unit["name"] = name
    doc["revision"] += 1
    return validate(doc)


def save(document: Any) -> None:
    clean = validate(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    path = storage_path()
    _assert_secure_file(path)
    raw = (json.dumps(clean, ensure_ascii=True,
                      separators=(",", ":")) + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise StructureError("FILE_TOO_LARGE")
    fd, temp = tempfile.mkstemp(prefix=".local-org-structure-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as writer:
            fd = -1
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temp, path)
        dfd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temp):
            os.unlink(temp)


def run(action: str) -> dict[str, Any]:
    if action == "read":
        return {"ok": True, "document": load()}
    if action != "update":
        raise StructureError("INVALID_REQUEST")
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not raw or len(raw) > MAX_REQUEST_BYTES or not raw.endswith(b"\n"):
        raise StructureError("INVALID_REQUEST")
    request = decode(raw)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock_path = root / ".local-org-structure.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise StructureError("UNSAFE_LOCK")
        fcntl.flock(fd, fcntl.LOCK_EX)
        changed = apply(load(), request)
        save(changed)
    finally:
        os.close(fd)
    return {"ok": True, "document": changed}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args not in (["read"], ["update"]):
            raise StructureError("INVALID_REQUEST")
        result = run(args[0])
        status = 0
    except (StructureError, StorageError, local_directory.DirectoryError,
            OSError) as error:
        status = 2
        result = {"ok": False, "error": error.code if isinstance(
            error, (StructureError, StorageError, local_directory.DirectoryError)
        ) else "STORAGE_UNAVAILABLE"}
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
