"""P48 PHONE // Actual Linux peer process evidence, DENY-ONLY.

A real AF_UNIX SO_PEERCRED is only a kernel UID/PID/GID snapshot at connect,
not trusted installed Post Apollo identity. Here we pin that kernel PID via
pidfd, inspect bounded /proc process metadata, hash the executable's bytes,
and recheck process start time, executable inode, and cgroup before responding.

This module NEVER verifies a C4b signed release or C3e/C5 producer, cannot
authenticate consent, and must not be treated as a key-release or save grant.
All observations are internal, ephemeral and never serialized to QML/logs.
No shell, keyring, vault, contact provider, socket server, or CLI entry point.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import select
import socket
import stat
import struct

STAT_MAX = 8192
STATUS_MAX = 8192
CGROUP_MAX = 8192
LSM_MAX = 2048
EXE_MAX = 128 * 1024 * 1024
CHUNK = 64 * 1024
PEER_SIZE = struct.calcsize("3i")


@dataclass(frozen=True, slots=True, repr=False)
class PeerEvidence:
    """Private, NON-AUTHORIZING process measurement."""
    pid: int
    uid: int
    gid: int
    start_ticks: int
    executable_sha256: str
    executable_device: int
    executable_inode: int
    cgroup_sha256: str
    lsm_observed: bool

    def __repr__(self) -> str:
        return "<PHONE_PEER_EVIDENCE_KERNEL_OBSERVED_NOT_AUTHENTICATED>"


def _bounded(path: Path, maximum: int) -> bytes:
    with path.open("rb") as f:
        raw = f.read(maximum + 1)
    if not 0 < len(raw) <= maximum or b"\x00" in raw:
        raise ValueError("bounded read failed")
    return raw


def _start_ticks(raw: bytes, pid: int) -> int:
    # /proc/<pid>/stat's comm is enclosed in parentheses, and may itself
    # contain spaces and parentheses. Locate the last ') ' before field 3.
    close = raw.rfind(b") ")
    if close <= 0 or not raw.startswith(str(pid).encode("ascii") + b" ("):
        raise ValueError("bad stat prefix")
    fields = raw[close + 2:].split()
    if len(fields) < 20 or len(fields[0]) != 1:
        raise ValueError("truncated stat")
    # After the parenthesized comm, fields start at stat field 3.
    value = fields[19]  # stat field 22: starttime, in clock ticks
    if not value.isdigit():
        raise ValueError("bad starttime")
    number = int(value)
    if number < 1:
        raise ValueError("zero starttime")
    return number


def _uids_gids(raw: bytes, uid: int, gid: int) -> bool:
    found = {}
    for row in raw.splitlines():
        if row.startswith(b"Uid:") or row.startswith(b"Gid:"):
            key, _, values = row.partition(b":")
            if key in found:
                return False
            parts = values.split()
            if len(parts) != 4 or any(not x.isdigit() for x in parts):
                return False
            found[key] = tuple(int(x) for x in parts)
    # Refuse setuid/setgid and mismatching saved/fs credentials rather than
    # treating SO_PEERCRED's identity as durable installed-host evidence.
    return found.get(b"Uid") == (uid,) * 4 and found.get(b"Gid") == (gid,) * 4


def _hash_executable(path: Path) -> tuple[str, int, int]:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("not a regular executable")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > EXE_MAX:
                raise ValueError("oversized executable")
            digest.update(chunk)
        if total == 0:
            raise ValueError("empty executable")
        return digest.hexdigest(), info.st_dev, info.st_ino
    finally:
        os.close(fd)


def _pidfd_alive(fd: int) -> bool:
    poller = select.poll()
    poller.register(fd, select.POLLIN | select.POLLERR | select.POLLHUP)
    return not bool(poller.poll(0))


def observe_socket_peer(conn: socket.socket) -> PeerEvidence | None:
    """Measure a real Linux peer. None always means deny, never retry/grant.

    A pidfd prevents the observed PID being silently recycled during our
    bounded /proc reads. Rechecking starttime, executable inode, cgroup and
    pidfd liveness narrows process-replacement races. It does not attest
    service installation, signed release, current user seat or a C5 gesture.
    """
    pidfd = None
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, PEER_SIZE)
        if type(raw) is not bytes or len(raw) != PEER_SIZE:
            return None
        pid, uid, gid = struct.unpack("3i", raw)
        if (pid <= 0 or uid != os.geteuid() or gid != os.getegid()
                or not hasattr(os, "pidfd_open")):
            return None
        pidfd = os.pidfd_open(pid, 0)
        if not _pidfd_alive(pidfd):
            return None

        prefix = Path("/proc") / str(pid)
        before = _start_ticks(_bounded(prefix / "stat", STAT_MAX), pid)
        if not _uids_gids(_bounded(prefix / "status", STATUS_MAX), uid, gid):
            return None
        group = _bounded(prefix / "cgroup", CGROUP_MAX)
        if b"\n" not in group:
            return None
        binary_hash, device, inode = _hash_executable(prefix / "exe")

        try:
            lsm = _bounded(prefix / "attr" / "current", LSM_MAX)
            lsm_observed = bool(lsm.strip())
        except (OSError, ValueError):
            # Availability of a label is OS-dependent. Missing label NEVER
            # means installed host trust or SELinux verification succeeded.
            lsm_observed = False

        after = _start_ticks(_bounded(prefix / "stat", STAT_MAX), pid)
        group_after = _bounded(prefix / "cgroup", CGROUP_MAX)
        executable_after = (prefix / "exe").stat()
        if (not _pidfd_alive(pidfd) or after != before or group != group_after
                or (executable_after.st_dev, executable_after.st_ino)
                   != (device, inode)):
            return None
        return PeerEvidence(
            pid=pid, uid=uid, gid=gid, start_ticks=before,
            executable_sha256=binary_hash,
            executable_device=device, executable_inode=inode,
            cgroup_sha256=hashlib.sha256(group).hexdigest(),
            lsm_observed=lsm_observed,
        )
    except (OSError, ValueError, TypeError, OverflowError,
            AttributeError, struct.error):
        return None
    finally:
        if pidfd is not None:
            try:
                os.close(pidfd)
            except OSError:
                pass


# No status success elevation, systemd enrollment, C4b signer, C3e challenge,
# C5 receipt, key vault call, real SAVE, QML publication, or IPC service.
