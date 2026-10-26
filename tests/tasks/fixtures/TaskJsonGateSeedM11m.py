#!/usr/bin/env python3
"""Explicit one-time disposable M11m fixture seed; not for live task folders.

Creates a new named private folder and a synthetic v3 task JSON fixture.
Never overwrites, imports or discovers user task data. Requires an existing,
absolute, owner-only parent; not run automatically by Quickshell or CI.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat


def seed(parent: Path):
    if not isinstance(parent, Path) or not parent.is_absolute():
        raise ValueError("ABSOLUTE_PRIVATE_PARENT_REQUIRED")
    info = parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or parent.is_symlink()
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError("PRIVATE_PARENT_REQUIRED")
    folder = parent / "m11l-tasks-copy"
    if folder.exists() or folder.is_symlink():
        raise ValueError("TEST_DIRECTORY_ALREADY_EXISTS")
    folder.mkdir(mode=0o700)
    raw = (json.dumps({
        "version": 3, "nextId": 2, "nextProjectId": 1,
        "projects": [], "tasks": [{
            "id":"t1", "title":"M11M_TEST_0", "done":False,
            "createdAtMs":1000, "updatedAtMs":1000,
            "priority":"none", "description":"", "dueDate":None,
            "projectId":None
        }]
    }, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
    target = folder / "todo-copy.json"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        dir_fd = os.open(folder, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        # An interrupted seed is deliberately left for manual inspection.
        raise
    return target


def main():
    ap = argparse.ArgumentParser(description="Create a new synthetic M11m test fixture")
    ap.add_argument("--private-parent", required=True, type=Path)
    args = ap.parse_args()
    try:
        path = seed(args.private_parent)
    except (OSError, ValueError) as exc:
        raise SystemExit("M11m seed denied: " + str(exc)) from exc
    print("Synthetic disposable test created:", path)


if __name__ == "__main__":
    main()
