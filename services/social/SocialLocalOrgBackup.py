#!/usr/bin/env python3
"""Owner-local organization backup snapshots. No restore/write-back action.

Covers only seven organization LABEL stores, never credentials, identity
contacts, provider tokens, or verified organization grants.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tempfile
from typing import Any

from SocialAccountDetails import (
    StoreError, _assert_secure_dir, _assert_secure_file, root_path,
)
import SocialOrganizationDirectory as directory
import SocialLocalPortfolios as portfolios
import SocialLocalOrganizationStructure as structure
import SocialLocalUnitLocationLinks as units
import SocialLocalBranchLocationLinks as branches
import SocialLocalFunctionalReporting as reporting
import SocialOrganizationLinks as social_links

SCHEMA = "post-apollo.social-local-org-backup.v1"
FOLDER = "organization-backups-v1"
MAX_BUNDLE_BYTES = 600_000
MAX_BACKUPS = 40
FILENAME = re.compile(r"^org-backup-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}\.json$")
SOURCES = (
    ("directory", directory, ".local-organizations.lock", "organizations"),
    ("portfolios", portfolios, ".local-portfolios.lock", "portfolios"),
    ("structure", structure, ".local-org-structure.lock", "units"),
    ("unitLocations", units, ".local-unit-locations.lock", "links"),
    ("branchLocations", branches, ".branch-location.lock", "links"),
    ("reporting", reporting, ".local-functional-reporting.lock", "links"),
    ("socialLinks", social_links, ".local-social-links.lock", "links"),
)


class BackupError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def folder(*, create: bool) -> Path | None:
    root = root_path()
    if not _assert_secure_dir(root, create=create):
        return None
    target = root / FOLDER
    if not _assert_secure_dir(target, create=create):
        return None
    return target


def canonical(document: Any) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def checksum(document: Any) -> str:
    return hashlib.sha256(canonical(document)).hexdigest()


def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise BackupError("INVALID_JSON")
        out[key] = value
    return out


def reject_constant(_: str) -> None:
    raise BackupError("INVALID_JSON")


def parse(raw: bytes) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=reject_duplicate,
                          parse_constant=reject_constant)
    except (ValueError, UnicodeError):
        raise BackupError("INVALID_JSON") from None


def lock_sources(stack: ExitStack) -> None:
    """Hold all seven original writer locks to prevent mid-snapshot edits."""
    root = root_path()
    _assert_secure_dir(root, create=True)
    for _, _, name, _ in sorted(SOURCES, key=lambda item: item[2]):
        path = root / name
        fd = os.open(path, os.O_CREAT | os.O_RDWR
                     | getattr(os, "O_NOFOLLOW", 0), 0o600)
        stack.callback(os.close, fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise BackupError("UNSAFE_LOCK")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BackupError("STORES_BUSY") from None


def validated_documents() -> dict[str, Any]:
    with ExitStack() as stack:
        lock_sources(stack)
        return {
            key: module.validate(module.load())
            for key, module, _, _ in SOURCES
        }


def inventory(documents: dict[str, Any]) -> dict[str, Any]:
    return {
        key: {"revision": documents[key]["revision"],
              "records": len(documents[key][record_key])}
        for key, _, _, record_key in SOURCES
    }


def snapshot() -> dict[str, Any]:
    docs = validated_documents()
    return {
        "schema": SCHEMA,
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "documents": docs,
        "sha256": {key: checksum(doc) for key, doc in docs.items()},
    }


def names() -> list[str]:
    target = folder(create=False)
    if target is None:
        return []
    out = []
    for item in target.iterdir():
        if FILENAME.fullmatch(item.name):
            _assert_secure_file(item)
            out.append(item.name)
    return sorted(out, reverse=True)


def list_backups() -> dict[str, Any]:
    matched = names()
    return {"ok": True, "backups": matched[:MAX_BACKUPS],
            "total": len(matched), "folder": FOLDER}


def make_backup() -> dict[str, Any]:
    if len(names()) >= MAX_BACKUPS:
        raise BackupError("BACKUP_LIMIT")
    data = snapshot()
    encoded = canonical(data) + b"\n"
    if len(encoded) > MAX_BUNDLE_BYTES:
        raise BackupError("BACKUP_TOO_LARGE")
    target = folder(create=True)
    assert target is not None
    filename = ("org-backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                + "-" + secrets.token_hex(6) + ".json")
    final = target / filename
    fd, temporary = tempfile.mkstemp(prefix=".creating-", dir=target)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as out:
            fd = -1
            out.write(encoded)
            out.flush()
            os.fsync(out.fileno())
        # Link, unlike replace, is no-clobber if random names collide.
        os.link(temporary, final, follow_symlinks=False)
        dfd = os.open(target, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"ok": True, "backup": filename, "createdAt": data["createdAt"],
            "inventory": inventory(data["documents"]), "restored": False}


def read_backup(filename: str) -> dict[str, Any]:
    if type(filename) is not str or not FILENAME.fullmatch(filename):
        raise BackupError("INVALID_BACKUP_ID")
    target_dir = folder(create=False)
    if target_dir is None:
        raise BackupError("BACKUP_NOT_FOUND")
    target = target_dir / filename
    if not _assert_secure_file(target):
        raise BackupError("BACKUP_NOT_FOUND")
    fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            raise BackupError("UNSAFE_FILE")
        raw = source.read(MAX_BUNDLE_BYTES + 1)
    if len(raw) > MAX_BUNDLE_BYTES:
        raise BackupError("BACKUP_TOO_LARGE")
    bundle = parse(raw)
    if (type(bundle) is not dict
            or set(bundle) != {"schema", "createdAt", "documents", "sha256"}
            or bundle["schema"] != SCHEMA
            or type(bundle["createdAt"]) is not str
            or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
                                 bundle["createdAt"])
            or type(bundle["documents"]) is not dict
            or type(bundle["sha256"]) is not dict):
        raise BackupError("INVALID_BACKUP")
    expected = {name for name, _, _, _ in SOURCES}
    if set(bundle["documents"]) != expected or set(bundle["sha256"]) != expected:
        raise BackupError("INCOMPLETE_BACKUP")
    for name, module, _, _ in SOURCES:
        doc = bundle["documents"][name]
        try:
            clean = module.validate(doc)
        except (ValueError, TypeError, Exception) as error:
            raise BackupError("INVALID_BACKUP_DOCUMENT") from None
        if clean != doc:
            raise BackupError("NONCANONICAL_BACKUP")
        digest = bundle["sha256"][name]
        if (type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest)
                or not secrets.compare_digest(checksum(doc), digest)):
            raise BackupError("CHECKSUM_MISMATCH")
    return bundle


def verify(filename: str) -> dict[str, Any]:
    bundle = read_backup(filename)
    return {"ok": True, "valid": True, "backup": filename,
            "createdAt": bundle["createdAt"],
            "inventory": inventory(bundle["documents"]),
            "restoreAvailable": False}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ["list"]:
            result = list_backups()
        elif args == ["create"]:
            result = make_backup()
        elif len(args) == 2 and args[0] == "verify":
            result = verify(args[1])
        else:
            raise BackupError("INVALID_REQUEST")
        code = 0
    except (BackupError, StoreError, OSError, ValueError, TypeError) as error:
        result = {"ok": False, "error": (error.code if hasattr(error, "code")
                                             else "STORAGE_UNAVAILABLE")}
        code = 2
    # No record documents or credentials are echoed to the Qt process.
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
