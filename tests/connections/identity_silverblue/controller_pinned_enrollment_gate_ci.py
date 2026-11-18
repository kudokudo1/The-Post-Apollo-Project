#!/usr/bin/env python3
"""C4b: require an out-of-guest pinned enrollment root for receipt-key claims.

This is a CI-only *verification contract*, NOT a release key provisioning tool.
The previously merged controller challenge verifier checks a signed BEGIN
denial with a key supplied by the guest. Here a separate Ed25519 enrollment
signature must authorize that exact key, release hash, version and role
BEFORE the response is checked using the enrolled key.

All test roots and certificate inputs are disposable caller-owned fixtures.
Production enrollment, host/seat attestation, protected floor storage,
revocation distribution, C5 consent and sign-in remain disabled.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import verify_controller_challenge_ci as V

SCHEMA = "postapollo.identity.c4b.controller-enrollment.ci-v1"
DOMAIN = b"postapollo.identity.c4b.controller-enrollment.ci-v1\x00"
ROLE = "postapollo.identity.silverblue-ci-gateway"
UNIT = "post-apollo-identity-silverblue-ci.service"
PACKAGE = "post-apollo-identity-silverblue-ci"
AUDIENCE = "protected-connections-c3e-ci-only"
SCOPE = "signed-denial-diagnostic-only"
HEX = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[0-9a-f]{32}\Z")
# Match protected C3e-AF's established host identity shape. This is a
# controller-pinned NAME, not evidence of the real computer's identity.
HOST = re.compile(r"postapollo-identity-ci@[a-z0-9][a-z0-9-]{2,63}\Z")
FIELDS = frozenset((
    "schema", "role", "package", "unit", "audience", "scope",
    "enrollmentId", "hostId", "releaseSha256", "receiptKeySha256",
    "releaseEpoch", "releaseSequence",
))
MAX_ENROLLMENT = 1536
NEGATIVE = {
    "operatorEnrollmentRootCustodyVerified": False,
    "externalEnrollmentAuthorizedForProduction": False,
    "independentHostKernelAttestationVerified": False,
    "independentSeatAndPeerVerified": False,
    "externallyProtectedRevocationLedgerVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """Source or independently pinned enrollment proof not trustworthy."""

def _deny(reason: str):
    raise Refused(reason)

def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _deny("C4B_ENROLLMENT_DUPLICATE_FIELD_REFUSED")
        result[key] = value
    return result

def canonical(record: dict) -> bytes:
    if type(record) is not dict:
        _deny("C4B_ENROLLMENT_EXPECTED_RECORD_REQUIRED")
    try:
        return json.dumps(
            record, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise Refused("C4B_ENROLLMENT_UNENCODABLE_RECORD") from exc

def _read_signed_record(raw: bytes) -> dict:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_ENROLLMENT:
        _deny("C4B_ENROLLMENT_FRAME_BOUNDS")
    try:
        record = json.loads(
            raw.decode("ascii"), object_pairs_hook=_unique,
            parse_constant=lambda _: _deny("C4B_ENROLLMENT_NONFINITE_NUMBER"),
        )
    except (UnicodeError, ValueError, RecursionError, TypeError) as exc:
        raise Refused("C4B_ENROLLMENT_JSON_REFUSED") from exc
    if type(record) is not dict or set(record) != FIELDS or canonical(record) != raw:
        _deny("C4B_ENROLLMENT_EXACT_CANONICAL_SCHEMA_REQUIRED")
    if (record["schema"] != SCHEMA or record["role"] != ROLE or
            record["package"] != PACKAGE or record["unit"] != UNIT or
            record["audience"] != AUDIENCE or record["scope"] != SCOPE or
            type(record["enrollmentId"]) is not str or
            IDENT.fullmatch(record["enrollmentId"]) is None or
            type(record["hostId"]) is not str or
            HOST.fullmatch(record["hostId"]) is None or
            any(type(record[k]) is not str or HEX.fullmatch(record[k]) is None
                for k in ("releaseSha256", "receiptKeySha256")) or
            any(type(record[k]) is not int or not 0 < record[k] < 2**53
                for k in ("releaseEpoch", "releaseSequence"))):
        _deny("C4B_ENROLLMENT_INVALID_SOURCE_ROLE_OR_VERSION")
    return record

def inspect_enrolled_controller_challenge_ci_only(
    *, serial: bytes, controller_challenge: str,
    signed_enrollment: bytes, enrollment_signature: bytes,
    independently_pinned_controller_root: Ed25519PublicKey,
    independently_pinned_release_sha256: str,
    independently_pinned_host_id: str,
    minimum_release_epoch: int, minimum_release_sequence: int,
    revoked_enrollment_ids: tuple,
):
    """Refuse guest self-key claims without a separate signed pinned identity.

    The root, source digest, minimum release floor and revocation list MUST
    come from independent controller ownership, never UART/guest self-report.
    This function cannot prove that source provenance or custody by itself.
    """
    if not isinstance(independently_pinned_controller_root, Ed25519PublicKey):
        _deny("C4B_ENROLLMENT_INDEPENDENT_CONTROLLER_ROOT_REQUIRED")
    if (type(enrollment_signature) is not bytes or len(enrollment_signature) != 64 or
            type(independently_pinned_release_sha256) is not str or
            HEX.fullmatch(independently_pinned_release_sha256) is None or
            type(independently_pinned_host_id) is not str or
            HOST.fullmatch(independently_pinned_host_id) is None or
            type(minimum_release_epoch) is not int or
            type(minimum_release_sequence) is not int or
            not 0 < minimum_release_epoch < 2**53 or
            not 0 < minimum_release_sequence < 2**53 or
            type(revoked_enrollment_ids) is not tuple or
            any(type(x) is not str or IDENT.fullmatch(x) is None
                for x in revoked_enrollment_ids) or
            len(set(revoked_enrollment_ids)) != len(revoked_enrollment_ids)):
        _deny("C4B_ENROLLMENT_EXACT_CONTROLLER_PINS_REQUIRED")
    record = _read_signed_record(signed_enrollment)
    try:
        independently_pinned_controller_root.verify(
            enrollment_signature, DOMAIN + signed_enrollment,
        )
    except InvalidSignature as exc:
        raise Refused("C4B_ENROLLMENT_SIGNATURE_UNTRUSTED") from exc
    if not hmac.compare_digest(record["hostId"], independently_pinned_host_id):
        _deny("C4B_ENROLLMENT_WRONG_CONTROLLER_PINNED_HOST")
    if (not hmac.compare_digest(
            record["releaseSha256"], independently_pinned_release_sha256,
        ) or (record["releaseEpoch"], record["releaseSequence"]) <
                (minimum_release_epoch, minimum_release_sequence)):
        _deny("C4B_ENROLLMENT_WRONG_RELEASE_OR_ROLLBACK")
    if record["enrollmentId"] in revoked_enrollment_ids:
        _deny("C4B_ENROLLMENT_EXPLICITLY_REVOKED")
    # The guest supplies a public key in its proof, but it cannot define what
    # the controller enrolled. Compare its hash to the signed controller
    # certificate BEFORE using any Ed25519 receipt signature.
    try:
        guest_public_raw, frame = V._proof_bytes(serial)
    except V.Refused as exc:
        raise Refused("C4B_ENROLLMENT_GUEST_PROOF_REFUSED") from exc
    if not hmac.compare_digest(
        hashlib.sha256(guest_public_raw).hexdigest(),
        record["receiptKeySha256"],
    ):
        _deny("C4B_ENROLLMENT_GUEST_KEY_NOT_CONTROLLER_PINNED")
    controller_public_raw = independently_pinned_controller_root.public_bytes(
        Encoding.Raw, PublicFormat.Raw,
    )
    if hmac.compare_digest(controller_public_raw, guest_public_raw):
        _deny("C4B_ENROLLMENT_ROOT_MUST_NOT_BE_GATEWAY_SIGNER")
    # Existing verifier must check BEGIN, UNAVAILABLE, exact controller
    # nonce and the Ed25519 signature. By this point, its guest public key
    # has been independently pinned by a controller-root-signed certificate.
    try:
        response = V.inspect_ci_only(
            serial=serial, controller_challenge=controller_challenge,
        )
    except V.Refused as exc:
        raise Refused("C4B_ENROLLMENT_SIGNED_CONTROLLER_NONCE_REFUSED") from exc
    if (response.get("freshControllerNonceInActualSignedBeginDenialInCI") is not True
            or response.get("publicKeyVerifiedOnlyForThisCIReceipt") is not True
            or response.get("runtimePublicKeySha256") !=
               record["receiptKeySha256"]
            or any(response.get(k) is not False for k in V.NEGATIVE)):
        _deny("C4B_ENROLLMENT_RESPONSE_AUTHORITY_PROMOTION_REFUSED")
    return {
        "schema": SCHEMA,
        "ciControllerRootSignatureAndSourcePinsMatch": True,
        "receiptSignerMatchesControllerSignedEnrollmentInCI": True,
        "signedDenialMatchesFreshControllerNonceInCI": True,
        "enrollmentId": record["enrollmentId"],
        "hostId": record["hostId"],
        "releaseEpoch": record["releaseEpoch"],
        "releaseSequence": record["releaseSequence"],
        "releaseSha256": record["releaseSha256"],
        "receiptKeySha256": record["receiptKeySha256"],
        **NEGATIVE,
    }
