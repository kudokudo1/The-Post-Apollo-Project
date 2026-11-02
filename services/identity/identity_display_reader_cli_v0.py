#!/usr/bin/env python3
"""Read-only, token-free Social Organizations viewer CLI, Linux CI pilot.

Exactly one fixed operation: --json. Read a verified, host-owned snapshot
from an existing private AF_UNIX socket. No token, login, logout, refresh,
person/company selection, browser opening, file mutation or host startup.

This is NOT a production Quickshell deployment or strong same-UID isolation.
The private host service and runtime directory are not automatically created.
The host must explicitly own ~/. no: XDG_RUNTIME_DIR under OS uid, not HOME.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import time

from private_context_ipc_v0 import (
    SOCKET_NAME, empty_display, read_private_display,
)

RUNTIME_CHILD = "post-apollo-identity-v0"


def _runtime_socket(env: dict[str, str]) -> Path | None:
    """Never fall back to /tmp, $HOME, CWD, or a caller-chosen socket."""
    raw = env.get("XDG_RUNTIME_DIR")
    if type(raw) is not str or not raw or len(raw) > 256:
        return None
    root = Path(raw)
    if (not root.is_absolute()
            or ".." in root.parts or root.as_posix() != os.path.normpath(raw)):
        return None
    try:
        info = root.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            return None
    except OSError:
        return None
    return root / RUNTIME_CHILD / SOCKET_NAME


def snapshot(env: dict[str, str] | None = None) -> dict[str, object]:
    runtime = _runtime_socket(os.environ if env is None else env)
    if runtime is None:
        return empty_display()
    return read_private_display(runtime, clock=lambda: int(time.time()))


def main(args: list[str] | None = None) -> int:
    args = sys.argv[1:] if args is None else args
    # Unknown commands must not do anything or disclose process diagnostics.
    if args != ["--json"]:
        return 2
    try:
        result = snapshot()
    except Exception:
        result = empty_display()
    # One JSON line only; never log tokens, paths, errors or IP addresses.
    sys.stdout.write(json.dumps(result, separators=(",", ":"),
                                ensure_ascii=True, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
