#!/usr/bin/env python3
"""Forest C5 v1 exact-session intent/receipt fixture checks, NEVER authority.

All signer keys, claimed B3 binding, permit, journal predecessor and counter
floor come from the caller. A valid signature, even on sessionId, does not
prove a protected original Forest DB row, enrolled writer or SQLite COMMIT.
This module is NOT installed, and every returned authority flag is False.
"""
from __future__ import annotations

import hashlib
from types import MappingProxyType

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from services.connections.forest import ForestC5SignedEvidencePreflight as S
from services.connections.forest import ForestC5TerminalReceiptPreflight as R
from services.connections.forest import ForestC5AuthorityBoundary as A

INTENT_SCHEMA_V1 = "postapollo.forest.commit-intent.v1"
ROLE_SCHEMA_V1 = "postapollo.forest.signed-role-evidence.v1"
RECEIPT_SCHEMA_V1 = "postapollo.forest.commit-terminal-receipt.v1"
RESULT_SCHEMA = "postapollo.forest.unenrolled-session-commit-consistency.v1"
INTENT_FIELDS = S.INTENT_FIELDS | frozenset(("sessionId",))
ROLE_FIELDS = S.RECORD_FIELDS
RECEIPT_FIELDS = R.RECEIPT_FIELDS | frozenset(("sessionId",))
# Keep role/audience distinct from any C3e Sign-In, Hospital or TimeW grant.
NO_AUTHORITY = MappingProxyType({
    **A.NO_AUTHORITY,
    "v1SignerRootsIndependentlyEnrolled": False,
    "v1SessionFromOriginalWriterAuthenticated": False,
    "v1WriterTerminalOutcomeProven": False,
    "v1IndependentJournalFloorVerified": False,
    "v1NativeRevocationAndDisclosureVerified": False,
})


class V1Hold(ValueError):
    """Do not use signed fixture consistency to grant protected operations."""


def _hold(reason: str) -> None:
    raise V1Hold("FOREST_C5_V1_UNENROLLED_HOLD // " + reason)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse(wire: bytes, fields: frozenset[str], name: str) -> dict:
    try:
        return S._parse_exact(wire, fields)
    except S.EvidenceHold:
        pass
    # Do not retain the rejected wire in a nested parser exception.
    _hold("INVALID_" + name)


def _id(value: object, name: str) -> None:
    if type(value) is not str or S.IDENTIFIER.fullmatch(value) is None:
        _hold("INVALID_" + name)


def _digest(value: object, name: str) -> None:
    if type(value) is not str or S.HEX64.fullmatch(value) is None:
        _hold("INVALID_" + name)


def _int(value: object, name: str, minimum: int = 0) -> None:
    if type(value) is not int or not minimum <= value < 2**63:
        _hold("INVALID_" + name)


def _public(key: object, signature: object, name: str) -> str:
    if type(key) is not bytes or len(key) != 32:
        _hold("INVALID_" + name + "_PUBLIC_KEY")
    if type(signature) is not bytes or len(signature) != 64:
        _hold("INVALID_" + name + "_SIGNATURE")
    return _sha(key)


def _signature(key: bytes, signature: bytes, wire: bytes, name: str) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(signature, wire)
    except (InvalidSignature, ValueError):
        pass
    else:
        return
    _hold("INVALID_" + name + "_SIGNATURE")


def _intent(wire: bytes) -> tuple[dict, str]:
    intent = _parse(wire, INTENT_FIELDS, "V1_INTENT")
    if (intent["schema"] != INTENT_SCHEMA_V1 or
            intent["audience"] != S.AUDIENCE or
            intent["phase"] != "COMMIT_GENERATE" or
            intent["action"] != "GENERATE"):
        _hold("V1_INTENT_WRONG_DOMAIN_OR_PHASE")
    for name in ("principal", "tree", "sessionId", "userTurn", "attempt",
                 "request", "grant", "challenge"):
        _id(intent[name], name)
    if type(intent["model"]) is not str or S.MODEL.fullmatch(intent["model"]) is None:
        _hold("INVALID_MODEL")
    for name in ("requesterReleaseSha256", "commitHostReleaseSha256"):
        _digest(intent[name], name)
    for name in ("revision", "requesterUid"):
        _int(intent[name], name)
    for name in ("consentEpoch", "requesterPid", "requesterStartTicks",
                 "seatEpoch", "issuedAtMs", "expiresAtMs"):
        _int(intent[name], name, 1)
    # This is historical receipt INSPECTION, not permission to execute now.
    if (intent["expiresAtMs"] <= intent["issuedAtMs"] or
            intent["expiresAtMs"] - intent["issuedAtMs"] > S.MAX_LEASE_MS):
        _hold("INVALID_OR_UNBOUNDED_ORIGINAL_LEASE")
    return intent, _sha(wire)


def _role(wire: bytes, role: str, decision: str, public_digest: str,
          intent: dict, intent_digest: str) -> None:
    record = _parse(wire, ROLE_FIELDS, "V1_ROLE")
    if (record["schema"] != ROLE_SCHEMA_V1 or
            record["audience"] != S.AUDIENCE or
            record["role"] != role or record["decision"] != decision):
        _hold("V1_ROLE_WRONG_DOMAIN")
    if (record["intentSha256"] != intent_digest or
            record["signerKeySha256"] != public_digest or
            record["consentEpoch"] != intent["consentEpoch"] or
            type(record["consentEpoch"]) is not int or
            record["challenge"] != intent["challenge"]):
        _hold("V1_ROLE_INTENT_OR_KEY_MISMATCH")


def _binding(intent: dict, candidate: object) -> None:
    if (type(candidate) is not dict
            or len(candidate) != len(A.BINDING_FIELDS)
            or any(type(key) is not str for key in candidate)
            or set(candidate) != A.BINDING_FIELDS):
        _hold("EXACT_FOREST_B4C_BINDING_REQUIRED")
    fields = {
        "owner_key": "principal",
        "tree_key": "tree",
        "session_id": "sessionId",
        "user_turn_id": "userTurn",
        "attempt_id": "attempt",
        "request_id": "request",
        "model_key": "model",
        "expected_revision": "revision",
    }
    for name, signed in fields.items():
        actual, expected = candidate[name], intent[signed]
        # Plain scalar type must precede equality: a caller object can
        # otherwise execute custom comparison code even on a refusal path.
        if type(actual) is not type(expected) or actual != expected:
            _hold("V1_SESSION_OR_ATTEMPT_BINDING_MISMATCH_" + name)
    # Request ID grammar comes from B4a/B4c, not from the general v0 ID.
    if not 16 <= len(candidate["request_id"]) <= 96:
        _hold("V1_B4C_REQUEST_ID_INVALID")
    # This remains a caller-supplied reproduction, not an authenticated B3 DB.
    for name in fields:
        if name in ("model_key", "expected_revision"):
            continue
        _id(candidate[name], name)


def _receipt(wire: bytes, intent: dict, intent_digest: str,
             writer_pin: str, predecessor: str, counter_floor: int) -> dict:
    value = _parse(wire, RECEIPT_FIELDS, "V1_RECEIPT")
    if (value["schema"] != RECEIPT_SCHEMA_V1 or
            value["audience"] != S.AUDIENCE or
            value["role"] != R.WRITER_ROLE):
        _hold("V1_RECEIPT_WRONG_DOMAIN")
    if type(value["terminalOutcome"]) is not str or value["terminalOutcome"] not in R.TERMINAL_OUTCOMES:
        _hold("V1_RECEIPT_NOT_A_TERMINAL_OUTCOME")
    for name in ("permitId", "attempt", "grant", "request", "principal",
                 "tree", "sessionId", "challenge", "storageTxnId"):
        _id(value[name], name)
    if type(value["model"]) is not str or S.MODEL.fullmatch(value["model"]) is None:
        _hold("V1_RECEIPT_INVALID_MODEL")
    for name in ("intentSha256", "commitHostReleaseSha256",
                 "writerKeySha256", "previousJournalSha256"):
        _digest(value[name], name)
    for name in ("revision", "recordedAtMs"):
        _int(value[name], name)
    for name in ("consentEpoch", "writerJournalCounter"):
        _int(value[name], name, 1)
    required = {
        "intentSha256": intent_digest, "attempt": intent["attempt"],
        "grant": intent["grant"], "request": intent["request"],
        "principal": intent["principal"], "tree": intent["tree"],
        "sessionId": intent["sessionId"], "model": intent["model"],
        "revision": intent["revision"],
        "consentEpoch": intent["consentEpoch"],
        "challenge": intent["challenge"],
        "commitHostReleaseSha256": intent["commitHostReleaseSha256"],
        "writerKeySha256": writer_pin,
        "previousJournalSha256": predecessor,
    }
    for name, wanted in required.items():
        if value[name] != wanted or type(value[name]) is not type(wanted):
            _hold("V1_RECEIPT_BINDING_MISMATCH_" + name)
    if (value["writerJournalCounter"] <= counter_floor or
            value["recordedAtMs"] < intent["issuedAtMs"]):
        _hold("V1_UNTRUSTED_JOURNAL_FLOOR_OR_TIME_MISMATCH")
    return value


def inspect_unenrolled_v1_claims(
    intent_wire: bytes, forest_binding: dict,
    requester_record: bytes, requester_signature: bytes, requester_public: bytes,
    reviewer_record: bytes, reviewer_signature: bytes, reviewer_public: bytes,
    receipt_wire: bytes, writer_signature: bytes, writer_public: bytes,
    *, claimed_previous_journal_sha256: str,
    claimed_minimum_journal_counter: int,
) -> dict:
    """Compare 3 signed caller-controlled fixture roles to exact session v1.

    This is strictly for offline contract evaluation. No protected issuer,
    original Forest writer/journal, actual SQLite proof or independent trusted
    signer enrollment exists. Never settle UNKNOWN_HOLD with the result.
    """
    _digest(claimed_previous_journal_sha256, "CLAIMED_JOURNAL_PREDECESSOR")
    _int(claimed_minimum_journal_counter, "CLAIMED_JOURNAL_FLOOR")
    intent, intent_digest = _intent(intent_wire)
    _binding(intent, forest_binding)
    r_pin = _public(requester_public, requester_signature, "REQUESTER")
    v_pin = _public(reviewer_public, reviewer_signature, "REVIEWER")
    w_pin = _public(writer_public, writer_signature, "WRITER")
    if len({requester_public, reviewer_public, writer_public}) != 3:
        _hold("V1_THREE_DISTINCT_ROLE_KEYS_REQUIRED")
    _role(requester_record, S.SOURCE_ROLE, "SOURCE_FIXTURE", r_pin, intent, intent_digest)
    _role(reviewer_record, S.REVIEW_ROLE, "REVIEW_FIXTURE", v_pin, intent, intent_digest)
    terminal = _receipt(
        receipt_wire, intent, intent_digest, w_pin,
        claimed_previous_journal_sha256, claimed_minimum_journal_counter,
    )
    _signature(requester_public, requester_signature, requester_record, "REQUESTER")
    _signature(reviewer_public, reviewer_signature, reviewer_record, "REVIEWER")
    _signature(writer_public, writer_signature, receipt_wire, "WRITER")
    return {
        "schema": RESULT_SCHEMA,
        "status": "V1_SESSION_BOUND_FIXTURE_CONSISTENT_NOT_AUTHENTICATED",
        "claimedSessionIdUntrusted": intent["sessionId"],
        "claimedIntentSha256Untrusted": intent_digest,
        "claimedReceiptSha256Untrusted": _sha(receipt_wire),
        "claimedTerminalOutcomeUntrusted": terminal["terminalOutcome"],
        "claimedWriterJournalCounterUntrusted": terminal["writerJournalCounter"],
        "claimedForestBindingCallerControlled": True,
        "claimedSignerKeysAndJournalCallerControlled": True,
        "safeActions": [],
        **dict(NO_AUTHORITY),
    }
