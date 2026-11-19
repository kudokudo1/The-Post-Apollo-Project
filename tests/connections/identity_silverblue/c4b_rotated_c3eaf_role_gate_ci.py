#!/usr/bin/env python3
"""C4b Package 1: rotated controller enrollment ↔ protected C3e-AF role CI.

The previous C4b root, newly rotated C4b root, and C3e enrollment root
must be distinct, and the existing protected C3e-AF validator must agree
with the new C4b controller's signed host, version, receipt and challenge.

Read-only CI evidence only. This neither enrolls a real host nor proves
outside-guest process/seat witness, durable issuer provenance, or permissions.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import c4b_signed_trust_transition_ci as T
import c4b_c3eaf_enrollment_alignment_ci as C

SCHEMA = "postapollo.identity.c4b-rotated-c3eaf-alignment.ci-v1"
NEGATIVE = {
    "protectedExternalRootCustodyVerified": False,
    "durableExternalTransitionLedgerVerified": False,
    "independentInstalledGatewayAttestationVerified": False,
    "independentHostProcessAndSeatWitnessVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Rotated C4b controller and C3e role identity do not align."""


def _deny(reason):
    raise Refused(reason)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inspect_rotated_roles_ci_only(
    *, rotation_inputs: dict,
    c3e_signed_role_enrollment: bytes,
    c3e_role_signature: bytes,
    separately_pinned_c3e_enrollment_root: Ed25519PublicKey,
    independently_supplied_runtime_snapshot: dict,
):
    """Compose unchanged C4b and protected C3e-AF verifiers, without grants.

    Caller-supplied roots, prior chain cursor and expected process snapshot
    remain disposable CI fixtures; real trust anchors belong to separate
    protected owner-controlled components. The result cannot authenticate a
    machine or authorize sign-in.
    """
    if type(rotation_inputs) is not dict:
        _deny("C4B_P1_ROTATION_INPUTS_REQUIRED")
    if type(independently_supplied_runtime_snapshot) is not dict:
        _deny("C4B_P1_INDEPENDENT_RUNTIME_SNAPSHOT_REQUIRED")
    # Freeze mutable caller mappings before the two independent verifiers.
    rotate = dict(rotation_inputs)
    snapshot = dict(independently_supplied_runtime_snapshot)
    try:
        c3e_root = C._bytes(separately_pinned_c3e_enrollment_root)
    except C.Refused as exc:
        raise Refused("C4B_P1_C3E_ROOT_REQUIRED") from exc

    try:
        rotated = T.inspect_rotation_ci_only(**rotate)
    except (T.Refused, TypeError) as exc:
        raise Refused("C4B_P1_CONTROLLER_ROTATION_REFUSED") from exc
    if any(rotated.get(key) is not False
           for key in (*T.NEGATIVE, *T.P.NEGATIVE, *T.E.NEGATIVE)):
        _deny("C4B_P1_ROTATION_ATTEMPTED_PERMISSION_PROMOTION")

    root_digest = _digest(c3e_root)
    if (hmac.compare_digest(root_digest, rotated["previousControllerRootSha256"])
            or hmac.compare_digest(root_digest, rotated["nextControllerRootSha256"])):
        _deny("C4B_P1_C3E_ENROLLMENT_ROOT_ALIASES_RETIRED_OR_NEW_C4B_ROOT")

    # This reads the new bundle again, and the output must exactly agree
    # with the frozen digest-level result of rotation verification. A file
    # replacement or stale C3e role between the checks must fail closed.
    try:
        aligned = C.inspect_aligned_ci_only(
            controller_dir=rotate["next_controller_dir"],
            serial=rotate["serial"],
            controller_challenge=rotate["controller_challenge"],
            c3e_signed_role_enrollment=c3e_signed_role_enrollment,
            c3e_role_signature=c3e_role_signature,
            separately_pinned_c3e_enrollment_root=separately_pinned_c3e_enrollment_root,
            independently_supplied_runtime_snapshot=snapshot,
        )
    except (C.Refused, KeyError, TypeError) as exc:
        raise Refused("C4B_P1_C3E_ROLE_OR_NEW_CONTROLLER_REFUSED") from exc

    if (aligned.get("c3eSignedRoleEnrollmentMatchedHostAndVersionInCI") is not True
            or aligned.get("sameReceiptKeyBoundToC4bAndC3eRolesInCI") is not True
            or aligned.get("c4bFreshSignedDenialMatchedControllerEnrollmentInCI") is not True
            or aligned.get("c4bPolicySha256") != rotated["nextPolicySha256"]
            or aligned.get("receiptKeySha256") != rotated["receiptKeySha256"]
            or aligned.get("hostId") != rotated["hostId"]
            or aligned.get("c4bReleaseSha256") != rotated["releaseSha256"]
            or aligned.get("releaseEpoch") != rotated["releaseEpoch"]
            or aligned.get("releaseSequence") != rotated["releaseSequence"]
            or any(aligned.get(flag) is not False
                   for flag in (*C.NEGATIVE, *C.P.NEGATIVE,
                                *C.E.NEGATIVE, *C.A.NEGATIVE))):
        _deny("C4B_P1_ROTATED_ENROLLMENT_IDENTITY_OR_AUTHORITY_MISMATCH")

    # After C3e-AF has required canonical signed enrollment, also refuse
    # reuse of the *retired* C4b root in any of C3e's key roles. The new
    # C4b root is already checked by unchanged C4b ↔ C3e-AF integration.
    try:
        role = json.loads(c3e_signed_role_enrollment.decode("ascii"))
        role_digests = (
            _digest(bytes.fromhex(role[name]))
            for name in ("releaseRootPublicHex", "hostWitnessPublicHex",
                         "receiptPublicHex")
        )
        if any(hmac.compare_digest(digest,
               rotated["previousControllerRootSha256"]) for digest in role_digests):
            _deny("C4B_P1_RETIRED_CONTROLLER_ROOT_REUSED_AS_C3E_ROLE_KEY")
    except (UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise Refused("C4B_P1_SIGNED_C3E_ROLE_BYTES_UNAVAILABLE") from exc

    return {
        "schema": SCHEMA,
        "rotatedControllerAndC3eSignedRoleAgreeInCI": True,
        "retiredAndNewControllerRootsRemainSeparateFromC3eRolesInCI": True,
        "freshControllerDenialStillMatchesProtectedRoleEnrollmentInCI": True,
        "hostId": rotated["hostId"],
        "releaseEpoch": rotated["releaseEpoch"],
        "releaseSequence": rotated["releaseSequence"],
        "transitionSha256": rotated["transitionSha256"],
        "nextControllerRootSha256": rotated["nextControllerRootSha256"],
        "c3eEnrollmentSha256": aligned["c3eEnrollmentSha256"],
        "receiptKeySha256": rotated["receiptKeySha256"],
        **T.NEGATIVE, **C.NEGATIVE, **C.A.NEGATIVE, **NEGATIVE,
    }
