#!/usr/bin/env python3
"""DOC 1: read-only local C3e IPC frames are NEVER protected settlement receipts.

This is a pure, CI-only negative classifier, not a command transport.
It verifies some existing disposable IPC diagnostic shapes to distinguish
observed read-only data from no response, but NEVER infers commit, noncommit,
an independent terminal receipt, safe retry, C5 intent or Sign-In admission.
DOC 6 owns Identity Center native command-delivery settlement, not this file.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_IPC_SETTLEMENT_EXISTING_PROBE_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P = _load("c3e_ipc_settlement_existing_readonly_probe",
          HERE / "C3eLocalReadOnlyIpcProbe.py")

SCHEMA = "postapollo.connections.c3e-ipc-nonsettlement-ci-v1"
RECEIVED_DIAGNOSTIC = "OBSERVED_LOCAL_DIAGNOSTIC_NOT_SETTLEMENT"
RECEIVED_REFUSAL = "OBSERVED_IPC_REFUSAL_NOT_SETTLEMENT"
NO_VERIFIED_FRAME = "NO_VERIFIED_IPC_FRAME_OUTCOME_UNKNOWN_HOLD"
OPERATIONS = frozenset(("SNAPSHOT", "OUTCOME", "CUSTODIAN_STATUS"))
DELIVERY = frozenset(("COMPLETE_FRAME", "NO_REPLY", "TIMEOUT", "EOF",
                      "TRUNCATED_FRAME", "CHILD_EXIT", "SEND_ERROR"))
HEX32 = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DENIED = {
    **P.S.DENIED,
    "protectedTerminalReceiptVerified": False,
    "protectedCommitVerified": False,
    "protectedNonCommitVerified": False,
    "protectedCurrentHeadVerified": False,
    "independentNonceConsumptionVerified": False,
    "identityCommandSettled": False,
    "safeToRetry": False,
    "operatorConsentVerified": False,
    "productionSignInAllowed": False,
}


class Refused(ValueError):
    """Incorrect CI invocation, never a settlement/admission result."""


def _deny(code: str):
    raise Refused(code)


def _untrusted(status: str) -> dict:
    return {
        "schema": SCHEMA, "status": status,
        "terminalStatus": "PROTECTED_OUTCOME_UNPROVEN",
        "next": "HOLD_NO_AUTOMATIC_RETRY_REQUIRE_INDEPENDENT_CUSTODIAN",
        **DENIED,
    }


def _pairs_no_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise Refused("C3E_IPC_DUPLICATE_REPLY_FIELD")
        seen[key] = value
    return seen


def _nonfinite(_token):
    raise Refused("C3E_IPC_NONFINITE_REPLY_NUMBER")


def _decode_frame(raw: bytes):
    """Exact one-frame read; never a signed protected receipt decoder."""
    if type(raw) is not bytes or len(raw) < 6 or len(raw) > P.MAX_FRAME + 4:
        raise Refused("C3E_IPC_REPLY_BOUNDS")
    n = struct.unpack(">I", raw[:4])[0]
    if n < 2 or n > P.MAX_FRAME or len(raw) != n + 4:
        raise Refused("C3E_IPC_REPLY_LENGTH_OR_TRAILING_DATA")
    try:
        payload = json.loads(
            raw[4:].decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates, parse_constant=_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("C3E_IPC_REPLY_ENCODING_REFUSED") from exc
    if type(payload) is not dict:
        raise Refused("C3E_IPC_REPLY_OBJECT_REQUIRED")
    return payload


def _diagnostic_shape(payload: dict, op: str, nonce: str):
    if set(payload) != {
        "schema", "status", "requestNonce", "result", *P.S.DENIED,
    }:
        return False
    if (payload.get("schema") != P.REPLY_SCHEMA
            or payload.get("status") != "IPC_CI_DIAGNOSTIC_ONLY"
            or payload.get("requestNonce") != nonce
            or any(payload[k] is not False for k in P.S.DENIED)):
        return False
    result = payload["result"]
    if type(result) is not dict:
        return False
    if op == "CUSTODIAN_STATUS":
        expected = {"schema", "status", "source", *P.S.DENIED}
        desired_status, desired_source = (
            P.S.STATUS_HOLD, P.S.PROTECTED_REQUIRED)
    elif op == "SNAPSHOT":
        expected = {
            "schema", "status", "source", "testHeadSha256", "testSequence",
            *P.S.DENIED,
        }
        desired_status, desired_source = (
            P.S.STATUS_LOCAL, P.S.LOCAL_DEVELOPMENT)
    else:
        expected = {
            "schema", "status", "source", "testState", "testHeadSha256",
            *P.S.DENIED,
        }
        desired_status, desired_source = (
            P.S.STATUS_LOCAL, P.S.LOCAL_DEVELOPMENT)
    if set(result) != expected:
        return False
    if (result["schema"] != P.S.SCHEMA
            or result["status"] != desired_status
            or result["source"] != desired_source
            or any(result[k] is not False for k in P.S.DENIED)):
        return False
    if op == "SNAPSHOT":
        return (type(result["testHeadSha256"]) is str
                and HEX64.fullmatch(result["testHeadSha256"]) is not None
                and type(result["testSequence"]) is int
                and result["testSequence"] >= 1)
    if op == "OUTCOME":
        state, head = result["testState"], result["testHeadSha256"]
        return (type(state) is str and (
            (state == "issued" and head is None)
            or (state == "consumed" and type(head) is str
                and HEX64.fullmatch(head) is not None)))
    return True


def observe_ci_only(*, operation: str, expected_request_nonce: str,
                    delivery_state: str, response_frame: bytes | None) -> dict:
    """Transport observation, NOT a signed command or terminal proof.

    Any malformed/absent frame and any delivery uncertainty remain unknown.
    Even a valid diagnostic or fixed refusal cannot prove that a previous
    independently protected operation settled or did not settle.
    """
    if type(operation) is not str or operation not in OPERATIONS:
        _deny("C3E_IPC_SETTLEMENT_UNKNOWN_READ_ONLY_OPERATION")
    if (type(expected_request_nonce) is not str
            or HEX32.fullmatch(expected_request_nonce) is None):
        _deny("C3E_IPC_SETTLEMENT_EXACT_REQUEST_NONCE_REQUIRED")
    if type(delivery_state) is not str or delivery_state not in DELIVERY:
        _deny("C3E_IPC_SETTLEMENT_INVALID_DELIVERY_STATE")
    if delivery_state != "COMPLETE_FRAME":
        # Any unverified bytes cannot establish a terminal receipt, even if a
        # caller claims they were almost complete or a server already acted.
        return _untrusted(NO_VERIFIED_FRAME)
    try:
        payload = _decode_frame(response_frame)
    except Refused:
        return _untrusted(NO_VERIFIED_FRAME)
    if (set(payload) == {"schema", "status", *P.S.DENIED}
            and payload.get("schema") == P.REPLY_SCHEMA
            and payload.get("status") == P.REFUSAL_STATUS
            and all(payload[k] is False for k in P.S.DENIED)):
        # No nonce in the existing fixed refusal. It cannot be used as
        # evidence that some earlier/different operation never committed.
        return _untrusted(RECEIVED_REFUSAL)
    if _diagnostic_shape(payload, operation, expected_request_nonce):
        return _untrusted(RECEIVED_DIAGNOSTIC)
    return _untrusted(NO_VERIFIED_FRAME)


def protected_terminal_admission(*_args, **_kwargs):
    _deny("C3E_IPC_SETTLEMENT_NO_PROTECTED_RECEIPT_OR_SIGNIN_AUTHORITY")
