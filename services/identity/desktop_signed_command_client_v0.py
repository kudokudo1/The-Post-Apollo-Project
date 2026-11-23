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
from hashlib import sha256
import os
from pathlib import Path
import secrets
import socket
import stat
import time
from collections.abc import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from native_attempt_fingerprint_v0 import AttemptedWireFingerprint
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
        # Local process observation only. A fresh client cannot prove that
        # an earlier process did not dispatch a command before crashing.
        self._last_wire_outcome = "UNOBSERVED"
        # Kept through post-send faults and subsequent rejected local calls.
        # Never persisted or accepted as independent issuer history.
        self._last_attempted_wire: AttemptedWireFingerprint | None = None

    @property
    def last_wire_outcome(self) -> str:
        """UNOBSERVED, NO_SEND_ATTEMPT, UNKNOWN_HOLD, or SIGNED_FRAME_SEEN.

        Not durable and NEVER authority, cancellation proof, nor retry
        permission. A signed frame can still report an uncertain host effect.
        """
        return self._last_wire_outcome

    @property
    def last_attempted_wire(self) -> AttemptedWireFingerprint | None:
        """Most recent attempted sendall, not necessarily the current call.

        This does NOT show whether bytes arrived, whether a command executed,
        or whether any externally protected receipt/consent exists. New
        client processes start with None; NO_SEND_ATTEMPT does not clear the
        last attempted command fingerprint.
        """
        return self._last_attempted_wire

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
            # Preserve the outcome of the last actual transport attempt,
            # especially UNKNOWN_HOLD. A denied retry is NOT reconciliation.
            raise ReceiptRejected("Native command client is faulted")
        # Each non-faulted call begins with zero attempted wire bytes, even if
        # local action/phase/nonce validation rejects it before socket setup.
        # This is per-client diagnostic telemetry, never a retry authority.
        self._last_wire_outcome = "NO_SEND_ATTEMPT"
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
        # One total budget for connect, send, and every response fragment.
        # Socket idle timeouts alone allow a slow peer to drip bytes forever.
        deadline = time.monotonic() + 2.0

        def remaining() -> float:
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError("Native command total deadline expired")
            return left

        try:
            self._socket_safety()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                conn.settimeout(remaining())
                conn.connect(str(self._path))
                peer = _peer(conn)
                if not self._trusted(peer):
                    raise ReceiptRejected("Untrusted installed native host or desktop seat")
                conn.settimeout(remaining())
                # Retain the exact attempted command identity BEFORE
                # sendall, including when a partial send or lost ACK faults
                # this client. Only bounded SHA-256 digests are exposed.
                # A digest from this process is NOT protected custody or
                # evidence of actual delivery / human consent.
                self._last_attempted_wire = AttemptedWireFingerprint(
                    action=action,
                    request_id_sha256=(
                        sha256(request_id.encode("ascii")).hexdigest()
                        if request_id is not None else None
                    ),
                    client_nonce_sha256=sha256(nonce.encode("ascii")).hexdigest(),
                    frame_sha256=sha256(wire).hexdigest(),
                )
                # Once a send is attempted, even a send failure cannot prove
                # the native host did not receive enough bytes to act.
                self._last_wire_outcome = "UNKNOWN_HOLD"
                conn.sendall(wire)
                raw = bytearray()
                while len(raw) <= 1024 and b"\n" not in raw:
                    conn.settimeout(remaining())
                    part = conn.recv(1025 - len(raw))
                    if not part:
                        break
                    raw.extend(part)
                body = verify_receipt(bytes(raw), pinned_key=self._key,
                                      action=action, command_request_id=request_id,
                                      client_nonce=nonce)
                # A complete frame is not a timely completed transaction:
                # verification and the final independent guard share the
                # same monotonic budget before we accept any receipt state.
                remaining()
                if not self._trusted(peer):
                    raise ReceiptRejected("Lost trusted host or desktop seat")
                remaining()
            if self._instance is None:
                self._instance = body["hostInstance"]
            elif self._instance != body["hostInstance"]:
                raise ReceiptRejected("Host instance changed during command session")
            if body["sequence"] <= self._sequence:
                raise ReceiptRejected("Replayed or reordered host receipt")
            self._sequence = body["sequence"]
            self._phase = body["state"]
            if self._phase == "UNAVAILABLE":
                self._last_wire_outcome = "SIGNED_FRAME_SEEN"
                # Unavailable is not permission. Keep the current host-issued
                # request for another explicit status check if still trusted.
                return HostCommandObservation(
                    phase="UNAVAILABLE", request_id=None,
                    instance=self._instance, sequence=self._sequence)
            self._request_id = body["requestId"]
            if self._phase == "HOST_LOST":
                self._fault()
                raise ReceiptRejected("Native host revoked; new enrollment required")
            self._last_wire_outcome = "SIGNED_FRAME_SEEN"
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
