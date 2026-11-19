#!/usr/bin/env python3
"""C3e protected witness enrollment: deny-only, externally pinned CI preflight.

Reuse the merged C3e-AF signed role enrollment. This file NEVER generates keys,
enrolls any trust anchor, issues/consumes a challenge, or authenticates a host.
The caller supplies a root fingerprint, revocation roster and release floor;
none of those are independently custodied merely by passing this preflight.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "c3e_operator_preflight_existing_af", HERE / "C3eAFSignedRoleEnrollment.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("C3E_ENROLLMENT_EXISTING_AF_SOURCE_REQUIRED")
AF = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = AF
_spec.loader.exec_module(AF)

SCHEMA = "postapollo.connections.c3e-operator-witness-enrollment-preflight.ci-v1"
STATUS = "C3E_OPERATOR_WITNESS_ENROLLMENT_FORMAT_VALID_NOT_TRUSTED"
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_FLOOR = 2**63
DENIED = {
    "operatorEnrollmentRootCustodyVerified": False,
    "independentWitnessSigningKeyCustodyVerified": False,
    "independentReleaseFloorCustodyVerified": False,
    "externalChallengeIssuerVerified": False,
    "externalRollbackResistanceVerified": False,
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
    """Pre-enrollment role, revocation, floor or root pin refused."""


def _deny(reason):
    raise Refused(reason)


def _fingerprint(key):
    if not isinstance(key, Ed25519PublicKey):
        _deny("C3E_OPERATOR_ROOT_OBJECT_REQUIRED")
    return hashlib.sha256(key.public_bytes(Encoding.Raw, PublicFormat.Raw)).hexdigest()


def _revocations(items):
    # A caller-supplied list is *not* operator-authenticated revocation state.
    # Strict ordering makes conflicting/noncanonical copies rejectable in CI.
    if (type(items) is not tuple or len(items) > 64
            or any(type(x) is not str or DIGEST.fullmatch(x) is None
                   for x in items)
            or tuple(sorted(set(items))) != items):
        _deny("C3E_OPERATOR_REVOCATION_ROSTER_INVALID")
    return set(items)


def _floor(epoch, sequence):
    if (type(epoch) is not int or type(sequence) is not int
            or not 0 < epoch < MAX_FLOOR
            or not 0 < sequence < MAX_FLOOR):
        _deny("C3E_OPERATOR_EXTERNAL_RELEASE_FLOOR_INVALID")
    return epoch, sequence


def inspect_enrollment_preflight_ci_only(
    *, signed_enrollment: bytes, enrollment_signature: bytes,
    independently_pinned_enrollment_root: Ed25519PublicKey,
    separately_expected_enrollment_root_sha256: str,
    expected_host_id: str,
    expected_release_epoch: int, expected_release_sequence: int,
    independently_measured_snapshot: dict,
    minimum_external_epoch: int, minimum_external_sequence: int,
    revoked_root_sha256: tuple, revoked_role_sha256: tuple,
):
    """Validate inputs needed for a later operator-authorized enrollment.

    Root pin, revocation and external floors are injected test arguments, NOT
    verified real custody. Do not call this output from production admission.
    No private key is consumed; no record, ledger, host or service is changed.
    """
    if (type(separately_expected_enrollment_root_sha256) is not str
            or DIGEST.fullmatch(separately_expected_enrollment_root_sha256) is None):
        _deny("C3E_OPERATOR_OUT_OF_BAND_ROOT_FINGERPRINT_REQUIRED")
    actual_root_hash = _fingerprint(independently_pinned_enrollment_root)
    if actual_root_hash != separately_expected_enrollment_root_sha256:
        _deny("C3E_OPERATOR_UNTRUSTED_OR_SUBSTITUTED_ENROLLMENT_ROOT")
    roots = _revocations(revoked_root_sha256)
    revoked_roles = _revocations(revoked_role_sha256)
    if actual_root_hash in roots or actual_root_hash in revoked_roles:
        _deny("C3E_OPERATOR_REVOKED_ENROLLMENT_ROOT")
    minimum = _floor(minimum_external_epoch, minimum_external_sequence)
    candidate = _floor(expected_release_epoch, expected_release_sequence)
    if candidate < minimum:
        _deny("C3E_OPERATOR_RELEASE_FLOOR_DOWNGRADE")

    try:
        roles = AF.verify_signed_enrollment_ci_only(
            enrollment=signed_enrollment, signature=enrollment_signature,
            independently_pinned_enrollment_root=independently_pinned_enrollment_root,
            expected_host_id=expected_host_id,
            expected_release_epoch=expected_release_epoch,
            expected_release_sequence=expected_release_sequence,
            independently_measured_snapshot=independently_measured_snapshot,
        )
    except (AF.Refused, TypeError, ValueError) as exc:
        raise Refused("C3E_OPERATOR_EXISTING_SIGNED_ROLE_ENROLLMENT_REFUSED") from exc

    role_hashes = {
        "releaseRoot": _fingerprint(roles["release_root"]),
        "hostWitness": _fingerprint(roles["witness"]),
        "receipt": _fingerprint(roles["receipt"]),
    }
    if (len(set(role_hashes.values())) != 3
            or actual_root_hash in set(role_hashes.values())
            or any(hash_ in revoked_roles or hash_ in roots
                   for hash_ in role_hashes.values())):
        _deny("C3E_OPERATOR_REVOKED_OR_ALIASED_ROLE")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "testOnlySignedRoleEnrollmentMatchesCallerPins": True,
        "testOnlyRevocationAndMinimumFloorInputsConsistent": True,
        "hostId": expected_host_id,
        "releaseEpoch": candidate[0],
        "releaseSequence": candidate[1],
        "enrollmentSha256": roles["enrollmentSha256"],
        "runtimeSnapshotSha256": roles["runtimeSnapshotSha256"],
        "rolePublicKeySha256": role_hashes,
        **AF.NEGATIVE,
        **DENIED,
    }
