#!/usr/bin/env python3
"""V2p pidfd-backed lifetime lease on a V2n kernel-identified peer.

Linux-only, test-fixture-only, DENY-ONLY. SO_PEERCRED proves a socket's peer
PID/UID/GID, not its authorizing application, script, service unit, key
custody, or human consent. pidfd prevents confusing PID reuse with the
original peer's lifetime; an executable/boot/start-tick recheck refuses
changed evidence. No production authorization or ArchiveStore access.
"""
import os
import select
import socket
import struct

from scripts.trash.archive_v2_peer_evidence import (
    _boot_identity, _executable_digest, _start_ticks,
)

POLL_EXIT = select.POLLIN | select.POLLHUP | select.POLLERR | select.POLLNVAL
FIELDS = frozenset(("ownerId", "pid", "uid", "gid",
                    "startTicks", "bootId", "exeSha256",
                    "peerWitnessSha256", "state",
                    "sourceProcessVerified", "sourceAuthorityVerified",
                    "captureAllowed", "productionAllowed"))


class PeerLeaseError(Exception):
    """Stable refusal codes without paths or process command lines."""


def _require(ok, code):
    if not ok:
        raise PeerLeaseError(code)


class FixturePeerLease:
    """Holds a kernel pidfd tied to one already authenticated socket peer.

    Construction and revalidation compare peer identity at two points.
    Unlike a raw integer PID, a pidfd refers to the original process. It
    does not prevent a running peer from changing its script contents or
    guarantee the peer stays alive after the last precommit check.
    """
    def __init__(self, connection, witness):
        _require(type(witness) is dict
                 and set(witness) == FIELDS
                 and witness["state"] == "TEST_KERNEL_PEER_MATCHED_DENY_ONLY"
                 and witness["captureAllowed"] is False
                 and witness["sourceProcessVerified"] is False
                 and witness["productionAllowed"] is False,
                 "PEER_LEASE_WITNESS_INVALID")
        _require(isinstance(connection, socket.socket)
                 and connection.family == socket.AF_UNIX
                 and connection.type & socket.SOCK_STREAM == socket.SOCK_STREAM
                 and hasattr(socket, "SO_PEERCRED"),
                 "PEER_LEASE_SOCKET_INVALID")
        _require(type(witness["pid"]) is int and witness["pid"] > 0
                 and type(witness["startTicks"]) is int
                 and witness["startTicks"] > 0
                 and type(witness["uid"]) is int
                 and type(witness["gid"]) is int
                 and type(witness["bootId"]) is str
                 and type(witness["exeSha256"]) is str,
                 "PEER_LEASE_WITNESS_INVALID")
        _require(hasattr(os, "pidfd_open") and hasattr(select, "poll"),
                 "PEER_PIDFD_UNAVAILABLE")
        self._socket = connection
        self._witness = witness.copy()
        self._fd = None
        self._closed = False
        try:
            # Verify the socket's kernel credentials, not request metadata.
            self._check_credentials()
            _require(_start_ticks(witness["pid"]) == witness["startTicks"],
                     "PEER_LEASE_PROCESS_CHANGED")
            try:
                self._fd = os.pidfd_open(witness["pid"], 0)
            except (OSError, ValueError) as exc:
                raise PeerLeaseError("PEER_PIDFD_UNAVAILABLE") from exc
            self.require_alive()
        except BaseException:
            self.close()
            raise

    def _check_credentials(self):
        try:
            raw = self._socket.getsockopt(socket.SOL_SOCKET,
                                          socket.SO_PEERCRED, struct.calcsize("3i"))
            identity = struct.unpack("3i", raw)
        except (OSError, struct.error) as exc:
            raise PeerLeaseError("PEER_LEASE_CREDENTIAL_UNAVAILABLE") from exc
        _require(identity == (self._witness["pid"], self._witness["uid"],
                              self._witness["gid"]),
                 "PEER_LEASE_CREDENTIAL_CHANGED")

    def require_alive(self):
        """Refuse exited, re-executed, rebooted or replaced process evidence."""
        _require(not self._closed and self._fd is not None,
                 "PEER_LEASE_CLOSED")
        poll = select.poll()
        try:
            poll.register(self._fd, POLL_EXIT)
            events = poll.poll(0)
        except OSError as exc:
            raise PeerLeaseError("PEER_PIDFD_UNAVAILABLE") from exc
        _require(not events, "PEER_LEASE_PROCESS_EXITED")
        self._check_credentials()
        try:
            start = _start_ticks(self._witness["pid"])
            boot = _boot_identity()
            exe = _executable_digest(self._witness["pid"])
        except Exception as exc:
            raise PeerLeaseError("PEER_LEASE_PROCESS_CHANGED") from exc
        _require(start == self._witness["startTicks"]
                 and boot == self._witness["bootId"]
                 and exe == self._witness["exeSha256"],
                 "PEER_LEASE_PROCESS_CHANGED")
        # Close the final gap of an exit while re-reading /proc.
        _require(not poll.poll(0), "PEER_LEASE_PROCESS_EXITED")
        return {"state": "TEST_PEER_ALIVE_DENY_ONLY",
                "peerWitnessSha256": self._witness["peerWitnessSha256"],
                "sourceProcessVerified": False,
                "captureAllowed": False,
                "productionAllowed": False}

    def close(self):
        if not self._closed:
            self._closed = True
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False


def pin_fixture_peer(connection, inspected_witness):
    """Obtain a kernel-backed lease; never return an actual capture permit."""
    return FixturePeerLease(connection, inspected_witness)
