#!/usr/bin/env python3
"""C4b Package 1B: bounded Unix witness CLIENT, disposable CI only.

This is the C4b-owned *consumer* of an externally signed controller
checkpoint. The real independent C3e/Identity witness and its signing key,
history, challenge ledger and operator enrollment DO NOT exist here.

A separate Linux Unix-socket peer is checked using actual SO_PEERCRED plus
caller-pinned PID/UID/GID and an independently pinned Ed25519 verifier.
Neither socket ownership nor peer credentials replace the signature.
Everything is fail-closed, read-only, local and deny-only; no credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

import c4b_signed_external_checkpoint_ci as W

REQUEST_SCHEMA = "postapollo.identity.c4b-witness-transport-request.ci-v1"
RESPONSE_SCHEMA = "postapollo.identity.c4b-witness-transport-response.ci-v1"
SOCKET_DIR_PREFIX = "c4b-p1-witness-ci-"
MAX_FRAME = 8192
MAX_REQUEST = 640
MAX_RESPONSE = 8192
NEGATIVE = {
    "realIndependentWitnessCustodyVerified": False,
    "protectedWitnessChallengeHistoryVerified": False,
    "operatorControlledNativeTransportEnrolled": False,
    "rootRollbackResistanceVerified": False,
    "independentInstalledHostAndSeatVerified": False,
    "c5HumanConsentVerified": False,
    "hostAuthenticated": False,
    "canBeginSignIn": False,
    "credentialActionsEnabled": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    """No verified signed witness transport checkpoint available."""


def _deny(code):
    raise Refused(code)


def _unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            _deny("C4B_P1_TRANSPORT_DUPLICATE_FIELD")
        obj[k] = v
    return obj


def _canonical(doc):
    if type(doc) is not dict:
        _deny("C4B_P1_TRANSPORT_OBJECT_REQUIRED")
    try:
        return json.dumps(doc, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Refused("C4B_P1_TRANSPORT_CANONICAL_JSON_REFUSED") from exc


def _response(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RESPONSE:
        _deny("C4B_P1_TRANSPORT_RESPONSE_BOUNDS_REFUSED")
    try:
        doc = json.loads(raw.decode("ascii"), object_pairs_hook=_unique,
                         parse_constant=lambda _: _deny(
                             "C4B_P1_TRANSPORT_NONFINITE_NUMBER"))
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise Refused("C4B_P1_TRANSPORT_RESPONSE_JSON_REFUSED") from exc
    if (type(doc) is not dict or set(doc) != {
            "schema", "signedCheckpointHex", "checkpointSignatureHex"}
            or _canonical(doc) != raw
            or doc["schema"] != RESPONSE_SCHEMA
            or type(doc["signedCheckpointHex"]) is not str
            or type(doc["checkpointSignatureHex"]) is not str
            or len(doc["signedCheckpointHex"]) % 2 != 0
            or not 0 < len(doc["signedCheckpointHex"]) <= 2 * W.MAX_PROOF
            or re.fullmatch(r"[0-9a-f]+", doc["signedCheckpointHex"],
                            re.ASCII) is None
            or re.fullmatch(r"[0-9a-f]{128}", doc["checkpointSignatureHex"],
                            re.ASCII) is None):
        _deny("C4B_P1_TRANSPORT_EXACT_RESPONSE_SCOPE_REFUSED")
    return (bytes.fromhex(doc["signedCheckpointHex"]),
            bytes.fromhex(doc["checkpointSignatureHex"]))


def _scope(sock_path, peer_uid, peer_gid, peer_pid):
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or os.environ.get("GITHUB_ACTOR") != "kudokudo1"
            or os.environ.get("POST_APOLLO_C4B_P1_TRANSPORT_TEST_ONLY") != "1"):
        _deny("C4B_P1_TRANSPORT_DISPOSABLE_ROOT_CI_ONLY")
    if (type(peer_uid) is not int or not 0 < peer_uid < 2**31
            or type(peer_gid) is not int or not 0 < peer_gid < 2**31
            or type(peer_pid) is not int or not 1 < peer_pid < 2**31):
        _deny("C4B_P1_TRANSPORT_INDEPENDENT_PEER_PIN_REQUIRED")
    if (not isinstance(sock_path, Path) or not sock_path.is_absolute()
            or sock_path.name != "current-checkpoint.sock"
            or sock_path.parent.parent != Path("/run")
            or not sock_path.parent.name.startswith(SOCKET_DIR_PREFIX)
            or len(sock_path.parent.name) > 96):
        _deny("C4B_P1_TRANSPORT_SOCKET_PATH_SCOPE_REFUSED")
    try:
        directory = os.lstat(sock_path.parent)
        sock = os.lstat(sock_path)
    except OSError as exc:
        raise Refused("C4B_P1_TRANSPORT_SOCKET_MISSING") from exc
    if (not stat.S_ISDIR(directory.st_mode)
            or directory.st_uid != peer_uid or directory.st_gid != peer_gid
            or stat.S_IMODE(directory.st_mode) != 0o700
            or not stat.S_ISSOCK(sock.st_mode)
            or sock.st_uid != peer_uid or sock.st_gid != peer_gid
            or stat.S_IMODE(sock.st_mode) != 0o600):
        _deny("C4B_P1_TRANSPORT_SOCKET_OWNER_OR_TYPE_REFUSED")


def _receive_exact(channel, size, deadline):
    """A shared absolute deadline, not a fresh timeout for every byte."""
    out = bytearray()
    while len(out) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _deny("C4B_P1_TRANSPORT_OVERALL_DEADLINE_EXCEEDED")
        channel.settimeout(remaining)
        chunk = channel.recv(size - len(out))
        if not chunk:
            _deny("C4B_P1_TRANSPORT_TRUNCATED_FRAME")
        out.extend(chunk)
    return bytes(out)


def _read_frame(channel, deadline):
    length = struct.unpack("!I", _receive_exact(channel, 4, deadline))[0]
    if not 0 < length <= MAX_FRAME:
        _deny("C4B_P1_TRANSPORT_OVERSIZE_OR_EMPTY_FRAME")
    return _receive_exact(channel, length, deadline)


def fetch_current_witness_ci_only(
    *, socket_path: Path, controller_state: dict, fresh_challenge: bytes,
    separately_pinned_peer_uid: int, separately_pinned_peer_gid: int,
    separately_pinned_peer_pid: int,
    separately_pinned_witness_root: Ed25519PublicKey,
    separately_pinned_witness_sha256: str,
):
    """Receive/check a separate process's signed checkpoint, no host grant.

    PID, UID, GID, signing root and challenge are ALL supplied by an
    independent caller in this fixture. In production they MUST originate
    from authenticated operator/protected issuer state, not the socket peer.
    An attacker with root privileges can impersonate the socket or roll
    back the controller; this test does not attest a native installed host.
    """
    _scope(socket_path, separately_pinned_peer_uid,
           separately_pinned_peer_gid, separately_pinned_peer_pid)
    if (type(controller_state) is not dict
            or set(controller_state) != W.STATE_FIELDS
            or type(fresh_challenge) is not bytes
            or len(fresh_challenge) != 32):
        _deny("C4B_P1_TRANSPORT_CURRENT_STATE_OR_NONCE_REQUIRED")
    request = _canonical({
        "schema": REQUEST_SCHEMA,
        "hostId": controller_state["hostId"],
        "challengeSha256": hashlib.sha256(fresh_challenge).hexdigest(),
    })
    if len(request) > MAX_REQUEST:
        _deny("C4B_P1_TRANSPORT_REQUEST_TOO_LARGE")

    if not hasattr(socket, "SO_PEERCRED"):
        _deny("C4B_P1_TRANSPORT_KERNEL_PEER_CREDENTIALS_UNAVAILABLE")
    try:
        deadline = time.monotonic() + 2.0
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
            channel.settimeout(2.0)
            channel.connect(str(socket_path))
            raw_peer = channel.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED,
                struct.calcsize("3i"))
            pid, uid, gid = struct.unpack("3i", raw_peer)
            if (pid != separately_pinned_peer_pid
                    or uid != separately_pinned_peer_uid
                    or gid != separately_pinned_peer_gid):
                _deny("C4B_P1_TRANSPORT_KERNEL_PEER_IDENTITY_MISMATCH")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _deny("C4B_P1_TRANSPORT_OVERALL_DEADLINE_EXCEEDED")
            channel.settimeout(remaining)
            channel.sendall(struct.pack("!I", len(request)) + request)
            raw = _read_frame(channel, deadline)
    except (OSError, TimeoutError) as exc:
        raise Refused("C4B_P1_TRANSPORT_UNIX_IO_OR_DEADLINE_REFUSED") from exc

    signed, signature = _response(raw)
    witness_input = {
        "signed_checkpoint": signed,
        "checkpoint_signature": signature,
        "independently_pinned_witness_root": separately_pinned_witness_root,
        "independently_pinned_witness_sha256": separately_pinned_witness_sha256,
        "independently_issued_challenge": fresh_challenge,
    }
    try:
        observation = W.inspect_current_checkpoint_ci_only(
            controller_state=dict(controller_state), **witness_input)
    except W.Refused as exc:
        raise Refused("C4B_P1_TRANSPORT_SIGNED_EXTERNAL_CHECKPOINT_REFUSED") from exc
    if (observation.get(
            "externalPinnedSignedCheckpointMatchesRootOwnedLedgerInCi") is not True
            or any(observation.get(flag) is not False for flag in W.NEGATIVE)):
        _deny("C4B_P1_TRANSPORT_WITNESS_ATTEMPTED_AUTHORITY_PROMOTION")
    return {
        "schema": RESPONSE_SCHEMA,
        "unixPeerPidUidGidMatchedCallerPinsInCI": True,
        "externalSignedCheckpointMatchedControllerInCI": True,
        "witnessInputs": witness_input,
        **NEGATIVE,
    }
