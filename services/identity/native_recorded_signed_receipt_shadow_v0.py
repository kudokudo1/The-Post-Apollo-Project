"""DOC 6: Verify recorded Identity signed command bytes without promoting trust.

This read-only shadow reuses the existing pinned Ed25519 command-receipt
verifier. It checks that one recorded frame matches the original native action,
request, nonce, signed host instance and sequence floor.

Even a real signature from a caller-selected test key is NOT independently
enrolled host provenance, durable terminal settlement, current protected
history, original seat/consent, or safe retry. The output always UNKNOWN_HOLD.

NO socket, native command sender, DB, host installation, UI or credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from native_outcome_candidate_shadow_v0 import OriginalCommandBinding
from signed_command_receipt_v0 import ReceiptRejected, verify_receipt

SCHEMA = "post-apollo.identity.recorded-signed-receipt-shadow.untrusted-v0"
MAX_FRAME = 1024


@dataclass(frozen=True, slots=True)
class SignedReceiptShadow:
    schema: str
    state: str
    reason: str
    signed_frame_checked: bool = False
    safe_actions: tuple[str, ...] = ()
    can_retry: bool = False
    can_begin_sign_in: bool = False
    can_cancel: bool = False
    can_recover: bool = False
    can_connect_provider: bool = False
    independently_enrolled_host: bool = False
    protected_history_current: bool = False
    protected_terminal_outcome: bool = False
    human_one_use_consent: bool = False
    production_authority: bool = False


def _held(reason: str, checked: bool = False) -> SignedReceiptShadow:
    return SignedReceiptShadow(
        schema=SCHEMA, state="UNKNOWN_HOLD", reason=reason,
        signed_frame_checked=checked,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def inspect_recorded_signed_receipt(
    *,
    original: OriginalCommandBinding,
    recorded_frame: bytes | None,
    pinned_receipt_key: Ed25519PublicKey | None,
    original_request_id: str | None,
    original_client_nonce: str | None,
) -> SignedReceiptShadow:
    """One bounded local signature check. Never a native recovery operation.

    All expected identities and the Ed25519 pin arrive from the caller.
    Caller ownership does not become independently protected enrollment.
    `signed_frame_checked` only means verify_receipt returned successfully.
    A matching old receipt is not a fresh protected issuer outcome query.
    """
    if type(original) is not OriginalCommandBinding:
        return _held("MISSING_ORIGINAL_COMMAND_BINDING")
    if (type(original_client_nonce) is not str
            or len(original_client_nonce) != 43
            or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
                   for c in original_client_nonce)
            or _digest(original_client_nonce) != original.nonce_digest):
        return _held("MISSING_OR_MISMATCHED_ORIGINAL_NONCE")
    if original.action == "BEGIN":
        if original_request_id is not None:
            return _held("INVALID_ORIGINAL_REQUEST_ID")
    elif (type(original_request_id) is not str
          or not 16 <= len(original_request_id) <= 96
          or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
                 for c in original_request_id)
          or _digest(original_request_id) != original.request_digest):
        return _held("MISSING_OR_MISMATCHED_ORIGINAL_REQUEST_ID")
    if (type(recorded_frame) is not bytes
            or not 0 < len(recorded_frame) <= MAX_FRAME):
        return _held("NO_BOUNDED_RECORDED_SIGNED_FRAME")
    if not isinstance(pinned_receipt_key, Ed25519PublicKey):
        return _held("NO_INDEPENDENTLY_VERIFIED_RECEIPT_PIN")
    try:
        body = verify_receipt(
            recorded_frame,
            pinned_key=pinned_receipt_key,
            action=original.action,
            command_request_id=original_request_id,
            client_nonce=original_client_nonce,
        )
    except (ReceiptRejected, ValueError, TypeError):
        return _held("INVALID_OR_MISMATCHED_SIGNED_FRAME")

    # Signed payload binds the command and nonce, but lacks the independently
    # protected C3e/C4b source/history/seat and C5 human one-use evidence.
    if (_digest(body["hostInstance"]) != original.host_instance_digest
            or body["sequence"] < original.minimum_sequence):
        return _held("SIGNED_FRAME_WRONG_HOST_OR_SEQUENCE", True)

    # A recorded AUTHENTICATED or UNAVAILABLE result is still NOT a protected
    # terminal outcome, safe retry, permission grant or external IdP scope.
    return _held("SIGNED_FRAME_MATCHED_BUT_NO_PROTECTED_TERMINAL", True)
