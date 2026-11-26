"""Hunter birth identity regression. Only ever targets children created here."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXECUTOR = (ROOT / "services/system/HunterExecutor.qml").read_text()
CONTROLLER = (ROOT / "widgets/appcontrol/HunterOperationController.qml").read_text()
SCRIPT = json.loads(re.search(
    r'function script\(\)\s*\{\s*return ("(?:\\.|[^"\\])*");', EXECUTOR
).group(1))


def identity(pid):
    stat = Path(f"/proc/{pid}/stat").read_text()
    first, last = stat.index("("), stat.rindex(")")
    return {"pid": pid, "name": stat[first + 1:last],
            "startTicks": int(stat[last + 2:].split()[19])}


def execute(targets):
    proc = subprocess.run([sys.executable, "-c", SCRIPT, json.dumps(targets)],
                          capture_output=True, text=True, check=True, timeout=8)
    return [json.loads(line) for line in proc.stdout.splitlines()]


class HunterBirthIdentity(unittest.TestCase):
    def setUp(self):
        if os.environ.get("POST_APOLLO_HUNTER_DISPOSABLE_CI") != "1":
            self.skipTest("disposable CI only")
        if not hasattr(os, "pidfd_open"):
            self.fail("native pidfd is required")
        self.child = subprocess.Popen([sys.executable, "-c",
                                       "import time; time.sleep(60)"])
        self.addCleanup(self.cleanup_child)
        self.target = identity(self.child.pid)

    def cleanup_child(self):
        if self.child.poll() is None:
            self.child.terminate()
        self.child.wait(timeout=5)

    def test_invalid_capture_cannot_signal(self):
        for target in ({**self.target, "startTicks": 0},
                       {**self.target, "startTicks": self.target["startTicks"] + 1},
                       {**self.target, "name": "not-the-captured-name"}):
            output = execute([target])
            self.assertIn(output[0]["status"], ("escaped", "gone"))
            self.assertIsNone(self.child.poll(), "stale request changed a live child")

    def test_exact_capture_signals_once_and_observes_exit(self):
        output = execute([self.target, self.target])
        self.assertEqual(len([row for row in output if row["type"] == "result"]), 1)
        self.assertEqual(output[0]["status"], "killed")
        self.assertIn("EXIT OBSERVED", output[0]["detail"])
        self.assertEqual(self.child.wait(timeout=5), -15)

    def test_capture_and_signal_path_are_exact(self):
        self.assertIn("startTicks: Number(entry.startTicks || 0)", CONTROLLER)
        self.assertIn("os.pidfd_open(pid)", SCRIPT)
        self.assertIn("signal.pidfd_send_signal(fd, signal.SIGTERM)", SCRIPT)
        self.assertNotIn("os.kill(", SCRIPT)
        self.assertIn("ticks != born", SCRIPT)


if __name__ == "__main__":
    unittest.main(verbosity=2)
