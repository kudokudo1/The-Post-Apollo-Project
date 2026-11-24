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
from runtime_events_r3 import OperationRef, RuntimeExchange, RuntimeEventRefusal
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

    def resolve_fixture_context(self):
        # Test-local owner resolves durable state anew; not a captured UI ref.
        # This is not a production currentness/identity witness.
        session = self.db.execute(
            "SELECT state,revision FROM forest_sessions "
            "WHERE owner_key=? AND tree_key=? AND session_id=?",
            (self.context.principal_key, self.context.tree_key, self.sid),
        ).fetchone()
        if session is None or session[0] != "OPEN":
            raise ContextRefusal("FIXTURE_SESSION_UNAVAILABLE")
        user = self.db.execute(
            "SELECT turn_id,role FROM forest_turns WHERE session_id=? "
            "ORDER BY ordinal DESC LIMIT 1", (self.sid,),
        ).fetchone()
        if user is None or user[1] != "user":
            raise ContextRefusal("FIXTURE_USER_UNAVAILABLE")
        return SessionContextRef(self.context, self.sid, session[1], user[0])

    def runtime(self, operation_id):
        bridge = ForestTurnBridge(self.journal, clock_ms=self.tick, streamer=self.streamer)
        op = OperationRef(self.ref, operation_id)
        return op, RuntimeExchange(bridge, op,
            resolve_current_context=self.resolve_fixture_context,
            model="fixture-model")

    def controller(self, pages, changed_scope=None):
        # Only M4 history frames enter the actual UI2 controller. Internal R3
        # payloads, original operation references and attempt IDs stay local.
        script = """
const fs=require("fs"), vm=require("vm"), assert=require("node:assert/strict");
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
const {pages,changedScope}=JSON.parse(fs.readFileSync(0,"utf8"));
const c=ctx.createController();
const scopeOf=r=>({treeKey:r.treeKey,generation:r.generation,
    sessionId:r.sessionId,revision:r.revision,viewKey:"fixture-view-"+r.generation});
const scope=scopeOf(pages[0][1]);
const snapshots=[];
for (let i=0;i<pages.length;i++) {
    const [frame,ref]=pages[i];
    const pending=i===0 ? c.open(scope,ref.requestId,ref.limit)
                       : c.next(scope,ref.requestId,ref.limit);
    assert.equal(pending.state,"PENDING");
    assert.deepEqual(JSON.parse(JSON.stringify(pending.request)),ref);
    const snapshot=c.receive(frame,scope);
    assert.equal(snapshot.state,frame.complete?"COMPLETE":"PARTIAL");
    assert.equal(snapshot.request,null);
    assert.equal(snapshot.permissionGranted,false);
    assert.equal(snapshot.sourceAuthenticated,false);
    snapshots.push(snapshot);
}
if(changedScope!==null) snapshots.push(c.observe({...scope,...changedScope}));
process.stdout.write(JSON.stringify(snapshots));
"""
        result = subprocess.run(["node", "-e", script,
            str(ROOT / "widgets/forest/ui2/PublicHistoryDisplay.js")],
            input=json.dumps({"pages":pages,"changedScope":changed_scope}, ensure_ascii=False),
            text=True, capture_output=True, check=True, timeout=10)
        return json.loads(result.stdout)

    def test_r3_restart_followup_and_controller_reopens_committed_history(self):
        self.append_user("Public first question")
        op, runtime = self.runtime("original-1")
        first = list(runtime.run())
        self.assertEqual([f.payload["event"] for f in first],
                         ["REQUESTED","RESERVED","STARTED","DELTA","COMMITTED"])
        self.assertEqual([f.ordinal for f in first], list(range(1,6)))
        self.assertTrue(all(f.operation == op for f in first))
        self.assertIsNone(first[0].attempt_id)
        self.assertTrue(all(f.attempt_id == first[1].attempt_id for f in first[1:]))
        self.rev += 1
        pages = [self.history(limit=1), self.history(after=1,limit=1)]
        snapshots = self.controller(pages, {"generation":2})
        self.assertEqual([s["state"] for s in snapshots],
                         ["PARTIAL","COMPLETE","UNAVAILABLE"])
        self.assertEqual(snapshots[-1]["messages"], [])
        self.assertEqual([m["body"] for m in snapshots[1]["messages"]],
                         ["Public first question","Public answer"])
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.journal = ForestSessionJournal(self.db)
        self.context = replace(self.context, task_id="task-b",
                               execution_context_id="exec-b", generation=2)
        reopened = self.controller([self.history()])[-1]
        self.assertEqual(reopened["messages"], snapshots[1]["messages"])
        self.append_user("Public follow-up")
        self.reply = "Public second answer"
        new_op, new_runtime = self.runtime("original-2")
        new_frames = list(new_runtime.run())
        self.assertEqual(new_frames[-1].payload["event"], "COMMITTED")
        self.assertNotEqual(new_op, op)
        self.assertNotEqual(new_frames[-1].attempt_id, first[-1].attempt_id)
        self.rev += 1
        self.assertEqual(self.calls[-1], [
            {"role":"user","content":"Public first question"},
            {"role":"assistant","content":"Public answer"},
            {"role":"user","content":"Public follow-up"}])
        final = self.controller([self.history(limit=2),self.history(after=2,limit=2)])[-1]
        self.assertEqual([m["body"] for m in final["messages"]],
                         ["Public first question","Public answer",
                          "Public follow-up","Public second answer"])

    def test_r3_stop_keeps_history_committed_and_unknown_no_replay(self):
        self.append_user("Public question")
        self.reply = "Public provisional text"
        op, runtime = self.runtime("original-stop")
        gen = runtime.run()
        frames = [next(gen) for _ in range(4)]
        self.assertEqual(frames[-1].payload["event"], "DELTA")
        self.assertTrue(frames[-1].payload["provisional"])
        before = self.controller([self.history()])[-1]
        self.assertEqual([m["body"] for m in before["messages"]], ["Public question"])
        self.assertEqual(runtime.request_stop(op, frames[-1].attempt_id), "STOP_LATCHED")
        end = list(gen)[-1]
        self.assertEqual(dict(end.payload), {"event":"UNKNOWN_HOLD"})
        self.assertEqual(end.attempt_id, frames[-1].attempt_id)
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (end.attempt_id,)
        ).fetchone()[0], "ABORTED")
        self.assertEqual(self.controller([self.history()])[-1]["messages"], before["messages"])
        with self.assertRaises(RuntimeEventRefusal):
            list(runtime.run())
        # Even constructing a second fixture exchange cannot replay the durable user turn.
        _, second = self.runtime("different-original")
        self.assertEqual(list(second.run())[-1].payload["event"], "UNKNOWN_HOLD")
        self.assertEqual(len(self.calls), 1)

    def test_r3_fresh_resolver_detects_revision_change_before_dispatch(self):
        self.append_user("Public first question")
        op, runtime = self.runtime("original-stale")
        gen = runtime.run()
        self.assertEqual(next(gen).payload["event"], "REQUESTED")
        reserved = next(gen)
        self.assertEqual(reserved.payload["event"], "RESERVED")
        # Change durable revision without updating the runtime's original ref.
        self.append_user("Public newer question")
        end = list(gen)[-1]
        self.assertEqual(dict(end.payload), {"event":"UNKNOWN_HOLD"})
        self.assertEqual(end.operation, op)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (reserved.attempt_id,)
        ).fetchone()[0], "ABORTED")
        self.assertEqual([m["body"] for m in self.controller([self.history()])[-1]["messages"]],
                         ["Public first question","Public newer question"])

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
