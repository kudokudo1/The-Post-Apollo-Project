"""BG1-A synthetic cross-process owner fencing. Never a real alarm actuator."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "services/time/AlarmOwnershipGate.py"
OBS = ROOT / "services/time/AlarmBackgroundObserver.py"
OWNER = ROOT / "services/time/AlarmManagerService.qml"
UNIT = ROOT / "ops/systemd/user/post-apollo-alarm-observer.service"
spec = importlib.util.spec_from_file_location("clock_gate_bg1", SOURCE)
gate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate_module)
Refused = gate_module.Refused
OwnershipGate = gate_module.OwnershipGate
DIGEST = hashlib.sha256(b"2026-11-11-wednesday-0640").hexdigest()


class ClockOwnershipGateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        root = Path(self.folder.name)
        self.storage = root / "quickshell-id-1"
        self.storage.mkdir(mode=0o700)
        self.alarms = self.storage / "time-alarms-v2.json"
        self.alarms.write_text(json.dumps({"version": 2, "nextId": 2,
                                           "alarms": [{"id": 1, "name": "Private wakeup",
                                                       "note": "Secret personal note"}]}) + "\n")
        self.alarms.chmod(0o600)
        self.state = self.storage / "alarm-ownership-v1"
        self.gate = OwnershipGate(self.alarms, self.state)

    def assert_refuses(self, code, call):
        with self.assertRaises(Refused) as ctx:
            call()
        self.assertEqual(str(ctx.exception), code)

    def test_only_one_live_owner_and_fenced_epoch(self):
        a = self.gate.acquire("quickshell", ttl_ms=3000)
        self.assertEqual(a["epoch"], 1)
        self.assertFalse(a["actuationEnabled"])
        self.assertFalse(a["ownsAlarmFile"])
        self.assertEqual(self.gate.inspect()["ownerRole"], "quickshell")
        self.assert_refuses("OWNER_ALREADY_ACTIVE",
                            lambda: self.gate.acquire("background"))
        self.assert_refuses("STALE_OR_FOREIGN_OWNER",
                            lambda: self.gate.renew("background", a["token"]))
        self.assert_refuses("STALE_OR_FOREIGN_OWNER",
                            lambda: self.gate.renew("quickshell", "wrong"))
        renewed = self.gate.renew("quickshell", a["token"], ttl_ms=2500)
        self.assertEqual(renewed["epoch"], 1)
        self.assertFalse(renewed["actuationEnabled"])
        self.assertTrue(self.gate.release("quickshell", a["token"])["released"])
        b = self.gate.acquire("background", ttl_ms=2500)
        self.assertEqual(b["epoch"], 2)
        self.assert_refuses("STALE_OR_FOREIGN_OWNER",
                            lambda: self.gate.reserve("quickshell", a["token"], 1,
                                                      1794408000000, DIGEST))
        self.assertEqual(self.gate.inspect()["ownerRole"], "background")
        self.assert_refuses("OWNER_ALREADY_ACTIVE",
                            lambda: self.gate.acquire("quickshell"))
        self.gate.release("background", b["token"])

    def test_occurrence_reservation_survives_owner_handoff_and_restart(self):
        a = self.gate.acquire("quickshell")
        due = 1794408000000
        reserved = self.gate.reserve("quickshell", a["token"], 1, due, DIGEST)
        self.assertEqual(reserved["status"], "RESERVED_ONLY")
        self.assertFalse(reserved["actuationEnabled"])
        self.assertFalse(reserved["ownsAlarmFile"])
        self.assertEqual(self.gate.inspect()["claimCount"], 1)
        self.assert_refuses("OCCURRENCE_ALREADY_RESERVED",
                            lambda: self.gate.reserve("quickshell", a["token"], 1, due, DIGEST))
        self.gate.release("quickshell", a["token"])
        # Separate gate object models a process losing all in-memory state.
        fresh = OwnershipGate(self.alarms, self.state)
        b = fresh.acquire("background")
        self.assertEqual(b["epoch"], a["epoch"] + 1)
        self.assert_refuses("OCCURRENCE_ALREADY_RESERVED",
                            lambda: fresh.reserve("background", b["token"], 1, due, DIGEST))
        # A second scheduled occurrence is independently reservable.
        new_due = due + 7 * 24 * 60 * 60 * 1000
        n = fresh.reserve("background", b["token"], 1, new_due, DIGEST)
        self.assertNotEqual(n["claim"], reserved["claim"])
        self.assertEqual(fresh.inspect()["claimCount"], 2)
        fresh.release("background", b["token"])
        saved = json.loads((self.state / "gate-v1.json").read_text())
        self.assertEqual(saved["epoch"], 2)
        self.assertEqual(len(saved["claims"]), 2)
        self.assertNotIn(a["token"], (self.state / "gate-v1.json").read_text())
        self.assertNotIn("Private wakeup", (self.state / "gate-v1.json").read_text())
        self.assertNotIn("Secret personal note", (self.state / "gate-v1.json").read_text())

    def test_lease_expiry_is_not_renewable_or_actuating(self):
        a = self.gate.acquire("quickshell", ttl_ms=110)
        time.sleep(0.21)
        self.assert_refuses("STALE_OR_FOREIGN_OWNER",
                            lambda: self.gate.renew("quickshell", a["token"]))
        b = self.gate.acquire("background")
        self.assertEqual(b["epoch"], 2)
        self.gate.release("background", b["token"])

    def test_active_pid_blocks_competing_process_and_dead_pid_cannot_hold_authority(self):
        a = self.gate.acquire("quickshell", ttl_ms=5000)
        script = (
            "import sys,json;"
            f"sys.path.insert(0,{str(SOURCE.parent)!r});"
            "from AlarmOwnershipGate import OwnershipGate,Refused;"
            f"g=OwnershipGate({str(self.alarms)!r},{str(self.state)!r});"
            "\ntry: print(json.dumps(g.acquire('background')))\n"
            "except Refused as e: print('REFUSED='+str(e))\n"
        )
        proc = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("REFUSED=OWNER_ALREADY_ACTIVE", proc.stdout)
        self.gate.release("quickshell", a["token"])
        child = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(child.returncode, 0, child.stderr)
        foreign = json.loads(child.stdout)
        self.assertEqual(foreign["epoch"], 2)
        # The subprocess has exited. Even before lease expiry, its PID
        # identity is no longer alive, so a new owner can be admitted.
        c = self.gate.acquire("quickshell")
        self.assertEqual(c["epoch"], 3)
        self.assert_refuses("STALE_OR_FOREIGN_OWNER",
                            lambda: self.gate.renew("background", foreign["token"]))
        self.gate.release("quickshell", c["token"])

    def test_corrupted_state_wrong_scope_and_symlink_refuse_without_rewrite(self):
        a = self.gate.acquire("quickshell")
        self.gate.release("quickshell", a["token"])
        state_file = self.state / "gate-v1.json"
        before = state_file.read_bytes()
        different = self.storage.parent / "quickshell-id-2"
        different.mkdir(mode=0o700)
        other = different / "time-alarms-v2.json"
        other.write_bytes(self.alarms.read_bytes())
        another = OwnershipGate(other, self.state)
        self.assert_refuses("INVALID_GATE_STATE", another.inspect)
        self.assertEqual(state_file.read_bytes(), before)
        state_file.write_text('{"version":1,"scope":"forged"}')
        self.assert_refuses("INVALID_GATE_STATE",
                            lambda: self.gate.acquire("background"))
        self.assertEqual(state_file.read_text(), '{"version":1,"scope":"forged"}')
        state_file.unlink()
        state_file.symlink_to(self.alarms)
        self.assert_refuses("UNSAFE_GATE_STATE",
                            lambda: self.gate.acquire("quickshell"))
        self.assertTrue(state_file.is_symlink())

    def test_explicit_read_only_cli_never_creates_state_dir_or_actuates(self):
        self.assertFalse(self.state.exists())
        proc = subprocess.run([sys.executable, "-I", "-B", str(SOURCE),
                               "--inspect", "--alarm-file", str(self.alarms),
                               "--state-dir", str(self.state)],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 2)
        result = json.loads(proc.stdout)
        self.assertEqual(result["state"], "REFUSED")
        self.assertFalse(result["actuationEnabled"])
        self.assertFalse(self.state.exists())
        # Normal inspection remains safe and excludes the private lease token.
        a = self.gate.acquire("quickshell")
        read = subprocess.run([sys.executable, "-I", "-B", str(SOURCE),
                               "--inspect", "--alarm-file", str(self.alarms),
                               "--state-dir", str(self.state)],
                              capture_output=True, text=True, timeout=10)
        result = json.loads(read.stdout)
        self.assertEqual(read.returncode, 0)
        self.assertTrue(result["ownerValid"])
        self.assertFalse(result["actuationEnabled"])
        self.assertNotIn(a["token"], read.stdout)
        self.gate.release("quickshell", a["token"])

    def test_source_is_opt_in_and_does_not_modify_quickshell_or_alarms(self):
        source = SOURCE.read_text(encoding="utf-8")
        qml = OWNER.read_text(encoding="utf-8")
        obs = OBS.read_text(encoding="utf-8")
        unit = UNIT.read_text(encoding="utf-8")
        original = self.alarms.read_bytes()
        a = self.gate.acquire("quickshell")
        self.gate.reserve("quickshell", a["token"], 1, 1794408000000, DIGEST)
        self.gate.release("quickshell", a["token"])
        self.assertEqual(self.alarms.read_bytes(), original)
        self.assertIn("actuationEnabled", source)
        self.assertIn("RESERVED_ONLY", source)
        self.assertIn("fcntl.flock(fd, fcntl.LOCK_EX)", source)
        self.assertIn("os.replace(temporary, target)", source)
        self.assertIn("os.fsync(stream.fileno())", source)
        self.assertIn('parser.add_argument("--inspect", action="store_true", required=True)', source)
        self.assertNotIn("AlarmOwnershipGate", qml)
        self.assertNotIn("AlarmOwnershipGate", obs)
        self.assertNotIn("AlarmOwnershipGate", unit)
        self.assertNotIn("[Install]", unit)
        self.assertNotIn("notify-send", source)
        self.assertNotIn("SoundEffect", source)
        self.assertNotIn("subprocess.run(", source)
        self.assertNotIn("systemctl", source)

if __name__ == "__main__":
    unittest.main()
