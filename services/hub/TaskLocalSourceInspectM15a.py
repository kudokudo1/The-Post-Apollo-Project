#!/usr/bin/env python3
"""TASKS M15a: one-shot explicit read-only inspection of saved local JSON.

This is not an encrypted draft host, recovery journal, writer, source-owner
authenticator, save acknowledgment, or automatic background watcher. The live
QML caller invokes it ONLY when the operator clicks CHECK LOCAL SOURCE.

Only bounded structural status/count metadata reaches stdout. Never emit task
text, paths, IDs, hashes, source bytes, credentials or Python tracebacks.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys

FILENAME = "apollo-hub-todo-v1.json"
MAX_BYTES = 1048576
MAX_TASKS = 200
MAX_PROJECTS = 30
STATUSES = frozenset({
    "SOURCE_STRUCTURALLY_READABLE", "SOURCE_MISSING",
    "SOURCE_PATH_REFUSED", "SOURCE_UNSAFE", "SOURCE_PERMISSION_REVIEW",
    "SOURCE_TOO_LARGE", "SOURCE_INVALID_JSON", "SOURCE_INVALID_STRUCTURE",
    "SOURCE_UNSUPPORTED_VERSION", "SOURCE_CHANGED", "SOURCE_UNAVAILABLE",
})
BASE = {
    "protocol": 1, "kind": "TASKS_LOCAL_SOURCE_CHECK_M15A",
    "readOnly": True, "writerAuthenticated": False,
    "savedAcknowledged": False, "sourceRevisionVerified": False,
    "encryptedDraftRecoveryEnabled": False,
    "writeAuthorized": False, "restoreAuthorized": False,
    "draftClearAuthorized": False, "keyReleaseAuthorized": False,
}


def report(status: str, present: bool = False,
           tasks: int | None = None, projects: int | None = None) -> dict:
    if status not in STATUSES:
        status = "SOURCE_UNAVAILABLE"
    if status != "SOURCE_STRUCTURALLY_READABLE":
        tasks = projects = None
    return {"status": status, "sourcePresent": bool(present),
            "taskCount": tasks, "projectCount": projects, **BASE}


def private_directory(directory: Path) -> bool:
    try:
        info = directory.lstat()
        return (not stat.S_ISLNK(info.st_mode)
                and stat.S_ISDIR(info.st_mode)
                and info.st_uid == os.geteuid()
                and info.st_nlink >= 1)
    except OSError:
        return False


def pairs_unique(pairs: list) -> dict:
    doc = {}
    for key, value in pairs:
        if key in doc:
            raise ValueError("DUPLICATE_JSON_KEY")
        doc[key] = value
    return doc


def reject_constant(_: str):
    raise ValueError("NONFINITE_JSON_VALUE")


def integer(v, lo, hi) -> bool:
    return type(v) is int and lo <= v <= hi


def structural_counts(data) -> tuple[int, int] | None:
    """Narrow structural check, NOT parity with TodoPolicy.validate()."""
    if type(data) is not dict:
        return None
    version = data.get("version")
    if type(version) is not int or version not in (1, 2, 3):
        return None
    if not integer(data.get("nextId"), 1, 1000000000):
        return None
    tasks = data.get("tasks")
    if type(tasks) is not list or len(tasks) > MAX_TASKS:
        return None
    projects = data.get("projects") if version == 3 else []
    if (type(projects) is not list or len(projects) > MAX_PROJECTS
            or version == 3 and not integer(
                data.get("nextProjectId"), 1, 1000000000)):
        return None
    ids = set()
    for task in tasks:
        if (type(task) is not dict or type(task.get("id")) is not str
                or type(task.get("title")) is not str
                or type(task.get("done")) is not bool
                or len(task["title"]) == 0 or len(task["title"]) > 160
                or task["id"] in ids):
            return None
        ids.add(task["id"])
    pids = set()
    if version == 3:
        for p in projects:
            if (type(p) is not dict or type(p.get("id")) is not str
                    or type(p.get("name")) is not str or not p["name"]
                    or p["id"] in pids):
                return None
            pids.add(p["id"])
    return len(tasks), len(projects)


def check(source: Path) -> dict:
    # The actual production QML supplies the existing singleton's path;
    # this CLI refusal is not a general OS authorization capability.
    if (not isinstance(source, Path) or not source.is_absolute()
            or source.name != FILENAME or len(str(source)) > 4096
            or os.path.normpath(str(source)) != str(source)
            or "\x00" in str(source)):
        return report("SOURCE_PATH_REFUSED")
    parent = source.parent
    if not private_directory(parent):
        return report("SOURCE_UNSAFE")
    try:
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY
                            | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return report("SOURCE_UNAVAILABLE")
    try:
        try:
            pre = os.stat(source.name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return report("SOURCE_MISSING")
        except OSError:
            return report("SOURCE_UNAVAILABLE")
        if (not stat.S_ISREG(pre.st_mode) or pre.st_uid != os.geteuid()
                or pre.st_nlink != 1):
            return report("SOURCE_UNSAFE")
        if stat.S_IMODE(pre.st_mode) & 0o077:
            # This status does not chmod or change permissions. Existing
            # user data is not opened when mode is too permissive.
            return report("SOURCE_PERMISSION_REVIEW", present=True)
        if not 0 < pre.st_size <= MAX_BYTES:
            return report("SOURCE_TOO_LARGE", present=True)
        try:
            fd = os.open(source.name, os.O_RDONLY
                         | getattr(os, "O_NOFOLLOW", 0)
                         | getattr(os, "O_NONBLOCK", 0),
                         dir_fd=directory)
        except OSError:
            return report("SOURCE_UNAVAILABLE")
        try:
            first = os.fstat(fd)
            if ((pre.st_dev, pre.st_ino) != (first.st_dev, first.st_ino)
                    or not stat.S_ISREG(first.st_mode)
                    or first.st_uid != os.geteuid()):
                return report("SOURCE_CHANGED", present=True)
            content = os.read(fd, MAX_BYTES + 1)
            second = os.fstat(fd)
        except OSError:
            return report("SOURCE_UNAVAILABLE")
        finally:
            os.close(fd)
        if len(content) > MAX_BYTES:
            return report("SOURCE_TOO_LARGE", present=True)
        try:
            final = os.stat(source.name, dir_fd=directory, follow_symlinks=False)
        except OSError:
            return report("SOURCE_CHANGED", present=True)
        stats = (lambda x: (x.st_dev, x.st_ino, x.st_size,
                            x.st_mtime_ns, x.st_ctime_ns))
        if stats(pre) != stats(first) or stats(first) != stats(second) \
                or stats(second) != stats(final):
            return report("SOURCE_CHANGED", present=True)
        try:
            data = json.loads(content.decode("utf-8"), object_pairs_hook=pairs_unique,
                              parse_constant=reject_constant)
        except (ValueError, UnicodeError, TypeError):
            return report("SOURCE_INVALID_JSON", present=True)
        if type(data) is dict and type(data.get("version")) is int \
                and data["version"] not in (1, 2, 3):
            return report("SOURCE_UNSUPPORTED_VERSION", present=True)
        counts = structural_counts(data)
        if counts is None:
            return report("SOURCE_INVALID_STRUCTURE", present=True)
        return report("SOURCE_STRUCTURALLY_READABLE", True, counts[0], counts[1])
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    try:
        answer = check(args.source)
    except Exception:
        # No traceback or file path on stdout/stderr. Fail closed.
        answer = report("SOURCE_UNAVAILABLE")
    sys.stdout.write(json.dumps(answer, separators=(",", ":"), sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
