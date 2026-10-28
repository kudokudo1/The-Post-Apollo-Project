#!/usr/bin/env python3
"""M11v disposable Linux interpreter/PIDFD/session correlation regressions."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "tests/tasks/fixtures"
PATH = BASE / "TaskInterpreterProcessProbeM11v.py"
spec = importlib.util.spec_from_file_location("m11v_bound_probe", PATH)
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)

CODE = """# M11U SYNTHETIC HOST ONLY
import json, secrets, sys
request = json.loads(sys.stdin.readline())
session = secrets.token_hex(24)
print(json.dumps({"protocol":1, "kind":"hello", "sessionId":session}), flush=True)
reply = {"protocol":1, "kind":"reply", "sessionId":session,
         "requestId":request["requestId"], "epoch":request["epoch"],
         "challenge":request["challenge"], "status":"M11V_SYNTHETIC_PING"}
print(json.dumps(reply), flush=True)
"""

def pin_from_explicit_test_fixture():
    # This computes a digest from the same CI interpreter. For functional
    # tests ONLY: NOT a separately trusted supply-chain trust anchor.
    path = probe.INTERPRETER.resolve(strict=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SyntheticBoundProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.interpreter_hash = pin_from_explicit_test_fixture()
        cls.pinned = probe.pinned_interpreter(cls.interpreter_hash)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name) / "m11u-host-copy"
        self.directory.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self, source=CODE):
        script = self.directory / "synthetic-host.py"
        data = source.encode()
        script.write_bytes(data)
        script.chmod(0o600)
        # Trusted in TEST scope only, not from any live task or host install.
        return probe.capsule.capture_synthetic_script(
            self.directory, hashlib.sha256(data).hexdigest())

    def test_one_kernel_observed_child_and_one_session_exchange(self):
        out = probe.run_bound_synthetic(self.snapshot(), self.pinned)
        self.assertEqual(out, {
            "status":"SYNTHETIC_PROCESS_BOUND",
            "syntheticOnly":True,
            "realTaskWriterAuthorized":False,
            "interpreterPinMatches":True,
            "kernelExecutableMatches":True,
            "pidfdWasOpened":True,
            "sessionRequestMatched":True,
        })

    def test_bad_interpreter_pin_refuses_before_launch(self):
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "INTERPRETER_DIGEST_MISMATCH"):
            probe.pinned_interpreter("0" * 64)
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "INTERPRETER_PIN_REQUIRED"):
            probe.pinned_interpreter("bad")
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "INTERPRETER_DIGEST_MISMATCH"):
            probe.run_bound_synthetic(self.snapshot(),
                                      replace(self.pinned, digest="0" * 64))

    def test_non_system_interpreter_is_never_accepted(self):
        fake = Path(self.temp.name) / "python3"
        fake.write_text("#!/bin/sh\nexit 0\n")
        fake.chmod(0o755)
        with patch.object(probe,"INTERPRETER",fake):
            with self.assertRaisesRegex(probe.ProcessRefusal,
                                        "SYSTEM_INTERPRETER_REQUIRED"):
                probe.pinned_interpreter(self.interpreter_hash)

    def test_kernel_executable_mismatch_revokes_before_request(self):
        with patch.object(probe, "_observed_executable_identity",
                          return_value=(-1,-1)):
            with self.assertRaisesRegex(probe.ProcessRefusal,
                                        "SYNTHETIC_CHILD_EXECUTABLE_MISMATCH"):
                probe.run_bound_synthetic(self.snapshot(), self.pinned)

    def test_epoch_mismatch_rejected(self):
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "INVALID_SYNTHETIC_OWNER_EPOCH"):
            probe.run_bound_synthetic(self.snapshot(), self.pinned,
                                      expected_epoch=8)
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "INVALID_SYNTHETIC_OWNER_EPOCH"):
            probe.run_bound_synthetic(self.snapshot(), self.pinned,
                                      expected_epoch=True)

    def test_wrong_session_or_challenge_refused(self):
        wrong = CODE.replace(
            '"challenge":request["challenge"]',
            '"challenge":"0" * 48')
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "SYNTHETIC_SESSION_REPLY_REFUSED"):
            probe.run_bound_synthetic(self.snapshot(wrong), self.pinned)

        wrong_session = CODE.replace(
            '"sessionId":session,\n         "requestId"',
            '"sessionId":"f" * 48,\n         "requestId"')
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "SYNTHETIC_SESSION_REPLY_REFUSED"):
            probe.run_bound_synthetic(self.snapshot(wrong_session),self.pinned)

    def test_forged_or_duplicate_stdout_refused(self):
        fake = CODE.replace('"status":"M11V_SYNTHETIC_PING"',
                            '"status":"NOT_AN_AUTHORITY"')
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "SYNTHETIC_SESSION_REPLY_REFUSED"):
            probe.run_bound_synthetic(self.snapshot(fake), self.pinned)
        extra = CODE + 'print("EXTRA", flush=True)\n'
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "SYNTHETIC_REPLY_FRAMING_REFUSED"):
            probe.run_bound_synthetic(self.snapshot(extra), self.pinned)

    def test_child_exit_no_reply_is_refused(self):
        dead = "# M11U SYNTHETIC HOST ONLY\nraise SystemExit(1)\n"
        with self.assertRaisesRegex(probe.ProcessRefusal,
                                    "SYNTHETIC_PROCESS_UNAVAILABLE|SYNTHETIC_CHILD_OUTPUT_REFUSED|SYNTHETIC_CHILD_EXITED"):
            probe.run_bound_synthetic(self.snapshot(dead), self.pinned)

    def test_environment_poisoning_does_not_select_python_from_path(self):
        script = self.snapshot()
        with patch.dict(os.environ,
                        {"PATH":str(self.directory),"PYTHONHOME":str(self.directory),
                         "PYTHONPATH":str(self.directory)}):
            self.assertEqual(
                probe.run_bound_synthetic(script, self.pinned)["status"],
                "SYNTHETIC_PROCESS_BOUND")

    def test_no_live_task_or_quickshell_mount(self):
        src = PATH.read_text()
        store=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        shell=(ROOT/"shell.qml").read_text()
        for name in ("apollo-hub-todo-v1.json", "Quickshell.dataDir",
                     "TaskJsonGateCandidateM11l", "TaskJsonGateTransportM11m"):
            self.assertNotIn(name, src)
        self.assertNotIn("TaskInterpreterProcessProbeM11v",store+shell)
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      store)
        self.assertEqual(store.count("FileView {"),1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
