#!/usr/bin/env python3
"""Owner-local explicit Company vector sidecar launch boundary.

Quickshell owns the child Process lifecycle. Never detached. No installation,
build, download, auto-connect, Company record access, or shell execution.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

SCHEMA = "post-apollo.company-vector-sidecar-launch.v1"
RELATIVE_EXECUTABLE = (".local", "libexec", "post-apollo", "company-vector-probe")
ACTIONS = ("probe", "offline", "online")


def trusted_executable(home: Path | None = None) -> Path | None:
    if os.getuid() == 0 or os.geteuid() != os.getuid():
        return None
    root = Path.home() if home is None else home
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        return None
    path = root
    for part in RELATIVE_EXECUTABLE:
        path = path / part
        try:
            info = path.lstat()
        except OSError:
            return None
        if info.st_uid != os.getuid() or (info.st_mode & 0o022):
            return None
        if part != RELATIVE_EXECUTABLE[-1]:
            if not stat.S_ISDIR(info.st_mode):
                return None
        elif not stat.S_ISREG(info.st_mode) or not (info.st_mode & 0o100):
            return None
    return path


def probe(home: Path | None = None) -> dict:
    available = trusted_executable(home) is not None
    return {
        "schema": SCHEMA,
        "status": "AVAILABLE" if available else "NOT_INSTALLED",
        "nativeQtVerified": False,  # Never infer desktop ABI from file presence.
        "runtimeLaunched": False,
    }


def main(argv: list[str] | None = None, home: Path | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0] not in ACTIONS:
        print(json.dumps({"schema": SCHEMA, "status": "INVALID_ACTION"}))
        return 2
    action = args[0]
    if action == "probe":
        print(json.dumps(probe(home), separators=(",", ":")))
        return 0
    executable = trusted_executable(home)
    if executable is None:
        print(json.dumps({"schema": SCHEMA, "status": "NOT_INSTALLED"}))
        return 69
    # The process is replaced, not detached. Quickshell's running=false
    # sends SIGTERM directly to the native Qt app. No background orphan.
    # 'online' is a second explicit UI-confirmed choice; it never reads
    # owner-local Company hubs and never auto-centers on private sites.
    options = ["--styled-online"] if action == "online" else []
    try:
        os.execv(str(executable), [str(executable), *options])
    except OSError:
        print(json.dumps({"schema": SCHEMA, "status": "LAUNCH_FAILED"}))
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
