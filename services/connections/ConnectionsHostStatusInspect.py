#!/usr/bin/env python3
"""C2i non-activating local Connections host-status inspection.

Read-only and deliberately UNTRUSTED. A same-UID process can impersonate a
user-session socket even after SO_PEERCRED validation. Only fixed, bounded
display observations are returned. Never unlock, read or write credentials,
approve, revoke, start a daemon, or call NASA.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import struct
import sys
import time
from typing import Callable

RUNTIME_DIRNAME = "post-apollo"
SOCKET_NAME = "connections-status-v1.sock"
REQUEST = b"STATUS V1\n"
SCHEMA = "post-apollo.connections.status.v1"
MAX_FRAME = 768
MAX_DURATION = 1.5
STATES = frozenset({
    "IDLE", "PENDING", "APPROVED", "DENIED", "CANCELLED",
    "EXPIRED", "COMPLETED", "FAILED",
})


def result(status: str, state: str = "") -> dict[str, object]:
    # Only fixed values. No account identity, path, request ID or secret.
    return {
        "status": status,
        "provider": "nasa-firms",
        "state": state,
        "hostAuthenticated": False,
        "credentialPresent": False,
        "grantActive": False,
        "canApprove": False,
    }


def _owned_private_directory(folder: Path) -> bool:
    try:
        info = folder.lstat()
        return (stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                and (info.st_mode & 0o077) == 0)
    except OSError:
        return False


def _socket_metadata(path: Path) -> bool:
    try:
        info = path.lstat()
        return (stat.S_ISSOCK(info.st_mode) and info.st_uid == os.geteuid()
                and (info.st_mode & 0o077) == 0)
    except OSError:
        return False


def _peer_uid(sock: socket.socket) -> bool:
    if not hasattr(socket, "SO_PEERCRED"):
        return False
    try:
        raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        _pid, uid, _gid = struct.unpack("3i", raw)
        return uid == os.geteuid()
    except (OSError, ValueError, struct.error):
        return False


def _normalize(raw: bytes) -> dict[str, object]:
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return result("RESPONSE_INVALID")
    if (type(decoded) is not dict
            or set(decoded) != {"schema", "provider", "state", "readonly"}
            or decoded["schema"] != SCHEMA
            or decoded["provider"] != "nasa-firms"
            or type(decoded["state"]) is not str
            or decoded["state"] not in STATES
            or decoded["readonly"] is not True):
        return result("RESPONSE_INVALID")
    return result("OBSERVED_UNVERIFIED", decoded["state"])


def probe(
    env: dict[str, str] | None = None,
    socket_factory: Callable[..., socket.socket] = socket.socket,
) -> dict[str, object]:
    supplied = os.environ if env is None else env
    raw_runtime = supplied.get("XDG_RUNTIME_DIR", "")
    if not raw_runtime or not os.path.isabs(raw_runtime):
        return result("RUNTIME_UNAVAILABLE")
    base = Path(raw_runtime)
    if not _owned_private_directory(base):
        return result("RUNTIME_UNSAFE")
    private = base / RUNTIME_DIRNAME
    if not private.exists() and not private.is_symlink():
        return result("HOST_NOT_FOUND")
    if not _owned_private_directory(private):
        return result("RUNTIME_UNSAFE")
    path = private / SOCKET_NAME
    if not path.exists() and not path.is_symlink():
        return result("HOST_NOT_FOUND")
    if not _socket_metadata(path):
        return result("RUNTIME_UNSAFE")
    if len(os.fsencode(path)) > 100:
        return result("RUNTIME_UNSAFE")

    sock: socket.socket | None = None
    try:
        sock = socket_factory(socket.AF_UNIX, socket.SOCK_STREAM)
        deadline = time.monotonic() + MAX_DURATION
        sock.settimeout(MAX_DURATION)
        sock.connect(str(path))
        if not _peer_uid(sock):
            return result("PEER_UNVERIFIED")
        sock.sendall(REQUEST)
        frame = bytearray()
        while b"\n" not in frame and len(frame) <= MAX_FRAME:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return result("HOST_UNAVAILABLE")
            sock.settimeout(remaining)
            chunk = sock.recv(MAX_FRAME + 1 - len(frame))
            if not chunk:
                return result("RESPONSE_INVALID")
            frame.extend(chunk)
        if (len(frame) > MAX_FRAME or not frame.endswith(b"\n")
                or frame.count(b"\n") != 1):
            return result("RESPONSE_INVALID")
        return _normalize(bytes(frame[:-1]))
    except (OSError, TimeoutError, ValueError):
        return result("HOST_UNAVAILABLE")
    finally:
        if sock is not None:
            sock.close()


def main() -> int:
    if len(sys.argv) != 1:
        print(json.dumps(result("RESPONSE_INVALID"), separators=(",", ":")))
        return 2
    print(json.dumps(probe(), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
