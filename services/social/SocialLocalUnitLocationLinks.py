#!/usr/bin/env python3
"""Manual functional-unit ↔ location labels within one local organization.

No employee membership, legal tenancy, reporting hierarchy or access rights.
Only opaque local org/unit IDs; the accepted original stores are read-only.
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

SCHEMA = "post-apollo.social-local-unit-location-links.v1"
FILE_NAME = "local-unit-location-links-v1.json"
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 2048
MAX_LINKS = 400
ORG_ID = re.compile(r"^org-[1-9][0-9]{0,8}$")
UNIT_ID = re.compile(r"^unit-[1-9][0-9]{0,8}$")
LINK_ID = re.compile(r"^placement-[1-9][0-9]{0,8}$")
FUNCTION_KINDS = frozenset({"division", "department", "team"})
FIELDS = {
    "add": {"orgId", "functionId", "locationId"},
    "remove": {"linkId"},
}


class PlacementError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def storage_path() -> Path:
    return root_path() / FILE_NAME


def initial() -> dict[str, Any]:
    return {"schema": SCHEMA, "revision": 0, "nextId": 1, "links": []}


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise PlacementError("INVALID_JSON")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise PlacementError("INVALID_JSON")


def decode(payload: bytes) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_pairs,
                          parse_constant=_reject_constant)
    except (UnicodeError, ValueError):
        raise PlacementError("INVALID_JSON") from None


def _id(value: Any, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise PlacementError("INVALID_ID")
    return value


def validate(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or raw.get("schema") != SCHEMA:
        raise PlacementError("UNSUPPORTED_VERSION")
    if set(raw) != {"schema", "revision", "nextId", "links"}:
        raise PlacementError("INVALID_DOCUMENT")
    revision, counter, links = raw["revision"], raw["nextId"], raw["links"]
    if (type(revision) is not int or not 0 <= revision < 1_000_000_000
            or type(counter) is not int or not 1 <= counter < 1_000_000_000
            or type(links) is not list or len(links) > MAX_LINKS):
        raise PlacementError("INVALID_DOCUMENT")

    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str, str]] = set()
    maximum = 0
    clean: list[dict[str, str]] = []
    for entry in links:
        if (type(entry) is not dict or
                set(entry) != {"id", "orgId", "functionId", "locationId"}):
            raise PlacementError("INVALID_DOCUMENT")
        link_id = _id(entry["id"], LINK_ID)
        org_id = _id(entry["orgId"], ORG_ID)
        function_id = _id(entry["functionId"], UNIT_ID)
        location_id = _id(entry["locationId"], UNIT_ID)
        pair = (org_id, function_id, location_id)
        if (link_id in seen_ids or pair in seen_pairs
                or function_id == location_id):
            raise PlacementError("DUPLICATE_OR_INVALID_LINK")
        seen_ids.add(link_id)
        seen_pairs.add(pair)
        maximum = max(maximum, int(link_id[len("placement-"):]))
        clean.append({
            "id": link_id, "orgId": org_id,
            "functionId": function_id, "locationId": location_id,
        })
    if maximum >= counter:
        raise PlacementError("INVALID_DOCUMENT")
    return {"schema": SCHEMA, "revision": revision,
            "nextId": counter, "links": clean}


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
            raise PlacementError("UNSAFE_FILE")
        data = reader.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise PlacementError("FILE_TOO_LARGE")
    return validate(decode(data))


def _check_local_targets(org_id: str, function_id: str, location_id: str) -> None:
    # Checking local existence is a data-quality guard, NOT authorization.
    organizations = directory.load()
    if not any(org["id"] == org_id and not org["archived"]
               for org in organizations["organizations"]):
        raise PlacementError("ORGANIZATION_UNAVAILABLE")
    current = structure.load()
    by_id = {unit["id"]: unit for unit in current["units"]}
    function, location = by_id.get(function_id), by_id.get(location_id)
    if (not function or function["archived"]
            or function["orgId"] != org_id
            or function["kind"] not in FUNCTION_KINDS):
        raise PlacementError("FUNCTION_UNAVAILABLE")
    if (not location or location["archived"]
            or location["orgId"] != org_id or location["kind"] != "location"):
        raise PlacementError("LOCATION_UNAVAILABLE")


def apply(current: Any, request: Any) -> dict[str, Any]:
    document = validate(current)
    if type(request) is not dict or type(request.get("action")) is not str:
        raise PlacementError("INVALID_REQUEST")
    action = request["action"]
    if (action not in FIELDS or
            set(request) != FIELDS[action] | {"action", "expectedRevision"}):
        raise PlacementError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != document["revision"]):
        raise PlacementError("REVISION_CONFLICT")

    if action == "add":
        if len(document["links"]) >= MAX_LINKS:
            raise PlacementError("LINK_CAPACITY")
        org_id = _id(request["orgId"], ORG_ID)
        function_id = _id(request["functionId"], UNIT_ID)
        location_id = _id(request["locationId"], UNIT_ID)
        if function_id == location_id:
            raise PlacementError("INVALID_REQUEST")
        _check_local_targets(org_id, function_id, location_id)
        if any(item["orgId"] == org_id and
               item["functionId"] == function_id and
               item["locationId"] == location_id
               for item in document["links"]):
            raise PlacementError("DUPLICATE_LINK")
        document["links"].append({
            "id": f'placement-{document["nextId"]}',
            "orgId": org_id, "functionId": function_id,
            "locationId": location_id,
        })
        document["nextId"] += 1
    else:
        link_id = _id(request["linkId"], LINK_ID)
        index = next((i for i, item in enumerate(document["links"])
                      if item["id"] == link_id), -1)
        if index < 0:
            raise PlacementError("LINK_NOT_FOUND")
        # Keep stale links removable even after an org/unit is archived.
        document["links"].pop(index)

    document["revision"] += 1
    return validate(document)


def save(document: Any) -> None:
    clean = validate(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    path = storage_path()
    _assert_secure_file(path)
    raw = (json.dumps(clean, ensure_ascii=True, separators=(",", ":"))
           + "\n").encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise PlacementError("FILE_TOO_LARGE")
    fd, temp = tempfile.mkstemp(prefix=".local-unit-locations-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as writer:
            fd = -1
            writer.write(raw)
            writer.flush()
            os.fsync(writer.fileno())
        os.replace(temp, path)
        dir_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temp):
            os.unlink(temp)


def run(action: str) -> dict[str, Any]:
    if action == "read":
        return {"ok": True, "document": load()}
    if action != "update":
        raise PlacementError("INVALID_REQUEST")
    data = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not data or len(data) > MAX_REQUEST_BYTES or not data.endswith(b"\n"):
        raise PlacementError("INVALID_REQUEST")
    request = decode(data)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock_path = root / ".local-unit-locations.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise PlacementError("UNSAFE_LOCK")
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
            raise PlacementError("INVALID_REQUEST")
        result = run(args[0])
        code = 0
    except (PlacementError, StorageError, structure.StructureError,
            directory.DirectoryError, OSError) as error:
        code = 2
        result = {"ok": False, "error": error.code if isinstance(error, (
            PlacementError, StorageError, structure.StructureError,
            directory.DirectoryError,
        )) else "STORAGE_UNAVAILABLE"}
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
