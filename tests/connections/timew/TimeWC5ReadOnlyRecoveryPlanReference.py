"""DOC 5 / TimeW C5 UNKNOWN/HOLD read-only recovery lookup INTENTS.

SOURCE-ONLY, NON-AUTHORIZING REFERENCE. This prepares two immutable, minimally
scoped *conceptual* lookup descriptions from one previously reviewed
untrusted TimeW/C5 operation fixture. It does not call a provider, issue an
operation, sign/verify packets, pin an issuer, open files, connect to a NAS,
verify a selected XDG surface, or prove a human gesture. These are not
accepted IPC/wire field names. A real enrolled custodian and native producer
must implement separately reviewed, protected read-only recovery endpoints.

The original grant is NEVER reissued, respent or retried; no automatic move,
undo, new operation ID, or claimed settlement is possible here.
"""
from __future__ import annotations

from dataclasses import dataclass

from TimeWC5ReviewShadowReference import _validate_original


UNCERTAINTIES = frozenset((
    "C5_SPENT_REPLY_LOST",
    "TIMEW_CRASH_AFTER_SPENT",
    "SPENT_BUT_TIMEW_PREPARED",
    "NATIVE_RESIZE_ACK_LOST",
    "NATIVE_RESIZE_TIMEOUT",
    "NATIVE_MOVE_ACK_LOST",
    "NATIVE_HOST_RESTARTED",
    "REVOCATION_AFTER_POSSIBLE_SPEND",
))

# These are separate purpose *labels*, not actual provider addresses or
# approved wire audiences. Distinct role enrollment is mandatory later.
CUSTODIAN_LOOKUP = "TIMEW_C5_PROTECTED_CURRENT_HISTORY_ONLY"
NATIVE_LOOKUP = "TIMEW_SELECTED_XDG_NATIVE_TERMINAL_ONLY"

CUSTODIAN_FIELDS = (
    "audience", "action", "grant_id", "operation_id", "issuer_epoch",
    "selection_sha256", "intent_sha256", "source_sha256", "session_id",
    "seat_id", "issued_ms", "expires_ms",
)
NATIVE_FIELDS = (
    "operation_id", "selection_sha256", "intent_sha256", "source_sha256",
    "session_id", "seat_id", "checkpoint_id", "window_key", "boot_epoch",
    "surface_generation", "output_id", "workspace_id",
    "output_scale_hex", "output_transform",
)

@dataclass(frozen=True, slots=True)
class UntrustedLookupIntent:
    """Not a signed grant, executable endpoint, request, or trusted receipt."""

    role: str
    original_operation_id: str
    original_grant_id: str
    original_binding: tuple[tuple[str, str | int], ...]

@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Contains no capability to spend, send, resize, move or retry."""

    diagnostic: str
    uncertainty: str | None
    query_intents: tuple[UntrustedLookupIntent, ...]
    production_authorized: bool = False
    protected_spent_verified: bool = False
    custodian_current_head_verified: bool = False
    original_human_consent_verified: bool = False
    native_source_authenticated: bool = False
    terminal_settlement_verified: bool = False
    native_action_allowed: bool = False
    automatic_second_spend_allowed: bool = False
    move_continuation_allowed: bool = False
    retry_allowed: bool = False
    undo_allowed: bool = False
    safe_actions: tuple = ()


def _hold(reason: str) -> RecoveryPlan:
    return RecoveryPlan(diagnostic=reason, uncertainty=None, query_intents=())


def prepare_unknown_recovery_intents(*, original, uncertainty):
    """Describe two ORIGINAL-operation read-only lookups; always UNKNOWN/HOLD.

    There is deliberately no provider callback, no transport method and no
    caller-created query payload. This can be used only by source/CI reviews
    until owner-approved trusted transport, enrollment and receipt semantics
    exist. Recovery remains necessary even after the old grant expires.
    """
    if not _validate_original(original):
        return _hold("INVALID_ORIGINAL_UNKNOWN_HOLD")
    if type(uncertainty) is not str or uncertainty not in UNCERTAINTIES:
        return _hold("INVALID_RECOVERY_CAUSE_UNKNOWN_HOLD")

    # _validate_original already rejects forged binary64 phases/NaN/-0,
    # invalid grant/operation UUIDs, wrong C5 audience, changed step order,
    # malformed output scale, issuer epoch, source/seat and missing fields.
    original_id = original["operation_id"]
    original_grant = original["grant_id"]
    custodian_binding = tuple((key, original[key]) for key in CUSTODIAN_FIELDS)
    native_binding = tuple((key, original[key]) for key in NATIVE_FIELDS)
    before = original["before_value"]
    target = original["target_value"]
    native_binding += (
        ("before_version", before.version),
        ("before_phase", before.phase),
        ("before_x_bits", before.x_bits),
        ("before_y_bits", before.y_bits),
        ("before_width_bits", before.width_bits),
        ("before_height_bits", before.height_bits),
        ("target_version", target.version),
        ("target_phase", target.phase),
        ("target_x_bits", target.x_bits),
        ("target_y_bits", target.y_bits),
        ("target_width_bits", target.width_bits),
        ("target_height_bits", target.height_bits),
    )
    return RecoveryPlan(
        diagnostic="UNTRUSTED_DUAL_READ_ONLY_LOOKUP_INTENTS_UNKNOWN_HOLD",
        uncertainty=uncertainty,
        query_intents=(
            UntrustedLookupIntent(
                CUSTODIAN_LOOKUP, original_id, original_grant,
                custodian_binding),
            UntrustedLookupIntent(
                NATIVE_LOOKUP, original_id, original_grant,
                native_binding),
        ),
    )
