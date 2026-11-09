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
  - RECOVER is explicit and request-bound; UI clients remain unwired.
  - No host-owned method or private display socket has been repurposed.

The service is a bounded integration building block requiring independent
security-owner review and operator activation before any desktop use.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
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
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{16,96}$")


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
    if not isinstance(path, Path) or not path.is_absolute():
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


def _parse_command(raw: bytes) -> tuple[str, str | None] | None:
    """Exact one-frame command grammar; client cannot supply trust claims."""
    if not 0 < len(raw) <= _MAX_REQUEST or not raw.endswith(b"\n"):
        return None
    if raw.count(b"\n") != 1:
        return None
    try:
        command = json.loads(raw[:-1].decode("utf-8", errors="strict"),
                             object_pairs_hook=_unique_pairs)
    except (UnicodeError, ValueError, TypeError):
        return None
    if (type(command) is not dict
            or set(command) != {"schema", "action", "requestId"}
            or command["schema"] != COMMAND_SCHEMA):
        return None
    action, request_id = command["action"], command["requestId"]
    if action == "BEGIN" and request_id is None:
        return ("BEGIN", None)
    if (action in ("CANCEL", "STATUS", "RECOVER")
            and type(request_id) is str
            and _REQUEST_ID.fullmatch(request_id) is not None):
        return (action, request_id)
    return None


def _receipt(state: str, request_id: str | None = None) -> bytes:
    # A receipt is *only* an experimental phase report, NOT an authenticated
    # identity, a signature, an authorization grant or provider consent.
    # No issuer, redirect, URL, token, subject, API error or membership data.
    if state not in ("REQUESTED", "PENDING", "AUTHENTICATED",
                     "CANCELLED", "FAILED", "HOST_LOST", "UNAVAILABLE"):
        raise ValueError("Unknown command receipt state")
    if state == "UNAVAILABLE":
        request_id = None
    elif (type(request_id) is not str
          or _REQUEST_ID.fullmatch(request_id) is None):
        raise ValueError("Required host-issued request identifier missing")
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

    BEGIN, request-scoped CANCEL, read-only STATUS and fresh RECOVER are
    supported behind separate host-supplied admissions. RECOVER closes a
    failed/cancelled host and creates a new one-use lifecycle. General
    logout() is never a command cancellation.
    """

    def __init__(
        self, *,
        runtime_directory: Path,
        host_factory: Callable[[], DesktopHostLifecycle],
        verified_peer: Callable[[KernelPeer], bool],
        active_seat: Callable[[], bool],
        approved_intent: Callable[[KernelPeer, str], bool],
        secure_receipt_issuer: object | None = None,
    ) -> None:
        if (not isinstance(runtime_directory, Path)
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
        if secure_receipt_issuer is not None:
            # Load crypto dependency ONLY in signed mode; old disposable
            # unsigned host tests keep working without a trust store.
            from signed_command_receipt_v0 import ReceiptIssuer
            if not isinstance(secure_receipt_issuer, ReceiptIssuer):
                raise ValueError("Owner-provisioned Ed25519 receipt issuer required")
        self._secure_issuer = secure_receipt_issuer
        self._lock = threading.RLock()
        self._closing = threading.Event()
        self._server: _Server | None = None
        self._thread: threading.Thread | None = None
        self._socket_inode: int | None = None
        self._host: DesktopHostLifecycle | None = None
        self._request_id: str | None = None
        self._owner_peer: KernelPeer | None = None
        # Keep all prior IDs spent for the lifetime of the gateway.
        # Even an unexpected random collision may NEVER revive a stale ID.
        self._issued_ids: set[str] = set()
        self._begun_once = False
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

    def _admitted(self, peer: KernelPeer, action: str) -> bool:
        # Kernel SO_PEERCRED and separately approved, host-owned callbacks
        # are required on *every* operation. A request ID alone is NEVER a
        # bearer capability or evidence of matching process provenance.
        if self._closing.is_set() or peer.uid != os.geteuid():
            return False
        try:
            seat_ok = self._active_seat() is True
        except Exception:
            seat_ok = False
        if not seat_ok:
            # Once an active host observes seat loss, its pending code or
            # verified local credential is revoked permanently. A future
            # true seat probe must NOT resurrect the previous login.
            if self._host is not None:
                try:
                    self._host.session_event("session-end")
                except Exception:
                    return False
            return False
        try:
            return (self._verify_peer(peer) is True
                    and self._approve(peer, action) is True)
        except Exception:
            return False

    def _new_attempt(self, peer: KernelPeer, previous_id: str | None) -> bytes:
        """Host-owned fresh login state, under the gateway lock.

        The previous attempt, if any, was already closed and invalidated.
        Failure cannot silently create another BEGIN or reuse old state.
        """
        host: DesktopHostLifecycle | None = None
        try:
            host = self._factory()
            if not isinstance(host, DesktopHostLifecycle):
                raise ValueError("Wrong host lifecycle owner")
            host.start()
            if host.begin_login() != {"status": "LOGIN_PENDING"}:
                raise RuntimeError("Host refused new login attempt")
            # Recheck seat/caller after browser side effects. One-shot C5
            # operator approval is intentionally not consumed a second time.
            if (self._closing.is_set()
                    or self._active_seat() is not True
                    or self._verify_peer(peer) is not True):
                raise RuntimeError("Seat or caller lost during new login")
            new_id = secrets.token_urlsafe(32)
            if (new_id == previous_id or new_id in self._issued_ids
                    or _REQUEST_ID.fullmatch(new_id) is None):
                raise RuntimeError("Fresh host request ID unavailable")
            self._issued_ids.add(new_id)
            self._host = host
            self._request_id = new_id
            self._owner_peer = peer
            return _receipt("REQUESTED", new_id)
        except Exception:
            if host is not None:
                try:
                    host.close()
                except Exception:
                    pass
            return _receipt("UNAVAILABLE")

    def _begin(self, peer: KernelPeer) -> bytes:
        with self._lock:
            if (self._host is not None or self._begun_once
                    or not self._admitted(peer, "BEGIN")):
                return _receipt("UNAVAILABLE")
            # Deny second BEGIN even if host creation/browser launch fails.
            self._begun_once = True
            return self._new_attempt(peer, None)

    def _recover(self, peer: KernelPeer, prior_id: str, phase: str) -> bytes:
        """Consume terminal request, revoke old host and start NEW login.

        Never replace pending or authenticated attempts. Host/seat loss is
        not recoverable on this socket; re-enrollment must be independent.
        """
        if phase not in ("CANCELLED", "FAILED"):
            return _receipt("UNAVAILABLE")
        old_host = self._host
        if old_host is None:
            return _receipt("UNAVAILABLE")
        # Invalidate the old receipt before cleanup and new browser action.
        self._host = None
        self._request_id = None
        self._owner_peer = None
        try:
            old_host.close()
        except Exception:
            # Unverified cleanup can never become a new login.
            return _receipt("UNAVAILABLE")
        if self._closing.is_set():
            return _receipt("UNAVAILABLE")
        try:
            if (self._active_seat() is not True
                    or self._verify_peer(peer) is not True):
                return _receipt("UNAVAILABLE")
        except Exception:
            return _receipt("UNAVAILABLE")
        return self._new_attempt(peer, prior_id)

    def _dispatch(self, peer: KernelPeer, raw: bytes) -> bytes:
        parsed = _parse_command(raw)
        if parsed is None:
            return _receipt("UNAVAILABLE")
        return self._dispatch_action(peer, *parsed)

    def _dispatch_action(self, peer: KernelPeer, action: str,
                         request_id: str | None) -> bytes:
        # Signed mode calls this only after strict challenge/frame parsing;
        # old test mode retains its already-reviewed exact legacy parser.
        if action == "BEGIN":
            return self._begin(peer)
        with self._lock:
            if (self._host is None or self._request_id is None
                    or self._owner_peer != peer
                    or request_id is None
                    or not secrets.compare_digest(request_id, self._request_id)
                    or not self._admitted(peer, action)):
                return _receipt("UNAVAILABLE")
            # The live host, NOT a client flag or private SNAPSHOT socket,
            # owns callback completion, session validity and terminal phase.
            phase = self._host.command_phase()
            if action == "STATUS":
                if phase not in ("PENDING", "AUTHENTICATED", "CANCELLED",
                                 "FAILED", "HOST_LOST"):
                    return _receipt("UNAVAILABLE")
                return _receipt(phase, request_id)
            if action == "CANCEL" and phase == "PENDING":
                result = self._host.cancel_pending_login()
                if result == {"status": "CANCELLED"}:
                    return _receipt("CANCELLED", request_id)
            if action == "RECOVER":
                return self._recover(peer, request_id, phase)
            return _receipt("UNAVAILABLE")

    def _invalidate_after_signing_failure(self) -> None:
        """A missing/untrusted receipt must not leave login running orphaned.

        Called under the command lock. Permanent closed admission until
        operator/installed-host owner explicitly starts a NEW gateway.
        """
        self._closing.set()
        old_host = self._host
        self._host = None
        self._request_id = None
        self._owner_peer = None
        if old_host is not None:
            try:
                old_host.close()
            except Exception:
                pass

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:
            conn = self.request
            try:
                conn.settimeout(1.5)
                peer = _peer(conn)
                raw = bytearray()
                while len(raw) <= _MAX_REQUEST and b"\n" not in raw:
                    try:
                        data = conn.recv(_MAX_REQUEST + 2 - len(raw))
                    except socket.timeout:
                        # An incomplete packet is a bounded denial, not a
                        # half-open login request or a raw exception.
                        break
                    if not data:
                        break
                    raw.extend(data)
                owner = self.server.owner
                if owner._secure_issuer is None:
                    # Legacy mode exists only for isolated compatibility CI;
                    # signed clients reject every legacy/unsigned response.
                    conn.sendall(owner._dispatch(peer, bytes(raw)))
                else:
                    # Production-mode CANDIDATE: signed request envelope only,
                    # no legacy fallback, no client-supplied trust claims.
                    from signed_command_receipt_v0 import parse_request
                    parsed = parse_request(bytes(raw))
                    if parsed is None:
                        conn.sendall(_receipt("UNAVAILABLE"))
                        return
                    action, request_id, nonce = parsed
                    with owner._lock:
                        raw_receipt = owner._dispatch_action(peer, action, request_id)
                        try:
                            signed = owner._secure_issuer.seal(
                                action, request_id, nonce, raw_receipt)
                        except Exception:
                            owner._invalidate_after_signing_failure()
                            return
                    conn.sendall(signed)
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
            self._owner_peer = None
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
