#!/usr/bin/env python3
"""MACHINE // bounded cancellation and session-context drift checks.

This negative-only guard observes the already accepted AF_UNIX connection and
Linux kernel procfs session/cgroup/namespace attributes of its SO_PEERCRED
process. It invalidates an in-flight metadata request on socket disconnect,
extra pipelined input, timeout, task exit, executable change, or observed
session-context drift. It cannot grant archive access or verify logind seat
lock/unlock state; owner-issued C3e/C5 evidence is still mandatory.

Do not mistake a matching /proc context for authenticated user/session/seat
identity. Same-user programs can share a session and namespace. No prod server.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path
import select
import socket
import stat
import time

MAX_CGROUP_BYTES = 8192
MAX_GUARD_NS = 2_000_000_000


class CancelledRequest(ValueError):
    pass


def refuse():
    raise CancelledRequest("MACHINE REQUEST CONTEXT INVALID")


@dataclass(frozen=True)
class SessionContext:
    session_id: int
    cgroup_sha256: str
    user_ns_device: int
    user_ns_inode: int
    pid_ns_device: int
    pid_ns_inode: int


def _session_context(pid: int) -> SessionContext:
    """Untrusted PID never comes from request JSON; caller uses SO_PEERCRED."""
    if type(pid) is not int or pid <= 1:
        refuse()
    root = Path("/proc") / str(pid)
    try:
        sid1 = os.getsid(pid)
        with (root / "cgroup").open("rb") as handle:
            cgroup = handle.read(MAX_CGROUP_BYTES + 1)
        user = os.stat(root / "ns" / "user")
        namespace = os.stat(root / "ns" / "pid")
        sid2 = os.getsid(pid)
    except (OSError, ValueError):
        refuse()
    if (sid1 <= 0 or sid1 != sid2 or not 1 <= len(cgroup) <= MAX_CGROUP_BYTES
            or b"\x00" in cgroup
            or not stat.S_ISREG(user.st_mode) or not stat.S_ISREG(namespace.st_mode)
            or min(user.st_ino, namespace.st_ino) <= 0):
        # nsfs namespace handles are stat'd as ordinary regular files.
        refuse()
    return SessionContext(
        session_id=sid1,
        cgroup_sha256=hashlib.sha256(cgroup).hexdigest(),
        user_ns_device=user.st_dev,
        user_ns_inode=user.st_ino,
        pid_ns_device=namespace.st_dev,
        pid_ns_inode=namespace.st_ino,
    )


def _socket_still_waiting(connection) -> bool:
    """No FIN/half-close/error and no trailing unframed/pipelined bytes.

    This is checked AFTER consuming the exact one-request frame. There is no
    busy loop or background polling. An unread byte is a protocol violation.
    """
    try:
        fd = connection.fileno()
        if type(fd) is not int or fd < 0:
            return False
        # POLLRDHUP is Linux-specific. Do not silently weaken this check.
        if not hasattr(select, "POLLRDHUP"):
            return False
        poller = select.poll()
        mask = select.POLLERR | select.POLLHUP | select.POLLIN | select.POLLRDHUP
        poller.register(fd, mask)
        observed = poller.poll(0)
        if any(events & (select.POLLERR | select.POLLHUP |
                         select.POLLRDHUP) for _, events in observed):
            return False
        # MSG_DONTWAIT avoids consuming the next byte or blocking. An empty
        # result is peer EOF; any actual byte means forbidden pipelining.
        try:
            pending = connection.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
        except BlockingIOError as exc:
            return exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK)
        return False  # EOF or extra byte are both invalid.
    except (OSError, AttributeError, TypeError, ValueError):
        return False


class InFlightGuard:
    """Does not own or close the socket or process lease passed by broker."""

    __slots__ = ("_connection", "_lease", "_initial", "_born_ns", "_cancelled")

    def __init__(self, connection, lease, initial: SessionContext):
        self._connection = connection
        self._lease = lease
        self._initial = initial
        self._born_ns = time.monotonic_ns()
        self._cancelled = False

    def valid(self) -> bool:
        if self._cancelled:
            return False
        try:
            age = time.monotonic_ns() - self._born_ns
            if age < 0 or age >= MAX_GUARD_NS:
                self._cancelled = True
                return False
            if not self._lease.valid() or not _socket_still_waiting(self._connection):
                self._cancelled = True
                return False
            if _session_context(self._lease.identity.pid) != self._initial:
                self._cancelled = True
                return False
            if not self._lease.valid() or not _socket_still_waiting(self._connection):
                self._cancelled = True
                return False
            return True
        except (CancelledRequest, OSError, ValueError, AttributeError):
            self._cancelled = True
            return False

    def cancel(self):
        self._cancelled = True


def begin(connection, lease) -> InFlightGuard:
    """Initial snapshot is taken only after a kernel-anchored process lease."""
    if not lease.valid():
        refuse()
    original = _session_context(lease.identity.pid)
    if not _socket_still_waiting(connection) or not lease.valid():
        refuse()
    guard = InFlightGuard(connection, lease, original)
    if not guard.valid():
        guard.cancel()
        refuse()
    return guard


if __name__ == "__main__":
    raise SystemExit(1)
