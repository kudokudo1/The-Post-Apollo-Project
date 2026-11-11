#!/usr/bin/env python3
"""V2n Linux AF_UNIX peer identity evidence for a future protected broker.

Read kernel SO_PEERCRED and /proc process incarnation/executable evidence.
Only an EXPLICIT TEST_FIXTURE_ONLY policy can match, and success remains
DENY-ONLY. This is not proof of an owner-controlled signer, script identity,
consent, a signed executable, or authorization to use ArchiveStore.
"""
import hashlib
import json
import os
import re
import socket
import stat
import struct

BOOT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
OWNERS = frozenset(("demo-scrape", "weather-events"))
MAX_EXE_BYTES = 128 * 1024 * 1024
POLICY_KEYS = frozenset(("ownerId", "expectedUid", "expectedGid",
                         "expectedExeSha256", "origin"))


class BrokerPeerError(Exception):
    """Stable refusal code; never include a host path or process command."""


def _require(ok, code):
    if not ok:
        raise BrokerPeerError(code)


def _start_ticks(pid):
    """Linux /proc/PID/stat field 22, after parenthesized command field 2."""
    try:
        with open(f"/proc/{pid}/stat", "rb") as handle:
            line = handle.read(8192)
    except OSError as exc:
        raise BrokerPeerError("PEER_PROCESS_UNAVAILABLE") from exc
    end = line.rfind(b")")
    _require(end > 0 and line[:line.find(b" ")].isdigit(),
             "PEER_PROCESS_INVALID")
    fields = line[end + 1:].strip().split()
    # fields[0] starts at field 3, so field 22 is zero-based index 19.
    _require(len(fields) > 19 and fields[19].isdigit(),
             "PEER_PROCESS_INVALID")
    ticks = int(fields[19])
    _require(ticks > 0, "PEER_PROCESS_INVALID")
    return ticks


def _boot_identity():
    try:
        with open("/proc/sys/kernel/random/boot_id", "r",
                  encoding="ascii") as handle:
            value = handle.read(100).strip().lower()
    except OSError as exc:
        raise BrokerPeerError("PEER_BOOT_UNAVAILABLE") from exc
    _require(BOOT_ID.fullmatch(value) is not None,
             "PEER_BOOT_UNAVAILABLE")
    return value


def _executable_digest(pid):
    # /proc/PID/exe references the executable inode, not a user-supplied
    # pathname. Python scripts can share this executable, so this is
    # intentionally NOT proof of which script or application is running.
    try:
        fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
    except OSError as exc:
        raise BrokerPeerError("PEER_EXECUTABLE_UNAVAILABLE") from exc
    hasher = hashlib.sha256()
    size = 0
    try:
        mode = os.fstat(fd).st_mode
        _require(stat.S_ISREG(mode), "PEER_EXECUTABLE_INVALID")
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            size += len(chunk)
            _require(size <= MAX_EXE_BYTES,
                     "PEER_EXECUTABLE_LIMIT")
            hasher.update(chunk)
    except OSError as exc:
        raise BrokerPeerError("PEER_EXECUTABLE_UNAVAILABLE") from exc
    finally:
        os.close(fd)
    _require(size > 0, "PEER_EXECUTABLE_INVALID")
    return hasher.hexdigest()


def inspect_fixture_peer(connection, policy):
    """Derive a witness from a connected Linux Unix-domain STREAM socket.

    Caller's own PID, UID, binary path, and claimed owner are not accepted as
    peer identity. Policy is test-only and must be independently supplied.
    No socket bind/listen/accept server is created by this module.
    """
    _require(type(policy) is dict and set(policy) == POLICY_KEYS
             and policy["origin"] == "TEST_FIXTURE_ONLY",
             "PEER_TRUST_NOT_PROVISIONED")
    _require(type(policy["ownerId"]) is str
             and policy["ownerId"] in OWNERS
             and type(policy["expectedUid"]) is int
             and 0 <= policy["expectedUid"] <= 2**32 - 1
             and type(policy["expectedGid"]) is int
             and 0 <= policy["expectedGid"] <= 2**32 - 1
             and type(policy["expectedExeSha256"]) is str
             and DIGEST.fullmatch(policy["expectedExeSha256"]),
             "PEER_POLICY_INVALID")
    _require(isinstance(connection, socket.socket)
             and connection.family == socket.AF_UNIX
             and connection.type & socket.SOCK_STREAM == socket.SOCK_STREAM
             and hasattr(socket, "SO_PEERCRED"),
             "PEER_SOCKET_UNSUPPORTED")
    try:
        credential = connection.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED,
            struct.calcsize("3i"))
        pid, uid, gid = struct.unpack("3i", credential)
    except (OSError, struct.error) as exc:
        raise BrokerPeerError("PEER_CREDENTIAL_UNAVAILABLE") from exc
    _require(pid > 0 and uid >= 0 and gid >= 0,
             "PEER_CREDENTIAL_UNAVAILABLE")
    _require(uid == policy["expectedUid"]
             and gid == policy["expectedGid"],
             "PEER_IDENTITY_MISMATCH")
    before = _start_ticks(pid)
    boot = _boot_identity()
    exe = _executable_digest(pid)
    after = _start_ticks(pid)
    _require(before == after, "PEER_PROCESS_CHANGED")
    _require(exe == policy["expectedExeSha256"],
             "PEER_EXECUTABLE_MISMATCH")
    identity = {"ownerId":policy["ownerId"],
                "pid":pid,"uid":uid,"gid":gid,
                "startTicks":before, "bootId":boot,
                "exeSha256":exe}
    canonical = json.dumps(identity,sort_keys=True,
                           separators=(",",":"),ensure_ascii=True)
    return {"state":"TEST_KERNEL_PEER_MATCHED_DENY_ONLY",
            "ownerId":identity["ownerId"],
            "pid":pid,"uid":uid,"gid":gid,
            "startTicks":before,"bootId":boot,
            "exeSha256":exe,
            "peerWitnessSha256":hashlib.sha256(
                canonical.encode("ascii")).hexdigest(),
            "sourceProcessVerified":False,
            "sourceAuthorityVerified":False,
            "captureAllowed":False,
            "productionAllowed":False}
