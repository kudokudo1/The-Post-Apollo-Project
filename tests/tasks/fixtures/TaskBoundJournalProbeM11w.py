#!/usr/bin/env python3
"""M11w: synthetic-only parent-side bound disposable journal process probe.

No CLI, no production paths, no Quickshell. Tests only. A verified M11u
synthetic child is launched from sealed bytes and reads a sealed copy of
the existing M11l disposable journal implementation, retaining its lock.
Hash pins are supplied by the test caller, NOT independently trusted here.
"""
from __future__ import annotations

import fcntl
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import select
import sqlite3
import stat
import subprocess
import sys
import time
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[3]
TESTS = ROOT / "tests/tasks/fixtures"
SPEC = importlib.util.spec_from_file_location(
    "m11w_process_probe_dependency", TESTS / "TaskInterpreterProcessProbeM11v.py")
m11v = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m11v
SPEC.loader.exec_module(m11v)

M11L = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
MAX_OWNER_BYTES = 131072
LIMIT_FRAME = 4096
SEALS = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW
         | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)


class SyntheticOwnerRefusal(ValueError):
    """Fixed refusal; no private folder, task document or stdout leakage."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SyntheticOwnerRefusal(message)


def pinned_owner_bytes(expected_digest: str) -> bytes:
    """Pin M11l SOURCE bytes, not live source. Caller must supply digest.

    CI calculates this digest from the checkout for mechanics testing only.
    This is not an independently trusted production supply-chain pin.
    """
    require(type(expected_digest) is str
            and re.fullmatch("[0-9a-f]{64}", expected_digest),
            "OWNER_SOURCE_PIN_REQUIRED")
    fd = -1
    try:
        fd = os.open(M11L, os.O_RDONLY | os.O_NOFOLLOW)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 1024 < before.st_size <= MAX_OWNER_BYTES,
                "INVALID_DISPOSABLE_OWNER_SOURCE")
        raw = bytearray()
        while len(raw) <= MAX_OWNER_BYTES:
            chunk = os.read(fd, MAX_OWNER_BYTES + 1 - len(raw))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(fd)
        end = M11L.lstat()
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size,
                               x.st_mtime_ns, x.st_ctime_ns)
        require(identity(before) == identity(after) == identity(end)
                and len(raw) == before.st_size,
                "OWNER_SOURCE_CHANGED")
        require(hmac.compare_digest(hashlib.sha256(raw).hexdigest(),
                                    expected_digest),
                "OWNER_SOURCE_DIGEST_MISMATCH")
        return bytes(raw)
    except OSError:
        raise SyntheticOwnerRefusal("OWNER_SOURCE_UNAVAILABLE") from None
    finally:
        if fd >= 0:
            os.close(fd)


def seal_bytes(data: bytes, label: str) -> int:
    require(type(data) is bytes and len(data) > 0
            and hasattr(os, "memfd_create")
            and hasattr(os, "MFD_ALLOW_SEALING"),
            "SEALED_SYNTHETIC_FD_REQUIRED")
    fd = -1
    try:
        fd = os.memfd_create(label, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        remaining = memoryview(data)
        while remaining:
            n = os.write(fd, remaining)
            require(n > 0, "SEALED_SYNTHETIC_FD_WRITE")
            remaining = remaining[n:]
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, SEALS)
        require(fcntl.fcntl(fd, fcntl.F_GET_SEALS) & SEALS == SEALS,
                "SEALED_SYNTHETIC_FD_INVALID")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except (OSError, ValueError):
        if fd >= 0:
            os.close(fd)
        raise SyntheticOwnerRefusal("SEALED_SYNTHETIC_FD_UNAVAILABLE") from None


def durable_row(folder: Path) -> dict:
    """Read the disposable journal only, using SQLite mode=ro."""
    require(isinstance(folder, Path) and folder.is_absolute()
            and folder.name == "m11l-tasks-copy"
            and ".." not in folder.parts,
            "DISPOSABLE_JOURNAL_DIRECTORY_ONLY")
    db = folder / "gate-review.db"
    try:
        st = db.lstat()
        require(stat.S_ISREG(st.st_mode) and not db.is_symlink()
                and st.st_uid == os.geteuid() and st.st_nlink == 1
                and stat.S_IMODE(st.st_mode) & 0o077 == 0,
                "UNSAFE_DISPOSABLE_JOURNAL")
        uri = "file:" + quote(str(db), safe="/") + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=0.2) as conn:
            conn.row_factory = sqlite3.Row
            require(conn.execute("PRAGMA user_version").fetchone()[0] == 2,
                    "UNEXPECTED_JOURNAL_SCHEMA")
            row = conn.execute(
                "SELECT writer,phase,epoch,pending_stage,source_hash,backup_hash"
                " FROM owner WHERE id=1").fetchone()
            require(row is not None, "MISSING_DURABLE_OWNER")
            return dict(row)
    except (OSError, sqlite3.DatabaseError):
        raise SyntheticOwnerRefusal("DISPOSABLE_JOURNAL_UNAVAILABLE") from None


def _unique(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, "DUPLICATE_SYNTHETIC_REPLY")
        result[k] = v
    return result


class BoundDisposableSession:
    def __init__(self, proc: subprocess.Popen, pidfd: int, folder: Path,
                 session: str, epoch: int, phase: str):
        self.proc = proc
        self.pidfd = pidfd
        self.folder = folder
        self.session = session
        self.epoch = epoch
        self.phase = phase
        self.request_id = 0
        self._buffer = b""
        self._closed = False

    def read_frame(self, seconds=4):
        deadline = time.monotonic() + seconds
        while b"\n" not in self._buffer:
            require(len(self._buffer) <= LIMIT_FRAME,
                    "SYNTHETIC_REPLY_TOO_LARGE")
            remaining = deadline - time.monotonic()
            require(remaining > 0, "SYNTHETIC_REPLY_TIMEOUT")
            ready, _, _ = select.select([self.proc.stdout], [], [], remaining)
            require(bool(ready), "SYNTHETIC_REPLY_TIMEOUT")
            chunk = os.read(self.proc.stdout.fileno(), LIMIT_FRAME + 1)
            require(bool(chunk), "SYNTHETIC_CHILD_CLOSED")
            self._buffer += chunk
        frame, self._buffer = self._buffer.split(b"\n", 1)
        require(len(frame) <= LIMIT_FRAME, "SYNTHETIC_REPLY_TOO_LARGE")
        try:
            data = json.loads(frame.decode("utf-8"), object_pairs_hook=_unique)
        except (UnicodeError, ValueError):
            raise SyntheticOwnerRefusal("SYNTHETIC_REPLY_INVALID") from None
        require(type(data) is dict, "SYNTHETIC_REPLY_INVALID")
        return data

    def send(self, kind, *, override_session=None, epoch=None):
        require(not self._closed and self.proc.poll() is None,
                "SYNTHETIC_PROCESS_EXITED")
        require(kind in ("status","reserve"), "SYNTHETIC_REQUEST_UNKNOWN")
        self.request_id += 1
        challenge = secrets.token_hex(24)
        request = {"protocol":1, "kind":kind, "requestId":self.request_id,
                   "sessionId":self.session if override_session is None
                   else override_session,
                   "epoch":self.epoch if epoch is None else epoch,
                   "challenge":challenge}
        try:
            self.proc.stdin.write(
                (json.dumps(request, separators=(",",":")) + "\n").encode())
            self.proc.stdin.flush()
        except (OSError, BrokenPipeError):
            raise SyntheticOwnerRefusal("SYNTHETIC_REQUEST_FAILED") from None
        data = self.read_frame()
        if data.get("kind") == "refused":
            require(data.get("status") in
                    ("STALE_OR_INVALID_SESSION", "RECOVERY_REVIEW_REQUIRED"),
                    "SYNTHETIC_REFUSAL_INVALID")
            return data
        require(set(data) == {"protocol","kind","status","sessionId",
                              "requestId","epoch","phase","pending","challenge"}
                and data["protocol"] == 1 and data["kind"] == "reply"
                and data["status"] == "SYNTHETIC_ONLY"
                and type(data["sessionId"]) is str
                and hmac.compare_digest(data["sessionId"],self.session)
                and type(data["requestId"]) is int
                and data["requestId"] == self.request_id
                and type(data["epoch"]) is int
                and data["epoch"] == self.epoch
                and type(data["challenge"]) is str
                and hmac.compare_digest(data["challenge"],challenge),
                "SYNTHETIC_SESSION_RESPONSE_MISMATCH")
        row = durable_row(self.folder)
        require(row["writer"] == "m11w-" + self.session
                and row["epoch"] == self.epoch
                and row["phase"] == data["phase"]
                and (row["pending_stage"] is not None) is data["pending"],
                "SYNTHETIC_JOURNAL_SESSION_MISMATCH")
        return data

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self.proc.poll() is None:
            self.proc.kill()
        try:
            self.proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.communicate(timeout=2)
        os.close(self.pidfd)


def attach_synthetic(folder: Path, mode: str,
                     child: m11v.capsule.SyntheticSnapshot,
                     interpreter: m11v.InterpreterPin,
                     owner_bytes: bytes,
                     expected_owner_digest: str) -> BoundDisposableSession:
    """Launch a sealed synthetic child that owns ONE real disposable lock."""
    require(mode in ("NEW","EXISTING")
            and folder.is_absolute() and folder.name == "m11l-tasks-copy"
            and ".." not in folder.parts,
            "SYNTHETIC_ATTACH_SCOPE_REQUIRED")
    require(isinstance(child, m11v.capsule.SyntheticSnapshot)
            and type(child.script) is bytes
            and child.script.startswith(m11v.capsule.MARKER)
            and hmac.compare_digest(hashlib.sha256(child.script).hexdigest(),
                                    child.sha256)
            and type(owner_bytes) is bytes
            and 1024 < len(owner_bytes) <= MAX_OWNER_BYTES
            and type(expected_owner_digest) is str
            and re.fullmatch("[0-9a-f]{64}", expected_owner_digest)
            and hmac.compare_digest(
                hashlib.sha256(owner_bytes).hexdigest(),
                expected_owner_digest),
            "SYNTHETIC_SEALED_SOURCES_REQUIRED")
    require(m11v.pinned_interpreter(interpreter.digest) == interpreter,
            "INTERPRETER_PIN_CHANGED")
    code_fd = -1
    owner_fd = -1
    pidfd = -1
    proc = None
    try:
        code_fd = seal_bytes(child.script, "m11w-test-child")
        owner_fd = seal_bytes(owner_bytes, "m11w-disposable-owner")
        proc = subprocess.Popen(
            [interpreter.path,"-I","-S","-B","/proc/self/fd/"+str(code_fd),
             str(folder),str(owner_fd),mode],
            pass_fds=(code_fd,owner_fd), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0,
            env={"PATH":"/usr/bin:/bin","LANG":"C","PYTHONNOUSERSITE":"1"})
        pidfd = os.pidfd_open(proc.pid, 0)
        require(proc.poll() is None, "SYNTHETIC_HOST_DIED")
        identity = m11v._observed_executable_identity(proc.pid)
        require(identity == (interpreter.device, interpreter.inode)
                and os.stat("/proc/"+str(proc.pid)).st_uid == os.geteuid()
                and m11v._start_ticks(proc.pid) > 0,
                "SYNTHETIC_HOST_PROCESS_MISMATCH")
        # A temporary reader object allows the same bounded frame parser.
        reader = BoundDisposableSession(proc, pidfd, folder, "", -1, "")
        hello = reader.read_frame()
        require(set(hello) == {"protocol","kind","sessionId","phase",
                               "epoch","status"}
                and hello["protocol"] == 1
                and hello["kind"] == "hello"
                and hello["status"] == "SYNTHETIC_OWNER_ATTACHED"
                and type(hello["sessionId"]) is str
                and re.fullmatch("[0-9a-f]{48}",hello["sessionId"])
                and type(hello["epoch"]) is int
                and hello["phase"] in ("JSON_ACTIVE","RECOVERY_REVIEW"),
                "SYNTHETIC_OWNER_HELLO_INVALID")
        session = BoundDisposableSession(
            proc, pidfd, folder, hello["sessionId"], hello["epoch"],
            hello["phase"])
        session._buffer = reader._buffer
        row = durable_row(folder)
        require(row["writer"] == "m11w-" + session.session
                and row["epoch"] == session.epoch
                and row["phase"] == session.phase,
                "SYNTHETIC_OWNER_NOT_DURABLY_BOUND")
        return session
    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate(timeout=2)
        if pidfd >= 0:
            os.close(pidfd)
        raise SyntheticOwnerRefusal("SYNTHETIC_ATTACH_REFUSED") from None
    finally:
        for fd in (code_fd,owner_fd):
            if fd >= 0:
                os.close(fd)
