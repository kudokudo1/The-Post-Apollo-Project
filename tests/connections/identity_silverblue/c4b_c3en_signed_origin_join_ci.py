#!/usr/bin/env python3
"""C4b owner-only CI composition with unchanged C3e-N origin/witness check.

A *real* disposable Linux Unix socket and signature check are performed by
the merged C4b consumer. The existing protected C3e-N source independently
checks installed-service and witness-floor fixture shapes. This module
refuses mismatched floors, signer/observer process alias and authority
claims, but does not establish one signed host/seat trust chain.

All inputs/pins are disposable CI evidence. NEVER enable native sign-in.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import c4b_signed_external_checkpoint_ci as W
import c4b_witness_transport_consumer_ci as T

SCHEMA = "postapollo.identity.c4b-c3en-signed-origin-join.ci-v1"
STATUS = "C4B_C3EN_SIGNED_AND_ORIGIN_FLOORS_COMPATIBLE_NOT_BOUND"
ROOT = Path(__file__).resolve().parents[2]
C3EN_PATH = ROOT / "tests/connections/c3e_release_trust/C3eNOriginWitnessHandoff.py"
NEGATIVE = {
    "cryptographicallyJoinedInstalledHostAndExternalSigner": False,
    "operatorEnrolledWitnessPeer": False,
    "offHostWitnessKeyCustodyVerified": False,
    "independentlyDurableExternalNonceHistoryVerified": False,
    "hostAuthenticated": False,
    "canApprove": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Cross-owner diagnostic comparison did not meet its CI-only contract."""


def _deny(code):
    raise Refused(code)


def _load_c3en():
    """Import the *original*, unmodified C3e-N checker by exact repo path."""
    if not C3EN_PATH.is_file():
        _deny("C4B_C3EN_EXISTING_PROTECTED_SOURCE_MISSING")
    spec = importlib.util.spec_from_file_location(
        "c4b_readonly_existing_c3en_origin", C3EN_PATH)
    if spec is None or spec.loader is None:
        _deny("C4B_C3EN_ORIGINAL_IMPORT_REFUSED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def inspect_ci_only(
    *, socket_path, controller_state, fresh_challenge,
    separately_pinned_peer_uid, separately_pinned_peer_gid,
    separately_pinned_peer_pid, separately_pinned_witness_root,
    separately_pinned_witness_sha256,
    installed_os_evidence, c4b_opt_proof, read_only_witness_status,
    expected_installed_pid, expected_witness_pid,
    expected_witness_enrollment_sha256,
):
    """Recheck a real socket and signed history, then original C3e-N.

    C3e-N's process snapshot is independently *simulated* by a fixture.
    Signing the C4b checkpoint does NOT authenticate that C3e-N snapshot.
    The result can never become a production approval.
    """
    c3en = _load_c3en()
    # No process role may silently collapse. A C4b nonroot signed-checkpoint
    # peer is separate from the C3e root-witness and installed status PID.
    if (type(expected_installed_pid) is not int
            or type(expected_witness_pid) is not int
            or type(separately_pinned_peer_pid) is not int
            or min(expected_installed_pid, expected_witness_pid,
                   separately_pinned_peer_pid) <= 1
            or len({expected_installed_pid, expected_witness_pid,
                    separately_pinned_peer_pid}) != 3):
        _deny("C4B_C3EN_THREE_DISTINCT_PROCESS_PINS_REQUIRED")

    try:
        check = T.fetch_current_witness_ci_only(
            socket_path=socket_path, controller_state=controller_state,
            fresh_challenge=fresh_challenge,
            separately_pinned_peer_uid=separately_pinned_peer_uid,
            separately_pinned_peer_gid=separately_pinned_peer_gid,
            separately_pinned_peer_pid=separately_pinned_peer_pid,
            separately_pinned_witness_root=separately_pinned_witness_root,
            separately_pinned_witness_sha256=separately_pinned_witness_sha256)
    except T.Refused as exc:
        raise Refused("C4B_C3EN_REAL_SOCKET_OR_SIGNED_WITNESS_REFUSED") from exc
    if (check.get("unixPeerPidUidGidMatchedCallerPinsInCI") is not True
            or check.get("externalSignedCheckpointMatchedControllerInCI") is not True
            or any(check.get(k) is not False for k in T.NEGATIVE)):
        _deny("C4B_C3EN_TRANSPORT_CLAIMED_AUTHORITY")

    witness_args = check["witnessInputs"]
    # The C4b transport already verifies these bytes. Parse them AGAIN
    # before cross-checking protected C3e-N release floors, rather than
    # trusting a caller-provided claim or unsigned transport metadata.
    signed = W._proof(witness_args["signed_checkpoint"])
    if (type(controller_state) is not dict
            or set(controller_state) != W.STATE_FIELDS
            or signed["hostId"] != controller_state["hostId"]):
        _deny("C4B_C3EN_SIGNED_CONTROLLER_HOST_MISMATCH")
    floor_epoch = signed["minimumReleaseEpoch"]
    floor_sequence = signed["minimumReleaseSequence"]

    origin = c3en.inspect(
        installed_os_evidence=installed_os_evidence,
        c4b_opt_proof=c4b_opt_proof,
        read_only_witness_status=read_only_witness_status,
        expected_installed_pid=expected_installed_pid,
        expected_witness_pid=expected_witness_pid,
        expected_witness_enrollment_sha256=expected_witness_enrollment_sha256,
        minimum_policy_epoch=floor_epoch,
        minimum_release_sequence=floor_sequence)
    if (type(origin) is not dict
            or origin.get("schema") != c3en.SCHEMA
            or origin.get("status") != c3en.STATUS
            or origin.get("testEvidenceCompatible") is not True
            or any(origin.get(k) is not False for k in (
                "hostAuthenticated", "canApprove", "credentialActionsEnabled",
                "productionAuthority"))):
        _deny("C4B_C3EN_ORIGINAL_PROTECTED_ORIGIN_REFUSED")
    if (type(origin.get("witness_floor_epoch")) is not int
            or type(origin.get("witness_floor_sequence")) is not int
            or origin["witness_floor_epoch"] != floor_epoch
            or origin["witness_floor_sequence"] != floor_sequence):
        # Exact equality is a deliberately conservative CI contract. Real
        # release-floor supersession requires protected C3e owner policy.
        _deny("C4B_C3EN_SIGNED_VS_PROTECTED_RELEASE_FLOOR_MISMATCH")

    if (origin.get("installed_status_service_pid") != expected_installed_pid
            or origin.get("separate_witness_process_pid") != expected_witness_pid):
        _deny("C4B_C3EN_PROTECTED_PROCESS_IDENTITY_CHANGED")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "threeDistinctProcessPinsComparedInCI": True,
        "signedCheckpointAndOriginalC3eFloorsMatchInCI": True,
        "controllerHostId": signed["hostId"],
        "controllerTransitionSequence": signed["transitionSequence"],
        "signedCheckpointSha256": hashlib.sha256(
            witness_args["signed_checkpoint"]).hexdigest(),
        "matchingFloorEpoch": floor_epoch,
        "matchingFloorSequence": floor_sequence,
        **NEGATIVE,
    }
