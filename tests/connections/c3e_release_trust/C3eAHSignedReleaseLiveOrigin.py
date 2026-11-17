#!/usr/bin/env python3
"""C3e-AH: pair verified C4b CI release bytes with real Linux process observation.

Both existing verifiers are unchanged, read-only inputs. The signed manifest
identifies the expected gateway script bytes; the separate C3e-AG observer
checks actual /proc process state and file bytes. This alone DOES NOT provide
signed remote host evidence, independent key custody or production authority.
"""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EAH_REQUIRED_VERIFIER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

I = _load("c3eah_identity_signed_release", REPO / "services/identity/silverblue_release_candidate_v1.py")
AG = _load("c3eah_real_kernel_observer", HERE / "C3eAGIdentityKernelObserver.py")

SCHEMA = "postapollo.connections.c3eah-signed-release-live-observation.ci-v1"
GATEWAY = I.PREFIX + "identity-gateway-ci"
NEGATIVE = {
    "independentlySignedRemoteKernelWitnessVerified": False,
    "independentlyInstalledSilverblueGatewayAuthenticated": False,
    "independentlyEnrolledOperatorReleaseRoot": False,
    "externalIssuerCustodyVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}

class Refused(ValueError):
    """A signed source or locally observed process did not agree."""

def _deny(reason: str):
    raise Refused(reason)

def inspect_ci_only(
    *, signed_release: bytes, release_signature: bytes,
    independently_pinned_release_root,
    independently_pinned_receipt_key: bytes,
    independently_measured_rpm_sha256: str,
    independently_measured_release_files: dict,
    minimum_release_epoch: int, minimum_release_sequence: int,
    expected_process: dict, mode: str = "fixture",
):
    """Refuse an unsigned script/real-process mismatch, with no grant path.

    Caller-provided expected measurements and signing root are only disposable
    CI pins. No independently enrolled host/root or verified RPM installation
    is created, and the process observation cannot be exported as attestation.
    """
    if (type(independently_measured_release_files) is not dict
            or type(expected_process) is not dict
            or type(minimum_release_epoch) is not int
            or type(minimum_release_sequence) is not int
            or mode not in ("fixture", "c4b-guest-candidate")):
        _deny("C3EAH_INDEPENDENT_SOURCE_PINS_REQUIRED")
    # Freeze caller-owned inputs before verifying source and then kernel
    # identity. No callback may replace the pins between these checks.
    files = dict(independently_measured_release_files)
    pins = dict(expected_process)
    if set(pins) != AG.EXPECTED:
        _deny("C3EAH_EXACT_RUNTIME_SNAPSHOT_REQUIRED")
    if (files.get(GATEWAY) != pins.get("entrypointSha256")
            or type(files.get(GATEWAY)) is not str):
        _deny("C3EAH_SIGNED_RELEASE_SCRIPT_HASH_DISAGREES_WITH_PROCESS_PIN")
    if (mode == "c4b-guest-candidate"
            and (pins["scriptPath"] != GATEWAY
                 or pins["unit"] != I.UNIT)):
        _deny("C3EAH_REAL_GUEST_INSTALLED_SCRIPT_SCOPE_REFUSED")
    try:
        candidate = I.assess_synthetic_release(
            signed_release=signed_release,
            signature=release_signature,
            independently_pinned_root=independently_pinned_release_root,
            independently_pinned_receipt_key=independently_pinned_receipt_key,
            independently_measured_rpm_sha256=independently_measured_rpm_sha256,
            independently_measured_files=files,
            minimum_epoch=minimum_release_epoch,
            minimum_sequence=minimum_release_sequence,
        )
    except I.CandidateRefused as exc:
        raise Refused("C3EAH_SIGNED_C4B_RELEASE_REFUSED") from exc
    if any((
        candidate.installed_guest_measured,
        candidate.host_authenticated,
        candidate.production_authority,
        candidate.can_begin_sign_in,
        candidate.credential_actions_enabled,
    )):
        _deny("C3EAH_IDENTITY_CANDIDATE_AUTHORITY_PROMOTION_REFUSED")
    try:
        observation = AG.observe_ci_only(expected=pins, mode=mode)
    except AG.Refused as exc:
        raise Refused("C3EAH_REAL_PROCESS_OBSERVATION_REFUSED") from exc
    if (observation.get("kernelProcessFieldsMatchCallerPinsInCI") is not True
            or observation.get("sourceScriptFileMatchesCallerPinInCI") is not True
            or observation.get("realLinuxPidAndExecutableObservedInDisposableCI") is not True
            or any(observation.get(k) is not False for k in AG.NEGATIVE)):
        _deny("C3EAH_OBSERVER_AUTHORITY_PROMOTION_REFUSED")
    return {
        "schema": SCHEMA,
        "state": "SIGNED_C4B_RELEASE_MATCHES_LOCAL_PROCESS_DIAGNOSTIC_ONLY",
        "signedReleaseAndRealProcessScriptBytesMatchInCI": True,
        "realKernelProcessMatchesCallerPinsInCI": True,
        "c4bOfficialSilverblueHostNotAttested":
            mode == "c4b-guest-candidate",
        "releaseEpoch": candidate.epoch,
        "releaseSequence": candidate.sequence,
        "releaseSha256": hashlib.sha256(signed_release).hexdigest(),
        "gatewayEntrySha256": files[GATEWAY],
        **AG.NEGATIVE,
        **NEGATIVE,
    }
