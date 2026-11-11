"""B0: independent alarm process without any actuation or shared-file writes."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/time/AlarmBackgroundObserver.py"
UNIT = ROOT / "ops/systemd/user/post-apollo-alarm-observer.service"
DOCS = ROOT / "services/time/BACKGROUND-ALARM-B0.md"


def epoch(day, hour, minute, second=0):
    return int(datetime(2026, 11, day, hour, minute, second).timestamp() * 1000)


def fixture(armed, *, hour=6, minute=40, weekdays=None, mode="weekly", day="2026-11-11"):
    if weekdays is None:
        weekdays = [3]
    return {"version": 2, "nextId": 2, "alarms": [{
        "id": 1, "name": "Private name not for logs",
        "note": "Sensitive personal note that must never appear in reports",
        "hour": hour, "minute": minute, "mode": mode, "weekdays": weekdays,
        "date": day if mode == "once" else "",
        "enabled": True, "completed": False, "ringing": False,
        "pausedUntilDate": "", "lastFiredDay": "", "lastProcessedDueMs": 0,
        "armedAtMs": armed, "ringStartedAtMs": 0, "snoozeUntilMs": 0,
        "soundId": "chime", "soundEnabled": True, "volumePercent": 65,
        "keepSaved": True
    }]}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.alarm_file = self.base / "time-alarms-v2.json"
        self.runtime = self.base / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.env = dict(os.environ, TZ="America/New_York",
                        XDG_RUNTIME_DIR=str(self.runtime))
        self.put(fixture(epoch(11, 6, 39, 30)))

    def put(self, doc):
        self.alarm_file.write_text(json.dumps(doc) + "\n", encoding="utf-8")
        self.alarm_file.chmod(0o600)

    def run_once(self, when, path=None):
        command = [sys.executable, "-I", "-B", str(HOST), "--once",
                   "--alarm-file", str(path or self.alarm_file),
                   "--at-ms", str(when)]
        result = subprocess.run(command, env=self.env, capture_output=True,
                                text=True, timeout=8)
        try:
            payload = json.loads(result.stdout)
        except ValueError:
            self.fail("Invalid observer JSON: " + repr(result))
        return result.returncode, payload, result.stdout

    def test_actual_weekly_schedule_and_same_occurrence_without_mutation(self):
        original = self.alarm_file.read_bytes()
        before = self.run_once(epoch(11, 6, 39, 30))
        self.assertEqual(before[0], 0)
        self.assertEqual(before[1]["state"], "READY")
        self.assertEqual(before[1]["alarms"][0]["phase"], "FUTURE")
        self.assertEqual(before[1]["alarms"][0]["nextDueMs"], epoch(11, 6, 40))
        self.assertEqual(self.run_once(epoch(11, 6, 40, 1))[1]["alarms"][0]["phase"],
                         "ELIGIBLE_IF_OWNED")
        self.assertEqual(self.run_once(epoch(11, 6, 41, 55))[1]["alarms"][0]["phase"],
                         "ELIGIBLE_IF_OWNED")
        self.assertEqual(self.run_once(epoch(11, 6, 43))[1]["alarms"][0]["phase"],
                         "MISSED_CANDIDATE")
        self.assertEqual(self.run_once(epoch(12, 7, 10))[1]["alarms"][0]["phase"],
                         "MISSED_CANDIDATE")
        self.assertEqual(self.alarm_file.read_bytes(), original)
        for raw in (before[2], self.run_once(epoch(11, 6, 41))[2]):
            self.assertNotIn("Private name", raw)
            self.assertNotIn("Sensitive personal note", raw)
            self.assertNotIn("soundId", raw)
            self.assertIn('"actuationEnabled":false', raw)
            self.assertIn('"ownsAlarmFile":false', raw)

    def test_replay_suppression_and_old_alarm_uncertainty(self):
        current = fixture(epoch(11, 6, 39, 30))
        current["alarms"][0]["lastProcessedDueMs"] = epoch(11, 6, 40)
        self.put(current)
        self.assertEqual(self.run_once(epoch(11, 6, 41))[1]["alarms"][0]["phase"],
                         "ALREADY_PROCESSED")
        old = fixture(epoch(11, 6, 39, 30))
        del old["alarms"][0]["armedAtMs"]
        del old["alarms"][0]["lastProcessedDueMs"]
        self.put(old)
        self.assertEqual(self.run_once(epoch(11, 6, 40, 30))[1]["alarms"][0]["phase"],
                         "UNKNOWN_ARM_TIME")
        old["alarms"][0]["lastFiredDay"] = "2026-11-11"
        self.put(old)
        self.assertEqual(self.run_once(epoch(11, 6, 40, 30))[1]["alarms"][0]["phase"],
                         "ALREADY_PROCESSED")

    def test_midnight_one_time_pause_snooze_and_active_ring(self):
        once = fixture(epoch(11, 23, 58, 30), hour=23, minute=59,
                       mode="once", day="2026-11-11")
        self.put(once)
        self.assertEqual(self.run_once(epoch(12, 0, 0, 45))[1]["alarms"][0]["phase"],
                         "ELIGIBLE_IF_OWNED")
        self.assertEqual(self.run_once(epoch(12, 0, 3))[1]["alarms"][0]["phase"],
                         "MISSED_CANDIDATE")
        weekly = fixture(epoch(11, 23, 58, 30), hour=23, minute=59)
        self.put(weekly)
        self.assertEqual(self.run_once(epoch(12, 0, 0, 45))[1]["alarms"][0]["phase"],
                         "ELIGIBLE_IF_OWNED")
        weekly["alarms"][0]["pausedUntilDate"] = "2026-11-18"
        self.put(weekly)
        self.assertEqual(self.run_once(epoch(12, 0, 0, 45))[1]["alarms"][0]["phase"],
                         "PAUSED")
        weekly["alarms"][0]["pausedUntilDate"] = ""
        weekly["alarms"][0]["snoozeUntilMs"] = epoch(12, 0, 5)
        self.put(weekly)
        self.assertEqual(self.run_once(epoch(12, 0, 1))[1]["alarms"][0]["phase"],
                         "SNOOZE_PENDING")
        weekly["alarms"][0]["snoozeUntilMs"] = 0
        weekly["alarms"][0]["ringing"] = True
        weekly["alarms"][0]["ringStartedAtMs"] = epoch(11, 23, 59)
        self.put(weekly)
        self.assertEqual(self.run_once(epoch(12, 0, 1))[1]["alarms"][0]["phase"],
                         "ACTIVE_RING_IN_QUICKSHELL")
        self.assertEqual(self.run_once(epoch(12, 0, 20))[1]["alarms"][0]["phase"],
                         "STALE_RING_NEEDS_OWNER_REVIEW")

    def test_bad_path_and_corrupted_document_fail_closed(self):
        incorrect = self.base / "not-alarm.json"
        incorrect.write_text("{}")
        exit_code, failure, _ = self.run_once(epoch(11, 6, 40), incorrect)
        self.assertEqual(exit_code, 2)
        self.assertEqual(failure["reason"], "EXPLICIT_V2_ALARM_PATH_REQUIRED")
        self.assertFalse(failure["actuationEnabled"])
        linked = self.base / "link" / "time-alarms-v2.json"
        linked.parent.mkdir()
        linked.symlink_to(self.alarm_file)
        code, payload, _ = self.run_once(epoch(11, 6, 40), linked)
        self.assertEqual(code, 2)
        self.assertEqual(payload["state"], "REFUSED")
        self.put({"version": 2, "nextId": 2, "alarms": [{
            **fixture(epoch(11, 6, 39))["alarms"][0], "hour": 28
        }]})
        self.assertEqual(self.run_once(epoch(11, 6, 40))[0], 2)
        self.put(fixture(epoch(11, 6, 39)))
        self.alarm_file.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
        self.assertEqual(self.run_once(epoch(11, 6, 40))[1]["state"], "REFUSED")

    def test_observer_watch_lock_prevents_duplicate_background_process(self):
        cmd = [sys.executable, "-I", "-B", str(HOST), "--watch",
               "--interval", "1", "--alarm-file", str(self.alarm_file)]
        first = subprocess.Popen(cmd, env=self.env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        try:
            line = first.stdout.readline()
            self.assertTrue(line, "first observer should emit one safe snapshot")
            self.assertEqual(json.loads(line)["mode"], "READ_ONLY")
            second = subprocess.run(cmd, env=self.env, capture_output=True,
                                    text=True, timeout=5)
            self.assertEqual(second.returncode, 3)
            self.assertEqual(json.loads(second.stdout)["reason"], "OBSERVER_ALREADY_RUNNING")
            self.assertEqual(first.poll(), None)
        finally:
            first.terminate()
            try:
                first.wait(timeout=4)
            except subprocess.TimeoutExpired:
                first.kill()
                first.wait(timeout=4)
            first.stdout.close()
            first.stderr.close()

    def test_no_install_and_no_notification_or_clock_mutation_api(self):
        source = HOST.read_text(encoding="utf-8")
        unit = UNIT.read_text(encoding="utf-8")
        docs = DOCS.read_text(encoding="utf-8")
        self.assertIn("def snapshot_file(path)", source)
        self.assertIn("fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)", source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("notify-send", source)
        self.assertNotIn("SoundEffect", source)
        self.assertNotIn("os.replace", source)
        self.assertNotIn("os.unlink", source)
        self.assertNotIn("[Install]", unit)
        self.assertIn("EnvironmentFile=-%h/.config/post-apollo/alarm-observer.env", unit)
        self.assertIn("POST_APOLLO_ALARM_FILE", unit)
        self.assertIn("Restart=no", unit)
        self.assertIn("NoNewPrivileges=true", unit)
        self.assertIn("RestrictAddressFamilies=AF_UNIX", unit)
        self.assertIn("single-owner lease", docs)
        self.assertIn("cannot ring", docs)


if __name__ == "__main__":
    unittest.main()
