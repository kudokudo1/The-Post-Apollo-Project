#!/usr/bin/env python3
"""DOC 1: one real signed custodian test denial over local SOCK_SEQPACKET.

The public key is independently passed by the CI caller (not read from packet)
but is NOT operator-enrolled, hardware protected or globally current. A valid
Ed25519 signature on a denial is not Sign-In permission, nonce settlement or
an authentic independently administered custodian. No writer/server is here.
"""
from __future__ import annotations

import importlib.util
import array
import json
import os
from pathlib import Path
import socket
import struct
import sys

HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "c3e_wire_original_signed_candidate",
        HERE / "C3eSignedCustodianCandidateCI.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_WIRE_ORIGINAL_CANDIDATE_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C = _load()
SCHEMA = "postapollo.connections.c3e-wire-signed-denial-ci-v1"
STATUS = "WIRE_TEST_SIGNATURE_VALID_NOT_ENROLLED_CUSTODIAN"
MAX_PACKET = 4096
DENIED = {
    **C.DENIED,
    "actualIndependentCustodianVerified": False,
    "realOneUseChallengeSettled": False,
    "testPublicKeyOperatorApproved": False,
    "remoteHardwareAuthenticated": False,
    "protectedOutcomeAuthoritativelyKnown": False,
    "credentialActionsAllowed": False,
    "safeToRetry": False,
    "productionSignInAllowed": False,
}


class Refused(ValueError):
    """Untrusted packet shape, signature, audience or role refused."""


class UnknownAfterSend(RuntimeError):
    """No reply can establish whether a remote operation occurred."""


def _deny(code):
    raise Refused(code)


def _ci():
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_WIRE_DISPOSABLE_HOSTED_ROOT_ONLY")


def _object_pairs(pairs):
    d = {}
    for key, value in pairs:
        if key in d:
            _deny("C3E_WIRE_DUPLICATE_JSON_KEY_REFUSED")
        d[key] = value
    return d


def _constant(_):
    _deny("C3E_WIRE_NONFINITE_JSON_REFUSED")


def _discard_ancillary(ancillary):
    """Close any passed SCM_RIGHTS descriptors before refusing the packet."""
    if not ancillary:
        return
    for level, kind, payload in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            fds = array.array("i")
            size = len(payload) - (len(payload) % fds.itemsize)
            fds.frombytes(payload[:size])
            for fd in fds:
                try:
                    os.close(fd)
                except OSError:
                    pass


def _frame_decode(data):
    if type(data) is not bytes or len(data) < 6:
        _deny("C3E_WIRE_INVALID_FRAME_LENGTH")
    length = struct.unpack(">I", data[:4])[0]
    if length < 2 or length > MAX_PACKET - 4 or length != len(data) - 4:
        _deny("C3E_WIRE_EXACT_FRAME_SIZE_REQUIRED")
    try:
        obj = json.loads(data[4:].decode("utf-8"), object_pairs_hook=_object_pairs,
                         parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("C3E_WIRE_INVALID_JSON_REFUSED") from exc
    if type(obj) is not dict:
        _deny("C3E_WIRE_EXACT_RESPONSE_OBJECT_REQUIRED")
    return obj


def verify_one_denial_ci_only(receiver: socket.socket, *, request,
                              prior_test_public_key: bytes):
    """Receive one packet then verify original signed denial, always HOLD.

    Sender/receiver transport is disposable local CI. The key came from a test
    fixture before packet receipt, NOT independent out-of-band enrollment.
    On missing response the caller must preserve UNKNOWN/HOLD, never retry.
    """
    _ci()
    if (type(receiver) is not socket.socket
            or receiver.family != socket.AF_UNIX
            or (receiver.type & 0xf) != socket.SOCK_SEQPACKET):
        _deny("C3E_WIRE_REAL_SEQPACKET_SOCKET_REQUIRED")
    if type(prior_test_public_key) is not bytes or len(prior_test_public_key) != 32:
        _deny("C3E_WIRE_PREEXISTING_TEST_PUBLIC_KEY_REQUIRED")
    C._query(request)
    try:
        data, ancillary, flags, _ = receiver.recvmsg(MAX_PACKET + 1, 512)
    except (TimeoutError, ConnectionError, OSError) as exc:
        raise UnknownAfterSend(
            "C3E_WIRE_NO_TERMINAL_ACK_UNKNOWN_HOLD_NO_AUTO_RETRY") from exc
    if not data:
        raise UnknownAfterSend(
            "C3E_WIRE_PEER_CLOSED_WITHOUT_REPLY_UNKNOWN_HOLD_NO_AUTO_RETRY")
    _discard_ancillary(ancillary)
    if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        _deny("C3E_WIRE_TRUNCATED_OR_UNEXPECTED_CONTROL_REFUSED")
    if ancillary:
        # Unexpected SCM_RIGHTS were closed; no ancillary metadata is
        # authenticated or part of this test-only signed denial contract.
        _deny("C3E_WIRE_UNEXPECTED_ANCILLARY_DATA_REFUSED")
    response = _frame_decode(data)
    try:
        original = C.inspect_ci_only(
            request=request, response=response,
            test_public_key=prior_test_public_key)
    except C.Refused as exc:
        raise Refused("C3E_WIRE_ORIGINAL_SIGNED_CANDIDATE_REFUSED") from exc
    if (type(original) is not dict
            or original.get("schema") != C.REPORT_SCHEMA
            or original.get("status") != C.STATUS
            or original.get("winner") is not None
            or original.get("safeActions") != []
            or original.get("cryptographicTestSignatureValid") is not True
            or any(original.get(k) is not False for k in C.DENIED)):
        _deny("C3E_WIRE_ORIGINAL_CANDIDATE_AUTHORITY_PROMOTION")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "relation": original["relation"],
        "candidateDigestSha256": original["testCandidateDigestSha256"],
        "testPublicKeySha256": original["testPublicKeySha256"],
        "testSignatureValid": True,
        "messageSenderEnrolled": False,
        "winner": None,
        "safeActions": [],
        "next": "HOLD_UNENROLLED_TEST_KEY_NO_TERMINAL_SETTLEMENT",
        **DENIED,
    }


def protected_admission(*_args, **_kwargs):
    _deny("C3E_WIRE_NO_INDEPENDENT_CUSTODIAN_OR_PRODUCTION_SIGNIN")
