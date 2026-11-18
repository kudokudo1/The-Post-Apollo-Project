#!/usr/bin/env python3
"""CI-only persistent Room lifecycle rehearsal. Creates disposable DB itself."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PX = ROOT / "px-source/bin/px-hospital-store"
V1 = ROOT / "scripts/hospital/room_lifecycle_fixture_v1.py"
V2 = ROOT / "scripts/hospital/room_lifecycle_disk_rehearsal_v2.py"

def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    obj = importlib.util.module_from_spec(spec)
    loader.exec_module(obj)
    return obj

px = load(PX, "px_hospital_lifecycle_disk")
v1 = load(V1, "hospital_lifecycle_memory")
v2 = load(V2, "hospital_lifecycle_disk")

class DiskRehearsal(unittest.TestCase):
    def setUp(self):
        self.scratch = v2.Scratch(px, v1)
        with self.scratch.connect() as db:
            db.execute("INSERT INTO patients(patient_id,repository) "
                       "VALUES('patient','fixture/repository')")
            for room in ("empty","historical","busy","contract","other"):
                db.execute("INSERT INTO rooms(room_id,patient_id) "
                           "VALUES(?,'patient')", (room,))
            db.execute("INSERT INTO sessions(session_id,room_id,status,ended_at) "
                       "VALUES('old','historical','COMPLETE','2026-10-09 00:00:00')")
            db.execute("INSERT INTO messages(room_id,session_id,author_role,"
                       "direction,body_md) VALUES('historical','old','doctor',"
                       "'incoming','SENSITIVE_FIXTURE_MESSAGE')")
            db.execute("INSERT INTO room_reports(room_id,body_md) "
                       "VALUES('historical','SENSITIVE_FIXTURE_REPORT')")
            db.execute("INSERT INTO room_checkpoints(room_id,body_md) "
                       "VALUES('historical','SENSITIVE_FIXTURE_CHECKPOINT')")
            db.execute("INSERT INTO chart_entries(scope_type,room_id,body_md) "
                       "VALUES('ROOM','historical','SENSITIVE_FIXTURE_CHART')")
            db.execute("INSERT INTO session_events(session_id,event_type) "
                       "VALUES('old','turn.completed')")
            db.execute("INSERT INTO sessions(session_id,room_id,status) "
                       "VALUES('running','busy','WAITING')")
            db.execute("INSERT INTO assignments(room_id,status,goal_md) "
                       "VALUES('contract','ACTIVE','work')")

    def tearDown(self):
        self.scratch.close()

    def review(self, room="empty"):
        return self.scratch.review(room)

    def move(self, room="empty", action="TRASH"):
        snap = self.review(room)
        return self.scratch.transition(room,action,snap["revision"],snap["digest"])

    def test_disk_restart_roundtrip_and_private_contents(self):
        first = self.review("historical")
        self.assertEqual(first["revision"],0)
        self.assertEqual(first["counts"]["session_events"],1)
        self.assertEqual(first["counts"]["messages"],1)
        self.move("historical")
        self.assertNotIn("historical",self.scratch.visible_rooms())
        with self.scratch.connect() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM rooms WHERE room_id='historical'"
            ).fetchone()[0],1)
            self.assertEqual(db.execute(
                "SELECT body_md FROM messages WHERE room_id='historical'"
            ).fetchone()[0],"SENSITIVE_FIXTURE_MESSAGE")
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts "
                "WHERE room_id='historical'").fetchone()[0],1)
            self.assertNotIn("SENSITIVE_FIXTURE_MESSAGE",repr(
                self.scratch.review("historical",db)))
        self.move("historical","RESTORE")
        self.assertIn("historical",self.scratch.visible_rooms())
        with self.scratch.connect() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts "
                "WHERE room_id='historical'").fetchone()[0],2)
            self.assertEqual(db.execute(
                "SELECT body_md FROM room_reports WHERE room_id='historical'"
            ).fetchone()[0],"SENSITIVE_FIXTURE_REPORT")
            self.assertEqual(db.execute(
                "SELECT count(*) FROM session_events WHERE session_id='old'"
            ).fetchone()[0],1)

    def test_refuses_active_work_without_receipts(self):
        for room in ("busy","contract"):
            before = self.review(room)
            self.assertTrue(before["blockers"])
            with self.assertRaisesRegex(v2.SyntheticOnly,"ROOM_NOT_QUIESCENT"):
                self.scratch.transition(room,"TRASH",0,before["digest"])
        with self.scratch.connect() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts"
            ).fetchone()[0],0)

    def test_guarded_writer_routes_after_trash(self):
        self.move("historical")
        operations = [
            ("UPDATE rooms SET team='changed' WHERE room_id='historical'",()),
            ("DELETE FROM rooms WHERE room_id='historical'",()),
            ("INSERT INTO messages(room_id,author_role,direction,body_md) "
             "VALUES('historical','test','outgoing','invalid')",()),
            ("UPDATE messages SET body_md='corrupt' WHERE room_id='historical'",()),
            ("INSERT INTO sessions(session_id,room_id) VALUES('new','historical')",()),
            ("UPDATE sessions SET status='FAILED' WHERE session_id='old'",()),
            ("DELETE FROM sessions WHERE session_id='old'",()),
            ("INSERT INTO room_reports(room_id,body_md) "
             "VALUES('historical','late')",()),
            ("INSERT INTO room_checkpoints(room_id,body_md) "
             "VALUES('historical','late')",()),
            ("INSERT INTO assignments(room_id,goal_md) "
             "VALUES('historical','late')",()),
            ("INSERT INTO chart_entries(scope_type,room_id,body_md) "
             "VALUES('ROOM','historical','late')",()),
            ("INSERT INTO chart_entries(scope_type,room_id,source_room_id,body_md) "
             "VALUES('ROOM','other','historical','inbound-link')",()),
            ("INSERT INTO chart_suggestions(scope_type,room_id,body_md) "
             "VALUES('ROOM','historical','late')",()),
            ("INSERT INTO session_events(session_id,event_type) "
             "VALUES('old','turn.started')",()),
            ("UPDATE session_events SET event_type='turn.failed' "
             "WHERE session_id='old'",()),
        ]
        with self.scratch.connect() as db:
            for sql,args in operations:
                with self.subTest(sql=sql):
                    with self.assertRaisesRegex(sqlite3.IntegrityError,
                                                "TRASHED_ROOM_WRITE_REFUSED"):
                        db.execute(sql,args)
            self.assertEqual(db.execute(
                "SELECT count(*) FROM rooms WHERE room_id='historical'"
            ).fetchone()[0],1)
        self.assertEqual(self.review("historical")["blockers"],[])
        self.move("historical","RESTORE")
        with self.scratch.connect() as db:
            db.execute("UPDATE rooms SET team='after-restore' "
                       "WHERE room_id='historical'")
        self.assertEqual(self.review("historical")["state"],"ACTIVE")

    def test_injected_crash_before_commit_rolls_back_wal(self):
        # Crash occurs in a separate process *after* updating state and
        # receipt in the transaction but *before* SQLite COMMIT.
        cmd = r'''
import os,sqlite3,sys
db=sqlite3.connect(sys.argv[1],isolation_level=None)
db.execute("PRAGMA journal_mode=WAL")
db.execute("BEGIN IMMEDIATE")
db.execute("INSERT INTO room_lifecycle_fixture "
 "(room_id,state,revision,frozen_digest) VALUES('empty','TRASHED',1,?)",
 (sys.argv[2],))
db.execute("INSERT INTO room_lifecycle_fixture_receipts "
 "(room_id,action,revision_before,revision_after,graph_digest) "
 "VALUES('empty','TRASH',0,1,?)",(sys.argv[2],))
os._exit(73)
'''
        before=self.review()
        out=subprocess.run([sys.executable,"-c",cmd,str(self.scratch.path),
                            before["digest"]],check=False,timeout=10)
        self.assertEqual(out.returncode,73)
        self.assertEqual(self.review()["revision"],0)
        self.assertIn("empty",self.scratch.visible_rooms())
        with self.scratch.connect() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts"
            ).fetchone()[0],0)
        self.move()

    def test_commit_survives_lost_ack_and_request_replay(self):
        # Committed state must outlive the caller losing its response.
        # A second request with the old witness is not permitted to replay.
        before=self.review()
        committed=self.scratch.transition("empty","TRASH",0,before["digest"])
        self.assertEqual(committed["revision"],1)
        with self.assertRaisesRegex(v2.SyntheticOnly,"STALE_REVISION"):
            self.scratch.transition("empty","TRASH",0,before["digest"])
        self.assertEqual(self.review()["revision"],1)
        with self.scratch.connect() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts"
            ).fetchone()[0],1)
        self.move(action="RESTORE")

    def test_concurrent_requests_admit_one_transition(self):
        before=self.review()
        barrier=threading.Barrier(2)
        def work():
            barrier.wait(timeout=4)
            try:
                return self.scratch.transition(
                    "empty","TRASH",0,before["digest"])
            except (v2.SyntheticOnly,sqlite3.OperationalError):
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            got=list(pool.map(lambda _:work(),range(2)))
        self.assertEqual(sum(x is not None for x in got),1)
        with self.scratch.connect() as db:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts "
                "WHERE room_id='empty'").fetchone()[0],1)
        self.move(action="RESTORE")

    def test_witness_change_and_burn_hold(self):
        before=self.review()
        with self.scratch.connect() as db:
            db.execute("UPDATE rooms SET team='new' WHERE room_id='empty'")
        with self.assertRaisesRegex(v2.SyntheticOnly,"STALE_GRAPH"):
            self.scratch.transition("empty","TRASH",0,before["digest"])
        for action in ("BURN","DELETE","BURN ALL"):
            with self.assertRaisesRegex(v2.SyntheticOnly,
                                        "BURN_AND_OTHER_ACTIONS_REFUSED"):
                self.scratch.transition(
                    "empty",action,0,self.review()["digest"])

    def test_real_px_rooms_list_remains_ungated(self):
        self.move()
        with self.scratch.connect() as db:
            # Demonstrates that the source-owner PX read path STILL exposes
            # trashed Rooms until the PX owner implements its own query gate.
            names=[x["id"] for x in px.rooms_list(db)]
        self.assertIn("empty",names)
        self.assertNotIn("empty",self.scratch.visible_rooms())

    def test_direct_disk_and_non_ci_inputs_have_no_entrypoint(self):
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"false"}):
            with self.assertRaisesRegex(v2.SyntheticOnly,"CI_ONLY"):
                v2.Scratch(px,v1)
        self.assertFalse(hasattr(v2,"open_existing"))
        self.assertFalse(hasattr(v2,"burn"))

if __name__=="__main__":
    unittest.main(verbosity=2)
