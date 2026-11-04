#!/usr/bin/env python3
"""C2j explicitly hosted, read-only Connections status server.

Host-controlled Python API; NO auto-launch, credentials, permission grants,
provider requests, or callable user input. The fixed local socket is useful
for inspection, but same-UID peer checks DO NOT authenticate the server to
Post-Apollo. The C2i reader must continue labeling all replies UNVERIFIED.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import socketserver
import stat
import struct
import threading
from collections.abc import Callable

SCHEMA = "post-apollo.connections.status.v1"
NAME = "connections-status-v1.sock"
SUBDIR = "post-apollo"
QUERY = b"STATUS V1\n"
STATES = frozenset({
    "IDLE", "PENDING", "APPROVED", "DENIED", "CANCELLED",
    "EXPIRED", "COMPLETED", "FAILED",
})
MAX_REQUEST = 32
MAX_WIRE = 768


def _private(path: Path) -> bool:
    try:
        info = path.lstat()
        return (stat.S_ISDIR(info.st_mode)
                and info.st_uid == os.geteuid()
                and info.st_mode & 0o077 == 0)
    except OSError:
        return False


def _peer_is_same_uid(conn: socket.socket) -> bool:
    # Same-UID is a local safety check, NOT true application identity.
    if not hasattr(socket, "SO_PEERCRED"):
        return False
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        _, uid, _ = struct.unpack("3i", raw)
        return uid == os.geteuid()
    except (OSError, ValueError, struct.error):
        return False


def _bounded_display(state: object) -> bytes:
    if type(state) is not str or state not in STATES:
        state = "IDLE"
    payload = {
        "schema": SCHEMA, "provider": "nasa-firms",
        "state": state, "readonly": True,
    }
    data = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
    if len(data) > MAX_WIRE:
        raise ValueError("Host status exceeds frame limit")
    return data + b"\n"


class _Server(socketserver.UnixStreamServer):
    allow_reuse_address = False
    request_queue_size = 4


class ConnectionsHostStatusServer:
    """Host-created status endpoint. Only the host supplies the state getter.

    The runtime dir is supplied by the caller, not read from a client request.
    One instance is single-use and will not replace any preexisting socket.
    Socket path is created only by explicit start() and deleted only if its
    inode still matches this instance's original socket.
    """

    def __init__(self, *, runtime_directory: Path,
                 status_provider: Callable[[], str]) -> None:
        if not isinstance(runtime_directory, Path) or not runtime_directory.is_absolute():
            raise ValueError("Absolute runtime_directory required")
        if not callable(status_provider):
            raise ValueError("Host status provider required")
        if not _private(runtime_directory):
            raise ValueError("Host runtime directory must be owned and private")
        self._runtime = runtime_directory
        self._directory = runtime_directory / SUBDIR
        self._path = self._directory / NAME
        if len(os.fsencode(self._path)) > 100:
            raise ValueError("Unix status path too long")
        self._provider = status_provider
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None
        self._socket_inode: int | None = None
        self._created_directory = False
        self._closed = False

    @property
    def socket_path(self) -> Path:
        if self._server is None:
            raise RuntimeError("Host status server not running")
        return self._path

    def start(self) -> None:
        if self._closed or self._server is not None:
            raise RuntimeError("Host status server already used")
        if not _private(self._runtime):
            raise ValueError("Host runtime directory changed")
        if not self._directory.exists() and not self._directory.is_symlink():
            self._directory.mkdir(mode=0o700)
            self._created_directory = True
        if not _private(self._directory):
            raise ValueError("Private Post-Apollo runtime directory required")
        if os.path.lexists(self._path):
            raise FileExistsError("Refusing to replace an existing status socket")
        owner = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                conn: socket.socket = self.request
                try:
                    conn.settimeout(1.0)
                    if not _peer_is_same_uid(conn):
                        return
                    raw = conn.recv(MAX_REQUEST + 1)
                    if raw != QUERY:
                        return
                    try:
                        display = _bounded_display(owner._provider())
                    except Exception:
                        display = _bounded_display("IDLE")
                    conn.sendall(display)
                except (OSError, TimeoutError):
                    return

        try:
            server = _Server(str(self._path), Handler)
            self._server = server
            os.chmod(self._path, 0o600)
            info = self._path.lstat()
            if (not stat.S_ISSOCK(info.st_mode)
                    or info.st_uid != os.geteuid()
                    or info.st_mode & 0o077):
                raise ValueError("Unsafe host status socket")
            self._socket_inode = info.st_ino
            self._thread = threading.Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.05},
                name="connections-status-readonly", daemon=True)
            self._thread.start()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        try:
            info = self._path.lstat()
            if (stat.S_ISSOCK(info.st_mode) and self._socket_inode is not None
                    and info.st_uid == os.geteuid()
                    and info.st_ino == self._socket_inode):
                self._path.unlink()
        except FileNotFoundError:
            pass
        if self._created_directory:
            try:
                # Only an empty host-created directory is removed.
                if _private(self._directory):
                    self._directory.rmdir()
            except OSError:
                pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.close()


if __name__ == "__main__":
    # Never start a server merely because a human runs this file.
    raise SystemExit("C2J_REFUSED_AUTOSTART_NO_HOST_OWNER")
