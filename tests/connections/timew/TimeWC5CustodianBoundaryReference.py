"""DOC 5 TimeW C5 provider-neutral recovery probe (TEST FIXTURE ONLY).

No actual installed custodian is connected. Every provider response and every
"last seen" head is caller-supplied and UNTRUSTED. This module neither verifies
signatures, establishes independent freshness, approves a human, nor issues,
spends, signs, retries, moves, resizes or authorizes anything. Every returned
result retains a permanent production/native HOLD.
"""
from __future__ import annotations

import re

from TimeWC5SpendFenceReference import (
    ACTION, AUDIENCE, MAX_MS, _claim,
)

SCHEMA = "postapollo.connections.c5.timew.custodian-probe-fixture.v1"
SOURCE_MODES = frozenset(("LOCAL_DEVELOPMENT", "INDEPENDENT_CANDIDATE"))
LEDGER_STATES = frozenset(("ACTIVE", "SPENT", "REVOKED", "UNKNOWN"))
JOURNAL_STAGES = frozenset(("PREPARED", "DISPATCHING", "UNCERTAIN",
                            "FIXTURE_COMPLETE"))
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
EVIDENCE_FIELDS = frozenset((
    "schema", "source_mode", "audience", "action", "grant_id",
    "operation_id", "selection_sha256", "intent_sha256", "source_sha256",
    "session_id", "seat_id", "issuer_epoch", "ledger_state",
    "head_sha256", "sequence", "terminal_receipt_sha256",
))
HEAD_FIELDS = frozenset(("head_sha256", "sequence"))


def hold(reason):
    """Never return positive authorization or a native action, even on success."""
    return {
        "diagnostic": reason,
        "production_authorized": False,
        "native_action_allowed": False,
        "human_consent_verified": False,
        "external_custody_verified": False,
        "revocation_acknowledged": False,
        "retry_allowed": False,
        "undo_allowed": False,
        "safe_actions": [],
    }


def _head_shape(observation):
    if not isinstance(observation, dict) or set(observation) != HEAD_FIELDS:
        return False
    head, seq = observation["head_sha256"], observation["sequence"]
    return (type(head) is str and HEX.fullmatch(head) is not None
            and type(seq) is int and 1 <= seq <= MAX_MS)


def reconcile_fixture(*, provider, claim, journal_stage, now_ms, last_seen=None):
    """Call a test-only read provider at most ONCE; never produce permission.

    There is no provider fallback. Input/provider-origin evidence is not pinned,
    and a matching fake terminal receipt is NOT native SwayPX evidence.
    """
    original = _claim(claim)  # Reuse merged C5 fixture's strict exact claim.
    if (type(journal_stage) is not str
            or journal_stage not in JOURNAL_STAGES):
        return hold("INVALID_JOURNAL_STAGE_HOLD")
    if type(now_ms) is not int or not 0 <= now_ms <= MAX_MS:
        return hold("INVALID_CLOCK_HOLD")
    if not original["issued_ms"] <= now_ms < original["expires_ms"]:
        return hold("EXPIRED_OR_NOT_YET_VALID_HOLD")
    if last_seen is not None and not _head_shape(last_seen):
        return hold("INVALID_PRIOR_HEAD_HOLD")
    if not callable(provider):
        return hold("PROVIDER_UNAVAILABLE_UNKNOWN_HOLD")

    query = {
        "audience": AUDIENCE,
        "action": ACTION,
        "grant_id": original["grant_id"],
        "operation_id": original["operation_id"],
    }
    try:
        evidence = provider(dict(query))
    except Exception:
        # An outage or lost response must not select a local SQLite fallback.
        return hold("PROVIDER_UNAVAILABLE_UNKNOWN_HOLD")

    if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_FIELDS:
        return hold("MALFORMED_PROVIDER_RESPONSE_HOLD")
    if (evidence["schema"] != SCHEMA
            or type(evidence["source_mode"]) is not str
            or evidence["source_mode"] not in SOURCE_MODES
            or type(evidence["ledger_state"]) is not str
            or evidence["ledger_state"] not in LEDGER_STATES
            or not _head_shape({k: evidence[k] for k in HEAD_FIELDS})):
        return hold("MALFORMED_PROVIDER_RESPONSE_HOLD")
    receipt = evidence["terminal_receipt_sha256"]
    if receipt is not None and (type(receipt) is not str
                                or HEX.fullmatch(receipt) is None):
        return hold("MALFORMED_PROVIDER_RESPONSE_HOLD")

    # Claimed terminal results from the wrong request, signer epoch or audience
    # cannot be reconciled, even when they appear internally well-formed.
    if (evidence["audience"] != AUDIENCE or evidence["action"] != ACTION
            or any(evidence[k] != original[k] for k in (
                "grant_id", "operation_id", "selection_sha256",
                "intent_sha256", "source_sha256", "session_id",
                "seat_id", "issuer_epoch"))):
        return hold("MISMATCHED_PURPOSE_OR_INTENT_HOLD")

    if last_seen is not None:
        previous_seq, previous_head = (last_seen["sequence"],
                                       last_seen["head_sha256"])
        current_seq, current_head = (evidence["sequence"],
                                     evidence["head_sha256"])
        if current_seq < previous_seq:
            return hold("OBSERVED_HISTORY_ROLLBACK_HOLD")
        if current_seq == previous_seq and current_head != previous_head:
            return hold("OBSERVED_HISTORY_FORK_HOLD")
        if current_seq > previous_seq and current_head == previous_head:
            return hold("INCONSISTENT_HEAD_ADVANCEMENT_HOLD")

    if evidence["source_mode"] == "LOCAL_DEVELOPMENT":
        return hold("LOCAL_ROLLBACKABLE_HISTORY_HOLD")

    # An external-candidate label and caller-provided "current" head are NOT
    # independent root/role enrollment or trusted terminal-receipt verification.
    state = evidence["ledger_state"]
    if state == "REVOKED":
        return hold("REVOKED_FIXTURE_HOLD")
    if state == "UNKNOWN":
        return hold("CUSTODIAN_UNKNOWN_HOLD")
    if state == "ACTIVE":
        if journal_stage != "PREPARED":
            return hold("LOCAL_DISPATCH_WITHOUT_PROVEN_SPEND_UNKNOWN_HOLD")
        return hold("UNSPENT_UNTRUSTED_FIXTURE_HOLD")
    if journal_stage == "PREPARED":
        return hold("SPENT_BUT_LOCAL_PREPARED_UNKNOWN_HOLD")
    if journal_stage == "FIXTURE_COMPLETE":
        return hold("SPENT_BUT_NATIVE_TERMINAL_UNVERIFIED_HOLD")
    return hold("SPENT_NATIVE_OUTCOME_UNKNOWN_HOLD")
