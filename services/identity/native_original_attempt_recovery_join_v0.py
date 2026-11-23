"""DOC 6: Read-only original native attempt ↔ two recovery diagnostics.

This is a nonauthorizing Identity Center comparison, not a protected issuer.
It reuses the real client-produced *process-local* attempted wire fingerprint,
the original strict native command serializer, the untrusted outcome-candidate
inspector and the existing signed-receipt shadow. All sources are caller
supplied; even two matching checks cannot establish independent custody.

No network I/O, database, sender, provider login, or native command action.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from collections.abc import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from desktop_signed_command_client_v0 import AttemptedWireFingerprint
from native_outcome_candidate_shadow_v0 import (
    OriginalCommandBinding, inspect_candidate_once,
)
from native_recorded_signed_receipt_shadow_v0 import (
    inspect_recorded_signed_receipt,
)
from signed_command_receipt_v0 import ReceiptRejected, build_request

SCHEMA = "post-apollo.identity.original-attempt-recovery-readonly-v0"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)


@dataclass(frozen=True, slots=True)
class OriginalAttemptRecoveryInspection:
    schema: str
    state: str
    reason: str
    original_frame_matched: bool = False
    candidate_lookup_count: int = 0
    candidate_reason: str = "NOT_INSPECTED"
    signed_frame_checked: bool = False
    signed_frame_reason: str = "NOT_INSPECTED"
    safe_actions: tuple[str, ...] = ()
    can_retry: bool = False
    can_begin_sign_in: bool = False
    can_cancel: bool = False
    can_recover: bool = False
    can_connect_provider: bool = False
    original_host_authenticated: bool = False
    protected_current_history: bool = False
    independent_issuer_enrolled: bool = False
    human_one_use_consent: bool = False
    terminal_outcome_settled: bool = False
    production_authority: bool = False


def _held(reason: str, *, matched: bool = False, candidate=None, signed=None):
    return OriginalAttemptRecoveryInspection(
        schema=SCHEMA, state="UNKNOWN_HOLD", reason=reason,
        original_frame_matched=matched,
        candidate_lookup_count=(candidate.lookup_count if candidate else 0),
        candidate_reason=(candidate.reason if candidate else "NOT_INSPECTED"),
        signed_frame_checked=(signed.signed_frame_checked if signed else False),
        signed_frame_reason=(signed.reason if signed else "NOT_INSPECTED"),
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: object) -> bool:
    return type(value) is str and _HEX64.fullmatch(value) is not None


def inspect_original_attempt_once(
    *,
    attempted: AttemptedWireFingerprint | None,
    original: OriginalCommandBinding,
    original_client_nonce: str | None,
    original_request_id: str | None,
    candidate_provider: Callable[[OriginalCommandBinding], object] | None,
    recorded_signed_frame: bytes | None,
    pinned_receipt_key: Ed25519PublicKey | None,
) -> OriginalAttemptRecoveryInspection:
    """Fail original-binding mismatch BEFORE any candidate source invocation.

    The result is always UNKNOWN_HOLD. This function cannot authenticate an
    independent issuer/source, current protected history or the C5 spend.
    Caller-supplied Ed25519 pins, recorded frames and provider responses
    are diagnostic inputs, not proof of external custody.
    """
    if type(original) is not OriginalCommandBinding:
        return _held("MISSING_OR_INVALID_ORIGINAL_BINDING")
    if type(attempted) is not AttemptedWireFingerprint:
        return _held("NO_PROCESS_LOCAL_ATTEMPT_FINGERPRINT")

    if (type(attempted.action) is not str
            or attempted.action != original.action
            or not _digest(attempted.client_nonce_sha256)
            or not _digest(attempted.frame_sha256)
            or (attempted.request_id_sha256 is not None
                and not _digest(attempted.request_id_sha256))
            or attempted.request_id_sha256 != original.request_digest
            or attempted.client_nonce_sha256 != original.nonce_digest):
        return _held("ORIGINAL_ATTEMPT_IDENTITY_CONFLICT")

    # Reconstruct only in local memory. The original request ID and nonce
    # are never included in the result; strict serializer validates both.
    try:
        wire = build_request(
            original.action, original_request_id, original_client_nonce
        )
    except (ReceiptRejected, TypeError, ValueError):
        return _held("INVALID_ORIGINAL_NATIVE_REQUEST")
    if _sha(wire) != attempted.frame_sha256:
        return _held("ORIGINAL_SERIALIZED_FRAME_CONFLICT")

    # One optional untrusted provider query, no retries or alternate source.
    candidate = inspect_candidate_once(
        original=original, provider=candidate_provider
    )
    signed = inspect_recorded_signed_receipt(
        original=original, recorded_frame=recorded_signed_frame,
        pinned_receipt_key=pinned_receipt_key,
        original_request_id=original_request_id,
        original_client_nonce=original_client_nonce,
    )

    # Local equality is never enough to trust a source or infer no effect.
    if candidate.reason == "CONFLICTING_UNTRUSTED_CANDIDATE":
        reason = "RECOVERY_CANDIDATE_CONFLICTS_WITH_ORIGINAL"
    elif signed.reason == "SIGNED_FRAME_WRONG_HOST_OR_SEQUENCE":
        reason = "SIGNED_RECEIPT_CONFLICTS_WITH_ORIGINAL"
    elif (candidate.reason == "MATCHED_CLAIM_STILL_UNTRUSTED"
          and signed.reason == "SIGNED_FRAME_MATCHED_BUT_NO_PROTECTED_TERMINAL"):
        reason = "MATCHING_UNTRUSTED_SOURCES_STILL_NOT_SETTLEMENT"
    else:
        reason = "INCOMPLETE_OR_UNTRUSTED_RECOVERY_EVIDENCE"

    return _held(reason, matched=True, candidate=candidate, signed=signed)
