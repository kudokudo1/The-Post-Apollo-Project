#!/usr/bin/env python3
"""DOC 1: demonstrate Linux SO_PEERCRED limits with real disposable processes.

This is a negative test fixture, not an authentication or attestation API.
An inherited AF_UNIX socketpair may expose creation-time peer credentials,
not the PID/UID of the later sender. A freshly accepted connection can bind
its peer to a connecting task, but still cannot prove signed release, seat,
independent root custody or Sign-In authority.

No named filesystem socket, remote connection, local service installation,
private key, SQL state mutation, consent, or native credential command.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import struct
import sys

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_PEER_ORIGINAL_IPC_BOUNDARY_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = _load("c3e_peer_existing_readonly_ipc", HERE / "C3eLocalReadOnlyIpcProbe.py")
SCHEMA = "postapollo.connections.c3e-unix-peer-negative.ci-v1"
CREATOR_NOT_SENDER = "SO_PEERCRED_SOCKETPAIR_CREATOR_NOT_FORKED_SENDER"
ACCEPTED_PEER_ONLY = "SO_PEERCRED_FRESH_CONNECTION_NOT_TRUST_ENROLLMENT"
NOT_AUTHORITY = "KERNEL_PEER_OBSERVATION_NO_PRODUCTION_AUTHORITY"
NOBODY_UID = 65534
DENIED = {
    **P.S.DENIED,
    "protectedCustodianEnrolled": False,
    "realReleaseAttested": False,
    "activeSeatAuthenticated": False,
    "independentCurrentHistoryVerified": False,
    "signInAuthorized": False,
}


class Refused(ValueError):
    """The probe cannot certify a sender or a trusted authority."""


def _deny(code: str):
    raise Refused(code)


def _guard():
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or not hasattr(socket, "SO_PEERCRED")):
        _deny("C3E_PEER_DISPOSABLE_HOSTED_LINUX_ROOT_ONLY")


def _peer(sock: socket.socket) -> tuple[int, int, int]:
    if type(sock) is not socket.socket or sock.family != socket.AF_UNIX:
        _deny("C3E_PEER_AF_UNIX_REQUIRED")
    raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                          struct.calcsize("3i"))
    if len(raw) != struct.calcsize("3i"):
        _deny("C3E_PEER_KERNEL_CREDENTIAL_LENGTH")
    return struct.unpack("3i", raw)


def _drop_in_child():
    # All children are disposable CI-only; no subprocess runs as an operator.
    os.setgroups([])
    os.setgid(NOBODY_UID)
    os.setuid(NOBODY_UID)
    if os.getuid() != NOBODY_UID or os.geteuid() != NOBODY_UID:
        os._exit(121)


def _wait(child_pid: int):
    pid, status = os.waitpid(child_pid, 0)
    if pid != child_pid or not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
        _deny("C3E_PEER_UNPRIVILEGED_CHILD_DID_NOT_COMPLETE")


def _report(status: str, **diagnostics):
    return {
        "schema": SCHEMA,
        "status": status,
        "authorityStatus": NOT_AUTHORITY,
        **diagnostics,
        **DENIED,
    }


def inherited_socketpair_ci_only() -> dict:
    """Fork+drop UID after creation; compare creator and inherited peer creds."""
    _guard()
    left, right = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    left.settimeout(3.0)
    creator_pid, creator_uid, creator_gid = os.getpid(), os.getuid(), os.getgid()
    originally = _peer(left)
    try:
        pid = os.fork()
        if pid == 0:
            try:
                left.close()
                _drop_in_child()
                right.sendall(b"unprivileged-sender")
                right.close()
                os._exit(0)
            except BaseException:
                os._exit(122)
        right.close()
        received = bytearray()
        while len(received) < len(b"unprivileged-sender"):
            chunk = left.recv(32)
            if not chunk:
                _deny("C3E_PEER_CHILD_MESSAGE_TRUNCATED")
            received.extend(chunk)
        observed = _peer(left)
        _wait(pid)
        if (bytes(received) != b"unprivileged-sender"
                or originally != (creator_pid, creator_uid, creator_gid)
                or observed != originally
                or pid == observed[0]
                or creator_uid == NOBODY_UID):
            _deny("C3E_PEER_CREATION_CREDENTIALS_NOT_OBSERVED")
        return _report(
            CREATOR_NOT_SENDER,
            socketCreationPid=creator_pid,
            childSenderPid=pid,
            socketPeerPid=observed[0],
            socketPeerUid=observed[1],
            childSenderExpectedUid=NOBODY_UID,
            socketPeerIdentityMatchesSender=False,
        )
    finally:
        left.close()
        right.close()


def fresh_accepted_connection_ci_only() -> dict:
    """Fork+drop UID before new AF_UNIX connect, get accepted task creds.

    Abstract socket exists only in the Linux CI namespace during this test.
    It is NOT a persistent Unix service, provider endpoint, or trusted key.
    """
    _guard()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.settimeout(3.0)
    address = b"\x00postapollo-c3e-ci-" + os.urandom(12).hex().encode("ascii")
    listener.bind(address)
    listener.listen(1)
    try:
        pid = os.fork()
        if pid == 0:
            try:
                listener.close()
                _drop_in_child()
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(3)
                    client.connect(address)
                    client.sendall(b"fresh-connection")
                os._exit(0)
            except BaseException:
                os._exit(123)
        conn, _addr = listener.accept()
        with conn:
            conn.settimeout(3)
            seen = _peer(conn)
            data = bytearray()
            while len(data) < len(b"fresh-connection"):
                chunk = conn.recv(32)
                if not chunk:
                    _deny("C3E_PEER_FRESH_CONNECTION_TRUNCATED")
                data.extend(chunk)
        _wait(pid)
        if (bytes(data) != b"fresh-connection"
                or seen[0] != pid or seen[1] != NOBODY_UID
                or pid == os.getpid()):
            _deny("C3E_PEER_FRESH_CONNECTION_OS_ID_MISMATCH")
        return _report(
            ACCEPTED_PEER_ONLY,
            acceptedPeerPid=seen[0],
            childSenderPid=pid,
            acceptedPeerUid=seen[1],
            socketPeerIdentityMatchesSender=True,
        )
    finally:
        listener.close()


def assert_observation_not_authority_ci_only(result: dict) -> dict:
    """Even kernel-correct peer credentials are only process-local diagnostics."""
    _guard()
    if type(result) is not dict:
        _deny("C3E_PEER_RESULT_EXACT_OBJECT_REQUIRED")
    permitted = {
        "schema", "status", "authorityStatus", *DENIED,
        "socketCreationPid", "childSenderPid", "socketPeerPid",
        "socketPeerUid", "childSenderExpectedUid",
        "socketPeerIdentityMatchesSender",
    } if result.get("status") == CREATOR_NOT_SENDER else {
        "schema", "status", "authorityStatus", *DENIED,
        "acceptedPeerPid", "childSenderPid", "acceptedPeerUid",
        "socketPeerIdentityMatchesSender",
    }
    if set(result) != permitted:
        _deny("C3E_PEER_OBSERVATION_FIELDS_REFUSED")
    if (result.get("schema") != SCHEMA
            or result.get("authorityStatus") != NOT_AUTHORITY
            or result.get("status") not in (CREATOR_NOT_SENDER, ACCEPTED_PEER_ONLY)
            or any(result.get(k) is not False for k in DENIED)):
        _deny("C3E_PEER_OBSERVATION_AUTHORITY_PROMOTION_REFUSED")
    if result["status"] == CREATOR_NOT_SENDER:
        if (result.get("socketPeerIdentityMatchesSender") is not False
                or any(type(result.get(k)) is not int or result[k] < 0
                       for k in ("socketCreationPid", "childSenderPid",
                                 "socketPeerPid", "socketPeerUid",
                                 "childSenderExpectedUid"))
                or result["socketPeerPid"] != result["socketCreationPid"]
                or result["childSenderPid"] == result["socketPeerPid"]):
            _deny("C3E_PEER_CREATOR_MISMATCH_NOT_ESTABLISHED")
    else:
        if (result.get("socketPeerIdentityMatchesSender") is not True
                or any(type(result.get(k)) is not int or result[k] < 0
                       for k in ("acceptedPeerPid", "childSenderPid",
                                 "acceptedPeerUid"))
                or result["acceptedPeerPid"] != result["childSenderPid"]):
            _deny("C3E_PEER_ACCEPTED_MATCH_INVALID")
    return {
        "schema": SCHEMA,
        "status": NOT_AUTHORITY,
        **DENIED,
    }


def production_admission(*_args, **_kwargs):
    _deny("C3E_PEER_NEVER_GRANTS_HOST_OR_CREDENTIAL_AUTHORITY")
