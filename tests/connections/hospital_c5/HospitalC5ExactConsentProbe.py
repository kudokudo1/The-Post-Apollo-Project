#!/usr/bin/env python3
"""C5-H3 source-only *diagnostic* Hospital exact-consent review reference.

No installed native consent agent, operator attestation, protected signer,
private key, challenge custodian or production admission exists here.
Even a perfectly matching claimed display/confirmation ALWAYS denies
human-consent authority. Nothing in the native issuer imports this file.
"""
from __future__ import annotations

import base64
import hashlib
import re

import HospitalNativeIssuerCore as C

REVIEW_SCHEMA = "postapollo.hospital.c5h3.exact-room-review.v1"
CLAIM_SCHEMA = "postapollo.hospital.c5h3.untrusted-display-claim.v1"
DOMAIN = b"postapollo.hospital.c5h3.exact-room-review.v1\x00"
REVIEW_FIELDS = frozenset({
    "schema", "purpose", "action", "roomId", "patientId", "repository",
    "expectedRevision", "expectedDigest", "requestNonce", "operatorUid",
    "seatId", "hostId", "policyGeneration", "issuedAt", "expiresAt",
    "retentionApproved", "legalHold", "originalPreserved", "burnAllowed",
})
CLAIM_FIELDS = frozenset({
    "schema", "reviewDigest", "requestNonce", "action", "roomId",
    "operatorUid", "seatId", "hostId", "agentReleaseDigest",
    "claimedVisible", "claimedConfirmed", "shownAt", "confirmedAt",
})
NONCE = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)


def _valid_nonce(value):
    if type(value) is not str or NONCE.fullmatch(value) is None:
        return False
    try:
        decoded = base64.urlsafe_b64decode(value + "=")
    except (ValueError, TypeError):
        return False
    return (len(decoded) == 32 and
            base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") == value)


def build_review(request, prepared, policy, *, operator_uid, seat_id, host_id, now):
    """Propose exact bytes to be displayed, never certify actual human display.

    Only the independently trusted native issuer may eventually supply the
    source facts. This CI reference has no capability to authenticate the
    caller, policy, active seat, or protected PX writer.
    """
    if (type(request) is not dict or type(prepared) is not dict
            or type(policy) is not dict or type(now) is not int
            or type(operator_uid) is not int or operator_uid <= 0
            or type(seat_id) is not str or C.ID.fullmatch(seat_id) is None
            or type(host_id) is not str or C.SHA.fullmatch(host_id) is None):
        C.deny("C5H3_UNTRUSTED_SOURCE_INPUT")
    if (operator_uid != policy.get("operatorUid")
            or host_id != policy.get("hostId")):
        C.deny("C5H3_OPERATOR_OR_HOST_MISMATCH")
    nonce = prepared.get("requestNonce")
    if not _valid_nonce(nonce):
        C.deny("C5H3_NONCANONICAL_REQUEST_NONCE")
    validated_request = C.validate_request(C.canonical(request))
    state = C.validate_prepared(
        C.canonical(prepared), validated_request, nonce, policy, now
    )
    review = {
        "schema": REVIEW_SCHEMA,
        "purpose": "HOSPITAL_ROOM_" + validated_request["action"],
        "action": validated_request["action"],
        "roomId": state["roomId"],
        "patientId": state["patientId"],
        "repository": state["repository"],
        "expectedRevision": state["expectedRevision"],
        "expectedDigest": state["expectedDigest"],
        "requestNonce": nonce,
        "operatorUid": operator_uid,
        "seatId": seat_id,
        "hostId": host_id,
        "policyGeneration": state["policyGeneration"],
        "issuedAt": now,
        "expiresAt": state["expiresAt"],
        "retentionApproved": True,
        "legalHold": False,
        "originalPreserved": True,
        "burnAllowed": False,
    }
    if set(review) != REVIEW_FIELDS:
        C.deny("C5H3_INCOMPLETE_REVIEW")
    digest = hashlib.sha256(DOMAIN + C.canonical(review)).hexdigest()
    return {"review": review, "reviewDigest": digest}


def inspect_untrusted_claim(reference, claim_raw, *, now):
    """Compare a candidate claim without trusting its producer or approving it.

    Matching fields, a plausible release digest, and claimed button clicks
    are NOT proof of an installed/root-pinned human-consent producer.
    """
    if type(now) is not int or type(reference) is not dict:
        C.deny("C5H3_CLOCK_OR_REFERENCE_UNTRUSTED")
    review = reference.get("review")
    if (type(review) is not dict or set(review) != REVIEW_FIELDS
            or review.get("schema") != REVIEW_SCHEMA
            or type(reference.get("reviewDigest")) is not str):
        C.deny("C5H3_REFERENCE_INCOMPLETE")
    digest = hashlib.sha256(DOMAIN + C.canonical(review)).hexdigest()
    if digest != reference["reviewDigest"]:
        C.deny("C5H3_REFERENCE_CHANGED")
    claim = C.parse_exact(claim_raw, CLAIM_FIELDS, 4096)
    if (claim["schema"] != CLAIM_SCHEMA
            or type(claim["reviewDigest"]) is not str
            or type(claim["requestNonce"]) is not str
            or type(claim["action"]) is not str
            or type(claim["roomId"]) is not str
            or type(claim["operatorUid"]) is not int
            or type(claim["seatId"]) is not str
            or type(claim["hostId"]) is not str
            or type(claim["agentReleaseDigest"]) is not str
            or C.SHA.fullmatch(claim["agentReleaseDigest"]) is None
            or type(claim["claimedVisible"]) is not bool
            or type(claim["claimedConfirmed"]) is not bool
            or type(claim["shownAt"]) is not int
            or type(claim["confirmedAt"]) is not int):
        C.deny("C5H3_CANDIDATE_FIELDS_INVALID")
    matched = (
        claim["reviewDigest"] == digest
        and claim["requestNonce"] == review["requestNonce"]
        and claim["action"] == review["action"]
        and claim["roomId"] == review["roomId"]
        and claim["operatorUid"] == review["operatorUid"]
        and claim["seatId"] == review["seatId"]
        and claim["hostId"] == review["hostId"]
        and claim["claimedVisible"] is True
        and claim["claimedConfirmed"] is True
        and review["issuedAt"] <= claim["shownAt"] <= claim["confirmedAt"] <= now
        and claim["confirmedAt"] < review["expiresAt"]
        and now < review["expiresAt"]
    )
    return {
        "schema": "postapollo.hospital.c5h3.consent-probe-result.v1",
        "status": ("MATCHING_CLAIM_UNTRUSTED_HOLD" if matched
                   else "CHANGED_OR_STALE_CLAIM_HOLD"),
        "claimMatchesReview": matched,
        "externalConsentProducerAuthenticated": False,
        "humanConsentVerified": False,
        "independentHistoryVerified": False,
        "signingAllowed": False,
        "nativeRoomMutationAllowed": False,
        "productionAuthorized": False,
        "safeActions": [],
    }


def production_admission(*_args, **_kwargs):
    """No injected callback/fixture/claim may turn this reference into authority."""
    C.deny("C5H3_INDEPENDENT_HUMAN_CONSENT_UNAVAILABLE")
