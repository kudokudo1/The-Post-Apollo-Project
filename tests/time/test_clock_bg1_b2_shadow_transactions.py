"""BG1-B2A: synthetic single-writer shadow transaction tests with real IPC."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_clock_bg1_broker_protocol import Client, due_ms

ROOT = Path(__file__).resolve().parents[2]
BROKER = ROOT / "services/time/AlarmOwnershipBroker.py"
SHADOW = ROOT / "services/time/AlarmShadowTransactions.py"
SHELL = ROOT / "services/time/AlarmManagerService.qml"
OBSERVER = ROOT / "services/time/AlarmBackgroundObserver.py"


class ShadowTransactionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "quickshell-id"
        self.data.mkdir(mode=0o700)
        self.alarms = self.data / "time-alarms-v2.json"
        self.state = self.data / "alarm-ownership-v1"
        self.sockdir = self.base / "private"
        self.sockdir.mkdir(mode=0o700)
        self.sock = self.sockdir / "bg1-synthetic.sock"
        self.now = due_ms() + 30000
        self.saved_doc = {
            "version": 2, "nextId": 2, "alarms": [{
                "id": 1, "name": "Sensitive personal wake alarm",
                "note": "Private family note",
                "hour": 6, "minute": 40, "mode": "weekly",
                "date": "", "weekdays": [3],
                "enabled": True, "completed": False, "ringing": False,
                "ringStartedAtMs": 0, "snoozeUntilMs": 0,
                "pausedUntilDate": "", "lastFiredDay": "",
                "lastProcessedDueMs": 0, "armedAtMs": due_ms() - 60000,
                "lastExpectedAtMs": 0,
            }]
        }
        self.alarms.write_text(json.dumps(self.saved_doc) + "\n")
        self.alarms.chmod(0o600)
        self.original_saved_bytes = self.alarms.read_bytes()
        self.env = dict(os.environ, TZ="America/New_York")
        self.process = subprocess.Popen([
            sys.executable, "-I", "-B", str(BROKER), "--serve-synthetic",
            "--alarm-file", str(self.alarms),
            "--state-dir", str(self.state),
            "--socket", str(self.sock),
            "--synthetic-now-ms", str(self.now),
        ], env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(self.close_server)
        for _ in range(150):
            if self.sock.is_socket():
                break
            if self.process.poll() is not None:
                self.fail("Synthetic broker exited: " + self.process.stderr.read())
            time.sleep(.025)
        self.assertTrue(self.sock.is_socket())

    def close_server(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate(timeout=4)

    def client(self, role="quickshell"):
        c = Client(self.sock)
        self.assertTrue(c.send(op="hello", role=role)["ok"])
        return c

    def begin(self, c):
        s = c.send(op="snapshot")
        self.assertTrue(s["ok"])
        self.assertTrue(c.send(op="acquire")["ok"])
        b = c.send(op="shadow_begin", sourceDigest=s["sourceDigest"])
        self.assertTrue(b["ok"], b)
        self.assertEqual(b["revision"], 0)
        return b

    def shadow_disk(self):
        p = self.state / "shadow-alarms-v1.json"
        return json.loads(p.read_text())

    def test_tick_and_stop_are_atomic_with_one_receipt_and_no_live_alarm_change(self):
        clock = self.client()
        rival = self.client("background")
        try:
            self.begin(clock)
            self.assertEqual(rival.send(op="shadow_view")["reason"], "NO_LIVE_OWNER_SESSION")
            self.assertEqual(rival.send(op="acquire")["reason"], "OWNER_ALREADY_ACTIVE")
            t = clock.send(op="shadow_tick", revision=0, alarmId=1,
                           expectedDueMs=due_ms())
            self.assertTrue(t["ok"], t)
            self.assertEqual(t["status"], "TICK_SHADOW_ONLY")
            self.assertEqual(t["revision"], 1)
            self.assertFalse(t["actuationEnabled"])
            disk = self.shadow_disk()
            self.assertEqual(disk["revision"], 1)
            self.assertEqual(len(disk["receipts"]), 1)
            self.assertTrue(disk["alarmDocument"]["alarms"][0]["ringing"])
            self.assertEqual(disk["alarmDocument"]["alarms"][0]["lastProcessedDueMs"], due_ms())
            self.assertEqual(next(iter(disk["receipts"].values()))["phase"], "ringing")
            self.assertEqual(self.alarms.read_bytes(), self.original_saved_bytes)
            duplicate = clock.send(op="shadow_tick", revision=1, alarmId=1,
                                   expectedDueMs=due_ms())
            self.assertFalse(duplicate["ok"])
            self.assertEqual(self.shadow_disk()["revision"], 1)
            # A stale notification cannot stop a different ring generation.
            stale = clock.send(op="shadow_stop", revision=1, alarmId=1,
                               ringStartedMs=self.now-60000)
            self.assertEqual(stale["reason"], "STALE_RING_ACTION")
            stopped = clock.send(op="shadow_stop", revision=1, alarmId=1,
                                 ringStartedMs=self.now)
            self.assertTrue(stopped["ok"], stopped)
            self.assertEqual(stopped["revision"], 2)
            disk = self.shadow_disk()
            self.assertFalse(disk["alarmDocument"]["alarms"][0]["ringing"])
            self.assertEqual(next(iter(disk["receipts"].values()))["phase"], "stopped")
            self.assertEqual(self.alarms.read_bytes(), self.original_saved_bytes)
            self.assertEqual(clock.send(op="shadow_stop", revision=1, alarmId=1,
                                       ringStartedMs=self.now)["reason"], "SHADOW_REVISION_MISMATCH")
            self.assertTrue(clock.send(op="release")["ok"])
            self.assertTrue(rival.send(op="acquire")["ok"])
            self.assertEqual(rival.send(op="shadow_view")["revision"], 2)
            self.assertEqual(rival.send(op="shadow_tick", revision=2, alarmId=1,
                                        expectedDueMs=due_ms())["reason"], "ALARM_NOT_DUE")
            self.assertTrue(rival.send(op="release")["ok"])
        finally:
            clock.close()
            rival.close()

    def test_snooze_and_edit_are_same_file_revision_checked(self):
        c = self.client()
        try:
            self.begin(c)
            self.assertTrue(c.send(op="shadow_tick", revision=0, alarmId=1,
                                   expectedDueMs=due_ms())["ok"])
            snoozed = c.send(op="shadow_snooze", revision=1, alarmId=1,
                             ringStartedMs=self.now)
            self.assertTrue(snoozed["ok"], snoozed)
            disk = self.shadow_disk()
            row = disk["alarmDocument"]["alarms"][0]
            self.assertFalse(row["ringing"])
            self.assertEqual(row["snoozeUntilMs"], self.now + 300000)
            self.assertEqual(row["lastEventKind"], "snoozed")
            self.assertEqual(next(iter(disk["receipts"].values()))["phase"], "snoozed")
            self.assertEqual(c.send(op="shadow_edit", revision=1, alarmId=1,
                                    patch={"note":"Changed"})["reason"],
                             "SHADOW_REVISION_MISMATCH")
            edited = c.send(op="shadow_edit", revision=2, alarmId=1,
                            patch={"name":"Travel alarm", "note":"New private note"})
            self.assertTrue(edited["ok"], edited)
            self.assertEqual(edited["revision"], 3)
            after = self.shadow_disk()
            self.assertEqual(after["alarmDocument"]["alarms"][0]["name"], "Travel alarm")
            self.assertEqual(after["receipts"], disk["receipts"])
            self.assertEqual(self.alarms.read_bytes(), self.original_saved_bytes)
            invalid = c.send(op="shadow_edit", revision=3, alarmId=1,
                             patch={"ringing":True})
            self.assertEqual(invalid["reason"], "INVALID_SHADOW_EDIT")
            self.assertEqual(self.shadow_disk()["revision"], 3)
            self.assertTrue(c.send(op="release")["ok"])
        finally:
            c.close()

    def test_corruption_and_stale_file_revision_refuse_without_overwrite(self):
        c = self.client()
        try:
            self.begin(c)
            target = self.state / "shadow-alarms-v1.json"
            target.write_text('{"tampered":true}')
            before = target.read_bytes()
            denied = c.send(op="shadow_view")
            self.assertEqual(denied["reason"], "INVALID_SHADOW_STATE")
            self.assertEqual(target.read_bytes(), before)
            denied = c.send(op="shadow_tick", revision=0, alarmId=1,
                            expectedDueMs=due_ms())
            self.assertEqual(denied["reason"], "INVALID_SHADOW_STATE")
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(c.send(op="release")["ok"])
        finally:
            c.close()

    def test_broker_cannot_reinitialize_shadow_or_apply_after_session_release(self):
        c = self.client()
        try:
            self.begin(c)
            digest = c.send(op="snapshot")["sourceDigest"]
            self.assertEqual(c.send(op="shadow_begin", sourceDigest=digest)["reason"],
                             "SHADOW_ALREADY_INITIALIZED")
            self.assertTrue(c.send(op="release")["ok"])
            self.assertEqual(c.send(op="shadow_tick", revision=0, alarmId=1,
                                    expectedDueMs=due_ms())["reason"],
                             "NO_LIVE_OWNER_SESSION")
            self.assertEqual(self.shadow_disk()["revision"], 0)
        finally:
            c.close()

    def test_failed_atomic_shadow_write_keeps_previous_receipt_and_document(self):
        # Direct unit test uses a synthetic owner epoch, not the live broker.
        import importlib.util
        spec = importlib.util.spec_from_file_location("bg1_shadow", SHADOW)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # The broker has already initialized the lease dir in its own
        # child process only after acquire; this test creates a private
        # disposable state directory for direct fixture use.
        self.state.mkdir(mode=0o700, exist_ok=True)
        store = module.ShadowStore(self.state, self.alarms)
        def minimal_validate(doc):
            assert doc["version"] == 2 and len(doc["alarms"]) == 1
        store.initialize(self.saved_doc, "b"*64, 1, minimal_validate)
        original = (self.state / "shadow-alarms-v1.json").read_bytes()
        def evaluate(a, now):
            return {"phase":"ELIGIBLE_IF_OWNED", "dueAtMs":due_ms()}
        with patch.object(store, "_write_locked", side_effect=OSError("simulated disk failure")):
            with self.assertRaises(OSError):
                store.transition(1, 0, "tick", 1, self.now,
                                 expected_due_ms=due_ms(),
                                 evaluate=evaluate, validate=minimal_validate)
        self.assertEqual((self.state / "shadow-alarms-v1.json").read_bytes(), original)
        self.assertEqual(self.alarms.read_bytes(), self.original_saved_bytes)

    def test_no_quickshell_or_background_actuation_in_shadow_path(self):
        for path in (BROKER, SHADOW):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("notify-send", text)
            self.assertNotIn("SoundEffect", text)
            self.assertNotIn("systemctl", text)
        self.assertNotIn("AlarmShadowTransactions", SHELL.read_text())
        self.assertNotIn("AlarmShadowTransactions", OBSERVER.read_text())
        self.assertIn("actuationEnabled", SHADOW.read_text())
        self.assertIn("realAlarmFileModified", SHADOW.read_text())


if __name__ == "__main__":
    unittest.main()
