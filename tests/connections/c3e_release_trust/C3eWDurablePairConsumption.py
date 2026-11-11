#!/usr/bin/env python3
"""C3e-W: disposable CI-only V pair check BEFORE R durable challenge consume.

A C4d UART record is still guest-origin plaintext; Q's independently pinned
signer is a disposable test signer. Pair consistency plus root-local SQLite
one-use challenge consumption is NOT independent host attestation, an external
rollback-resistant ledger, C5 consent or provider credential authority.

The protected CI runner takes bounded, nofollow snapshots of the signed
message, signature and test public key into its own private root-only
directory. V and R both verify those same snapshots. No re-read of mutable
caller-owned original paths occurs after snapshotting.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EW_REQUIRED_RECEIVER_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = _load("c3ew_pair", "C3eVSignedGuestDiagnosticPair.py")
R = _load("c3ew_ledger", "C3eRDurableChallengeLedger.py")

SCHEMA = "postapollo.connections.c3ew-durable-pair-consumption.ci-v1"
NEGATIVE = (
    "signedGuestOriginAuthenticated", "evidenceCryptographicallyAttested",
    "installedGuestMeasured", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
)


class Refused(Exception):
    pass


def deny(code: str):
    raise Refused(code)


def _snapshot(original: Path, destination: Path, ceiling: int, code: str):
    """Copy one caller-controlled file ONCE into a root-private CI directory."""
    try:
        raw = V.Q.safe_bytes(Path(original), ceiling, code)
        # The parent is a fresh mode-0700 directory under R's mode-0700 root.
        # Exclusive create refuses an unexpected pre-existing destination.
        with destination.open("xb") as out:
            destination.chmod(0o600)
            out.write(raw)
    except V.Q.Refused as exc:
        raise Refused("SIGNED_SOURCE_UNSAFE:" + str(exc)) from exc
    except OSError as exc:
        raise Refused("CI_PRIVATE_SNAPSHOT_REFUSED") from exc
    return destination


def inspect_and_consume(*, ledger_root: Path, diagnostic_line: bytes,
                        challenge: bytes, signed_evidence: Path,
                        signature: Path, public_key: Path, pinned_signer: str,
                        expected_rpm_sha256: str,
                        expected_script_sha256: str,
                        expected_interpreter_sha256: str,
                        expected_service_pid: int,
                        expected_start_ticks: str,
                        expected_service_uid: int,
                        expected_service_gid: int):
    """Fail-closed CI composition: V pair check, then R single-use consume.

    ledger_root must already be initialized by the disposable root CI
    supervisor. Never bootstrap a missing ledger, issue a challenge from the
    untrusted guest, or derive expected pins from the guest report itself.
    """
    try:
        ledger = R.DurableTestVerifier(Path(ledger_root))
    except (R.Refused, OSError, ValueError, TypeError) as exc:
        raise Refused("DURABLE_CI_LEDGER_UNAVAILABLE") from exc
    try:
        with tempfile.TemporaryDirectory(
                prefix="c3ew-snapshot-", dir=ledger.root) as temp:
            private = Path(temp)
            private.chmod(0o700)
            evidence = _snapshot(
                signed_evidence, private / "evidence.json",
                V.Q.MAX_EVIDENCE, "EVIDENCE_FILE_UNSAFE")
            detached = _snapshot(
                signature, private / "evidence.sig",
                V.Q.MAX_SIG, "SIGNATURE_FILE_UNSAFE")
            pub = _snapshot(
                public_key, private / "signer.asc",
                V.Q.MAX_PUBLIC, "PUBLIC_KEY_UNSAFE")
            common = dict(
                diagnostic_line=diagnostic_line,
                challenge=challenge,
                signed_evidence=evidence,
                signature=detached,
                public_key=pub,
                pinned_signer=pinned_signer,
                expected_rpm_sha256=expected_rpm_sha256,
                expected_script_sha256=expected_script_sha256,
                expected_interpreter_sha256=expected_interpreter_sha256,
                expected_service_pid=expected_service_pid,
                expected_start_ticks=expected_start_ticks,
            )
            # V compares the signed Q claim to U's strictly bounded C4d
            # diagnostic. A failure MUST leave R's challenge unconsumed.
            pair = V.inspect_pair(
                **common, expected_service_uid=expected_service_uid,
                expected_service_gid=expected_service_gid)
            if (pair.get("signedClaimAndPlainGuestReportAgreeInCI") is not True
                    or any(pair.get(k) is not False for k in NEGATIVE)):
                deny("PAIR_NOT_DENY_ONLY")
            # R performs its own real detached-signature check against the
            # *same root-private files*, then atomically conditionally
            # consumes the issued challenge in root-owned SQLite.
            receipt = ledger.consume(
                challenge, evidence=evidence, signature=detached,
                public_key=pub, pinned_signer=pinned_signer,
                expected_rpm_sha256=expected_rpm_sha256,
                expected_script_sha256=expected_script_sha256,
                expected_interpreter_sha256=expected_interpreter_sha256,
                expected_service_pid=expected_service_pid,
                expected_start_ticks=expected_start_ticks)
            if (receipt.get("challengeConsumedDurablyInCI") is not True
                    or receipt.get("signedEvidenceValidInCI") is not True
                    or any(receipt.get(k) is not False
                           for k in NEGATIVE if k in receipt)):
                deny("DURABLE_RECEIPT_NOT_DENY_ONLY")
    except V.Refused as exc:
        raise Refused("C3EV_PAIR_REFUSED:" + str(exc)) from exc
    except R.Refused as exc:
        raise Refused("C3ER_DURABLE_REFUSED:" + str(exc)) from exc
    return {
        "schema": SCHEMA,
        "signedAndDiagnosticPairMatchedInCI": True,
        "challengeConsumedDurablyInCI": True,
        # R is ROOT-LOCAL disposable SQLite. An independent privileged
        # rollback-resistant authority is still missing.
        "externalIssuerCustodyVerified": False,
        "externalRollbackResistanceVerified": False,
        "signedGuestOriginAuthenticated": False,
        "evidenceCryptographicallyAttested": False,
        "installedGuestMeasured": False,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }
