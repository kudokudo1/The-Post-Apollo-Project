#!/usr/bin/env python3
"""Local portfolio grouping labels only, never verified organization membership.

A portfolio is a personal directory grouping of local organization IDs.
It does NOT create tenant affiliation, ownership, account access or grants.
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
import SocialOrganizationDirectory as organization_directory

SCHEMA = "post-apollo.social-local-portfolios.v1"
FILE_NAME = "local-portfolios-v1.json"
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 2048
MAX_PORTFOLIOS = 30
MAX_ORGS_PER_PORTFOLIO = 30
NAME_LIMIT = 80
PORTFOLIO_ID = re.compile(r"^portfolio-[1-9][0-9]{0,8}$")
ORG_ID = re.compile(r"^org-[1-9][0-9]{0,8}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
ACTIONS = {
    "create": {"name"},
    "rename": {"portfolioId", "name"},
    "archive": {"portfolioId"},
    "restore": {"portfolioId"},
    "attach": {"portfolioId", "orgId"},
    "detach": {"portfolioId", "orgId"},
}


class PortfolioError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def storage_path() -> Path:
    return root_path() / FILE_NAME


def initial() -> dict[str, Any]:
    return {"schema": SCHEMA, "revision": 0, "nextId": 1, "portfolios": []}


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    item: dict[str, Any] = {}
    for k, v in pairs:
        if k in item:
            raise PortfolioError("INVALID_JSON")
        item[k] = v
    return item


def _reject_constant(_: str) -> None:
    raise PortfolioError("INVALID_JSON")


def decode(payload: bytes) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_pairs,
                          parse_constant=_reject_constant)
    except (UnicodeError, ValueError):
        raise PortfolioError("INVALID_JSON") from None


def _name(value: Any) -> str:
    if type(value) is not str or len(value) > NAME_LIMIT or CONTROL.search(value):
        raise PortfolioError("INVALID_NAME")
    value = value.strip()
    if not value:
        raise PortfolioError("INVALID_NAME")
    return value


def _id(value: Any, regex: re.Pattern[str]) -> str:
    if type(value) is not str or not regex.fullmatch(value):
        raise PortfolioError("INVALID_ID")
    return value


def validate(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or raw.get("schema") != SCHEMA:
        raise PortfolioError("UNSUPPORTED_VERSION")
    if set(raw) != {"schema", "revision", "nextId", "portfolios"}:
        raise PortfolioError("INVALID_DOCUMENT")
    revision, next_id, portfolios = raw["revision"], raw["nextId"], raw["portfolios"]
    if (type(revision) is not int or not 0 <= revision < 1_000_000_000
            or type(next_id) is not int or not 1 <= next_id < 1_000_000_000
            or type(portfolios) is not list or len(portfolios) > MAX_PORTFOLIOS):
        raise PortfolioError("INVALID_DOCUMENT")
    seen_ids: set[str] = set()
    seen_active_names: set[str] = set()
    largest = 0
    cleaned: list[dict[str, Any]] = []
    for p in portfolios:
        if type(p) is not dict or set(p) != {"id", "name", "archived", "orgIds"}:
            raise PortfolioError("INVALID_DOCUMENT")
        pid = _id(p["id"], PORTFOLIO_ID)
        name = _name(p["name"])
        archived, org_ids = p["archived"], p["orgIds"]
        if (pid in seen_ids or type(archived) is not bool
                or type(org_ids) is not list or len(org_ids) > MAX_ORGS_PER_PORTFOLIO):
            raise PortfolioError("INVALID_DOCUMENT")
        if not archived:
            key = name.casefold()
            if key in seen_active_names:
                raise PortfolioError("DUPLICATE_NAME")
            seen_active_names.add(key)
        largest = max(largest, int(pid[len("portfolio-"):]))
        seen_ids.add(pid)
        org_set: set[str] = set()
        clean_orgs: list[str] = []
        for oid in org_ids:
            oid = _id(oid, ORG_ID)
            if oid in org_set:
                raise PortfolioError("DUPLICATE_ORGANIZATION")
            org_set.add(oid)
            clean_orgs.append(oid)
        cleaned.append({"id":pid, "name":name, "archived":archived,
                        "orgIds":clean_orgs})
    if largest >= next_id:
        raise PortfolioError("INVALID_DOCUMENT")
    return {"schema":SCHEMA, "revision":revision, "nextId":next_id,
            "portfolios":cleaned}


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return initial()
    path = storage_path()
    if not _assert_secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as inp:
        info = os.fstat(inp.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise PortfolioError("UNSAFE_FILE")
        data = inp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise PortfolioError("FILE_TOO_LARGE")
    return validate(decode(data))


def _portfolio(document: dict[str, Any], ident: Any) -> dict[str, Any]:
    ident = _id(ident, PORTFOLIO_ID)
    for item in document["portfolios"]:
        if item["id"] == ident:
            return item
    raise PortfolioError("PORTFOLIO_NOT_FOUND")


def _active_org(ident: Any) -> str:
    ident = _id(ident, ORG_ID)
    # Reference validation only: this does NOT verify a real corporate tenant.
    current = organization_directory.load()
    if not any(o["id"] == ident and not o["archived"]
               for o in current["organizations"]):
        raise PortfolioError("ORGANIZATION_UNAVAILABLE")
    return ident


def apply(current: Any, request: Any) -> dict[str, Any]:
    doc = validate(current)
    if type(request) is not dict:
        raise PortfolioError("INVALID_REQUEST")
    action = request.get("action")
    if type(action) is not str or action not in ACTIONS:
        raise PortfolioError("INVALID_REQUEST")
    if set(request) != (ACTIONS[action] | {"action", "expectedRevision"}):
        raise PortfolioError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != doc["revision"]):
        raise PortfolioError("REVISION_CONFLICT")

    portfolios = doc["portfolios"]
    if action == "create":
        name = _name(request["name"])
        if len(portfolios) >= MAX_PORTFOLIOS:
            raise PortfolioError("PORTFOLIO_CAPACITY")
        if any(not p["archived"] and p["name"].casefold() == name.casefold()
               for p in portfolios):
            raise PortfolioError("DUPLICATE_NAME")
        portfolios.append({"id":f'portfolio-{doc["nextId"]}', "name":name,
                           "archived":False, "orgIds":[]})
        doc["nextId"] += 1
    else:
        p = _portfolio(doc, request["portfolioId"])
        if action == "restore":
            if not p["archived"]:
                raise PortfolioError("NO_CHANGE")
            if any(item is not p and not item["archived"]
                   and item["name"].casefold() == p["name"].casefold()
                   for item in portfolios):
                raise PortfolioError("DUPLICATE_NAME")
            p["archived"] = False
        elif action == "archive":
            if p["archived"]:
                raise PortfolioError("NO_CHANGE")
            p["archived"] = True
        else:
            if p["archived"]:
                raise PortfolioError("PORTFOLIO_ARCHIVED")
            if action == "rename":
                name = _name(request["name"])
                if any(item is not p and not item["archived"]
                       and item["name"].casefold() == name.casefold()
                       for item in portfolios):
                    raise PortfolioError("DUPLICATE_NAME")
                if p["name"] == name:
                    raise PortfolioError("NO_CHANGE")
                p["name"] = name
            elif action == "attach":
                oid = _active_org(request["orgId"])
                if oid in p["orgIds"]:
                    raise PortfolioError("ALREADY_ATTACHED")
                if len(p["orgIds"]) >= MAX_ORGS_PER_PORTFOLIO:
                    raise PortfolioError("ORGANIZATION_CAPACITY")
                p["orgIds"].append(oid)
            elif action == "detach":
                # Detaching an archived/missing org must remain possible.
                oid = _id(request["orgId"], ORG_ID)
                if oid not in p["orgIds"]:
                    raise PortfolioError("NOT_ATTACHED")
                p["orgIds"].remove(oid)

    doc["revision"] += 1
    return validate(doc)


def save(document: Any) -> None:
    doc = validate(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    path = storage_path()
    _assert_secure_file(path)
    encoded = (json.dumps(doc, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    if len(encoded) > MAX_BYTES:
        raise PortfolioError("FILE_TOO_LARGE")
    fd, temp = tempfile.mkstemp(prefix=".local-portfolios-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
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
        return {"ok":True, "document":load()}
    if action != "update":
        raise PortfolioError("INVALID_REQUEST")
    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if (not raw or len(raw) > MAX_REQUEST_BYTES
            or not raw.endswith(b"\n")):
        raise PortfolioError("INVALID_REQUEST")
    request = decode(raw)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock = root / ".local-portfolios.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise PortfolioError("UNSAFE_LOCK")
        fcntl.flock(fd, fcntl.LOCK_EX)
        changed = apply(load(), request)
        save(changed)
    finally:
        os.close(fd)
    return {"ok":True, "document":changed}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args not in (["read"], ["update"]):
            raise PortfolioError("INVALID_REQUEST")
        result = run(args[0])
        code = 0
    except (PortfolioError, StorageError,
            organization_directory.DirectoryError, OSError) as exc:
        code = 2
        result = {"ok":False, "error":exc.code if isinstance(
            exc, (PortfolioError, StorageError, organization_directory.DirectoryError)
        ) else "STORAGE_UNAVAILABLE"}
    print(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
