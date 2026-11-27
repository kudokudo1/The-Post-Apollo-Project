"""M6 composition regression: actual B3/M2/M4/UI2, injected public stream only."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import threading
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "forest"))
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from turn_bridge_b3 import ForestTurnBridge, BridgeRefusal, bootstrap_attempts_synthetic
from shared_context_b6r1 import TaskContext, BarkAttachment
from context_first_tree_m2 import ContextRefusal, SessionContextRef
from runtime_stop_control_r2 import RuntimeStopControl
from runtime_events_r3 import OperationRef, RuntimeExchange, RuntimeEventRefusal
from runtime_public_status_r4 import FixtureTreeBinding, Observation, PublicRuntimeStatus
from runtime_public_conversation_r5 import PublicConversationHost, FixtureHostRefusal
from runtime_public_delivery_r4b import PresentationCorrelation
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

    def attachment(self):
        return BarkAttachment(self.context, "bark-a", "requester-a",
            "release-a", "seat-a", "recipient-a", "CHERRY", self.context.generation)

    def history(self, *, after=0, limit=16, revision=None, attachment=None,
                current_attachment=None):
        revision = self.rev if revision is None else revision
        attachment = self.attachment() if attachment is None else attachment
        current_attachment = attachment if current_attachment is None else current_attachment
        rid = "fixture_request_" + str(self.tick()).zfill(4)
        ref = HistoryPageRef(PublicViewRef(attachment, rid), self.sid, revision, after, limit)
        # Distinct immutable original/current refs. Test host only, not custody.
        current = replace(ref, view=PublicViewRef(current_attachment, rid))
        self.db.execute("BEGIN")
        try:
            frame = history_public_fixture_in_transaction(self.journal, ref, current=current)
        finally:
            self.db.rollback()
        fields = {"requestId":rid,"treeKey":attachment.requested_tree,"generation":attachment.view_generation,
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

    def projector(self, op, attachment):
        binding = FixtureTreeBinding("cherry", "CHERRY")
        p = PublicRuntimeStatus(op, attachment, tree_binding=binding)
        # Fixture owner selects the pair independently of presentation inputs.
        current = dict(current_operation=op, current_attachment=attachment,
                       current_tree_binding=FixtureTreeBinding("cherry", "CHERRY"))
        return p, current

    def assert_status(self, packet, status):
        self.assertEqual(packet, {
            "schema":"postapollo.forest.public-runtime-status.v1",
            "status":status, "sourceAuthenticated":False,
            "permissionGranted":False, "productionAuthority":False,
            "modelExecutionPermitted":False, "safeActions":[]})

    def first_light_http(self, *, lines):
        # Reuse the existing B2 disposable HTTP peer; do not substitute the
        # B3 streamer or contact an installed Ollama daemon. Independent
        # subclass state prevents reuse of another transport test's input.
        from test_ollama_chat_transport import FakeOllama

        class Peer(FakeOllama):
            pass

        Peer.lines = lines
        Peer.observed = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), Peer)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def close():
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

        self.addCleanup(close)
        endpoint = "http://127.0.0.1:%d" % server.server_address[1]
        return Peer, endpoint

    def first_light_runtime(self, operation_id, endpoint):
        # Actual default B2 transport, exact M2 reference and existing R3
        # operation/STOP lifetime, only the disposable HTTP peer is fake.
        bridge = ForestTurnBridge(self.journal, clock_ms=self.tick)
        op = OperationRef(self.ref, operation_id)
        runtime = RuntimeExchange(bridge, op,
            resolve_current_context=self.resolve_fixture_context,
            model="fixture-model", max_predict=32, num_ctx=2048,
            endpoint=endpoint)
        return op, runtime

    def test_first_light_exact_single_prompt_through_actual_http_transport(self):
        from test_ollama_chat_transport import packet
        prompt = "Public first light: café."
        self.append_user(prompt)
        peer, endpoint = self.first_light_http(lines=[
            packet("Public ", message={"role": "assistant", "content": "Public ",
                                      "thinking": "Fixture trace not for display"}),
            packet("reply", done=True),
        ])
        op, runtime = self.first_light_runtime("first-light-commit", endpoint)
        gen = runtime.run()
        self.addCleanup(gen.close)
        for name in ("REQUESTED", "RESERVED", "STARTED"):
            self.assertEqual(next(gen).payload["event"], name)
        delta = next(gen)
        self.assertEqual(delta.operation, op)
        self.assertEqual(dict(delta.payload),
                         {"event": "DELTA", "text": "Public ", "provisional": True})
        self.assertEqual(peer.observed, [("POST", "/api/chat", {
            "model": "fixture-model", "messages": [{"role": "user", "content": prompt}],
            "stream": True, "options": {"num_predict": 32, "num_ctx": 2048},
        })])
        self.assertEqual([m["body"] for m in self.display(self.history())["messages"]],
                         [prompt])
        terminal = list(gen)[-1]
        self.assertEqual(terminal.operation, op)
        self.assertEqual(terminal.attempt_id, delta.attempt_id)
        self.assertEqual(terminal.payload["event"], "COMMITTED")
        self.assertEqual(terminal.payload["text"], "Public reply")
        self.rev += 1
        self.assertEqual([m["body"] for m in self.display(self.history())["messages"]],
                         [prompt, "Public reply"])
        self.assertEqual(self.db.execute(
            "SELECT status,reply_turn_id FROM forest_attempts_b3 WHERE attempt_id=?",
            (terminal.attempt_id,)).fetchone(),
            ("COMMITTED", terminal.payload["turn_id"]))
        self.assertEqual(len(peer.observed), 1)

    def test_first_light_stop_does_not_persist_partial_or_replay_http(self):
        from test_ollama_chat_transport import packet
        prompt = "Public first light STOP fixture."
        self.append_user(prompt)
        peer, endpoint = self.first_light_http(lines=[
            packet("Provisional public text"), packet(" not committed", done=True),
        ])
        op, runtime = self.first_light_runtime("first-light-stop", endpoint)
        gen = runtime.run()
        self.addCleanup(gen.close)
        for name in ("REQUESTED", "RESERVED", "STARTED"):
            self.assertEqual(next(gen).payload["event"], name)
        delta = next(gen)
        self.assertEqual(delta.payload["event"], "DELTA")
        self.assertEqual(delta.operation, op)
        self.assertEqual(runtime.request_stop(op, delta.attempt_id), "STOP_LATCHED")
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?",
            (delta.attempt_id,)).fetchone(), ("RESERVED",))
        end = list(gen)[-1]
        self.assertEqual(end.attempt_id, delta.attempt_id)
        self.assertEqual(dict(end.payload), {"event": "UNKNOWN_HOLD"})
        self.assertEqual(self.db.execute(
            "SELECT status,reply_turn_id FROM forest_attempts_b3 WHERE attempt_id=?",
            (delta.attempt_id,)).fetchone(), ("ABORTED", None))
        self.assertEqual([m["body"] for m in self.display(self.history())["messages"]],
                         [prompt])
        with self.assertRaisesRegex(RuntimeEventRefusal, "OPERATION_ALREADY_USED"):
            list(runtime.run())
        _, second = self.first_light_runtime("first-light-no-replay", endpoint)
        self.assertEqual(list(second.run())[-1].payload["event"], "UNKNOWN_HOLD")
        self.assertEqual(len(peer.observed), 1)

    def test_first_light_actual_host_isolates_two_trials_from_existing_history(self):
        # Actual FL3 host, actual B2 HTTP, and a separate preexisting M6
        # journal. This is a disposable sentinel, NOT personal data.
        from unittest.mock import patch, call
        import first_light_trial_host as fl
        from ollama_chat_transport import stream_chat
        from test_ollama_chat_transport import packet

        self.append_user("Public sentinel: must not reach either trial.")
        self.commit()
        before = tuple(self.db.iterdump())
        changes = self.db.total_changes
        peer, endpoint = self.first_light_http(
            lines=[packet("First trial reply"), packet(" complete", done=True)])

        def transport(**options):
            # Only the test endpoint is substituted; B2 builds the request.
            options["endpoint"] = endpoint
            yield from stream_chat(**options)

        def reject_existing_access(action, *args):
            accesses.append(action)
            return sqlite3.SQLITE_DENY

        accesses = []
        original_connect = sqlite3.connect
        self.db.set_authorizer(reject_existing_access)
        try:
            with patch.object(sqlite3, "connect", wraps=original_connect) as opened:
                operations = []
                for stop in (False, True):
                    host = fl.FirstLightTrialHost(test_transport=transport)
                    gen = None
                    try:
                        op = host.submit(fl.PROMPT)
                        operations.append(op)
                        trial_db = host._db
                        self.assertEqual(
                            [(name, filename) for _, name, filename in
                             trial_db.execute("PRAGMA database_list")],
                            [("main", "")])
                        self.assertEqual(trial_db.execute(
                            "SELECT revision FROM forest_sessions").fetchall(), [(1,)])
                        self.assertEqual(trial_db.execute(
                            "SELECT role,body FROM forest_turns").fetchall(),
                            [("user", fl.PROMPT)])
                        gen = host.run_internal()
                        if stop:
                            for event in ("REQUESTED", "RESERVED", "STARTED", "DELTA"):
                                frame = next(gen)
                                self.assertEqual(frame.payload["event"], event)
                            self.assertEqual(host.request_stop(op, frame.attempt_id),
                                             "STOP_LATCHED")
                            self.assertEqual(list(gen)[-1].payload["event"], "UNKNOWN_HOLD")
                            self.assertEqual(trial_db.execute(
                                "SELECT role,body FROM forest_turns").fetchall(),
                                [("user", fl.PROMPT)])
                            expected = "ABORTED_LOCAL"
                        else:
                            terminal = list(gen)[-1]
                            self.assertEqual(terminal.operation, op)
                            self.assertEqual(terminal.payload["event"], "COMMITTED")
                            self.assertEqual(trial_db.execute(
                                "SELECT role,body FROM forest_turns ORDER BY ordinal").fetchall(),
                                [("user", fl.PROMPT), ("assistant", "First trial reply complete")])
                            expected = "COMMITTED_LOCAL"
                        self.assertEqual(host.local_outcome(), expected)
                        self.assertEqual(host.close(), expected)
                        with self.assertRaises(sqlite3.ProgrammingError):
                            trial_db.execute("SELECT 1")
                    finally:
                        if gen is not None:
                            gen.close()
                        if not host._closed:
                            host.close()
                self.assertNotEqual(operations[0].context_ref.session_id,
                                    operations[1].context_ref.session_id)
                self.assertNotEqual(operations[0].operation_id, operations[1].operation_id)
                self.assertEqual(opened.call_args_list,
                                 [call(":memory:"), call(":memory:")])
            expected_post = ("POST", "/api/chat", {
                "model": fl.MODEL, "messages": [{"role": "user", "content": fl.PROMPT}],
                "stream": True, "options": {"num_predict": 32, "num_ctx": 2048},
            })
            self.assertEqual(peer.observed, [expected_post, expected_post])
            self.assertEqual(accesses, [])
        finally:
            self.db.set_authorizer(None)
        self.assertEqual(tuple(self.db.iterdump()), before)
        self.assertEqual(self.db.total_changes, changes)

    def test_r4a_status_and_committed_history_after_restart(self):
        self.append_user("Public first question")
        op, runtime = self.runtime("status-first")
        att = self.attachment()
        projector, current = self.projector(op, att)
        gen = runtime.run()
        for expected in ("REQUEST_PENDING", "PREPARING", "GENERATING"):
            self.assert_status(projector.observe(next(gen), **current), expected)
        delta = next(gen)
        self.assertEqual(delta.payload["event"], "DELTA")
        self.assertIs(projector.observe(delta, **current), Observation.NO_UPDATE)
        old_page = self.history(attachment=att)
        before = self.controller([old_page])[-1]
        self.assertTrue(before["complete"])
        self.assertEqual([m["body"] for m in before["messages"]], ["Public first question"])
        self.assert_status(projector.snapshot(**current), "GENERATING")
        receipt = list(gen)[-1]
        self.assertEqual(receipt.payload["event"], "COMMITTED")
        self.assert_status(projector.observe(receipt, **current), "LOCAL_COMMIT_RECORDED")
        self.assertIs(projector.finish(**current), Observation.NO_UPDATE)
        # A status packet is not a page. Old revision is refused; only explicit
        # new M4 requests may render the committed response.
        old_rev = self.rev
        self.rev += 1
        with self.assertRaisesRegex(ContextRefusal, "STALE_REVISION"):
            self.history(revision=old_rev, attachment=att)
        self.assertEqual(self.controller([old_page], {"revision":self.rev})[-1]["messages"], [])
        first = self.controller([self.history(limit=1, attachment=att),
                                 self.history(after=1, limit=1, attachment=att)])[-1]
        self.assertEqual([m["body"] for m in first["messages"]],
                         ["Public first question", "Public answer"])
        self.assertEqual(self.journal.session("fixture-owner", self.sid)["tree_key"], "cherry")
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.journal = ForestSessionJournal(self.db)
        self.context = replace(self.context, task_id="task-b",
                               execution_context_id="exec-b", generation=2)
        att2 = self.attachment()
        self.assertIsNone(projector.snapshot(**dict(current, current_attachment=att2)))
        self.assertIsNone(projector.snapshot(**current))
        reopened = self.controller([self.history(attachment=att2)])[-1]
        self.assertEqual(reopened["messages"], first["messages"])
        self.append_user("Public follow-up")
        self.reply = "Public second answer"
        op2, runtime2 = self.runtime("status-second")
        p2, c2 = self.projector(op2, att2)
        self.assert_status(p2.snapshot(**c2), "IDLE")
        frames = list(runtime2.run())
        observations = [p2.observe(f, **c2) for f in frames]
        self.assertIs(observations[3], Observation.NO_UPDATE)
        self.assert_status(observations[-1], "LOCAL_COMMIT_RECORDED")
        self.assertNotEqual(op2, op)
        self.assertNotEqual(frames[-1].attempt_id, receipt.attempt_id)
        self.assertEqual(self.calls[-1], [
            {"role":"user","content":"Public first question"},
            {"role":"assistant","content":"Public answer"},
            {"role":"user","content":"Public follow-up"}])
        self.rev += 1
        final = self.controller([self.history(limit=2, attachment=att2),
                                 self.history(after=2, limit=2, attachment=att2)])[-1]
        self.assertEqual([m["body"] for m in final["messages"]],
                         ["Public first question", "Public answer",
                          "Public follow-up", "Public second answer"])

    def test_r4a_stop_status_is_not_history_or_terminal_ack(self):
        self.append_user("Public question")
        self.reply = "Public provisional text"
        op, runtime = self.runtime("status-stop")
        att = self.attachment()
        projector, current = self.projector(op, att)
        gen = runtime.run()
        for expected in ("REQUEST_PENDING", "PREPARING", "GENERATING"):
            self.assert_status(projector.observe(next(gen), **current), expected)
        delta = next(gen)
        self.assertIs(projector.observe(delta, **current), Observation.NO_UPDATE)
        ack = runtime.request_stop(op, delta.attempt_id)
        self.assertEqual(ack, "STOP_LATCHED")
        self.assert_status(projector.observe_stop_ack(ack, delta.attempt_id, **current),
                           "STOP_REQUESTED")
        before = self.controller([self.history(attachment=att)])[-1]
        self.assertEqual([m["body"] for m in before["messages"]], ["Public question"])
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (delta.attempt_id,)
        ).fetchone()[0], "RESERVED")
        end = list(gen)[-1]
        self.assert_status(projector.observe(end, **current), "UNKNOWN_HOLD")
        self.assertIs(projector.finish(**current), Observation.NO_UPDATE)
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (delta.attempt_id,)
        ).fetchone()[0], "ABORTED")
        self.assertEqual(self.controller([self.history(attachment=att)])[-1]["messages"],
                         before["messages"])
        _, again = self.runtime("status-stop-other-operation")
        self.assertEqual(list(again.run())[-1].payload["event"], "UNKNOWN_HOLD")
        self.assertEqual(len(self.calls), 1)

    def test_r4a_view_withdrawal_does_not_cancel_durable_operation(self):
        self.append_user("Public question")
        op, runtime = self.runtime("status-withdraw")
        att = self.attachment()
        projector, current = self.projector(op, att)
        gen = runtime.run()
        for expected in ("REQUEST_PENDING", "PREPARING", "GENERATING"):
            self.assert_status(projector.observe(next(gen), **current), expected)
        delta = next(gen)
        self.assertIs(projector.observe(delta, **current), Observation.NO_UPDATE)
        old_page = self.history(attachment=att)
        # View recipient changes but the task and its original operation do not.
        changed = replace(att, recipient_id="recipient-b", view_generation=2)
        self.assertIsNone(projector.snapshot(**dict(current, current_attachment=changed)))
        self.assertIsNone(projector.snapshot(**current))
        with self.assertRaisesRegex(ContextRefusal, "VIEW_CHANGED"):
            self.history(attachment=att, current_attachment=changed)
        cleared = self.controller([old_page], {"generation":2, "viewKey":"new-view"})[-1]
        self.assertEqual(cleared["state"], "UNAVAILABLE")
        self.assertEqual(cleared["messages"], [])
        # No STOP request was made; the fixture can finish internally.
        end = list(gen)[-1]
        self.assertEqual(end.payload["event"], "COMMITTED")
        self.assertIsNone(projector.observe(end, **current))
        self.assertIsNone(projector.finish(**current))
        self.rev += 1
        self.assertEqual(self.db.execute(
            "SELECT status FROM forest_attempts_b3 WHERE attempt_id=?", (delta.attempt_id,)
        ).fetchone()[0], "COMMITTED")
        # Explicit independently resolved public history, not old status replay.
        refreshed = self.controller([self.history(attachment=changed,
                                                  current_attachment=changed)])[-1]
        self.assertEqual([m["body"] for m in refreshed["messages"]],
                         ["Public question", "Public answer"])
        self.assertEqual(len(self.calls), 1)

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



class ConnectedHistoryRevision(unittest.TestCase):
    """Actual R5 owner fixture + actual UI2 history controller; no UI sender."""

    def test_r5b_reopen_and_commit_between_pages_requires_explicit_fresh_snapshot(self):
        current = None
        units = []

        def open_lifetime(ref):
            nonlocal current
            current = PresentationCorrelation(ref["requestId"], ref["viewKey"],
                                              ref["generation"])
            return True

        def invalidate(ref):
            nonlocal current
            if current is not None and current.view_key == ref["viewKey"]:
                current = None

        # The status callback only records local fixture units. It never
        # opens history or sends a packet to the history controller.
        with PublicConversationHost(open_lifetime=open_lifetime,
                current_view=lambda: current, receive_unit=units.append,
                invalidate_lifetime=invalidate) as host:
            def finish():
                for _ in range(8):
                    outcome = host.advance()
                    if outcome != "ACTIVE":
                        self.assertEqual(outcome, "TERMINAL")
                        return
                self.fail("bounded R5 fixture did not finish")

            host.start_next()
            finish()
            old_view = current
            original_db = host._db
            original_task = host._binding.operation.context_ref.context
            original_first = host.history_page(limit=1)
            original_second = host.history_page(after=1, limit=1,
                expected_revision=original_first["revision"], expected_view=old_view)
            self.assertEqual(original_first["revision"], 2)
            self.assertTrue(original_second["complete"])
            self.assertEqual(host.reopen_journal(), "JOURNAL_REOPENED")
            with self.assertRaises(sqlite3.ProgrammingError):
                original_db.execute("SELECT 1")
            self.assertIsNot(host._db, original_db)
            self.assertIsNone(current)
            with self.assertRaises(FixtureHostRefusal):
                host.history_page()
            host.start_next()
            self.assertNotEqual(current, old_view)
            self.assertNotEqual(host._binding.operation.context_ref.context, original_task)
            # REQUESTED, RESERVED, STARTED, DELTA: second answer is provisional.
            for _ in range(4):
                self.assertEqual(host.advance(), "ACTIVE")
            first = host.history_page(limit=2)
            self.assertEqual(first["revision"], 3)
            self.assertFalse(first["complete"])
            view_key = current.view_key
            self.assertEqual(first["generation"], current.generation)
            self.assertEqual(first["sessionId"], original_first["sessionId"])
            self.assertEqual(first["messages"],
                             original_first["messages"] + original_second["messages"])
            self.assertEqual(len(first["messages"]), 2)
            with self.assertRaisesRegex(FixtureHostRefusal, "HISTORY_CONTINUATION_UNAVAILABLE"):
                host.history_page(after=2, limit=2, expected_revision=first["revision"],
                                  expected_view=old_view)
            finish()
            self.assertEqual(current.view_key, view_key)
            # The actual merged host refuses the old revision and missing pins.
            for pins in ({}, {"expected_revision":first["revision"], "expected_view":current}):
                with self.assertRaisesRegex(FixtureHostRefusal, "HISTORY_CONTINUATION_UNAVAILABLE"):
                    host.history_page(after=2, limit=2, **pins)
            # An independent receiver-defense fixture, NOT an alternate R5
            # history API or an automatic fallback after a refused request.
            # R5b rejects stale/unpinned continuations at its host boundary.
            # Exercise UI2 defense even if a valid M4 page for a different
            # explicit revision is accidentally routed to the old request.
            def independently_project(revision, request_id):
                self.assertEqual(current.view_key, view_key)
                attachment = host._binding.attachment
                self.assertEqual(attachment.view_generation, current.generation)
                req = HistoryPageRef(PublicViewRef(attachment, request_id),
                                     first["sessionId"], revision, 2, 2)
                db = sqlite3.connect(host._path)
                try:
                    journal = ForestSessionJournal(db)
                    db.execute("BEGIN")
                    observed = host._binding
                    self.assertEqual(observed.correlation, current)
                    resolved = HistoryPageRef(
                        PublicViewRef(observed.attachment, request_id),
                        first["sessionId"], revision, 2, 2)
                    return history_public_fixture_in_transaction(
                        journal, req, current=resolved)
                finally:
                    db.rollback()
                    db.close()

            fresh = host.history_page(limit=2)
            self.assertEqual(fresh["revision"], 4)
            continuation = independently_project(
                fresh["revision"], "receiver_fixture_wrong_revision_0001")
            self.assertEqual(continuation["revision"], 4)
            self.assertEqual(continuation["generation"], first["generation"])
            self.assertEqual(continuation["sessionId"], first["sessionId"])
            fresh_next = host.history_page(after=2, limit=2,
                expected_revision=fresh["revision"], expected_view=current)
            self.assertEqual(fresh["revision"], fresh_next["revision"])
            self.assertEqual(len({f["requestId"] for f in
                (first, continuation, fresh, fresh_next)}), 4)
            # The fixed R5 host owns one immutable canonical session, with
            # no caller-selected database, Tree or session. This is not a
            # generic selectable-session write authorization test.
            db = sqlite3.connect(host._path)
            try:
                self.assertEqual(db.execute(
                    "SELECT session_id,tree_key,revision FROM forest_sessions"
                ).fetchall(), [(first["sessionId"], "cherry", 4)])
                self.assertEqual(db.execute(
                    "SELECT status FROM forest_attempts_b3 ORDER BY created_at_ms"
                ).fetchall(), [("COMMITTED",), ("COMMITTED",)])
            finally:
                db.close()

            # Both defensive paths use the real controller: observe the
            # independently changed revision, or receive a mismatched
            # continuation before the observer reports that change.
            # A fresh explicit open is the only recovery; never append
            # pages across revisions or infer history from status.
            script = """
const fs=require("fs"), vm=require("vm"), assert=require("node:assert/strict");
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync(process.argv[1],"utf8"),ctx);
const {first,continuation,fresh,freshNext,viewKey}=JSON.parse(fs.readFileSync(0,"utf8"));
const scope=f=>({treeKey:f.treeKey,generation:f.generation,
    sessionId:f.sessionId,revision:f.revision,viewKey});
const old=scope(first), now=scope(fresh);
function unavailable(s) {
    assert.equal(s.state,"UNAVAILABLE");
    assert.equal(s.complete,false);
    assert.deepEqual(Array.from(s.messages),[]);
    assert.equal(s.request,null);
    assert.equal(s.sourceAuthenticated,false);
    assert.equal(s.permissionGranted,false);
}
for(const observed of [true,false]) {
    const c=ctx.createController();
    assert.equal(c.open(old,first.requestId,2).state,"PENDING");
    const partial=c.receive(first,old);
    assert.equal(partial.state,"PARTIAL");
    assert.equal(partial.messages.length,2);
    const pending=c.next(old,continuation.requestId,2);
    assert.equal(pending.state,"PENDING");
    assert.equal(pending.request.revision,first.revision);
    assert.equal(pending.request.after,2);
    if(observed) unavailable(c.observe(now));
    unavailable(c.receive(continuation,observed?now:old));
    unavailable(c.next(now,continuation.requestId,2));
    assert.equal(c.open(now,fresh.requestId,2).state,"PENDING");
    assert.equal(c.receive(fresh,now).state,"PARTIAL");
    assert.equal(c.next(now,freshNext.requestId,2).state,"PENDING");
    const final=c.receive(freshNext,now);
    assert.equal(final.state,"COMPLETE");
    assert.deepEqual(Array.from(final.messages,m=>m.ordinal),[1,2,3,4]);
    assert.deepEqual(Array.from(final.messages,m=>m.body),[
        "What is a Tree?","Public fixture: a Tree is a Forest agent identity.",
        "What does its journal preserve?","Public fixture: committed conversation turns."]);
    assert.equal(final.permissionGranted,false);
    assert.equal(final.sourceAuthenticated,false);
}
"""
            # Only M4 public pages and local view correlation reach Node.
            subprocess.run(["node", "-e", script,
                str(ROOT / "widgets/forest/ui2/PublicHistoryDisplay.js")],
                input=json.dumps(dict(first=first, continuation=continuation,
                    fresh=fresh, freshNext=fresh_next, viewKey=view_key)),
                text=True, capture_output=True, check=True, timeout=10)


if __name__ == "__main__":
    unittest.main()
