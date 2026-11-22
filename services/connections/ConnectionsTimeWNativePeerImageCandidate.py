#!/usr/bin/env python3
"""Read real Linux image/LSM/cgroup of one connected TimeW candidate peer.

This is a DIAGNOSTIC ONLY, not an enrolled SwayPX native source authenticator.
SO_PEERPIDFD pins the socket's original Linux process lifetime across bounded
/proc observation, but neither /proc nor an executable SHA proves that the
process made a protected compositor-internal window selection. A signed
operator-approved release/root, active seat, challenge and C5 remain absent.

No socket listener/connector, subprocess, key, policy, compositor command,
host installer, production authorization or source packet parser is used.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import select
import socket
import stat
import struct
import sys

SO_PEERPIDFD = getattr(socket, "SO_PEERPIDFD", 77)
_CREDS = struct.Struct("=3i")
MAX_PROC = 8192
MAX_IMAGE_BYTES = 128 * 1024 * 1024
MAX_TIMEOUT_SECONDS = 1.5
KIND = "postapollo.connections.timew.untrusted-peer-process-image.v1"
NO_AUTHORITY = {
    "installedSwayPXReleaseEnrolled": False,
    "compositorProcessAuthenticated": False,
    "compositorSelectionAuthenticated": False,
    "activeSeatAuthenticated": False,
    "protectedChallengeVerified": False,
    "signedNativeReceiptsVerified": False,
    "c5HumanConsentAndSpendVerified": False,
    "sourceEvidenceTrusted": False,
    "nativeGeometryAllowed": False,
    "timewRestoreAllowed": False,
    "productionAuthority": False,
}


class PeerImageHold(ValueError):
    """Ambiguous or unavailable original-peer kernel evidence."""


def _hold(reason):
    raise PeerImageHold("C3E_TIMEW_PEER_IMAGE_HOLD // " + reason)


def _pidfd_alive(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN | select.POLLERR | select.POLLHUP)
    return not poller.poll(0)


def _read_proc(pid, filename, maximum=MAX_PROC):
    try:
        raw = (Path("/proc") / str(pid) / filename).read_bytes()
    except (OSError, ValueError) as exc:
        raise PeerImageHold("C3E_TIMEW_PEER_IMAGE_HOLD // PROC_UNAVAILABLE") from exc
    if not raw or len(raw) > maximum:
        _hold("PROC_RECORD_BOUNDS")
    return raw


def _start_ticks(pid):
    raw = _read_proc(pid, "stat").decode("ascii")
    try:
        # Linux /proc/pid/stat field 22, index 19 after ') '.
        start = raw.rsplit(") ", 1)[1].split()[19]
        if not start.isdecimal() or int(start) < 1:
            _hold("PROCESS_START_INVALID")
        return int(start)
    except (IndexError, ValueError, UnicodeError) as exc:
        raise PeerImageHold(
            "C3E_TIMEW_PEER_IMAGE_HOLD // PROCESS_START_UNAVAILABLE") from exc


def _identities(pid):
    try:
        raw = _read_proc(pid, "status").decode("ascii")
        data = {}
        for line in raw.splitlines():
            if line.startswith(("Uid:", "Gid:")):
                name, body = line.split(":", 1)
                if name in data:
                    _hold("DUPLICATE_KERNEL_IDENTITY")
                fields = body.split()
                if len(fields) != 4 or any(not x.isdecimal() for x in fields):
                    _hold("KERNEL_IDENTITY_MALFORMED")
                data[name] = tuple(map(int, fields))
        if set(data) != {"Uid", "Gid"}:
            _hold("KERNEL_IDENTITY_MISSING")
        return data
    except (UnicodeError, IndexError) as exc:
        raise PeerImageHold(
            "C3E_TIMEW_PEER_IMAGE_HOLD // KERNEL_IDENTITY_UNREADABLE") from exc


def _cgroup(pid):
    try:
        raw = _read_proc(pid, "cgroup", 4096).decode("utf-8")
    except UnicodeError as exc:
        raise PeerImageHold("C3E_TIMEW_PEER_IMAGE_HOLD // CGROUP_UNREADABLE") from exc
    rows = raw.splitlines()
    if (len(rows) != 1 or not rows[0].startswith("0::/") or
            "\x00" in raw):
        _hold("CGROUP_V2_REQUIRED")
    return rows[0][3:]


def _lsm(pid):
    raw = _read_proc(pid, "attr/current", 1024).rstrip(b"\n\x00")
    if not raw or b"\n" in raw or b"\x00" in raw:
        _hold("LSM_LABEL_INVALID")
    try:
        return raw.decode("ascii")
    except UnicodeError as exc:
        raise PeerImageHold("C3E_TIMEW_PEER_IMAGE_HOLD // LSM_LABEL_UNREADABLE") from exc


def _image(pid):
    fd = None
    try:
        fd = os.open(f"/proc/{pid}/exe", os.O_RDONLY | os.O_CLOEXEC)
        initial = os.fstat(fd)
        if (not stat.S_ISREG(initial.st_mode) or
                not 0 < initial.st_size <= MAX_IMAGE_BYTES):
            _hold("EXECUTABLE_UNSAFE_OR_TOO_LARGE")
        digest = hashlib.sha256()
        total = 0
        while total <= MAX_IMAGE_BYTES:
            blob = os.read(fd, min(65536, MAX_IMAGE_BYTES + 1 - total))
            if not blob:
                break
            total += len(blob)
            digest.update(blob)
        if total != initial.st_size or total > MAX_IMAGE_BYTES:
            _hold("EXECUTABLE_CHANGED_OR_TRUNCATED")
        final = os.fstat(fd)
        current = os.stat(f"/proc/{pid}/exe")
        def sig(st):
            return (st.st_dev, st.st_ino, st.st_size,
                    st.st_mtime_ns, st.st_ctime_ns)
        if sig(initial) != sig(final) or sig(final) != sig(current):
            _hold("EXECUTABLE_CHANGED_DURING_READ")
        return digest.hexdigest(), sig(initial)
    except OSError as exc:
        raise PeerImageHold(
            "C3E_TIMEW_PEER_IMAGE_HOLD // EXECUTABLE_UNAVAILABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)


def observe_untrusted_peer_process_image(receiver: socket.socket) -> dict:
    """Observe the ORIGINAL socket peer under its kernel pidfd.

    This is NOT a packet-bound/at-send-time attestation. The peer could
    execve between a different packet observation and this call; the sender
    could also be a genuine process that lies about an internal window.
    Thus every return's native authority flags are permanently False.
    """
    if sys.platform != "linux":
        _hold("LINUX_REQUIRED")
    if (type(receiver) is not socket.socket or
            receiver.family != socket.AF_UNIX or
            (receiver.type & 15) != socket.SOCK_SEQPACKET or
            type(receiver.gettimeout()) not in (float, int) or
            not 0 < receiver.gettimeout() <= MAX_TIMEOUT_SECONDS):
        _hold("BOUNDED_CONNECTED_UNIX_SEQPACKET_REQUIRED")

    pidfd = None
    try:
        raw = receiver.getsockopt(socket.SOL_SOCKET, SO_PEERPIDFD, 4)
        if len(raw) != 4:
            _hold("ORIGINAL_PEER_PIDFD_REQUIRED")
        pidfd = struct.unpack("=i", raw)[0]
        if pidfd < 0 or not _pidfd_alive(pidfd):
            _hold("ORIGINAL_PEER_EXITED")
        raw_creds = receiver.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, _CREDS.size)
        if len(raw_creds) != _CREDS.size:
            _hold("ORIGINAL_PEER_CREDS_REQUIRED")
        pid, uid, gid = _CREDS.unpack(raw_creds)
        if pid <= 1 or uid < 0 or gid < 0:
            _hold("ORIGINAL_PEER_CREDS_INVALID")
        begin = _start_ticks(pid)
        ident = _identities(pid)
        # A setuid/setgid transition is not an enrolled SwayPX user service.
        if (ident["Uid"] != (uid,) * 4 or
                ident["Gid"] != (gid,) * 4):
            _hold("KERNEL_PEER_IDENTITY_DRIFT")
        cgroup = _cgroup(pid)
        lsm = _lsm(pid)
        image_sha, image_stat = _image(pid)
        if (not _pidfd_alive(pidfd) or
                _start_ticks(pid) != begin or
                _identities(pid) != ident or
                _cgroup(pid) != cgroup or
                _lsm(pid) != lsm):
            _hold("PROCESS_CHANGED_DURING_OBSERVATION")
        # Recheck actual process exe inode even after the image fd closed.
        current = os.stat(f"/proc/{pid}/exe")
        if (current.st_dev, current.st_ino, current.st_size,
                current.st_mtime_ns, current.st_ctime_ns) != image_stat:
            _hold("PROCESS_EXECUTABLE_CHANGED")
        if not _pidfd_alive(pidfd):
            _hold("ORIGINAL_PEER_EXITED_DURING_READ")
        return {
            "kind": KIND,
            "status": "ACTUAL_LINUX_PEER_IMAGE_OBSERVED_UNENROLLED",
            "kernelPeerPidObserved": pid,
            "kernelPeerUidObserved": uid,
            "kernelPeerGidObserved": gid,
            "kernelProcessStartTicksObserved": begin,
            "kernelCgroupObservedUntrusted": cgroup,
            "kernelLsmObservedUntrusted": lsm,
            "executableSha256ObservedUntrusted": image_sha,
            "executableInodeObservedUntrusted": image_stat[1],
            "sourceMetadataIsNotPacketBound": True,
            **NO_AUTHORITY,
            "safeActions": [],
        }
    except OSError as exc:
        raise PeerImageHold(
            "C3E_TIMEW_PEER_IMAGE_HOLD // KERNEL_OR_PROC_UNAVAILABLE") from exc
    finally:
        if pidfd is not None and pidfd >= 0:
            os.close(pidfd)
