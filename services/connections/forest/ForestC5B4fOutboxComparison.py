#!/usr/bin/env python3
"""DOC 3 // Forest B4f LOCAL terminal outbox vs untrusted C5 V1 claims.

CI-only. The B4f inspector is an untrusted snapshot of a restorable SQLite
file, not an independently enrolled native writer. An event ID is not a
signed terminal receipt or one-use permit. Never settle UNKNOWN_HOLD.
"""
from __future__ import annotations

import re
from types import MappingProxyType

from services.connections.forest import ForestC5LocalRecoveryComparison as L

SCHEMA = "postapollo.forest.c5-b4f-outbox-interop-deny.v0"
OUTBOX_SCHEMA = "post-apollo.forest.local-terminal.synthetic-b4f"
STATUS_HOLD = "FOREST_B4F_LOCAL_OUTBOX_NOT_C5_CUSTODY_HOLD"
OUTBOX_FIELDS = frozenset((
    "schema", "attemptId", "sessionId", "forestWriteState",
    "localTerminalEvent", "localEventId", "c5Settlement",
    "terminalReceiptAuthenticated", "custodyAuthenticated",
    "safeToRetryInference", "safeToReleaseRevocation",
    "productionAuthority",
))
LOCAL_TERMINAL = frozenset((
    "LOCAL_COMMITTED", "LOCAL_ABORTED", "LOCAL_EVENT_NOT_OBSERVED",
))
EVENT_ID = re.compile(r"e_[0-9a-f]{32}\Z", re.ASCII)
NO_AUTHORITY = MappingProxyType({
    **dict(L.NO_AUTHORITY),
    "b4fLocalTerminalEventAuthenticated": False,
    "b4fOriginalWriterReleaseAuthenticated": False,
    "b4fIndependentHistoryAuthenticated": False,
    "b4fExactC5PermitInWriterTransaction": False,
})


class B4fC5Hold(ValueError):
    """Malformed source or fabricated claims cannot imply an authorized act."""


def _hold(code: str) -> None:
    raise B4fC5Hold("FOREST_B4F_C5_UNKNOWN_HOLD // " + code)


def _local_view(outbox: object) -> tuple[dict, str]:
    if type(outbox) is not dict or set(outbox) != OUTBOX_FIELDS:
        _hold("LOCAL_OUTBOX_EXACT_FIELDS_REQUIRED")
    if (outbox["schema"] != OUTBOX_SCHEMA or
            type(outbox["attemptId"]) is not str or
            type(outbox["sessionId"]) is not str or
            type(outbox["forestWriteState"]) is not str or
            outbox["forestWriteState"] not in L.LOCAL_STATES or
            type(outbox["localTerminalEvent"]) is not str or
            outbox["localTerminalEvent"] not in LOCAL_TERMINAL or
            outbox["c5Settlement"] != "UNKNOWN_HOLD"):
        _hold("LOCAL_OUTBOX_SHAPE_OR_STATUS_INVALID")
    for name in (
        "terminalReceiptAuthenticated", "custodyAuthenticated",
        "safeToRetryInference", "safeToReleaseRevocation",
        "productionAuthority",
    ):
        if outbox[name] is not False:
            _hold("LOCAL_OUTBOX_AUTHORITY_PROMOTION_REFUSED")
    event = outbox["localTerminalEvent"]
    event_id = outbox["localEventId"]
    if event == "LOCAL_EVENT_NOT_OBSERVED":
        if event_id is not None:
            _hold("MISSING_EVENT_WITH_NONEMPTY_ID")
    elif (type(event_id) is not str or
          EVENT_ID.fullmatch(event_id) is None):
        _hold("EVENT_ID_INVALID_OR_MISSING")
    if event != "LOCAL_EVENT_NOT_OBSERVED" and (
        event != outbox["forestWriteState"].replace("FOREST_", "LOCAL_", 1)
    ):
        _hold("LOCAL_OUTBOX_EVENT_AND_ATTEMPT_CONTRADICT")
    if (outbox["forestWriteState"] == "FOREST_RESERVED" and
            event != "LOCAL_EVENT_NOT_OBSERVED"):
        _hold("RESERVED_CANNOT_HAVE_TERMINAL_EVENT")
    # Match the actual reviewed B4e output contract by constructing ONLY
    # required fields; never copy injected issuer, owner, body or authority.
    b4e_view = {
        "schema": L.LOCAL_SCHEMA,
        "attemptId": outbox["attemptId"],
        "sessionId": outbox["sessionId"],
        "forestWriteState": outbox["forestWriteState"],
        "c5Settlement": "UNKNOWN_HOLD",
        "c5EvidenceAuthenticated": False,
        "terminalReceiptAuthenticated": False,
        "safeToRetryInference": False,
        "safeToReleaseRevocation": False,
        "productionAuthority": False,
    }
    return b4e_view, event


def compare_untrusted_b4f_event_and_v1_fixture(
    b4f_local_outbox: dict,
    v1_fixture_diagnostic: dict,
    original_v1_intent_wire: bytes,
) -> dict:
    """Read-only equality check, NO protected receipt reconciliation.

    In particular, LOCAL_EVENT_NOT_OBSERVED is ambiguous for an originally
    uninstrumented attempt vs a lost event. Do not guess that the writer
    aborted. A matching local event+V1 fixture can be restored/forged together.
    """
    local, event = _local_view(b4f_local_outbox)
    try:
        base = L.compare_untrusted_local_with_v1_claim(
            local, v1_fixture_diagnostic, original_v1_intent_wire
        )
    except L.RecoveryComparisonHold as exc:
        raise B4fC5Hold(
            "FOREST_B4F_C5_UNKNOWN_HOLD // V1_OR_ORIGINAL_ATTEMPT_MISMATCH"
        ) from exc
    if event == "LOCAL_EVENT_NOT_OBSERVED":
        # Missing cannot be classified as legacy or corruption without a
        # separately durable, trusted 'instrumented at reserve' provenance.
        reason = "EXPECTED_EVENT_UNKNOWN_LEGACY_OR_MISSING_HOLD"
    elif base["localAndSignedClaimsConflict"]:
        reason = "LOCAL_B4F_EVENT_AND_V1_CLAIM_CONFLICT_HOLD"
    else:
        reason = "EVENT_AND_SIGNED_CLAIM_MATCH_BUT_NOT_AUTHENTICATED_HOLD"
    return {
        "schema": SCHEMA,
        "status": STATUS_HOLD,
        "reason": reason,
        "localTerminalObservationUntrusted": event,
        "claimedTerminalOutcomeUntrusted": base["signedWriterTerminalClaimUntrusted"],
        "localAndSignedClaimsConflict": base["localAndSignedClaimsConflict"],
        "localEventIdIsOnlyUntrustedCorrelation": True,
        "independentB4fWriterCustodyAvailable": False,
        "safeActions": [],
        **dict(NO_AUTHORITY),
    }
