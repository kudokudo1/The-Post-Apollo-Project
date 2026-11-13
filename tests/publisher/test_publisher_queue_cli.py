"""P1.4 queue exercises actual SQLite transactions, DST, idempotency, recovery.

Never connects to a provider, starts a daemon, or writes to the host desktop.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import datetime as dt
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
SOURCE = ROOT / "services/publisher/PublisherQueueCli.py"
spec = importlib.util.spec_from_file_location("PublisherQueueCliTest", SOURCE)
assert spec and spec.loader
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)
UTC = dt.timezone.utc


def ms(date: str) -> int:
    return int(dt.datetime.fromisoformat(date).replace(tzinfo=UTC).timestamp() * 1000)


class QueueP14Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.db = root / "publisher-queue-v1.sqlite3"
        self.drafts = root / "publisher-drafts-v1.json"
        self.clock = ms("2026-11-12T10:00:00")
        self.rewrite("Morning recruitment", 1500)

    def rewrite(self, title: str, revision: int):
        record = {"version":1,"nextId":2,"drafts":[
            {"id":"d1","title":title,"body":"Verified factual source to be reviewed",
             "createdAtMs":1000,"updatedAtMs":revision}
        ]}
        self.drafts.write_text(json.dumps(record), encoding="utf-8")
        self.drafts.chmod(0o600)

    def call(self, action: str, **values):
        base = {"db":str(self.db),"drafts":str(self.drafts),"draft":"d1",
                "local_time":"2026-11-13T09:00","timezone":"America/New_York",
                "recurrence":"once","id":0,"action":action}
        base.update(values)
        return queue.execute(type("Args", (), base)(), self.clock)

    def test_future_schedule_persists_and_is_idempotent(self):
        one = self.call("schedule")
        self.assertTrue(one["ok"])
        self.assertFalse(one["idempotent"])
        self.assertEqual(one["status"], "scheduled")
        duplicate = self.call("schedule")
        self.assertTrue(duplicate["idempotent"])
        self.assertEqual(one["id"], duplicate["id"])
        self.assertEqual(len(self.call("status")["jobs"]), 1)
        self.assertEqual(self.call("status")["executor"], "DISABLED")
        self.assertFalse(self.call("status")["canPublish"])
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0],1)
        self.assertEqual(self.db.stat().st_mode & 0o077, 0)

    def test_due_needs_review_never_posts_even_after_restart(self):
        self.call("schedule")
        due = ms("2026-11-13T15:00:00")
        with queue.connect(self.db) as conn:
            first = queue.tick(conn,self.drafts,due)
        self.assertEqual(first["reviewRequired"],1)
        self.assertEqual(first["posted"],0)
        self.assertEqual(self.call("status")["jobs"][0]["status"], "needs_review")
        with queue.connect(self.db) as conn:
            again = queue.tick(conn,self.drafts,due + 30000)
        self.assertEqual(again["reviewRequired"],0)
        result = self.call("acknowledge",id=1)
        self.assertEqual(result["status"], "reviewed")
        self.assertEqual(result["posted"],0)
        self.assertEqual(self.call("status")["jobs"][0]["status"], "reviewed")

    def test_pause_resume_cancel_and_refusal_rollback(self):
        job = self.call("schedule")
        self.assertEqual(self.call("pause",id=job["id"])["status"],"paused")
        self.assertRaises(queue.Refused, self.call, "pause",id=job["id"])
        self.assertEqual(self.call("status")["jobs"][0]["status"],"paused")
        self.assertEqual(self.call("resume",id=job["id"])["status"],"scheduled")
        self.assertEqual(self.call("cancel",id=job["id"])["status"],"cancelled")
        self.assertRaises(queue.Refused,self.call,"cancel",id=job["id"])
        self.assertEqual(len(self.call("status")["jobs"]),1)
        self.assertEqual(self.call("status")["jobs"][0]["status"],"cancelled")

    def test_source_changed_before_due_is_blocked(self):
        self.call("schedule")
        self.rewrite("Changed job terms",2000)
        later = ms("2026-11-13T16:00:00")
        with queue.connect(self.db) as conn:
            ticked = queue.tick(conn,self.drafts,later)
        self.assertEqual(ticked["blocked"],1)
        self.assertEqual(ticked["reviewRequired"],0)
        self.assertEqual(self.call("status")["jobs"][0]["status"],"blocked")
        self.assertRaises(queue.Refused,self.call,"acknowledge",id=1)

    def test_daily_rearm_requires_manual_review_and_same_draft(self):
        entry = self.call("schedule",recurrence="daily")
        nextday = ms("2026-11-13T18:00:00")
        with queue.connect(self.db) as conn:
            queue.tick(conn,self.drafts,nextday)
        self.assertEqual(self.call("status")["jobs"][0]["status"],"needs_review")
        self.assertRaises(queue.Refused,self.call,"rearm",id=entry["id"])
        self.call("acknowledge",id=entry["id"])
        reopened = self.call("rearm",id=entry["id"])
        self.assertEqual(reopened["status"],"scheduled")
        row = self.call("status")["jobs"][0]
        self.assertGreater(row["due_ms"], self.clock)
        self.assertEqual(row["occurrence"],2)
        self.assertEqual(len(self.call("status")["jobs"]),1)

    def test_weekly_rearm_and_draft_change_refusal(self):
        self.call("schedule",recurrence="weekly")
        with queue.connect(self.db) as conn:
            queue.tick(conn,self.drafts,ms("2026-11-13T18:00:00"))
        self.call("acknowledge",id=1)
        self.rewrite("No longer the original source",2000)
        self.assertRaises(queue.Refused,self.call,"rearm",id=1)
        self.assertEqual(self.call("status")["jobs"][0]["status"],"reviewed")

    def test_dst_rejects_ambiguous_and_skipped_hours(self):
        with self.assertRaisesRegex(queue.Refused,"NONEXISTENT_LOCAL_TIME"):
            queue.local_to_ms("2026-03-08T02:30","America/New_York")
        with self.assertRaisesRegex(queue.Refused,"AMBIGUOUS_LOCAL_TIME"):
            queue.local_to_ms("2026-11-01T01:30","America/New_York")
        valid = queue.local_to_ms("2026-11-01T03:30","America/New_York")
        self.assertIsInstance(valid,int)
        self.assertEqual(queue.local_to_ms("2026-11-13T15:00","UTC"),
                         ms("2026-11-13T15:00:00"))
        with self.assertRaises(queue.Refused):
            queue.local_to_ms("2026-11-13T15:00","bad/zone")
        with self.assertRaises(queue.Refused):
            queue.local_to_ms("2026-02-30T15:00","UTC")

    def test_bad_inputs_do_not_create_jobs(self):
        for changes in (
            {"local_time":"2026-11-10T15:00"},
            {"local_time":"2026-13-02T01:00"},
            {"timezone":"America/NotReal"},
            {"recurrence":"hourly"},
            {"draft":"d3"},
        ):
            with self.subTest(changes=changes):
                self.assertRaises(queue.Refused,self.call,"schedule",**changes)
        self.assertEqual(len(self.call("status")["jobs"]),0)

    def test_cross_process_reload_and_json_cli(self):
        self.call("schedule")
        args = [sys.executable,"-I","-B",str(SOURCE),"status",
                "--db",str(self.db),"--drafts",str(self.drafts)]
        result = subprocess.run(args,check=True,capture_output=True,text=True)
        data = json.loads(result.stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["jobs"][0]["status"],"scheduled")
        self.assertEqual(data["executor"],"DISABLED")
        self.assertEqual(result.stderr,"")

    def test_sqlite_concurrent_repeat_intent(self):
        def repeat(_):
            return self.call("schedule")
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(repeat,range(8)))
        self.assertTrue(all(v["ok"] for v in results))
        self.assertEqual(len({v["id"] for v in results}),1)
        self.assertEqual(len(self.call("status")["jobs"]),1)

    def test_symlinked_queue_file_refused(self):
        target = Path(self.temp.name) / "other.sqlite3"
        target.write_text("not a db")
        self.db.symlink_to(target)
        with self.assertRaisesRegex(queue.Refused,"UNTRUSTED_QUEUE_FILE"):
            self.call("status")


if __name__=="__main__":
    unittest.main()
