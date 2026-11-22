#!/usr/bin/env python3
"""Observe one genuine Linux TimeW candidate packet without authenticating SwayPX.

This is deliberately NOT the native source-admission verifier. It only proves
that the kernel attributed one bounded seqpacket to the same live peer that
created the connected Unix socket. The packet is NOT parsed or trusted; a
verified sender can still forge a window, C5 consent or a source receipt.

No socket is created, no commands are sent, no signing key or installer is
read, and no observation enables geometry, recovery, or authorization.
"""
from __future__ import annotations

import hashlib
import os
import select
import socket
import struct
import sys

# Linux UAPI: asm-generic/socket.h SO_PEERPIDFD = 77. Python may not expose it.
SO_PEERPIDFD = getattr(socket, "SO_PEERPIDFD", 77)
_CREDS = struct.Struct("=3i")
MAX_PAYLOAD = 4096
MAX_TIMEOUT_SECONDS = 1.5
OBSERVATION_KIND = "postapollo.connections.timew.native-peer-observation-untrusted.v1"
NO_AUTHORITY = {
    "compositorOriginAuthenticated": False,
    "explicitSelectionAuthenticated": False,
    "selectedSurfaceLifetimeAuthenticated": False,
    "activeSeatAuthenticated": False,
    "installedReleaseEnrolled": False,
    "sourceSigningRootEnrolled": False,
    "sourceEvidenceTrusted": False,
    "independentChallengeCustodyVerified": False,
    "protectedC5SpendVerified": False,
    "nativeGeometryAllowed": False,
    "timewRestoreAllowed": False,
    "productionAuthority": False,
}


class ObservationHold(ValueError):
    """Reject an ambiguous packet or missing kernel custody."""


def _hold(reason: str) -> None:
    raise ObservationHold("C3E_TIMEW_NATIVE_PEER_HOLD // " + reason)


def _live(fd: int) -> bool:
    """pidfd is signalled when its exact process exits; PID reuse is irrelevant."""
    poll = select.poll()
    poll.register(fd, select.POLLIN | select.POLLHUP | select.POLLERR)
    return not poll.poll(0)


def inspect_one_untrusted_packet(receiver: socket.socket) -> dict:
    """Consume one real bounded packet. Never return authorization or raw data.

    A future Connections trusted producer must independently verify enrolled
    release/process/LSM/seat, compositor selection origin and signed receipts.
    These are intentionally not parameters to this function: callers may not
    'upgrade' an observation with their own booleans, keys or policy files.
    """
    if sys.platform != "linux":
        _hold("LINUX_ONLY")
    if (type(receiver) is not socket.socket
            or receiver.family != socket.AF_UNIX
            or (receiver.type & 15) != socket.SOCK_SEQPACKET):
        _hold("EXACT_CONNECTED_UNIX_SEQPACKET_REQUIRED")
    timeout = receiver.gettimeout()
    if (type(timeout) not in (float, int)
            or not 0 < timeout <= MAX_TIMEOUT_SECONDS):
        _hold("BOUNDED_TIMEOUT_REQUIRED")
    peer_pidfd = None
    try:
        if receiver.getsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED) != 1:
            _hold("PER_PACKET_KERNEL_CREDENTIALS_REQUIRED")
        # The kernel returns a new fd for the SOCKET'S ORIGINAL peer process.
        # os.pidfd_open(pid) cannot replace this due to PID reuse between reads.
        raw_pidfd = receiver.getsockopt(socket.SOL_SOCKET, SO_PEERPIDFD, 4)
        if len(raw_pidfd) != 4:
            _hold("SOCKET_ORIGINAL_PIDFD_REQUIRED")
        peer_pidfd = struct.unpack("=i", raw_pidfd)[0]
        if peer_pidfd < 0 or not _live(peer_pidfd):
            _hold("SOCKET_ORIGINAL_PEER_EXITED")
        raw_creds = receiver.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED,
                                       _CREDS.size)
        if len(raw_creds) != _CREDS.size:
            _hold("KERNEL_PEER_CREDENTIALS_MISSING")
        original = _CREDS.unpack(raw_creds)
        if original[0] <= 1 or original[1] < 0 or original[2] < 0:
            _hold("KERNEL_PEER_CREDENTIALS_INVALID")
        payload, controls, flags, address = receiver.recvmsg(
            MAX_PAYLOAD + 1, socket.CMSG_SPACE(_CREDS.size))
        if ((flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC))
                or address or not 0 < len(payload) <= MAX_PAYLOAD):
            _hold("PACKET_TRUNCATED_OVERSIZED_OR_EMPTY")
        senders = []
        for level, kind, value in controls:
            if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                if len(value) != _CREDS.size:
                    _hold("PER_PACKET_CREDENTIALS_MALFORMED")
                senders.append(_CREDS.unpack(value))
        if len(senders) != 1 or senders[0] != original:
            _hold("DIFFERENT_SENDER_OR_INHERITED_SOCKET")
        if not _live(peer_pidfd):
            _hold("ORIGINAL_PEER_EXITED_DURING_READ")
        # A digest is for diagnostic correlation, never a signed source proof.
        return {
            "kind": OBSERVATION_KIND,
            "status": "KERNEL_PACKET_PEER_OBSERVED_BUT_SWAYPX_UNENROLLED",
            "packetSha256Untrusted": hashlib.sha256(payload).hexdigest(),
            "packetLength": len(payload),
            "kernelPeerPidObserved": original[0],
            "kernelPeerUidObserved": original[1],
            "kernelPeerGidObserved": original[2],
            "exactPeerPidfdAliveAtRead": True,
            "rawPacketUntrusted": True,
            **NO_AUTHORITY,
            "safeActions": [],
        }
    except (OSError, struct.error) as exc:
        raise ObservationHold(
            "C3E_TIMEW_NATIVE_PEER_HOLD // KERNEL_PEER_OBSERVATION_UNAVAILABLE"
        ) from exc
    finally:
        if peer_pidfd is not None and peer_pidfd >= 0:
            os.close(peer_pidfd)


def run_native_timew_source_admission(*_args, **_kwargs):
    """No approved installed source, release root or C5 spend exists yet."""
    _hold("PROTECTED_SWAYPX_SOURCE_AND_C5_NOT_ENROLLED")
