#!/usr/bin/env python3
"""C3e-L: client-side, kernel-pinned read-only host-status observation (CI only).

Companion of C3e-K's root-owned UNIX socket witness. Unlike a client that
trusts any socket response, this reader requires a trusted test supervisor's
expected root host PID, UID, GID, process-start tick, enrolled witness digest,
and minimum release floors; it checks Linux SO_PEERCRED and the actual socket
inode/ownership before interpreting the status.

These caller-supplied *test pins are NOT independently signed/enrolled*.
They do not establish a real protected installed service, a production
authenticated broker, operator consent, or permission to release secrets.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys

REQUEST = b"WITNESS-FLOOR-READ-V1"
HOST_SCHEMA = "postapollo.connections.c3ej.witness-read.v1"
CLIENT_SCHEMA = "postapollo.connections.c3el.host-observation.v1"
EXPECTED_FIELDS = frozenset({
    "schema", "minimum_policy_epoch", "minimum_release_sequence",
    "enrollment_sha256", "authorized", "writable",
})
HEX = re.compile(r"[0-9a-f]{64}")
CRED_SIZE = struct.calcsize("3i")
MAX_RESPONSE = 4096


class Refused(Exception):
    pass


def deny(reason: str):
    raise Refused(reason)


def process_start(pid: int) -> str:
    if type(pid) is not int or pid <= 1:
        deny("HOST_PID_INVALID")
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        token = text.rsplit(") ", 1)[1].split()[19]
        if not token.isdecimal() or int(token) < 1:
            deny("HOST_START_INVALID")
        return token
    except (OSError, ValueError, IndexError):
        deny("HOST_PROCESS_UNAVAILABLE")


def _stat_exact(path: Path, *, expected_type, uid: int, gid: int, mode: int,
                reason: str):
    try:
        st = os.lstat(path)
    except OSError:
        deny(reason)
    if (not expected_type(st.st_mode) or st.st_uid != uid or
            st.st_gid != gid or stat.S_IMODE(st.st_mode) != mode):
        deny(reason)
    return st


def socket_origin(path: Path, client_gid: int):
    if not path.is_absolute() or path.name != "witness.sock":
        deny("HOST_SOCKET_PATH_UNEXPECTED")
    parent, base = path.parent, path.parent.parent
    if (parent.name != "public" or base.parent != Path("/run")
            or not base.name.startswith("c3ek-ci-")):
        deny("HOST_SOCKET_SCOPE_UNEXPECTED")
    _stat_exact(base, expected_type=stat.S_ISDIR, uid=0, gid=0,
                mode=0o711, reason="HOST_BASE_UNSAFE")
    _stat_exact(parent, expected_type=stat.S_ISDIR, uid=0, gid=client_gid,
                mode=0o750, reason="HOST_SOCKET_PARENT_UNSAFE")
    return _stat_exact(path, expected_type=stat.S_ISSOCK, uid=0,
                       gid=client_gid, mode=0o660,
                       reason="HOST_SOCKET_UNSAFE")


def validate_status(packet: bytes, *, expected_enrollment_sha256: str,
                    minimum_policy_epoch: int,
                    minimum_release_sequence: int):
    if type(packet) is not bytes or not 0 < len(packet) <= MAX_RESPONSE:
        deny("HOST_RESPONSE_SIZE_REFUSED")

    def strict_pairs(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                deny("HOST_RESPONSE_DUPLICATE_FIELD")
            out[key] = value
        return out

    try:
        doc = json.loads(packet.decode("utf-8"), object_pairs_hook=strict_pairs)
    except (ValueError, UnicodeError):
        deny("HOST_RESPONSE_JSON_INVALID")
    if type(doc) is not dict or set(doc) != EXPECTED_FIELDS:
        deny("HOST_RESPONSE_SHAPE_INVALID")
    if (doc["schema"] != HOST_SCHEMA or
            doc["authorized"] is not False or doc["writable"] is not False):
        deny("HOST_RESPONSE_CLAIMS_AUTHORITY")
    if (type(doc["minimum_policy_epoch"]) is not int or
            type(doc["minimum_release_sequence"]) is not int or
            doc["minimum_policy_epoch"] < minimum_policy_epoch or
            doc["minimum_release_sequence"] < minimum_release_sequence):
        deny("HOST_RELEASE_FLOOR_REFUSED")
    if (type(expected_enrollment_sha256) is not str or
            HEX.fullmatch(expected_enrollment_sha256) is None or
            doc["enrollment_sha256"] != expected_enrollment_sha256):
        deny("HOST_ENROLLMENT_MISMATCH")
    return doc


def observe(*, socket_path: str, expected_host_pid: int,
            expected_host_uid: int, expected_host_gid: int,
            expected_host_start: str, expected_enrollment_sha256: str,
            minimum_policy_epoch: int, minimum_release_sequence: int):
    """Read one witness floor. All pins must come from a trusted test harness.

    The returned proof concerns ONLY test transport identity and observed
    release floors. In particular, it is NEVER a credential/consent grant.
    """
    if not sys.platform.startswith("linux") or os.geteuid() == 0:
        deny("TEST_NONROOT_LINUX_CLIENT_REQUIRED")
    if (type(expected_host_pid) is not int or expected_host_pid <= 1 or
            type(expected_host_uid) is not int or expected_host_uid != 0 or
            type(expected_host_gid) is not int or expected_host_gid != 0 or
            type(expected_host_start) is not str or
            type(minimum_policy_epoch) is not int or minimum_policy_epoch < 1 or
            type(minimum_release_sequence) is not int or
            minimum_release_sequence < 1):
        deny("UNTRUSTED_OR_INVALID_TEST_HOST_PIN")
    if process_start(expected_host_pid) != expected_host_start:
        deny("EXPECTED_HOST_PROCESS_STALE")

    target = Path(socket_path)
    inode = socket_origin(target, os.getgid())
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        conn.settimeout(4)
        try:
            conn.connect(str(target))
        except OSError:
            deny("HOST_SOCKET_CONNECT_FAILED")
        try:
            cred = struct.unpack("3i", conn.getsockopt(
                socket.SOL_SOCKET, socket.SO_PEERCRED, CRED_SIZE))
        except OSError:
            deny("HOST_KERNEL_IDENTITY_UNAVAILABLE")
        if cred != (expected_host_pid, expected_host_uid, expected_host_gid):
            deny("HOST_KERNEL_IDENTITY_MISMATCH")
        if process_start(cred[0]) != expected_host_start:
            deny("HOST_KERNEL_PROCESS_CHANGED")
        try:
            conn.sendall(REQUEST)
            response, ancillary, flags, _ = conn.recvmsg(MAX_RESPONSE, 0)
        except OSError:
            deny("HOST_RESPONSE_UNAVAILABLE")
        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
            deny("HOST_RESPONSE_TRUNCATED")
        if (process_start(cred[0]) != expected_host_start or
                struct.unpack("3i", conn.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, CRED_SIZE)) != cred):
            deny("HOST_CHANGED_AFTER_RESPONSE")
        # The C3e-K host is intentionally one-shot: it closes and unlinks
        # its listener immediately after returning the read-only response.
        # Missing *after* a verified connected-peer exchange is expected;
        # a still-existing listener MUST retain the original root-owned inode.
        try:
            os.lstat(target)
        except FileNotFoundError:
            pass
        except OSError:
            deny("HOST_SOCKET_POSTREAD_UNAVAILABLE")
        else:
            after = socket_origin(target, os.getgid())
            if (after.st_dev, after.st_ino) != (inode.st_dev, inode.st_ino):
                deny("HOST_SOCKET_REPLACED")
        verified = validate_status(
            response, expected_enrollment_sha256=expected_enrollment_sha256,
            minimum_policy_epoch=minimum_policy_epoch,
            minimum_release_sequence=minimum_release_sequence)
        return {
            "schema": CLIENT_SCHEMA,
            "transport_peer_verified": True,
            "host_uid_observed": cred[1],
            "observed_policy_epoch": verified["minimum_policy_epoch"],
            "observed_release_sequence": verified["minimum_release_sequence"],
            "enrollment_sha256": verified["enrollment_sha256"],
            "hostAuthenticated": False,
            "canApprove": False,
            "credentialActionsEnabled": False,
            "productionAuthority": False,
        }
    finally:
        conn.close()
