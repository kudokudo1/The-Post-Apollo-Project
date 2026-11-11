#!/usr/bin/env python3
"""MACHINE // negative-only Linux peer-process lifecycle lease.

The kernel socket SO_PEERPIDFD pins the socket peer against PID reuse.
The lease checks /proc task start ticks, four UID/GID fields, and executable
device/inode, plus pidfd exit and brief monotonic expiry. Failure merely
INVALIDATES evidence; success grants NO authorization or trust.

Linux UAPI SO_PEERPIDFD is 77; Python may not publish this constant yet.
If unavailable, capture refuses: never fall back to os.pidfd_open(peer_pid),
which could bind a reused PID instead of the original socket peer.
This is not independently verified C3e provenance or C5 one-use consent.

An exec of the same executable inode with matching UID/GID and start ticks
can be indistinguishable using these interfaces. A surviving lease is NOT
positive proof of client or browser extension identity.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import select
import socket
import stat
import struct
import time

SO_PEERPIDFD = getattr(socket, "SO_PEERPIDFD", 77)  # Linux UAPI
MAX_LEASE_NS = 2_000_000_000
MAX_PROC_BYTES = 16384


class LifecycleRefusal(ValueError):
    pass


def refuse():
    raise LifecycleRefusal("MACHINE PROCESS LIFECYCLE REFUSED")


@dataclass(frozen=True)
class Identity:
    pid: int
    uid: int
    gid: int
    start_ticks: int
    exe_device: int
    exe_inode: int
    uid_fields: tuple[int, int, int, int]
    gid_fields: tuple[int, int, int, int]


def _pidfd_alive(fd: int) -> bool:
    if type(fd) is not int or fd < 0:
        return False
    try:
        poller = select.poll()
        poller.register(fd, select.POLLIN | select.POLLERR | select.POLLHUP)
        return not poller.poll(0)
    except (OSError, ValueError):
        return False


def _read_bytes(path: Path) -> bytes:
    # /proc is kernel-owned; all components below are fixed or numeric PID.
    # No user-controlled path or process name is used.
    try:
        with path.open("rb") as source:
            data = source.read(MAX_PROC_BYTES + 1)
    except (OSError, ValueError):
        refuse()
    if not data or len(data) > MAX_PROC_BYTES:
        refuse()
    return data


def _start_ticks(pid: int) -> int:
    # /proc/PID/stat starts: PID (possibly parenthesized name) state ...
    # starttime is field #22; the first field after ") " is #3.
    raw = _read_bytes(Path("/proc") / str(pid) / "stat")
    delim = raw.rfind(b") ")
    if delim < 0 or b" (" not in raw[:delim + 2]:
        refuse()
    try:
        initial = raw[:raw.index(b" (")]
        if int(initial) != pid:
            refuse()
        fields = raw[delim + 2:].split()
        if len(fields) <= 19 or len(fields[0]) != 1:
            refuse()
        ticks = int(fields[19])
    except (ValueError, IndexError, TypeError):
        refuse()
    if ticks <= 0:
        refuse()
    return ticks


def _identity(pid: int, uid: int, gid: int) -> Identity:
    if (type(pid) is not int or pid <= 1 or type(uid) is not int or uid < 0
            or type(gid) is not int or gid < 0):
        refuse()
    folder = Path("/proc") / str(pid)
    ticks = _start_ticks(pid)
    status = _read_bytes(folder / "status")
    found = {}
    for raw in status.splitlines():
        if raw.startswith(b"Uid:") or raw.startswith(b"Gid:"):
            key, _, values = raw.partition(b":")
            if key in found:
                refuse()
            try:
                numbers = tuple(int(x) for x in values.split())
            except ValueError:
                refuse()
            if len(numbers) != 4 or any(x < 0 for x in numbers):
                refuse()
            found[key] = numbers
    # SO_PEERCRED represents effective credentials; the other three
    # /proc slots may legitimately differ. Pin all four to detect changes.
    uids = found.get(b"Uid")
    gids = found.get(b"Gid")
    if uids is None or gids is None or uids[1] != uid or gids[1] != gid:
        refuse()
    try:
        exe = os.stat(folder / "exe")
    except (OSError, ValueError):
        refuse()
    if not stat.S_ISREG(exe.st_mode) or exe.st_dev <= 0 or exe.st_ino <= 0:
        refuse()
    return Identity(pid, uid, gid, ticks, exe.st_dev, exe.st_ino, uids, gids)


class ProcessLease:
    """Transient borrowed evidence only; never a broker grant."""

    __slots__ = ("identity", "_fd", "_born_ns", "_closed")

    def __init__(self, identity: Identity, fd: int):
        self.identity = identity
        self._fd = fd
        self._born_ns = time.monotonic_ns()
        self._closed = False

    def valid(self) -> bool:
        if self._closed:
            return False
        try:
            age = time.monotonic_ns() - self._born_ns
            if age < 0 or age >= MAX_LEASE_NS or not _pidfd_alive(self._fd):
                return False
            observed = _identity(
                self.identity.pid, self.identity.uid, self.identity.gid)
            return observed == self.identity and _pidfd_alive(self._fd)
        except (LifecycleRefusal, OSError, ValueError):
            return False

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                os.close(self._fd)
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()


def capture_socket_peer(connection, *, peer) -> ProcessLease:
    """Require kernel-anchored socket peer task and independent proc observations.

    A kernel lacking SO_PEERPIDFD produces no usable lease. The caller must
    obtain peer using SO_PEERCRED, never a request payload.
    """
    for name in ("pid", "uid", "gid"):
        if not hasattr(peer, name) or type(getattr(peer, name)) is not int:
            refuse()
    if peer.pid <= 1 or peer.uid < 0 or peer.gid < 0:
        refuse()
    fd = -1
    try:
        raw = connection.getsockopt(socket.SOL_SOCKET, SO_PEERPIDFD, 4)
        if type(raw) is not bytes or len(raw) != 4:
            refuse()
        fd = struct.unpack("=i", raw)[0]
        if fd < 0:
            refuse()
        if not _pidfd_alive(fd):
            refuse()
        first = _identity(peer.pid, peer.uid, peer.gid)
        if not _pidfd_alive(fd):
            refuse()
        second = _identity(peer.pid, peer.uid, peer.gid)
        if first != second:
            refuse()
        lease = ProcessLease(first, fd)
        fd = -1  # ownership transferred
        if not lease.valid():
            lease.close()
            refuse()
        return lease
    except (OSError, AttributeError, struct.error, TypeError) as exc:
        raise LifecycleRefusal("MACHINE PROCESS LIFECYCLE REFUSED") from exc
    finally:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass


if __name__ == "__main__":
    raise SystemExit(1)
