#!/usr/bin/env python3
"""DOC 1: disposable pathname AF_UNIX read-only C3e service origin experiment.

Fresh accept() SO_PEERCRED is tied to connecting process, unlike inherited
socketpair's creation-time peer. Even a matching UID/PID NEVER authenticates
the current message writer, independently enrolled root, host/seat, or Sign-In.
This module is CI ONLY; it does not install/run a persistent daemon.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import socket
import stat
import struct
import sys

HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_ACCEPTED_SOCKET_ORIGINAL_IPC_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


P = _load("c3e_accepted_existing_ipc_probe",
          HERE / "C3eLocalReadOnlyIpcProbe.py")
SCHEMA = "postapollo.connections.c3e-accepted-unix-readonly.ci-v1"
SOCKET_NAME = "read-only-ci.sock"
DENIED = {
    **P.S.DENIED,
    "acceptedPeerAuthenticatedAsHost": False,
    "originalMessageSenderAuthenticated": False,
    "custodianRootIndependentlyEnrolled": False,
    "authoritativeCurrentHeadVerified": False,
    "protectedTerminalReceiptVerified": False,
    "credentialActionsAllowed": False,
    "safeToRetry": False,
}


class Refused(ValueError):
    """Test-only listener misuse or unsafe pathname and peer observation."""


def _deny(code):
    raise Refused(code)


def _guard():
    if (sys.platform != "linux" or os.geteuid() != 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or not hasattr(socket, "SO_PEERCRED")):
        _deny("C3E_ACCEPTED_DISPOSABLE_HOSTED_LINUX_ROOT_ONLY")


def _root(root):
    _guard()
    if (not isinstance(root, Path) or not root.is_absolute()
            or root.parent != Path("/run")
            or not root.name.startswith("c3es-ci-")
            or root.is_symlink()):
        _deny("C3E_ACCEPTED_UNSAFE_ROOT_PATH")
    try:
        info = root.lstat()
    except OSError as exc:
        raise Refused("C3E_ACCEPTED_ROOT_MISSING") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o700):
        _deny("C3E_ACCEPTED_UNSAFE_ROOT_OWNER_OR_MODE")
    return root


def _socket_info(root):
    path = _root(root) / SOCKET_NAME
    if path.is_symlink():
        _deny("C3E_ACCEPTED_SOCKET_SYMLINK_REFUSED")
    try:
        info = path.lstat()
    except OSError as exc:
        raise Refused("C3E_ACCEPTED_SOCKET_MISSING") from exc
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_nlink != 1):
        _deny("C3E_ACCEPTED_UNSAFE_SOCKET_NODE")
    return path, info.st_ino


def bind_one_ci_only(root: Path):
    """Create ONE disposable pathname listener; never unlink existing nodes."""
    path = _root(root) / SOCKET_NAME
    if os.path.lexists(path):
        _deny("C3E_ACCEPTED_EXISTING_SOCKET_NODE_REFUSED")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    bound = False
    try:
        listener.bind(str(path))
        bound = True
        os.chmod(path, 0o600, follow_symlinks=False)
        _socket_info(root)
        listener.listen(1)
        listener.settimeout(3.0)
        return listener
    except BaseException:
        listener.close()
        if bound:
            try:
                node, _ = _socket_info(root)
                node.unlink()
            except Refused:
                pass
        raise


def _accepted_peer(conn):
    if type(conn) is not socket.socket or conn.family != socket.AF_UNIX:
        _deny("C3E_ACCEPTED_REAL_AF_UNIX_CONNECTION_REQUIRED")
    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                          struct.calcsize("3i"))
    if len(raw) != struct.calcsize("3i"):
        _deny("C3E_ACCEPTED_KERNEL_CREDENTIAL_SIZE_REFUSED")
    pid, uid, gid = struct.unpack("3i", raw)
    if any(type(n) is not int or n < 0 for n in (pid, uid, gid)):
        _deny("C3E_ACCEPTED_KERNEL_CREDENTIAL_INVALID")
    return pid, uid, gid


def serve_one_ci_only(listener, root: Path, boundary, *,
                      expected_connecting_pid: int, expected_uid: int = 0):
    """Accept and answer one diagnostic request, never an authority command.

    The expected PID is supplied by the trusted CI test parent, not enrolled
    remote identity or proof of who actually wrote the frame. A connected FD
    can be inherited or transferred after connect().
    """
    _guard()
    if (type(expected_connecting_pid) is not int
            or expected_connecting_pid <= 1
            or type(expected_uid) is not int or expected_uid < 0
            or type(listener) is not socket.socket
            or listener.family != socket.AF_UNIX
            or type(boundary) is not P.S.TrustBoundary):
        _deny("C3E_ACCEPTED_EXACT_CI_SERVER_INPUT_REQUIRED")
    path, inode = _socket_info(root)
    if listener.getsockname() != str(path):
        _deny("C3E_ACCEPTED_WRONG_LISTENER_PATH")
    try:
        try:
            conn, _ = listener.accept()
        except TimeoutError as exc:
            raise Refused("C3E_ACCEPTED_NO_CLIENT_TIMEOUT") from exc
        with conn:
            conn.settimeout(3.0)
            peer_pid, peer_uid, _peer_gid = _accepted_peer(conn)
            if peer_pid != expected_connecting_pid or peer_uid != expected_uid:
                # Drop without parsing the unapproved peer's request bytes.
                # The peer may observe EOF or connection reset; we promise
                # neither an acknowledgement nor a parseable refusal frame.
                return
            # The ORIGINAL C3e read-only route validates exactly one request,
            # fixed refusal, and all false authority flags. No writes.
            P.serve_one_ci_only(conn, boundary)
    finally:
        listener.close()
        # Never delete an unrelated file substituted at the same path.
        try:
            now_path, now_inode = _socket_info(root)
        except Refused:
            pass
        else:
            if now_inode == inode:
                now_path.unlink()


def assert_accepted_observation_no_authority_ci_only(report):
    """Even a properly denied IPC response is not independent enrollment."""
    expected = {"schema", "status", "peerObservedFrom",
                "trustedTerminalOutcome", *DENIED}
    if type(report) is not dict or set(report) != expected:
        _deny("C3E_ACCEPTED_DIAGNOSTIC_FIELDS_REFUSED")
    if (report["schema"] != SCHEMA
            or report["status"] != "ACCEPTED_KERNEL_PEER_ONLY_NOT_CUSTODY"
            or report["peerObservedFrom"] != "SO_PEERCRED_AT_ACCEPT"
            or report["trustedTerminalOutcome"] is not None
            or any(report[k] is not False for k in DENIED)):
        _deny("C3E_ACCEPTED_AUTHORITY_INJECTION_REFUSED")
    return report


def denial_only_observation_ci_only():
    return assert_accepted_observation_no_authority_ci_only({
        "schema": SCHEMA,
        "status": "ACCEPTED_KERNEL_PEER_ONLY_NOT_CUSTODY",
        "peerObservedFrom": "SO_PEERCRED_AT_ACCEPT",
        "trustedTerminalOutcome": None,
        **DENIED,
    })


def protected_admission(*_args, **_kwargs):
    _deny("C3E_ACCEPTED_NO_ENROLLED_SOURCE_OR_PRODUCTION_AUTHORITY")
