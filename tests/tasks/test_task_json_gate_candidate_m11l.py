#!/usr/bin/env python3
"""M11l disposable real TASKS schema fixture and fail-closed owner tests."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
spec = importlib.util.spec_from_file_location("task_json_gate_candidate", HOST)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def document(version=3, *, label="Example"):
    row = {"id":"t1","title":label,"done":False,
           "createdAtMs":1000,"updatedAtMs":1000}
    payload = {"version":version,"nextId":2,"tasks":[row]}
    if version >= 2:
        row.update(priority="none",description="",dueDate=None)
    if version == 3:
        row["projectId"] = "p1"
        payload["nextProjectId"] = 2
        payload["projects"] = [{"id":"p1","name":"Example project",
                                "createdAtMs":900,"updatedAtMs":900}]
    return payload


def raw(doc):
    return (json.dumps(doc, ensure_ascii=True, separators=(",",":"))+"\n").encode()


def write(path, data):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600),
                   "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_fileview_simulation(path, data):
    replacement = path.parent / "atomic-next.json"
    write(replacement, data)
    os.replace(replacement, path)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "m11l-tasks-copy"
        self.root.mkdir(mode=0o700)
        self.source = self.root / "todo-copy.json"
        self.initial = raw(document())
        write(self.source, self.initial)
        self.writer = "m11l-test-writer-0001"

    def tearDown(self):
        self.temp.cleanup()

    def owner(self, bootstrap=False):
        return mod.CandidateOwner(self.root, self.writer, bootstrap=bootstrap)

    def assertCode(self, code, call):
        with self.assertRaises(mod.GateError) as ctx:
            call()
        self.assertEqual(str(ctx.exception), code)

    def test_two_saves_and_frozen_reopen(self):
        with self.owner(bootstrap=True) as owner:
            snapshot = owner.state()
            self.assertEqual(snapshot["phase"], "JSON_ACTIVE")
            self.assertFalse(snapshot["liveWriterAuthorized"])
            self.assertEqual((self.root/"source-before-gate.bak").read_bytes(),
                             self.initial)
            next1 = raw(document(label="First confirmed"))
            reservation = owner.reserve("m11l-stage-0001", next1)
            self.assertFalse(reservation["liveWriterAuthorized"])
            self.assertEqual(reservation["epoch"], 0)
            self.assertCode("READBACK_MISMATCH",
                            lambda: owner.verify("m11l-stage-0001", 0))
            self.assertCode("STAGE_NOT_ADMISSIBLE",
                            lambda: owner.reserve("m11l-stage-0002", next1))
            atomic_fileview_simulation(self.source, next1)
            self.assertTrue(owner.verify("m11l-stage-0001", 0)["settled"])
            self.assertFalse(owner.state()["pending"])
            next2 = raw(document(label="Second confirmed"))
            owner.reserve("m11l-stage-0002", next2)
            self.assertCode("FREEZE_REFUSED", lambda: owner.freeze(0))
            atomic_fileview_simulation(self.source, next2)
            self.assertTrue(owner.verify("m11l-stage-0002", 0)["settled"])
            frozen = owner.freeze(0)
            self.assertEqual(frozen["phase"], "JSON_QUIESCED")
            self.assertCode("STAGE_NOT_ADMISSIBLE",
                            lambda: owner.reserve("m11l-stage-0003", next1))
        with self.owner() as later:
            self.assertEqual(later.state()["phase"], "RECOVERY_REVIEW")
            self.assertEqual(later.state()["epoch"], 2)
            self.assertCode("STAGE_NOT_ADMISSIBLE",
                            lambda: later.reserve("m11l-stage-0004", next1))

    def test_pending_stage_restarts_into_review(self):
        with self.owner(bootstrap=True) as owner:
            owner.reserve("m11l-stage-pending", raw(document(label="Pending")))
            self.assertTrue(owner.state()["pending"])
        with self.owner() as later:
            self.assertEqual(later.state()["phase"], "RECOVERY_REVIEW")
            self.assertTrue(later.state()["pending"])
            self.assertCode("STAGE_NOT_ADMISSIBLE",
                            lambda: later.reserve("m11l-stage-after", raw(document(label="After"))))

    def test_lock_conflict_and_no_rebootstrap(self):
        with self.owner(bootstrap=True) as owner:
            self.assertCode("LOCK_CONTENDED", lambda: self.owner())
            self.assertCode("LOCK_CONTENDED", lambda: self.owner(bootstrap=True))
            self.assertFalse(owner.state()["sqliteWriteAuthorized"])
        self.assertCode("JOURNAL_ALREADY_EXISTS", lambda: self.owner(bootstrap=True))

    def test_external_source_change_is_not_admitted(self):
        with self.owner(bootstrap=True) as owner:
            external = raw(document(label="External"))
            atomic_fileview_simulation(self.source, external)
            self.assertCode("SOURCE_CHANGED_EXTERNALLY",
                            lambda: owner.reserve("m11l-stage-extern",
                                                  raw(document(label="Candidate"))))
            self.assertEqual(self.source.read_bytes(), external)

    def test_fixture_identity_and_missing_authority(self):
        self.assertCode("JOURNAL_MISSING", lambda: self.owner())
        bad_dir = self.root.parent / "not-the-disposable-copy"
        bad_dir.mkdir(mode=0o700)
        self.assertCode("DISPOSABLE_COPY_REQUIRED",
                        lambda: mod.CandidateOwner(bad_dir,self.writer))
        self.source.unlink()
        self.assertCode("SOURCE_UNAVAILABLE", lambda: self.owner(bootstrap=True))

    def test_task_schema_v1_v2_v3_and_rejections(self):
        for version in (1,2,3):
            self.assertEqual(mod.parse_task_document(raw(document(version)))["version"], version)
        invalid = document()
        invalid["version"] = 99
        self.assertCode("UNSUPPORTED_VERSION",
                        lambda: mod.parse_task_document(raw(invalid)))
        invalid = document()
        invalid["tasks"][0]["projectId"] = "p404"
        self.assertCode("INVALID_TASK_PROJECT",
                        lambda: mod.parse_task_document(raw(invalid)))
        invalid = document()
        invalid["tasks"][0]["dueDate"] = "2026-02-30"
        self.assertCode("INVALID_TASK_DETAILS",
                        lambda: mod.parse_task_document(raw(invalid)))
        self.assertCode("DUPLICATE_JSON_KEY",
                        lambda: mod.parse_task_document(b'{"version":3,"version":3}\n'))

    def test_readback_wrong_epoch_is_rejected(self):
        with self.owner(bootstrap=True) as owner:
            final = raw(document(label="Different"))
            owner.reserve("m11l-stage-stale", final)
            atomic_fileview_simulation(self.source, final)
            self.assertCode("STALE_STAGE",
                            lambda: owner.verify("m11l-stage-stale", 100))
            self.assertCode("STALE_STAGE",
                            lambda: owner.verify("m11l-stage-unknown", 0))
            self.assertTrue(owner.state()["pending"])
            owner.verify("m11l-stage-stale", 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
