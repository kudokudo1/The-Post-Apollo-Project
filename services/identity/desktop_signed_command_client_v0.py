"""Out-of-QML Identity Center native command client, experimental v0.

This is a real AF_UNIX client for the signed gateway mode: it sends commands,
checks an independently supplied installed-host identity guard and desktop
seat, verifies pinned Ed25519 receipts with fresh client challenges, and
tracks one host-issued request. It never handles OAuth tokens or IdP URLs.

PRODUCTION HOLD: server_guard and active_seat are mandatory owner-provided
callbacks, but their *production* C3e/C4b/logind implementations and C5
human-intent gate are NOT supplied by this module. Test callbacks are not
authorization. Do not activate UI buttons using this client yet.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import secrets
import socket
import stat
from collections.abc import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from desktop_command_gateway_v0 import KernelPeer, _peer
from signed_command_receipt_v0 import (
    ReceiptRejected, build_request, verify_receipt,
)


@dataclass(frozen=True, slots=True)
class HostCommandObservation:
    """Only a signed, local host observation, never an identity grant."""

    phase: str
    request_id: str | None
    instance: str
    sequence: int


class SignedIdentityCommandClient:
    """No trust-on-first-use: public key and real host identity MUST be pinned.

    Client faults permanently on missing/invalid signatures, host process or
    active seat changes, stale/replayed sequence, or unexpected host instance.
    It does NOT provide a QML bridge, a login authorization flag or credentials.
    """

    def __init__(self, *, socket_path: Path,
                 pinned_host_public_key: Ed25519PublicKey,
                 trusted_server_peer: Callable[[KernelPeer], bool],
                 active_seat: Callable[[], bool],
                 enrolled_origin_consistent: Callable[[KernelPeer], bool] | None = None
                 ) -> None:
        if (not isinstance(socket_path, Path) or not socket_path.is_absolute()
                or not isinstance(pinned_host_public_key, Ed25519PublicKey)
                or not callable(trusted_server_peer) or not callable(active_seat)
                or (enrolled_origin_consistent is not None
                    and not callable(enrolled_origin_consistent))):
            raise ValueError("Pinned host key, absolute path and owner trust guards required")
        if len(os.fsencode(str(socket_path))) > 100:
            raise ValueError("Unix command socket path too long")
        self._path = socket_path
        self._key = pinned_host_public_key
        self._verify_server = trusted_server_peer
        self._active_seat = active_seat
        # Optional ADDITIONAL independently enrolled process corroboration.
        # Never replaces trusted_server_peer, seat, or pinned signature key.
        self._enrolled_origin = enrolled_origin_consistent
        self._instance: str | None = None
        self._sequence = 0
        self._request_id: str | None = None
        self._phase: str | None = None
        self._nonces: set[str] = set()
        self._begin_consumed = False
        self._faulted = False

    @property
    def faulted(self) -> bool:
        return self._faulted

    def _fault(self) -> None:
        self._faulted = True
        self._request_id = None
        self._phase = None
        self._instance = None

    def _socket_safety(self) -> None:
        # Local metadata is necessary but not enough. The **connected** peer
        # must pass a separate independently approved process-identity guard.
        directory = self._path.parent.lstat()
        info = self._path.lstat()
        if (not stat.S_ISDIR(directory.st_mode)
                or directory.st_uid != os.geteuid()
                or stat.S_IMODE(directory.st_mode) != 0o700
                or not stat.S_ISSOCK(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise ReceiptRejected("Unsafe native command socket")

    def _trusted(self, peer: KernelPeer) -> bool:
        try:
            return (peer.uid == os.geteuid()
                    and self._active_seat() is True
                    and self._verify_server(peer) is True
                    and (self._enrolled_origin is None
                         or self._enrolled_origin(peer) is True))
        except Exception:
            return False

    def _transact(self, action: str) -> HostCommandObservation:
        if self._faulted:
            raise ReceiptRejected("Native command client is faulted")
        request_id = None if action == "BEGIN" else self._request_id
        if action == "BEGIN":
            if self._begin_consumed or self._request_id is not None:
                raise ReceiptRejected("BEGIN already consumed")
            self._begin_consumed = True
        elif request_id is None:
            raise ReceiptRejected("No host-issued request to operate on")
        if action == "RECOVER" and self._phase not in ("CANCELLED", "FAILED"):
            raise ReceiptRejected("No terminal request eligible for recovery")
        if action == "CANCEL" and self._phase not in ("REQUESTED", "PENDING"):
            raise ReceiptRejected("Not a pending login")
        nonce = secrets.token_urlsafe(32)
        if nonce in self._nonces:
            self._fault()
            raise ReceiptRejected("Repeated native command challenge")
        self._nonces.add(nonce)
        wire = build_request(action, request_id, nonce)
        try:
            self._socket_safety()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                conn.settimeout(2.0)
                conn.connect(str(self._path))
                peer = _peer(conn)
                if not self._trusted(peer):
                    raise ReceiptRejected("Untrusted installed native host or desktop seat")
                conn.sendall(wire)
                raw = bytearray()
                while len(raw) <= 1024 and b"\n" not in raw:
                    part = conn.recv(1025 - len(raw))
                    if not part:
                        break
                    raw.extend(part)
                body = verify_receipt(bytes(raw), pinned_key=self._key,
                                      action=action, command_request_id=request_id,
                                      client_nonce=nonce)
                if not self._trusted(peer):
                    raise ReceiptRejected("Lost trusted host or desktop seat")
            if self._instance is None:
                self._instance = body["hostInstance"]
            elif self._instance != body["hostInstance"]:
                raise ReceiptRejected("Host instance changed during command session")
            if body["sequence"] <= self._sequence:
                raise ReceiptRejected("Replayed or reordered host receipt")
            self._sequence = body["sequence"]
            self._phase = body["state"]
            if self._phase == "UNAVAILABLE":
                # Unavailable is not permission. Keep the current host-issued
                # request for another explicit status check if still trusted.
                return HostCommandObservation(
                    phase="UNAVAILABLE", request_id=None,
                    instance=self._instance, sequence=self._sequence)
            self._request_id = body["requestId"]
            if self._phase == "HOST_LOST":
                self._fault()
                raise ReceiptRejected("Native host revoked; new enrollment required")
            return HostCommandObservation(
                phase=self._phase, request_id=self._request_id,
                instance=self._instance, sequence=self._sequence)
        except (OSError, ValueError, TimeoutError) as e:
            self._fault()
            raise ReceiptRejected("Authenticated command/receipt failed closed") from e

    def begin(self) -> HostCommandObservation:
        return self._transact("BEGIN")

    def status(self) -> HostCommandObservation:
        return self._transact("STATUS")

    def cancel(self) -> HostCommandObservation:
        return self._transact("CANCEL")

    def recover(self) -> HostCommandObservation:
        return self._transact("RECOVER")
