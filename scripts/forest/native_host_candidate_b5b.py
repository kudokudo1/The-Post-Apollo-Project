"""Forest B5b: disposable Linux host candidate, NOT installed authority.

One real process owns one inherited unnamed connected AF_UNIX SEQPACKET
endpoint. It can send exactly one fixed public HOLD status packet. No
private DB, inference, issuer, listener, credential grant or renderer.
The inherited descriptor and process observations do NOT authenticate
either peer, prove enrollment or establish revocation across processes.
"""
from __future__ import annotations

import array
import os
import socket
import sys

MAX_CONTROL_BYTES = 128
TIMEOUT_SECONDS = 2.0
# These are disposable test control tokens, NOT a native protocol.
_CONTROL = frozenset((
    b"STATUS", b"LIST_SESSIONS", b"DISCLOSE_SESSION_TITLES",
    b"READ_SESSION", b"GENERATE", b"DISCLOSE_PROVISIONAL", b"COMMIT_GENERATE",
    b"SEND", b"VOICE",
))
_PUBLIC_HOLD = (
    b'{"schema":"post-apollo.forest.b5b-ci-only","status":"UNKNOWN_HOLD",'
    b'"sourceAuthenticated":false,"recipientAuthenticated":false,'
    b'"permissionGranted":false,"productionAuthority":false,'
    b'"privateBytesSubmitted":0,"revocationFencedAck":false,"safeActions":[]}'
)


def _receive_control(channel):
    """Read one bounded packet; discard received rights before ANY refusal."""
    width = array.array("i").itemsize
    packet, ancillary, flags, _ = channel.recvmsg(
        MAX_CONTROL_BYTES + 1, socket.CMSG_SPACE(16 * width),
        socket.MSG_CMSG_CLOEXEC,
    )
    cleanup_ok = True
    # Empty packets can carry SCM_RIGHTS; cleanup precedes empty/truncation
    # checks. Linux discards excess received rights on ancillary truncation.
    for level, kind, payload in ancillary:
        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
            received = array.array("i")
            received.frombytes(payload[:len(payload) - len(payload) % width])
            if len(payload) % width:
                cleanup_ok = False
            for fd in received:
                try:
                    os.close(fd)
                except OSError:
                    cleanup_ok = False
    if (not cleanup_ok or ancillary or
            flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or
            not packet or len(packet) > MAX_CONTROL_BYTES):
        return None
    return packet


def _submit_public_hold_once(channel):
    """The candidate's sole outgoing serialization/write admission point.

    Single process, single synchronous exchange, fixed immutable public
    bytes. No caller-provided payload or retry. This is NOT an authorized
    private-send gate or cross-process revoke fence.
    """
    return channel.send(_PUBLIC_HOLD) == len(_PUBLIC_HOLD)


def run_disposable_fd(fd):
    """Adopt exactly one test endpoint and close it on every outcome.

    Return a local exit status only. A close/failed send is UNKNOWN, never
    a terminal receipt, protected revoke ACK, or evidence of delivered bytes.
    """
    if type(fd) is not int or fd < 3 or not sys.platform.startswith("linux"):
        return 2
    try:
        with socket.socket(fileno=fd) as channel:
            # No bind/listen/connect path, filesystem socket or TCP endpoint.
            if (channel.family != socket.AF_UNIX or
                    channel.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                    != socket.SOCK_SEQPACKET or
                    channel.getsockname() != "" or
                    channel.getpeername() != ""):
                return 2
            channel.settimeout(TIMEOUT_SECONDS)
            packet = _receive_control(channel)
            # Explicit stop closes the endpoint, does not acknowledge
            # protected revocation. Unknown/malformed input is not echoed.
            if packet == b"STOP" or packet not in _CONTROL:
                return 2
            return 0 if _submit_public_hold_once(channel) else 2
    except (OSError, ValueError, OverflowError):
        return 2


def main(argv):
    # No default startup, no named service, no file or endpoint selection.
    if len(argv) != 2 or argv[0] != "--disposable-test-fd":
        return 2
    if not argv[1].isascii() or not argv[1].isdecimal() or len(argv[1]) > 9:
        return 2
    return run_disposable_fd(int(argv[1]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
