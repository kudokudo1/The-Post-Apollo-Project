"""Linux-only, CI-prototype, credential-free Identity Center display IPC.

An explicitly started, read-only Unix-domain socket transports a *validated*
DesktopContextProjection snapshot from a separately owned host process to a
local viewer. No QML wiring, no login commands, no bearer/session/PKCE fields,
no user-provided tenant selector and no service auto-start.

The caller MUST supply an already-created, private 0700 runtime directory. The
server refuses existing socket names (no takeover), binds 0600, and verifies
Linux SO_PEERCRED. Only the host may own snapshot_provider. A same-UID hostile
process can still read the local display; this is NOT sandboxing, production
authentication, access control for business records, or a deployable service.
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

from desktop_context_projection_v0 import _context

DISPLAY_SCHEMA = "post-apollo.identity.desktop-context-display.v0"
SOCKET_NAME = "identity-display-v0.sock"
_REQUEST = b"SNAPSHOT\n"
_MAX_WIRE = 65536
_ALLOWED_STATUS = {
    "READY", "NO_MEMBERSHIPS", "NOT_CONNECTED", "SIGNED_OUT", "UNAVAILABLE",
}


def empty_display(status: str = "UNAVAILABLE") -> dict[str, object]:
    """Never return stale organization data on a failed read."""
    if status not in _ALLOWED_STATUS or status == "READY":
        status = "UNAVAILABLE"
    return {
        "schema": DISPLAY_SCHEMA, "status": status,
        "organizations": [], "portfolios": [], "canSwitchOrganization": False,
    }


def _now(clock: Callable[[], int]) -> int:
    current = clock()
    if type(current) is not int or current < 0:
        raise ValueError("Trusted display clock unavailable")
    return current


def _clean(display: object, now: int) -> dict[str, object]:
    """Apply a strict allowlist on both sides of the socket boundary."""
    if (type(display) is not dict
            or set(display) != {
                "schema", "status", "organizations",
                "portfolios", "canSwitchOrganization",
            }
            or display["schema"] != DISPLAY_SCHEMA
            or type(display["status"]) is not str
            or display["status"] not in _ALLOWED_STATUS
            or display["canSwitchOrganization"] is not False):
        raise ValueError("Invalid UI-only display snapshot")
    status = display["status"]
    if status in ("READY", "NO_MEMBERSHIPS"):
        # Reuse the existing API scope/tenant validation; a portfolio may not
        # introduce an organization absent from the verified membership list.
        envelope = {
            "schema": "post-apollo.identity.context-summary.v0", "status": "OK",
            "organizations": display["organizations"],
            "portfolios": display["portfolios"],
        }
        raw = json.dumps(envelope, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
        output = _context(raw, now=now)
        if bool(output["organizations"]) != (status == "READY"):
            raise ValueError("Inconsistent membership state")
        return {
            "schema": DISPLAY_SCHEMA, "status": status,
            "organizations": output["organizations"],
            "portfolios": output["portfolios"],
            "canSwitchOrganization": False,
        }
    if display["organizations"] != [] or display["portfolios"] != []:
        raise ValueError("A non-ready display must be empty")
    return empty_display(status)


def _private_directory(path: Path) -> Path:
    if type(path) is not Path or not path.is_absolute():
        raise ValueError("A host-owned absolute runtime directory is required")
    info = path.lstat()  # never resolve a symlink into another user's directory
    if (not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077):
        raise ValueError("Runtime directory must be owned by host and mode 0700")
    return path


def _peer_uid(sock: socket.socket) -> int:
    if not hasattr(socket, "SO_PEERCRED"):
        raise OSError("Linux SO_PEERCRED required for this pilot")
    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    _, uid, _ = struct.unpack("3i", raw)
    return uid


class _SocketServer(socketserver.UnixStreamServer):
    allow_reuse_address = False
    request_queue_size = 4


class PrivateContextSocket:
    """Host-owned, read-only IPC. Explicit start/close; no auto-launch."""

    def __init__(self, *, runtime_directory: Path,
                 snapshot_provider: Callable[[], dict[str, object]],
                 clock: Callable[[], int]) -> None:
        if not callable(snapshot_provider) or not callable(clock):
            raise ValueError("A trusted host-owned projection and clock required")
        self._directory = _private_directory(runtime_directory)
        self._path = self._directory / SOCKET_NAME
        if len(os.fsencode(self._path)) > 98:
            raise ValueError("Unix socket path too long")
        self._provider = snapshot_provider
        self._clock = clock
        self._server: _SocketServer | None = None
        self._worker: threading.Thread | None = None
        self._inode: int | None = None
        self._closed = False

    @property
    def socket_path(self) -> Path:
        if self._server is None:
            raise RuntimeError("IPC is not started")
        return self._path

    def start(self) -> None:
        if self._closed or self._server is not None:
            raise RuntimeError("IPC instance already started or closed")
        _private_directory(self._directory)
        if os.path.lexists(self._path):
            raise FileExistsError("Refusing to replace existing IPC path")
        owner = self

        class _Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                conn = self.request
                conn.settimeout(1.5)
                if _peer_uid(conn) != os.geteuid():
                    return
                try:
                    request = conn.recv(32)
                    if request != _REQUEST:
                        payload = empty_display()
                    else:
                        try:
                            payload = _clean(owner._provider(), _now(owner._clock))
                        except Exception:
                            payload = empty_display()
                    data = json.dumps(payload, separators=(",", ":"),
                                      allow_nan=False).encode("utf-8")
                    if len(data) > _MAX_WIRE:
                        data = json.dumps(empty_display()).encode("utf-8")
                    conn.sendall(data + b"\n")
                except (OSError, TimeoutError, ValueError):
                    return

        # The server creates an actual filesystem socket *only on start()*.
        server = _SocketServer(str(self._path), _Handler)
        self._server = server
        try:
            os.chmod(self._path, 0o600)
            info = self._path.lstat()
            if (not stat.S_ISSOCK(info.st_mode)
                    or info.st_uid != os.geteuid()
                    or info.st_mode & 0o077):
                raise ValueError("Refusing insecure IPC socket permissions")
            self._inode = info.st_ino
            worker = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                name="identity-ci-private-display",
                daemon=True,
            )
            self._worker = worker
            worker.start()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        self._closed = True
        server, worker = self._server, self._worker
        self._server = None
        self._worker = None
        if server is not None:
            server.shutdown() if worker is not None and worker.is_alive() else None
            server.server_close()
        # Never unlink a path changed by another process.
        try:
            if self._inode is not None and self._path.lstat().st_ino == self._inode:
                self._path.unlink()
        except FileNotFoundError:
            pass
        self._inode = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, kind, value, traceback):
        self.close()


def read_private_display(socket_path: Path, *,
                         clock: Callable[[], int]) -> dict[str, object]:
    """View-only client. Never passes a person, tenant, command or token.

    A private path and Linux peer credentials are checked, but a same-UID
    malicious host is not stopped by this experiment. Do not feed this path
    from QML, a web page or another untrusted request.
    """
    try:
        if (type(socket_path) is not Path
                or socket_path.name != SOCKET_NAME
                or not socket_path.is_absolute()):
            return empty_display()
        _private_directory(socket_path.parent)
        info = socket_path.lstat()
        if (not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != os.geteuid()
                or info.st_mode & 0o077):
            return empty_display()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(2.0)
            conn.connect(str(socket_path))
            if _peer_uid(conn) != os.geteuid():
                return empty_display()
            conn.sendall(_REQUEST)
            reply = bytearray()
            while len(reply) <= _MAX_WIRE:
                chunk = conn.recv(min(4096, _MAX_WIRE + 1 - len(reply)))
                if not chunk:
                    break
                reply.extend(chunk)
                if b"\n" in chunk:
                    break
        if len(reply) > _MAX_WIRE or not reply.endswith(b"\n"):
            return empty_display()
        result = json.loads(bytes(reply[:-1]).decode("utf-8"))
        return _clean(result, _now(clock))
    except Exception:
        return empty_display()
