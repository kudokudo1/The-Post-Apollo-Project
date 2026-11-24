#!/usr/bin/env python3
"""DOC 3 Forest C5 // separate provisional disclosure INTENT, NEVER a permit.

Source-only, uninstalled reference for Forest Core and ForestW. The candidate
and original COMMIT v1 wire are supplied by the caller, without trusted
signer/issuer, independent original writer, active seat or revocation state.

No candidate can authorize streamed output. The only DELTA gate discards it.
"""
from __future__ import annotations

import hashlib
from types import MappingProxyType

from services.connections.forest import ForestC5SignedEvidencePreflight as S
from services.connections.forest import ForestC5ExactSessionV1Preflight as V

SCHEMA = "postapollo.forest.provisional-disclosure-intent.candidate-v0"
AUDIENCE = "postapollo.forest.provisional-disclosure.candidate-v0"
PHASE = "DISCLOSE_PROVISIONAL"
RESULT_SCHEMA = "postapollo.forest.c5-disclosure-candidate-deny.v0"
MAX_CANDIDATE_LEASE_MS = 300000  # Structural cap, NOT permission duration.
MAX_CANDIDATE_BYTES = 16000  # Matches B1 MAX_BODY at review; NOT an enforced stream quota.
FIELDS = frozenset((
    "schema", "audience", "phase", "action", "commitIntentSha256",
    "principal", "tree", "sessionId", "userTurn", "attempt", "model",
    "revision", "consentEpoch",
    "disclosureRequest", "disclosureCandidateId", "disclosureNonce",
    "disclosureEpoch",
    "recipientInstance", "recipientReleaseSha256", "recipientSeatEpoch",
    "maxBytes", "issuedAtMs", "expiresAtMs",
))
BOUND_FIELDS = frozenset((
    "principal", "tree", "sessionId", "userTurn", "attempt",
    "model", "revision", "consentEpoch",
))
NO_AUTHORITY = MappingProxyType({
    **dict(V.NO_AUTHORITY),
    "c5ProvisionalDisclosurePermitIssued": False,
    "c5ProvisionalDisclosureRecipientAuthenticated": False,
    "c5ProvisionalDisclosureCurrentRevocationVerified": False,
    "c5ProvisionalDisclosureLeaseAuthenticated": False,
    "c5ProvisionalDisclosureBudgetEnforced": False,
    "safeToEmitProvisionalText": False,
    "safeToCommitForestReply": False,
})


class DisclosureHold(ValueError):
    """Fixed diagnostic only; no prompts, tokens, identifiers or keys in errors."""


def _hold(code: str) -> None:
    raise DisclosureHold("FOREST_C5_PROVISIONAL_DISCLOSURE_HOLD // " + code)


def _integer(value: object, name: str, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value < 2**63:
        _hold("INVALID_" + name)


def _ident(value: object, name: str) -> None:
    if type(value) is not str or S.IDENTIFIER.fullmatch(value) is None:
        _hold("INVALID_" + name)


def _candidate(candidate_wire: object, original_v1_intent_wire: object,
               now_ms: int) -> tuple[dict, str]:
    _integer(now_ms, "CURRENT_TIME", minimum=1)
    try:
        original, original_digest = V._intent(original_v1_intent_wire)
    except (V.V1Hold, TypeError):
        original = None
    # Raise after the handler so decoder exceptions cannot escape as causes
    # or implicit contexts (JSONDecodeError.doc / UnicodeError.object).
    if original is None:
        _hold("INVALID_ORIGINAL_COMMIT_INTENT")
    try:
        candidate = S._parse_exact(candidate_wire, FIELDS)
    except S.EvidenceHold:
        candidate = None
    if candidate is None:
        _hold("INVALID_CANDIDATE_WIRE")
    if (candidate["schema"] != SCHEMA or candidate["audience"] != AUDIENCE
            or candidate["phase"] != PHASE or candidate["action"] != PHASE):
        _hold("WRONG_DISCLOSURE_DOMAIN_OR_ACTION")
    if candidate["commitIntentSha256"] != original_digest:
        _hold("PARENT_COMMIT_INTENT_MISMATCH")
    # A signature-bearing COMMIT_GENERATE grant never substitutes for
    # an independently issued disclosure grant, even when all data matches.
    for field in BOUND_FIELDS:
        if (type(candidate[field]) is not type(original[field]) or
                candidate[field] != original[field]):
            _hold("ORIGINAL_SCOPE_MISMATCH_" + field)
    for name in (
        "disclosureRequest", "disclosureCandidateId", "disclosureNonce",
        "recipientInstance",
    ):
        _ident(candidate[name], name)
    # Separate disclosure correlation is distinct from existing commit
    # grant/request/challenge AND from other disclosure identifiers.
    distinct = (
        candidate["disclosureRequest"],
        candidate["disclosureCandidateId"],
        candidate["disclosureNonce"],
        original["request"],
        original["grant"],
        original["challenge"],
    )
    if len(set(distinct)) != len(distinct):
        _hold("COMMIT_AND_DISCLOSURE_IDENTIFIERS_MUST_BE_DISTINCT")
    if (type(candidate["recipientReleaseSha256"]) is not str or
            S.HEX64.fullmatch(candidate["recipientReleaseSha256"]) is None):
        _hold("INVALID_RECIPIENT_RELEASE")
    for name in (
        "disclosureEpoch", "recipientSeatEpoch", "maxBytes",
        "issuedAtMs", "expiresAtMs",
    ):
        _integer(candidate[name], name, minimum=1)
    if candidate["maxBytes"] > MAX_CANDIDATE_BYTES:
        _hold("UNBOUNDED_CANDIDATE_OUTPUT")
    if (candidate["expiresAtMs"] <= candidate["issuedAtMs"] or
            candidate["expiresAtMs"] - candidate["issuedAtMs"] >
            MAX_CANDIDATE_LEASE_MS):
        _hold("INVALID_CANDIDATE_LEASE")
    if not (original["issuedAtMs"] <= candidate["issuedAtMs"]
            < candidate["expiresAtMs"] <= original["expiresAtMs"]):
        _hold("DISCLOSURE_CANNOT_EXTEND_ORIGINAL_COMMIT_LEASE")
    if not candidate["issuedAtMs"] <= now_ms < candidate["expiresAtMs"]:
        _hold("CANDIDATE_NOT_CURRENT")
    # No issuer, reviewer, recipient, revocation epoch, delivery-sink or
    # active seat is authenticated by this structural check.
    return candidate, hashlib.sha256(candidate_wire).hexdigest()


def inspect_untrusted_disclosure_candidate(
    candidate_wire: bytes, original_v1_intent_wire: bytes, *, now_ms: int
) -> dict:
    """Inspect shape+intent equality only, with no grant or disclosure."""
    _, digest = _candidate(candidate_wire, original_v1_intent_wire, now_ms)
    return {
        "schema": RESULT_SCHEMA,
        "status": "CANDIDATE_MATCHES_ORIGINAL_SCOPE_NO_PROTECTED_PERMISSION_HOLD",
        "candidateSha256Untrusted": digest,
        "bothWiresCallerControlled": True,
        "safeActions": [],
        **dict(NO_AUTHORITY),
    }


def block_provisional_delta(
    candidate_wire: bytes, original_v1_intent_wire: bytes,
    event: dict, *, now_ms: int
) -> dict:
    """Demonstrate a drop-only sink boundary. Never return DELTA text.

    The actual Forest B3 generator may already have yielded these bytes to
    its direct caller. A future trusted host must gate BEFORE external
    disclosure and serialize revocation with in-flight output. This test
    reference is NOT a production release/cancellation implementation.
    """
    _candidate(candidate_wire, original_v1_intent_wire, now_ms)
    # Bound the existing drop-only shape before comparing untrusted keys or
    # event tags. No custom Python equality is needed to refuse an event.
    if (type(event) is not dict or len(event) != 3 or
            any(type(key) is not str for key in event) or
            set(event) != {"event", "text", "provisional"} or
            type(event["event"]) is not str or event["event"] != "DELTA" or
            event["provisional"] is not True or
            type(event["text"]) is not str or not event["text"]):
        _hold("ONLY_UNTRUSTED_PROVISIONAL_DELTA_IS_INSPECTABLE")
    # Every valid UTF-8 code point occupies at least one byte. Reject
    # obviously oversized strings before allocating their encoded copy.
    if len(event["text"]) > MAX_CANDIDATE_BYTES:
        _hold("DELTA_EXCEEDS_ABSOLUTE_SOURCE_CAP")
    try:
        size = len(event["text"].encode("utf-8"))
    except UnicodeError:
        size = None
    if size is None:
        _hold("INVALID_DELTA_ENCODING")
    if size > MAX_CANDIDATE_BYTES:
        _hold("DELTA_EXCEEDS_ABSOLUTE_SOURCE_CAP")
    # Even a valid candidate does not establish authentication or enforce
    # cumulative stream budget. No bytes, event body or issuance escapes.
    return {
        "schema": RESULT_SCHEMA,
        "status": "UNTRUSTED_DELTA_SUPPRESSED_NO_C5_DISCLOSURE_PERMISSION_HOLD",
        "emitEvent": None,
        "emittedBytes": 0,
        "safeActions": [],
        **dict(NO_AUTHORITY),
    }
