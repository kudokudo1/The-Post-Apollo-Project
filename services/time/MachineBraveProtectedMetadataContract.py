#!/usr/bin/env python3
"""MACHINE // disconnected, DENY-ONLY protected archive metadata broker seam.

There is intentionally NO executable server, socket listener, unit file,
native host, authenticator, signer or production deployment path here.

The default ingress has no grant hook. CI proves the read-only metadata
reader independently under a protected service UID after kernel permissions
deny the browser direct access. Real C3e host/seat provenance and C5 one-use
consent are unavailable, so every broker request refuses.

No ciphertext, tab URL, passphrase, export, write, delete, restore or window
operation is ever returned. This module must never be wired into normal Brave
until separate ownership, process authentication and consent reviews.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
from dataclasses import dataclass
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import MachineBraveSealedVault as vault
import MachineBraveArchiveAdmissionIntent as admission
import MachineBraveProcessLease as lifecycle
import MachineBraveRequestCancellation as cancellation

REQUEST_KIND = "machine-protected-archive-metadata-request-v1"
RESPONSE_KIND = "machine-protected-archive-metadata-response-v1"
PURPOSE = "machine.archive.metadata.read"
LIST = "LIST_METADATA"
INSPECT = "INSPECT_METADATA"
MAX_REQUEST = 4096
MAX_RESPONSE = 16384
MAX_RECORDS = vault.MAX_RECORDS
REFUSED = {"kind": RESPONSE_KIND, "status": "request_rejected",
           "client_authenticated": False,
           "operator_consent_verified": False,
           "restore_allowed": False, "safe_actions": []}


class BrokerRefusal(ValueError):
    pass


def refuse():
    raise BrokerRefusal("PROTECTED ARCHIVE METADATA REFUSED")


@dataclass(frozen=True)
class Peer:
    pid: int
    uid: int
    gid: int


def peer_credentials(connection):
    """Kernel SO_PEERCRED, never a UID/PID claimed in JSON or an origin argv."""
    if not hasattr(socket, "SO_PEERCRED"):
        refuse()
    try:
        raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        pid, uid, gid = struct.unpack("3i", raw)
    except (OSError, ValueError, struct.error, AttributeError):
        refuse()
    if pid <= 1 or uid < 0 or gid < 0:
        refuse()
    return Peer(pid, uid, gid)


def _receive_exact(connection, count):
    pieces = []
    while count:
        part = connection.recv(count)
        if not part:
            refuse()
        pieces.append(part)
        count -= len(part)
    return b"".join(pieces)


def read_frame(connection):
    size = struct.unpack("=I", _receive_exact(connection, 4))[0]
    if not 1 <= size <= MAX_REQUEST:
        refuse()
    raw = _receive_exact(connection, size)
    return raw, parse_request(raw)


def parse_request(raw):
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_REQUEST:
        refuse()
    request = vault.strict_json(raw)
    if type(request) is not dict:
        refuse()
    if request.get("kind") != REQUEST_KIND:
        refuse()
    action = request.get("action")
    if action == LIST:
        vault.exact_keys(request, ("kind", "action", "challenge"))
    elif action == INSPECT:
        vault.exact_keys(request, ("kind", "action", "challenge", "record_id"))
        vault._id(request["record_id"])
    else:
        refuse()
    vault._id(request["challenge"])
    return request


def _protected_directory_fd(root):
    """Read-only protected service-owned data root; no user HOME/XDG paths."""
    if not isinstance(root, Path) or not root.is_absolute():
        refuse()
    if os.geteuid() == 0:  # production broker must be distinct non-root UID
        refuse()
    if root.is_symlink():
        refuse()
    try:
        fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                     getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(fd)
    except OSError:
        refuse()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or
            stat.S_IMODE(info.st_mode) != 0o700):
        os.close(fd)
        refuse()
    return fd


def _read_metadata(fd, identifier):
    record_id = vault._id(identifier)
    raw = vault._safe_open_file(fd, record_id + ".json")
    entry = vault._record(raw, record_id)
    if entry["kind"] != vault.RECORD_KIND:
        refuse()
    return {
        "record_id": record_id,
        "created_at_utc": entry["created_at_utc"],
        "sealed_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def metadata_from_protected_root(root, request):
    """Only for a broker already running as protected UID after grant check.

    The source root is a trusted supervisor/fixture argument, never from JSON.
    It must contain only existing 0600 sealed-vault records; nothing created.
    """
    fd = _protected_directory_fd(root)
    try:
        names = []
        try:
            with os.scandir(fd) as entries:
                for item in entries:
                    if item.name.startswith(".tmp-"):
                        refuse()
                    if not item.name.endswith(".json"):
                        refuse()
                    key = vault._id(item.name[:-5])
                    if item.is_symlink() or not item.is_file(follow_symlinks=False):
                        refuse()
                    names.append(key)
                    if len(names) > MAX_RECORDS:
                        refuse()
        except OSError:
            refuse()
        names.sort()
        if request["action"] == INSPECT:
            if request["record_id"] not in names:
                refuse()
            return {"record": _read_metadata(fd, request["record_id"])}
        if request["action"] != LIST:
            refuse()
        return {"records": [_read_metadata(fd, key) for key in names],
                "record_count": len(names)}
    finally:
        os.close(fd)


def _send(connection, payload):
    serialized = json.dumps(payload, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")
    if not 1 <= len(serialized) <= MAX_RESPONSE:
        refuse()
    connection.sendall(struct.pack("=I", len(serialized)) + serialized)


def handle_once(connection, *, protected_root):
    """Metadata broker ingress is DENY ONLY without independent C3e+C5.

    This performs real socket parsing and exact request/peer binding but
    it cannot grant or return metadata. The separate protected reader is
    directly exercised by privileged, isolated source tests only.
    """
    response = dict(REFUSED)
    try:
        connection.settimeout(2.0)
        initial = peer_credentials(connection)
        if os.geteuid() == 0 or initial.uid == os.geteuid():
            refuse()
        # Obtain stable task reference FROM THE KERNEL SOCKET before parsing.
        # Unsupported kernel, dead peer or changed executable => refusal.
        with lifecycle.capture_socket_peer(connection, peer=initial) as lease:
            # Capture kernel session context before consuming a request.
            # No positive rights even if it stays unchanged.
            guard = cancellation.begin(connection, lease)
            try:
                raw, request = read_frame(connection)
                if not guard.valid() or peer_credentials(connection) != initial:
                    refuse()
                intent = admission.bind_request(
                    raw, peer_pid=initial.pid,
                    peer_uid=initial.uid, peer_gid=initial.gid)
                if (intent.action != request["action"] or
                        intent.challenge != request["challenge"]):
                    refuse()
                if not guard.valid() or peer_credentials(connection) != initial:
                    refuse()
                # Cancellation/session context is negative evidence only.
                # Signed C3e host and one-use C5 consent remain absent.
                if admission.may_read_metadata(intent):
                    refuse()  # no positive path even if monkeypatched
            finally:
                guard.cancel()
        refuse()
    except (BrokerRefusal, lifecycle.LifecycleRefusal,
            cancellation.CancelledRequest,
            admission.IntentRefusal, vault.VaultError,
            OSError, ValueError, TypeError, KeyError, struct.error,
            TimeoutError):
        response = dict(REFUSED)
    try:
        _send(connection, response)
    except (OSError, BrokerRefusal):
        return False
    return False


if __name__ == "__main__":
    # Explicitly not a runnable broker until the external C3e/C5 boundary
    # and privileged-service deployment are designed, approved and reviewed.
    print(json.dumps(REFUSED, sort_keys=True, separators=(",", ":")))
    raise SystemExit(1)
