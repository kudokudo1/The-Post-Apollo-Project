#!/usr/bin/env python3
"""DOC 1: kernel packet attribution + C3e read-only shape NEVER grant Identity.

Only disposable GitHub-hosted root CI may invoke this composition. Reuse
the ALREADY MERGED dormant C3e TimeW packet observer to avoid building a
second kernel credential / SCM_RIGHTS parser. That observer does not certify
SwayPX, and this adapter does not certify an enrolled Identity gateway.
The expected frame is caller-supplied; matching its hash proves no root.
No live socket listener, signer, SQLite writer, command or production hook.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_IDENTITY_PACKET_ORIGINAL_SOURCE_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = _load("c3e_identity_packet_original_ipc",
          HERE / "C3eLocalReadOnlyIpcProbe.py")
K = _load("c3e_identity_packet_existing_kernel_observer",
          ROOT / "services/connections/ConnectionsTimeWNativePacketObservation.py")

SCHEMA = "postapollo.connections.c3e-identity-packet-nonadmission.ci-v1"
STATUS = "LOCAL_PACKET_KERNEL_ORIGIN_NOT_IDENTITY_SOURCE_AUTHORITY"
DENIED = {
    **P.S.DENIED,
    "identityPurposeSourceEnrolled": False,
    "independentlyCurrentIdentityHistory": False,
    "verifiedOriginalNativeGateway": False,
    "perPacketProcessObservationIsProtectedProof": False,
    "protectedOneUseChallengeSpent": False,
    "signedTerminalOutcomeVerified": False,
    "humanConsentC5Verified": False,
    "safeToRetry": False,
    "signInAllowed": False,
}


class Refused(ValueError):
    """Malformed/untrusted packet, false source claim or boundary violation."""


def _deny(code):
    raise Refused(code)


def _ci_only():
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        _deny("C3E_IDENTITY_PACKET_HOSTED_ROOT_CI_ONLY")


def _expected_readonly_request(frame: bytes):
    if type(frame) is not bytes or not 6 <= len(frame) <= P.MAX_FRAME + 4:
        _deny("C3E_IDENTITY_PACKET_BOUNDED_FRAME_REQUIRED")
    size = struct.unpack(">I", frame[:4])[0]
    if size < 2 or size > P.MAX_FRAME or size != len(frame) - 4:
        _deny("C3E_IDENTITY_PACKET_EXACT_FRAMING_REQUIRED")
    try:
        doc = json.loads(
            frame[4:].decode("utf-8"),
            object_pairs_hook=P._pairs_unique,
            parse_constant=P._json_constant)
    except (UnicodeError, json.JSONDecodeError, P.Refused) as exc:
        raise Refused("C3E_IDENTITY_PACKET_REQUEST_ENCODING_REFUSED") from exc
    if type(doc) is not dict:
        _deny("C3E_IDENTITY_PACKET_REQUEST_OBJECT_REQUIRED")
    return doc


def inspect_ci_only(receiver: socket.socket, *,
                    expected_request_frame: bytes,
                    boundary: P.S.TrustBoundary):
    """Observe ONE kernel-attributed packet then route an untrusted test frame.

    The original kernel observer sees the actual packet and returns its SHA,
    but not its raw bytes. Only when the caller-supplied expectation hashes to
    those bytes do we invoke the original C3e read-only test router. This does
    NOT make caller-supplied expectations an independently trusted command.
    """
    _ci_only()
    if type(boundary) is not P.S.TrustBoundary:
        _deny("C3E_IDENTITY_PACKET_ORIGINAL_TRUST_BOUNDARY_REQUIRED")
    request = _expected_readonly_request(expected_request_frame)
    try:
        observed = K.inspect_one_untrusted_packet(receiver)
    except K.ObservationHold as exc:
        raise Refused("C3E_IDENTITY_PACKET_KERNEL_PROVENANCE_UNKNOWN_HOLD") from exc

    fields = {
        "kind", "status", "packetSha256Untrusted", "packetLength",
        "kernelPeerPidObserved", "kernelPeerUidObserved",
        "kernelPeerGidObserved", "exactPeerPidfdAliveAtRead",
        "rawPacketUntrusted", "safeActions", *K.NO_AUTHORITY,
    }
    if type(observed) is not dict or set(observed) != fields:
        _deny("C3E_IDENTITY_PACKET_UNEXPECTED_KERNEL_REPORT")
    if (observed["kind"] != K.OBSERVATION_KIND
            or observed["status"] !=
            "KERNEL_PACKET_PEER_OBSERVED_BUT_SWAYPX_UNENROLLED"
            or observed["exactPeerPidfdAliveAtRead"] is not True
            or observed["rawPacketUntrusted"] is not True
            or observed["safeActions"] != []
            or any(observed[k] is not False for k in K.NO_AUTHORITY)
            or type(observed["packetLength"]) is not int
            or observed["packetLength"] != len(expected_request_frame)
            or type(observed["packetSha256Untrusted"]) is not str
            or observed["packetSha256Untrusted"] !=
            hashlib.sha256(expected_request_frame).hexdigest()
            or any(type(observed[k]) is not int or observed[k] < 0
                   for k in ("kernelPeerPidObserved",
                             "kernelPeerUidObserved",
                             "kernelPeerGidObserved"))):
        _deny("C3E_IDENTITY_PACKET_UNTRUSTED_PACKET_OR_AUTHORITY_MISMATCH")

    try:
        diagnostic = P._route(boundary, request)
    except (P.Refused, P.S.Refused, P.S.L.Refused) as exc:
        raise Refused("C3E_IDENTITY_PACKET_ORIGINAL_READONLY_ROUTE_REFUSED") from exc
    if (type(diagnostic) is not dict
            or set(diagnostic) != {
                "schema", "status", "requestNonce", "result", *P.S.DENIED}
            or diagnostic["schema"] != P.REPLY_SCHEMA
            or diagnostic["status"] != "IPC_CI_DIAGNOSTIC_ONLY"
            or any(diagnostic[k] is not False for k in P.S.DENIED)):
        _deny("C3E_IDENTITY_PACKET_ROUTE_PROMOTION_REFUSED")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "packetSha256LocalComparisonOnly": observed["packetSha256Untrusted"],
        "kernelSenderPidObservedOnly": observed["kernelPeerPidObserved"],
        "localReadOnlyOperation": request["op"],
        "originalDiagnosticStatus": diagnostic["result"]["status"],
        "next": "HOLD_NO_PROTECTED_IDENTITY_OR_AUTO_RETRY",
        **DENIED,
    }


def protected_identity_admission(*_args, **_kwargs):
    _deny("C3E_IDENTITY_PACKET_NO_INDEPENDENT_SIGNIN_SOURCE_OR_CUSTODY")
