#!/usr/bin/env python3
"""Clock BG1-B1: synthetic peer-bound, non-actuating Unix socket broker.

This is NOT the production alarm owner. The live Quickshell manager and B0
observer do not connect to it. CLI has --serve-synthetic ONLY; never sound,
send a notification, write alarms or authorize playback from this broker.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import stat
import struct
import sys
import threading
import time

# Explicit source-tree sibling loading works even with python -I; do not
# search the user working directory for lookalike modules.
def _sibling(name):
    target = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location(name, target)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing bundled Clock component: " + name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_gate_module = _sibling("AlarmOwnershipGate")
_observer_module = _sibling("AlarmBackgroundObserver")
_shadow_module = _sibling("AlarmShadowTransactions")
ShadowStore = _shadow_module.ShadowStore
ShadowRefused = _shadow_module.Refused
OwnershipGate = _gate_module.OwnershipGate
Refused = _gate_module.Refused
evaluate_alarm = _observer_module.evaluate_alarm
validate_snapshot = _observer_module.validate_snapshot
ObserverRefused = _observer_module.Refused

MAX_FRAME = 8192
MAX_ALARMS_BYTES = 2 * 1024 * 1024
DIGEST = re.compile(r"^[0-9a-f]{64}$")
PREFIX = {"mode": "SYNTHETIC_BG1_B", "actuationEnabled": False,
          "ownsAlarmFile": False}


def _integer(value, minimum=0, maximum=8640000000000000):
    return type(value) is int and minimum <= value <= maximum


def _peer_start_ticks(pid):
    try:
        record = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        fields = record.rsplit(") ", 1)[1].split()
        if fields[0] in ("Z", "X", "x"):
            raise ValueError("exited")
        value = int(fields[19])
        if value <= 0:
            raise ValueError("invalid start")
        return value
    except (OSError, ValueError, IndexError) as exc:
        raise Refused("PEER_PROCESS_UNVERIFIED") from exc


def _peer_process(connection, expected_exe):
    if not hasattr(socket, "SO_PEERCRED"):
        raise Refused("SO_PEERCRED_UNAVAILABLE")
    try:
        raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, uid, _gid = struct.unpack("3i", raw)
        if pid <= 1 or uid != os.getuid():
            raise Refused("PEER_UID_REFUSED")
        exe = os.path.realpath(os.readlink(f"/proc/{pid}/exe"))
        if exe != expected_exe:
            raise Refused("UNEXPECTED_SYNTHETIC_PEER_EXE")
        return {"pid": pid, "uid": uid, "ticks": _peer_start_ticks(pid)}
    except OSError as exc:
        raise Refused("PEER_PROCESS_UNVERIFIED") from exc


def _source_snapshot(alarm_file, now_ms):
    # The saved file is read once via a no-follow file descriptor, bounded
    # and checked for same-UID ownership before parsing. No sidecar writes.
    target = Path(alarm_file)
    if not target.is_absolute() or target.name != "time-alarms-v2.json":
        raise Refused("EXACT_ALARM_FILE_REQUIRED")
    fd = None
    try:
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or not 0 < info.st_size <= MAX_ALARMS_BYTES):
            raise Refused("UNSAFE_ALARM_FILE")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_ALARMS_BYTES + 1)
        if len(raw) > MAX_ALARMS_BYTES:
            raise Refused("ALARM_FILE_TOO_LARGE")
    except (OSError, PermissionError) as exc:
        raise Refused("ALARM_FILE_UNREADABLE") from exc
    finally:
        if fd is not None:
            os.close(fd)
    try:
        doc = json.loads(raw)
        validate_snapshot(doc)
    except (ValueError, UnicodeError, KeyError, TypeError, Refused, ObserverRefused) as exc:
        raise Refused("INVALID_ALARM_DOCUMENT") from exc
    # Snapshot hash is a PRE-ACTUATION witness only. It does not make
    # Quickshell's current FileView write transactional with this broker.
    return hashlib.sha256(raw).hexdigest(), doc, [
        evaluate_alarm(row, now_ms) for row in doc["alarms"]
    ]


def _schedule_digest(row):
    # Source digest changes on notes/volume edits; a scheduled occurrence
    # must not become reservable again just because unrelated data changed.
    fields = ("id", "mode", "hour", "minute", "date",
              "weekdays", "armedAtMs", "snoozeUntilMs")
    stable = {key: row.get(key) for key in fields}
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _private_socket_path(path):
    target = Path(path)
    if not target.is_absolute() or target.name != "bg1-synthetic.sock":
        raise Refused("EXPLICIT_SYNTHETIC_SOCKET_REQUIRED")
    parent = target.parent
    if parent.is_symlink():
        raise Refused("SYMLINK_SOCKET_DIR")
    try:
        info = parent.stat()
    except OSError as exc:
        raise Refused("SOCKET_DIR_UNAVAILABLE") from exc
    if (not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise Refused("UNSAFE_SOCKET_DIR")
    if len(os.fsencode(target)) >= 100:
        raise Refused("SOCKET_PATH_TOO_LONG")
    if target.exists() or target.is_symlink():
        raise Refused("SOCKET_ALREADY_EXISTS")
    return str(target)


class BrokerServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, path, alarm_file, state_dir, test_now_ms):
        self.alarm_file = alarm_file
        self.gate = OwnershipGate(alarm_file, state_dir)
        self.shadow = ShadowStore(state_dir, alarm_file)
        self.test_now_ms = test_now_ms
        # Only a same-UID Python synthetic test client qualifies for this
        # source-only prototype. Not proof of Quickshell binary identity.
        self.synthetic_exe = os.path.realpath(sys.executable)
        self.state_guard = threading.Lock()
        self.active_owner = None
        super().__init__(_private_socket_path(path), BrokerHandler)
        os.chmod(path, 0o600)

    def now_ms(self):
        return self.test_now_ms or int(time.time() * 1000)


class BrokerHandler(socketserver.StreamRequestHandler):
    def setup(self):
        super().setup()
        self.peer = None
        self.role = None
        self.token = None
        self.epoch = None
        self.request.settimeout(5)

    def _reply(self, result):
        payload = dict(PREFIX)
        payload.update(result)
        self.wfile.write(
            (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode()
        )
        self.wfile.flush()

    def _peer_ok(self):
        if self.peer is None:
            self.peer = _peer_process(self.request, self.server.synthetic_exe)
        if _peer_start_ticks(self.peer["pid"]) != self.peer["ticks"]:
            raise Refused("PEER_PROCESS_CHANGED")
        return self.peer

    def _require_owner(self):
        if not self.token or self.role not in ("quickshell", "background"):
            raise Refused("NO_LIVE_OWNER_SESSION")
        if self.server.active_owner is not self:
            raise Refused("OTHER_OWNER_SESSION_ACTIVE")

    def process(self, message):
        if not isinstance(message, dict):
            raise Refused("INVALID_REQUEST")
        op = message.get("op")
        shapes = {
            "hello": {"op", "role"},
            "snapshot": {"op"},
            "acquire": {"op"},
            "renew": {"op"},
            "release": {"op"},
            "reserve": {"op", "alarmId", "expectedDueMs", "sourceDigest"},
            "shadow_begin": {"op", "sourceDigest"},
            "shadow_view": {"op"},
            "shadow_tick": {"op", "revision", "alarmId", "expectedDueMs"},
            "shadow_stop": {"op", "revision", "alarmId", "ringStartedMs"},
            "shadow_snooze": {"op", "revision", "alarmId", "ringStartedMs"},
            "shadow_edit": {"op", "revision", "alarmId", "patch"},
        }
        if op not in shapes or set(message) != shapes[op]:
            raise Refused("INVALID_REQUEST_FIELDS")
        self._peer_ok()
        if op == "hello":
            if self.role is not None:
                raise Refused("SESSION_ALREADY_ATTACHED")
            if message["role"] not in ("quickshell", "background"):
                raise Refused("UNKNOWN_SYNTHETIC_ROLE")
            self.role = message["role"]
            return {"ok": True, "role": self.role,
                    "peerPid": self.peer["pid"], "testOnly": True}
        if self.role is None:
            raise Refused("HELLO_REQUIRED")
        if op == "snapshot":
            digest, _doc, phases = _source_snapshot(
                self.server.alarm_file, self.server.now_ms())
            return {"ok": True, "sourceDigest": digest, "phases": phases}
        if op == "acquire":
            if self.token:
                raise Refused("SESSION_ALREADY_OWNER")
            with self.server.state_guard:
                if self.server.active_owner is not None:
                    raise Refused("OWNER_ALREADY_ACTIVE")
                lease = self.server.gate.acquire(self.role, ttl_ms=5000)
                self.server.active_owner = self
                self.token, self.epoch = lease["token"], lease["epoch"]
            return {"ok": True, "epoch": self.epoch, "reservedOnly": True}
        if op.startswith("shadow_"):
            with self.server.state_guard:
                self._require_owner()
                # Every shadow action is forced through the current broker
                # lease, including after an owner disconnect or timeout.
                self.server.gate.renew(self.role, self.token, ttl_ms=5000)
                if op == "shadow_begin":
                    witnessed, doc, _ = _source_snapshot(
                        self.server.alarm_file, self.server.now_ms())
                    if type(message["sourceDigest"]) is not str or message["sourceDigest"] != witnessed:
                        raise Refused("STALE_ALARM_FILE_REVISION")
                    result = self.server.shadow.initialize(
                        doc, witnessed, self.epoch, validate_snapshot)
                    return dict({"ok": True, "shadowOnly": True}, **result)
                if op == "shadow_view":
                    return dict({"ok": True, "shadowOnly": True},
                                **self.server.shadow.view())
                return dict({"ok": True, "shadowOnly": True},
                    **self.server.shadow.transition(
                        self.epoch, message["revision"],
                        op.removeprefix("shadow_"),
                        message["alarmId"], self.server.now_ms(),
                        expected_due_ms=message.get("expectedDueMs", 0),
                        ring_started_ms=message.get("ringStartedMs", 0),
                        patch=message.get("patch"),
                        evaluate=evaluate_alarm, validate=validate_snapshot))
        if op in ("renew", "release", "reserve"):
            with self.server.state_guard:
                self._require_owner()
                if op == "renew":
                    result = self.server.gate.renew(self.role, self.token, ttl_ms=5000)
                    return {"ok": True, "epoch": result["epoch"]}
                if op == "release":
                    self.server.gate.release(self.role, self.token)
                    self.server.active_owner = None
                    self.token = None
                    return {"ok": True, "released": True}
                alarm_id = message["alarmId"]
                due = message["expectedDueMs"]
                digest = message["sourceDigest"]
                if (not _integer(alarm_id, 1, 2147483647)
                        or not _integer(due, 1)
                        or type(digest) is not str or not DIGEST.fullmatch(digest)):
                    raise Refused("INVALID_OCCURRENCE_REQUEST")
                source_digest, doc, phases = _source_snapshot(
                    self.server.alarm_file, self.server.now_ms())
                if digest != source_digest:
                    raise Refused("STALE_ALARM_FILE_REVISION")
                candidates = [p for p in phases if p["alarmId"] == alarm_id]
                if len(candidates) != 1:
                    raise Refused("ALARM_NOT_IN_SOURCE")
                candidate = candidates[0]
                if (candidate["phase"] not in (
                        "ELIGIBLE_IF_OWNED", "SNOOZE_ELIGIBLE_IF_OWNED")
                        or candidate["dueAtMs"] != due):
                    raise Refused("OCCURRENCE_NOT_ELIGIBLE")
                row = next(a for a in doc["alarms"] if a["id"] == alarm_id)
                claim = self.server.gate.reserve(
                    self.role, self.token, alarm_id, due, _schedule_digest(row))
                # Never claim success if a concurrent Quickshell save changed
                # the saved source while the synthetic reservation was made.
                after_digest, _, _ = _source_snapshot(
                    self.server.alarm_file, self.server.now_ms())
                if after_digest != digest:
                    raise Refused("SOURCE_CHANGED_DURING_RESERVATION")
                return {"ok": True, "claim": claim["claim"],
                        "ownerEpoch": claim["ownerEpoch"],
                        "status": "RESERVED_ONLY"}
        raise Refused("UNKNOWN_REQUEST")

    def handle(self):
        try:
            self._peer_ok()
            while True:
                data = self.rfile.readline(MAX_FRAME + 1)
                if not data:
                    return
                if len(data) > MAX_FRAME or not data.endswith(b"\n"):
                    self._reply({"ok": False, "reason": "FRAME_TOO_LARGE_OR_INCOMPLETE"})
                    return
                try:
                    message = json.loads(data)
                    result = self.process(message)
                except (UnicodeError, ValueError, TypeError, Refused, ShadowRefused, OSError) as exc:
                    reason = (str(exc) if isinstance(exc, (Refused, ShadowRefused))
                              else "INVALID_REQUEST")
                    result = {"ok": False, "reason": reason}
                self._reply(result)
        except (Refused, OSError, TimeoutError):
            return
        finally:
            if self.token:
                with self.server.state_guard:
                    if self.server.active_owner is self:
                        try:
                            self.server.gate.release(self.role, self.token)
                        except (Refused, OSError):
                            # A stale lease or lost disk still fails closed;
                            # acquisition checks the saved epoch/dead PID.
                            pass
                        self.server.active_owner = None
                        self.token = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve-synthetic", action="store_true", required=True)
    parser.add_argument("--alarm-file", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--synthetic-now-ms", type=int, default=0)
    args = parser.parse_args()
    if not _integer(args.synthetic_now_ms):
        parser.error("synthetic time must be an integer timestamp")
    server = None
    bound_path = None
    bound_inode = None
    try:
        # Validate the precise saved file even before binding the socket.
        _source_snapshot(args.alarm_file, args.synthetic_now_ms or int(time.time() * 1000))
        server = BrokerServer(args.socket, args.alarm_file, args.state_dir,
                              args.synthetic_now_ms)
        bound_path = Path(args.socket)
        bound_inode = bound_path.stat().st_ino
        server.serve_forever(poll_interval=0.2)
        return 0
    except (Refused, OSError, ValueError) as exc:
        result = dict(PREFIX, state="REFUSED",
                      reason=str(exc) if isinstance(exc, Refused) else "BROKER_START_FAILED")
        print(json.dumps(result, separators=(",", ":")), flush=True)
        return 2
    except KeyboardInterrupt:
        return 0
    finally:
        if server is not None:
            server.server_close()
        # Never unlink a socket path another process has replaced.
        if bound_path is not None:
            try:
                st = bound_path.lstat()
                if stat.S_ISSOCK(st.st_mode) and st.st_ino == bound_inode:
                    bound_path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    sys.exit(main())
