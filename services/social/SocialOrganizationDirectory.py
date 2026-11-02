#!/usr/bin/env python3
"""Private local organization/branch directory. Never an authorization source.

Only names, kinds and reversible archive flags are stored. No credentials,
provider subjects, grants, signed-in state or privileged operations.
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

from SocialAccountDetails import _assert_secure_dir, _assert_secure_file, root_path

SCHEMA = "post-apollo.social-local-organizations.v1"
FILE_NAME = "local-organizations-v1.json"
MAX_BYTES = 65536
MAX_REQUEST = 2048
MAX_ORGS = 30
MAX_BRANCHES = 40
IDENTIFIER = re.compile(r"^(org|branch)-[1-9][0-9]{0,8}$")
CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
FIELDS = {
    "add_org": ("name", "kind"),
    "rename_org": ("orgId", "name"),
    "archive_org": ("orgId",),
    "restore_org": ("orgId",),
    "add_branch": ("orgId", "name"),
    "rename_branch": ("orgId", "branchId", "name"),
    "archive_branch": ("orgId", "branchId"),
    "restore_branch": ("orgId", "branchId"),
}


class DirectoryError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def location() -> Path:
    return root_path() / FILE_NAME


def initial() -> dict[str, Any]:
    return {"schema": SCHEMA, "revision": 0, "nextId": 1, "organizations": []}


def label(value: Any) -> str:
    if type(value) is not str or len(value) > 80 or CONTROLS.search(value):
        raise DirectoryError("INVALID_NAME")
    clean = value.strip()
    if not clean:
        raise DirectoryError("INVALID_NAME")
    return clean


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise DirectoryError("INVALID_JSON")
        obj[key] = value
    return obj


def decode(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        raise DirectoryError("INVALID_JSON") from None


def validate(doc: Any) -> dict[str, Any]:
    if type(doc) is not dict or doc.get("schema") != SCHEMA:
        raise DirectoryError("UNSUPPORTED_VERSION")
    if set(doc) != {"schema", "revision", "nextId", "organizations"}:
        raise DirectoryError("INVALID_DOCUMENT")
    rev, next_id, orgs = doc["revision"], doc["nextId"], doc["organizations"]
    if (type(rev) is not int or not 0 <= rev < 1_000_000_000
            or type(next_id) is not int or not 1 <= next_id < 1_000_000_000
            or type(orgs) is not list or len(orgs) > MAX_ORGS):
        raise DirectoryError("INVALID_DOCUMENT")
    seen: set[str] = set()
    active_names: set[str] = set()
    maximum = 0
    clean_orgs = []
    for org in orgs:
        if type(org) is not dict or set(org) != {"id", "name", "kind", "archived", "branches"}:
            raise DirectoryError("INVALID_DOCUMENT")
        oid = org["id"]
        if (type(oid) is not str or not IDENTIFIER.fullmatch(oid)
                or not oid.startswith("org-") or oid in seen
                or org["kind"] not in ("llc", "nonprofit", "other")
                or type(org["archived"]) is not bool):
            raise DirectoryError("INVALID_DOCUMENT")
        maximum = max(maximum, int(oid.split("-")[1]))
        seen.add(oid)
        org_name = label(org["name"])
        if not org["archived"]:
            if org_name.casefold() in active_names:
                raise DirectoryError("DUPLICATE_NAME")
            active_names.add(org_name.casefold())
        branches = org["branches"]
        if type(branches) is not list or len(branches) > MAX_BRANCHES:
            raise DirectoryError("INVALID_DOCUMENT")
        branch_names: set[str] = set()
        clean_branches = []
        for branch in branches:
            if type(branch) is not dict or set(branch) != {"id", "name", "archived"}:
                raise DirectoryError("INVALID_DOCUMENT")
            bid = branch["id"]
            if (type(bid) is not str or not IDENTIFIER.fullmatch(bid)
                    or not bid.startswith("branch-") or bid in seen
                    or type(branch["archived"]) is not bool):
                raise DirectoryError("INVALID_DOCUMENT")
            seen.add(bid)
            maximum = max(maximum, int(bid.split("-")[1]))
            branch_name = label(branch["name"])
            if not branch["archived"]:
                if branch_name.casefold() in branch_names:
                    raise DirectoryError("DUPLICATE_NAME")
                branch_names.add(branch_name.casefold())
            clean_branches.append({"id": bid, "name": branch_name,
                                   "archived": branch["archived"]})
        clean_orgs.append({"id": oid, "name": org_name, "kind": org["kind"],
                           "archived": org["archived"], "branches": clean_branches})
    if maximum >= next_id:
        raise DirectoryError("INVALID_DOCUMENT")
    return {"schema": SCHEMA, "revision": rev, "nextId": next_id,
            "organizations": clean_orgs}


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return initial()
    path = location()
    if not _assert_secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        st = os.fstat(stream.fileno())
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077):
            raise DirectoryError("UNSAFE_FILE")
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise DirectoryError("FILE_TOO_LARGE")
    return validate(decode(raw))


def _find(items: list[dict], ident: Any, kind: str) -> dict:
    if (type(ident) is not str or not IDENTIFIER.fullmatch(ident)
            or not ident.startswith(kind + "-")):
        raise DirectoryError("INVALID_ID")
    for item in items:
        if item["id"] == ident:
            return item
    raise DirectoryError("NOT_FOUND")


def apply(current: Any, request: Any) -> dict[str, Any]:
    doc = validate(current)
    if type(request) is not dict:
        raise DirectoryError("INVALID_REQUEST")
    op = request.get("action")
    if op not in FIELDS or set(request) != {"action", "expectedRevision", *FIELDS[op]}:
        raise DirectoryError("INVALID_REQUEST")
    if type(request["expectedRevision"]) is not int or request["expectedRevision"] != doc["revision"]:
        raise DirectoryError("REVISION_CONFLICT")
    orgs = doc["organizations"]
    if op == "add_org":
        name = label(request["name"])
        kind = request["kind"]
        if kind not in ("llc", "nonprofit", "other") or type(kind) is not str:
            raise DirectoryError("INVALID_KIND")
        if len(orgs) >= MAX_ORGS:
            raise DirectoryError("ORG_CAPACITY")
        if any(not o["archived"] and o["name"].casefold() == name.casefold() for o in orgs):
            raise DirectoryError("DUPLICATE_NAME")
        orgs.append({"id": "org-" + str(doc["nextId"]), "name": name,
                     "kind": kind, "archived": False, "branches": []})
        doc["nextId"] += 1
    else:
        org = _find(orgs, request["orgId"], "org")
        if op == "rename_org":
            if org["archived"]:
                raise DirectoryError("ARCHIVED")
            name = label(request["name"])
            if any(o is not org and not o["archived"]
                   and o["name"].casefold() == name.casefold() for o in orgs):
                raise DirectoryError("DUPLICATE_NAME")
            org["name"] = name
        elif op in ("archive_org", "restore_org"):
            archived = op == "archive_org"
            if org["archived"] == archived:
                raise DirectoryError("NO_CHANGE")
            if not archived and any(o is not org and not o["archived"]
                                    and o["name"].casefold() == org["name"].casefold()
                                    for o in orgs):
                raise DirectoryError("DUPLICATE_NAME")
            org["archived"] = archived
        else:
            if org["archived"]:
                raise DirectoryError("ARCHIVED")
            branches = org["branches"]
            if op == "add_branch":
                name = label(request["name"])
                if len(branches) >= MAX_BRANCHES:
                    raise DirectoryError("BRANCH_CAPACITY")
                if any(not b["archived"] and b["name"].casefold() == name.casefold()
                       for b in branches):
                    raise DirectoryError("DUPLICATE_NAME")
                branches.append({"id": "branch-" + str(doc["nextId"]),
                                 "name": name, "archived": False})
                doc["nextId"] += 1
            else:
                branch = _find(branches, request["branchId"], "branch")
                if op == "rename_branch":
                    if branch["archived"]:
                        raise DirectoryError("ARCHIVED")
                    name = label(request["name"])
                    if any(b is not branch and not b["archived"]
                           and b["name"].casefold() == name.casefold() for b in branches):
                        raise DirectoryError("DUPLICATE_NAME")
                    branch["name"] = name
                else:
                    archived = op == "archive_branch"
                    if branch["archived"] == archived:
                        raise DirectoryError("NO_CHANGE")
                    if not archived and any(b is not branch and not b["archived"]
                                            and b["name"].casefold() == branch["name"].casefold()
                                            for b in branches):
                        raise DirectoryError("DUPLICATE_NAME")
                    branch["archived"] = archived
    doc["revision"] += 1
    return validate(doc)


def save(doc: dict[str, Any]) -> None:
    clean = validate(doc)
    root = root_path()
    _assert_secure_dir(root, create=True)
    target = location()
    _assert_secure_file(target)
    data = (json.dumps(clean, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
    if len(data) > MAX_BYTES:
        raise DirectoryError("FILE_TOO_LARGE")
    fd, temp = tempfile.mkstemp(prefix=".local-organizations-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
        directory_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
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
        raise DirectoryError("INVALID_REQUEST")
    raw = sys.stdin.buffer.readline(MAX_REQUEST + 1)
    if not raw or len(raw) > MAX_REQUEST or not raw.endswith(b"\n"):
        raise DirectoryError("INVALID_REQUEST")
    request = decode(raw)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock = root / ".local-organizations.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077):
            raise DirectoryError("UNSAFE_LOCK")
        fcntl.flock(fd, fcntl.LOCK_EX)
        doc = apply(load(), request)
        save(doc)
    finally:
        os.close(fd)
    return {"ok": True, "document": doc}


def main(argv: list[str] | None = None) -> int:
    action = (sys.argv[1:] if argv is None else argv)
    try:
        if action not in (["read"], ["update"]):
            raise DirectoryError("INVALID_REQUEST")
        result = run(action[0])
        code = 0
    except (DirectoryError, OSError) as error:
        result = {"ok": False, "error": error.code if isinstance(error, DirectoryError)
                  else "STORAGE_UNAVAILABLE"}
        code = 2
    print(json.dumps(result, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
