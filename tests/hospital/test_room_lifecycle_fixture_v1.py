#!/usr/bin/env python3
"""Hospital Room lifecycle: exact PX v10, strictly in-memory rehearsal."""
import importlib.machinery
import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PX = ROOT / "bin/px-hospital-store"
MODULE = ROOT / "scripts/hospital/room_lifecycle_fixture_v1.py"

def load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module

px = load(PX, "px_hospital_store_lifecycle_fixture")
prototype = load(MODULE, "hospital_lifecycle_fixture")

def fixture():
    db = sqlite3.connect(":memory:", isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    px.migrate(db)
    prototype.install_fixture(db)
    db.execute("INSERT INTO patients(patient_id,repository) VALUES('patient','demo/test')")
    for room_id in ("empty", "historical", "open", "assignment", "stale"):
        db.execute("INSERT INTO rooms(room_id,patient_id) VALUES(?, 'patient')",
                   (room_id,))
    db.execute("""INSERT INTO sessions(session_id,room_id,status,ended_at)
                  VALUES('s-old','historical','COMPLETE','2026-10-08 00:00:00')""")
    db.execute("""INSERT INTO messages(room_id,session_id,author_role,
                  direction,body_md) VALUES('historical','s-old','doctor',
                  'outgoing','Private message content')""")
    db.execute("""INSERT INTO room_checkpoints(room_id,body_md)
                  VALUES('historical','Preserve checkpoint')""")
    db.execute("""INSERT INTO room_reports(room_id,body_md)
                  VALUES('historical','Preserve report')""")
    db.execute("""INSERT INTO chart_entries(scope_type,room_id,body_md)
                  VALUES('ROOM','historical','Preserve decision')""")
    db.execute("""INSERT INTO sessions(session_id,room_id,status)
                  VALUES('s-open','open','WAITING')""")
    db.execute("""INSERT INTO assignments(room_id,goal_md,status,title)
                  VALUES('assignment','goal','ACTIVE','Live assignment')""")
    return db

class LifecycleFixtureTests(unittest.TestCase):
    def test_reversible_empty_room_preserves_original_record_and_receipt(self):
        with fixture() as db:
            before = prototype.review(db, "empty")
            self.assertEqual(before["revision"], 0)
            self.assertIn("empty", prototype.visible_room_ids(db))
            trashed = prototype.transition(
                db,"empty","TRASH",before["revision"],before["digest"])
            self.assertEqual(trashed["state"],"TRASHED")
            self.assertNotIn("empty", prototype.visible_room_ids(db))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM rooms WHERE room_id='empty'"
            ).fetchone()[0],1)
            current = prototype.review(db, "empty")
            self.assertEqual(current["revision"],1)
            restored = prototype.transition(
                db,"empty","RESTORE",current["revision"],current["digest"])
            self.assertEqual(restored["state"],"ACTIVE")
            self.assertIn("empty",prototype.visible_room_ids(db))
            self.assertEqual(db.execute(
                "SELECT action FROM room_lifecycle_fixture_receipts "
                "WHERE room_id='empty' ORDER BY receipt_id"
            ).fetchall()[0][0],"TRASH")
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts "
                "WHERE room_id='empty'"
            ).fetchone()[0],2)

    def test_historical_graph_not_deleted_or_exported(self):
        with fixture() as db:
            before = prototype.review(db,"historical")
            self.assertEqual(before["blockers"],[])
            counts = before["relatedCounts"]
            for key in ("sessions","messages","room_checkpoints",
                        "room_reports","chart_entries"):
                self.assertEqual(counts[key],1,key)
            prototype.transition(db,"historical","TRASH",0,before["digest"])
            self.assertNotIn("historical",prototype.visible_room_ids(db))
            self.assertEqual(db.execute(
                "SELECT body_md FROM messages WHERE room_id='historical'"
            ).fetchone()[0],"Private message content")
            review = prototype.review(db,"historical")
            self.assertNotIn("Private message content",repr(review))
            prototype.transition(db,"historical","RESTORE",
                                 review["revision"],review["digest"])
            self.assertIn("historical",prototype.visible_room_ids(db))
            self.assertEqual(db.execute(
                "SELECT body_md FROM room_reports WHERE room_id='historical'"
            ).fetchone()[0],"Preserve report")

    def test_refuse_open_session_and_assignment(self):
        with fixture() as db:
            for room in ("open","assignment"):
                current=prototype.review(db,room)
                self.assertTrue(current["blockers"])
                with self.assertRaisesRegex(prototype.FixtureRefusal,
                                            "ROOM_NOT_QUIESCENT"):
                    prototype.transition(db,room,"TRASH",0,current["digest"])
                self.assertIn(room,prototype.visible_room_ids(db))

    def test_stale_revision_and_changed_room_are_denied(self):
        with fixture() as db:
            current=prototype.review(db,"stale")
            db.execute("UPDATE rooms SET team='new' WHERE room_id='stale'")
            with self.assertRaisesRegex(prototype.FixtureRefusal,"CHANGED_GRAPH"):
                prototype.transition(db,"stale","TRASH",0,current["digest"])
            fresh=prototype.review(db,"stale")
            prototype.transition(db,"stale","TRASH",0,fresh["digest"])
            with self.assertRaisesRegex(prototype.FixtureRefusal,"STALE_REVISION"):
                prototype.transition(db,"stale","TRASH",0,fresh["digest"])
            db.execute("UPDATE rooms SET team='changed-again' WHERE room_id='stale'")
            tampered=prototype.review(db,"stale")
            self.assertIn("TRASHED_GRAPH_CHANGED",tampered["blockers"])
            with self.assertRaisesRegex(prototype.FixtureRefusal,
                                        "TRASHED_GRAPH_CHANGED"):
                prototype.transition(db,"stale","RESTORE",1,tampered["digest"])

    def test_injected_crash_rolls_back_state_and_receipt(self):
        with fixture() as db:
            current=prototype.review(db,"empty")
            with self.assertRaisesRegex(prototype.FixtureRefusal,"INJECTED_CRASH"):
                prototype.transition(db,"empty","TRASH",0,current["digest"],
                                     fail_before_commit=True)
            self.assertEqual(prototype.review(db,"empty")["revision"],0)
            self.assertIn("empty",prototype.visible_room_ids(db))
            self.assertEqual(db.execute(
                "SELECT count(*) FROM room_lifecycle_fixture_receipts"
            ).fetchone()[0],0)

    def test_burn_not_implemented_and_replay_refused(self):
        with fixture() as db:
            current=prototype.review(db,"empty")
            for action in ("BURN","DELETE","burn","BURN ALL"):
                with self.assertRaisesRegex(prototype.FixtureRefusal,
                                            "BURN_AND_UNKNOWN_ACTION_REFUSED"):
                    prototype.transition(db,"empty",action,0,current["digest"])
            prototype.transition(db,"empty","TRASH",0,current["digest"])
            again=prototype.review(db,"empty")
            with self.assertRaisesRegex(prototype.FixtureRefusal,
                                        "ROOM_ALREADY_TRASHED"):
                prototype.transition(db,"empty","TRASH",1,again["digest"])
            self.assertFalse(again["productionAuthority"])
            self.assertFalse(again["burnSupported"])

    def test_on_disk_and_attached_database_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"hospital.db"
            disk = sqlite3.connect(path)
            with self.assertRaisesRegex(prototype.FixtureRefusal,
                                        "DISK_OR_ATTACHED_DATABASE_REFUSED"):
                prototype.install_fixture(disk)
            disk.close()
        with fixture() as db:
            db.execute("ATTACH DATABASE ':memory:' AS foreign_db")
            with self.assertRaisesRegex(prototype.FixtureRefusal,
                                        "DISK_OR_ATTACHED_DATABASE_REFUSED"):
                prototype.review(db,"empty")

    def test_invalid_revision_and_id_refused(self):
        with fixture() as db:
            for bad in ("../room", "", "illegal room", "\u0000"):
                with self.assertRaises(prototype.FixtureRefusal):
                    prototype.review(db,bad)
            current=prototype.review(db,"empty")
            for rev in (-1,True,"0",9999999999):
                with self.assertRaisesRegex(prototype.FixtureRefusal,
                                            "EXPECTED_REVISION_REFUSED"):
                    prototype.transition(db,"empty","TRASH",rev,current["digest"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
