#!/usr/bin/env python3
"""Connections/Hospital: proposed RECOVER query, strictly CI-only and deny-only.

A lost staffing COMMIT reply is UNKNOWN unless an independently enrolled
protected Hospital writer can prove its original atomic outcome. This module
only correlates untrusted caller-provided PREPARE/PREPARED/COMMIT fixture bytes
with a caller-provided fresh-looking challenge. It does not create a secure
challenge, send a packet, query a database, authenticate a result, or retry.
"""
from __future__ import annotations

import base64
import hashlib
import re
import uuid

import StaffingReceiptIdentityPreflight as Receipt
import StaffingTransportPreflight as Transport

SCHEMA = "postapollo.connections.hospital.staffing-recover-query.ci-v1"
KIND = "recover-original-commit-not-a-new-commit"
PROTOCOL_VERSION = 1
MAX_QUERY_LEASE_MS = 5000  # CI fixture bound; NOT approved native duration.
MAX_CLOCK = 9007199254740991
MAX_ID = 128
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
FIELDS = frozenset((
    "schema", "kind", "protocolVersion", "originalRequestSchema",
    "requestNonce", "roomId", "action", "sessionId",
    "writerInstance", "expectedRevision", "graphDigest",
    "grantDigest", "grantNonce", "approvalId", "reviewDigest",
    "originalScopeSha256", "originalPrepareSha256", "preparedSha256",
    "commitSha256", "queryId", "challengeB64", "issuedMs", "expiresMs",
))
DENIED = {
    "recoveryProtocolAcceptedByHospital": False,
    "challengeIndependentlyIssued": False,
    "challengeReplayProtected": False,
    "originalSignedGrantVerified": False,
    "writerOriginAuthenticated": False,
    "writerReleaseEnrolled": False,
    "writerReceiptAuthenticated": False,
    "durableCommitOutcomeVerified": False,
    "durableRefusalFenceVerified": False,
    "hospitalWriterRecoveryEndpointAvailable": False,
    "c5HumanConsentVerified": False,
    "canSendRecoveryQuery": False,
    "canReplayCommit": False,
    "canRetryWithSameGrant": False,
    "canAttachSession": False,
    "canSucceedDoctor": False,
    "productionAuthority": False,
}


class RecoveryQueryHold(ValueError):
    pass


def _hold(reason):
    raise RecoveryQueryHold("CONNECTIONS_HOSPITAL_RECOVER_QUERY_HOLD // " + reason)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _time(v):
    if type(v) is not int or not 0 <= v <= MAX_CLOCK:
        _hold("INVALID_QUERY_TIME")
    return v


def _uuid(v):
    if type(v) is not str or len(v) != 36:
        _hold("INVALID_QUERY_ID")
    try:
        parsed = uuid.UUID(v)
    except (ValueError, TypeError, AttributeError):
        _hold("INVALID_QUERY_ID")
    if parsed.version != 4 or str(parsed) != v:
        _hold("INVALID_QUERY_ID")
    return v


def _challenge(v):
    if type(v) is not bytes or len(v) != 32:
        _hold("UNTRUSTED_CHALLENGE_LENGTH")
    return base64.urlsafe_b64encode(v).rstrip(b"=").decode("ascii")


def _context(original_prepare_raw, prepared_raw, commit_raw):
    try:
        original, prepared, commit, digest, session_id = Receipt._source_context(
            original_prepare_raw, prepared_raw, commit_raw)
        envelope_raw = Transport._decode_b64(
            commit["signedEnvelope"],
            len(base64.urlsafe_b64decode(
                commit["signedEnvelope"] + "=" * (-len(commit["signedEnvelope"]) % 4))))
        envelope = Transport._exact_json(envelope_raw, Transport.MAX_GRANT_BYTES)
        body = envelope["body"]
        grant_nonce = body["nonce"]
        Transport._decode_b64(grant_nonce, 32)
        approval_id = body["approvalId"]
        review_digest = body["reviewDigest"]
        if (type(approval_id) is not str or not 1 <= len(approval_id) <= MAX_ID
                or not approval_id.isascii()
                or any(ord(c) < 33 or ord(c) > 126 for c in approval_id)
                or type(review_digest) is not str
                or not HEX.fullmatch(review_digest)):
            _hold("INVALID_GRANT_REFERENCE")
        return original, prepared, digest, session_id, grant_nonce, approval_id, review_digest
    except RecoveryQueryHold:
        raise
    except (Receipt.ReceiptHold, Transport.PreflightHold, TypeError,
            KeyError, IndexError, ValueError, OverflowError) as exc:
        raise RecoveryQueryHold(
            "CONNECTIONS_HOSPITAL_RECOVER_QUERY_HOLD // INVALID_ORIGINAL_SOURCE"
        ) from exc


def candidate_query_ci_only(
        *, original_prepare_raw: bytes, prepared_raw: bytes,
        commit_raw: bytes, query_id: str, challenge: bytes,
        issued_ms: int, expires_ms: int, now_ms: int):
    """Build one test-only query's bytes. Even valid bytes cannot be sent."""
    now, issued, expires = _time(now_ms), _time(issued_ms), _time(expires_ms)
    _uuid(query_id)
    challenge_b64 = _challenge(challenge)
    if (not issued <= now < expires
            or not 0 < expires - issued <= MAX_QUERY_LEASE_MS):
        _hold("QUERY_STALE_OR_UNBOUNDED")
    original, prepared, grant_digest, session_id, nonce, approval, review = (
        _context(original_prepare_raw, prepared_raw, commit_raw))
    request = {
        "schema": SCHEMA, "kind": KIND, "protocolVersion": PROTOCOL_VERSION,
        "originalRequestSchema": Receipt.REQUEST_SCHEMA,
        "requestNonce": original["requestNonce"],
        "roomId": original["roomId"], "action": original["action"],
        "sessionId": session_id, "writerInstance": prepared["writerInstance"],
        "expectedRevision": prepared["expectedRevision"],
        "graphDigest": prepared["expectedDigest"],
        "grantDigest": grant_digest, "grantNonce": nonce,
        "approvalId": approval, "reviewDigest": review,
        "originalScopeSha256": _digest(Transport.canonical(original["intent"])),
        "originalPrepareSha256": _digest(original_prepare_raw),
        "preparedSha256": _digest(prepared_raw),
        "commitSha256": _digest(commit_raw),
        "queryId": query_id, "challengeB64": challenge_b64,
        "issuedMs": issued, "expiresMs": expires,
    }
    try:
        raw = Transport.canonical(request)
        Transport.frame_budget(raw)
    except Transport.PreflightHold as exc:
        raise RecoveryQueryHold(
            "CONNECTIONS_HOSPITAL_RECOVER_QUERY_HOLD // QUERY_FRAME_NOT_BOUNDED"
        ) from exc
    return {"candidateQueryRawForTestOnly": raw,
            "candidateSha256ForTestOnly": _digest(raw),
            "status": "UNTRUSTED_RECOVERY_QUERY_SHAPE_ONLY",
            "originalCommitOutcome": "UNKNOWN",
            "noSameGrantRetryEverFromThisObservation": True,
            **DENIED}


def inspect_candidate_query_ci_only(
        *, candidate_query_raw: bytes, original_prepare_raw: bytes,
        prepared_raw: bytes, commit_raw: bytes, now_ms: int):
    """Compare immutable original operation to exact proposed query fields."""
    try:
        candidate = Transport._exact_json(candidate_query_raw,
                                           Transport.MAX_FRAME)
    except Transport.PreflightHold as exc:
        raise RecoveryQueryHold(
            "CONNECTIONS_HOSPITAL_RECOVER_QUERY_HOLD // INVALID_QUERY_FRAME"
        ) from exc
    if set(candidate) != FIELDS:
        _hold("QUERY_FIELDS_CHANGED")
    try:
        challenge = Transport._decode_b64(candidate["challengeB64"], 32)
    except Transport.PreflightHold as exc:
        raise RecoveryQueryHold(
            "CONNECTIONS_HOSPITAL_RECOVER_QUERY_HOLD // INVALID_QUERY_CHALLENGE"
        ) from exc
    expected = candidate_query_ci_only(
        original_prepare_raw=original_prepare_raw,
        prepared_raw=prepared_raw, commit_raw=commit_raw,
        query_id=candidate["queryId"], challenge=challenge,
        issued_ms=candidate["issuedMs"], expires_ms=candidate["expiresMs"],
        now_ms=now_ms)
    if candidate_query_raw != expected["candidateQueryRawForTestOnly"]:
        _hold("QUERY_PROTOCOL_OR_ORIGINAL_IDENTITY_CHANGED")
    return {
        "status": "UNTRUSTED_RECOVERY_QUERY_IDENTITY_MATCH_ONLY",
        "candidateSha256ForTestOnly": _digest(candidate_query_raw),
        "originalCommitOutcome": "UNKNOWN",
        "noSameGrantRetryEverFromThisObservation": True,
        **DENIED,
    }


def run_native_staffing_recover_query(*_args, **_kwargs):
    _hold("NATIVE_RECOVERY_REQUEST_NOT_APPROVED_OR_INSTALLED")
