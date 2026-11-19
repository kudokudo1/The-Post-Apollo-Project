#!/usr/bin/env python3
"""C4b: third-party-signed *test-evidence* binding for C4b + original C3e-N.

A signed statement covers the exact canonical raw C3b installed-origin and
C3e read-only-witness fixture evidence, the verified C4b checkpoint bytes
and signature digests, release floors, three distinct process PIDs and
two fresh challenges. The independent signer is ONLY a CI test key.

The signed claim does not authenticate the source of fixture evidence:
real operator-managed key custody, measured running host/seat, external
nonce history and C5 consent remain missing. NEVER authorize sign-in.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

import c4b_c3en_signed_origin_join_ci as J
import c4b_root_owned_controller_ledger_ci as L
import c4b_signed_external_checkpoint_ci as W

SCHEMA = "postapollo.identity.c4b-c3en-host-binding.ci-v1"
DOMAIN = b"postapollo.identity.c4b-c3en-host-binding.ci-v1\x00"
AUDIENCE = "protected-c3e-identity-host-evidence-ci-only"
SCOPE = "deny-only-signed-origin-comparison-not-native-host-attestation"
STATUS = "C4B_C3EN_SIGNED_CI_SNAPSHOT_BOUND_NOT_HOST_AUTHENTICATED"
MAX_RECORD_BYTES = 4096
SHA256 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
JOIN_KEYS = frozenset({
    "socket_path", "controller_state", "fresh_challenge",
    "separately_pinned_peer_uid", "separately_pinned_peer_gid",
    "separately_pinned_peer_pid", "separately_pinned_witness_root",
    "separately_pinned_witness_sha256",
    "installed_os_evidence", "c4b_opt_proof", "read_only_witness_status",
    "expected_installed_pid", "expected_witness_pid",
    "expected_witness_enrollment_sha256",
})
NEGATIVE = {
    "realInstalledHostAttestationVerified": False,
    "independentHostSigningKeyCustodyVerified": False,
    "externalWitnessRollbackResistanceVerified": False,
    "protectedExternalChallengeLedgerVerified": False,
    "authenticatedNativeSeatVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canApprove": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Unsigned, stale, forged or mismatched host/evidence boundary."""


def _deny(code):
    raise Refused(code)


def _sha(blob):
    return hashlib.sha256(blob).hexdigest()


def _canonical(obj):
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        raise Refused("C4B_C3EN_HOST_BINDING_CANONICAL_EVIDENCE_REFUSED") from exc


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            _deny("C4B_C3EN_HOST_BINDING_DUPLICATE_SIGNED_FIELD")
        out[key] = value
    return out


def _signed_record(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RECORD_BYTES:
        _deny("C4B_C3EN_HOST_BINDING_SIZE_REFUSED")
    try:
        doc = json.loads(raw.decode("ascii"), object_pairs_hook=_unique,
                         parse_constant=lambda _: _deny(
                             "C4B_C3EN_HOST_BINDING_NONFINITE_NUMBER"))
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Refused("C4B_C3EN_HOST_BINDING_JSON_REFUSED") from exc
    if type(doc) is not dict or _canonical(doc) != raw:
        _deny("C4B_C3EN_HOST_BINDING_NONCANONICAL")
    return doc


def make_expected_statement_ci_only(
    *, join_inputs: dict, join_result: dict, host_attestation_challenge: bytes,
):
    """Build the *bytes to be signed*, never an authorization.

    This helper intentionally DOES NOT sign. CI signer keys are created by
    the separate test, not this module. In production every observation
    would need to be obtained from an approved, independently authenticated
    installed-host witness before signing any analogous statement.
    """
    if (type(join_inputs) is not dict or set(join_inputs) != JOIN_KEYS
            or type(join_result) is not dict
            or type(host_attestation_challenge) is not bytes
            or len(host_attestation_challenge) != 32):
        _deny("C4B_C3EN_HOST_BINDING_EXACT_INPUTS_REQUIRED")
    if (join_result.get("schema") != J.SCHEMA
            or join_result.get("status") != J.STATUS
            or join_result.get("signedCheckpointAndOriginalC3eFloorsMatchInCI")
            is not True
            or join_result.get("threeDistinctProcessPinsComparedInCI")
            is not True
            or any(join_result.get(key) is not False for key in J.NEGATIVE)):
        _deny("C4B_C3EN_HOST_BINDING_ORIGINAL_JOIN_REQUIRED")
    raw_state = join_inputs["controller_state"]
    fresh = join_inputs["fresh_challenge"]
    if (type(raw_state) is not dict
            or type(raw_state.get("controllerRootSha256")) is not str
            or SHA256.fullmatch(raw_state["controllerRootSha256"]) is None
            or type(fresh) is not bytes or len(fresh) != 32):
        _deny("C4B_C3EN_HOST_BINDING_CONTROLLER_ROOT_OR_NONCE_REQUIRED")
    keys = ("signedCheckpointSha256", "signedCheckpointSignatureSha256",
            "controllerTransitionSequence", "matchingFloorEpoch",
            "matchingFloorSequence")
    if (any(key not in join_result for key in keys)
            or any(type(join_result[k]) is not str
                   or SHA256.fullmatch(join_result[k]) is None
                   for k in keys[:2])
            or any(type(join_result[k]) is not int
                   or not 0 < join_result[k] < 2**53
                   for k in keys[2:])):
        _deny("C4B_C3EN_HOST_BINDING_VERIFIED_CHECKPOINT_REQUIRED")
    pid_keys = (
        "expected_installed_pid", "expected_witness_pid",
        "separately_pinned_peer_pid")
    if (any(type(join_inputs[k]) is not int
            or not 1 < join_inputs[k] < 2**31 for k in pid_keys)
            or len({join_inputs[k] for k in pid_keys}) != 3):
        _deny("C4B_C3EN_HOST_BINDING_THREE_PROCESS_ROLES_REQUIRED")
    digest_keys = ("separately_pinned_witness_sha256",
                   "expected_witness_enrollment_sha256")
    if any(type(join_inputs[k]) is not str
           or SHA256.fullmatch(join_inputs[k]) is None for k in digest_keys):
        _deny("C4B_C3EN_HOST_BINDING_WITNESS_PINS_REQUIRED")
    record = {
        "schema": SCHEMA,
        "audience": AUDIENCE,
        "scope": SCOPE,
        "hostAttestationChallengeSha256": _sha(host_attestation_challenge),
        "checkpointChallengeSha256": _sha(fresh),
        "controllerHostId": join_result["controllerHostId"],
        "controllerRootSha256": raw_state["controllerRootSha256"],
        "controllerStateSha256": _sha(_canonical(raw_state)),
        "signedCheckpointSha256": join_result["signedCheckpointSha256"],
        "signedCheckpointSignatureSha256": join_result[
            "signedCheckpointSignatureSha256"],
        "controllerTransitionSequence": join_result[
            "controllerTransitionSequence"],
        "releaseEpoch": join_result["matchingFloorEpoch"],
        "releaseSequence": join_result["matchingFloorSequence"],
        "installedOriginEvidenceSha256": _sha(_canonical(join_inputs[
            "installed_os_evidence"])),
        "canonicalOptProofSha256": _sha(_canonical(join_inputs["c4b_opt_proof"])),
        "readOnlyC3eWitnessSha256": _sha(_canonical(join_inputs[
            "read_only_witness_status"])),
        "installedStatusPid": join_inputs["expected_installed_pid"],
        "protectedWitnessPid": join_inputs["expected_witness_pid"],
        "checkpointPeerPid": join_inputs["separately_pinned_peer_pid"],
        "witnessEnrollmentSha256": join_inputs[
            "expected_witness_enrollment_sha256"],
        "checkpointSignerSha256": join_inputs[
            "separately_pinned_witness_sha256"],
    }
    encoded = _canonical(record)
    if len(encoded) > MAX_RECORD_BYTES:
        _deny("C4B_C3EN_HOST_BINDING_EXPECTED_STATEMENT_TOO_LARGE")
    return encoded


def inspect_signed_host_binding_ci_only(
    *, join_inputs: dict, controller_ledger_root: Path,
    signed_host_binding: bytes, host_binding_signature: bytes,
    independently_pinned_host_signer: Ed25519PublicKey,
    independently_pinned_host_signer_sha256: str,
    independently_issued_host_challenge: bytes,
):
    """Compare independently signed exact snapshots, all grants still OFF."""
    if (type(join_inputs) is not dict or set(join_inputs) != JOIN_KEYS
            or type(host_binding_signature) is not bytes
            or len(host_binding_signature) != 64
            or not isinstance(independently_pinned_host_signer, Ed25519PublicKey)
            or type(independently_pinned_host_signer_sha256) is not str
            or SHA256.fullmatch(independently_pinned_host_signer_sha256) is None
            or type(independently_issued_host_challenge) is not bytes
            or len(independently_issued_host_challenge) != 32):
        _deny("C4B_C3EN_HOST_BINDING_SIGNER_NONCE_AND_INPUTS_REQUIRED")
    pub = independently_pinned_host_signer.public_bytes(
        Encoding.Raw, PublicFormat.Raw)
    if not hmac.compare_digest(_sha(pub), independently_pinned_host_signer_sha256):
        _deny("C4B_C3EN_HOST_BINDING_SIGNER_PIN_REFUSED")
    if type(join_inputs["controller_state"]) is not dict:
        _deny("C4B_C3EN_HOST_BINDING_EXACT_CONTROLLER_STATE_REQUIRED")
    # Re-read actual root-owned disposable ledger instead of trusting two
    # mutually consistent stale caller snapshots. This is still local
    # root-only CI custody, NOT rollback resistance against privileged root.
    try:
        persisted = L.inspect_current_ci_only(controller_ledger_root)
    except L.Refused as exc:
        raise Refused("C4B_C3EN_HOST_BINDING_ROOT_LEDGER_REFUSED") from exc
    current = {key: persisted[key] for key in W.STATE_FIELDS}
    if not hmac.compare_digest(
            _canonical(join_inputs["controller_state"]), _canonical(current)):
        _deny("C4B_C3EN_HOST_BINDING_PROTECTED_LEDGER_STATE_CHANGED")
    root_hash = current.get("controllerRootSha256")
    witness_hash = join_inputs["separately_pinned_witness_sha256"]
    if (type(root_hash) is not str or type(witness_hash) is not str
            or SHA256.fullmatch(root_hash) is None
            or SHA256.fullmatch(witness_hash) is None
            or hmac.compare_digest(root_hash, independently_pinned_host_signer_sha256)
            or hmac.compare_digest(witness_hash, independently_pinned_host_signer_sha256)
            or hmac.compare_digest(root_hash, witness_hash)):
        _deny("C4B_C3EN_HOST_BINDING_ALL_SIGNING_ROLES_MUST_BE_DISTINCT")
    signed = _signed_record(signed_host_binding)
    try:
        independently_pinned_host_signer.verify(
            host_binding_signature, DOMAIN + signed_host_binding)
    except (InvalidSignature, ValueError) as exc:
        raise Refused("C4B_C3EN_HOST_BINDING_SIGNATURE_REFUSED") from exc
    try:
        joined = J.inspect_ci_only(**join_inputs)
    except J.Refused as exc:
        raise Refused("C4B_C3EN_HOST_BINDING_UNDERLYING_PROOFS_REFUSED") from exc
    expected = make_expected_statement_ci_only(
        join_inputs=join_inputs, join_result=joined,
        host_attestation_challenge=independently_issued_host_challenge)
    if (set(signed) != set(json.loads(expected))
            or not hmac.compare_digest(signed_host_binding, expected)):
        _deny("C4B_C3EN_HOST_BINDING_SIGNED_VS_VERIFIED_EVIDENCE_MISMATCH")
    # The socket exchange and C3e-N checks happen outside the SQLite
    # inspection transaction. Refuse if the protected controller advanced
    # or its database disappeared before returning a diagnostic result.
    # Root may still roll back BOTH observations; no production authority.
    try:
        after = L.inspect_current_ci_only(controller_ledger_root)
    except L.Refused as exc:
        raise Refused(
            "C4B_C3EN_HOST_BINDING_LEDGER_LOST_DURING_VERIFICATION") from exc
    after_state = {key: after[key] for key in W.STATE_FIELDS}
    if not hmac.compare_digest(_canonical(current), _canonical(after_state)):
        _deny("C4B_C3EN_HOST_BINDING_LEDGER_CHANGED_DURING_VERIFICATION")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "signedHostEvidenceMatchesOriginalC3eAndC4bCIOnly": True,
        "separateControllerCheckpointAndHostSignerRootsInCI": True,
        "signedHostBindingSha256": _sha(signed_host_binding),
        "verifiedC4bCheckpointSha256": joined["signedCheckpointSha256"],
        "floorEpoch": joined["matchingFloorEpoch"],
        "floorSequence": joined["matchingFloorSequence"],
        **NEGATIVE,
    }
