#!/usr/bin/env python3
"""DOC 3 // UNTRUSTED native disclosure handoff fixture, never authority.

This is a pure, source-only cross-owner contract probe. Three records are
CALLER-SUPPLIED: their syntax and equality do not attest an issuer, recipient
process, original Forest writer, current revocation or actual output delivery.

There is deliberately NO successful token-release path and NO signing key,
socket, ledger, clock source, model execution or system actuation.
"""
from __future__ import annotations

import hashlib
from types import MappingProxyType

from services.connections.forest import ForestC5SignedEvidencePreflight as S
from services.connections.forest import ForestC5ProvisionalDisclosurePreflight as D
from services.connections.forest import ForestC5ExactSessionV1Preflight as V

ISSUER_SCHEMA = "postapollo.forest.c5-disclosure-issuer-handoff.fixture-v0"
RECIPIENT_SCHEMA = "postapollo.forest.c5-disclosure-recipient-handoff.fixture-v0"
REVOCATION_SCHEMA = "postapollo.forest.c5-disclosure-revocation-handoff.fixture-v0"
RESULT_SCHEMA = "postapollo.forest.c5-native-disclosure-handoff-deny.v0"
HANDOFF_AUDIENCE = "postapollo.forest.c5-disclosure-handoff.fixture-v0"
ISSUER_FIELDS = frozenset((
    "schema", "audience", "action", "candidateSha256", "commitIntentSha256",
    "permitId", "issuerInstance", "issuerReleaseSha256", "issuerEpoch",
    "consentEpoch", "disclosureEpoch", "oneUseGeneration",
    "revocationGeneration", "recipientInstance", "recipientReleaseSha256",
    "recipientSeatEpoch", "maxBytes", "issuedAtMs", "expiresAtMs",
))
RECIPIENT_FIELDS = frozenset((
    "schema", "audience", "issuerInstance", "permitId", "recipientInstance",
    "recipientReleaseSha256", "recipientSeatEpoch", "processPid",
    "processStartTicks", "processUid", "hostBootId", "peerEvidenceDigest",
))
REVOCATION_FIELDS = frozenset((
    "schema", "audience", "issuerInstance", "permitId", "issuerEpoch",
    "oneUseGeneration", "revocationGeneration", "state",
    "claimedEmittedBytes", "highestChunkSequence", "drainedChunkSequence",
    "inFlightSends", "observedAtMs",
))
NO_AUTHORITY = MappingProxyType({
    **dict(D.NO_AUTHORITY),
    "issuerHandoffAuthenticated": False,
    "recipientNativeProcessAuthenticated": False,
    "nativePeerAndSeatIndependentlyVerified": False,
    "issuerOneUseCounterDurable": False,
    "revocationOrderingIndependentlyVerified": False,
    "allInFlightOutputDrained": False,
    "protectedTerminalReceiptAuthenticated": False,
})


class HandoffHold(ValueError):
    """Fixed error codes; do not echo the user's input or provisional text."""


def _hold(code: str) -> None:
    raise HandoffHold("FOREST_C5_NATIVE_HANDOFF_UNKNOWN_HOLD // " + code)


def _parse(wire: bytes, fields: frozenset[str], schema: str, label: str) -> dict:
    try:
        value = S._parse_exact(wire, fields)
    except S.EvidenceHold:
        value = None
    # Do not propagate raw parser exception objects through public refusals.
    if value is None:
        _hold("INVALID_" + label + "_WIRE")
    if value["schema"] != schema or value["audience"] != HANDOFF_AUDIENCE:
        _hold(label + "_DOMAIN_MISMATCH")
    return value


def _id(value: object, name: str) -> None:
    if type(value) is not str or S.IDENTIFIER.fullmatch(value) is None:
        _hold("INVALID_" + name)


def _sha(value: object, name: str) -> None:
    if type(value) is not str or S.HEX64.fullmatch(value) is None:
        _hold("INVALID_" + name)


def _num(value: object, name: str, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value < 2**63:
        _hold("INVALID_" + name)


def inspect_untrusted_native_handoff_fixture(
    candidate_wire: bytes, original_v1_intent_wire: bytes,
    claimed_issuer_wire: bytes, claimed_recipient_wire: bytes,
    claimed_revocation_wire: bytes, *, now_ms: int,
) -> dict:
    """Validate proposed record shape and equality, but NEVER issue a permit.

    The installed host must instead obtain these facts over an authenticated
    local channel with an independently trusted issuer and process identity.
    In particular, any 'revoked and drained' assertion in input is untrusted.
    """
    try:
        candidate, candidate_digest = D._candidate(
            candidate_wire, original_v1_intent_wire, now_ms)
        original, original_digest = V._intent(original_v1_intent_wire)
    except (D.DisclosureHold, V.V1Hold, TypeError):
        candidate = None
    if candidate is None:
        _hold("ORIGINAL_CANDIDATE_INVALID")
    issuer = _parse(claimed_issuer_wire, ISSUER_FIELDS, ISSUER_SCHEMA, "ISSUER")
    recipient = _parse(
        claimed_recipient_wire, RECIPIENT_FIELDS, RECIPIENT_SCHEMA, "RECIPIENT")
    revocation = _parse(
        claimed_revocation_wire, REVOCATION_FIELDS, REVOCATION_SCHEMA,
        "REVOCATION")

    if issuer["action"] != D.PHASE:
        _hold("COMMIT_PERMISSION_CANNOT_BECOME_DISCLOSURE")
    for key in ("permitId", "issuerInstance"):
        _id(issuer[key], "ISSUER_" + key)
    _sha(issuer["candidateSha256"], "CANDIDATE_DIGEST")
    _sha(issuer["commitIntentSha256"], "COMMIT_DIGEST")
    _sha(issuer["issuerReleaseSha256"], "ISSUER_RELEASE")
    _sha(issuer["recipientReleaseSha256"], "RECIPIENT_RELEASE")
    for key in ("issuerEpoch", "consentEpoch", "disclosureEpoch",
                "oneUseGeneration", "revocationGeneration", "maxBytes",
                "issuedAtMs", "expiresAtMs", "recipientSeatEpoch"):
        _num(issuer[key], "ISSUER_" + key, 1)
    for key in ("recipientInstance",):
        _id(issuer[key], "ISSUER_" + key)
    if issuer["permitId"] in (
        original["grant"], original["request"], original["challenge"],
        candidate["disclosureRequest"], candidate["disclosureCandidateId"],
        candidate["disclosureNonce"],
    ):
        _hold("PERMIT_ID_REUSES_REQUEST_OR_COMMIT_GRANT")
    if (issuer["candidateSha256"] != candidate_digest or
            issuer["commitIntentSha256"] != original_digest or
            issuer["consentEpoch"] != candidate["consentEpoch"] or
            issuer["disclosureEpoch"] != candidate["disclosureEpoch"]):
        _hold("ISSUER_CANDIDATE_OR_ORIGINAL_INTENT_MISMATCH")
    for key in ("recipientInstance", "recipientReleaseSha256",
                "recipientSeatEpoch", "maxBytes"):
        if issuer[key] != candidate[key] or type(issuer[key]) is not type(candidate[key]):
            _hold("ISSUER_RECIPIENT_OR_BUDGET_SCOPE_MISMATCH")
    if not (candidate["issuedAtMs"] <= issuer["issuedAtMs"]
            < issuer["expiresAtMs"] <= candidate["expiresAtMs"]):
        _hold("ISSUER_CANNOT_EXTEND_DISCLOSURE_CANDIDATE_LEASE")
    if not issuer["issuedAtMs"] <= now_ms < issuer["expiresAtMs"]:
        _hold("ISSUER_FIXTURE_TIME_NOT_CURRENT")

    for key in ("issuerInstance", "permitId", "recipientInstance"):
        _id(recipient[key], "RECIPIENT_" + key)
    _sha(recipient["recipientReleaseSha256"], "RECIPIENT_RELEASE")
    _sha(recipient["peerEvidenceDigest"], "PEER_EVIDENCE")
    _id(recipient["hostBootId"], "RECIPIENT_BOOT")
    for key in ("recipientSeatEpoch", "processPid", "processStartTicks"):
        _num(recipient[key], "RECIPIENT_" + key, 1)
    _num(recipient["processUid"], "RECIPIENT_PROCESS_UID")
    for key in ("issuerInstance", "permitId", "recipientInstance",
                "recipientReleaseSha256", "recipientSeatEpoch"):
        if recipient[key] != issuer[key] or type(recipient[key]) is not type(issuer[key]):
            _hold("RECIPIENT_CLAIM_MISMATCH_" + key)
    # A self-reported peerEvidenceDigest, pid, seat or boot ID is NOT
    # kernel witness, enrollment, active foreground seat, or recipient proof.

    for key in ("issuerInstance", "permitId"):
        _id(revocation[key], "REVOCATION_" + key)
    for key in ("issuerEpoch", "oneUseGeneration", "revocationGeneration",
                "claimedEmittedBytes", "highestChunkSequence",
                "drainedChunkSequence", "inFlightSends", "observedAtMs"):
        _num(revocation[key], "REVOCATION_" + key)
    for key in ("issuerInstance", "permitId", "issuerEpoch", "oneUseGeneration"):
        if revocation[key] != issuer[key] or type(revocation[key]) is not type(issuer[key]):
            _hold("REVOCATION_CLAIM_MISMATCH_" + key)
    if revocation["claimedEmittedBytes"] > issuer["maxBytes"]:
        _hold("CLAIMED_STREAM_EXCEEDS_BOUND")
    if revocation["drainedChunkSequence"] > revocation["highestChunkSequence"]:
        _hold("IMPOSSIBLE_DRAIN_SEQUENCE")
    if revocation["observedAtMs"] < issuer["issuedAtMs"]:
        _hold("REVOCATION_OBSERVATION_BEFORE_ISSUANCE")
    if revocation["state"] not in ("ACTIVE", "REVOKING", "REVOKED"):
        _hold("INVALID_REVOCATION_STATE")
    if revocation["state"] == "ACTIVE":
        if revocation["revocationGeneration"] != issuer["revocationGeneration"]:
            _hold("ACTIVE_WITH_CHANGED_REVOCATION_GENERATION")
    elif revocation["revocationGeneration"] <= issuer["revocationGeneration"]:
        _hold("REVOCATION_WITHOUT_ADVANCING_GENERATION")
    if revocation["state"] == "REVOKED":
        if (revocation["inFlightSends"] != 0 or
                revocation["drainedChunkSequence"] !=
                revocation["highestChunkSequence"]):
            _hold("REVOKED_ACK_CLAIMS_IN_FLIGHT_OUTPUT")
    # Even a fully consistent fixture including "REVOKED" with zero claimed
    # in-flight sends never proves a real kernel send has drained.
    return {
        "schema": RESULT_SCHEMA,
        "status": "THREE_UNTRUSTED_NATIVE_HANDOFF_CLAIMS_UNKNOWN_HOLD",
        "claimedRevocationStateUntrusted": revocation["state"],
        "claimedScopeStructurallyConsistent": True,
        "claimedIssuerRecipientRevocationCallerControlled": True,
        "safeActions": [],
        "emitEvent": None,
        "emittedBytes": 0,
        **dict(NO_AUTHORITY),
    }
