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
