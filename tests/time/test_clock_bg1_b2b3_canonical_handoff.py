"""BG1-B2B3: source-fenced, two-phase canonical writer fixture, no actuation."""
from __future__ import annotations

from datetime import datetime
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/time/AlarmCanonicalHandoffFixture.py"
QML = ROOT / "services/time/AlarmManagerService.qml"
OBSERVER = ROOT / "services/time/AlarmBackgroundObserver.py"
BROKER = ROOT / "services/time/AlarmOwnershipBroker.py"
spec = importlib.util.spec_from_file_location("bg1_canonical_handoff_test", MODULE)
Handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Handoff)


def due_ms():
    return int(datetime(2026, 11, 11, 6, 40).timestamp() * 1000)


def worker(root, source, secret, epoch, revision, note, ready, results):
    f = Handoff.CanonicalHandoffFixture(
        root, source, old_writer_test_secret=secret, synthetic_only=True)
    ready.wait(5)
    try:
        result = f.action(epoch=epoch, revision=revision, kind="note",
                          alarm_id=1, now_ms=due_ms()+30000, note=note)
        results.put(("success", result["revision"]))
    except Handoff.Refused as exc:
        results.put(("refused", str(exc)))


class CanonicalHandoffFixtureTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="bg1-handoff-")
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)
        self.data = self.base / "synthetic-quickshell"
        self.data.mkdir(mode=0o700)
        self.root = self.base / "bg1-canonical-fixture"
        self.root.mkdir(mode=0o700)
        self.source = self.data / "time-alarms-v2.json"
        self.doc = {"version": 2, "nextId": 2, "alarms": [{
            "id": 1, "name": "private family alarm",
            "note": "private family note", "hour": 6, "minute": 40,
            "mode": "weekly", "date": "", "weekdays": [3],
            "enabled": True, "completed": False, "ringing": False,
            "ringStartedAtMs": 0, "snoozeUntilMs": 0,
            "pausedUntilDate": "", "lastFiredDay": "",
            "lastProcessedDueMs": 0, "armedAtMs": due_ms() - 60000,
            "lastExpectedAtMs": 0,
        }]}
        self.write_source()
        self.original = self.source.read_bytes()
        self.secret = bytes(range(32))
        self.writer = self.instance()

    def write_source(self):
        self.source.write_bytes((json.dumps(self.doc, sort_keys=True)
                                 + "\n").encode())
        self.source.chmod(0o600)

    def instance(self):
        return Handoff.CanonicalHandoffFixture(
            self.root, self.source, old_writer_test_secret=self.secret,
            synthetic_only=True)

    def prepared(self):
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        return self.writer.prepare(digest, old_epoch=7)

    def released(self):
        receipt = self.prepared()
        proof = Handoff.synthetic_release_proof(
            self.secret, receipt["scope"], receipt["sourceDigest"],
            old_epoch=7, challenge=receipt["challenge"])
        return self.writer.synthetic_ack_release(
            receipt["challenge"], proof, expected_revision=0)

    def candidate(self):
        self.released()
        return self.writer.take_candidate(new_epoch=8, expected_revision=1)

    def refusal(self, fn, code):
        with self.assertRaises(Handoff.Refused) as ctx:
            fn()
        self.assertEqual(str(ctx.exception), code)

    def state_from_sqlite(self):
        conn = sqlite3.connect(self.writer.db)
        try:
            row = conn.execute("SELECT record FROM canonical_state").fetchone()
            return json.loads(row[0]) if row else None
        finally:
            conn.close()

    def test_full_rehearsal_keeps_exact_source_bytes_and_private_metadata(self):
        start = self.prepared()
        self.assertEqual(start["status"], "PREPARED_SYNTHETIC")
        self.assertTrue(start["candidateOnly"])
        self.assertFalse(start["ownsRealAlarmFile"])
        self.assertFalse(start["canRing"])
        self.assertFalse(start["canNotify"])
        self.assertEqual(self.writer.db.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.writer.view()["alarmCount"], 1)
        self.assertNotIn("private family", str(self.writer.view()))
        proof = Handoff.synthetic_release_proof(
            self.secret, start["scope"], start["sourceDigest"], 7,
            start["challenge"])
        released = self.writer.synthetic_ack_release(
            start["challenge"], proof, expected_revision=0)
        self.assertEqual(released["revision"], 1)
        moved = self.writer.take_candidate(new_epoch=8, expected_revision=1)
        self.assertEqual(moved["revision"], 2)
        self.assertEqual(moved["ownerEpoch"], 8)
        self.assertEqual(self.state_from_sqlite()["phase"], "candidate")
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertFalse(self.writer.view()["ownsRealAlarmFile"])

    def test_bad_old_writer_proof_cannot_release_or_takeover(self):
        a = self.prepared()
        self.refusal(lambda: self.writer.take_candidate(8, 0),
                     "OLD_WRITER_NOT_RELEASED")
        self.refusal(lambda: self.writer.synthetic_ack_release(
            a["challenge"], "0"*64, 0), "UNTRUSTED_SYNTHETIC_RELEASE")
        self.refusal(lambda: self.writer.synthetic_ack_release(
            "0"*64, "0"*64, 0), "RELEASE_CHALLENGE_MISMATCH")
        self.assertEqual(self.state_from_sqlite()["revision"], 0)
        self.refusal(lambda: self.writer.prepare(a["sourceDigest"], 7),
                     "CANDIDATE_ALREADY_PREPARED")
        self.released if False else None
        proof = Handoff.synthetic_release_proof(
            self.secret, a["scope"], a["sourceDigest"], 7, a["challenge"])
        self.assertEqual(
            self.writer.synthetic_ack_release(a["challenge"], proof, 0)[
                "status"], "RELEASED_SYNTHETIC")
        self.refusal(lambda: self.writer.synthetic_ack_release(
            a["challenge"], proof, 1), "SYNTHETIC_RELEASE_ALREADY_USED")
        self.refusal(lambda: self.writer.take_candidate(7, 1),
                     "OWNER_EPOCH_NOT_ADVANCED")
        self.refusal(lambda: self.writer.take_candidate(8, 0),
                     "STALE_HANDOFF_REVISION")

    def test_source_change_after_release_denies_candidate_without_overwrite(self):
        self.released()
        self.doc["alarms"][0]["note"] = "updated outside synthetic candidate"
        self.write_source()
        source_after = self.source.read_bytes()
        self.refusal(lambda: self.writer.take_candidate(8, 1),
                     "SOURCE_CHANGED_OUTSIDE_CANDIDATE")
        self.refusal(self.writer.view, "SOURCE_CHANGED_OUTSIDE_CANDIDATE")
        self.assertEqual(self.state_from_sqlite()["phase"], "released")
        self.assertEqual(self.source.read_bytes(), source_after)

    def test_source_change_after_candidate_denies_all_new_transactions(self):
        self.candidate()
        self.doc["alarms"][0]["hour"] = 9
        self.write_source()
        source_after = self.source.read_bytes()
        self.refusal(lambda: self.writer.action(
            epoch=8, revision=2, kind="note", alarm_id=1,
            now_ms=due_ms()+30000, note="new"),
            "SOURCE_CHANGED_OUTSIDE_CANDIDATE")
        self.assertEqual(self.state_from_sqlite()["revision"], 2)
        self.assertEqual(self.source.read_bytes(), source_after)

    def test_exact_due_tick_receipt_and_stop_in_one_sqlite_transaction(self):
        self.candidate()
        due = due_ms()
        started = due + 30000
        tick = self.writer.action(epoch=8, revision=2, kind="tick",
                                  alarm_id=1, now_ms=started, due_ms=due)
        self.assertEqual(tick["revision"], 3)
        st = self.state_from_sqlite()
        self.assertTrue(st["alarmDocument"]["alarms"][0]["ringing"])
        self.assertEqual(len(st["receipts"]), 1)
        self.assertEqual(next(iter(st["receipts"].values()))["phase"], "ringing")
        self.refusal(lambda: self.writer.action(
            epoch=7, revision=3, kind="stop", alarm_id=1,
            now_ms=started + 1000, ring_started_ms=started),
            "STALE_OWNER_EPOCH")
        self.refusal(lambda: self.writer.action(
            epoch=8, revision=3, kind="stop", alarm_id=1,
            now_ms=started + 1000, ring_started_ms=started - 1),
            "STALE_RING_ACTION")
        stopped = self.writer.action(epoch=8, revision=3, kind="stop",
                                     alarm_id=1, now_ms=started + 1000,
                                     ring_started_ms=started)
        self.assertEqual(stopped["revision"], 4)
        st = self.state_from_sqlite()
        self.assertFalse(st["alarmDocument"]["alarms"][0]["ringing"])
        self.assertEqual(next(iter(st["receipts"].values()))["phase"], "stopped")
        self.assertEqual(self.source.read_bytes(), self.original)
        self.refusal(lambda: self.writer.action(
            epoch=8, revision=3, kind="tick", alarm_id=1,
            now_ms=started, due_ms=due), "STALE_CANDIDATE_REVISION")

    def test_snooze_is_atomic_and_notes_do_not_expose_or_change_source(self):
        self.candidate()
        due = due_ms()
        started = due + 30000
        self.writer.action(epoch=8, revision=2, kind="tick",
                           alarm_id=1, now_ms=started, due_ms=due)
        result = self.writer.action(epoch=8, revision=3, kind="snooze",
                                    alarm_id=1, now_ms=started+2000,
                                    ring_started_ms=started)
        self.assertEqual(result["revision"], 4)
        state = self.state_from_sqlite()
        self.assertEqual(state["alarmDocument"]["alarms"][0]["snoozeUntilMs"],
                         started + 302000)
        self.assertEqual(next(iter(state["receipts"].values()))["phase"],
                         "snoozed")
        note = self.writer.action(epoch=8, revision=4, kind="note",
                                  alarm_id=1, now_ms=started+3000,
                                  note="SENSITIVE REHEARSAL NOTE")
        self.assertNotIn("SENSITIVE", str(note))
        self.assertEqual(self.state_from_sqlite()["alarmDocument"]["alarms"][0][
            "note"], "SENSITIVE REHEARSAL NOTE")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_failed_commit_rolls_back_state_and_receipts_after_restart(self):
        self.candidate()
        before = self.state_from_sqlite()
        def crash():
            raise OSError("simulated crash before SQLite commit")
        self.writer.before_commit = crash
        with self.assertRaises(OSError):
            self.writer.action(epoch=8, revision=2, kind="tick",
                               alarm_id=1, now_ms=due_ms()+30000,
                               due_ms=due_ms())
        self.writer.before_commit = None
        after = self.instance()
        self.assertEqual(after.view()["revision"], 2)
        self.assertEqual(self.state_from_sqlite(), before)
        self.assertEqual(after.action(
            epoch=8, revision=2, kind="tick", alarm_id=1,
            now_ms=due_ms()+30000, due_ms=due_ms())["revision"], 3)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_two_processes_cannot_commit_same_revision_twice(self):
        self.candidate()
        context = multiprocessing.get_context("fork")
        go = context.Event()
        result = context.Queue()
        procs = [
            context.Process(target=worker, args=(
                str(self.root), str(self.source), self.secret, 8, 2,
                f"Worker {i}", go, result))
            for i in range(2)
        ]
        for proc in procs:
            proc.start()
        go.set()
        outcomes = [result.get(timeout=8) for _ in range(2)]
        for proc in procs:
            proc.join(timeout=8)
            self.assertEqual(proc.exitcode, 0)
        self.assertEqual(sum(v[0] == "success" for v in outcomes), 1)
        self.assertEqual(sum(v == ("refused", "STALE_CANDIDATE_REVISION")
                             for v in outcomes), 1)
        self.assertEqual(self.state_from_sqlite()["revision"], 3)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_source_and_candidate_path_permissions_fail_closed(self):
        self.refusal(lambda: Handoff.CanonicalHandoffFixture(
            self.root, self.source, old_writer_test_secret=self.secret),
            "DISPOSABLE_FIXTURE_REQUIRED")
        self.refusal(lambda: Handoff.CanonicalHandoffFixture(
            self.root, self.source, old_writer_test_secret=self.secret,
            synthetic_only="true"), "DISPOSABLE_FIXTURE_REQUIRED")
        wrong = self.base / "normal-alarm-ownership-v1"
        wrong.mkdir(mode=0o700)
        self.refusal(lambda: Handoff.CanonicalHandoffFixture(
            wrong, self.source, old_writer_test_secret=self.secret,
            synthetic_only=True), "DISPOSABLE_FIXTURE_REQUIRED")
        self.source.chmod(0o644)
        self.refusal(self.prepared, "UNSAFE_SOURCE_RECORD")
        self.source.chmod(0o600)
        self.root.chmod(0o755)
        self.refusal(self.prepared, "UNSAFE_FIXTURE_DIRECTORY")
        self.root.chmod(0o700)
        other = self.base / "replacement.json"
        other.write_bytes(self.source.read_bytes())
        self.source.unlink()
        self.source.symlink_to(other)
        self.refusal(self.prepared, "SOURCE_LINK_REFUSED")

    def test_corrupted_candidate_never_auto_resets(self):
        self.candidate()
        conn = sqlite3.connect(self.writer.db)
        conn.execute("UPDATE canonical_state SET record=? WHERE singleton=1",
                     ('{"version":1,"forged":true}',))
        conn.commit()
        conn.close()
        self.refusal(self.writer.view, "CANDIDATE_STATE_INVALID")
        self.refusal(lambda: self.writer.action(
            epoch=8, revision=2, kind="note", alarm_id=1,
            now_ms=due_ms()+30000, note="no"), "CANDIDATE_STATE_INVALID")
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_production_hooks_cannot_be_enabled(self):
        module = MODULE.read_text()
        live = QML.read_text()
        observer = OBSERVER.read_text()
        broker = BROKER.read_text()
        for forbidden in ("notify-send", "SoundEffect", "systemctl",
                          "os.replace(", "alarmFile.setText("):
            self.assertNotIn(forbidden, module)
        self.assertIn("DISPOSABLE_FIXTURE_REQUIRED", module)
        self.assertIn('ownsRealAlarmFile": False', module)
        self.assertIn('canRing": False', module)
        self.assertNotIn("AlarmCanonicalHandoffFixture", live)
        self.assertNotIn("AlarmCanonicalHandoffFixture", observer)
        self.assertNotIn("AlarmCanonicalHandoffFixture", broker)


if __name__ == "__main__":
    unittest.main()
