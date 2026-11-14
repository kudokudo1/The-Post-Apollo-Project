#!/usr/bin/env python3
"""BG1-B2B3: disposable canonical alarm handoff rehearsal; never production.

One SQLite row atomically stores a proposed V2 alarm document AND occurrence
receipts. A synthetic old-writer release must precede a candidate new epoch.
Every operation compares the original exact V2 source bytes and expected
revision, but this does NOT coordinate the live Quickshell FileView writer.

The source JSON is NEVER written by this module. No sound, notifications,
systemd, app activation, or permissions to operate on a real Clock process.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
from datetime import datetime


def _sibling(name):
    path = Path(__file__).resolve().with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("bg1_b2b3_" + name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing bundled BG1 component: " + name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


Observer = _sibling("AlarmBackgroundObserver")
Shadow = _sibling("AlarmShadowTransactions")
MAX_SOURCE = 2 * 1024 * 1024
MAX_ROW = 3 * 1024 * 1024
MAX_RECEIPTS = 2048
HEX = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
DOMAIN = b"postapollo.clock.bg1-b2b3.synthetic-old-writer-release.v1\x00"
SCHEMA = 1


class Refused(ValueError):
    """Stable, non-private rejection code."""


def integer(n, lo=0, hi=2147483647):
    return type(n) is int and lo <= n <= hi


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def synthetic_release_proof(secret, scope, source_digest, old_epoch, challenge):
    """Test fixture helper, NOT a way to obtain real Quickshell release."""
    if (type(secret) is not bytes or len(secret) != 32
            or type(scope) is not str or not HEX.fullmatch(scope)
            or type(source_digest) is not str
            or not HEX.fullmatch(source_digest)
            or not integer(old_epoch, 1)
            or type(challenge) is not str
            or not HEX.fullmatch(challenge)):
        raise Refused("INVALID_SYNTHETIC_RELEASE_INPUT")
    message = (scope + "|" + source_digest + "|" + str(old_epoch)
               + "|" + challenge).encode("ascii")
    return hmac.new(secret, DOMAIN + message, hashlib.sha256).hexdigest()


class CanonicalHandoffFixture:
    """Two-phase, cross-process transaction model for disposable CI only."""

    def __init__(self, root, source_file, *, old_writer_test_secret,
                 synthetic_only=False):
        self.root = Path(root)
        self.source = Path(source_file)
        if (synthetic_only is not True
                or self.root.name != "bg1-canonical-fixture"
                or self.source.name != "time-alarms-v2.json"
                or self.source.parent.name != "synthetic-quickshell"
                or self.root.parent != self.source.parent.parent
                or not self.root.is_absolute()
                or not self.source.is_absolute()
                or type(old_writer_test_secret) is not bytes
                or len(old_writer_test_secret) != 32):
            raise Refused("DISPOSABLE_FIXTURE_REQUIRED")
        self.secret = old_writer_test_secret
        self.db = self.root / "alarm-canonical-fixture-v1.sqlite3"
        self.before_commit = None  # Test-only crash injection, never public IPC.
        self._private_root()
        self.scope = _digest((str(os.getuid()) + "\n"
                             + str(self.source.parent.resolve(strict=True)
                                   / self.source.name)).encode())

    def _private_root(self):
        for root in (self.root, self.source.parent):
            if root.is_symlink():
                raise Refused("UNSAFE_FIXTURE_DIRECTORY")
            try:
                st = root.stat()
            except OSError as exc:
                raise Refused("FIXTURE_DIRECTORY_MISSING") from exc
            if (not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid()
                    or stat.S_IMODE(st.st_mode) != 0o700):
                raise Refused("UNSAFE_FIXTURE_DIRECTORY")

    def _read_source(self):
        self._private_root()
        if self.source.is_symlink():
            raise Refused("SOURCE_LINK_REFUSED")
        fd = None
        try:
            fd = os.open(self.source, os.O_RDONLY | os.O_NOFOLLOW
                         | os.O_CLOEXEC)
            st = os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode)
                    or st.st_uid != os.getuid() or st.st_nlink != 1
                    or stat.S_IMODE(st.st_mode) != 0o600
                    or not 0 < st.st_size <= MAX_SOURCE):
                raise Refused("UNSAFE_SOURCE_RECORD")
            raw = os.read(fd, MAX_SOURCE + 1)
            if len(raw) != st.st_size:
                raise Refused("SOURCE_READ_CHANGED")
        except OSError as exc:
            raise Refused("SOURCE_UNREADABLE") from exc
        finally:
            if fd is not None:
                os.close(fd)
        try:
            document = json.loads(raw)
            Observer.validate_snapshot(document)
        except (ValueError, UnicodeError, TypeError,
                Observer.Refused) as exc:
            raise Refused("INVALID_SOURCE_ALARMS") from exc
        return _digest(raw), document

    def _connect(self):
        self._private_root()
        if self.db.is_symlink():
            raise Refused("UNSAFE_CANDIDATE_FILE")
        try:
            fd = os.open(self.db, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
                         | os.O_CLOEXEC, 0o600)
            try:
                st = os.fstat(fd)
                if (not stat.S_ISREG(st.st_mode)
                        or st.st_uid != os.getuid() or st.st_nlink != 1
                        or stat.S_IMODE(st.st_mode) != 0o600):
                    raise Refused("UNSAFE_CANDIDATE_FILE")
            finally:
                os.close(fd)
            conn = sqlite3.connect(str(self.db), timeout=2,
                                   isolation_level=None)
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA secure_delete=ON")
            conn.execute("PRAGMA busy_timeout=2000")
            conn.execute("CREATE TABLE IF NOT EXISTS canonical_state("
                         "singleton INTEGER PRIMARY KEY CHECK(singleton=1),"
                         "record TEXT NOT NULL)")
            return conn
        except (sqlite3.Error, OSError) as exc:
            raise Refused("CANDIDATE_STORE_UNAVAILABLE") from exc

    def _validate(self, state):
        if (type(state) is not dict
                or set(state) != {"version", "scope", "phase", "revision",
                                  "sourceDigest", "oldEpoch", "ownerEpoch",
                                  "challengeSha256", "alarmDocument", "receipts"}
                or state["version"] != SCHEMA
                or state["scope"] != self.scope
                or state["phase"] not in ("prepared", "released", "candidate")
                or not integer(state["revision"])
                or not integer(state["oldEpoch"], 1)
                or not integer(state["ownerEpoch"])
                or type(state["sourceDigest"]) is not str
                or not HEX.fullmatch(state["sourceDigest"])
                or type(state["challengeSha256"]) is not str
                or not HEX.fullmatch(state["challengeSha256"])
                or type(state["receipts"]) is not dict
                or len(state["receipts"]) > MAX_RECEIPTS):
            raise Refused("CANDIDATE_STATE_INVALID")
        if ((state["phase"] == "prepared"
             and (state["revision"] != 0 or state["ownerEpoch"] != 0))
            or (state["phase"] == "released"
                and (state["revision"] != 1 or state["ownerEpoch"] != 0))
            or (state["phase"] == "candidate"
                and (state["revision"] < 2
                     or state["ownerEpoch"] <= state["oldEpoch"]))):
            raise Refused("CANDIDATE_PHASE_INVALID")
        try:
            Observer.validate_snapshot(state["alarmDocument"])
        except (Observer.Refused, KeyError, TypeError) as exc:
            raise Refused("CANDIDATE_ALARMS_INVALID") from exc
        for key, value in state["receipts"].items():
            if (type(key) is not str or not HEX.fullmatch(key)
                    or type(value) is not dict
                    or set(value) != {"alarmId", "expectedDueMs",
                                      "ownerEpoch", "phase"}
                    or not integer(value["alarmId"], 1)
                    or not integer(value["expectedDueMs"], 1, 8640000000000000)
                    or not integer(value["ownerEpoch"], 1)
                    or value["phase"] not in ("ringing", "stopped", "snoozed")):
                raise Refused("CANDIDATE_RECEIPT_INVALID")
        return state

    def _transaction(self, action):
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            found = conn.execute(
                "SELECT record FROM canonical_state WHERE singleton=1").fetchone()
            current = None
            if found is not None:
                if type(found[0]) is not str or len(found[0]) > MAX_ROW:
                    raise Refused("CANDIDATE_STATE_INVALID")
                try:
                    current = self._validate(json.loads(found[0]))
                except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
                    raise Refused("CANDIDATE_STATE_INVALID") from exc
            result, updated = action(current)
            if updated is not None:
                serialized = json.dumps(updated, separators=(",", ":"),
                                        sort_keys=True, ensure_ascii=False)
                if len(serialized.encode()) > MAX_ROW:
                    raise Refused("CANDIDATE_TOO_LARGE")
                self._validate(updated)
                conn.execute(
                    "INSERT INTO canonical_state(singleton,record) VALUES(1,?) "
                    "ON CONFLICT(singleton) DO UPDATE SET record=excluded.record",
                    (serialized,))
            if self.before_commit is not None:
                self.before_commit()
            conn.execute("COMMIT")
            return result
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    @staticmethod
    def _receipt(state, status):
        return {"status": status, "revision": state["revision"],
                "ownerEpoch": state["ownerEpoch"],
                "receiptCount": len(state["receipts"]),
                "candidateOnly": True, "ownsRealAlarmFile": False,
                "canRing": False, "canNotify": False}

    def prepare(self, expected_source_digest, old_epoch):
        if (type(expected_source_digest) is not str
                or not HEX.fullmatch(expected_source_digest)
                or not integer(old_epoch, 1)):
            raise Refused("INVALID_PREPARE_INPUT")
        source_hash, document = self._read_source()
        if source_hash != expected_source_digest:
            raise Refused("SOURCE_REVISION_CHANGED")
        challenge = secrets.token_hex(32)
        def apply(current):
            if current is not None:
                raise Refused("CANDIDATE_ALREADY_PREPARED")
            state = {"version": SCHEMA, "scope": self.scope,
                     "phase": "prepared", "revision": 0,
                     "sourceDigest": source_hash,
                     "oldEpoch": old_epoch, "ownerEpoch": 0,
                     "challengeSha256": _digest(challenge.encode("ascii")),
                     "alarmDocument": document, "receipts": {}}
            if self._read_source()[0] != source_hash:
                raise Refused("SOURCE_CHANGED_DURING_PREPARE")
            return dict(self._receipt(state, "PREPARED_SYNTHETIC"),
                        scope=self.scope, sourceDigest=source_hash,
                        challenge=challenge), state
        return self._transaction(apply)

    def synthetic_ack_release(self, challenge, proof, expected_revision):
        if (type(challenge) is not str or not HEX.fullmatch(challenge)
                or type(proof) is not str or not HEX.fullmatch(proof)
                or not integer(expected_revision)):
            raise Refused("INVALID_RELEASE_INPUT")
        def apply(current):
            if current is None:
                raise Refused("CANDIDATE_NOT_PREPARED")
            if current["phase"] != "prepared":
                raise Refused("SYNTHETIC_RELEASE_ALREADY_USED")
            if current["revision"] != expected_revision:
                raise Refused("STALE_HANDOFF_REVISION")
            if _digest(challenge.encode("ascii")) != current["challengeSha256"]:
                raise Refused("RELEASE_CHALLENGE_MISMATCH")
            expected = synthetic_release_proof(
                self.secret, self.scope, current["sourceDigest"],
                current["oldEpoch"], challenge)
            if not hmac.compare_digest(proof, expected):
                raise Refused("UNTRUSTED_SYNTHETIC_RELEASE")
            if self._read_source()[0] != current["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_OUTSIDE_CANDIDATE")
            after = dict(current, phase="released", revision=1)
            return self._receipt(after, "RELEASED_SYNTHETIC"), after
        return self._transaction(apply)

    def take_candidate(self, new_epoch, expected_revision):
        if not integer(new_epoch, 1) or not integer(expected_revision):
            raise Refused("INVALID_TAKEOVER_INPUT")
        def apply(current):
            if current is None or current["phase"] != "released":
                raise Refused("OLD_WRITER_NOT_RELEASED")
            if expected_revision != current["revision"]:
                raise Refused("STALE_HANDOFF_REVISION")
            if new_epoch <= current["oldEpoch"]:
                raise Refused("OWNER_EPOCH_NOT_ADVANCED")
            if self._read_source()[0] != current["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_OUTSIDE_CANDIDATE")
            after = dict(current, ownerEpoch=new_epoch,
                         phase="candidate", revision=current["revision"] + 1)
            if self._read_source()[0] != current["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_DURING_HANDOFF")
            return self._receipt(after, "CANDIDATE_ONLY"), after
        return self._transaction(apply)

    def view(self):
        def apply(current):
            if current is None:
                raise Refused("CANDIDATE_NOT_PREPARED")
            if self._read_source()[0] != current["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_OUTSIDE_CANDIDATE")
            return dict(self._receipt(current, current["phase"].upper()),
                        alarmCount=len(current["alarmDocument"]["alarms"]),
                        sourceDigest=current["sourceDigest"]), None
        return self._transaction(apply)

    def action(self, *, epoch, revision, kind, alarm_id, now_ms,
               due_ms=0, ring_started_ms=0, note=None):
        if (not integer(epoch, 1) or not integer(revision)
                or not integer(alarm_id, 1)
                or not integer(now_ms, 1, 8640000000000000)
                or kind not in ("tick", "stop", "snooze", "note")):
            raise Refused("INVALID_CANDIDATE_ACTION")
        def apply(current):
            if current is None or current["phase"] != "candidate":
                raise Refused("CANONICAL_HANDOFF_NOT_COMPLETE")
            if current["ownerEpoch"] != epoch:
                raise Refused("STALE_OWNER_EPOCH")
            if current["revision"] != revision:
                raise Refused("STALE_CANDIDATE_REVISION")
            if self._read_source()[0] != current["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_OUTSIDE_CANDIDATE")
            after = copy.deepcopy(current)
            alarms = after["alarmDocument"]["alarms"]
            selected = [row for row in alarms if row.get("id") == alarm_id]
            if len(selected) != 1:
                raise Refused("ALARM_NOT_IN_CANDIDATE")
            row = selected[0]
            if kind == "tick":
                phase = Observer.evaluate_alarm(row, now_ms)
                if (not integer(due_ms, 1, 8640000000000000)
                        or phase["phase"] not in (
                            "ELIGIBLE_IF_OWNED", "SNOOZE_ELIGIBLE_IF_OWNED")
                        or phase["dueAtMs"] != due_ms):
                    raise Refused("CANDIDATE_ALARM_NOT_DUE")
                key = Shadow.receipt_key(row, due_ms)
                if key in after["receipts"]:
                    raise Refused("CANDIDATE_OCCURRENCE_ALREADY_RECORDED")
                if len(after["receipts"]) >= MAX_RECEIPTS:
                    raise Refused("CANDIDATE_RECEIPTS_FULL")
                row.update(ringing=True, ringStartedAtMs=now_ms,
                           snoozeUntilMs=0, lastProcessedDueMs=due_ms,
                           lastExpectedAtMs=due_ms,
                           lastEventAtMs=now_ms, lastEventKind="fired",
                           lastFiredAtMs=now_ms, lastOccurrenceKey=key,
                           lastFiredDay=datetime.fromtimestamp(
                               due_ms / 1000).date().isoformat())
                after["receipts"][key] = {
                    "alarmId": alarm_id, "expectedDueMs": due_ms,
                    "ownerEpoch": epoch, "phase": "ringing"}
            elif kind in ("stop", "snooze"):
                if (not integer(ring_started_ms, 1, 8640000000000000)
                        or not row.get("ringing")
                        or row.get("ringStartedAtMs") != ring_started_ms):
                    raise Refused("STALE_RING_ACTION")
                key = row.get("lastOccurrenceKey")
                receipt = after["receipts"].get(key)
                if (not isinstance(receipt, dict)
                        or receipt["phase"] != "ringing"
                        or receipt["alarmId"] != alarm_id
                        or receipt["expectedDueMs"]
                            != row.get("lastExpectedAtMs")):
                    raise Refused("MISSING_CURRENT_OCCURRENCE_RECEIPT")
                row.update(ringing=False, ringStartedAtMs=0,
                           snoozeUntilMs=now_ms + 300000
                               if kind == "snooze" else 0,
                           lastEventAtMs=now_ms,
                           lastEventKind="snoozed" if kind == "snooze"
                               else "stopped")
                receipt["phase"] = row["lastEventKind"]
            else:
                if (type(note) is not str or len(note) > 256
                        or any(ord(c) < 32 or ord(c) == 127 for c in note)):
                    raise Refused("INVALID_CANDIDATE_NOTE")
                row["note"] = note
            Observer.validate_snapshot(after["alarmDocument"])
            after["revision"] += 1
            if self._read_source()[0] != after["sourceDigest"]:
                raise Refused("SOURCE_CHANGED_DURING_CANDIDATE_ACTION")
            return self._receipt(after, kind.upper() + "_CANDIDATE_ONLY"), after
        return self._transaction(apply)
