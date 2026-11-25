"""R4 status-only projection over actual disposable R3/B3 fixtures."""
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import test_runtime_events_r3 as fixture
from shared_context_b6r1 import BarkAttachment
from runtime_events_r3 import InternalEvent
from runtime_public_status_r4 import PublicRuntimeStatus, Observation, FixtureTreeBinding
from history_public_fixture_m4 import (
    PublicViewRef, HistoryPageRef, history_public_fixture_in_transaction,
)


class PublicRuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.RuntimeEventsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        # Reuse the actual R3 test transport, but use Mind's canonical Tree
        # identity and a fresh durable user turn, not an uppercase alias.
        self.fixture.sid = self.fixture.journal.create_session(
            "owner", "cherry", "public fixture", now_ms=100)["session_id"]
        self.fixture.journal.append_turn(
            "owner", self.fixture.sid, expected_revision=0, role="user",
            body="public canonical question", now_ms=101)
        latest = self.fixture.db.execute(
            "SELECT turn_id FROM forest_turns WHERE session_id=?",
            (self.fixture.sid,)).fetchone()[0]
        self.fixture.ref = replace(self.fixture.ref,
            context=replace(self.fixture.ref.context, tree_key="cherry"),
            session_id=self.fixture.sid, user_turn_id=latest)
        self.fixture.op = replace(self.fixture.op, context_ref=self.fixture.ref)
        self.op = self.fixture.op
        self.binding = FixtureTreeBinding("cherry", "CHERRY")
        self.att = BarkAttachment(
            self.op.context_ref.context, "bark-secret", "requester-secret",
            "release-secret", "seat-secret", "recipient-secret", "CHERRY", 1)
        self.p = PublicRuntimeStatus(self.op, self.att, tree_binding=self.binding)
        self.current = dict(current_operation=self.op, current_attachment=self.att,
                            current_tree_binding=self.binding)

    def observe(self, event):
        return self.p.observe(event, **self.current)

    def test_same_attachment_maps_canonical_r3_and_m4_history(self):
        runtime = self.fixture.exchange()
        frames = list(runtime.run())
        results = [self.observe(f) for f in frames]
        self.assertEqual(results[-1]["status"], "LOCAL_COMMIT_RECORDED")
        # Explicit separately resolved postcommit history request. The status
        # is not a history row, request, revision witness or delivery receipt.
        view = PublicViewRef(self.att, "fixture_request_0001")
        page = HistoryPageRef(view, self.fixture.sid, 2)
        self.fixture.db.execute("BEGIN")
        try:
            result = history_public_fixture_in_transaction(
                self.fixture.journal, page, current=page)
        finally:
            self.fixture.db.rollback()
        self.assertEqual(result["treeKey"], "CHERRY")
        self.assertEqual([m["role"] for m in result["messages"]],
                         ["user", "assistant"])
        self.assertEqual(result["messages"][-1]["text"], "fixture reply")
        self.assertEqual(self.fixture.journal.session("owner", self.fixture.sid)
                         ["tree_key"], "cherry")
        self.assertNotIn("treeKey", results[-1])

    def test_unapproved_pairs_are_not_normalized(self):
        for canonical, hint in (
            ("CHERRY", "CHERRY"), ("cherry", "cherry"),
            ("maple", "MAPLE"), ("bristlecone", "BRISTLECONE_PINE"),
            ("cherry", "MAPLE"), ("cherry", "Cherry"),
        ):
            with self.subTest(canonical=canonical, hint=hint):
                with self.assertRaisesRegex(ValueError, "UNAPPROVED_FIXTURE_TREE_PAIR"):
                    FixtureTreeBinding(canonical, hint)

    def test_wrong_tree_or_hint_refuses_even_with_matching_contexts(self):
        for key, hint in (("maple", "CHERRY"), ("cherry", "MAPLE"),
                          ("CHERRY", "CHERRY"), ("cherry", "cherry")):
            ctx = replace(self.att.context, tree_key=key)
            op = replace(self.op, context_ref=replace(self.op.context_ref,
                                                       context=ctx))
            att = replace(self.att, context=ctx, requested_tree=hint)
            with self.assertRaisesRegex(ValueError, "INVALID_FIXTURE_BINDING"):
                PublicRuntimeStatus(op, att, tree_binding=self.binding)
        with self.assertRaisesRegex(ValueError, "INVALID_FIXTURE_BINDING"):
            PublicRuntimeStatus(self.op, self.att, tree_binding=None)

    def test_current_binding_loss_or_wrong_type_withdraws_permanently(self):
        for current in (None, ("cherry", "CHERRY"), "CHERRY"):
            p = PublicRuntimeStatus(self.op, self.att, tree_binding=self.binding)
            self.assertIsNone(p.snapshot(current_operation=self.op,
                current_attachment=self.att, current_tree_binding=current))
            self.assertIsNone(p.snapshot(**self.current))

    def test_changed_hint_recipient_and_operation_withdraw(self):
        for op, att in (
            (self.op, replace(self.att, requested_tree="MAPLE")),
            (self.op, replace(self.att, recipient_id="other")),
            (replace(self.op, operation_id="new-operation"), self.att),
        ):
            p = PublicRuntimeStatus(self.op, self.att, tree_binding=self.binding)
            self.assertIsNone(p.snapshot(current_operation=op,
                current_attachment=att, current_tree_binding=self.binding))
            self.assertIsNone(p.snapshot(**self.current))

    def test_real_r3_status_sequence_never_serializes_internal_data(self):
        frames = list(self.fixture.exchange().run())
        results = [self.observe(f) for f in frames]
        self.assertIs(results[3], Observation.NO_UPDATE)
        packets = [p for p in results if type(p) is dict]
        self.assertEqual([p["status"] for p in packets],
                         ["REQUEST_PENDING", "PREPARING", "GENERATING",
                          "LOCAL_COMMIT_RECORDED"])
        for packet in packets:
            self.assertEqual(set(packet), {"schema", "status",
                "sourceAuthenticated", "permissionGranted",
                "productionAuthority", "modelExecutionPermitted", "safeActions"})
            for key in ("sourceAuthenticated", "permissionGranted",
                        "productionAuthority", "modelExecutionPermitted"):
                self.assertIs(packet[key], False)
            self.assertEqual(packet["safeActions"], [])
        wire = json.dumps(packets)
        for secret in ("fixture reply", "recipient-secret", "bark-secret",
                       self.op.operation_id + '"', frames[1].attempt_id,
                       self.op.context_ref.session_id,
                       self.op.context_ref.user_turn_id):
            self.assertNotIn(secret, wire)

    def test_stop_ack_not_terminal_and_real_abort_unknown(self):
        x = self.fixture.exchange()
        g = x.run()
        for _ in range(4):
            frame = next(g)
            self.observe(frame)
        ack = x.request_stop(self.op, frame.attempt_id)
        packet = self.p.observe_stop_ack(ack, frame.attempt_id, **self.current)
        self.assertEqual(packet["status"], "STOP_REQUESTED")
        self.assertEqual(self.observe(list(g)[-1])["status"], "UNKNOWN_HOLD")
        self.assertEqual(self.fixture.status(), ("ABORTED",))

    def test_missing_terminal_frame_is_unknown_even_if_local_commit_exists(self):
        frames = list(self.fixture.exchange().run())
        for frame in frames[:-1]:
            self.observe(frame)
        self.assertEqual(self.fixture.status(), ("COMMITTED",))
        self.assertEqual(self.p.finish(**self.current)["status"], "UNKNOWN_HOLD")
        self.assertIs(self.observe(frames[-1]), Observation.NO_UPDATE)

    def test_detach_and_reattach_cannot_revive_view(self):
        frames = list(self.fixture.exchange().run())
        self.observe(frames[0])
        self.assertIsNone(self.p.observe(frames[1],
            current_operation=self.op, current_attachment=self.att.detach(),
            current_tree_binding=self.binding))
        self.assertIsNone(self.observe(frames[2]))
        self.assertIsNone(self.p.snapshot(**self.current))
        new_att = replace(self.att, view_generation=2)
        self.assertIsNone(self.p.snapshot(current_operation=self.op,
                                           current_attachment=new_att, current_tree_binding=self.binding))

    def test_view_recipient_and_task_changes_withdraw(self):
        for att in (replace(self.att, view_generation=2),
                    replace(self.att, recipient_id="other"),
                    replace(self.att, seat_id="other"),
                    replace(self.att, context=replace(self.att.context,
                                                       generation=2))):
            p = PublicRuntimeStatus(self.op, self.att, tree_binding=self.binding)
            self.assertIsNone(p.snapshot(current_operation=self.op,
                                         current_attachment=att, current_tree_binding=self.binding))
            self.assertIsNone(p.snapshot(**self.current))

    def test_wrong_operation_and_ordinal_hold(self):
        frame = next(self.fixture.exchange().run())
        for bad in (replace(frame, ordinal=2),
                    replace(frame, ordinal=True),
                    replace(frame, operation=replace(self.op, operation_id="other"))):
            p = PublicRuntimeStatus(self.op, self.att, tree_binding=self.binding)
            self.assertEqual(p.observe(bad, **self.current)["status"], "UNKNOWN_HOLD")

    def test_wrong_attempt_or_invalid_transition_cannot_promote(self):
        frames = list(self.fixture.exchange().run())
        for bad in (replace(frames[2], attempt_id="other"),
                    replace(frames[2], payload=MappingProxyType({"event": "COMMITTED"}))):
            p = PublicRuntimeStatus(self.op, self.att, tree_binding=self.binding)
            p.observe(frames[0], **self.current)
            p.observe(frames[1], **self.current)
            self.assertEqual(p.observe(bad, **self.current)["status"], "UNKNOWN_HOLD")
            self.assertIs(p.observe(frames[-1], **self.current), Observation.NO_UPDATE)

    def test_explicit_withdrawal_returns_no_packet(self):
        self.p.withdraw()
        self.assertIsNone(self.p.finish(**self.current))
        self.assertIsNone(self.p.observe_stop_ack("STOP_LATCHED", None, **self.current))

    def test_many_deltas_never_generate_more_public_updates(self):
        frames = list(self.fixture.exchange().run())
        for f in frames[:3]:
            self.assertIsInstance(self.observe(f), dict)
        for ordinal in range(4, 104):
            f = replace(frames[3], ordinal=ordinal)
            self.assertIs(self.observe(f), Observation.NO_UPDATE)
        terminal = replace(frames[-1], ordinal=104)
        self.assertEqual(self.observe(terminal)["status"],
                         "LOCAL_COMMIT_RECORDED")
        self.assertIs(self.p.finish(**self.current), Observation.NO_UPDATE)
        with self.assertRaises(TypeError):
            json.dumps(Observation.NO_UPDATE)

    def test_repeated_stop_ack_and_delta_do_not_emit(self):
        x = self.fixture.exchange()
        g = x.run()
        for _ in range(4):
            frame = next(g)
            self.observe(frame)
        ack = x.request_stop(self.op, frame.attempt_id)
        self.assertEqual(self.p.observe_stop_ack(ack, frame.attempt_id,
                         **self.current)["status"], "STOP_REQUESTED")
        self.assertIs(self.p.observe_stop_ack(ack, frame.attempt_id,
                      **self.current), Observation.NO_UPDATE)
        self.assertEqual(self.observe(list(g)[-1])["status"], "UNKNOWN_HOLD")
        self.assertIs(self.p.finish(**self.current), Observation.NO_UPDATE)

    def test_entry_won_stop_does_not_claim_cancelled(self):
        frames = list(self.fixture.exchange().run())
        for frame in frames[:-1]:
            self.observe(frame)
        p = self.p.observe_stop_ack("COMMIT_ENTRY_ALREADY_WON",
                                    frames[1].attempt_id, **self.current)
        self.assertIs(p, Observation.NO_UPDATE)
        self.assertEqual(self.observe(frames[-1])["status"], "LOCAL_COMMIT_RECORDED")


if __name__ == "__main__":
    unittest.main()
