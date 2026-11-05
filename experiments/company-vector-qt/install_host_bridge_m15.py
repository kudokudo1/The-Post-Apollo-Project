#!/usr/bin/python3
"""Explicit, owner-local M15 bridge installer. Does not build/launch anything.

Default is read-only inspection. --install / --remove are local mutations and
must only be executed with the operator's specific approval.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import tempfile

SCHEMA = "post-apollo.company-vector-host-install.v1"
TARGET_PARTS = (".local", "libexec", "post-apollo", "company-vector-probe")
BRIDGE_SOURCE = Path(__file__).with_name("CompanyVectorHostBridge.py")


def _owner_directory(directory: Path) -> bool:
    try:
        info = directory.lstat()
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o022


def _safe_existing_target(target: Path, expected: bytes) -> bool:
    try:
        info = target.lstat()
    except OSError:
        return False
    return (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and not (info.st_mode & (0o022 | 0o6000))
            and target.read_bytes() == expected)


def perform(action: str, home: Path | None = None, source: Path = BRIDGE_SOURCE) -> dict:
    root = home if home is not None else Path.home()
    if os.getuid() == 0 or os.geteuid() != os.getuid() or not _owner_directory(root):
        return {"schema": SCHEMA, "status": "REFUSED_IDENTITY"}
    try:
        expected = source.read_bytes()
    except OSError:
        return {"schema": SCHEMA, "status": "SOURCE_UNAVAILABLE"}
    target = root.joinpath(*TARGET_PARTS)
    if action == "check":
        if not target.exists() and not target.is_symlink():
            state = "NOT_INSTALLED"
        else:
            state = "INSTALLED" if _safe_existing_target(target, expected) else "FOREIGN_OR_MODIFIED"
        return {"schema": SCHEMA, "status": state}

    # Never create, change, or remove anything without an explicit action.
    parent = root
    if action == "install":
        for part in TARGET_PARTS[:-1]:
            parent = parent / part
            if not parent.exists() and not parent.is_symlink():
                parent.mkdir(mode=0o700)
            if not _owner_directory(parent):
                return {"schema": SCHEMA, "status": "UNSAFE_DIRECTORY"}
        if target.exists() or target.is_symlink():
            return {"schema": SCHEMA, "status": "ALREADY_INSTALLED" if _safe_existing_target(target, expected) else "REFUSED_EXISTING"}
        # Same-directory hard-link publish is atomic and refuses overwrite.
        staged = None
        try:
            fd, name = tempfile.mkstemp(prefix=".company-vector-m15-", dir=str(parent))
            staged = Path(name)
            with os.fdopen(fd, "wb") as handle:
                handle.write(expected)
                handle.flush()
                os.fsync(handle.fileno())
            staged.chmod(0o700)
            os.link(staged, target, follow_symlinks=False)
            return {"schema": SCHEMA, "status": "INSTALLED"}
        except OSError:
            return {"schema": SCHEMA, "status": "INSTALL_FAILED"}
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    if action == "remove":
        # Never delete a preexisting executable with unrecognized contents.
        for part in TARGET_PARTS[:-1]:
            parent = parent / part
            if not _owner_directory(parent):
                return {"schema": SCHEMA, "status": "UNSAFE_DIRECTORY"}
        if not _safe_existing_target(target, expected):
            return {"schema": SCHEMA, "status": "REFUSED_EXISTING"}
        target.unlink()
        return {"schema": SCHEMA, "status": "REMOVED"}
    return {"schema": SCHEMA, "status": "INVALID_ACTION"}


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in (["check"], ["install"], ["remove"]):
        print(json.dumps({"schema": SCHEMA, "status": "INVALID_ACTION"}))
        return 2
    outcome = perform(args[0])
    print(json.dumps(outcome, separators=(",", ":")))
    return 0 if outcome["status"] in ("NOT_INSTALLED", "INSTALLED", "ALREADY_INSTALLED", "REMOVED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
