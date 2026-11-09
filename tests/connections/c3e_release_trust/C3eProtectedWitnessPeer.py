#!/usr/bin/env python3
"""C3e-K: test-only, separately-owned, read-only Linux witness service.

The witness runs with a DIFFERENT Linux UID from the requesting process.
In disposable CI the server has UID 0, a 0600 root-owned SQLite witness,
a private root-only ledger directory, and a non-writable group-accessible
UNIX socket directory. Neither a signed release nor credential authority
is granted. This is NOT a production root daemon or host installation.

The expected peer PID/UID/GID/start are supplied by the trusted test
supervisor at service launch. Actual client identity comes from Linux
SO_PEERCRED and per-packet SCM_CREDENTIALS. No client-supplied identity,
file path, state or method changes are accepted in a packet.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import stat
import sys

import C3eReadOnlyWitnessPeer as previous

RESPONSE_LIMIT = 4096
READY = "C3EK_READY // DISTINCT_OS_UID_READ_ONLY_WITNESS"
ERROR = {"error": "REFUSED", "authorized": False}


class Refused(Exception):
    pass


def deny(code):
    raise Refused(code)


def must_dir(path: Path, *, uid: int, gid: int, mode: int, code: str):
    try:
        st = os.lstat(path)
    except OSError:
        deny(code)
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != uid or
            st.st_gid != gid or stat.S_IMODE(st.st_mode) != mode):
        deny(code)


def preflight(*, sock: Path, witness: Path, peer_pid: int,
              peer_uid: int, peer_gid: int, peer_start: str):
    if os.name != "posix" or not sys.platform.startswith("linux"):
        deny("LINUX_REQUIRED")
    # A root runner is required ONLY in disposable CI. This file never
    # installs a daemon, enables a grant or edits the actual workstation.
    if os.geteuid() != 0 or os.getuid() != 0:
        deny("DISPOSABLE_CI_ROOT_REQUIRED")
    if (type(peer_pid) is not int or peer_pid < 2 or
            type(peer_uid) is not int or peer_uid <= 0 or
            type(peer_gid) is not int or peer_gid < 0 or
            type(peer_start) is not str):
        deny("INVALID_EXPECTED_PEER")
    if not sock.is_absolute() or not witness.is_absolute():
        deny("ABSOLUTE_PATH_REQUIRED")
    base = sock.parent.parent
    if (base != witness.parent.parent or
            sock.parent.name != "public" or
            witness.parent.name != "private" or
            base.parent != Path("/run") or
            not base.name.startswith("c3ek-ci-")):
        deny("CI_PATH_SCOPE_REFUSED")
    must_dir(base, uid=0, gid=0, mode=0o711, code="BASE_NOT_PROTECTED")
    must_dir(sock.parent, uid=0, gid=peer_gid, mode=0o750,
             code="PUBLIC_SOCKET_DIRECTORY_UNSAFE")
    must_dir(witness.parent, uid=0, gid=0, mode=0o700,
             code="WITNESS_DIRECTORY_UNSAFE")
    if os.path.lexists(sock):
        deny("SOCKET_ALREADY_EXISTS")
    try:
        st = os.lstat(witness)
    except OSError:
        deny("WITNESS_MISSING")
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or
            st.st_gid != 0 or stat.S_IMODE(st.st_mode) != 0o600 or
            st.st_nlink != 1):
        deny("WITNESS_FILE_UNSAFE")
    try:
        if previous.process_start(peer_pid) != peer_start:
            deny("EXPECTED_PROCESS_START_MISMATCH")
    except previous.Refused:
        deny("EXPECTED_PEER_UNAVAILABLE")


def serve(*, socket_path: str, witness_db: str, peer_pid: int,
          peer_uid: int, peer_gid: int, peer_start: str):
    sock = Path(socket_path)
    witness = Path(witness_db)
    preflight(sock=sock, witness=witness, peer_pid=peer_pid,
              peer_uid=peer_uid, peer_gid=peer_gid, peer_start=peer_start)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    sock_inode = None
    try:
        listener.settimeout(10)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        listener.bind(str(sock))
        sock_inode = os.lstat(sock).st_ino
        os.chown(sock, 0, peer_gid)
        os.chmod(sock, 0o660)
        listener.listen(1)
        print(READY, flush=True)
        conn, _ = listener.accept()
        with conn:
            conn.settimeout(5)
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            try:
                connected, sender, packet = previous._credentials(conn)
                expected = (peer_pid, peer_uid, peer_gid)
                if (connected != expected or sender != expected or
                        previous.process_start(sender[0]) != peer_start):
                    deny("KERNEL_SENDER_OR_PROCESS_START_REFUSED")
                if packet != previous.REQUEST:
                    deny("READ_ONLY_OPERATION_REQUIRED")
                # The witness remains owned by the SERVER identity.
                response = previous.read_floor(witness)
            except (Refused, previous.Refused, OSError, ValueError):
                response = ERROR
            data = json.dumps(response, separators=(",", ":"), sort_keys=True).encode()
            if len(data) > RESPONSE_LIMIT:
                data = json.dumps(ERROR).encode()
            try:
                conn.sendall(data)
            except OSError:
                pass
    finally:
        listener.close()
        # Root-owned socket directory is not writable by the client.
        if sock_inode is not None:
            try:
                st = os.lstat(sock)
                if stat.S_ISSOCK(st.st_mode) and st.st_ino == sock_inode:
                    sock.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CI-only protected witness peer")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--witness", required=True)
    parser.add_argument("--peer-pid", type=int, required=True)
    parser.add_argument("--peer-uid", type=int, required=True)
    parser.add_argument("--peer-gid", type=int, required=True)
    parser.add_argument("--peer-start", required=True)
    args = parser.parse_args()
    try:
        serve(socket_path=args.socket, witness_db=args.witness,
              peer_pid=args.peer_pid, peer_uid=args.peer_uid,
              peer_gid=args.peer_gid, peer_start=args.peer_start)
    except (Refused, previous.Refused, OSError):
        print("C3EK_REFUSED // isolated-test-startup", file=sys.stderr)
        sys.exit(2)
