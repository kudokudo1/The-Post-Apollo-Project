#!/usr/bin/env python3
"""BG1-B2B1 Linux AF_UNIX kernel peer lifetime evidence (DENY-ONLY).

SO_PEERPIDFD pins the *socket peer*, not a PID found in userspace after
SO_PEERCRED. This closes the PID reuse race between peer credentials and
os.pidfd_open(). A pidfd does not authenticate a role, installed binary,
application manifest or a future right to actuate an alarm.

This module never grants live ownership, writes alarm data, or acts on time.
"""
from __future__ import annotations

import os
from pathlib import Path
import select
import socket
import struct
import stat

# Linux SO_PEERPIDFD was introduced in Linux 6.5. Python distributions may
# lack the exported constant, even when the running kernel supports it.
# Linux kernel uapi asm-generic/socket.h: SO_PEERPIDFD = 77.
SO_PEERPIDFD = 77


class Refused(Exception):
    """A peer has no sufficient OS lifetime evidence for even a test lease."""


def _start_ticks(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields = raw.rsplit(") ", 1)[1].split()
        if fields[0] in ("Z", "X", "x"):
            raise ValueError("dead")
        ticks = int(fields[19])
        if ticks <= 0:
            raise ValueError("zero ticks")
        return ticks
    except (OSError, ValueError, IndexError) as exc:
        raise Refused("PEER_PROCESS_UNVERIFIED") from exc


def _process_credentials(pid):
    """Read all real/effective/saved/filesystem UID/GID, not just username."""
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="ascii")
        fields = {}
        for line in status.splitlines():
            if line.startswith(("Uid:", "Gid:")):
                name, values = line.split(":", 1)
                parts = values.split()
                if len(parts) != 4:
                    raise ValueError("incomplete credentials")
                fields[name] = tuple(int(v) for v in parts)
        if set(fields) != {"Uid", "Gid"}:
            raise ValueError("missing credentials")
        return fields["Uid"], fields["Gid"]
    except (OSError, ValueError) as exc:
        raise Refused("PEER_CREDENTIALS_UNVERIFIED") from exc


def _executable(pid):
    try:
        path = os.path.realpath(os.readlink(f"/proc/{pid}/exe"))
        if not path or not Path(path).is_absolute():
            raise ValueError("missing peer executable")
        return path
    except (OSError, ValueError) as exc:
        raise Refused("PEER_EXECUTABLE_UNVERIFIED") from exc


def _exited(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN | select.POLLERR | select.POLLHUP)
    try:
        return bool(poller.poll(0))
    except OSError as exc:
        raise Refused("PEER_PIDFD_UNVERIFIED") from exc


def _credentials_from_socket(connection):
    if not hasattr(socket, "SO_PEERCRED"):
        raise Refused("SO_PEERCRED_UNAVAILABLE")
    try:
        raw = connection.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, gid = struct.unpack("3i", raw)
    except (OSError, struct.error) as exc:
        raise Refused("PEER_CREDENTIALS_UNVERIFIED") from exc
    if pid <= 1 or uid != os.getuid() or gid < 0:
        raise Refused("PEER_UID_REFUSED")
    return pid, uid, gid


def _socket_peer_pidfd(connection):
    try:
        raw = connection.getsockopt(socket.SOL_SOCKET, SO_PEERPIDFD,
                                    struct.calcsize("i"))
        fd = struct.unpack("i", raw)[0]
        if fd < 0:
            raise ValueError("invalid pidfd")
        os.set_inheritable(fd, False)
        info = os.fstat(fd)
        # Kernel pidfd is an anon inode with no user-readable file content.
        if not stat.S_ISREG(info.st_mode) and info.st_ino == 0:
            raise ValueError("invalid pidfd metadata")
        return fd
    except (OSError, struct.error, ValueError) as exc:
        # Crucial: never fall back to os.pidfd_open(pid) for a trusted
        # lifetime witness; a PID could be reused before that call.
        raise Refused("SO_PEERPIDFD_UNAVAILABLE") from exc


def capture(connection, expected_exe):
    """Acquire and pin the AF_UNIX peer process. Caller must close() it."""
    pid, uid, gid = _credentials_from_socket(connection)
    fd = _socket_peer_pidfd(connection)
    try:
        witness = {"pid": pid, "uid": uid, "gid": gid,
                   "ticks": _start_ticks(pid), "exe": _executable(pid),
                   "pidfd": fd}
        verify(connection, witness, expected_exe)
        return witness
    except BaseException:
        os.close(fd)
        raise


def verify(connection, witness, expected_exe):
    """Each request must still originate from the exact live connected PID."""
    if (not isinstance(witness, dict)
            or set(witness) != {"pid", "uid", "gid", "ticks", "exe", "pidfd"}):
        raise Refused("PEER_WITNESS_INVALID")
    fd = witness["pidfd"]
    try:
        os.fstat(fd)
    except (OSError, ValueError, TypeError) as exc:
        raise Refused("PEER_PIDFD_UNVERIFIED") from exc
    if _exited(fd):
        raise Refused("PEER_PROCESS_EXITED")
    pid, uid, gid = _credentials_from_socket(connection)
    if (pid, uid, gid) != (
            witness["pid"], witness["uid"], witness["gid"]):
        raise Refused("PEER_CREDENTIALS_CHANGED")
    if _start_ticks(pid) != witness["ticks"]:
        raise Refused("PEER_PROCESS_CHANGED")
    real_uids, real_gids = _process_credentials(pid)
    if any(v != uid for v in real_uids) or any(v != gid for v in real_gids):
        raise Refused("PEER_CREDENTIALS_CHANGED")
    exe = _executable(pid)
    if exe != witness["exe"] or exe != os.path.realpath(expected_exe):
        raise Refused("UNEXPECTED_SYNTHETIC_PEER_EXE")
    if _exited(fd):
        raise Refused("PEER_PROCESS_EXITED")
    # This is evidence for a test client's OS lifetime, NOT role authority.
    return True


def close(witness):
    if isinstance(witness, dict):
        fd = witness.pop("pidfd", None)
        if isinstance(fd, int) and fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
