"""Explicit host-owned Identity Center BEGIN command endpoint, experimental v0.

This is an ACTUAL AF_UNIX listener/dispatcher that invokes the existing
DesktopHostLifecycle.start()/begin_login() in a disposable, controlled process.
It does not create a second OAuth implementation, expose bearer tokens, or
install/run a persistent daemon. Constructing it makes NO socket or browser.

SECURITY / PRODUCTION HOLD:
  - Same-UID SO_PEERCRED and 0600 Unix socket are not host attestation.
  - A separately installed and independently verified host must provide
    verified_peer, active_seat and approved_intent callbacks.
  - All three callbacks are mandatory and fail closed; untrusted clients
    cannot set any approval fields in the command JSON.
  - This module does NOT itself implement C3e/C4b witness binding, C5 real
    human consent, enrollment, or a production identity-provider config.
  - CANCEL/RECOVER and UI clients are intentionally NOT wired or supported.
  - No host-owned method or private display socket has been repurposed.

The service is a bounded integration building block requiring independent
security-owner review and operator activation before any desktop use.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import stat
import struct
import threading
from collections.abc import Callable

from desktop_host_lifecycle_v0 import DesktopHostLifecycle

COMMAND_SCHEMA = "post-apollo.identity.command-intent.proposed-v0"
RECEIPT_SCHEMA = "post-apollo.identity.command-receipt.experimental-v0"
COMMAND_SOCKET = "identity-command-v0.sock"
_MAX_REQUEST = 1024
_MAX_RECEIPT = 256


@dataclass(frozen=True, slots=True)
class KernelPeer:
    """SO_PEERCRED supplied by kernel, never client JSON."""

    pid: int
    uid: int
    gid: int


def _peer(conn: socket.socket) -> KernelPeer:
    if not hasattr(socket, "SO_PEERCRED"):
        raise OSError("Linux peer credentials are required")
    data = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    if len(data) != 12:
        raise OSError("Peer credential length mismatch")
    pid, uid, gid = struct.unpack("3i", data)
    if pid <= 0 or uid < 0 or gid < 0:
        raise OSError("Invalid peer identity")
    return KernelPeer(pid, uid, gid)


def _private_directory(path: Path) -> None:
    if type(path) is not Path or not path.is_absolute():
        raise ValueError("Existing absolute runtime directory required")
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("Command directory must be owner-private 0700")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError("Duplicate command key")
        parsed[key] = value
    return parsed


def _valid_begin(raw: bytes) -> bool:
    if not 0 < len(raw) <= _MAX_REQUEST or not raw.endswith(b"\n"):
        return False
    if raw.count(b"\n") != 1:
        return False
    try:
        command = json.loads(raw[:-1].decode("utf-8", errors="strict"),
                             object_pairs_hook=_unique_pairs)
    except (UnicodeError, ValueError, TypeError):
        return False
    return (type(command) is dict
            and set(command) == {"schema", "action", "requestId"}
            and command["schema"] == COMMAND_SCHEMA
            and command["action"] == "BEGIN"
            and command["requestId"] is None)


def _receipt(state: str, request_id: str | None = None) -> bytes:
    # No issuer, redirect, authorization URL, subject, token, API error or
    # display membership leaves the host command boundary.
    if state not in ("REQUESTED", "UNAVAILABLE"):
        raise ValueError("Unknown command receipt state")
    if state != "REQUESTED":
        request_id = None
    payload = json.dumps(
        {"schema": RECEIPT_SCHEMA, "state": state, "requestId": request_id},
        ensure_ascii=True, allow_nan=False, separators=(",", ":"),
    ).encode("ascii") + b"\n"
    if len(payload) > _MAX_RECEIPT:
        raise ValueError("Command receipt too large")
    return payload


class _Server(socketserver.ThreadingUnixStreamServer):
    allow_reuse_address = False
    daemon_threads = True
    block_on_close = False


class IdentityCommandGateway:
    """Explicitly started, strictly gated command-to-existing-host bridge.

    The verified_peer callback must independently verify signed installed
    caller provenance/current PID/seat, not merely return uid == own uid.
    The active_seat callback must fail on lock/suspend/loss of host identity.
    The approved_intent callback must validate a fresh, human-initiated,
    one-use operation for THIS peer. A positive callback fixture in CI is not
    a production authorization implementation.

    Only BEGIN is supported. CANCEL and RECOVER return UNAVAILABLE; the
    existing host's logout() is never repurposed as request cancellation.
    """

    def __init__(
        self, *,
        runtime_directory: Path,
        host_factory: Callable[[], DesktopHostLifecycle],
        verified_peer: Callable[[KernelPeer], bool],
        active_seat: Callable[[], bool],
        approved_intent: Callable[[KernelPeer, str], bool],
    ) -> None:
        if (type(runtime_directory) is not Path
                or not runtime_directory.is_absolute()
                or not all(callable(fn) for fn in
                           (host_factory, verified_peer, active_seat,
                            approved_intent))):
            raise ValueError("Host-owned command admission dependencies required")
        self._directory = runtime_directory
        self._path = runtime_directory / COMMAND_SOCKET
        if len(os.fsencode(str(self._path))) > 100:
            raise ValueError("Unix command socket path is too long")
        self._factory = host_factory
        self._verify_peer = verified_peer
        self._active_seat = active_seat
        self._approve = approved_intent
        self._lock = threading.RLock()
        self._closing = threading.Event()
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None
        self._socket_inode: int | None = None
        self._host: DesktopHostLifecycle | None = None
        self._request_id: str | None = None
        self._started_once = False

    @property
    def socket_path(self) -> Path:
        """Host diagnostic only; a QML client must not discover this path."""
        return self._path

    def start(self) -> None:
        """Bind only on explicit trusted-host activation; no host login yet."""
        with self._lock:
            if self._started_once or self._closing.is_set():
                raise RuntimeError("Command gateway is single-use")
            self._started_once = True
            _private_directory(self._directory)
            if os.path.lexists(self._path):
                raise FileExistsError("Refusing existing command endpoint")
            server = _Server(str(self._path), self._Handler)
            server.owner = self
            self._server = server
            try:
                # Record the inode before chmod/checks so a failed start can
                # safely remove only the socket we just created.
                self._socket_inode = self._path.lstat().st_ino
                os.chmod(self._path, 0o600)
                info = self._path.lstat()
                if (not stat.S_ISSOCK(info.st_mode)
                        or info.st_uid != os.geteuid()
                        or stat.S_IMODE(info.st_mode) != 0o600):
                    raise ValueError("Command socket permissions denied")
                self._socket_inode = info.st_ino
                self._thread = threading.Thread(
                    target=server.serve_forever,
                    kwargs={"poll_interval": 0.05},
                    daemon=True,
                    name="identity-experimental-command-gateway",
                )
                self._thread.start()
            except Exception:
                self._server = None
                server.server_close()
                self._remove_owned_socket()
                self._closing.set()
                raise

    def _remove_owned_socket(self) -> None:
        try:
            if (self._socket_inode is not None
                    and self._path.lstat().st_ino == self._socket_inode):
                self._path.unlink()
        except FileNotFoundError:
            pass
        self._socket_inode = None

    def _admitted(self, peer: KernelPeer) -> bool:
        # This is an independent host-owned callback decision, not a client
        # JSON boolean or a property set by QML.
        if self._closing.is_set() or peer.uid != os.geteuid():
            return False
        try:
            return (self._active_seat() is True
                    and self._verify_peer(peer) is True
                    and self._approve(peer, "BEGIN") is True)
        except Exception:
            return False

    def _begin(self, peer: KernelPeer, raw: bytes) -> bytes:
        if not _valid_begin(raw):
            return _receipt("UNAVAILABLE")
        with self._lock:
            if self._host is not None or not self._admitted(peer):
                return _receipt("UNAVAILABLE")
            host: DesktopHostLifecycle | None = None
            try:
                host = self._factory()
                if not isinstance(host, DesktopHostLifecycle):
                    raise ValueError("Wrong host lifecycle owner")
                host.start()
                if host.begin_login() != {"status": "LOGIN_PENDING"}:
                    raise RuntimeError("Real host refused BEGIN")
                # Seat/host may be revoked while browser dispatch is pending.
                if self._closing.is_set() or self._active_seat() is not True:
                    raise RuntimeError("Lost trusted seat during BEGIN")
                request_id = secrets.token_urlsafe(32)
                self._host = host
                self._request_id = request_id
                return _receipt("REQUESTED", request_id)
            except Exception:
                if host is not None:
                    try:
                        host.close()
                    except Exception:
                        pass
                return _receipt("UNAVAILABLE")

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            conn = self.request
            try:
                conn.settimeout(1.5)
                peer = _peer(conn)
                raw = bytearray()
                while len(raw) <= _MAX_REQUEST and b"\n" not in raw:
                    data = conn.recv(_MAX_REQUEST + 2 - len(raw))
                    if not data:
                        break
                    raw.extend(data)
                response = self.server.owner._begin(peer, bytes(raw))
                conn.sendall(response)
            except (OSError, TimeoutError, ValueError):
                # No raw diagnostic/URL/secret is echoed to a client.
                return

    def close(self) -> None:
        """Deny new commands first, revoke owned login, then release sockets."""
        self._closing.set()
        with self._lock:
            host, server, thread = self._host, self._server, self._thread
            self._host = None
            self._request_id = None
            self._server = None
            self._thread = None
        # The host revokes token/pending callback before we release the gate.
        try:
            if host is not None:
                host.close()
        finally:
            if server is not None:
                if thread is not None and thread.is_alive():
                    server.shutdown()
                server.server_close()
            self._remove_owned_socket()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, kind, value, traceback):
        self.close()
