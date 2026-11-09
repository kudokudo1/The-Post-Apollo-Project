#!/usr/bin/env python3
"""C3e-J: disposable, read-only release witness in a separate Linux process.

This process exposes a SINGLE observation, not a signed proof, grant, recovery
decision or release admission. Kernel SO_PEERCRED and per-message SCM_CREDENTIALS
must both match a test-supervisor-pinned PID/UID/process-start identity.
This prevents a connection FD forwarded to a different process from acting as
the pinned caller. It does NOT secure a witness DB from a same-UID writer or
privileged restoration. Not installed on the operator's machine.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import struct
import sys

HERE = Path(__file__).resolve().parent
REQUEST = b"WITNESS-FLOOR-READ-V1"
MAX_PACKET = 96
MAX_RESPONSE = 4096
CREDENTIAL_BYTES = struct.calcsize("3i")


class Refused(Exception):
    pass


def deny(reason):
    raise Refused(reason)


def _load_witness():
    spec = importlib.util.spec_from_file_location("c3ej_witness", HERE / "C3eRollbackWitness.py")
    if spec is None or spec.loader is None:
        deny("WITNESS_SOURCE_MISSING")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def process_start(pid):
    """Linux /proc stat field 22, never a self-reported request value."""
    if type(pid) is not int or pid <= 0:
        deny("INVALID_PEER_PID")
    try:
        data = Path("/proc/%d/stat" % pid).read_text()
        after = data.rsplit(") ", 1)[1].split()
        ticks = after[19]
        if not ticks.isdecimal() or int(ticks) <= 0:
            deny("INVALID_PROCESS_START")
        return ticks
    except (OSError, IndexError, ValueError):
        deny("PROCESS_START_UNAVAILABLE")


def _private_directory(path):
    try:
        st = os.lstat(path)
    except OSError:
        deny("PRIVATE_DIRECTORY_MISSING")
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or
            stat.S_IMODE(st.st_mode) & 0o077):
        deny("PRIVATE_DIRECTORY_UNSAFE")


def read_floor(path):
    """Use SQLite read-only mode and existing C3e-F witness row validation."""
    try:
        st = os.lstat(path)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or
                stat.S_IMODE(st.st_mode) & 0o077 or st.st_nlink != 1):
            deny("WITNESS_FILE_UNSAFE")
        uri = Path(path).as_uri() + "?mode=ro"
        db = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=2)
        try:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            node, root, authority, epoch, sequence = _load_witness()._read(db)
            db.execute("ROLLBACK")
        finally:
            db.close()
        after = os.lstat(path)
        if (st.st_ino, st.st_dev) != (after.st_ino, after.st_dev):
            deny("WITNESS_FILE_CHANGED")
        identity = hashlib.sha256(
            json.dumps([node, root, authority], separators=(",", ":")).encode()
        ).hexdigest()
        return {"schema": "postapollo.connections.c3ej.witness-read.v1",
                "minimum_policy_epoch": epoch,
                "minimum_release_sequence": sequence,
                "enrollment_sha256": identity,
                "authorized": False, "writable": False}
    except Refused:
        raise
    except (OSError, ValueError, sqlite3.Error):
        deny("WITNESS_READ_UNAVAILABLE")
    except Exception:
        deny("WITNESS_VALIDATION_FAILED")


def _credentials(conn):
    raw_peer = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, CREDENTIAL_BYTES)
    peer = struct.unpack("3i", raw_peer)
    packet, ancillary, flags, address = conn.recvmsg(
        MAX_PACKET, socket.CMSG_SPACE(CREDENTIAL_BYTES))
    if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        deny("TRUNCATED_PACKET")
    sender = [struct.unpack("3i", data[:CREDENTIAL_BYTES])
              for level, kind, data in ancillary
              if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS
              and len(data) >= CREDENTIAL_BYTES]
    if len(sender) != 1:
        deny("MESSAGE_SENDER_UNAVAILABLE")
    return peer, sender[0], packet


def serve(*, socket_path, witness_db, peer_pid, peer_uid, peer_start):
    path = Path(socket_path)
    if not path.is_absolute() or not Path(witness_db).is_absolute():
        deny("REQUIRE_ABSOLUTE_PATH")
    _private_directory(path.parent)
    _private_directory(Path(witness_db).parent)
    if os.path.lexists(path):
        deny("SOCKET_ALREADY_EXISTS")
    # The test supervisor passes expected values at launch; never accept
    # identity, filename or permission changes inside the client packet.
    if peer_uid != os.getuid() or peer_start != process_start(peer_pid):
        deny("SUPERVISOR_IDENTITY_INVALID")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    try:
        server.settimeout(10)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        server.bind(str(path))
        os.chmod(path, 0o600)
        server.listen(1)
        print("C3EJ_READY // test-only-read-only-peer", flush=True)
        conn, _ = server.accept()
        with conn:
            conn.settimeout(5)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            try:
                peer, sender, packet = _credentials(conn)
                if (peer != sender or peer[0] != peer_pid or
                        peer[1] != peer_uid or sender[1] != peer_uid or
                        process_start(sender[0]) != peer_start):
                    deny("KERNEL_SENDER_IDENTITY_REFUSED")
                if packet != REQUEST:
                    deny("READ_ONLY_OPERATION_REQUIRED")
                reply = read_floor(Path(witness_db))
            except (Refused, OSError, socket.error) as exc:
                reply = {"error": "REFUSED", "authorized": False}
            data = json.dumps(reply, sort_keys=True, separators=(",", ":")).encode()
            if len(data) > MAX_RESPONSE:
                data = b'{"error":"REFUSED","authorized":false}'
            try:
                conn.sendall(data)
            except OSError:
                pass
    finally:
        server.close()
        # Only unlink the socket inode this process created.
        try:
            if path.is_socket():
                path.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CI-only read-only C3e witness peer")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--witness", required=True)
    parser.add_argument("--peer-pid", required=True, type=int)
    parser.add_argument("--peer-uid", required=True, type=int)
    parser.add_argument("--peer-start", required=True)
    args = parser.parse_args()
    try:
        serve(socket_path=args.socket, witness_db=args.witness,
              peer_pid=args.peer_pid, peer_uid=args.peer_uid,
              peer_start=args.peer_start)
    except (Refused, OSError) as exc:
        print("C3EJ_REFUSED // startup", file=sys.stderr)
        sys.exit(2)
