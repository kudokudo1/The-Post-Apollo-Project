"""P1.6 real SQLite local-history/recovery and v1->v2 migration tests.

No provider sessions, network, permissions, host services, or live workstation.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "services/publisher/PublisherQueueCli.py"
spec = importlib.util.spec_from_file_location("P16QueueHistory", SCRIPT)
assert spec and spec.loader
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)


def utc_ms(day: str) -> int:
    return int(dt.datetime.fromisoformat(day).replace(
        tzinfo=dt.timezone.utc).timestamp() * 1000)


class P16History(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "publisher-queue-v1.sqlite3"
        self.drafts = Path(self.tmp.name) / "publisher-drafts-v1.json"
        self.clock = utc_ms("2026-11-12T12:00:00")
        self.write_draft("Original", 1000)

    def write_draft(self, title: str, revision: int):
        self.drafts.write_text(json.dumps({
            "version": 1, "nextId": 2,
            "drafts": [{
                "id": "d1", "title": title, "body": "Local text only",
                "createdAtMs": 1000, "updatedAtMs": revision,
            }],
        }), encoding="utf-8")
        self.drafts.chmod(0o600)

    def action(self, name: str, now: int | None = None, **kwargs):
        params = dict(
            db=str(self.db), drafts=str(self.drafts), draft="d1",
            local_time="2026-11-13T09:00", timezone="America/New_York",
            recurrence="once", id=0, action=name,
        )
        params.update(kwargs)
        return queue.execute(type("Arguments", (), params)(),
                             self.clock if now is None else now)

    def schedule(self, **kw):
        return self.action("schedule", **kw)

    def test_history_is_local_only_and_duplicate_does_not_forge_event(self):
        first = self.schedule()
        self.assertEqual(first["status"], "scheduled")
        self.assertTrue(self.schedule()["idempotent"])
        history = self.action("history")
        self.assertEqual(len(history["events"]), 1)
        event = history["events"][0]
        self.assertEqual(event["action"], "schedule")
        self.assertEqual(event["from_state"], "none")
        self.assertEqual(event["to_state"], "scheduled")
        self.assertEqual(event["occurrence"], 1)
        self.assertIsNone(event["providerReceipt"])
        self.assertEqual(history["source"], "LOCAL_QUEUE_ONLY")
        self.assertEqual(history["posted"], 0)
        self.assertFalse(history["canPublish"])
        self.assertTrue(self.action("audit")["ledgerConsistent"])

    def test_events_share_transaction_with_each_status_transition(self):
        self.schedule(recurrence="daily")
        self.action("pause", id=1)
        self.action("resume", id=1)
        with queue.connect(self.db) as conn:
            queue.tick(conn, self.drafts, utc_ms("2026-11-13T16:00:00"))
        self.action("acknowledge", id=1)
        self.action("rearm", id=1)
        self.assertTrue(self.action("audit")["ledgerConsistent"])
        first = self.action("history")["events"]
        self.assertEqual(
            [e["action"] for e in reversed(first)],
            ["schedule", "pause", "resume", "due", "acknowledge", "rearm"],
        )
        self.assertEqual(first[0]["occurrence"], 2)
        with queue.connect(self.db) as conn:
            queue.tick(conn, self.drafts, utc_ms("2026-11-14T18:00:00"))
        more = self.action("history")["events"]
        self.assertEqual(more[0]["to_state"], "needs_review")
        self.assertEqual(more[0]["occurrence"], 2)
        self.assertTrue(self.action("audit")["ledgerConsistent"])
        self.assertEqual(self.action("history", id=999)["events"], [])

    def test_audit_is_read_only_and_reports_changed_source(self):
        self.schedule()
        self.write_draft("Edited later", 3000)
        before = self.action("history")["events"]
        report = self.action("audit")
        self.assertTrue(report["ledgerConsistent"])
        self.assertEqual(report["sourceProblems"],
                         [{"jobId": 1, "reason": "SOURCE_CHANGED_OR_MISSING"}])
        self.assertFalse(report["repairPerformed"])
        self.assertEqual(self.action("history")["events"], before)
        self.assertEqual(self.action("status")["jobs"][0]["status"], "scheduled")

    def test_explicit_reconcile_blocks_only_stale_local_jobs(self):
        self.schedule()
        self.write_draft("Changed", 2000)
        result = self.action("reconcile")
        self.assertEqual(result["blocked"], 1)
        self.assertEqual(result["posted"], 0)
        self.assertFalse(result["canPublish"])
        self.assertEqual(self.action("status")["jobs"][0]["status"], "blocked")
        self.assertEqual(self.action("history")["events"][0]["action"], "reconcile")
        self.assertTrue(self.action("audit")["ledgerConsistent"])
        self.assertEqual(self.action("reconcile")["blocked"], 0)
        self.assertEqual(self.action("audit")["sourceProblems"], [])
        self.assertTrue(self.drafts.exists())

    def test_history_divergence_fails_closed_before_mutation(self):
        self.schedule()
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE jobs SET status='cancelled' WHERE id=1")
        report = self.action("audit")
        self.assertFalse(report["ledgerConsistent"])
        self.assertEqual(report["ledgerProblems"][0]["reason"], "EVENT_STATE_MISMATCH")
        with self.assertRaisesRegex(queue.Refused, "HISTORY_DIVERGENCE"):
            self.action("pause", id=1)
        with self.assertRaisesRegex(queue.Refused, "HISTORY_DIVERGENCE"):
            self.action("reconcile")
        self.assertEqual(self.action("history")["events"][0]["to_state"], "scheduled")

    def test_corrupt_early_event_detected_not_rewritten(self):
        self.schedule(recurrence="daily")
        self.action("pause", id=1)
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE queue_events SET from_state='reviewed' WHERE action='pause'")
        report = self.action("audit")
        self.assertFalse(report["ledgerConsistent"])
        self.assertTrue(any(x["reason"] == "EVENT_CHAIN_DIVERGENCE"
                            for x in report["ledgerProblems"]))
        with self.assertRaisesRegex(queue.Refused, "HISTORY_DIVERGENCE"):
            self.action("resume", id=1)

    def test_crash_before_commit_rolls_back_state_and_history(self):
        self.schedule()
        with queue.connect(self.db) as conn:
            def simulate_crash():
                conn.execute("UPDATE jobs SET status='cancelled' WHERE id=1")
                queue.append_event(conn, 1, "cancel", "scheduled",
                                   "cancelled", self.clock + 10, 1, "CANCEL")
                raise RuntimeError("synthetic process crash")
            with self.assertRaisesRegex(RuntimeError, "synthetic process crash"):
                queue.transaction(conn, simulate_crash)
        self.assertEqual(self.action("status")["jobs"][0]["status"], "scheduled")
        self.assertEqual(len(self.action("history")["events"]), 1)
        self.assertTrue(self.action("audit")["ledgerConsistent"])

    def test_migration_from_existing_v1_never_makes_up_history(self):
        self.schedule()
        with sqlite3.connect(self.db) as conn:
            conn.execute("DROP TABLE queue_events")
            conn.execute("PRAGMA user_version=1")
        # P1.4 v1 jobs survive intact. Only a labeled UNVERIFIED baseline
        # is created for preexisting jobs, not fake prior operation receipts.
        self.assertEqual(self.action("status")["jobs"][0]["status"], "scheduled")
        events = self.action("history")["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["action"], "legacy_snapshot")
        self.assertEqual(events[0]["detail"], "LEGACY_BASELINE_UNVERIFIED")
        self.assertEqual(events[0]["from_state"], "unknown")
        self.assertTrue(self.action("audit")["ledgerConsistent"])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 2)

    def test_cli_history_and_audit_are_one_json_line(self):
        self.schedule()
        for action in ("history", "audit"):
            out = subprocess.run(
                [sys.executable, "-I", "-B", str(SCRIPT), action,
                 "--db", str(self.db), "--drafts", str(self.drafts)],
                check=True, capture_output=True, text=True,
            )
            self.assertEqual(len(out.stdout.strip().splitlines()), 1)
            result = json.loads(out.stdout)
            self.assertTrue(result["ok"])
            self.assertEqual(result["posted"], 0)
            self.assertFalse(result["canPublish"])
            self.assertEqual(out.stderr, "")


if __name__ == "__main__":
    unittest.main()
