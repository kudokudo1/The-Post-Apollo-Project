"""Shared read-only Identity native command attempt fingerprint value.

A digest-only process-local observation, not command evidence or permission.
This contains no transport, gateway, signer, issuer, C5 consent or native call.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AttemptedWireFingerprint:
    """Digest-only last *attempted* command, not a signed/trusted record.

    Does not prove the peer received bytes or that an effect occurred.
    The client retains this object only in process memory. No auto retry.
    """

    action: str
    request_id_sha256: str | None
    client_nonce_sha256: str
    frame_sha256: str

@dataclass(frozen=True, slots=True)
class NativeCommandDeliverySnapshot:
    """Coherent process-local delivery observation, never authorization.

    The latest attempted fingerprint may predate the current call's outcome.
    A signed frame is not terminal effect evidence. A fresh process cannot
    infer a previous process's outcome from UNOBSERVED.
    """

    wire_outcome: str
    last_attempted_wire: AttemptedWireFingerprint | None
    faulted: bool
