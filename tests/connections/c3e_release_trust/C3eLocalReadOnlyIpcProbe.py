#!/usr/bin/env python3
"""DOC 1 disposable AF_UNIX read-only IPC to C3e fixture ledger.

This is NOT a production service, custodian protocol or authenticated channel.
No listener, connectable filesystem socket, network, commit, challenge issuance,
enrollment, credential action, or fallback. A separately forked GitHub CI child
answers ONE request using an existing deny-only TrustBoundary. All output flags
remain false. Production requires its OWN audited, authenticated protocol.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import struct
import sys

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_IPC_REQUIRED_BOUNDARY_MISSING")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


S = _load("c3e_ipc_original_storage_boundary",
          HERE / "C3eStorageIndependentTrustBoundary.py")

SCHEMA = "postapollo.connections.c3e-local-readonly-ipc.ci-v1"
REPLY_SCHEMA = "postapollo.connections.c3e-local-readonly-ipc-response.ci-v1"
MAX_FRAME = 4096
NONCE = re.compile(r"[0-9a-f]{32}\Z", re.ASCII)
CHALLENGE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
REQUEST_OPS = frozenset(("SNAPSHOT", "OUTCOME", "CUSTODIAN_STATUS"))
REFUSAL_STATUS = "IPC_CI_REQUEST_REFUSED_NO_AUTHORITY"
REFUSAL = {"schema": REPLY_SCHEMA, "status": REFUSAL_STATUS, **S.DENIED}


class Refused(ValueError):
    """Unsafe test-only IPC frame, request, mode or backend output."""


def _deny(reason: str):
    raise Refused(reason)


def _ci_only():
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_IPC_DISPOSABLE_GITHUB_HOSTED_ROOT_ONLY")


def _pairs_unique(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            _deny("C3E_IPC_DUPLICATE_FIELD")
        output[key] = value
    return output


def _json_constant(_name):
    _deny("C3E_IPC_NONFINITE_NUMBER")


def _canonical(doc) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _exact(sock: socket.socket, count: int):
    buf = bytearray()
    while len(buf) < count:
        try:
            chunk = sock.recv(count - len(buf))
        except TimeoutError as exc:
            raise Refused("C3E_IPC_READ_TIMEOUT_REFUSED") from exc
        if not chunk:
            _deny("C3E_IPC_TRUNCATED")
        buf.extend(chunk)
    return bytes(buf)


def _read(sock: socket.socket):
    if type(sock) is not socket.socket or sock.family != socket.AF_UNIX:
        _deny("C3E_IPC_UNIX_SOCKETPAIR_ONLY")
    size = struct.unpack(">I", _exact(sock, 4))[0]
    if size < 2 or size > MAX_FRAME:
        _deny("C3E_IPC_FRAME_SIZE_REFUSED")
    raw = _exact(sock, size)
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs_unique,
                         parse_constant=_json_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("C3E_IPC_JSON_MALFORMED") from exc
    if type(obj) is not dict:
        _deny("C3E_IPC_OBJECT_REQUIRED")
    # A single exact frame per request. The child closes after one response.
    return obj


def _write(sock: socket.socket, doc: dict):
    raw = _canonical(doc)
    if len(raw) > MAX_FRAME:
        _deny("C3E_IPC_REPLY_TOO_LARGE")
    sock.sendall(struct.pack(">I", len(raw)) + raw)


def frame_ci_only(doc: dict):
    """Build a test input. Not a production client or signed transport."""
    _ci_only()
    raw = _canonical(doc)
    if len(raw) < 2 or len(raw) > MAX_FRAME:
        _deny("C3E_IPC_TEST_FRAME_TOO_LARGE")
    return struct.pack(">I", len(raw)) + raw


def _validated_diagnostic(op: str, boundary: S.TrustBoundary,
                          result: dict) -> dict:
    """Reject arbitrary nested/extra claims even when known flags are false.

    This is a CI-only *shape* check, not independent custodian authentication.
    A valid local fixture or protected HOLD may not acquire a new success
    field by appending it to an otherwise correctly denied response.
    """
    if type(result) is not dict:
        _deny("C3E_IPC_BACKEND_RESULT_NOT_OBJECT")
    if op == "CUSTODIAN_STATUS":
        expected = {"schema", "status", "source", *S.DENIED}
        expected_status = S.STATUS_HOLD
        expected_source = S.PROTECTED_REQUIRED
    elif op == "SNAPSHOT":
        expected = {"schema", "status", "source",
                    "testHeadSha256", "testSequence", *S.DENIED}
        expected_status = S.STATUS_LOCAL
        expected_source = S.LOCAL_DEVELOPMENT
    elif op == "OUTCOME":
        expected = {"schema", "status", "source",
                    "testState", "testHeadSha256", *S.DENIED}
        expected_status = S.STATUS_LOCAL
        expected_source = S.LOCAL_DEVELOPMENT
    else:
        _deny("C3E_IPC_UNEXPECTED_DIAGNOSTIC_OPERATION")
    if set(result) != expected:
        _deny("C3E_IPC_EXTRA_OR_MISSING_BACKEND_FIELDS")
    if (result["schema"] != S.SCHEMA
            or result["status"] != expected_status
            or result["source"] != expected_source
            or boundary._mode != expected_source):
        _deny("C3E_IPC_OPERATION_MODE_OR_STATUS_MISMATCH")
    if any(result[k] is not False for k in S.DENIED):
        _deny("C3E_IPC_BACKEND_ATTEMPTED_AUTHORITY_PROMOTION")
    if op == "SNAPSHOT":
        if (type(result["testHeadSha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", result["testHeadSha256"]) is None
                or type(result["testSequence"]) is not int
                or result["testSequence"] < 1):
            _deny("C3E_IPC_MALFORMED_LOCAL_SNAPSHOT")
    if op == "OUTCOME":
        state, head = result["testState"], result["testHeadSha256"]
        if (type(state) is not str or state not in ("issued", "consumed")
                or (state == "issued" and head is not None)
                or (state == "consumed" and
                    (type(head) is not str
                     or re.fullmatch(r"[0-9a-f]{64}", head) is None))):
            _deny("C3E_IPC_MALFORMED_LOCAL_OUTCOME")
    return result


def _route(boundary: S.TrustBoundary, request: dict):
    if type(boundary) is not S.TrustBoundary:
        _deny("C3E_IPC_ORIGINAL_BOUNDARY_REQUIRED")
    if set(request) not in (
        {"schema", "op", "requestNonce"},
        {"schema", "op", "requestNonce", "challengeHex"},
    ):
        _deny("C3E_IPC_EXACT_REQUEST_FIELDS_REQUIRED")
    if (request.get("schema") != SCHEMA
            or type(request.get("op")) is not str
            or request["op"] not in REQUEST_OPS
            or type(request.get("requestNonce")) is not str
            or NONCE.fullmatch(request["requestNonce"]) is None):
        _deny("C3E_IPC_DOMAIN_OPERATION_NONCE_REFUSED")
    op = request["op"]
    if op == "OUTCOME":
        ch = request.get("challengeHex")
        if type(ch) is not str or CHALLENGE.fullmatch(ch) is None:
            _deny("C3E_IPC_EXACT_CHALLENGE_REQUIRED")
        if set(request) != {"schema", "op", "requestNonce", "challengeHex"}:
            _deny("C3E_IPC_OUTCOME_FIELDS_REFUSED")
    elif "challengeHex" in request:
        _deny("C3E_IPC_UNUSED_CHALLENGE_REFUSED")

    if op == "CUSTODIAN_STATUS":
        result = boundary.protected_required_status()
    elif op == "SNAPSHOT":
        result = boundary.read_current_snapshot()
    else:
        result = boundary.lookup_terminal_outcome(bytes.fromhex(request["challengeHex"]))

    result = _validated_diagnostic(op, boundary, result)
    return {
        "schema": REPLY_SCHEMA,
        "status": "IPC_CI_DIAGNOSTIC_ONLY",
        "requestNonce": request["requestNonce"],
        "result": result,
        **S.DENIED,
    }


def serve_one_ci_only(sock: socket.socket, boundary: S.TrustBoundary):
    """Exactly one request, one deny-only reply, no service activation.

    Client-provided bytes are never trusted enrollment or authenticated
    process/seat evidence. No promise is made about a future NAS transport.
    """
    _ci_only()
    if type(boundary) is not S.TrustBoundary:
        _deny("C3E_IPC_ORIGINAL_BOUNDARY_REQUIRED")
    sock.settimeout(3.0)
    try:
        try:
            request = _read(sock)
            answer = _route(boundary, request)
        except (Refused, S.Refused, S.L.Refused):
            answer = dict(REFUSAL)
        _write(sock, answer)
    finally:
        sock.close()


def production_admission(*_args, **_kwargs):
    _deny("C3E_IPC_NO_REAL_SIGNIN_OR_PROTECTED_AUTHORITY")
