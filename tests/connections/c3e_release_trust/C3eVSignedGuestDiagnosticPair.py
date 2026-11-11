#!/usr/bin/env python3
"""C3e-V: CI-only consistency check between C4d UART and C3e-Q signed claims.

This is NOT a guest-origin attestor. The C4B_OBSERVED line is unsigned
self-observation, and the separately pinned C3e-Q signer is disposable CI.
Passing proves only that a valid CI-signed, challenge-bound statement and
a bounded diagnostic record agree with caller-provided expected values.

The issuer custody, origin of those expected values, R's protected durable
one-use challenge and real host authority are NOT supplied by this module.
No credential or host authentication result may be inferred or granted.
"""
from __future__ import annotations

import hashlib
import hmac
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EV_REQUIRED_RECEIVER_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Q = _load("c3ev_c3eq", "C3eQSignedGuestEvidence.py")
U = _load("c3ev_c3eu", "C3eUObservedGuestImport.py")

SCHEMA = "postapollo.connections.c3ev-signed-guest-diagnostic-pair.ci-v1"

# Both schemas refer to the SAME fake Connections status service. They are
# explicitly not the Identity Gateway service and not a production witness.
MATCHED = {
    "signed_rpm_sha256": "release_rpm_sha256",
    "signed_script_sha256": "signed_script_sha256",
    "running_script_sha256": "running_script_sha256",
    "interpreter_sha256": "interpreter_sha256",
    "service_pid": "service_pid",
    "dbus_owner_pid": "dbus_owner_pid",
    "process_start_ticks": "process_start_ticks",
    "service_uid": "service_uid",
    "service_gid": "service_gid",
    "systemd_unit": "systemd_unit",
    "selinux_enforcing": "selinux_enforcing",
}


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def inspect_pair(*, diagnostic_line: bytes, challenge: bytes,
                 signed_evidence: Path, signature: Path, public_key: Path,
                 pinned_signer: str,
                 expected_rpm_sha256: str,
                 expected_script_sha256: str,
                 expected_interpreter_sha256: str,
                 expected_service_pid: int,
                 expected_start_ticks: str,
                 expected_service_uid: int,
                 expected_service_gid: int):
    """Compare existing bounded receivers; return a diagnostic ONLY.

    The expected pins and the signing key are supplied by the caller for CI.
    Passing cannot establish that these originated from independent custody.
    Never source them from the untrusted guest line or signed record itself.
    """
    try:
        # Gate the untrusted plain UART record with the independently supplied
        # test pins before touching the signed message.
        diagnostic = U.inspect(
            report_line=diagnostic_line,
            independent_signed_rpm_sha256=expected_rpm_sha256,
            independent_signed_script_sha256=expected_script_sha256,
            independent_interpreter_sha256=expected_interpreter_sha256,
            expected_service_pid=expected_service_pid,
            expected_start_ticks=expected_start_ticks,
            expected_service_uid=expected_service_uid,
            expected_service_gid=expected_service_gid,
        )
        # Snapshot before verification, then bind that snapshot to the SHA of
        # Q's EXACT signature-verified byte snapshot. This avoids trusting a
        # new pathname read after signature verification.
        snapshot = Q.safe_bytes(
            signed_evidence, Q.MAX_EVIDENCE, "SIGNED_RECORD_FILE_UNSAFE")
        verifier = Q.OneUseTestChallenge(challenge)
        signed = verifier.verify(
            evidence=signed_evidence,
            signature=signature,
            public_key=public_key,
            pinned_signer=pinned_signer,
            expected_rpm_sha256=expected_rpm_sha256,
            expected_script_sha256=expected_script_sha256,
            expected_interpreter_sha256=expected_interpreter_sha256,
            expected_service_pid=expected_service_pid,
            expected_start_ticks=expected_start_ticks,
        )
        if (signed.get("signedEvidenceValidInCI") is not True
                or signed.get("challengeConsumedInMemory") is not True
                or type(signed.get("verifiedEvidenceSHA256")) is not str
                or not hmac.compare_digest(
                    hashlib.sha256(snapshot).hexdigest(),
                    signed["verifiedEvidenceSHA256"])):
            deny("VERIFIED_SIGNED_SNAPSHOT_DISAGREES")
        # Only decode the previously captured bytes, whose digest was
        # returned by the same Q signature verification. Q enforces the exact
        # sorted-compact signing format, schema, purpose and false grant flags.
        statement = Q.exact_json(snapshot)
        guest = U._decode(diagnostic_line)
    except U.Refused as exc:
        raise Refused("C4D_DIAGNOSTIC_REFUSED:" + str(exc)) from exc
    except Q.Refused as exc:
        raise Refused("C3EQ_SIGNED_CLAIM_REFUSED:" + str(exc)) from exc

    for guest_field, signed_field in MATCHED.items():
        # Equality with a cryptographically signed CLAIM is not a trusted
        # measurement. The signer and expected pins still need independent
        # real-world enrollment, attestation and anti-replay custody.
        if guest[guest_field] != statement[signed_field]:
            deny("SIGNED_CLAIM_AND_GUEST_REPORT_DISAGREE")
    if (diagnostic["hostAuthenticated"] is not False
            or signed["hostAuthenticated"] is not False
            or signed["productionAuthority"] is not False):
        deny("TEST_RECEIPT_CLAIMS_PRODUCTION_AUTHORITY")

    return {
        "schema": SCHEMA,
        "c4dDiagnosticSchemaMatchedInCI": True,
        "c3eqSignedClaimVerifiedInCI": True,
        "signedClaimAndPlainGuestReportAgreeInCI": True,
        # This verifies neither the issuer's production custody nor the
        # claimed guest/kernel reality and does not use R's durable ledger.
        "externalIssuerCustodyVerified": False,
        "durableChallengeConsumptionVerified": False,
        "signedGuestOriginAuthenticated": False,
        "evidenceCryptographicallyAttested": False,
        "installedGuestMeasured": False,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }
