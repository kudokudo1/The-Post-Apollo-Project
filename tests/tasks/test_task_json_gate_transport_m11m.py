#!/usr/bin/env python3
"""M11m subprocess transport tests use only private disposable TASKS copies."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "tests/tasks/fixtures/TaskJsonGateTransportM11m.py"


def task_copy(n=0):
    return {
        "version": 3, "nextId": 2, "nextProjectId": 1,
        "projects": [], "tasks": [{
            "id": "t1", "title": "M11M_TEST_" + str(n), "done": False,
            "createdAtMs": 1000, "updatedAtMs": 1000 + n,
            "priority": "none", "description": "", "dueDate": None,
            "projectId": None
        }]
    }


def raw(n):
    return json.dumps(task_copy(n), sort_keys=True, indent=2) + "\n"


def write_exclusive(path, content):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, content.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "m11l-tasks-copy"
        self.folder.mkdir(mode=0o700)
        self.path = self.folder / "todo-copy.json"
        write_exclusive(self.path, raw(0))
        self.procs = []

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
            if proc.stdin is not None and proc.stdin.closed:
                proc.stdin = None
            proc.communicate(timeout=5)
        self.temp.cleanup()

    def start(self, bootstrap=False, directory=None):
        cmd = [sys.executable, "-B", "-I", str(HOST),
               "--directory", str(directory or self.folder),
               "--writer-id", "m11m-test-owner-0001"]
        if bootstrap:
            cmd.append("--bootstrap-test")
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                bufsize=0)
        self.procs.append(proc)
        hello = json.loads(proc.stdout.readline())
        self.assertFalse(hello["liveWriterAuthorized"])
        self.assertFalse(hello["sqliteWriteAuthorized"])
        self.assertFalse(hello["migrationAuthorized"])
        self.assertFalse(hello["remoteWriteAuthorized"])
        return proc, hello

    def send(self, proc, body):
        proc.stdin.write((json.dumps(body) + "\n").encode())
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    def replace(self, content):
        target = self.folder / "staged-atomic.json"
        write_exclusive(target, content)
        os.replace(target, self.path)

    def test_reserve_native_simulation_verify_freeze_and_restart(self):
        proc, hello = self.start(bootstrap=True)
        self.assertTrue(hello["ok"])
        self.assertEqual(hello["phase"], "JSON_ACTIVE")
        self.assertEqual(hello["requestId"], 0)
        self.assertEqual(self.path.read_text(), raw(0))
        reserve = self.send(proc, {"requestId":1,"kind":"reserve",
                                  "stageId":"m11m-test-stage-001",
                                  "candidateText":raw(1)})
        self.assertTrue(reserve["ok"])
        self.assertTrue(reserve["pending"])
        self.assertEqual(reserve["stageId"], "m11m-test-stage-001")
        self.assertEqual(self.path.read_text(), raw(0)) # Host cannot write file
        self.replace(raw(1))                          # External FileView simulation
        settled = self.send(proc, {"requestId":2,"kind":"verify",
                                   "stageId":"m11m-test-stage-001",
                                   "expectedEpoch":reserve["epoch"]})
        self.assertTrue(settled["ok"])
        self.assertFalse(settled["pending"])
        self.assertEqual(self.path.read_text(), raw(1))
        freeze = self.send(proc, {"requestId":3,"kind":"freeze",
                                  "expectedEpoch":settled["epoch"]})
        self.assertTrue(freeze["ok"])
        self.assertEqual(freeze["phase"], "JSON_QUIESCED")
        proc.stdin.close()
        self.assertEqual(proc.wait(timeout=5), 0)
        another, hello2 = self.start()
        self.assertTrue(hello2["ok"])
        self.assertEqual(hello2["phase"], "RECOVERY_REVIEW")
        self.assertEqual(hello2["epoch"], 2)
        refused = self.send(another, {"requestId":1,"kind":"reserve",
                                      "stageId":"m11m-test-stage-002",
                                      "candidateText":raw(2)})
        self.assertFalse(refused["ok"])
        self.assertEqual(another.wait(timeout=5), 2)
        self.assertEqual(self.path.read_text(), raw(1))
        self.assertEqual((self.folder / "source-before-gate.bak").read_text(),raw(0))

    def test_wrong_readback_enters_unsettled_review_on_restart(self):
        proc, _ = self.start(bootstrap=True)
        result = self.send(proc, {"requestId":1,"kind":"reserve",
                                  "stageId":"m11m-test-stage-003",
                                  "candidateText":raw(1)})
        self.assertTrue(result["ok"])
        # Deliberate mismatch simulating FileView writing different valid bytes.
        self.replace(raw(9))
        refused = self.send(proc, {"requestId":2,"kind":"verify",
                                   "stageId":"m11m-test-stage-003",
                                   "expectedEpoch":0})
        self.assertFalse(refused["ok"])
        self.assertEqual(proc.wait(timeout=5),2)
        _, reopened = self.start()
        self.assertEqual(reopened["phase"],"RECOVERY_REVIEW")
        self.assertTrue(reopened["pending"])

    def test_invalid_traffic_does_not_touch_source(self):
        proc, _ = self.start(bootstrap=True)
        reply = self.send(proc, {"requestId":1,"kind":"reserve",
                                 "stageId":"bad",
                                 "candidateText":raw(1)})
        self.assertFalse(reply["ok"])
        self.assertEqual(proc.wait(timeout=5),2)
        self.assertEqual(self.path.read_text(),raw(0))

    def test_duplicate_protocol_keys_are_rejected(self):
        proc, _ = self.start(bootstrap=True)
        proc.stdin.write(b'{"requestId":1,"requestId":1,"kind":"status"}\n')
        proc.stdin.flush()
        reply = json.loads(proc.stdout.readline())
        self.assertFalse(reply["ok"])
        self.assertEqual(proc.wait(timeout=5),2)

    def test_lock_conflict_and_missing_directory(self):
        first, hello = self.start(bootstrap=True)
        self.assertTrue(hello["ok"])
        second, deny = self.start()
        self.assertFalse(deny["ok"])
        self.assertEqual(second.wait(timeout=5),2)
        self.assertIsNone(first.poll())
        invalid_folder = Path(self.temp.name) / "other-folder"
        invalid_folder.mkdir(mode=0o700)
        third, deny = self.start(directory=invalid_folder)
        self.assertFalse(deny["ok"])
        self.assertEqual(third.wait(timeout=5),2)
        self.assertEqual(self.path.read_text(),raw(0))

    def test_one_time_private_seed_refuses_overwrite(self):
        import importlib.util
        seed_path = ROOT / "tests/tasks/fixtures/TaskJsonGateSeedM11m.py"
        spec = importlib.util.spec_from_file_location("m11m_private_seed", seed_path)
        seed_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seed_mod)
        parent = Path(self.temp.name) / "fresh-private-parent"
        parent.mkdir(mode=0o700)
        created = seed_mod.seed(parent)
        self.assertEqual(created.parent.name, "m11l-tasks-copy")
        self.assertEqual(created.name, "todo-copy.json")
        self.assertEqual(json.loads(created.read_text())["tasks"][0]["title"],
                         "M11M_TEST_0")
        with self.assertRaises(ValueError):
            seed_mod.seed(parent)
        self.assertEqual(json.loads(created.read_text())["tasks"][0]["title"],
                         "M11M_TEST_0")

    def test_freeze_before_settlement_closes_transport(self):
        proc, _ = self.start(bootstrap=True)
        reserved = self.send(proc, {"requestId":1,"kind":"reserve",
                                    "stageId":"m11m-test-stage-freeze",
                                    "candidateText":raw(1)})
        self.assertTrue(reserved["ok"])
        refused = self.send(proc, {"requestId":2,"kind":"freeze",
                                   "expectedEpoch":reserved["epoch"]})
        self.assertFalse(refused["ok"])
        self.assertEqual(proc.wait(timeout=5), 2)
        _, next_hello = self.start()
        self.assertEqual(next_hello["phase"], "RECOVERY_REVIEW")
        self.assertTrue(next_hello["pending"])

    def test_qml_bridge_is_unmounted_and_defers_native_reload(self):
        path = ROOT / "services/projects/TaskJsonGateHostBridgeM11m.qml"
        bridge = path.read_text()
        shell = (ROOT / "shell.qml").read_text()
        store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text()
        assert "Qt.callLater(function()" in bridge
        assert "fixtureFile.reload();" in bridge
        assert "pendingStageId === savedStageId" in bridge
        assert "fixtureFile.setText(pendingRaw);" in bridge
        assert 'bridge.send("verify", {stageId:bridge.pendingStageId})' in bridge
        assert "TaskJsonGateTransportM11m.py" in bridge
        assert "m11l-tasks-copy/todo-copy.json" in bridge
        assert "liveWriterAuthorized: false" in bridge
        assert "productionActivation: false" in bridge
        assert "TaskJsonGateHostBridgeM11m" not in shell + store
        assert "TaskJsonGateTransportM11m.py" not in shell + store
        assert "readonly property bool guardedWriterEnabled: false" in store
        assert store.count("FileView {") == 1
        assert store.count("todoFile.setText(") == 1
        window = (ROOT / "TaskJsonGateHarnessM11m.qml").read_text()
        assert "WlrKeyboardFocus.OnDemand" in window
        assert "TaskJsonGateHostBridgeM11m {" in window


if __name__ == "__main__":
    unittest.main(verbosity=2)
