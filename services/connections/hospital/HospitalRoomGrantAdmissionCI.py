#!/usr/bin/env python3
"""Hospital Room Trash/Restore: Connections-side signed grant admission CI contract.

This module is NOT an issuer and deliberately has no signing code, private
key, key generation, CLI, socket or native activation path. It cross-checks
PX v12's already-signed one-use grant against an exact Hospital operation,
source Room review and separately supplied CI host/operator/seat pins.

A caller-provided root or observation is never independently trusted. The
positive flags describe test consistency ONLY, not native authentication,
operator consent, protected database storage or permission to mutate a Room.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

SCHEMA = "postapollo.connections.hospital-room-grant-admission.ci-v1"
REQUEST_SCHEMA = "postapollo.connections.hospital-room-request.ci-v1"
PX_SCHEMA = "post-apollo.hospital.room-lifecycle-grant.v1"
PX_AUDIENCE = "px-hospital-room-lifecycle-v12"
PX_DOMAIN = b"post-apollo.hospital.room-lifecycle-grant.v1\x00"
HOSPITAL_SCOPES = {
    "TRASH": "postapollo.connections.hospital.room-trash.v1",
    "RESTORE": "postapollo.connections.hospital.room-restore.v1",
}
REQUEST_FIELDS = frozenset((
    "schema", "scope", "action", "roomId", "patientId", "repository",
    "expectedRevision", "expectedDigest", "requestNonce",
))
PX_FIELDS = frozenset((
    "schema", "audience", "action", "roomId", "patientId", "repository",
    "expectedRevision", "expectedDigest", "operatorId", "approvalId",
    "seatId", "hostId", "retentionApproved", "nonce", "issuedAt", "expiresAt",
))
ROOM = re.compile(r"[A-Za-z0-9._:/-]{1,160}\Z", re.ASCII)
OPERATOR = re.compile(r"[A-Za-z0-9_.:@/-]{1,96}\Z", re.ASCII)
APPROVAL = re.compile(r"[A-Za-z0-9_-]{12,128}\Z", re.ASCII)
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
BASE64_NONCE = re.compile(r"[A-Za-z0-9_-]{43}\Z", re.ASCII)
BASE64_SIGNATURE = re.compile(r"[A-Za-z0-9_-]{86}\Z", re.ASCII)

NEGATIVE = {
    "installedNativeIssuerAuthenticated": False,
    "independentlyProtectedIssuerRootVerified": False,
    "independentKernelCallerIdentityVerified": False,
    "independentActiveSeatVerified": False,
    "realHumanConsentAuthenticated": False,
    "independentRetentionLegalHoldEvaluationVerified": False,
    "protectedPxWriterAndDatabaseVerified": False,
    "protectedRevocationAndRollbackHistoryVerified": False,
    "operatorC5HospitalPermissionGranted": False,
    "roomTrashAuthorized": False,
    "roomRestoreAuthorized": False,
    "hostAuthenticated": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """A signed PX grant does not agree with exact Hospital CI scope."""

def _deny(code: str):
    raise Refused("C5H_HOLD // " + code)

def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            _deny("DUPLICATE_JSON_FIELD")
        out[key] = value
    return out

def canonical(value):
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("ascii")
    except (UnicodeError, ValueError, OverflowError, TypeError, RecursionError):
        _deny("CANONICAL_ENCODING_REFUSED")

def _strict(raw, limit, fields, label):
    if type(raw) is not bytes or not 2 <= len(raw) <= limit:
        _deny(label + "_BOUNDS_REFUSED")
    try:
        value = json.loads(
            raw.decode("ascii"), object_pairs_hook=_unique,
            parse_constant=lambda _: _deny("NONFINITE_JSON_REFUSED"),
        )
        if (type(value) is not dict or set(value) != fields
                or raw != canonical(value)):
            _deny(label + "_NONCANONICAL_OR_FIELDS_REFUSED")
        return value
    except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise Refused("C5H_HOLD // " + label + "_JSON_REFUSED") from exc

def _unb64(value, chars, raw_len):
    if type(value) is not str or chars.fullmatch(value) is None:
        _deny("BASE64_FORMAT_REFUSED")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise Refused("C5H_HOLD // BASE64_REFUSED") from exc
    if (len(raw) != raw_len
            or base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value):
        _deny("NONCANONICAL_BASE64_REFUSED")
    return raw

def _positive_review(review, request):
    # PX read-only review never grants operator authority. Both marker fields
    # stay false/true respectively even when the Room is eligible.
    if (type(review) is not dict
            or review.get("operatorAuthenticated") is not False
            or review.get("requiresOwnerReview") is not True
            or type(review.get("blockers")) is not list
            or review["blockers"] != []
            or review.get("roomId") != request["roomId"]
            or type(review.get("revision")) is not int
            or review["revision"] != request["expectedRevision"]
            or review.get("digest") != request["expectedDigest"]):
        _deny("PX_READ_ONLY_REVIEW_DIFFERENT_OR_MISREPRESENTED")
    action = request["action"]
    if action == "TRASH":
        if (review.get("state") != "ACTIVE"
                or review.get("canTrash") is not True
                or review.get("canRestore") is not False):
            _deny("PX_ROOM_TRASH_NOT_ELIGIBLE")
    elif action == "RESTORE":
        if (review.get("state") != "TRASHED"
                or review.get("canRestore") is not True
                or review.get("canTrash") is not False):
            _deny("PX_ROOM_RESTORE_NOT_ELIGIBLE")

def _validate_fields(doc, action, *, now):
    if (doc["schema"] != PX_SCHEMA or doc["audience"] != PX_AUDIENCE
            or doc["action"] != action
            or type(doc["roomId"]) is not str or ROOM.fullmatch(doc["roomId"]) is None
            or any(type(doc[field]) is not str
                   or OPERATOR.fullmatch(doc[field]) is None
                   for field in ("patientId", "operatorId"))
            or any(type(doc[field]) is not str
                   or APPROVAL.fullmatch(doc[field]) is None
                   for field in ("approvalId", "seatId", "hostId"))
            or type(doc["repository"]) is not str
            or not 1 <= len(doc["repository"]) <= 256
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in doc["repository"])
            or type(doc["expectedRevision"]) is not int
            or not 0 <= doc["expectedRevision"] < 1_000_000_000
            or type(doc["expectedDigest"]) is not str
            or HEX64.fullmatch(doc["expectedDigest"]) is None
            or doc["retentionApproved"] is not True
            or type(doc["issuedAt"]) is not int
            or type(doc["expiresAt"]) is not int
            or not 0 < doc["expiresAt"] - doc["issuedAt"] <= 60
            or doc["issuedAt"] > now + 3 or doc["expiresAt"] <= now):
        _deny("PX_SIGNED_GRANT_FIELDS_OR_TIME_REFUSED")
    _unb64(doc["nonce"], BASE64_NONCE, 32)

def inspect_signed_hospital_grant_ci_only(
    *, request_bytes: bytes, px_review: dict,
    signed_px_grant_bytes: bytes,
    separately_pinned_px_issuer_public: Ed25519PublicKey,
    independently_expected_patient_id: str,
    independently_expected_repository: str,
    independently_expected_operator_id: str,
    independently_expected_seat_id: str,
    independently_expected_host_id: str,
    now: int | None = None,
):
    """Return strict CI consistency diagnostics, never an authority token.

    All independently_* inputs are controlled by the disposable caller.
    Production MUST obtain these from a protected native issuer + writer,
    not QML, the Room record, a guest, a fixture or this result. There is no
    production signing/export function in this module.
    """
    if not isinstance(separately_pinned_px_issuer_public, Ed25519PublicKey):
        _deny("SEPARATE_ISSUER_PUBLIC_ROOT_REQUIRED")
    if type(now) is not int and now is not None:
        _deny("TEST_CLOCK_REFUSED")
    tick = int(time.time()) if now is None else now
    request = _strict(request_bytes, 4096, REQUEST_FIELDS, "HOSPITAL_REQUEST")
    action = request["action"]
    if (type(action) is not str or action not in HOSPITAL_SCOPES
            or request["schema"] != REQUEST_SCHEMA
            or request["scope"] != HOSPITAL_SCOPES[action]
            or type(request["roomId"]) is not str
            or ROOM.fullmatch(request["roomId"]) is None
            or type(request["expectedRevision"]) is not int
            or not 0 <= request["expectedRevision"] < 1_000_000_000
            or type(request["expectedDigest"]) is not str
            or HEX64.fullmatch(request["expectedDigest"]) is None):
        _deny("HOSPITAL_SCOPE_OR_ROOM_REFUSED")
    _unb64(request["requestNonce"], BASE64_NONCE, 32)
    for key, expected in (
        ("patientId", independently_expected_patient_id),
        ("repository", independently_expected_repository),
    ):
        if type(expected) is not str or request[key] != expected:
            _deny("INDEPENDENT_SOURCE_IDENTITY_REQUIRED")
    _positive_review(px_review, request)

    # PX's signed envelope has body/signature. Require canonical exact bytes
    # and Ed25519 under caller-chosen CI public root; never mint grants.
    envelope = _strict(signed_px_grant_bytes, 4096,
                       frozenset({"body", "signature"}), "PX_ENVELOPE")
    body = envelope["body"]
    if type(body) is not dict or set(body) != PX_FIELDS:
        _deny("PX_EXACT_SIGNED_FIELDS_REQUIRED")
    _validate_fields(body, action, now=tick)
    sig = _unb64(envelope["signature"], BASE64_SIGNATURE, 64)
    try:
        separately_pinned_px_issuer_public.verify(sig, PX_DOMAIN + canonical(body))
    except (InvalidSignature, ValueError) as exc:
        raise Refused("C5H_HOLD // PX_ED25519_SIGNATURE_UNTRUSTED") from exc

    for field, request_field in (
        ("roomId", "roomId"), ("patientId", "patientId"),
        ("repository", "repository"), ("expectedRevision", "expectedRevision"),
        ("expectedDigest", "expectedDigest"), ("nonce", "requestNonce"),
    ):
        if body[field] != request[request_field]:
            _deny("SIGNED_" + field.upper() + "_REQUEST_MISMATCH")
    for key, expected in (
        ("operatorId", independently_expected_operator_id),
        ("seatId", independently_expected_seat_id),
        ("hostId", independently_expected_host_id),
    ):
        if (type(expected) is not str or
                not hmac.compare_digest(body[key], expected)):
            _deny("SIGNED_" + key.upper() + "_PIN_MISMATCH")
    # A TASKS scope or a UI confirmation has no accepted conversion into a
    # Hospital permission. This function cannot create one by returning True.
    return {
        "schema": SCHEMA,
        "scope": request["scope"],
        "ciSignedHospitalRoomGrantMatchesSourceAndRequest": True,
        "ciPXVerifierDomainAndKeyMatched": True,
        "requestSha256": hashlib.sha256(request_bytes).hexdigest(),
        "signedGrantSha256": hashlib.sha256(signed_px_grant_bytes).hexdigest(),
        "issuerPublicSha256": hashlib.sha256(
            separately_pinned_px_issuer_public.public_bytes(
                Encoding.Raw, PublicFormat.Raw)).hexdigest(),
        **NEGATIVE,
    }
