#!/usr/bin/env python3
"""Forest B4c // C3e/C5 signed-role evidence consistency, NOT authorization.

Source-only, imported manually by disposable CI tests. This module has NO
production trust root, key custodian, protected seat, human consent, fence
issuer, socket, listener, storage, subprocess, or Forest runtime dependency.

Caller-provided public keys and host-context bytes can be fabricated. Even a
valid Ed25519 signature pair proves only byte consistency with those supplied
keys, NEVER a production grant. Every returned authority bit is hard FALSE.
"""
from __future__ import annotations

import hashlib
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

AUDIENCE = "postapollo.forest.conversation.v1"
INTENT_SCHEMA = "postapollo.forest.commit-intent.v0"
RECORD_SCHEMA = "postapollo.forest.signed-role-evidence.v0"
SOURCE_ROLE = "postapollo.forest.requester.v1"
REVIEW_ROLE = "postapollo.forest.consent-reviewer.v1"
RESULT_SCHEMA = "postapollo.forest.unenrolled-role-consistency.v0"
MAX_WIRE = 4096
MAX_LEASE_MS = 300000
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
IDENTIFIER = re.compile(r"[A-Za-z0-9_-]{1,96}\Z", re.ASCII)
MODEL = re.compile(r"[A-Za-z0-9_./:-]{1,120}\Z", re.ASCII)
INTENT_FIELDS = frozenset((
    "schema", "audience", "phase", "action", "principal", "tree",
    "userTurn", "attempt", "request", "grant", "model", "revision",
    "consentEpoch", "issuedAtMs", "expiresAtMs", "challenge",
    "requesterReleaseSha256", "commitHostReleaseSha256",
    "requesterPid", "requesterStartTicks", "requesterUid", "seatEpoch",
))
RECORD_FIELDS = frozenset((
    "schema", "audience", "role", "decision", "intentSha256",
    "signerKeySha256", "consentEpoch", "challenge",
))
NO_AUTHORITY = {
    "installedRequesterVerified": False,
    "installedCommitHostVerified": False,
    "activeOperatorSeatVerified": False,
    "enrolledIssuerRootVerified": False,
    "independentlyCustodiedHistoryVerified": False,
    "humanConsentVerified": False,
    "c5RevocationFenceGranted": False,
    "forestDatabaseCommitAllowed": False,
    "forestReadSessionAllowed": False,
    "forestToolExecutionAllowed": False,
    "productionAuthority": False,
}


class EvidenceHold(ValueError):
    """Untrusted, unbound, noncanonical, or mismatched evidence."""


def _hold(reason: str) -> None:
    raise EvidenceHold("FOREST_B4C_EVIDENCE_HOLD // " + reason)


def _pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _hold("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def canonical_bytes(value: object) -> bytes:
    if type(value) is not dict:
        _hold("OBJECT_REQUIRED")
    try:
        raw = json.dumps(
            value, ensure_ascii=True, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError, OverflowError) as exc:
        raise EvidenceHold("FOREST_B4C_EVIDENCE_HOLD // INVALID_CANONICAL_JSON") from exc
    if not 0 < len(raw) <= MAX_WIRE:
        _hold("WIRE_BOUNDS")
    return raw


def _parse_exact(wire: object, expected_fields: frozenset[str]) -> dict:
    if type(wire) is not bytes or not 0 < len(wire) <= MAX_WIRE:
        _hold("WIRE_BOUNDS")
    try:
        value = json.loads(
            wire.decode("utf-8"), object_pairs_hook=_pairs_unique,
            parse_constant=lambda _: _hold("JSON_CONSTANT_REFUSED"),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise EvidenceHold("FOREST_B4C_EVIDENCE_HOLD // INVALID_JSON") from exc
    if type(value) is not dict or set(value) != expected_fields:
        _hold("EXACT_FIELDS_REQUIRED")
    if canonical_bytes(value) != wire:
        _hold("NONCANONICAL_JSON")
    return value


def _str_id(value, field):
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        _hold("INVALID_" + field)


def _sha256_lower(value, field):
    if type(value) is not str or HEX64.fullmatch(value) is None:
        _hold("INVALID_" + field)


def _integer(value, field, minimum=0):
    if type(value) is not int or value < minimum or value >= 2**63:
        _hold("INVALID_" + field)


def _intent(wire: bytes, now_ms: int) -> tuple[dict, str]:
    value = _parse_exact(wire, INTENT_FIELDS)
    if (value["schema"] != INTENT_SCHEMA or
            value["audience"] != AUDIENCE or
            value["phase"] != "COMMIT_GENERATE" or
            value["action"] != "GENERATE"):
        _hold("WRONG_SCHEMA_AUDIENCE_OR_PHASE")
    for field in ("principal", "tree", "userTurn", "attempt",
                  "request", "grant", "challenge"):
        _str_id(value[field], field)
    if type(value["model"]) is not str or MODEL.fullmatch(value["model"]) is None:
        _hold("INVALID_MODEL")
    for field in ("requesterReleaseSha256", "commitHostReleaseSha256"):
        _sha256_lower(value[field], field)
    for field in ("revision", "requesterUid"):
        _integer(value[field], field)
    for field in ("consentEpoch", "requesterPid", "requesterStartTicks",
                  "seatEpoch", "issuedAtMs", "expiresAtMs"):
        _integer(value[field], field, minimum=1)
    _integer(now_ms, "CURRENT_TIME")
    if (now_ms < value["issuedAtMs"] or now_ms >= value["expiresAtMs"]
            or value["expiresAtMs"] - value["issuedAtMs"] > MAX_LEASE_MS):
        _hold("EXPIRED_FUTURE_OR_UNBOUNDED_LEASE")
    return value, hashlib.sha256(wire).hexdigest()


def _record(wire: bytes, role: str, decision: str, key_digest: str,
            intent_digest: str, intent: dict) -> None:
    value = _parse_exact(wire, RECORD_FIELDS)
    if (value["schema"] != RECORD_SCHEMA or
            value["audience"] != AUDIENCE or
            value["role"] != role or
            value["decision"] != decision):
        _hold("SIGNED_ROLE_DOMAIN_MISMATCH")
    if (value["intentSha256"] != intent_digest or
            value["signerKeySha256"] != key_digest or
            value["challenge"] != intent["challenge"] or
            type(value["consentEpoch"]) is not int or
            value["consentEpoch"] != intent["consentEpoch"]):
        _hold("SIGNED_INTENT_KEY_OR_EPOCH_MISMATCH")


def verify_unenrolled_role_consistency(
    intent_wire: bytes, requester_record: bytes, requester_signature: bytes,
    requester_public: bytes, reviewer_record: bytes, reviewer_signature: bytes,
    reviewer_public: bytes, *, now_ms: int,
) -> dict:
    """Check exact *fixture* roles, then ALWAYS return NO native authority.

    Public keys come from the caller of this test-only function. A valid
    signature without independent operator-enrolled pin custody is not a
    trusted requester, human reviewer, protected C5 permit or native receipt.
    """
    intent, digest = _intent(intent_wire, now_ms)
    if (type(requester_public) is not bytes or
            type(reviewer_public) is not bytes or
            len(requester_public) != 32 or len(reviewer_public) != 32 or
            requester_public == reviewer_public):
        _hold("DISTINCT_SIGNER_KEYS_REQUIRED")
    if (type(requester_signature) is not bytes or
            type(reviewer_signature) is not bytes or
            len(requester_signature) != 64 or len(reviewer_signature) != 64):
        _hold("SIGNATURE_BOUNDS")
    source_pin = hashlib.sha256(requester_public).hexdigest()
    review_pin = hashlib.sha256(reviewer_public).hexdigest()
    _record(requester_record, SOURCE_ROLE, "SOURCE_FIXTURE",
            source_pin, digest, intent)
    _record(reviewer_record, REVIEW_ROLE, "REVIEW_FIXTURE",
            review_pin, digest, intent)
    try:
        Ed25519PublicKey.from_public_bytes(requester_public).verify(
            requester_signature, requester_record)
        Ed25519PublicKey.from_public_bytes(reviewer_public).verify(
            reviewer_signature, reviewer_record)
    except (InvalidSignature, ValueError) as exc:
        raise EvidenceHold(
            "FOREST_B4C_EVIDENCE_HOLD // SIGNATURE_INVALID") from exc
    return {
        "schema": RESULT_SCHEMA,
        "status": "TWO_SIGNED_ROLES_MATCH_UNENROLLED_FIXTURE",
        "intentSha256ObservedUntrusted": digest,
        "requesterRolePublicKeySha256Untrusted": source_pin,
        "reviewerRolePublicKeySha256Untrusted": review_pin,
        "issuerRolesAreFixtureControlled": True,
        "safeActions": [],
        **NO_AUTHORITY,
    }
