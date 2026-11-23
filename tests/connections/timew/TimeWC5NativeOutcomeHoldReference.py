"""DOC 5 TimeW C5 one-spend/native-outcome trace interpreter: CI ONLY.

All inputs are caller-controlled diagnostics. This source does not verify native
SwayPX callbacks, an enrolled producer, a protected one-use grant, a trusted
human seat, compositor settlement, or a cryptographic wire. It never issues an
action. Even a fully consistent trace remains UNKNOWN/HOLD.
"""
from __future__ import annotations

from TimeWC5ReviewShadowReference import (
    ORIGINAL_FIELDS, _validate_original,
)
from TimeWC5SpendFenceReference import MAX_MS

TRACE_SCHEMA = "postapollo.connections.c5.timew.outcome-shadow-fixture.v1"
CONTEXT_FIELDS = frozenset((
    "audience", "action", "grant_id", "operation_id",
    "selection_sha256", "intent_sha256", "source_sha256",
    "session_id", "seat_id", "issuer_epoch",
    "checkpoint_id", "window_key", "boot_epoch", "surface_generation",
    "output_id", "workspace_id", "output_scale_hex", "output_transform",
    "before_value", "target_value", "issued_ms", "expires_ms",
))
EVENT_FIELDS = frozenset(("kind", "context"))
EVENT_KINDS = frozenset((
    "C5_SPENT_REPORTED", "C5_REVOKE_REQUESTED", "SECOND_SPEND_REPORTED",
    "RESIZE_DISPATCH_REPORTED", "SECOND_RESIZE_REPORTED",
    "RESIZE_READY_CALLBACK", "RESIZE_TIMER_TIMEOUT",
    "RESIZE_CURRENT_COPIED", "RESIZE_SCENE_ARRANGED",
    "RESIZE_PRESENT_REPORTED",
    "MOVE_DISPATCH_REPORTED", "MOVE_READY_CALLBACK",
    "MOVE_TIMER_TIMEOUT", "MOVE_CURRENT_COPIED",
    "MOVE_SCENE_ARRANGED", "MOVE_PRESENT_REPORTED",
    "ACK_LOST_REPORTED", "HOST_EXIT_REPORTED",
))
RESIZE_CALLBACKS = frozenset((
    "RESIZE_READY_CALLBACK", "RESIZE_TIMER_TIMEOUT",
    "RESIZE_CURRENT_COPIED", "RESIZE_SCENE_ARRANGED",
    "RESIZE_PRESENT_REPORTED",
))
MOVE_CALLBACKS = frozenset((
    "MOVE_READY_CALLBACK", "MOVE_TIMER_TIMEOUT",
    "MOVE_CURRENT_COPIED", "MOVE_SCENE_ARRANGED",
    "MOVE_PRESENT_REPORTED",
))
LEDGER_STATES = frozenset(("ACTIVE", "SPENT", "REVOKED", "UNKNOWN"))
JOURNAL_STAGES = frozenset((
    "PREPARED", "DISPATCHING", "UNCERTAIN", "FIXTURE_COMPLETE",
))
MAX_EVENTS = 64


def hold(reason):
    """All outputs irrevocably deny native command, permission and retry."""
    return {
        "diagnostic": reason,
        "production_authorized": False,
        "native_action_allowed": False,
        "human_consent_verified": False,
        "trusted_source_verified": False,
        "protected_spent_verified": False,
        "terminal_settlement_verified": False,
        "revocation_acknowledged": False,
        "move_continuation_allowed": False,
        "retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


def original_event_context(original):
    """Untrusted in-memory fixture identity, NOT a signed source/wire format."""
    if not _validate_original(original):
        raise ValueError("INVALID_TIMEW_C5_SHADOW_ORIGINAL")
    return {name: original[name] for name in CONTEXT_FIELDS}


def evaluate_native_outcome_shadow(*, original, ledger_state, journal_stage,
                                   events, now_ms):
    """Compare entire event sequence against one immutable candidate operation.

    This function performs no IO. Event order is an untrusted test assertion,
    not the authoritative ordering of compositor events or protected SPENT.
    """
    if not _validate_original(original):
        return hold("INVALID_ORIGINAL_HOLD")
    if type(ledger_state) is not str or ledger_state not in LEDGER_STATES:
        return hold("INVALID_LEDGER_STATE_HOLD")
    if type(journal_stage) is not str or journal_stage not in JOURNAL_STAGES:
        return hold("INVALID_JOURNAL_STAGE_HOLD")
    if type(now_ms) is not int or not 0 <= now_ms <= MAX_MS:
        return hold("INVALID_CLOCK_HOLD")
    if type(events) is not tuple or len(events) > MAX_EVENTS:
        return hold("INVALID_EVENT_CONTAINER_HOLD")

    expected = original_event_context(original)
    kinds = []
    for item in events:
        if (type(item) is not dict or set(item) != EVENT_FIELDS
                or type(item["kind"]) is not str
                or item["kind"] not in EVENT_KINDS
                or type(item["context"]) is not dict
                or set(item["context"]) != CONTEXT_FIELDS):
            return hold("MALFORMED_EVENT_HOLD")
        if any(type(item["context"][key]) is not type(expected[key])
               or item["context"][key] != expected[key]
               for key in CONTEXT_FIELDS):
            return hold("CHANGED_OPERATION_OR_SOURCE_HOLD")
        kinds.append(item["kind"])

    spent_seen = False
    resized = False
    moved = False
    ready = False
    timed_out = False
    copied_after_timeout = False
    scene_after_timeout = False
    current_copied = False
    scene_arranged = False
    present_reported = False
    revoked_after_spend = False
    revoked_before_spend = False
    lost_or_exit = False

    for kind in kinds:
        if kind == "C5_SPENT_REPORTED":
            if spent_seen or revoked_before_spend:
                return hold("DUPLICATE_OR_REVOKED_SPEND_HOLD")
            if resized or moved:
                return hold("SPEND_AFTER_EFFECT_HOLD")
            spent_seen = True
        elif kind == "SECOND_SPEND_REPORTED":
            return hold("SECOND_SPEND_ATTEMPT_HOLD")
        elif kind == "C5_REVOKE_REQUESTED":
            if spent_seen or ledger_state == "SPENT":
                revoked_after_spend = True
            else:
                revoked_before_spend = True
        elif kind == "RESIZE_DISPATCH_REPORTED":
            if resized:
                return hold("DUPLICATE_RESIZE_DISPATCH_HOLD")
            if not spent_seen:
                return hold("RESIZE_BEFORE_SPENT_REPORT_HOLD")
            resized = True
        elif kind == "SECOND_RESIZE_REPORTED":
            return hold("SECOND_RESIZE_ATTEMPT_HOLD")
        elif kind in RESIZE_CALLBACKS:
            if not resized:
                return hold("RESIZE_CALLBACK_WITHOUT_DISPATCH_HOLD")
            if kind == "RESIZE_READY_CALLBACK":
                ready = True
            elif kind == "RESIZE_TIMER_TIMEOUT":
                timed_out = True
            elif kind == "RESIZE_CURRENT_COPIED":
                current_copied = True
                copied_after_timeout |= timed_out
            elif kind == "RESIZE_SCENE_ARRANGED":
                scene_arranged = True
                scene_after_timeout |= timed_out
            elif kind == "RESIZE_PRESENT_REPORTED":
                present_reported = True
        elif kind == "MOVE_DISPATCH_REPORTED":
            if moved:
                return hold("DUPLICATE_MOVE_DISPATCH_HOLD")
            if not resized:
                return hold("MOVE_WITHOUT_RESIZE_HOLD")
            moved = True
        elif kind in MOVE_CALLBACKS:
            if not moved:
                return hold("MOVE_CALLBACK_WITHOUT_DISPATCH_HOLD")
        elif kind in ("ACK_LOST_REPORTED", "HOST_EXIT_REPORTED"):
            lost_or_exit = True

    # The ledger/journal are NOT independent real records. These checks expose
    # obvious inconsistencies, but a forged internally consistent pair remains
    # denied too. Recovery after expiry may still need evidence read; expiry is
    # not permission to discard SPENT or retry.
    effect_reported = resized or moved
    if revoked_before_spend and effect_reported:
        return hold("EFFECT_AFTER_REVOKE_UNKNOWN_HOLD")
    if ledger_state != "SPENT" and effect_reported:
        return hold("EFFECT_WITHOUT_SPENT_LEDGER_UNKNOWN_HOLD")
    if journal_stage == "PREPARED" and effect_reported:
        return hold("SPENT_WITH_PREPARED_AND_EFFECT_UNKNOWN_HOLD")
    if revoked_after_spend:
        return hold("POST_SPENT_REVOCATION_UNKNOWN_HOLD")
    if lost_or_exit:
        return hold("LOST_ACK_OR_HOST_EXIT_UNKNOWN_HOLD")
    if now_ms >= original["expires_ms"] or now_ms < original["issued_ms"]:
        return hold("EXPIRED_OR_NOT_YET_ISSUED_RECOVERY_HOLD")
    if timed_out:
        if moved:
            return hold("FOLLOWON_MOVE_AFTER_TIMEOUT_UNKNOWN_HOLD")
        if copied_after_timeout or scene_after_timeout:
            return hold("TIMEOUT_CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD")
        return hold("RESIZE_TIMEOUT_UNKNOWN_HOLD")
    if moved:
        # Even normal READY + CURRENT + SCENE + reported PRESENT is not a
        # protected source, signed per-step receipt, or authenticated settlement.
        return hold("MOVE_REPORTED_WITHOUT_TRUSTED_TERMINAL_UNKNOWN_HOLD")
    if not spent_seen:
        return hold("NO_SPENT_EVIDENCE_UNKNOWN_HOLD")
    if journal_stage == "PREPARED":
        return hold("SPENT_BUT_LOCAL_PREPARED_UNKNOWN_HOLD")
    if not resized:
        return hold("SPENT_WITHOUT_RESIZE_EVIDENCE_UNKNOWN_HOLD")
    if ready and current_copied and scene_arranged and present_reported:
        return hold("PRESENT_REPORTED_BUT_UNAUTHENTICATED_HOLD")
    if current_copied or scene_arranged:
        return hold("CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD")
    return hold("RESIZE_DISPATCH_OUTCOME_UNKNOWN_HOLD")
