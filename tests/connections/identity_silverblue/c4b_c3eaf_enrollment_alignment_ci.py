#!/usr/bin/env python3
"""C4b-owned CI composition with the existing protected C3e-AF role contract.

This is a READ-ONLY and DENY-ONLY interface, not an actual protected issuer.
It refuses a valid-but-different C3e role enrollment after inspecting C4b's
controller-side policy source and fresh signed BEGIN/UNAVAILABLE denial.

Both enrollment roots, expected host and runtime snapshot are still
independent *caller fixtures*. This cannot establish operator key custody,
real Linux kernel attestation, revocation history or production permission.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import controller_owned_policy_intake_ci as P
import controller_pinned_enrollment_gate_ci as E

ROOT = Path(__file__).resolve().parents[3]
C3EAF_PATH = ROOT / "tests/connections/c3e_release_trust/C3eAFSignedRoleEnrollment.py"
_spec = importlib.util.spec_from_file_location("c4b_existing_c3eaf_role_enrollment", C3EAF_PATH)
if _spec is None or _spec.loader is None:
    raise RuntimeError("C4B_C3EAF_REQUIRED_PROTECTED_ROLE_VERIFIER_UNAVAILABLE")
A = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = A
_spec.loader.exec_module(A)

SCHEMA = "postapollo.identity.c4b-c3eaf-enrollment-alignment.ci-v1"
NEGATIVE = {
    "operatorControlledEnrollmentRootsVerified": False,
    "independentlyEnrolledProductionHostVerified": False,
    "independentlySignedKernelProcessSeatVerified": False,
    "crossReleaseArtifactDigestAuthenticated": False,
    "protectedRevocationHistoryVerified": False,
    "externalChallengeLedgerCustodyVerified": False,
    "rollbackResistantVersionFloorVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """CI source, enrollment, role key or version are not aligned."""

def _deny(reason):
    raise Refused(reason)

def _bytes(key):
    if not isinstance(key, Ed25519PublicKey):
        _deny("C4B_C3EAF_SEPARATE_C3E_ROOT_REQUIRED")
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)

def inspect_aligned_ci_only(
    *, controller_dir: Path, serial: bytes, controller_challenge: str,
    c3e_signed_role_enrollment: bytes, c3e_role_signature: bytes,
    separately_pinned_c3e_enrollment_root: Ed25519PublicKey,
    independently_supplied_runtime_snapshot: dict,
):
    """Match verified host/version/receipt public key across two CI contracts.

    C4b pins come exclusively from its controller-side allowlisted bundle
    (never UART). C3e-AF's signature and expected snapshot checks are reused
    as-is: no C3e source is edited and no C3e one-use ledger is consumed.
    Actual independent trust-root and runtime-snapshot provenance must be
    supplied and authenticated by separately approved infrastructure.
    """
    c3e_root_bytes = _bytes(separately_pinned_c3e_enrollment_root)
    if type(independently_supplied_runtime_snapshot) is not dict:
        _deny("C4B_C3EAF_INDEPENDENT_SNAPSHOT_REQUIRED")
    frozen = dict(independently_supplied_runtime_snapshot)

    try:
        c4b = P.inspect_controller_owned_ci_only(
            controller_dir=controller_dir,
            serial=serial,
            controller_challenge=controller_challenge,
        )
    except P.Refused as exc:
        raise Refused("C4B_C3EAF_CONTROLLER_POLICY_OR_NONCE_REFUSED") from exc
    if (c4b.get("localControllerFixturePinsConsumedInCI") is not True
            or c4b.get("enrolledReceiptKeyMatchesSignedFreshDenialInCI") is not True
            or any(c4b.get(flag) is not False
                   for flag in (*P.NEGATIVE, *E.NEGATIVE))):
        _deny("C4B_C3EAF_CONTROLLER_AUTHORITY_PROMOTION_REFUSED")

    if hmac.compare_digest(
        hashlib.sha256(c3e_root_bytes).hexdigest(),
        c4b["controllerRootSha256"],
    ):
        _deny("C4B_C3EAF_CONTROLLER_AND_C3E_ENROLLMENT_ROOTS_ALIAS")

    # The expected host/version comes from the fully verified C4b signed
    # enrollment, not the C3e role document or a guest-authored marker.
    try:
        c3e = A.verify_signed_enrollment_ci_only(
            enrollment=c3e_signed_role_enrollment,
            signature=c3e_role_signature,
            independently_pinned_enrollment_root=separately_pinned_c3e_enrollment_root,
            expected_host_id=c4b["hostId"],
            expected_release_epoch=c4b["releaseEpoch"],
            expected_release_sequence=c4b["releaseSequence"],
            independently_measured_snapshot=frozen,
        )
    except A.Refused as exc:
        raise Refused("C4B_C3EAF_PROTECTED_ROLE_ENROLLMENT_REFUSED") from exc

    public_receipt = _bytes(c3e["receipt"])
    if not hmac.compare_digest(
        hashlib.sha256(public_receipt).hexdigest(),
        c4b["receiptKeySha256"],
    ):
        _deny("C4B_C3EAF_CROSS_ENROLLMENT_RECEIPT_KEY_MISMATCH")

    # A signing root from C4b is not permitted to double as C3e's
    # release-signing, host witness or receipt-signing key.
    for key in ("release_root", "witness", "receipt"):
        if hmac.compare_digest(
            hashlib.sha256(_bytes(c3e[key])).hexdigest(),
            c4b["controllerRootSha256"],
        ):
            _deny("C4B_C3EAF_CROSS_ROLE_KEY_ALIAS_REFUSED")

    if not hmac.compare_digest(
        c3e["runtimeSnapshotSha256"],
        hashlib.sha256(A.Z.Y.X._canonical(frozen)).hexdigest(),
    ):
        _deny("C4B_C3EAF_SIGNED_SNAPSHOT_DIGEST_CHANGED")

    # C4b releaseSha256 and the C3e RPM/source hashes have different
    # contracts. DO NOT assert those are the same artifact or imply signed
    # cross-release provenance until a separately authorized mapping exists.
    return {
        "schema": SCHEMA,
        "c4bFreshSignedDenialMatchedControllerEnrollmentInCI": True,
        "c3eSignedRoleEnrollmentMatchedHostAndVersionInCI": True,
        "sameReceiptKeyBoundToC4bAndC3eRolesInCI": True,
        "hostId": c4b["hostId"],
        "releaseEpoch": c4b["releaseEpoch"],
        "releaseSequence": c4b["releaseSequence"],
        "c4bReleaseSha256": c4b["releaseSha256"],
        "c3eRuntimeSnapshotSha256": c3e["runtimeSnapshotSha256"],
        "receiptKeySha256": c4b["receiptKeySha256"],
        "c4bPolicySha256": c4b["policySha256"],
        "c3eEnrollmentSha256": c3e["enrollmentSha256"],
        **P.NEGATIVE, **E.NEGATIVE, **A.NEGATIVE, **NEGATIVE,
    }
