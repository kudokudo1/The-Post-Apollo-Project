#!/usr/bin/env python3
"""M11w synthetic OS child / disposable journal owner lifecycle acceptance.

All mutable files live in TemporaryDirectory and use M11l's strict
m11l-tasks-copy path. No Fedora user TASKS JSON, QML or production host.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
FILES = ROOT / "tests/tasks/fixtures"
CHILD = FILES / "TaskBoundJournalChildM11w.py"
DRIVER = FILES / "TaskBoundJournalProbeM11w.py"

spec = importlib.util.spec_from_file_location("m11w_test_probe", DRIVER)
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


def fixture_doc():
    return {
        "version": 3, "nextId": 2, "nextProjectId": 1,
        "projects": [], "tasks": [
            {"id": "t1", "title": "M11W_TEST_0", "done": False,
             "createdAtMs": 1000, "updatedAtMs": 1000,
             "priority": "none", "description": "", "dueDate": None,
             "projectId": None}
        ]
    }


def explicit_synthetic_interpreter_pin():
    # Functional CI test only: hash taken from same environment, NOT a
    # separately trusted production provenance / distribution channel.
    return hashlib.sha256(
        probe.m11v.INTERPRETER.resolve(strict=True).read_bytes()).hexdigest()


class BoundJournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.interpreter = probe.m11v.pinned_interpreter(
            explicit_synthetic_interpreter_pin())
        cls.owner_digest = hashlib.sha256(probe.M11L.read_bytes()).hexdigest()
        cls.owner_code = probe.pinned_owner_bytes(cls.owner_digest)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.code_folder = root / "m11u-host-copy"
        self.code_folder.mkdir(mode=0o700)
        self.code_path = self.code_folder / "synthetic-host.py"
        self.folder = root / "m11l-tasks-copy"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "todo-copy.json"
        self.source.write_text(json.dumps(fixture_doc(), indent=2) + "\n")
        self.source.chmod(0o600)
        self.original = self.source.read_bytes()
        self.clients = []

    def tearDown(self):
        for client in reversed(self.clients):
            client.close()
        self.temp.cleanup()

    def snapshot(self, raw=None):
        data = CHILD.read_bytes() if raw is None else raw
        self.code_path.write_bytes(data)
        self.code_path.chmod(0o600)
        return probe.m11v.capsule.capture_synthetic_script(
            self.code_folder, hashlib.sha256(data).hexdigest())

    def attach(self, mode, *, snapshot=None, owner_code=None):
        client = probe.attach_synthetic(
            self.folder, mode, snapshot or self.snapshot(),
            self.interpreter,
            self.owner_code if owner_code is None else owner_code)
        self.clients.append(client)
        return client

    def history(self):
        uri = "file:" + str(self.folder / "gate-review.db") + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as db:
            rows = db.execute(
                "SELECT stage_id,epoch,state FROM stage_history").fetchall()
        return rows

    def test_bootstrap_process_session_and_durable_owner_same(self):
        client = self.attach("NEW")
        row = probe.durable_row(self.folder)
        self.assertEqual(client.phase, "JSON_ACTIVE")
        self.assertEqual(client.epoch, 0)
        self.assertEqual(row["writer"], "m11w-" + client.session)
        self.assertEqual(row["phase"], "JSON_ACTIVE")
        self.assertEqual(client.send("status")["pending"], False)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(self.history(), [])

    def test_lifetime_flock_refuses_second_disposable_owner(self):
        client = self.attach("NEW")
        self.assertEqual(client.send("status")["phase"], "JSON_ACTIVE")
        owner_module_spec = importlib.util.spec_from_file_location(
            "m11w_parent_lock_contender", probe.M11L)
        owner_module = importlib.util.module_from_spec(owner_module_spec)
        owner_module_spec.loader.exec_module(owner_module)
        with self.assertRaisesRegex(owner_module.GateError, "LOCK_CONTENDED"):
            owner_module.CandidateOwner(
                self.folder,"m11w-lock-contender-test",bootstrap=False)
        self.assertEqual(probe.durable_row(self.folder)["writer"],
                         "m11w-"+client.session)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_interrupted_reservation_and_fresh_owner_quarantine(self):
        original_owner = self.attach("NEW")
        accepted = original_owner.send("reserve")
        self.assertIs(accepted["pending"], True)
        self.assertEqual(accepted["phase"], "JSON_ACTIVE")
        previous_session = original_owner.session
        before = probe.durable_row(self.folder)
        self.assertEqual(before["writer"], "m11w-"+previous_session)
        self.assertEqual(before["epoch"], 0)
        self.assertIsNotNone(before["pending_stage"])
        hist = self.history()
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0][0], before["pending_stage"])
        self.assertEqual(hist[0][1:], (0, "RESERVED"))
        self.assertEqual(self.source.read_bytes(), self.original)
        backup = self.folder / "source-before-gate.bak"
        self.assertEqual(backup.read_bytes(), self.original)

        original_owner.close()  # Abruptly kill process with pending stage.
        new_owner = self.attach("EXISTING")
        self.assertNotEqual(new_owner.session, previous_session)
        self.assertEqual(new_owner.epoch, 1)
        self.assertEqual(new_owner.phase, "RECOVERY_REVIEW")
        self.assertEqual(new_owner.send("status")["pending"], True)
        self.assertEqual(new_owner.send("reserve"),
                         {"protocol":1,"kind":"refused",
                          "status":"RECOVERY_REVIEW_REQUIRED",
                          "sessionId":new_owner.session,"requestId":2})
        after = probe.durable_row(self.folder)
        self.assertEqual(after["writer"],"m11w-"+new_owner.session)
        self.assertEqual(after["phase"],"RECOVERY_REVIEW")
        self.assertEqual(after["epoch"],1)
        self.assertEqual(after["pending_stage"],before["pending_stage"])
        self.assertEqual(self.history(), hist)
        self.assertEqual(backup.read_bytes(),self.original)
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_wrong_session_or_epoch_refuses_and_preserves_journal(self):
        client=self.attach("NEW")
        self.assertEqual(client.send("status",override_session="f"*48),
                         {"protocol":1,"kind":"refused",
                          "status":"STALE_OR_INVALID_SESSION"})
        row=probe.durable_row(self.folder)
        self.assertIsNone(row["pending_stage"])
        self.assertEqual(self.history(),[])
        self.assertEqual(self.source.read_bytes(),self.original)

        client.close()
        fresh=self.attach("EXISTING")
        self.assertEqual(fresh.phase,"RECOVERY_REVIEW")
        self.assertEqual(fresh.send("status",epoch=0),
                         {"protocol":1,"kind":"refused",
                          "status":"STALE_OR_INVALID_SESSION"})
        self.assertEqual(self.history(),[])
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_altered_executable_identity_prevents_attaching(self):
        with patch.object(probe.m11v, "_observed_executable_identity",
                          return_value=(-1,-1)):
            with self.assertRaisesRegex(probe.SyntheticOwnerRefusal,
                                        "SYNTHETIC_ATTACH_REFUSED"):
                self.attach("NEW")
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_fake_hello_session_cannot_match_durable_writer(self):
        untrusted = CHILD.read_text().replace(
            '"sessionId": session,',
            '"sessionId": "f" * 48,',1).encode()
        with self.assertRaisesRegex(probe.SyntheticOwnerRefusal,
                                    "SYNTHETIC_ATTACH_REFUSED"):
            self.attach("NEW",snapshot=self.snapshot(untrusted))
        self.assertEqual(self.source.read_bytes(),self.original)

    def test_wrong_owner_module_pin_and_mutated_code_are_refused(self):
        with self.assertRaisesRegex(probe.SyntheticOwnerRefusal,
                                    "OWNER_SOURCE_DIGEST_MISMATCH"):
            probe.pinned_owner_bytes("0"*64)
        with self.assertRaisesRegex(probe.SyntheticOwnerRefusal,
                                    "OWNER_SOURCE_PIN_REQUIRED"):
            probe.pinned_owner_bytes("unknown")
        broken = self.owner_code.replace(
            b"class CandidateOwner:", b"class BrokenOwner:",1)
        with self.assertRaisesRegex(probe.SyntheticOwnerRefusal,
                                    "SYNTHETIC_ATTACH_REFUSED"):
            self.attach("NEW",owner_code=broken)

    def test_no_wrong_task_file_and_no_production_integration(self):
        child=CHILD.read_text()
        driver=DRIVER.read_text()
        store=(ROOT/"services/hub/ApolloHubTodoStore.qml").read_text()
        shell=(ROOT/"shell.qml").read_text()
        for forbidden in ("apollo-hub-todo-v1.json","Quickshell.dataDir",
                          "ApolloHubTodoStore.qml"):
            self.assertNotIn(forbidden,child+driver)
        self.assertIn("readonly property bool guardedWriterEnabled: false",
                      store)
        self.assertNotIn("TaskBoundJournalProbeM11w",store+shell)
        self.assertNotIn("TaskBoundJournalChildM11w",store+shell)
        self.assertEqual(store.count("FileView {"),1)
        bad=Path(self.temp.name)
        with self.assertRaisesRegex(probe.SyntheticOwnerRefusal,
                                    "SYNTHETIC_ATTACH_SCOPE_REQUIRED"):
            probe.attach_synthetic(bad,"NEW",self.snapshot(),
                                   self.interpreter,self.owner_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
