#!/usr/bin/env python3
"""C4b Package 1: verify an outside-signed current controller checkpoint.

A separate, independently *pinned* Ed25519 public key verifies a fresh
nonce-bound statement of the currently committed root, policy and transition
cursor. This is a read-only cryptographic contract, NOT deployment of an
external witness. A disposable CI test signer can fabricate these statements.

A real witness must own its private key and history OUTSIDE the C4b
controller's root/UID/SQLite recovery domain. A restored controller DB is
refused only if the witness independently reports the NEWER state. The
caller also has to protect challenge creation and one-use consumption.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

SCHEMA = "postapollo.identity.c4b-external-checkpoint.ci-v1"
DOMAIN = b"postapollo.identity.c4b-external-checkpoint.ci-v1\x00"
AUDIENCE = "protected-connections-c3e-ci-only"
SCOPE = "read-only-current-controller-state-diagnostic"
MAX_PROOF = 2048
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
HOST = re.compile(r"postapollo-identity-ci@[a-z0-9][a-z0-9-]{2,63}\Z", re.ASCII)
FIELDS = frozenset({
    "schema", "audience", "scope", "challenge", "hostId",
    "controllerRootSha256", "controllerPolicySha256", "transitionSha256",
    "transitionSequence", "minimumReleaseEpoch", "minimumReleaseSequence",
})
STATE_FIELDS = frozenset({
    "hostId", "controllerRootSha256", "controllerPolicySha256",
    "transitionSha256", "transitionSequence",
    "minimumReleaseEpoch", "minimumReleaseSequence",
})
NEGATIVE = {
    "realWitnessSignerCustodyVerified": False,
    "separateWitnessHistoryAuthorityVerified": False,
    "externallyProtectedChallengeLedgerVerified": False,
    "hardwareRollbackResistanceVerified": False,
    "independentInstalledHostAndSeatVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Signed checkpoint not independently verified for this controller."""


def _deny(code):
    raise Refused(code)


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _canonical(obj):
    if type(obj) is not dict:
        _deny("C4B_P1_WITNESS_CANONICAL_DICT_REQUIRED")
    try:
        return json.dumps(obj, sort_keys=True, ensure_ascii=True,
                          allow_nan=False, separators=(",", ":")).encode("ascii")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise Refused("C4B_P1_WITNESS_INVALID_CANONICAL_SOURCE") from exc


def _no_duplicate_fields(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            _deny("C4B_P1_WITNESS_DUPLICATE_SIGNED_FIELD")
        out[key] = value
    return out


def _proof(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_PROOF:
        _deny("C4B_P1_WITNESS_SIGNED_RECORD_BOUNDS")
    try:
        obj = json.loads(raw.decode("ascii"),
                         object_pairs_hook=_no_duplicate_fields,
                         parse_constant=lambda _: _deny(
                             "C4B_P1_WITNESS_NONFINITE_SIGNED_NUMBER"))
    except (TypeError, UnicodeError, ValueError, RecursionError) as exc:
        raise Refused("C4B_P1_WITNESS_SIGNED_JSON_REFUSED") from exc
    if type(obj) is not dict or set(obj) != FIELDS or _canonical(obj) != raw:
        _deny("C4B_P1_WITNESS_SIGNED_RECORD_NONCANONICAL")
    if (obj["schema"] != SCHEMA or obj["audience"] != AUDIENCE
            or obj["scope"] != SCOPE
            or type(obj["hostId"]) is not str or HOST.fullmatch(obj["hostId"]) is None
            or any(type(obj[k]) is not str or HEX64.fullmatch(obj[k]) is None
                   for k in ("challenge", "controllerRootSha256",
                             "controllerPolicySha256", "transitionSha256"))
            or any(type(obj[k]) is not int or not 0 <= obj[k] < 2**53
                   for k in ("transitionSequence", "minimumReleaseEpoch",
                             "minimumReleaseSequence"))
            or obj["minimumReleaseEpoch"] == 0
            or obj["minimumReleaseSequence"] == 0):
        _deny("C4B_P1_WITNESS_SIGNED_SCOPE_OR_VALUE_REFUSED")
    return obj


def inspect_current_checkpoint_ci_only(
    *, controller_state: dict, signed_checkpoint: bytes,
    checkpoint_signature: bytes,
    independently_pinned_witness_root: Ed25519PublicKey,
    independently_pinned_witness_sha256: str,
    independently_issued_challenge: bytes,
):
    """Compare a fresh signature from a caller-pinned *external* witness.

    The prior trust source, real witness signing service, nonce custody,
    durability and witness-machine identity are NOT established here.
    All returned positive flags are diagnostic; all grant flags stay false.
    """
    if (type(controller_state) is not dict
            or set(controller_state) != STATE_FIELDS):
        _deny("C4B_P1_WITNESS_EXACT_CONTROLLER_STATE_REQUIRED")
    if (type(independently_issued_challenge) is not bytes
            or len(independently_issued_challenge) != 32
            or type(checkpoint_signature) is not bytes
            or len(checkpoint_signature) != 64
            or type(independently_pinned_witness_sha256) is not str
            or HEX64.fullmatch(independently_pinned_witness_sha256) is None
            or not isinstance(independently_pinned_witness_root, Ed25519PublicKey)):
        _deny("C4B_P1_WITNESS_TRUSTED_PIN_NONCE_OR_SIGNATURE_REQUIRED")
    pub = independently_pinned_witness_root.public_bytes(
        Encoding.Raw, PublicFormat.Raw)
    if not hmac.compare_digest(_sha(pub), independently_pinned_witness_sha256):
        _deny("C4B_P1_WITNESS_INDEPENDENT_ROOT_PIN_MISMATCH")
    obj = _proof(signed_checkpoint)
    try:
        independently_pinned_witness_root.verify(
            checkpoint_signature, DOMAIN + signed_checkpoint)
    except (InvalidSignature, ValueError) as exc:
        raise Refused("C4B_P1_WITNESS_SIGNATURE_REFUSED") from exc
    if not hmac.compare_digest(obj["challenge"], _sha(
            independently_issued_challenge)):
        _deny("C4B_P1_WITNESS_NOT_SIGNED_FOR_FRESH_CHALLENGE")
    # The witness signing key must not double as the locally current root.
    if hmac.compare_digest(obj["controllerRootSha256"],
                           independently_pinned_witness_sha256):
        _deny("C4B_P1_WITNESS_SIGNER_AND_CONTROLLER_ROOT_ALIAS")
    for key in STATE_FIELDS:
        actual = controller_state[key]
        value = obj[key]
        if key == "hostId":
            if type(actual) is not str or not hmac.compare_digest(actual, value):
                _deny("C4B_P1_WITNESS_HOST_DIFFERENT_FROM_PROTECTED_LEDGER")
        elif "Sha256" in key:
            if (type(actual) is not str or HEX64.fullmatch(actual) is None
                    or not hmac.compare_digest(actual, value)):
                _deny("C4B_P1_WITNESS_CONTROLLER_DIGEST_OR_CHAIN_MISMATCH")
        else:
            if type(actual) is not int or actual != value:
                _deny("C4B_P1_WITNESS_MONOTONIC_CURSOR_OR_RELEASE_MISMATCH")
    return {
        "schema": SCHEMA,
        "externalPinnedSignedCheckpointMatchesRootOwnedLedgerInCi": True,
        "signedCheckpointMatchesCallerFreshNonceInCi": True,
        "hostId": obj["hostId"],
        "transitionSequence": obj["transitionSequence"],
        "transitionSha256": obj["transitionSha256"],
        "witnessPublicSha256": independently_pinned_witness_sha256,
        "signedCheckpointSha256": _sha(signed_checkpoint),
        **NEGATIVE,
    }
