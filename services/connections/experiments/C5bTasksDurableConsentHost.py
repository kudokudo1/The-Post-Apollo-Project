#!/usr/bin/env python3
"""Connections C5b: CI-only per-sender identity and durable consent refusal.

This is an experimental, never-installed process. A disposable harness owns the
reviewer descriptor and chooses the allowed client process. SO_PASSCRED verifies
the sender of EACH packet, unlike SO_PEERCRED on a pre-created socketpair.
Neither this harness nor a Python process proves signed production release
identity, independently authenticated human consent, or key access.
"""
from __future__ import annotations

import fcntl
import os
from pathlib import Path
import re
import selectors
import socket
import sqlite3
import stat
import struct
import sys
import time
from secrets import token_hex

import C5aTasksScopeHost as C5a

MARKER = "C5B_DISPOSABLE_DURABLE_CONSENT_NO_REAL_AUTHORITY"
MAX_ROWS = 256
CRED_SIZE = struct.calcsize("3i")
REQUEST_FIELDS = {"op", "scope", "target", "editorEpoch", "sourceGeneration"}
EXECUTE_FIELDS = REQUEST_FIELDS | {"requestId"}
REVIEW_FIELDS = {"op", "requestId", "scope", "target", "ttlMs", "confirmed"}


def private_ci() -> bool:
    if (sys.platform != "linux" or os.geteuid() == 0
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("POST_APOLLO_C5B_DISPOSABLE") != "1"):
        return False
    raw = os.environ.get("POST_APOLLO_C5B_FIXTURE_ROOT", "")
    if not re.fullmatch(r"/tmp/postapollo-c5b-durable-[A-Za-z0-9_-]{8,48}", raw):
        return False
    root = Path(raw)
    try:
        st = root.lstat()
        marker = (root / ".c5b-test-only")
        mt = marker.lstat()
        return (stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid()
                and stat.S_IMODE(st.st_mode) == 0o700
                and stat.S_ISREG(mt.st_mode) and mt.st_nlink == 1
                and mt.st_uid == os.geteuid()
                and stat.S_IMODE(mt.st_mode) == 0o600
                and marker.read_text() == MARKER + "\n")
    except (OSError, UnicodeError):
        return False


def protected_file(path: Path) -> int:
    """Create or reopen only a private, regular, single-link file."""
    flags = os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        fd = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        fd = os.open(path, flags)
    st = os.fstat(fd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid()
            or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600):
        os.close(fd)
        raise OSError("C5B_PRIVATE_FILE_REFUSED")
    return fd


def process_start_ticks(pid: int) -> int | None:
    """Read kernel process-start identity, not a caller-supplied PID label."""
    if type(pid) is not int or pid < 2:
        return None
    try:
        raw = Path("/proc/%d/stat" % pid).read_bytes()
        tail = raw.rsplit(b") ", 1)[1].split()
        number = int(tail[19])  # field 22, starttime
        return number if number > 0 else None
    except (OSError, ValueError, IndexError):
        return None


def packet(sock: socket.socket) -> tuple[object, tuple[int, int, int] | None]:
    raw, ancillary, flags, _address = sock.recvmsg(
        C5a.MAX_WIRE + 1, socket.CMSG_SPACE(CRED_SIZE))
    if not raw:
        raise EOFError
    credentials = []
    for level, kind, payload in ancillary:
        if (level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS
                and len(payload) == CRED_SIZE):
            credentials.append(struct.unpack("3i", payload))
    if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        return None, None
    return C5a.decode(raw), credentials[0] if len(credentials) == 1 else None


class DurableBroker:
    """Only host-side code owns state. No approved work touches real resources."""
    def __init__(self, root: Path, clock=None):
        if not private_ci() or Path(os.environ["POST_APOLLO_C5B_FIXTURE_ROOT"]) != root:
            raise OSError("C5B_REFUSED_OUTSIDE_DISPOSABLE_HOST")
        self.clock = clock or time.monotonic_ns
        self.client_binding: tuple[int, int, int, int] | None = None
        os.umask(0o077)
        self.lock_fd = protected_file(root / ".consent.lock")
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            db_fd = protected_file(root / "consent.sqlite3")
            os.close(db_fd)
            self.db = sqlite3.connect(str(root / "consent.sqlite3"),
                                      isolation_level=None, timeout=0.1)
            self.db.execute("PRAGMA journal_mode=DELETE")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA trusted_schema=OFF")
            self.db.execute("""CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY,
                scope TEXT NOT NULL, target TEXT NOT NULL,
                editor_epoch INTEGER NOT NULL, source_gen INTEGER NOT NULL,
                state TEXT NOT NULL, deadline_ns INTEGER NOT NULL DEFAULT 0
            )""")
            # Startup is itself a durable revocation barrier. No approval
            # survives a crashed/restarted host, even on the same OS boot.
            with self.db:
                self.db.execute("""UPDATE requests SET state='INTERRUPTED'
                    WHERE state IN ('PENDING', 'APPROVED')""")
        except Exception:
            os.close(self.lock_fd)
            raise

    def close(self):
        self.db.close()
        os.close(self.lock_fd)

    def bind_client(self, value: object) -> dict:
        if (not C5a.exact(value, {"op", "pid", "uid", "gid"})
                or not all(type(value[k]) is int for k in ("pid", "uid", "gid"))
                or value["pid"] < 2 or value["uid"] <= 0
                or value["gid"] < 0):
            return C5a.reply("INVALID_REVIEW_BINDING")
        start = process_start_ticks(value["pid"])
        if start is None:
            return C5a.reply("CALLER_PROCESS_NOT_FOUND")
        identity = (value["pid"], value["uid"], value["gid"], start)
        if self.client_binding is not None and self.client_binding != identity:
            return C5a.reply("CALLER_ALREADY_BOUND")
        self.client_binding = identity
        return C5a.reply("SYNTHETIC_CALLER_PID_BOUND_NO_RELEASE_ATTESTATION", True)

    def allowed_client(self, credentials: tuple[int, int, int] | None) -> bool:
        if self.client_binding is None or credentials is None:
            return False
        pid, uid, gid, start = self.client_binding
        return (credentials == (pid, uid, gid)
                and process_start_ticks(pid) == start)

    def client(self, value: object, credentials: tuple[int, int, int] | None) -> dict:
        if not self.allowed_client(credentials):
            return C5a.reply("CALLER_NOT_BOUND_OR_SENDER_CHANGED")
        if type(value) is not dict or type(value.get("op")) is not str:
            return C5a.reply("INVALID_CLIENT_FRAME")
        if value["op"] == "submit":
            if not C5a.exact(value, REQUEST_FIELDS):
                return C5a.reply("INVALID_REQUEST_FIELDS")
            if not C5a.valid_scope_target(value["scope"], value["target"],
                                          value["editorEpoch"], value["sourceGeneration"]):
                return C5a.reply("INVALID_SCOPE_OR_TARGET")
            count = self.db.execute("SELECT count(*) FROM requests").fetchone()[0]
            active = self.db.execute("""SELECT count(*) FROM requests
                WHERE state IN ('PENDING','APPROVED')""").fetchone()[0]
            if count >= MAX_ROWS or active >= C5a.MAX_REQUESTS:
                return C5a.reply("REQUEST_LIMIT_REACHED")
            rid = token_hex(16)
            with self.db:
                self.db.execute("""INSERT INTO requests
                    (id, scope, target, editor_epoch, source_gen, state)
                    VALUES (?, ?, ?, ?, ?, 'PENDING')""",
                    (rid, value["scope"], value["target"], value["editorEpoch"],
                     value["sourceGeneration"]))
            return C5a.reply("SYNTHETIC_REVIEW_PENDING_DURABLE", True, rid)
        if value["op"] == "execute":
            if not C5a.exact(value, EXECUTE_FIELDS):
                return C5a.reply("INVALID_EXECUTE_FIELDS")
            rid = value["requestId"]
            if type(rid) is not str or re.fullmatch(r"[0-9a-f]{32}", rid) is None:
                return C5a.reply("INVALID_REQUEST_ID")
            row = self.db.execute("""SELECT scope, target, editor_epoch,
                source_gen, state, deadline_ns FROM requests WHERE id=?""",
                (rid,)).fetchone()
            if row is None:
                return C5a.reply("UNKNOWN_REQUEST")
            if (row[:4] != (value["scope"], value["target"],
                            value["editorEpoch"], value["sourceGeneration"])
                    or not C5a.valid_scope_target(value["scope"], value["target"],
                                                  value["editorEpoch"],
                                                  value["sourceGeneration"])):
                return C5a.reply("REQUEST_BINDING_CHANGED")
            if row[4] != "APPROVED":
                return C5a.reply("NOT_APPROVED_OR_ALREADY_USED")
            # Commit the one-use tombstone BEFORE any success reply.
            with self.db:
                changed = self.db.execute("""UPDATE requests SET state='CONSUMED'
                    WHERE id=? AND state='APPROVED'""", (rid,)).rowcount
            if changed != 1 or self.clock() >= row[5]:
                return C5a.reply("REVOKED_OR_EXPIRED")
            return C5a.reply("SYNTHETIC_SCOPED_STEP_CONSUMED_NO_REAL_GRANT", True)
        return C5a.reply("CLIENT_CANNOT_AUTHORIZE")

    def reviewer(self, value: object) -> dict:
        if type(value) is not dict or type(value.get("op")) is not str:
            return C5a.reply("INVALID_REVIEW_FRAME")
        if value["op"] == "bindClient":
            return self.bind_client(value)
        if value["op"] == "approve":
            if not C5a.exact(value, REVIEW_FIELDS):
                return C5a.reply("INVALID_REVIEW_FIELDS")
            rid = value["requestId"]
            if type(rid) is not str or re.fullmatch(r"[0-9a-f]{32}", rid) is None:
                return C5a.reply("INVALID_REQUEST_ID")
            row = self.db.execute(
                "SELECT scope, target, state FROM requests WHERE id=?",
                (rid,)).fetchone()
            if row is None or row[2] != "PENDING":
                return C5a.reply("UNKNOWN_OR_ALREADY_REVIEWED")
            if (value["confirmed"] is not True or type(value["scope"]) is not str
                    or type(value["target"]) is not str
                    or value["scope"] != row[0] or value["target"] != row[1]
                    or type(value["ttlMs"]) is not int
                    or not 1 <= value["ttlMs"] <= C5a.MAX_TTL_MS):
                return C5a.reply("REVIEW_SCOPE_OR_CONSENT_REFUSED")
            deadline = self.clock() + value["ttlMs"] * 1_000_000
            with self.db:
                self.db.execute("""UPDATE requests
                    SET state='APPROVED', deadline_ns=?
                    WHERE id=? AND state='PENDING'""", (deadline, rid))
            return C5a.reply("SYNTHETIC_REVIEW_COMMITTED_NO_REAL_CONSENT", True)
        if value["op"] == "revoke":
            if not C5a.exact(value, {"op"}):
                return C5a.reply("INVALID_REVOKE_FIELDS")
            with self.db:
                self.db.execute("""UPDATE requests SET state='REVOKED'
                    WHERE state IN ('PENDING','APPROVED')""")
            return C5a.reply("SYNTHETIC_REVOCATION_COMMITTED", True)
        if value["op"] == "shutdown":
            if not C5a.exact(value, {"op"}):
                return C5a.reply("INVALID_SHUTDOWN_FIELDS")
            return C5a.reply("SYNTHETIC_SHUTDOWN", True)
        return C5a.reply("OPERATOR_OPERATION_REFUSED")


def serve(operator_fd: int, client_fd: int) -> int:
    root = Path(os.environ["POST_APOLLO_C5B_FIXTURE_ROOT"])
    with (socket.socket(fileno=operator_fd) as operator,
          socket.socket(fileno=client_fd) as client,
          selectors.DefaultSelector() as events):
        for sock in (operator, client):
            if (sock.family != socket.AF_UNIX
                    or sock.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE)
                    != socket.SOCK_SEQPACKET):
                return 2
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        # Kernel origin of original reviewer endpoint, not a label in a frame.
        reviewer_origin = struct.unpack("3i", operator.getsockopt(
            socket.SOL_SOCKET, socket.SO_PEERCRED, CRED_SIZE))
        ledger = DurableBroker(root)
        try:
            events.register(operator, selectors.EVENT_READ, "reviewer")
            events.register(client, selectors.EVENT_READ, "client")
            while True:
                available = events.select(timeout=4.0)
                if not available:
                    break
                for key, _ in available:
                    sock = key.fileobj
                    try:
                        data, sender = packet(sock)
                        if key.data == "reviewer":
                            result = (ledger.reviewer(data)
                                      if sender == reviewer_origin
                                      else C5a.reply("REVIEWER_ORIGIN_MISMATCH"))
                        else:
                            result = ledger.client(data, sender)
                        C5a.exchange(sock, result)
                        if (key.data == "reviewer" and sender == reviewer_origin
                                and type(data) is dict
                                and data.get("op") == "shutdown"
                                and result["ok"]):
                            return 0
                    except EOFError:
                        return 0
                    except (OSError, TimeoutError, ValueError, sqlite3.Error):
                        return 2
            return 0
        finally:
            ledger.close()


def main() -> int:
    if not private_ci():
        print("C5B_REFUSED_OUTSIDE_DISPOSABLE_HOST")
        return 2
    if len(sys.argv) != 4 or sys.argv[1] not in ("--host", "--client"):
        print("C5B_INVALID_MODE")
        return 2
    try:
        first, second = int(sys.argv[2]), int(sys.argv[3])
        if (first < 3
                or (sys.argv[1] == "--host" and (second < 3 or first == second))
                or (sys.argv[1] == "--client" and second != 0)):
            raise ValueError("INVALID_FD")
        if sys.argv[1] == "--client":
            return C5a.fake_client(first)
        return serve(first, second)
    except (ValueError, OSError, sqlite3.Error):
        print("C5B_DISPOSABLE_HOST_REFUSED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
