#!/usr/bin/env python3
"""Manual links between local organization records and Social layout/account labels.

This store is NOT an Identity Center authority or an Account Broker:
it stores only opaque local IDs, never tokens, roles, provider subjects or grants.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any

from SocialAccountDetails import (
    ITEM_BY_ID, StoreError as ExistingStorageError,
    _assert_secure_dir, _assert_secure_file, root_path,
)
import SocialOrganizationDirectory as organizations

SCHEMA = "post-apollo.social-local-associations.v1"
FILE_NAME = "local-social-associations-v1.json"
MAX_LINKS = 120
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 2048
NUMBERED = re.compile(r"^[1-9][0-9]{0,8}$")
IDENTITY_ID = re.compile(r"^identity-[1-9][0-9]{0,8}$")
ACCOUNT_ID = re.compile(r"^account-[1-9][0-9]{0,8}$")
LINK_ID = re.compile(r"^link-[1-9][0-9]{0,8}$")
ORG_ID = re.compile(r"^org-[1-9][0-9]{0,8}$")
BRANCH_ID = re.compile(r"^branch-[1-9][0-9]{0,8}$")
LINK_FIELDS = {"id", "orgId", "branchId", "identityId", "serviceId", "accountId"}


class LinkError(Exception):
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
            raise LinkError("INVALID_JSON")
        result[key] = value
    return result


def _bad_constant(_value: str) -> None:
    raise LinkError("INVALID_JSON")


def decode(payload: bytes) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_pairs,
                          parse_constant=_bad_constant)
    except (UnicodeError, ValueError):
        raise LinkError("INVALID_JSON") from None


def _required_id(value: Any, pattern: re.Pattern[str]) -> str:
    if type(value) is not str or not pattern.fullmatch(value):
        raise LinkError("INVALID_ID")
    return value


def validate(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or raw.get("schema") != SCHEMA:
        raise LinkError("UNSUPPORTED_VERSION")
    if set(raw) != {"schema", "revision", "nextId", "links"}:
        raise LinkError("INVALID_DOCUMENT")
    revision, counter, links = raw["revision"], raw["nextId"], raw["links"]
    if (type(revision) is not int or not 0 <= revision < 1_000_000_000
            or type(counter) is not int or not 1 <= counter < 1_000_000_000
            or type(links) is not list or len(links) > MAX_LINKS):
        raise LinkError("INVALID_DOCUMENT")

    ids: set[str] = set()
    tuples: set[tuple[str, str | None, str, str | None, str | None]] = set()
    largest = 0
    clean = []
    for entry in links:
        if type(entry) is not dict or set(entry) != LINK_FIELDS:
            raise LinkError("INVALID_DOCUMENT")
        ident = _required_id(entry["id"], LINK_ID)
        org_id = _required_id(entry["orgId"], ORG_ID)
        branch_id = entry["branchId"]
        if branch_id is not None:
            branch_id = _required_id(branch_id, BRANCH_ID)
        identity_id = _required_id(entry["identityId"], IDENTITY_ID)
        service_id, account_id = entry["serviceId"], entry["accountId"]
        if (service_id is None) != (account_id is None):
            raise LinkError("INVALID_DOCUMENT")
        if service_id is not None:
            if type(service_id) is not str or service_id not in ITEM_BY_ID:
                raise LinkError("INVALID_SERVICE")
            account_id = _required_id(account_id, ACCOUNT_ID)
        key = (org_id, branch_id, identity_id, service_id, account_id)
        if ident in ids or key in tuples:
            raise LinkError("DUPLICATE_LINK")
        ids.add(ident)
        tuples.add(key)
        largest = max(largest, int(ident[5:]))
        clean.append({
            "id": ident, "orgId": org_id, "branchId": branch_id,
            "identityId": identity_id,
            "serviceId": service_id, "accountId": account_id,
        })
    if largest >= counter:
        raise LinkError("INVALID_DOCUMENT")
    return {"schema": SCHEMA, "revision": revision, "nextId": counter,
            "links": clean}


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return initial()
    path = storage_path()
    if not _assert_secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise LinkError("UNSAFE_FILE")
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise LinkError("FILE_TOO_LARGE")
    return validate(decode(payload))


def _local_target(org_id: str, branch_id: str | None) -> None:
    # A local directory entry is not a verified tenant, but link creation
    # must never target a missing or archived local record.
    doc = organizations.load()
    org = next((item for item in doc["organizations"]
                if item["id"] == org_id), None)
    if org is None or org["archived"]:
        raise LinkError("ORGANIZATION_UNAVAILABLE")
    if branch_id is not None:
        branch = next((item for item in org["branches"]
                       if item["id"] == branch_id), None)
        if branch is None or branch["archived"]:
            raise LinkError("BRANCH_UNAVAILABLE")


def apply(document: Any, request: Any) -> dict[str, Any]:
    doc = validate(document)
    if type(request) is not dict:
        raise LinkError("INVALID_REQUEST")
    action = request.get("action")
    fields = ({"action", "expectedRevision", "orgId", "branchId",
               "identityId", "serviceId", "accountId"} if action == "add_link"
              else {"action", "expectedRevision", "linkId"}
              if action == "remove_link" else set())
    if not fields or set(request) != fields:
        raise LinkError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != doc["revision"]):
        raise LinkError("REVISION_CONFLICT")

    if action == "add_link":
        if len(doc["links"]) >= MAX_LINKS:
            raise LinkError("LINK_CAPACITY")
        org_id = _required_id(request["orgId"], ORG_ID)
        branch_id = request["branchId"]
        if branch_id is not None:
            branch_id = _required_id(branch_id, BRANCH_ID)
        identity_id = _required_id(request["identityId"], IDENTITY_ID)
        service_id, account_id = request["serviceId"], request["accountId"]
        if (service_id is None) != (account_id is None):
            raise LinkError("INVALID_REQUEST")
        if service_id is not None:
            if type(service_id) is not str or service_id not in ITEM_BY_ID:
                raise LinkError("INVALID_SERVICE")
            account_id = _required_id(account_id, ACCOUNT_ID)
        _local_target(org_id, branch_id)
        key = (org_id, branch_id, identity_id, service_id, account_id)
        for entry in doc["links"]:
            if key == (entry["orgId"], entry["branchId"], entry["identityId"],
                       entry["serviceId"], entry["accountId"]):
                raise LinkError("DUPLICATE_LINK")
        doc["links"].append({
            "id": f'link-{doc["nextId"]}', "orgId": org_id,
            "branchId": branch_id, "identityId": identity_id,
            "serviceId": service_id, "accountId": account_id,
        })
        doc["nextId"] += 1
    else:
        link_id = _required_id(request["linkId"], LINK_ID)
        index = next((i for i, entry in enumerate(doc["links"])
                      if entry["id"] == link_id), -1)
        if index == -1:
            raise LinkError("LINK_NOT_FOUND")
        doc["links"].pop(index)

    doc["revision"] += 1
    return validate(doc)


def save(document: Any) -> None:
    doc = validate(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    path = storage_path()
    _assert_secure_file(path)
    payload = (json.dumps(doc, ensure_ascii=True, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise LinkError("FILE_TOO_LARGE")
    fd, tmp = tempfile.mkstemp(prefix=".local-social-links-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(payload)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        dir_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(tmp):
            os.unlink(tmp)


def run(action: str) -> dict[str, Any]:
    if action == "read":
        return {"ok": True, "document": load()}
    if action != "update":
        raise LinkError("INVALID_REQUEST")
    payload = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if (not payload or len(payload) > MAX_REQUEST_BYTES
            or not payload.endswith(b"\n")):
        raise LinkError("INVALID_REQUEST")
    request = decode(payload)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock_path = root / ".local-social-links.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise LinkError("UNSAFE_LOCK")
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
            raise LinkError("INVALID_REQUEST")
        result = run(args[0])
        status = 0
    except (LinkError, ExistingStorageError, organizations.DirectoryError, OSError) as exc:
        result = {"ok": False, "error": exc.code if isinstance(
            exc, (LinkError, ExistingStorageError, organizations.DirectoryError)
        ) else "STORAGE_UNAVAILABLE"}
        status = 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
