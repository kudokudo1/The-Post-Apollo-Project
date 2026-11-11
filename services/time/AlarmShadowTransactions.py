#!/usr/bin/env python3
"""Clock BG1-B2A: synthetic atomic alarm-state + occurrence-receipt store.

Never writes Quickshell's time-alarms-v2.json. Never rings or notifies.
All operations are deliberately restricted to a broker-held synthetic owner.
A real migration must replace Quickshell's FileView writer transactionally.
"""
from __future__ import annotations
import copy
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

VERSION = 1
MAX_BYTES = 2 * 1024 * 1024
MAX_RECEIPTS = 2048
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
SNOOZE_MS = 5 * 60 * 1000
MAX_NAME = 40
MAX_NOTE = 256
ALLOWED_EDITS = {"name", "note", "enabled", "hour", "minute", "weekdays",
                 "mode", "date", "soundId", "soundEnabled", "volumePercent"}


class Refused(Exception):
    pass


def integer(n, lowest=0, highest=8640000000000000):
    return type(n) is int and lowest <= n <= highest


def digest(data):
    return hashlib.sha256(data).hexdigest()


def schedule_hash(a):
    return digest(json.dumps({k: a.get(k) for k in (
        "id", "mode", "date", "weekdays", "hour", "minute",
        "armedAtMs", "snoozeUntilMs")},
        sort_keys=True, separators=(",", ":")).encode())


def receipt_key(a, due):
    return digest(f'{a["id"]}|{due}|{schedule_hash(a)}'.encode("ascii"))


def _require_directory(root):
    if not root.is_absolute() or root.is_symlink():
        raise Refused("UNSAFE_SHADOW_DIRECTORY")
    try:
        st = root.stat()
    except OSError as exc:
        raise Refused("SHADOW_DIRECTORY_NOT_INITIALIZED") from exc
    if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
            or st.st_mode & 0o077):
        raise Refused("UNSAFE_SHADOW_DIRECTORY")


def _validate(doc, scope):
    if (not isinstance(doc, dict)
            or set(doc) != {"version", "scope", "revision", "ownerEpoch",
                            "sourceDigest", "alarmDocument", "receipts"}
            or doc["version"] != VERSION or doc["scope"] != scope
            or not integer(doc["revision"], 0, 2147483647)
            or not integer(doc["ownerEpoch"], 0, 2147483647)
            or not isinstance(doc["sourceDigest"], str)
            or not HEX_DIGEST.fullmatch(doc["sourceDigest"])
            or not isinstance(doc["alarmDocument"], dict)
            or doc["alarmDocument"].get("version") != 2
            or not isinstance(doc["alarmDocument"].get("alarms"), list)
            or len(doc["alarmDocument"]["alarms"]) > 100
            or not isinstance(doc["receipts"], dict)
            or len(doc["receipts"]) > MAX_RECEIPTS):
        raise Refused("INVALID_SHADOW_STATE")
    for key, value in doc["receipts"].items():
        if (not isinstance(key, str) or not HEX_DIGEST.fullmatch(key)
                or not isinstance(value, dict)
                or set(value) != {"alarmId", "expectedDueMs",
                                  "ownerEpoch", "phase"}
                or not integer(value["alarmId"], 1)
                or not integer(value["expectedDueMs"], 1)
                or not integer(value["ownerEpoch"], 1, 2147483647)
                or value["phase"] not in ("ringing", "stopped", "snoozed")):
            raise Refused("INVALID_SHADOW_RECEIPT")
    return doc


class ShadowStore:
    """One shadow file is the atomic owner state AND occurrence ledger."""

    def __init__(self, state_dir, alarm_file):
        self.root = Path(state_dir)
        target = Path(alarm_file)
        if not target.is_absolute() or target.name != "time-alarms-v2.json":
            raise Refused("EXACT_ALARM_PATH_REQUIRED")
        self.scope = digest((str(os.getuid()) + "\n" +
                             str(target.parent.resolve(strict=True) / target.name)
                             ).encode())

    def _load_locked(self):
        path = self.root / "shadow-alarms-v1.json"
        if path.is_symlink():
            raise Refused("UNSAFE_SHADOW_FILE")
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                st = os.fstat(fd)
                if (not stat.S_ISREG(st.st_mode)
                        or st.st_uid != os.getuid()
                        or not 0 < st.st_size <= MAX_BYTES):
                    raise Refused("UNSAFE_SHADOW_FILE")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    contents = stream.read(MAX_BYTES + 1)
                if len(contents) > MAX_BYTES:
                    raise Refused("SHADOW_TOO_LARGE")
            finally:
                os.close(fd)
        except FileNotFoundError as exc:
            raise Refused("SHADOW_NOT_INITIALIZED") from exc
        try:
            return _validate(json.loads(contents), self.scope)
        except (ValueError, UnicodeError, TypeError) as exc:
            raise Refused("INVALID_SHADOW_STATE") from exc

    def _write_locked(self, document):
        target = self.root / "shadow-alarms-v1.json"
        if target.is_symlink():
            raise Refused("UNSAFE_SHADOW_FILE")
        raw = (json.dumps(document, separators=(",", ":"),
                          ensure_ascii=False, sort_keys=True) + "\n").encode()
        if len(raw) > MAX_BYTES:
            raise Refused("SHADOW_TOO_LARGE")
        fd, tmp = tempfile.mkstemp(prefix=".alarm-shadow-", dir=self.root)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, target)
            folder = os.open(self.root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(folder)
            finally:
                os.close(folder)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def _execute(self, callback):
        _require_directory(self.root)
        path = self.root / "shadow-transaction.lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
                raise Refused("UNSAFE_SHADOW_LOCK")
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            return callback()
        finally:
            os.close(fd)

    def initialize(self, original_doc, source_digest, epoch, validate_alarm):
        if (not integer(epoch, 1, 2147483647)
                or not isinstance(source_digest, str)
                or not HEX_DIGEST.fullmatch(source_digest)):
            raise Refused("INVALID_SHADOW_INIT")
        validate_alarm(original_doc)
        def init():
            target = self.root / "shadow-alarms-v1.json"
            if target.exists() or target.is_symlink():
                raise Refused("SHADOW_ALREADY_INITIALIZED")
            shadow = {"version": VERSION, "scope": self.scope,
                      "revision": 0, "ownerEpoch": epoch,
                      "sourceDigest": source_digest,
                      "alarmDocument": copy.deepcopy(original_doc),
                      "receipts": {}}
            self._write_locked(shadow)
            return {"revision": 0, "ownerEpoch": epoch}
        return self._execute(init)

    def view(self):
        def load():
            d = self._load_locked()
            # Do not expose private names, notes, or sound paths over IPC.
            return {"revision": d["revision"], "ownerEpoch": d["ownerEpoch"],
                    "sourceDigest": d["sourceDigest"],
                    "receiptCount": len(d["receipts"]), "alarmCount":
                    len(d["alarmDocument"]["alarms"])}
        return self._execute(load)

    def transition(self, epoch, expected_revision, action, alarm_id, now_ms,
                   *, expected_due_ms=0, ring_started_ms=0, patch=None,
                   evaluate, validate):
        if (not integer(epoch, 1, 2147483647)
                or not integer(expected_revision, 0, 2147483647)
                or not integer(alarm_id, 1, 2147483647)
                or not integer(now_ms, 1)
                or action not in ("tick", "stop", "snooze", "edit")):
            raise Refused("INVALID_SHADOW_TRANSITION")
        def apply():
            original = self._load_locked()
            if original["revision"] != expected_revision:
                raise Refused("SHADOW_REVISION_MISMATCH")
            if epoch < original["ownerEpoch"]:
                raise Refused("STALE_OWNER_EPOCH")
            document = copy.deepcopy(original)
            alarms = document["alarmDocument"]["alarms"]
            selected = [a for a in alarms if a.get("id") == alarm_id]
            if len(selected) != 1:
                raise Refused("ALARM_NOT_FOUND")
            a = selected[0]
            prior_due = a.get("lastExpectedAtMs", 0)
            prior_key = a.get("lastOccurrenceKey", "")
            if action == "tick":
                phase = evaluate(a, now_ms)
                if (not integer(expected_due_ms, 1)
                        or phase.get("phase") not in ("ELIGIBLE_IF_OWNED",
                                                     "SNOOZE_ELIGIBLE_IF_OWNED")
                        or phase.get("dueAtMs") != expected_due_ms):
                    raise Refused("ALARM_NOT_DUE")
                key = receipt_key(a, expected_due_ms)
                if key in document["receipts"]:
                    raise Refused("OCCURRENCE_ALREADY_RECORDED")
                if len(document["receipts"]) >= MAX_RECEIPTS:
                    raise Refused("SHADOW_RECEIPTS_FULL")
                a["ringing"] = True
                a["ringStartedAtMs"] = now_ms
                a["snoozeUntilMs"] = 0
                a["lastProcessedDueMs"] = expected_due_ms
                a["lastExpectedAtMs"] = expected_due_ms
                a["lastEventAtMs"] = now_ms
                a["lastEventKind"] = "fired"
                a["lastFiredAtMs"] = now_ms
                a["lastFiredDay"] = datetime.fromtimestamp(
                    expected_due_ms / 1000).date().isoformat()
                a["lastOccurrenceKey"] = key
                document["receipts"][key] = {
                    "alarmId": alarm_id, "expectedDueMs": expected_due_ms,
                    "ownerEpoch": epoch, "phase": "ringing"}
            elif action in ("stop", "snooze"):
                if (not integer(ring_started_ms, 1)
                        or not a.get("ringing")
                        or a.get("ringStartedAtMs") != ring_started_ms):
                    raise Refused("STALE_RING_ACTION")
                key = prior_key
                if (not isinstance(key, str) or key not in document["receipts"]
                        or document["receipts"][key]["phase"] != "ringing"
                        or document["receipts"][key]["alarmId"] != alarm_id
                        or document["receipts"][key]["expectedDueMs"] != prior_due):
                    raise Refused("NO_MATCHING_OCCURRENCE_RECEIPT")
                a["ringing"] = False
                a["ringStartedAtMs"] = 0
                a["snoozeUntilMs"] = now_ms + SNOOZE_MS if action == "snooze" else 0
                a["lastEventKind"] = "snoozed" if action == "snooze" else "stopped"
                a["lastEventAtMs"] = now_ms
                document["receipts"][key]["phase"] = a["lastEventKind"]
            else:
                if (not isinstance(patch, dict) or not patch
                        or not set(patch).issubset(ALLOWED_EDITS)):
                    raise Refused("INVALID_SHADOW_EDIT")
                for field, value in patch.items():
                    if field in ("name", "note"):
                        limit = MAX_NAME if field == "name" else MAX_NOTE
                        if (not isinstance(value, str) or len(value) > limit
                                or (field == "name" and not value.strip())
                                or any(ord(c) < 32 or ord(c) == 127 for c in value)):
                            raise Refused("INVALID_SHADOW_EDIT")
                    elif field in ("enabled", "soundEnabled"):
                        if type(value) is not bool:
                            raise Refused("INVALID_SHADOW_EDIT")
                    elif field in ("hour", "minute", "volumePercent"):
                        limit = 23 if field == "hour" else 59 if field == "minute" else 100
                        if not integer(value, 0, limit):
                            raise Refused("INVALID_SHADOW_EDIT")
                    elif field == "weekdays":
                        if (not isinstance(value, list) or
                                not 0 < len(value) <= 7 or
                                any(not integer(x, 0, 6) for x in value)
                                or len(set(value)) != len(value)):
                            raise Refused("INVALID_SHADOW_EDIT")
                    elif field == "mode":
                        if value not in ("weekly", "once"):
                            raise Refused("INVALID_SHADOW_EDIT")
                    elif field == "date":
                        if type(value) is not str or len(value) > 10:
                            raise Refused("INVALID_SHADOW_EDIT")
                    elif field == "soundId":
                        if (type(value) is not str or
                                not (value in ("chime", "soft", "urgent")
                                     or (len(value) == 69 and
                                         value.startswith("user-") and
                                         all(c in "0123456789abcdef" for c in value[5:])))):
                            raise Refused("INVALID_SHADOW_EDIT")
                changed_schedule = any(k in patch for k in (
                    "hour", "minute", "weekdays", "date", "mode", "enabled"))
                for field, value in patch.items():
                    a[field] = value
                if changed_schedule:
                    a["armedAtMs"] = now_ms
                    a["lastProcessedDueMs"] = 0
                    a["lastFiredDay"] = ""
                    a["lastOccurrenceKey"] = ""
                    a["lastExpectedAtMs"] = 0
                    a["ringing"] = False
                    a["ringStartedAtMs"] = 0
                    a["snoozeUntilMs"] = 0
                    a["completed"] = False
                validate(document["alarmDocument"])
            document["ownerEpoch"] = epoch
            document["revision"] += 1
            # Both live state and receipt in ONE atomic shadow JSON replace.
            self._write_locked(document)
            return {"revision": document["revision"], "ownerEpoch": epoch,
                    "status": action.upper() + "_SHADOW_ONLY",
                    "receiptCount": len(document["receipts"]),
                    "alarmId": alarm_id, "actuationEnabled": False,
                    "realAlarmFileModified": False}
        return self._execute(apply)
