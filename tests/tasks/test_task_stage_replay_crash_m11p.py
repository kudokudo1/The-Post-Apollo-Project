#!/usr/bin/env python3
"""M11p long-lived stage tombstones and abrupt process fault windows.

All data is fabricated, and every filesystem path is beneath a fresh private
TemporaryDirectory. Real TASKS or operator-local folders are never accessed.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = ROOT / "services/projects/TaskJsonGateCandidateM11l.py"
PROBE = ROOT / "tests/tasks/fixtures/task_stage_crash_probe_m11p.py"
spec = importlib.util.spec_from_file_location("m11p_owner_module", GATE_PATH)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_json(counter):
    return (json.dumps({
        "version":3, "nextId":2, "nextProjectId":1,
        "projects":[], "tasks":[{
            "id":"t1", "title":"M11P_TEST_"+str(counter), "done":False,
            "createdAtMs":1000, "updatedAtMs":1000+counter,
            "priority":"none", "description":"", "dueDate":None,
            "projectId":None
        }]
    }, separators=(",",":")) + "\n").encode("utf-8")


def write_new(path, payload):
    fd = os.open(path, os.O_EXCL | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def atomic_test_write(path, payload):
    replacement = path.parent / "m11p-atomic-next.json"
    write_new(replacement, payload)
    os.replace(replacement, path)


class DurableStageHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name) / "m11l-tasks-copy"
        self.folder.mkdir(mode=0o700)
        self.source = self.folder / "todo-copy.json"
        self.initial = test_json(0)
        write_new(self.source, self.initial)
        self.writer = "m11p-stage-ledger-test-owner-001"
        self.dbpath = self.folder / "gate-review.db"

    def tearDown(self):
        self.temp.cleanup()

    def owner(self, bootstrap=False):
        return gate.CandidateOwner(self.folder, self.writer, bootstrap=bootstrap)

    def rows(self):
        with sqlite3.connect(self.dbpath) as db:
            return db.execute("""SELECT stage_id,epoch,expected_hash,
                source_hash_before,state FROM stage_history
                ORDER BY stage_id""").fetchall()

    def persisted(self):
        with sqlite3.connect(self.dbpath) as db:
            row = db.execute("""SELECT phase,epoch,pending_stage,expected_hash,
                source_hash,history_complete FROM owner WHERE id=1""").fetchone()
            schema = db.execute("PRAGMA user_version").fetchone()[0]
        return schema, row

    def denied(self, code, fn):
        with self.assertRaises(gate.GateError) as cm:
            fn()
        self.assertEqual(str(cm.exception), code)

    def test_settled_stage_id_consumed_forever_within_owner(self):
        with self.owner(bootstrap=True) as owner:
            self.assertTrue(owner.state()["historyComplete"])
            a = owner.reserve("m11p-never-reuse-001", test_json(1))
            self.assertEqual(a["epoch"], 0)
            self.assertEqual(self.rows()[0][-1], "RESERVED")
            atomic_test_write(self.source, test_json(1))
            owner.verify("m11p-never-reuse-001", 0)
            self.assertEqual(self.rows()[0][-1], "SETTLED")
            self.denied("STAGE_ID_REPLAY", lambda: owner.reserve(
                "m11p-never-reuse-001", test_json(2)))
            self.denied("STAGE_ID_REPLAY", lambda: owner.reserve(
                "m11p-never-reuse-001", test_json(1)))
            b = owner.reserve("m11p-never-reuse-002", test_json(2))
            self.assertEqual(b["epoch"], 0)
            atomic_test_write(self.source, test_json(2))
            owner.verify("m11p-never-reuse-002", 0)
            self.assertEqual([r[-1] for r in self.rows()], ["SETTLED","SETTLED"])
            self.assertEqual(len(self.rows()), 2)
            self.denied("STAGE_ID_REPLAY", lambda: owner.reserve(
                "m11p-never-reuse-002", test_json(3)))
            self.denied("STALE_STAGE", lambda: owner.verify(
                "m11p-never-reuse-001", 0))
        with self.owner() as next_owner:
            self.assertEqual(next_owner.state()["phase"], "RECOVERY_REVIEW")
            self.assertTrue(next_owner.state()["historyComplete"])
            self.assertEqual(len(self.rows()), 2)
            self.denied("STAGE_NOT_ADMISSIBLE", lambda: next_owner.reserve(
                "m11p-never-reuse-001", test_json(3)))
        self.assertEqual(self.source.read_bytes(), test_json(2))

    def test_atomic_failed_reservation_has_no_ledger_or_pending_half(self):
        with self.owner(bootstrap=True) as owner:
            owner._db.execute("""CREATE TRIGGER m11p_abort_reservation
                BEFORE UPDATE OF pending_stage ON owner
                BEGIN SELECT RAISE(ABORT, 'SIMULATED_FAILURE'); END""")
            with self.assertRaises(sqlite3.DatabaseError):
                owner.reserve("m11p-atomic-failure-001", test_json(1))
            self.assertEqual(self.rows(), [])
            self.assertFalse(owner.state()["pending"])
            self.assertEqual(self.source.read_bytes(), self.initial)
            owner._db.execute("DROP TRIGGER m11p_abort_reservation")
            owner.reserve("m11p-atomic-failure-001", test_json(1))
            self.assertEqual(self.rows()[0][-1], "RESERVED")
            atomic_test_write(self.source, test_json(1))
            owner.verify("m11p-atomic-failure-001", 0)
            self.assertEqual(self.rows()[0][-1], "SETTLED")

    def test_atomic_failed_settlement_does_not_release_stage(self):
        with self.owner(bootstrap=True) as owner:
            owner.reserve("m11p-failed-settle-001", test_json(1))
            atomic_test_write(self.source, test_json(1))
            owner._db.execute("""CREATE TRIGGER m11p_abort_settlement
                BEFORE UPDATE OF source_hash ON owner
                BEGIN SELECT RAISE(ABORT, 'SIMULATED_FAILURE'); END""")
            with self.assertRaises(sqlite3.DatabaseError):
                owner.verify("m11p-failed-settle-001", 0)
            self.assertEqual(self.rows()[0][-1], "RESERVED")
            self.assertTrue(owner.state()["pending"])
            owner._db.execute("DROP TRIGGER m11p_abort_settlement")
            owner.verify("m11p-failed-settle-001", 0)
            self.assertEqual(self.rows()[0][-1], "SETTLED")
            self.assertFalse(owner.state()["pending"])

    def test_missing_history_row_fails_closed_on_fresh_owner(self):
        with self.owner(bootstrap=True) as owner:
            owner.reserve("m11p-corrupt-stage-001", test_json(1))
        with sqlite3.connect(self.dbpath) as db:
            db.execute("DELETE FROM stage_history")
            db.commit()
        self.denied("JOURNAL_HISTORY_CORRUPT", lambda: self.owner())
        self.assertEqual(self.source.read_bytes(), self.initial)

    def test_extra_orphan_reserved_stage_fails_closed(self):
        with self.owner(bootstrap=True):
            pass
        with sqlite3.connect(self.dbpath) as db:
            db.execute("""INSERT INTO stage_history VALUES
                ('m11p-orphan-stage-001',0,?,?, 'RESERVED')""",
                ("a"*64, "b"*64))
            db.commit()
        self.denied("JOURNAL_HISTORY_CORRUPT", lambda: self.owner())

    def test_legacy_v1_without_known_history_is_review_only(self):
        with self.owner(bootstrap=True) as owner:
            self.assertTrue(owner.state()["historyComplete"])
        with sqlite3.connect(self.dbpath) as db:
            db.execute("DROP TABLE stage_history")
            db.execute("ALTER TABLE owner DROP COLUMN history_complete")
            db.execute("PRAGMA user_version=1")
            db.commit()
        with self.owner() as upgraded:
            self.assertEqual(upgraded.state()["phase"], "RECOVERY_REVIEW")
            self.assertFalse(upgraded.state()["historyComplete"])
            self.denied("STAGE_NOT_ADMISSIBLE",lambda:upgraded.reserve(
                "m11p-legacy-reuse-001",test_json(1)))
        schema, row = self.persisted()
        self.assertEqual(schema,2)
        self.assertEqual(row[0],"RECOVERY_REVIEW")
        self.assertEqual(row[5],0)
        self.assertEqual(self.rows(),[])
        self.assertEqual(self.source.read_bytes(),self.initial)

    def test_legacy_pending_id_is_carried_as_permanent_reserved(self):
        with self.owner(bootstrap=True) as owner:
            owner.reserve("m11p-legacy-pending-001",test_json(1))
        with sqlite3.connect(self.dbpath) as db:
            db.execute("DROP TABLE stage_history")
            db.execute("ALTER TABLE owner DROP COLUMN history_complete")
            db.execute("PRAGMA user_version=1")
            db.commit()
        with self.owner() as upgraded:
            self.assertEqual(upgraded.state()["phase"],"RECOVERY_REVIEW")
            self.assertTrue(upgraded.state()["pending"])
            self.assertFalse(upgraded.state()["historyComplete"])
            self.assertEqual(self.rows()[0][0],"m11p-legacy-pending-001")
            self.assertEqual(self.rows()[0][-1],"RESERVED")
            self.denied("STAGE_NOT_ADMISSIBLE",lambda:upgraded.reserve(
                "m11p-legacy-pending-001",test_json(1)))
        self.assertEqual(self.source.read_bytes(),self.initial)

    def test_four_abrupt_process_windows_are_fenced_on_reopen(self):
        cases = [
            ("before-reserve",80,None,"JSON_ACTIVE",test_json(0),0),
            ("after-reserve",81,"RESERVED","JSON_ACTIVE",test_json(0),1),
            ("after-file-write",82,"RESERVED","JSON_ACTIVE",test_json(1),1),
            ("after-settlement",83,"SETTLED","JSON_ACTIVE",test_json(1),0)
        ]
        for mode,exit_code,stage_state,prephase,expected_file,pending in cases:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as root:
                folder=Path(root)/"m11l-tasks-copy"
                folder.mkdir(mode=0o700)
                source=folder/"todo-copy.json"
                write_new(source,test_json(0))
                command=[sys.executable, "-B", "-I",str(PROBE),
                         "--directory",str(folder),"--mode",mode]
                proc=subprocess.run(command,capture_output=True,timeout=10,
                                    check=False)
                self.assertEqual(proc.returncode,exit_code,proc.stderr.decode())
                self.assertEqual(source.read_bytes(),expected_file)
                dbpath=folder/"gate-review.db"
                with sqlite3.connect(dbpath) as db:
                    phase, before_epoch, pending_stage, state_hash = db.execute(
                        "SELECT phase,epoch,pending_stage,source_hash FROM owner"
                    ).fetchone()
                    history=db.execute(
                        "SELECT stage_id,state FROM stage_history"
                    ).fetchall()
                self.assertEqual(phase,prephase)
                self.assertEqual(before_epoch,0)
                self.assertEqual(bool(pending_stage),bool(pending))
                self.assertEqual(len(history),0 if stage_state is None else 1)
                if stage_state is not None:
                    self.assertEqual(history[0][-1],stage_state)
                # File replacement before verify MUST NOT be treated as
                # durable settlement. Last confirmed digest remains old.
                if mode=="after-file-write":
                    self.assertEqual(state_hash,hashlib.sha256(test_json(0)).hexdigest())
                    self.assertNotEqual(state_hash,hashlib.sha256(expected_file).hexdigest())
                with gate.CandidateOwner(folder,"m11p-new-owner-after-crash",
                                         bootstrap=False) as recovered:
                    self.assertEqual(recovered.state()["phase"],"RECOVERY_REVIEW")
                    self.assertEqual(recovered.state()["epoch"],1)
                    self.assertEqual(recovered.state()["pending"],bool(pending))
                    self.assertTrue(recovered.state()["historyComplete"])
                    with self.assertRaises(gate.GateError):
                        recovered.reserve("m11p-crash-stage-001",test_json(2))
                self.assertEqual(source.read_bytes(),expected_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
