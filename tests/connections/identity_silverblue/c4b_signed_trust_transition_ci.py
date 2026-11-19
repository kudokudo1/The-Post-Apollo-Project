#!/usr/bin/env python3
"""C4b Package 1: source-only dual-signed controller trust transition.

A controller-root change is authorized by BOTH the old anchored signing key
and the proposed new key over the same canonical transition record. The
previous policy hash and chain cursor must come from a separate, protected
authority. This module does not provide that authority: every input in CI
is synthetic and every production permission stays false.

No private keys, host commands, service activation, credential access or
database mutations are performed here.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import controller_owned_policy_intake_ci as P
import controller_pinned_enrollment_gate_ci as E

SCHEMA = "postapollo.identity.c4b.controller-root-transition.ci-v1"
DOMAIN = b"postapollo.identity.c4b.controller-root-transition.ci-v1\x00"
AUDIENCE = "protected-connections-c3e-ci-only"
ACTION = "ROTATE_CONTROLLER_ENROLLMENT_ROOT_DIAGNOSTIC_ONLY"
FIELDS = frozenset({
    "schema", "audience", "action", "transitionId", "transitionSequence",
    "previousTransitionSha256", "hostId", "previousPolicySha256",
    "nextPolicySha256", "previousRootSha256", "nextRootSha256",
    "previousFloorEpoch", "previousFloorSequence",
    "nextFloorEpoch", "nextFloorSequence",
})
MAX_RECORD = 3072
NEGATIVE = {
    "operatorControlledRootCustodyVerified": False,
    "independentRotationAuthorityEnrolled": False,
    "protectedTransitionHistoryVerified": False,
    "externalRollbackResistanceVerified": False,
    "independentHostKernelAndSeatWitnessVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """No trusted transition is established by these CI inputs."""


def _deny(code):
    raise Refused(code)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _raw_public(key):
    if not isinstance(key, Ed25519PublicKey):
        _deny("C4B_ROTATION_INDEPENDENT_PUBLIC_KEY_REQUIRED")
    return key.public_bytes(Encoding.Raw, PublicFormat.Raw)


def _unique(pairs):
    out = {}
    for name, value in pairs:
        if name in out:
            _deny("C4B_ROTATION_DUPLICATE_FIELD")
        out[name] = value
    return out


def canonical(document):
    if type(document) is not dict:
        _deny("C4B_ROTATION_DICTIONARY_REQUIRED")
    try:
        return json.dumps(document, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise Refused("C4B_ROTATION_CANONICAL_ENCODING_REFUSED") from exc


def _record(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RECORD:
        _deny("C4B_ROTATION_RECORD_SIZE_REFUSED")
    try:
        document = json.loads(raw.decode("ascii"), object_pairs_hook=_unique,
                              parse_constant=lambda _: _deny(
                                  "C4B_ROTATION_NONFINITE_NUMBER"))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Refused("C4B_ROTATION_RECORD_JSON_REFUSED") from exc
    if type(document) is not dict or set(document) != FIELDS:
        _deny("C4B_ROTATION_EXACT_FIELDS_REQUIRED")
    if canonical(document) != raw:
        _deny("C4B_ROTATION_NONCANONICAL_RECORD")
    if (document["schema"] != SCHEMA or document["audience"] != AUDIENCE
            or document["action"] != ACTION
            or type(document["transitionId"]) is not str
            or E.IDENT.fullmatch(document["transitionId"]) is None
            or type(document["hostId"]) is not str
            or E.HOST.fullmatch(document["hostId"]) is None
            or any(type(document[name]) is not str or
                   E.HEX.fullmatch(document[name]) is None
                   for name in ("previousTransitionSha256",
                                "previousPolicySha256", "nextPolicySha256",
                                "previousRootSha256", "nextRootSha256"))
            or any(type(document[name]) is not int or
                   not 0 < document[name] < 2**53
                   for name in ("transitionSequence", "previousFloorEpoch",
                                "previousFloorSequence", "nextFloorEpoch",
                                "nextFloorSequence"))):
        _deny("C4B_ROTATION_SCOPE_OR_FIELDS_INVALID")
    return document


def inspect_rotation_ci_only(
    *, previous_policy: bytes, next_policy: bytes, transition: bytes,
    previous_root: Ed25519PublicKey, proposed_root: Ed25519PublicKey,
    previous_signature: bytes, proposed_signature: bytes,
    independently_pinned_previous_policy_sha256: str,
    independently_pinned_previous_transition_sha256: str,
    independently_pinned_transition_sequence: int,
    independently_expected_transition_id: str,
    next_controller_dir: Path, serial: bytes, controller_challenge: str,
):
    """Check a controller-side rotation without admitting the host.

    The previous policy digest, previous chain head, sequence and current
    public root MUST be separately authenticated outside this function.
    A same-UID caller able to replace all of those inputs can forge CI
    acceptance; this is NOT a production root-custody or antirollback service.
    """
    if (type(independently_pinned_previous_policy_sha256) is not str or
            E.HEX.fullmatch(independently_pinned_previous_policy_sha256) is None
            or type(independently_pinned_previous_transition_sha256) is not str
            or E.HEX.fullmatch(independently_pinned_previous_transition_sha256) is None
            or type(independently_pinned_transition_sequence) is not int
            or not 0 <= independently_pinned_transition_sequence < 2**53 - 1
            or type(independently_expected_transition_id) is not str
            or E.IDENT.fullmatch(independently_expected_transition_id) is None
            or type(previous_signature) is not bytes
            or type(proposed_signature) is not bytes
            or len(previous_signature) != 64 or len(proposed_signature) != 64):
        _deny("C4B_ROTATION_INDEPENDENT_CURSOR_AND_SIGNATURES_REQUIRED")

    old_public = _raw_public(previous_root)
    new_public = _raw_public(proposed_root)
    if hmac.compare_digest(old_public, new_public):
        _deny("C4B_ROTATION_OLD_AND_NEW_ROOT_MUST_DIFFER")
    old_digest, new_digest = _sha(old_public), _sha(new_public)
    previous_digest, next_digest = _sha(previous_policy), _sha(next_policy)
    if not hmac.compare_digest(previous_digest,
                               independently_pinned_previous_policy_sha256):
        _deny("C4B_ROTATION_PREVIOUS_POLICY_NOT_EXTERNALLY_PINNED")

    try:
        previous = P._parse_policy(previous_policy)
        following = P._parse_policy(next_policy)
    except P.Refused as exc:
        raise Refused("C4B_ROTATION_CONTROLLER_POLICY_REFUSED") from exc
    if (not hmac.compare_digest(previous["rootPublicSha256"], old_digest)
            or not hmac.compare_digest(following["rootPublicSha256"], new_digest)
            or previous["hostId"] != following["hostId"]
            or previous["audience"] != following["audience"]
            or previous["scope"] != following["scope"]):
        _deny("C4B_ROTATION_POLICY_HOST_SCOPE_OR_ROOT_MISMATCH")

    old_floor = (previous["minimumReleaseEpoch"],
                 previous["minimumReleaseSequence"])
    new_floor = (following["minimumReleaseEpoch"],
                 following["minimumReleaseSequence"])
    if new_floor < old_floor:
        _deny("C4B_ROTATION_RELEASE_FLOOR_DOWNGRADE")
    if previous["releaseSha256"] != following["releaseSha256"] and new_floor == old_floor:
        _deny("C4B_ROTATION_CHANGED_RELEASE_WITHOUT_VERSION_ADVANCE")
    if not set(previous["revokedEnrollmentIds"]).issubset(
            following["revokedEnrollmentIds"]):
        _deny("C4B_ROTATION_REVOCATION_ERASURE")

    record = _record(transition)
    if (record["transitionSequence"] !=
                independently_pinned_transition_sequence + 1
            or not hmac.compare_digest(
                record["previousTransitionSha256"],
                independently_pinned_previous_transition_sha256)
            or record["transitionId"] != independently_expected_transition_id
            or record["hostId"] != previous["hostId"]
            or record["previousPolicySha256"] != previous_digest
            or record["nextPolicySha256"] != next_digest
            or record["previousRootSha256"] != old_digest
            or record["nextRootSha256"] != new_digest
            or (record["previousFloorEpoch"],
                record["previousFloorSequence"]) != old_floor
            or (record["nextFloorEpoch"],
                record["nextFloorSequence"]) != new_floor):
        _deny("C4B_ROTATION_TRANSITION_CHAIN_OR_PINS_REFUSED")

    try:
        previous_root.verify(previous_signature, DOMAIN + transition)
        proposed_root.verify(proposed_signature, DOMAIN + transition)
    except InvalidSignature as exc:
        raise Refused("C4B_ROTATION_DUAL_ROOT_SIGNATURE_REFUSED") from exc

    # Prove that the proposed controller bundle actually contains the new
    # root and a certificate signed with it for the same running denial key.
    # This existing C4b reader remains unchanged; no C3e edits or grants.
    try:
        candidate = P.inspect_controller_owned_ci_only(
            controller_dir=next_controller_dir, serial=serial,
            controller_challenge=controller_challenge)
    except P.Refused as exc:
        raise Refused("C4B_ROTATION_NEXT_SIGNED_BUNDLE_REFUSED") from exc
    if (candidate.get("policySha256") != next_digest
            or candidate.get("controllerRootSha256") != new_digest
            or candidate.get("hostId") != following["hostId"]
            or candidate.get("releaseSha256") != following["releaseSha256"]
            or (candidate.get("releaseEpoch"),
                candidate.get("releaseSequence")) < new_floor
            or candidate.get("enrolledReceiptKeyMatchesSignedFreshDenialInCI") is not True
            or any(candidate.get(flag) is not False
                   for flag in (*P.NEGATIVE, *E.NEGATIVE))):
        _deny("C4B_ROTATION_NEXT_BUNDLE_AUTHORITY_OR_CONSISTENCY_REFUSED")

    return {
        "schema": SCHEMA,
        "dualSignedControllerRootTransitionCheckedInCI": True,
        "successorEnrollmentStillSignsRealChallengeDenialInCI": True,
        "monotonicTransitionAndRevocationContinuityCheckedInCI": True,
        "transitionSequence": record["transitionSequence"],
        "transitionSha256": _sha(transition),
        "nextControllerRootSha256": new_digest,
        "nextPolicySha256": next_digest,
        "hostId": following["hostId"],
        "releaseEpoch": candidate["releaseEpoch"],
        "releaseSequence": candidate["releaseSequence"],
        **P.NEGATIVE, **E.NEGATIVE, **NEGATIVE,
    }
