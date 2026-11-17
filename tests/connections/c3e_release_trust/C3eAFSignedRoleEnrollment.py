#!/usr/bin/env python3
"""C3e-AF: sign the three C3e-Z verifier key roles before CI consumption.

This is a TEST-ONLY composition: the independent enrollment root is supplied
by the disposable CI caller, not an operator/HSM/remote authority. A passing
signature proves key-role consistency under THAT test root; it never grants
installed host, replay/issuer custody, consent, credentials or sign-in.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "c3eaf_existing_z", HERE / "C3eZReleaseBoundHostEvidence.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3EAF_REQUIRED_Z_MODULE_MISSING")
Z = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = Z
_spec.loader.exec_module(Z)

SCHEMA = "postapollo.connections.c3eaf-signed-role-enrollment.ci-v1"
PURPOSE = "postapollo.connections.c3eaf-deny-only-ci-key-role-binding"
DOMAIN = b"postapollo.connections.c3eaf-signed-role-enrollment.ci-v1\x00"
HOST = re.compile(r"postapollo-identity-ci@[a-z0-9][a-z0-9-]{2,63}\Z", re.ASCII)
HEX_PUBLIC = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
FIELDS = frozenset((
    "schema", "role", "purpose", "hostId", "releaseEpoch",
    "releaseSequence", "releaseRootPublicHex", "hostWitnessPublicHex",
    "receiptPublicHex",
))
NEGATIVE = {
    "operatorEnrollmentRootCustodyVerified": False,
    "independentProductionHostAttested": False,
    "externalChallengeCustodyVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """A mismatched CI key enrollment or protected evidence is refused."""

def _deny(code):
    raise Refused(code)

def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _deny("C3EAF_DUPLICATE_ENROLLMENT_FIELD")
        result[key] = value
    return result

def _canonical(document):
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")

def _public_bytes(public):
    if not isinstance(public, Ed25519PublicKey):
        _deny("C3EAF_INDEPENDENT_ENROLLMENT_ROOT_REQUIRED")
    return public.public_bytes(Encoding.Raw, PublicFormat.Raw)

def _key_from_hex(raw):
    if type(raw) is not str or HEX_PUBLIC.fullmatch(raw) is None:
        _deny("C3EAF_PUBLIC_KEY_ENCODING_REFUSED")
    try:
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(raw))
    except (TypeError, ValueError) as exc:
        raise Refused("C3EAF_PUBLIC_KEY_INVALID") from exc

def verify_signed_enrollment_ci_only(
    *, enrollment: bytes, signature: bytes,
    independently_pinned_enrollment_root: Ed25519PublicKey,
    expected_host_id: str, expected_release_epoch: int,
    expected_release_sequence: int,
):
    """Return pinned *CI* role keys, not an authenticated production host.

    This function cannot establish where the pinned enrollment root came from.
    The root MUST be selected by a separate trusted owner, not the signer,
    gateway, artifact, local self-report or QML. Disposable CI cannot prove it.
    """
    if (type(enrollment) is not bytes or not 1 <= len(enrollment) <= 4096
            or type(signature) is not bytes or len(signature) != 64):
        _deny("C3EAF_ENROLLMENT_FRAME_BOUNDS_REFUSED")
    root_raw = _public_bytes(independently_pinned_enrollment_root)
    if (type(expected_host_id) is not str
            or HOST.fullmatch(expected_host_id) is None
            or type(expected_release_epoch) is not int
            or not 0 < expected_release_epoch < 2**63
            or type(expected_release_sequence) is not int
            or not 0 < expected_release_sequence < 2**63):
        _deny("C3EAF_INDEPENDENT_HOST_OR_RELEASE_SCOPE_MISSING")
    try:
        doc = json.loads(
            enrollment.decode("ascii"), object_pairs_hook=_unique,
            parse_constant=lambda _: _deny("C3EAF_NONFINITE_JSON_REFUSED"),
        )
    except (UnicodeError, ValueError, TypeError, OverflowError,
            RecursionError) as exc:
        raise Refused("C3EAF_ENROLLMENT_JSON_REFUSED") from exc
    if (type(doc) is not dict or set(doc) != FIELDS
            or _canonical(doc) != enrollment):
        _deny("C3EAF_NONCANONICAL_OR_PARTIAL_ENROLLMENT_REFUSED")
    if (doc["schema"] != SCHEMA or doc["purpose"] != PURPOSE
            or doc["role"] != Z.I.ROLE or doc["hostId"] != expected_host_id
            or type(doc["releaseEpoch"]) is not int
            or doc["releaseEpoch"] != expected_release_epoch
            or type(doc["releaseSequence"]) is not int
            or doc["releaseSequence"] != expected_release_sequence):
        _deny("C3EAF_ENROLLMENT_SCOPE_OR_FLOOR_REFUSED")
    release = _key_from_hex(doc["releaseRootPublicHex"])
    witness = _key_from_hex(doc["hostWitnessPublicHex"])
    receipt = _key_from_hex(doc["receiptPublicHex"])
    roles = (root_raw, _public_bytes(release), _public_bytes(witness),
             _public_bytes(receipt))
    if len(set(roles)) != 4:
        _deny("C3EAF_ENROLLMENT_KEY_ROLE_ALIAS_REFUSED")
    try:
        independently_pinned_enrollment_root.verify(signature, DOMAIN + enrollment)
    except (InvalidSignature, ValueError) as exc:
        raise Refused("C3EAF_ENROLLMENT_SIGNATURE_REFUSED") from exc
    return {
        "release_root": release,
        "witness": witness,
        "receipt": receipt,
        "enrollmentSha256": hashlib.sha256(enrollment).hexdigest(),
    }

def inspect_enrolled_ci_only(
    *, enrollment: bytes, enrollment_signature: bytes,
    independently_pinned_enrollment_root: Ed25519PublicKey,
    expected_host_id: str,
    signed_release: bytes, release_signature: bytes,
    independently_measured_files: dict, independently_measured: dict,
    ledger_root, challenge: bytes, signed_statement: bytes,
    witness_signature: bytes, evidence_line: bytes, signed_receipts,
    expected_release_epoch: int, expected_release_sequence: int,
):
    """Require signed role enrollment BEFORE C3e-Z one-use test challenge.

    This does not add a live host observer or override existing C3e-Z denials.
    A malformed enrollment is rejected before the root-local challenge is
    consumed. An accepted role enrollment is STILL NOT PRODUCTION CUSTODY.
    """
    roles = verify_signed_enrollment_ci_only(
        enrollment=enrollment, signature=enrollment_signature,
        independently_pinned_enrollment_root=independently_pinned_enrollment_root,
        expected_host_id=expected_host_id,
        expected_release_epoch=expected_release_epoch,
        expected_release_sequence=expected_release_sequence,
    )
    try:
        outcome = Z.inspect_release_and_consume(
            signed_release=signed_release,
            release_signature=release_signature,
            independently_pinned_release_root=roles["release_root"],
            independently_measured_files=independently_measured_files,
            ledger_root=ledger_root,
            challenge=challenge,
            signed_statement=signed_statement,
            witness_signature=witness_signature,
            independently_pinned_witness_key=roles["witness"],
            independently_pinned_receipt_key=roles["receipt"],
            evidence_line=evidence_line,
            signed_receipts=signed_receipts,
            independently_measured=independently_measured,
            expected_release_epoch=expected_release_epoch,
            expected_release_sequence=expected_release_sequence,
        )
    except Z.Refused as exc:
        raise Refused("C3EAF_ENROLLED_C3EZ_EVIDENCE_REFUSED") from exc
    if (outcome.get("releaseSourceAndRuntimePinsMatchedInCI") is not True
            or outcome.get("fullRecordChallengeConsumedInRootLocalCI") is not True
            or any(outcome.get(flag) is not False
                   for flag in (*Z.NEGATIVE, *Z.Y.X.NEGATIVE))):
        _deny("C3EAF_PARENT_C3EZ_ATTEMPTED_AUTHORITY_PROMOTION")
    return {
        "schema": SCHEMA,
        "signedRoleEnrollmentMatchesCallerPinInCI": True,
        "releaseAndSignedHostEvidenceBoundToEnrolledRolesInCI": True,
        "oneUseChallengeConsumedInRootLocalCI": True,
        "enrollmentSha256": roles["enrollmentSha256"],
        **Z.NEGATIVE,
        **Z.Y.X.NEGATIVE,
        **NEGATIVE,
    }
