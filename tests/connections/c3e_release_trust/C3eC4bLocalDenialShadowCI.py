#!/usr/bin/env python3
"""DOC 1: connect existing local C3e challenge to C4b signed denial in CI.

This is an untrusted diagnostic shadow. A correctly signed DENIAL from a
locally generated, rollbackable challenge NEVER becomes enrolled host origin,
current independent history, protected terminal settlement, consent or Sign-In.
No new signer, SQL writer, network transport or production admission.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
OTHER = HERE.parent / "identity_silverblue"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_C4B_REQUIRED_ORIGINAL_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


S = _load("c3e_c4b_shadow_original_storage",
          HERE / "C3eStorageIndependentTrustBoundary.py")
E = _load("c3e_c4b_shadow_original_denial",
          OTHER / "c4b_raw_challenge_evidence_candidate_ci.py")

SCHEMA = "postapollo.connections.c3e-c4b-local-denial-shadow.ci-v1"
STATUS = "LOCAL_C3E_C4B_SIGNED_DENIAL_NOT_INDEPENDENT_TRUST"
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DENIED = {
    **S.DENIED,
    **E.DENIED,
    "operatorEnrolledCurrentIssuerVerified": False,
    "actualHostProducerIdentityVerified": False,
    "nativeSeatSelectionVerified": False,
    "protectedChallengeSpentVerified": False,
    "protectedTerminalReceiptVerified": False,
    "identityCommandSettled": False,
    "safeToRetry": False,
    "timewC5AuthorizationVerified": False,
    "productionSignInAllowed": False,
}


class Refused(ValueError):
    """Untrusted bridge inputs or attempted authority promotion."""


def _deny(code: str):
    raise Refused(code)


def _exact_record(record: dict, fields: set[str], *,
                  schema: str, status: str, source: str | None,
                  denied: dict):
    if type(record) is not dict or set(record) != fields:
        _deny("C3E_C4B_SHADOW_EXTRA_OR_MISSING_FIELDS")
    if record["schema"] != schema or record["status"] != status:
        _deny("C3E_C4B_SHADOW_WRONG_SCHEMA_OR_STATUS")
    if source is not None and record["source"] != source:
        _deny("C3E_C4B_SHADOW_WRONG_SOURCE")
    if any(record[k] is not False for k in denied):
        _deny("C3E_C4B_SHADOW_ATTEMPTED_AUTHORITY_PROMOTION")


def inspect_ci_only(*, local: S.TrustBoundary,
                    protected: S.TrustBoundary,
                    local_challenge: bytes, signed_denial: bytes):
    """Never promote local signed-denial correspondence to protected custody.

    All calls reuse original imported DOC 1 and DOC 2 implementations. The
    protected instance must be independently configured to HOLD with no local
    SQLite fallback. No challenge is newly issued, spent or authorized here.
    """
    if (type(local) is not S.TrustBoundary
            or local._mode != S.LOCAL_DEVELOPMENT
            or type(local._local) is not S.LocalSQLiteTestAdapter
            or type(protected) is not S.TrustBoundary
            or protected._mode != S.PROTECTED_REQUIRED
            or protected._local is not None):
        _deny("C3E_C4B_SHADOW_EXACT_LOCAL_AND_PROTECTED_MODES_REQUIRED")
    if type(local_challenge) is not bytes or len(local_challenge) != 32:
        _deny("C3E_C4B_SHADOW_LOCAL_EXACT_CHALLENGE_REQUIRED")
    if type(signed_denial) is not bytes:
        _deny("C3E_C4B_SHADOW_EXACT_SIGNED_DENIAL_BYTES_REQUIRED")

    try:
        snapshot = local.read_current_snapshot()
        outcome = local.lookup_terminal_outcome(local_challenge)
        hold = protected.protected_required_status()
        signed = E.inspect_raw_challenge_denial_ci_only(
            raw_challenge=local_challenge, serial=signed_denial)
    except (S.Refused, S.L.Refused, E.Refused) as exc:
        raise Refused("C3E_C4B_SHADOW_UNTRUSTED_INPUT_OR_DENIAL_REFUSED") from exc

    _exact_record(
        snapshot, {"schema", "status", "source",
                   "testHeadSha256", "testSequence", *S.DENIED},
        schema=S.SCHEMA, status=S.STATUS_LOCAL,
        source=S.LOCAL_DEVELOPMENT, denied=S.DENIED)
    _exact_record(
        outcome, {"schema", "status", "source",
                  "testState", "testHeadSha256", *S.DENIED},
        schema=S.SCHEMA, status=S.STATUS_LOCAL,
        source=S.LOCAL_DEVELOPMENT, denied=S.DENIED)
    _exact_record(
        hold, {"schema", "status", "source", *S.DENIED},
        schema=S.SCHEMA, status=S.STATUS_HOLD,
        source=S.PROTECTED_REQUIRED, denied=S.DENIED)
    _exact_record(
        signed, {"schema", "status", "rawChallengeSha256",
                 "encodedCommandNonceSha256", "receiptFrameSha256",
                 "runtimePublicKeySha256",
                 "ciOnlyOriginalSignedDenialVerified", *E.DENIED},
        schema=E.SCHEMA, status=E.STATUS,
        source=None, denied=E.DENIED)
    if signed["ciOnlyOriginalSignedDenialVerified"] is not True:
        _deny("C3E_C4B_SHADOW_SIGNED_DENIAL_NOT_VERIFIED")
    state, observed_head = outcome["testState"], outcome["testHeadSha256"]
    if (type(state) is not str or state not in ("issued", "consumed")
            or (state == "issued" and observed_head is not None)
            or (state == "consumed" and
                (type(observed_head) is not str
                 or HEX64.fullmatch(observed_head) is None))
            or type(snapshot["testSequence"]) is not int
            or snapshot["testSequence"] < 1
            or type(snapshot["testHeadSha256"]) is not str
            or HEX64.fullmatch(snapshot["testHeadSha256"]) is None):
        _deny("C3E_C4B_SHADOW_LOCAL_OBSERVATION_MALFORMED")
    for k in ("rawChallengeSha256", "encodedCommandNonceSha256",
              "receiptFrameSha256", "runtimePublicKeySha256"):
        if type(signed[k]) is not str or HEX64.fullmatch(signed[k]) is None:
            _deny("C3E_C4B_SHADOW_DENIAL_DIGEST_MALFORMED")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "localObservedState": state,
        "localObservedHeadSha256": snapshot["testHeadSha256"],
        "localObservedSequence": snapshot["testSequence"],
        "ciOnlySignedDenialFrameSha256": signed["receiptFrameSha256"],
        "ciOnlyLocalRawChallengeSha256": signed["rawChallengeSha256"],
        "protectedCustodianStatus": S.STATUS_HOLD,
        "next": "HOLD_NO_PROTECTED_CUSTODY_OR_SIGNIN",
        **DENIED,
    }


def production_admission(*_args, **_kwargs):
    _deny("C3E_C4B_SHADOW_NO_INDEPENDENT_CUSTODY_OR_PRODUCTION")
