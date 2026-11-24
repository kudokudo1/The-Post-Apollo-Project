"""M6 composition regression: actual B3/M2/M4/UI2, injected public stream only."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forest"))
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from turn_bridge_b3 import ForestTurnBridge, BridgeRefusal, bootstrap_attempts_synthetic
from shared_context_b6r1 import TaskContext, BarkAttachment
from context_first_tree_m2 import ContextRefusal, SessionContextRef
from runtime_stop_control_r2 import RuntimeStopControl
from history_public_fixture_m4 import (
    PublicViewRef, HistoryPageRef, history_public_fixture_in_transaction,
)


class IntegratedContinuity(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "public.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(lambda: self.db.close())
        bootstrap_synthetic(self.db)
        bootstrap_attempts_synthetic(self.db)
        self.journal = ForestSessionJournal(self.db)
        self.context = TaskContext("fixture-owner", "cherry", None,
                                   "task-a", "exec-a", 1, "INTERACTIVE")
        self.sid = self.journal.create_session("fixture-owner", "cherry",
                                               "Not a display title", now_ms=1)["session_id"]
        self.rev = 0
        self.clock = 10
        self.calls = []
        self.reply = "Public answer"

    def tick(self):
        self.clock += 1
        return self.clock

    def streamer(self, **kwargs):
        self.calls.append(kwargs["messages"])
        model = kwargs["model"]
        yield {"event":"STARTED","provider":"ollama","model":model}
        yield {"event":"DELTA","text":self.reply}
        yield {"event":"COMPLETE","provider":"ollama","model":model,"text":self.reply}

    def append_user(self, text):
        row = self.journal.append_turn("fixture-owner", self.sid,
            expected_revision=self.rev, role="user", body=text, now_ms=self.tick())
        self.rev = row["revision"]
        self.ref = SessionContextRef(self.context, self.sid, self.rev, row["turn_id"])

    def exchange(self):
        bridge = ForestTurnBridge(self.journal, clock_ms=self.tick, streamer=self.streamer)
        self.control = RuntimeStopControl(self.context, "operation-" + str(self.rev))
        self.operation = "operation-" + str(self.rev)
        return bridge.exchange(owner="fixture-owner", session_id=self.sid,
            expected_revision=self.rev, model="fixture-model", context_ref=self.ref,
            current_context_ref=self.ref, resolve_current_context=lambda: self.ref,
            stop_control=self.control, operation_id=self.operation)

    def history(self, *, after=0, limit=16, revision=None):
        revision = self.rev if revision is None else revision
        attachment = BarkAttachment(self.context, "bark-a", "requester-a",
            "release-a", "seat-a", "recipient-a", "CHERRY", self.context.generation)
        rid = "fixture_request_" + str(self.tick()).zfill(4)
        ref = HistoryPageRef(PublicViewRef(attachment, rid), self.sid, revision, after, limit)
        self.db.execute("BEGIN")
        try:
            frame = history_public_fixture_in_transaction(self.journal, ref, current=ref)
        finally:
            self.db.rollback()
        fields = {"requestId":rid,"treeKey":"CHERRY","generation":self.context.generation,
                  "sessionId":self.sid,"revision":revision,"after":after,"limit":limit}
        return frame, fields

    def display(self, page):
        # Execute the actual merged UI2 page adapter, not a Python reimplementation.
        script = """
const fs=require("fs"), vm=require("vm");
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
const [frame,ref]=JSON.parse(fs.readFileSync(0,"utf8"));
process.stdout.write(JSON.stringify(ctx.project(frame,ref,ref)));
"""
        result = subprocess.run(["node", "-e", script,
            str(ROOT / "widgets/forest/ui2/PublicHistoryDisplay.js")],
            input=json.dumps(page, ensure_ascii=False), text=True,
            capture_output=True, check=True, timeout=10)
        return json.loads(result.stdout)

    def commit(self):
        events = list(self.exchange())
        self.assertEqual(events[-1]["event"], "COMMITTED")
        self.rev += 1
        return events

    def test_two_turns_restart_and_actual_ui_projection(self):
        self.append_user("Public first question")
        self.reply = "Public first answer 🌲"
        self.commit()
        page = self.history(limit=1)
        first = self.display(page)
        self.assertEqual(first["state"], "STRUCTURALLY_VALID_PUBLIC_FIXTURE")
        self.assertFalse(first["complete"])
        self.assertEqual(first["nextAfter"], 1)
        second = self.display(self.history(after=1, limit=1))
        self.assertTrue(second["complete"])
        self.assertEqual(second["messages"][0]["body"], self.reply)
        self.assertFalse(second["permissionGranted"])
        self.assertFalse(second["sourceAuthenticated"])
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.journal = ForestSessionJournal(self.db)
        self.context = replace(self.context, task_id="task-b",
                               execution_context_id="exec-b", generation=2)
        self.assertEqual(self.display(self.history())["messages"],
                         first["messages"] + second["messages"])
        previous_revision = self.rev
        self.append_user("Public follow-up")
        self.reply = "Public second answer"
        self.commit()
        self.assertEqual(self.calls[-1], [
            {"role":"user","content":"Public first question"},
            {"role":"assistant","content":"Public first answer 🌲"},
            {"role":"user","content":"Public follow-up"}])
        full = self.display(self.history())
        self.assertTrue(full["complete"])
        self.assertEqual([r["body"] for r in full["messages"]],
            ["Public first question","Public first answer 🌲",
             "Public follow-up","Public second answer"])
        with self.assertRaisesRegex(ContextRefusal, "STALE_REVISION"):
            self.history(revision=previous_revision)

    def test_provisional_text_never_appears_and_stop_no_replay(self):
        self.append_user("Public question")
        self.reply = "Provisional only"
        gen = self.exchange()
        attempt = next(gen)["attempt_id"]
        self.assertEqual(next(gen)["event"], "STARTED")
        self.assertEqual(next(gen)["event"], "DELTA")
        pending = self.display(self.history())
        self.assertEqual([r["body"] for r in pending["messages"]], ["Public question"])
        self.control.request_stop(self.context, self.operation, attempt)
        with self.assertRaisesRegex(BridgeRefusal, "OLLAMA_CANCELLED"):
            list(gen)
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (attempt,)
        ).fetchone()[0], "ABORTED")
        self.assertEqual(self.display(self.history())["messages"], pending["messages"])
        with self.assertRaisesRegex(BridgeRefusal, "ATTEMPT_ALREADY_EXISTS"):
            list(self.exchange())
        self.assertEqual(len(self.calls), 1)

    def test_lost_context_before_commit_never_adds_reply(self):
        self.append_user("Public question")
        gen = self.exchange()
        attempt = next(gen)["attempt_id"]
        self.assertEqual(next(gen)["event"], "STARTED")
        self.assertEqual(next(gen)["event"], "DELTA")
        self.ref = replace(self.ref, context=replace(self.context, generation=2))
        with self.assertRaisesRegex(BridgeRefusal, "CONTEXT_CHANGED"):
            list(gen)
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (attempt,)
        ).fetchone()[0], "ABORTED")
        self.assertEqual([r["body"] for r in self.display(self.history())["messages"]],
                         ["Public question"])


if __name__ == "__main__":
    unittest.main()
