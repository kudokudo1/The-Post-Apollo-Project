"""Real AF_UNIX peer sessions for synthetic BG1-B1 Clock owner broker."""
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
BROKER = ROOT / "services/time/AlarmOwnershipBroker.py"
GATE = ROOT / "services/time/AlarmOwnershipGate.py"
SHELL = ROOT / "services/time/AlarmManagerService.qml"
OBSERVER = ROOT / "services/time/AlarmBackgroundObserver.py"
DOC = ROOT / "services/time/BG1-ALARM-BROKER.md"


def due_ms():
    return int(datetime(2026, 11, 11, 6, 40).timestamp() * 1000)


class Client:
    def __init__(self, path):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(3)
        self.socket.connect(str(path))
        self.read = self.socket.makefile("rb", buffering=0)

    def send(self, **request):
        self.socket.sendall((json.dumps(request, separators=(",", ":")) + "\n").encode())
        result = self.read.readline()
        if not result:
            raise AssertionError("Broker closed before answering " + str(request))
        decoded = json.loads(result)
        assert decoded["mode"] == "SYNTHETIC_BG1_B", decoded
        assert decoded["actuationEnabled"] is False, decoded
        assert decoded["ownsAlarmFile"] is False, decoded
        return decoded

    def close(self):
        self.read.close()
        self.socket.close()


class ClockBG1BrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "quickshell-id"
        self.data.mkdir(mode=0o700)
        self.alarm = self.data / "time-alarms-v2.json"
        self.state = self.data / "alarm-ownership-v1"
        self.sockdir = self.base / "private-socket"
        self.sockdir.mkdir(mode=0o700)
        self.sock = self.sockdir / "bg1-synthetic.sock"
        self.now = due_ms() + 30000
        self.document = {
            "version": 2, "nextId": 2,
            "alarms": [{
                "id": 1, "name": "Private alarm title", "note": "Secret alarm notes",
                "mode": "weekly", "date": "", "weekdays": [3],
                "hour": 6, "minute": 40, "pausedUntilDate": "",
                "enabled": True, "ringing": False, "completed": False,
                "lastFiredDay": "", "ringStartedAtMs": 0,
                "snoozeUntilMs": 0, "armedAtMs": due_ms() - 60000,
                "lastProcessedDueMs": 0,
            }]
        }
        self.write_alarm()
        self.env = dict(os.environ, TZ="America/New_York")
        self.process = subprocess.Popen([
            sys.executable, "-I", "-B", str(BROKER), "--serve-synthetic",
            "--alarm-file", str(self.alarm),
            "--state-dir", str(self.state),
            "--socket", str(self.sock),
            "--synthetic-now-ms", str(self.now),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=self.env, text=True)
        self.addCleanup(self.cleanup_broker)
        for _ in range(160):
            if self.sock.is_socket():
                break
            if self.process.poll() is not None:
                self.fail("BG1 broker crashed before socket: " + self.process.stderr.read())
            time.sleep(.025)
        self.assertTrue(self.sock.is_socket(), "Broker did not bind")
        self.assertEqual(self.sock.stat().st_mode & 0o777, 0o600)

    def write_alarm(self):
        self.alarm.write_text(json.dumps(self.document) + "\n", encoding="utf-8")
        self.alarm.chmod(0o600)

    def cleanup_broker(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.communicate(timeout=4)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.communicate(timeout=4)

    def hello(self, role):
        c = Client(self.sock)
        r = c.send(op="hello", role=role)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["role"], role)
        self.assertTrue(r["testOnly"])
        return c

    def test_two_real_socket_sessions_cannot_own_same_alarm(self):
        clock = self.hello("quickshell")
        background = self.hello("background")
        try:
            a = clock.send(op="acquire")
            self.assertTrue(a["ok"], a)
            self.assertEqual(a["epoch"], 1)
            self.assertTrue(a["reservedOnly"])
            denied = background.send(op="acquire")
            self.assertFalse(denied["ok"])
            self.assertEqual(denied["reason"], "OWNER_ALREADY_ACTIVE")
            renewal = clock.send(op="renew")
            self.assertTrue(renewal["ok"])
            self.assertEqual(renewal["epoch"], 1)
            self.assertTrue(clock.send(op="release")["released"])
            b = background.send(op="acquire")
            self.assertTrue(b["ok"], b)
            self.assertEqual(b["epoch"], 2)
            self.assertTrue(background.send(op="release")["released"])
        finally:
            clock.close()
            background.close()

    def test_exact_source_digest_and_stable_occurrence_claim(self):
        clock = self.hello("quickshell")
        try:
            snapshot = clock.send(op="snapshot")
            self.assertTrue(snapshot["ok"])
            self.assertEqual(snapshot["phases"][0]["phase"], "ELIGIBLE_IF_OWNED")
            self.assertEqual(snapshot["phases"][0]["dueAtMs"], due_ms())
            self.assertTrue(clock.send(op="acquire")["ok"])
            invalid = clock.send(op="reserve", alarmId=1,
                                 expectedDueMs=due_ms() + 60000,
                                 sourceDigest=snapshot["sourceDigest"])
            self.assertEqual(invalid["reason"], "OCCURRENCE_NOT_ELIGIBLE")
            accepted = clock.send(op="reserve", alarmId=1,
                                  expectedDueMs=due_ms(),
                                  sourceDigest=snapshot["sourceDigest"])
            self.assertTrue(accepted["ok"], accepted)
            self.assertEqual(accepted["status"], "RESERVED_ONLY")
            self.assertEqual(accepted["ownerEpoch"], 1)
            duplicate = clock.send(op="reserve", alarmId=1,
                                   expectedDueMs=due_ms(),
                                   sourceDigest=snapshot["sourceDigest"])
            self.assertFalse(duplicate["ok"])
            self.assertEqual(duplicate["reason"], "OCCURRENCE_ALREADY_RESERVED")
            # Updating an alarm note changes file bytes, but not the
            # occurrence identity: note edits cannot make the same alarm ring twice.
            self.document["alarms"][0]["note"] = "Changed private note"
            self.write_alarm()
            stale = clock.send(op="reserve", alarmId=1, expectedDueMs=due_ms(),
                               sourceDigest=snapshot["sourceDigest"])
            self.assertEqual(stale["reason"], "STALE_ALARM_FILE_REVISION")
            new_digest = clock.send(op="snapshot")["sourceDigest"]
            self.assertNotEqual(new_digest, snapshot["sourceDigest"])
            second = clock.send(op="reserve", alarmId=1, expectedDueMs=due_ms(),
                                sourceDigest=new_digest)
            self.assertEqual(second["reason"], "OCCURRENCE_ALREADY_RESERVED")
            assert "Private alarm title" not in str(snapshot)
            assert "Secret alarm notes" not in str(snapshot)
            self.assertTrue(clock.send(op="release")["ok"])
            saved = (self.state / "gate-v1.json").read_text()
            self.assertNotIn("Private alarm title", saved)
            self.assertNotIn("Secret alarm notes", saved)
        finally:
            clock.close()

    def test_disconnect_releases_session_without_production_actuation(self):
        first = self.hello("quickshell")
        self.assertTrue(first.send(op="acquire")["ok"])
        first.close()
        # The broker notices EOF and releases the lease. Poll until the
        # thread exits instead of assuming socket close is instantaneous.
        other = self.hello("background")
        try:
            for _ in range(60):
                response = other.send(op="acquire")
                if response["ok"]:
                    break
                self.assertEqual(response["reason"], "OWNER_ALREADY_ACTIVE")
                time.sleep(.025)
            self.assertTrue(response["ok"], response)
            self.assertEqual(response["epoch"], 2)
            self.assertTrue(other.send(op="release")["released"])
        finally:
            other.close()

    def test_bad_schema_and_rejected_wrong_source_no_claim(self):
        client = self.hello("quickshell")
        try:
            self.assertEqual(client.send(op="reserve", alarmId=1, expectedDueMs=due_ms(),
                                         sourceDigest="a"*64)["reason"], "NO_LIVE_OWNER_SESSION")
            self.assertEqual(client.send(op="acquire", evil=True)["reason"],
                             "INVALID_REQUEST_FIELDS")
            self.assertTrue(client.send(op="acquire")["ok"])
            self.assertEqual(client.send(op="reserve", alarmId=True, expectedDueMs=due_ms(),
                                         sourceDigest="a"*64)["reason"], "INVALID_OCCURRENCE_REQUEST")
            self.document["alarms"][0]["enabled"] = False
            self.write_alarm()
            digest = client.send(op="snapshot")["sourceDigest"]
            self.assertEqual(client.send(op="reserve", alarmId=1, expectedDueMs=due_ms(),
                                         sourceDigest=digest)["reason"], "OCCURRENCE_NOT_ELIGIBLE")
            self.assertEqual(json.loads((self.state / "gate-v1.json").read_text())["claims"], {})
            self.assertTrue(client.send(op="release")["ok"])
        finally:
            client.close()

    def test_untrusted_socket_path_refusal_does_not_unlink_existing_socket(self):
        # A second broker must not replace the existing active socket.
        cmd = [sys.executable, "-I", "-B", str(BROKER), "--serve-synthetic",
               "--alarm-file", str(self.alarm), "--state-dir", str(self.state),
               "--socket", str(self.sock), "--synthetic-now-ms", str(self.now)]
        result = subprocess.run(cmd, env=self.env, capture_output=True,
                                text=True, timeout=5)
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["state"], "REFUSED")
        self.assertEqual(report["reason"], "SOCKET_ALREADY_EXISTS")
        self.assertTrue(self.sock.is_socket())
        alive = self.hello("quickshell")
        self.assertTrue(alive.send(op="snapshot")["ok"])
        alive.close()

    def test_no_live_quickshell_or_background_actuation(self):
        source = BROKER.read_text(encoding="utf-8")
        qml = SHELL.read_text(encoding="utf-8")
        observer = OBSERVER.read_text(encoding="utf-8")
        docs = DOC.read_text(encoding="utf-8")
        self.assertIn("--serve-synthetic", source)
        self.assertIn("socket.SO_PEERCRED", source)
        self.assertIn("_peer_start_ticks(", source)
        self.assertIn("STALE_ALARM_FILE_REVISION", source)
        self.assertIn("OCCURRENCE_NOT_ELIGIBLE", source)
        self.assertIn("OCCURRENCE_ALREADY_RESERVED", source)
        self.assertIn("actuationEnabled", source)
        self.assertNotIn("notify-send", source)
        self.assertNotIn("SoundEffect", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("AlarmOwnershipBroker", qml)
        self.assertNotIn("AlarmOwnershipBroker", observer)
        self.assertIn("synthetic", docs.lower())
        self.assertIn("not authenticated", docs.lower())


if __name__ == "__main__":
    unittest.main()
