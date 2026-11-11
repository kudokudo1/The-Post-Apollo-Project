#!/usr/bin/env python3
"""Clock BG1-A: synthetic owner-fencing and durable occurrence-claim foundation.

The live Quickshell alarm manager DOES NOT call this module yet. No process
may interpret a successful lease or reservation as permission to ring, notify,
write the alarm document, or take over the running Clock owner. The one-shot
CLI supports read-only inspection only.

All lease/claim writes use an exclusive cross-process flock. Owner epochs
fence stale clients, and occurrence reservations are never automatically
recycled: crash after reservation may miss an alarm, but must not double-ring.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import tempfile
import time

SCHEMA = 1
MAX_STATE_BYTES = 1024 * 1024
MAX_CLAIMS = 2048
MAX_ALARM_BYTES = 2 * 1024 * 1024
MAX_LEASE_MS = 10000
ROLES = ("quickshell", "background")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")


class Refused(Exception):
    """Expected fail-closed result with stable diagnostic code."""


def _nonnegative(value, max_value=8640000000000000):
    return type(value) is int and 0 <= value <= max_value


def _boot_id():
    try:
        value = BOOT_ID.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise Refused("BOOT_ID_UNAVAILABLE") from exc
    if not re.fullmatch(r"[0-9a-f-]{36}", value):
        raise Refused("INVALID_BOOT_ID")
    return value


def _self_start_ticks():
    # /proc/<pid>/stat starttime is field 22. The second ')' ends comm,
    # whose contents can include spaces or ')'. Field 3 is suffix token 0.
    try:
        statline = Path("/proc/self/stat").read_text(encoding="ascii")
        start = int(statline.rsplit(") ", 1)[1].split()[19])
        if start < 1:
            raise ValueError()
        return start
    except (OSError, ValueError, IndexError) as exc:
        raise Refused("PROCESS_IDENTITY_UNAVAILABLE") from exc


def _owner_process_alive(lease):
    try:
        pid = lease["pid"]
        line = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        suffix = line.rsplit(") ", 1)[1].split()
        start = int(suffix[19])
        state = suffix[0]
        return start == lease["startTicks"] and state not in ("Z", "X", "x")
    except (OSError, ValueError, IndexError, KeyError, TypeError):
        return False


def _scope_for(alarm_file):
    path = Path(alarm_file)
    if not path.is_absolute() or path.name != "time-alarms-v2.json":
        raise Refused("EXACT_ALARM_FILE_REQUIRED")
    if path.is_symlink():
        raise Refused("UNSAFE_ALARM_LINK")
    parent = path.parent
    try:
        root_stat = parent.stat()
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                     | getattr(os, "O_CLOEXEC", 0))
        try:
            st = os.fstat(fd)
            if (not stat.S_ISDIR(root_stat.st_mode)
                    or root_stat.st_uid != os.getuid()
                    or not stat.S_ISREG(st.st_mode)
                    or st.st_uid != os.getuid()
                    or not 0 < st.st_size <= MAX_ALARM_BYTES):
                raise Refused("UNSAFE_ALARM_RECORD")
            with os.fdopen(fd, "rb", closefd=False) as inp:
                data = inp.read(MAX_ALARM_BYTES + 1)
            if len(data) > MAX_ALARM_BYTES:
                raise Refused("ALARM_RECORD_TOO_LARGE")
        finally:
            os.close(fd)
    except FileNotFoundError as exc:
        raise Refused("ALARM_RECORD_MISSING") from exc
    except OSError as exc:
        raise Refused("ALARM_RECORD_UNREADABLE") from exc
    try:
        doc = json.loads(data)
    except (UnicodeError, ValueError) as exc:
        raise Refused("ALARM_RECORD_INVALID") from exc
    if (not isinstance(doc, dict) or doc.get("version") != 2
            or not isinstance(doc.get("alarms"), list)
            or len(doc["alarms"]) > 100):
        raise Refused("ALARM_RECORD_INVALID")
    # Pin the parent path, not the file inode: Quickshell FileView uses
    # atomic replacement and legitimately changes the saved file inode.
    absolute = str(parent.resolve(strict=True) / path.name)
    return hashlib.sha256(
        (str(os.getuid()) + "\n" + absolute).encode("utf-8")
    ).hexdigest()


def _state_directory(path, create):
    root = Path(path)
    if not root.is_absolute() or root.is_symlink():
        raise Refused("INVALID_GATE_DIRECTORY")
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        st = root.stat()
    except FileNotFoundError as exc:
        raise Refused("GATE_NOT_INITIALIZED") from exc
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or (st.st_mode & 0o077)):
        raise Refused("UNSAFE_GATE_DIRECTORY")
    return root


def _empty_state(scope):
    return {"version": SCHEMA, "scope": scope, "epoch": 0,
            "lease": None, "claims": {}}


def _read_state(root, scope):
    p = root / "gate-v1.json"
    if not p.exists():
        return _empty_state(scope)
    if p.is_symlink():
        raise Refused("UNSAFE_GATE_STATE")
    try:
        st = p.stat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid()
                or not 0 < st.st_size <= MAX_STATE_BYTES):
            raise Refused("UNSAFE_GATE_STATE")
        raw = p.read_bytes()
        data = json.loads(raw)
    except (OSError, UnicodeError, ValueError) as exc:
        raise Refused("INVALID_GATE_STATE") from exc
    if (not isinstance(data, dict)
            or set(data) != {"version", "scope", "epoch", "lease", "claims"}
            or data["version"] != SCHEMA or data["scope"] != scope
            or not _nonnegative(data["epoch"], 2147483647)
            or not isinstance(data["claims"], dict)
            or len(data["claims"]) > MAX_CLAIMS):
        raise Refused("INVALID_GATE_STATE")
    lease = data["lease"]
    if lease is not None:
        if (not isinstance(lease, dict)
                or set(lease) != {"role", "pid", "startTicks", "bootId",
                                  "untilMonoMs", "tokenDigest", "epoch"}
                or lease["role"] not in ROLES
                or not _nonnegative(lease["pid"], 2147483647)
                or not _nonnegative(lease["startTicks"])
                or not _nonnegative(lease["untilMonoMs"])
                or not isinstance(lease["bootId"], str)
                or not isinstance(lease["tokenDigest"], str)
                or not DIGEST.fullmatch(lease["tokenDigest"])
                or lease["epoch"] != data["epoch"]):
            raise Refused("INVALID_GATE_STATE")
    for key, claim in data["claims"].items():
        if (not isinstance(key, str) or not DIGEST.fullmatch(key)
                or not isinstance(claim, dict)
                or set(claim) != {"alarmId", "expectedDueMs",
                                  "scheduleDigest", "ownerEpoch", "status"}
                or not _nonnegative(claim["alarmId"], 2147483647)
                or not _nonnegative(claim["expectedDueMs"])
                or not isinstance(claim["scheduleDigest"], str)
                or not DIGEST.fullmatch(claim["scheduleDigest"])
                or not _nonnegative(claim["ownerEpoch"], 2147483647)
                or claim["status"] != "RESERVED_ONLY"):
            raise Refused("INVALID_GATE_STATE")
    return data


def _write_state(root, data):
    target = root / "gate-v1.json"
    if target.is_symlink():
        raise Refused("UNSAFE_GATE_STATE")
    fd, temporary = tempfile.mkstemp(dir=root, prefix=".gate-v1-", suffix=".tmp")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.stat(temporary).st_size > MAX_STATE_BYTES:
            raise Refused("GATE_STATE_TOO_LARGE")
        os.replace(temporary, target)
        parent_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _locked(root, create=False):
    path = root / "gate.lock"
    flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    if create:
        flags |= os.O_CREAT
    try:
        fd = os.open(path, flags, 0o600)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
            raise Refused("UNSAFE_GATE_LOCK")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        if "fd" in locals():
            os.close(fd)


class OwnershipGate:
    """CI-use foundation; deliberately not connected to live sound/UI."""

    def __init__(self, alarm_file, state_dir):
        self.alarm_file = str(alarm_file)
        self.state_dir = str(state_dir)

    def _snapshot(self, create=False):
        return (_scope_for(self.alarm_file),
                _state_directory(self.state_dir, create))

    @staticmethod
    def _valid_lease(lease):
        return bool(
            lease
            and lease["bootId"] == _boot_id()
            and lease["untilMonoMs"] > time.monotonic_ns() // 1000000
            and _owner_process_alive(lease)
        )

    @staticmethod
    def _authorized(data, role, token):
        lease = data["lease"]
        if (not OwnershipGate._valid_lease(lease)
                or role != lease["role"]
                or type(token) is not str
                or hashlib.sha256(token.encode("utf-8")).hexdigest()
                    != lease["tokenDigest"]
                or lease["pid"] != os.getpid()
                or lease["startTicks"] != _self_start_ticks()):
            raise Refused("STALE_OR_FOREIGN_OWNER")
        return lease

    def inspect(self):
        scope, root = self._snapshot(create=False)
        with _locked(root):
            doc = _read_state(root, scope)
            lease = doc["lease"]
            return {"mode": "PRE_ACTUATION", "actuationEnabled": False,
                    "ownerValid": self._valid_lease(lease),
                    "ownerRole": lease["role"] if self._valid_lease(lease) else "none",
                    "epoch": doc["epoch"], "claimCount": len(doc["claims"]),
                    "ownsAlarmFile": False}

    def acquire(self, role, ttl_ms=5000):
        if role not in ROLES or not _nonnegative(ttl_ms, MAX_LEASE_MS) or ttl_ms < 100:
            raise Refused("INVALID_OWNER_REQUEST")
        scope, root = self._snapshot(create=True)
        with _locked(root, create=True):
            doc = _read_state(root, scope)
            if self._valid_lease(doc["lease"]):
                raise Refused("OWNER_ALREADY_ACTIVE")
            if doc["epoch"] >= 2147483647:
                raise Refused("OWNER_EPOCH_EXHAUSTED")
            token = secrets.token_hex(32)
            epoch = doc["epoch"] + 1
            doc["epoch"] = epoch
            doc["lease"] = {"role": role, "pid": os.getpid(),
                            "startTicks": _self_start_ticks(),
                            "bootId": _boot_id(),
                            "untilMonoMs": time.monotonic_ns() // 1000000 + ttl_ms,
                            "tokenDigest": hashlib.sha256(token.encode()).hexdigest(),
                            "epoch": epoch}
            _write_state(root, doc)
            return {"role": role, "token": token, "epoch": epoch,
                    "actuationEnabled": False, "ownsAlarmFile": False}

    def renew(self, role, token, ttl_ms=5000):
        if not _nonnegative(ttl_ms, MAX_LEASE_MS) or ttl_ms < 100:
            raise Refused("INVALID_RENEWAL")
        scope, root = self._snapshot()
        with _locked(root):
            doc = _read_state(root, scope)
            lease = self._authorized(doc, role, token)
            lease["untilMonoMs"] = time.monotonic_ns() // 1000000 + ttl_ms
            _write_state(root, doc)
            return {"epoch": doc["epoch"], "actuationEnabled": False}

    def release(self, role, token):
        scope, root = self._snapshot()
        with _locked(root):
            doc = _read_state(root, scope)
            self._authorized(doc, role, token)
            doc["lease"] = None
            _write_state(root, doc)
            return {"released": True, "actuationEnabled": False}

    def reserve(self, role, token, alarm_id, expected_due_ms, schedule_digest):
        if (not _nonnegative(alarm_id, 2147483647) or alarm_id == 0
                or not _nonnegative(expected_due_ms) or expected_due_ms == 0
                or not isinstance(schedule_digest, str)
                or not DIGEST.fullmatch(schedule_digest)):
            raise Refused("INVALID_OCCURRENCE")
        scope, root = self._snapshot()
        with _locked(root):
            doc = _read_state(root, scope)
            lease = self._authorized(doc, role, token)
            # No inferred schedule from this receipt. The future BG1-B
            # reader must independently validate expectedDueMs against the
            # exact saved alarm revision and current schedule.
            raw = f"{alarm_id}|{expected_due_ms}|{schedule_digest}".encode("ascii")
            occurrence_key = hashlib.sha256(raw).hexdigest()
            if occurrence_key in doc["claims"]:
                raise Refused("OCCURRENCE_ALREADY_RESERVED")
            if len(doc["claims"]) >= MAX_CLAIMS:
                raise Refused("CLAIM_LEDGER_FULL")
            doc["claims"][occurrence_key] = {
                "alarmId": alarm_id, "expectedDueMs": expected_due_ms,
                "scheduleDigest": schedule_digest,
                "ownerEpoch": lease["epoch"], "status": "RESERVED_ONLY"}
            _write_state(root, doc)
            return {"claim": occurrence_key, "ownerEpoch": lease["epoch"],
                    "status": "RESERVED_ONLY", "actuationEnabled": False,
                    "ownsAlarmFile": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true", required=True)
    parser.add_argument("--alarm-file", required=True)
    parser.add_argument("--state-dir", required=True)
    args = parser.parse_args()
    try:
        answer = OwnershipGate(args.alarm_file, args.state_dir).inspect()
    except (Refused, OSError) as exc:
        answer = {"mode": "PRE_ACTUATION", "actuationEnabled": False,
                  "ownsAlarmFile": False, "state": "REFUSED",
                  "reason": str(exc) if isinstance(exc, Refused) else "IO_ERROR"}
    print(json.dumps(answer, separators=(",", ":"), sort_keys=True))
    return 0 if answer.get("state") != "REFUSED" else 2


if __name__ == "__main__":
    sys.exit(main())
