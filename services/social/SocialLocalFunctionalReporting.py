#!/usr/bin/env python3
"""Explicit local functional reporting links, never trusted workforce authority.

The graph relates existing functional unit labels of one local organization.
It is acyclic, but does not impose one parent or one fixed kind ordering.
No staff, provider account, verified membership or access grant is stored.
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
import SocialOrganizationDirectory as directory
import SocialLocalOrganizationStructure as structure

SCHEMA = "post-apollo.social-local-functional-reporting.v1"
FILE_NAME = "local-functional-reporting-v1.json"
MAX_BYTES = 65536
MAX_REQUEST_BYTES = 2048
MAX_EDGES = 400
ORG_ID = re.compile(r"^org-[1-9][0-9]{0,8}$")
UNIT_ID = re.compile(r"^unit-[1-9][0-9]{0,8}$")
EDGE_ID = re.compile(r"^report-link-[1-9][0-9]{0,8}$")
FUNCTION_KINDS = frozenset(("division", "department", "team"))
FIELDS = {"add": {"orgId", "parentId", "childId"}, "remove": {"linkId"}}


class ReportingError(Exception):
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
            raise ReportingError("INVALID_JSON")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ReportingError("INVALID_JSON")


def decode(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=_reject_constant)
    except (UnicodeError, ValueError):
        raise ReportingError("INVALID_JSON") from None


def _id(value: Any, regex: re.Pattern[str]) -> str:
    if type(value) is not str or not regex.fullmatch(value):
        raise ReportingError("INVALID_ID")
    return value


def _acyclic(edges: list[dict[str, str]]) -> None:
    # Every stored edge counts, even when its source unit is archived.
    # Restoring a unit must never uncover an already-persisted cycle.
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        parent = edge["orgId"] + ":" + edge["parentId"]
        child = edge["orgId"] + ":" + edge["childId"]
        adjacency.setdefault(parent, []).append(child)
    gray: set[str] = set()
    black: set[str] = set()
    def visit(start: str) -> None:
        # Iterative DFS avoids recursion limits and handles up to MAX_EDGES.
        stack: list[tuple[str, int]] = [(start, 0)]
        gray.add(start)
        while stack:
            node, index = stack[-1]
            children = adjacency.get(node, [])
            if index == len(children):
                gray.remove(node)
                black.add(node)
                stack.pop()
                continue
            stack[-1] = (node, index + 1)
            nxt = children[index]
            if nxt in gray:
                raise ReportingError("CYCLE_DETECTED")
            if nxt not in black:
                gray.add(nxt)
                stack.append((nxt, 0))
    for node in tuple(adjacency):
        if node not in black:
            visit(node)


def validate(raw: Any) -> dict[str, Any]:
    if type(raw) is not dict or raw.get("schema") != SCHEMA:
        raise ReportingError("UNSUPPORTED_VERSION")
    if set(raw) != {"schema", "revision", "nextId", "links"}:
        raise ReportingError("INVALID_DOCUMENT")
    revision, counter, links = raw["revision"], raw["nextId"], raw["links"]
    if (type(revision) is not int or not 0 <= revision < 1_000_000_000
            or type(counter) is not int or not 1 <= counter < 1_000_000_000
            or type(links) is not list or len(links) > MAX_EDGES):
        raise ReportingError("INVALID_DOCUMENT")
    ids: set[str] = set()
    triples: set[tuple[str, str, str]] = set()
    max_id = 0
    cleaned: list[dict[str, str]] = []
    for edge in links:
        if (type(edge) is not dict
                or set(edge) != {"id", "orgId", "parentId", "childId"}):
            raise ReportingError("INVALID_DOCUMENT")
        edge_id = _id(edge["id"], EDGE_ID)
        org_id = _id(edge["orgId"], ORG_ID)
        parent = _id(edge["parentId"], UNIT_ID)
        child = _id(edge["childId"], UNIT_ID)
        triple = (org_id, parent, child)
        if parent == child:
            raise ReportingError("SELF_LINK")
        if edge_id in ids or triple in triples:
            raise ReportingError("DUPLICATE_LINK")
        ids.add(edge_id)
        triples.add(triple)
        max_id = max(max_id, int(edge_id[len("report-link-"):]))
        cleaned.append({
            "id": edge_id, "orgId": org_id,
            "parentId": parent, "childId": child,
        })
    if max_id >= counter:
        raise ReportingError("INVALID_DOCUMENT")
    _acyclic(cleaned)
    return {"schema": SCHEMA, "revision": revision,
            "nextId": counter, "links": cleaned}


def load() -> dict[str, Any]:
    root = root_path()
    if not _assert_secure_dir(root, create=False):
        return initial()
    path = storage_path()
    if not _assert_secure_file(path):
        return initial()
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as reader:
        st = os.fstat(reader.fileno())
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077):
            raise ReportingError("UNSAFE_FILE")
        data = reader.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ReportingError("FILE_TOO_LARGE")
    return validate(decode(data))


def _active_targets(org_id: str, parent_id: str, child_id: str) -> None:
    # Local metadata consistency, not authorization.
    doc = directory.load()
    if not any(org["id"] == org_id and not org["archived"]
               for org in doc["organizations"]):
        raise ReportingError("ORGANIZATION_UNAVAILABLE")
    units = {unit["id"]: unit for unit in structure.load()["units"]}
    for kind, ident in (("PARENT", parent_id), ("CHILD", child_id)):
        target = units.get(ident)
        if (not target or target["orgId"] != org_id or target["archived"]
                or target["kind"] not in FUNCTION_KINDS):
            raise ReportingError(kind + "_UNAVAILABLE")


def apply(current: Any, request: Any) -> dict[str, Any]:
    doc = validate(current)
    if type(request) is not dict or type(request.get("action")) is not str:
        raise ReportingError("INVALID_REQUEST")
    action = request["action"]
    if (action not in FIELDS
            or set(request) != FIELDS[action] | {"action", "expectedRevision"}):
        raise ReportingError("INVALID_REQUEST")
    if (type(request["expectedRevision"]) is not int
            or request["expectedRevision"] != doc["revision"]):
        raise ReportingError("REVISION_CONFLICT")
    if action == "add":
        if len(doc["links"]) >= MAX_EDGES:
            raise ReportingError("LINK_CAPACITY")
        org_id = _id(request["orgId"], ORG_ID)
        parent_id = _id(request["parentId"], UNIT_ID)
        child_id = _id(request["childId"], UNIT_ID)
        if parent_id == child_id:
            raise ReportingError("SELF_LINK")
        _active_targets(org_id, parent_id, child_id)
        if any(edge["orgId"] == org_id
               and edge["parentId"] == parent_id
               and edge["childId"] == child_id for edge in doc["links"]):
            raise ReportingError("DUPLICATE_LINK")
        doc["links"].append({
            "id": f'report-link-{doc["nextId"]}', "orgId": org_id,
            "parentId": parent_id, "childId": child_id,
        })
        _acyclic(doc["links"])
        doc["nextId"] += 1
    else:
        link_id = _id(request["linkId"], EDGE_ID)
        index = next((i for i, edge in enumerate(doc["links"])
                      if edge["id"] == link_id), -1)
        if index == -1:
            raise ReportingError("LINK_NOT_FOUND")
        # Stale references must remain removable, not silently deleted.
        doc["links"].pop(index)
    doc["revision"] += 1
    return validate(doc)


def save(document: Any) -> None:
    clean = validate(document)
    root = root_path()
    _assert_secure_dir(root, create=True)
    path = storage_path()
    _assert_secure_file(path)
    data = (json.dumps(clean, ensure_ascii=True, separators=(",", ":"))
            + "\n").encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ReportingError("FILE_TOO_LARGE")
    fd, temp = tempfile.mkstemp(prefix=".local-functional-reporting-", dir=root)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as writer:
            fd = -1
            writer.write(data)
            writer.flush()
            os.fsync(writer.fileno())
        directory_fd = os.open(root, os.O_RDONLY |
                               getattr(os, "O_DIRECTORY", 0))
        try:
            os.replace(temp, path)
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
        raise ReportingError("INVALID_REQUEST")
    data = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
    if not data or len(data) > MAX_REQUEST_BYTES or not data.endswith(b"\n"):
        raise ReportingError("INVALID_REQUEST")
    request = decode(data)
    root = root_path()
    _assert_secure_dir(root, create=True)
    lock = root / ".local-functional-reporting.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or st.st_mode & 0o077):
            raise ReportingError("UNSAFE_LOCK")
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
            raise ReportingError("INVALID_REQUEST")
        result = run(args[0])
        status = 0
    except (ReportingError, StorageError, directory.DirectoryError,
            structure.StructureError, OSError) as error:
        status = 2
        result = {"ok": False, "error": error.code if isinstance(error, (
            ReportingError, StorageError, directory.DirectoryError,
            structure.StructureError,
        )) else "STORAGE_UNAVAILABLE"}
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
