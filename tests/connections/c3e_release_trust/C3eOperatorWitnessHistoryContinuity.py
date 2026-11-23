#!/usr/bin/env python3
"""C3e protected witness-history continuity: signed, read-only CI contract.

Reuses C3e operator signer-enrollment preflight. It checks a SEPARATELY
signed proposed next history head against a caller-pinned previous head and
fresh 32-byte challenge. The verifier NEVER owns the external history,
records a checkpoint, enrolls a key, consumes a nonce or authorizes sign-in.

In CI, the history signer, previous head, challenge and custodian pins are
synthetic caller inputs. A valid signature is NOT rollback-resistant storage.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
import re
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "c3e_history_existing_operator_preflight",
    HERE / "C3eOperatorWitnessEnrollmentPreflight.py",
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3E_HISTORY_EXISTING_PREFLIGHT_REQUIRED")
P = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = P
_spec.loader.exec_module(P)

SCHEMA = "postapollo.connections.c3e-witness-history-continuity.ci-v1"
PURPOSE = "postapollo.connections.external-history-continuity-deny-only-ci"
DOMAIN = b"postapollo.connections.c3e-witness-history-continuity.ci-v1\x00"
STATUS = "C3E_HISTORY_SIGNED_CONTINUITY_FORMAT_VALID_STORAGE_NOT_ATTESTED"
MAX_BYTES = 4096
MAX_SEQUENCE = 2**63 - 1
SHA = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
ENROLLMENT_INPUTS = frozenset((
    "signed_enrollment", "enrollment_signature",
    "independently_pinned_enrollment_root",
    "separately_expected_enrollment_root_sha256",
    "expected_host_id", "expected_release_epoch",
    "expected_release_sequence", "independently_measured_snapshot",
    "minimum_external_epoch", "minimum_external_sequence",
    "revoked_root_sha256", "revoked_role_sha256",
))
FIELDS = frozenset((
    "schema", "purpose", "hostId", "releaseEpoch", "releaseSequence",
    "enrollmentSha256", "runtimeSnapshotSha256",
    "releaseRootSha256", "hostWitnessSha256", "receiptKeySha256",
    "historyAuthoritySha256", "historySequence", "previousHeadSha256",
    "challengeSha256",
))
DENIED = {
    "independentlyCustodiedHistorySignerVerified": False,
    "independentlyPersistedPreviousHeadVerified": False,
    "externallyRecordedNextHeadVerified": False,
    "externallyConsumedOneUseChallengeVerified": False,
    "externalRollbackResistanceVerified": False,
    "operatorEnrollmentRootCustodyVerified": False,
    "realInstalledHostAuthenticated": False,
    "authenticatedActiveSeatVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canApprove": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """A forged, stale, substituted or self-signed history proposal."""


def _deny(code):
    raise Refused(code)


def _digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def _canonical(doc):
    return json.dumps(
        doc, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("ascii")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _deny("C3E_HISTORY_DUPLICATE_SIGNED_FIELD")
        result[key] = value
    return result


def inspect_next_history_proposal_ci_only(
    *, enrollment_inputs: dict,
    signed_history_record: bytes, history_signature: bytes,
    independently_pinned_history_authority: Ed25519PublicKey,
    separately_expected_history_authority_sha256: str,
    independently_pinned_previous_head_sha256: str,
    independently_pinned_previous_sequence: int,
    independently_issued_challenge: bytes,
    revoked_history_authority_sha256: tuple,
):
    """Check signed continuity, NEVER assert actual independent custody.

    The root pin, previous head/sequence and challenge must originate in a
    separate future protected issuer, not the history record or gateway.
    This CI parser cannot authenticate that issuer or persist its state.
    """
    if (type(enrollment_inputs) is not dict
            or set(enrollment_inputs) != ENROLLMENT_INPUTS
            or type(enrollment_inputs["independently_measured_snapshot"]) is not dict):
        _deny("C3E_HISTORY_ENROLLMENT_INPUTS_REQUIRED")
    # Snapshot caller-controlled inputs before invoking the existing
    # verifier; no callback, signer or history record can replace its pins.
    frozen = dict(enrollment_inputs)
    frozen["independently_measured_snapshot"] = dict(
        enrollment_inputs["independently_measured_snapshot"])
    try:
        enrolled = P.inspect_enrollment_preflight_ci_only(**frozen)
    except (P.Refused, TypeError, ValueError) as exc:
        raise Refused("C3E_HISTORY_SIGNED_ENROLLMENT_PREFLIGHT_REFUSED") from exc
    if (enrolled.get("status") != P.STATUS
            or any(enrolled.get(key) is not False
                   for key in (*P.DENIED, *P.AF.NEGATIVE))):
        _deny("C3E_HISTORY_ENROLLMENT_ATTEMPTED_AUTHORITY_PROMOTION")

    if (type(separately_expected_history_authority_sha256) is not str
            or SHA.fullmatch(separately_expected_history_authority_sha256) is None
            or not isinstance(independently_pinned_history_authority,
                              Ed25519PublicKey)):
        _deny("C3E_HISTORY_INDEPENDENT_AUTHORITY_PIN_REQUIRED")
    try:
        history_signer_sha = P._fingerprint(
            independently_pinned_history_authority)
        revoked = P._revocations(revoked_history_authority_sha256)
    except P.Refused as exc:
        raise Refused("C3E_HISTORY_AUTHORITY_OR_REVOCATION_REFUSED") from exc
    if not hmac.compare_digest(
        history_signer_sha, separately_expected_history_authority_sha256
    ):
        _deny("C3E_HISTORY_SUBSTITUTED_AUTHORITY_ROOT")
    roles = enrolled.get("rolePublicKeySha256")
    if (type(roles) is not dict
            or set(roles) != {"releaseRoot", "hostWitness", "receipt"}
            or any(type(value) is not str or SHA.fullmatch(value) is None
                   for value in roles.values())
            or history_signer_sha == frozen[
                "separately_expected_enrollment_root_sha256"]
            or history_signer_sha in set(roles.values())):
        _deny("C3E_HISTORY_AUTHORITY_MUST_HAVE_DISTINCT_SIGNING_ROLE")
    if (history_signer_sha in revoked
            or history_signer_sha in frozen["revoked_root_sha256"]
            or history_signer_sha in frozen["revoked_role_sha256"]):
        _deny("C3E_HISTORY_REVOKED_HISTORY_AUTHORITY")

    if (type(independently_pinned_previous_head_sha256) is not str
            or SHA.fullmatch(independently_pinned_previous_head_sha256) is None
            or type(independently_pinned_previous_sequence) is not int
            or not 1 <= independently_pinned_previous_sequence < MAX_SEQUENCE
            or type(independently_issued_challenge) is not bytes
            or len(independently_issued_challenge) != 32):
        _deny("C3E_HISTORY_EXTERNAL_HEAD_SEQUENCE_OR_CHALLENGE_REQUIRED")
    if (type(signed_history_record) is not bytes
            or not 0 < len(signed_history_record) <= MAX_BYTES
            or type(history_signature) is not bytes
            or len(history_signature) != 64):
        _deny("C3E_HISTORY_SIGNED_RECORD_SIZE_REFUSED")

    try:
        independently_pinned_history_authority.verify(
            history_signature, DOMAIN + signed_history_record)
    except (InvalidSignature, ValueError) as exc:
        raise Refused("C3E_HISTORY_SIGNED_CONTINUITY_REFUSED") from exc
    try:
        doc = json.loads(
            signed_history_record.decode("ascii"),
            object_pairs_hook=_unique,
            parse_constant=lambda _: _deny("C3E_HISTORY_NONFINITE_SIGNED_VALUE"),
        )
        if (type(doc) is not dict or set(doc) != FIELDS
                or _canonical(doc) != signed_history_record):
            _deny("C3E_HISTORY_NONCANONICAL_OR_PARTIAL_SIGNED_RECORD")
    except (UnicodeError, ValueError, TypeError, OverflowError,
            RecursionError) as exc:
        if isinstance(exc, Refused):
            raise
        raise Refused("C3E_HISTORY_SIGNED_JSON_REFUSED") from exc

    # Python treats True == 1, so equality alone must never authorize
    # a correctly signed boolean masquerading as a release/chain counter.
    integer_fields = ("releaseEpoch", "releaseSequence", "historySequence")
    if (any(type(doc[field]) is not int for field in integer_fields)
            or any(type(doc[field]) is not str
                   for field in FIELDS.difference(integer_fields))):
        _deny("C3E_HISTORY_SIGNED_RECORD_MISMATCH_OR_REPLAY")

    expected = {
        "schema": SCHEMA,
        "purpose": PURPOSE,
        "hostId": enrolled["hostId"],
        "releaseEpoch": enrolled["releaseEpoch"],
        "releaseSequence": enrolled["releaseSequence"],
        "enrollmentSha256": enrolled["enrollmentSha256"],
        "runtimeSnapshotSha256": enrolled["runtimeSnapshotSha256"],
        "releaseRootSha256": roles["releaseRoot"],
        "hostWitnessSha256": roles["hostWitness"],
        "receiptKeySha256": roles["receipt"],
        "historyAuthoritySha256": history_signer_sha,
        "historySequence": independently_pinned_previous_sequence + 1,
        "previousHeadSha256": independently_pinned_previous_head_sha256,
        "challengeSha256": _digest(independently_issued_challenge),
    }
    if doc != expected:
        _deny("C3E_HISTORY_SIGNED_RECORD_MISMATCH_OR_REPLAY")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "signedNextHistoryRecordMatchesCallerPinsInCI": True,
        "signedHistoryExtendsOneExactCallerPinnedHeadInCI": True,
        "nextHistoryHeadSha256": _digest(
            DOMAIN + signed_history_record + history_signature),
        "nextHistorySequence": expected["historySequence"],
        "enrollmentSha256": enrolled["enrollmentSha256"],
        **P.AF.NEGATIVE,
        **P.DENIED,
        **DENIED,
    }
