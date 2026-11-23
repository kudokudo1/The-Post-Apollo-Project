#!/usr/bin/env python3
"""C4b signed CI denial ↔ original C3e protected-HOLD compatibility.

Fixture-only: caller-supplied guest public key and nonce cannot authorize an
installed host, live seat, independent custodian, C5 or Sign-In.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_controller_challenge_ci as C4B

SOURCE = ROOT / "tests/connections/c3e_release_trust/C3eStorageIndependentTrustBoundary.py"
_spec = importlib.util.spec_from_file_location("doc2_unmodified_c3e_storage", SOURCE)
if _spec is None or _spec.loader is None:
    raise RuntimeError("C4B_C3E_REQUIRED_CUSTODY_BOUNDARY_MISSING")
C3E = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = C3E
_spec.loader.exec_module(C3E)

SCHEMA = "postapollo.identity.c4b-c3e-protected-hold-compat.ci-v1"
STATUS = "C4B_VALID_CI_DENIAL_C3E_PROTECTED_CUSTODIAN_UNAVAILABLE_HOLD"
DIGEST = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DENIED = {
    **C4B.NEGATIVE,
    **C3E.DENIED,
    "realCustodianVerified": False,
}

class Refused(ValueError):
    """Unverified receipt or attempted cross-boundary authority promotion."""

def _deny(reason):
    raise Refused(reason)

def inspect_ci_only(*, serial: bytes, controller_challenge: str):
    """Verify original signed denial, but require independent custody HOLD."""
    try:
        proof = C4B.inspect_ci_only(
            serial=serial, controller_challenge=controller_challenge,
        )
    except C4B.Refused as exc:
        raise Refused("C4B_C3E_ORIGINAL_SIGNED_DENIAL_REFUSED") from exc
    expected_proof = {
        "schema", "freshControllerNonceInActualSignedBeginDenialInCI",
        "publicKeyVerifiedOnlyForThisCIReceipt",
        "controllerChallengeSha256", "receiptFrameSha256",
        "runtimePublicKeySha256", *C4B.NEGATIVE,
    }
    if type(proof) is not dict or set(proof) != expected_proof:
        _deny("C4B_C3E_ORIGINAL_PROOF_FIELDS_REFUSED")
    if (proof["schema"] != C4B.SCHEMA
            or proof["freshControllerNonceInActualSignedBeginDenialInCI"] is not True
            or proof["publicKeyVerifiedOnlyForThisCIReceipt"] is not True
            or any(proof[key] is not False for key in C4B.NEGATIVE)
            or any(type(proof[key]) is not str
                   or DIGEST.fullmatch(proof[key]) is None
                   for key in ("controllerChallengeSha256",
                               "receiptFrameSha256", "runtimePublicKeySha256"))):
        _deny("C4B_C3E_ORIGINAL_PROOF_ATTEMPTED_PROMOTION")

    # Deliberately no SQLite adapter: protected mode cannot silently fall back.
    protected = C3E.TrustBoundary(required_mode=C3E.PROTECTED_REQUIRED)
    hold = protected.protected_required_status()
    expected_hold = {"schema", "status", "source", *C3E.DENIED}
    if type(hold) is not dict or set(hold) != expected_hold:
        _deny("C4B_C3E_PROTECTED_STATUS_FIELDS_REFUSED")
    if (hold["schema"] != C3E.SCHEMA
            or hold["status"] != C3E.STATUS_HOLD
            or hold["source"] != C3E.PROTECTED_REQUIRED
            or any(hold[k] is not False for k in C3E.DENIED)):
        _deny("C4B_C3E_PROTECTED_STATUS_MUST_HOLD")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "c4bCiReceiptMatchesCallerNonceDiagnostic": True,
        "c3eProtectedCustodianUnavailable": True,
        "controllerChallengeSha256": proof["controllerChallengeSha256"],
        "receiptFrameSha256": proof["receiptFrameSha256"],
        "runtimePublicKeySha256": proof["runtimePublicKeySha256"],
        **DENIED,
    }
