#!/usr/bin/env python3
"""C3e-Z: CI-only composition of Identity signed release and C3e-Y host evidence.

The exact release package and gateway entrypoint digests, receipt signing key,
epoch and sequence must agree BEFORE C3e-Y consumes its pre-issued challenge.
All "independently" named pins are provided by a disposable CI caller, not
independent installed-host/root authority. Never authorize real login.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EZ_REQUIRED_VALIDATOR_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Y = _load("c3ez_signed_host", HERE / "C3eYSignedHostChallenge.py")
I = _load("c3ez_identity_release",
          ROOT / "services/identity/silverblue_release_candidate_v1.py")

SCHEMA = "postapollo.connections.c3ez-release-bound-host-denial.ci-v1"
GATEWAY_ENTRYPOINT = I.PREFIX + "identity-gateway-ci"
NEGATIVE = {
    "independentlyEnrolledReleaseRoot": False,
    "independentlyEnrolledWitnessKey": False,
    "independentlyEnrolledReceiptKey": False,
    "installedHostEvidenceAuthenticated": False,
    "externalChallengeCustodyVerified": False,
    "externalRollbackResistanceVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """Refused test-only evidence; no host/user authority may be inferred."""


def _deny(code: str):
    raise Refused(code)


def inspect_release_and_consume(*,
                                signed_release: bytes,
                                release_signature: bytes,
                                independently_pinned_release_root,
                                independently_measured_files: dict,
                                ledger_root,
                                challenge: bytes,
                                signed_statement: bytes,
                                witness_signature: bytes,
                                independently_pinned_witness_key,
                                independently_pinned_receipt_key,
                                evidence_line: bytes,
                                signed_receipts,
                                independently_measured: dict,
                                expected_release_epoch: int,
                                expected_release_sequence: int):
    """Fail closed if independently supplied CI release and runtime pins differ.

    Perform all static release signature, source hash, epoch, receipt key,
    signer-role and production-false checks BEFORE the Y one-time consumption.
    This function has no native process, network, credential or consent path.
    """
    if (type(independently_measured) is not dict
            or type(independently_measured_files) is not dict):
        _deny("EXACT_INDEPENDENT_PIN_DICTIONARIES_REQUIRED")

    # Copy caller-owned pin dictionaries before any signature work; neither
    # source may change what the later host verifier receives during a call.
    pins = dict(independently_measured)
    file_pins = dict(independently_measured_files)
    if set(file_pins) != I.FILES:
        _deny("RELEASE_FILE_ROSTER_REFUSED")
    try:
        Y.X._validate_pins(pins)
        receipt_key = Y._public_bytes(independently_pinned_receipt_key)
        root_key = Y._public_bytes(independently_pinned_release_root)
        witness_key = Y._public_bytes(independently_pinned_witness_key)
    except (Y.X.Refused, Y.Refused) as exc:
        raise Refused("INDEPENDENT_PIN_OR_SIGNER_REFUSED") from exc

    # Three different cryptographic key roles, even for disposable CI.
    if len({root_key, witness_key, receipt_key}) != 3:
        _deny("RELEASE_WITNESS_RECEIPT_SIGNERS_MUST_BE_DISTINCT")
    if (pins["unit"] != I.UNIT
            or file_pins[GATEWAY_ENTRYPOINT] != pins["entrypointSha256"]):
        _deny("INSTALLED_GATEWAY_SOURCE_PIN_DISAGREES")

    try:
        release = I.assess_synthetic_release(
            signed_release=signed_release,
            signature=release_signature,
            independently_pinned_root=independently_pinned_release_root,
            independently_pinned_receipt_key=receipt_key,
            independently_measured_rpm_sha256=pins["rpmSha256"],
            independently_measured_files=file_pins,
            minimum_epoch=expected_release_epoch,
            minimum_sequence=expected_release_sequence)
    except (I.CandidateRefused, ValueError, TypeError) as exc:
        raise Refused("SIGNED_RELEASE_CANDIDATE_REFUSED") from exc

    # The release consumer accepts an epoch/sequence AT LEAST the minimum.
    # This composer requires equality with the issued challenge and signed
    # C3e-Y record, never a different future/rollback release.
    if (type(expected_release_epoch) is not int
            or type(expected_release_sequence) is not int
            or (release.epoch, release.sequence)
            != (expected_release_epoch, expected_release_sequence)
            or release.package_sha256 != pins["rpmSha256"]
            or release.receipt_key_sha256 != Y._hash(receipt_key)
            or any(getattr(release, field) is not False for field in (
                "installed_guest_measured", "host_authenticated",
                "production_authority", "can_begin_sign_in",
                "credential_actions_enabled"))):
        _deny("RELEASE_FLOOR_OR_AUTHORITY_DISAGREES")

    # Y independently verifies the complete witness signed statement,
    # pinned host record and four Ed25519 denials BEFORE consuming challenge.
    # Failed release verification above must leave that challenge ISSUED.
    try:
        receipt = Y.inspect_and_consume(
            ledger_root=ledger_root, challenge=challenge,
            signed_statement=signed_statement,
            witness_signature=witness_signature,
            independently_pinned_witness_key=independently_pinned_witness_key,
            independently_pinned_receipt_key=independently_pinned_receipt_key,
            evidence_line=evidence_line, signed_receipts=signed_receipts,
            independently_measured=pins,
            expected_release_epoch=expected_release_epoch,
            expected_release_sequence=expected_release_sequence)
    except Y.Refused as exc:
        raise Refused("C3EY_COMPLETE_HOST_RECORD_REFUSED") from exc
    if (receipt.get("completeHostRecordSignatureVerifiedInCI") is not True
            or receipt.get("separatelyIssuedChallengeConsumedInRootLocalCI")
            is not True
            or any(receipt.get(k) is not False
                   for k in ("externalIssuerCustodyVerified",
                             "externalRollbackResistanceVerified",
                             "independentHostOriginVerified", *Y.X.NEGATIVE))):
        _deny("C3EY_RECEIPT_NOT_DENY_ONLY")

    return {
        "schema": SCHEMA,
        "releaseSourceAndRuntimePinsMatchedInCI": True,
        "releaseReceiptSignerMatchedInCI": True,
        "fullRecordChallengeConsumedInRootLocalCI": True,
        **NEGATIVE,
        # Intentionally inherit additional preexisting C3e-X false flags.
        **Y.X.NEGATIVE,
    }
