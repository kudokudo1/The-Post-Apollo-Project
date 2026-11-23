#!/usr/bin/env python3
"""DOC 3 // Compare UNTRUSTED Forest B4e and C5 V1 recovery observations.

This diagnostic never accesses a Forest database, invokes B4e, trusts an
injected host, signs receipts, or settles a permit. Callers supply both
observations. Even matching local COMMITTED and signed fixture COMMIT claims
are NEVER proof of an independently enrolled, durable native C5 terminal.
"""
from __future__ import annotations

from types import MappingProxyType

from services.connections.forest import ForestC5ExactSessionV1Preflight as V

SCHEMA = "postapollo.forest.c5-local-recovery-interop.v0"
STATUS_HOLD = "FOREST_C5_TWO_UNTRUSTED_SOURCES_UNKNOWN_HOLD"
LOCAL_SCHEMA = "post-apollo.forest.local-recovery.synthetic-b4d"
LOCAL_STATES = frozenset((
    "FOREST_RESERVED", "FOREST_ABORTED", "FOREST_COMMITTED",
))
LOCAL_FIELDS = frozenset((
    "schema", "attemptId", "sessionId", "forestWriteState", "c5Settlement",
    "c5EvidenceAuthenticated", "terminalReceiptAuthenticated",
    "safeToRetryInference", "safeToReleaseRevocation", "productionAuthority",
))
SIGNED_FIELDS = frozenset((
    "schema", "status", "claimedSessionIdUntrusted",
    "claimedIntentSha256Untrusted", "claimedReceiptSha256Untrusted",
    "claimedTerminalOutcomeUntrusted", "claimedWriterJournalCounterUntrusted",
    "claimedForestBindingCallerControlled",
    "claimedSignerKeysAndJournalCallerControlled", "safeActions",
)) | frozenset(V.NO_AUTHORITY)

NO_AUTHORITY = MappingProxyType({
    **dict(V.NO_AUTHORITY),
    "localForestRecordOriginAuthenticated": False,
    "protectedOriginalWriterAndProcessAuthenticated": False,
    "actualSQLiteTransactionDurabilityProven": False,
    "independentC5IssuerOutcomeAuthenticated": False,
    "crossStoreTerminalSettlementVerified": False,
    "safeToRetryInference": False,
    "safeToReleaseRevocation": False,
})


class RecoveryComparisonHold(ValueError):
    """A malformed/conflicting untrusted observation never releases a grant."""


def _hold(reason: str) -> None:
    raise RecoveryComparisonHold("FOREST_C5_RECOVERY_UNKNOWN_HOLD // " + reason)


def _check_local(value: object) -> dict:
    if type(value) is not dict or set(value) != LOCAL_FIELDS:
        _hold("LOCAL_EXACT_FIELDS_REQUIRED")
    if (value["schema"] != LOCAL_SCHEMA or
            type(value["attemptId"]) is not str or
            type(value["sessionId"]) is not str or
            type(value["forestWriteState"]) is not str or
            value["forestWriteState"] not in LOCAL_STATES or
            value["c5Settlement"] != "UNKNOWN_HOLD"):
        _hold("LOCAL_SCHEMA_OR_STATE_UNTRUSTED")
    for name in (
        "c5EvidenceAuthenticated", "terminalReceiptAuthenticated",
        "safeToRetryInference", "safeToReleaseRevocation",
        "productionAuthority",
    ):
        if value[name] is not False:
            _hold("LOCAL_AUTHORITY_PROMOTION_REFUSED")
    return value


def _check_signed(value: object) -> dict:
    if type(value) is not dict or set(value) != SIGNED_FIELDS:
        _hold("SIGNED_EXACT_FIELDS_REQUIRED")
    if (value["schema"] != V.RESULT_SCHEMA or
            value["status"] != "V1_SESSION_BOUND_FIXTURE_CONSISTENT_NOT_AUTHENTICATED" or
            value["claimedForestBindingCallerControlled"] is not True or
            value["claimedSignerKeysAndJournalCallerControlled"] is not True or
            type(value["safeActions"]) is not list or
            value["safeActions"] != []):
        _hold("SIGNED_NOT_UNTRUSTED_DIAGNOSTIC")
    if (type(value["claimedSessionIdUntrusted"]) is not str or
            type(value["claimedIntentSha256Untrusted"]) is not str or
            type(value["claimedReceiptSha256Untrusted"]) is not str or
            type(value["claimedWriterJournalCounterUntrusted"]) is not int or
            value["claimedWriterJournalCounterUntrusted"] < 1 or
            value["claimedTerminalOutcomeUntrusted"] not in
            ("COMMIT_CONFIRMED", "ROLLBACK_CONFIRMED")):
        _hold("SIGNED_DIAGNOSTIC_INVALID")
    for name in V.NO_AUTHORITY:
        if value[name] is not False:
            _hold("SIGNED_AUTHORITY_PROMOTION_REFUSED")
    return value


def compare_untrusted_local_with_v1_claim(
    local_observation: dict, signed_fixture_diagnostic: dict,
    original_v1_intent_wire: bytes,
) -> dict:
    """Compare coarse observed attempt/session identities, NEVER authenticate.

    The local record is the Forest-owned B4e shape and may come from real
    *disposable* SQLite. The V1 diagnostic contains three caller-supplied
    fixture signatures/claimed journal counters. Neither can prove the
    latest protected writer root, current history, native commit, or issuer.
    Reject contradictory inputs rather than silently relabeling an unknown.
    """
    local = _check_local(local_observation)
    signed = _check_signed(signed_fixture_diagnostic)
    try:
        intent, digest = V._intent(original_v1_intent_wire)
    except V.V1Hold as exc:
        raise RecoveryComparisonHold(
            "FOREST_C5_RECOVERY_UNKNOWN_HOLD // INTENT_V1_UNTRUSTED_OR_MALFORMED"
        ) from exc
    if (local["attemptId"] != intent["attempt"] or
            local["sessionId"] != intent["sessionId"] or
            signed["claimedSessionIdUntrusted"] != intent["sessionId"] or
            signed["claimedIntentSha256Untrusted"] != digest):
        _hold("ATTEMPT_OR_SESSION_OR_INTENT_MISMATCH")
    # Even a hash match does not authenticate the signed fixture or local row.
    if len(signed["claimedReceiptSha256Untrusted"]) != 64 or any(
            x not in "0123456789abcdef"
            for x in signed["claimedReceiptSha256Untrusted"]):
        _hold("UNTRUSTED_RECEIPT_DIGEST_INVALID")
    state = local["forestWriteState"]
    claim = signed["claimedTerminalOutcomeUntrusted"]
    # The local attempt can be stale/restored, and the signer can be fake.
    conflict = ((state == "FOREST_COMMITTED" and claim == "ROLLBACK_CONFIRMED")
                or (state == "FOREST_ABORTED" and claim == "COMMIT_CONFIRMED"))
    if conflict:
        reason = "LOCAL_AND_SIGNED_CLAIM_CONFLICT_HOLD"
    elif state == "FOREST_RESERVED":
        reason = "LOCAL_RESERVED_NO_TERMINAL_PROOF_HOLD"
    else:
        reason = "LOCAL_AND_SIGNED_CLAIM_AGREE_BUT_UNTRUSTED_HOLD"
    # Never expose prompts, responses, owner, session or attempt IDs, or
    # pretend a diagnosis is an authenticated issuer settlement.
    return {
        "schema": SCHEMA,
        "status": STATUS_HOLD,
        "reason": reason,
        "localForestWriteStateUntrusted": state,
        "signedWriterTerminalClaimUntrusted": claim,
        "localAndSignedClaimsConflict": conflict,
        "sourceObservationsBothUntrusted": True,
        "safeActions": [],
        **dict(NO_AUTHORITY),
    }
