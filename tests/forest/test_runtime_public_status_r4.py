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
from runtime_public_status_r4 import PublicRuntimeStatus


class PublicRuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.RuntimeEventsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.op = self.fixture.op
        self.att = BarkAttachment(
            self.op.context_ref.context, "bark-secret", "requester-secret",
            "release-secret", "seat-secret", "recipient-secret", "CHERRY", 1)
        self.p = PublicRuntimeStatus(self.op, self.att)
        self.current = dict(current_operation=self.op, current_attachment=self.att)

    def observe(self, event):
        return self.p.observe(event, **self.current)

    def test_real_r3_status_sequence_never_serializes_internal_data(self):
        frames = list(self.fixture.exchange().run())
        packets = [self.observe(f) for f in frames]
        self.assertEqual([p["status"] for p in packets],
                         ["REQUEST_PENDING", "PREPARING", "GENERATING",
                          "GENERATING", "LOCAL_COMMIT_RECORDED"])
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
        self.assertEqual(self.observe(frames[-1])["status"], "UNKNOWN_HOLD")

    def test_detach_and_reattach_cannot_revive_view(self):
        frames = list(self.fixture.exchange().run())
        self.observe(frames[0])
        self.assertIsNone(self.p.observe(frames[1],
            current_operation=self.op, current_attachment=self.att.detach()))
        self.assertIsNone(self.observe(frames[2]))
        self.assertIsNone(self.p.snapshot(**self.current))
        new_att = replace(self.att, view_generation=2)
        self.assertIsNone(self.p.snapshot(current_operation=self.op,
                                           current_attachment=new_att))

    def test_view_recipient_and_task_changes_withdraw(self):
        for att in (replace(self.att, view_generation=2),
                    replace(self.att, recipient_id="other"),
                    replace(self.att, seat_id="other"),
                    replace(self.att, context=replace(self.att.context,
                                                       generation=2))):
            p = PublicRuntimeStatus(self.op, self.att)
            self.assertIsNone(p.snapshot(current_operation=self.op,
                                         current_attachment=att))
            self.assertIsNone(p.snapshot(**self.current))

    def test_wrong_operation_and_ordinal_hold(self):
        frame = next(self.fixture.exchange().run())
        for bad in (replace(frame, ordinal=2),
                    replace(frame, ordinal=True),
                    replace(frame, operation=replace(self.op, operation_id="other"))):
            p = PublicRuntimeStatus(self.op, self.att)
            self.assertEqual(p.observe(bad, **self.current)["status"], "UNKNOWN_HOLD")

    def test_wrong_attempt_or_invalid_transition_cannot_promote(self):
        frames = list(self.fixture.exchange().run())
        for bad in (replace(frames[2], attempt_id="other"),
                    replace(frames[2], payload=MappingProxyType({"event": "COMMITTED"}))):
            p = PublicRuntimeStatus(self.op, self.att)
            p.observe(frames[0], **self.current)
            p.observe(frames[1], **self.current)
            self.assertEqual(p.observe(bad, **self.current)["status"], "UNKNOWN_HOLD")
            self.assertEqual(p.observe(frames[-1], **self.current)["status"], "UNKNOWN_HOLD")

    def test_explicit_withdrawal_returns_no_packet(self):
        self.p.withdraw()
        self.assertIsNone(self.p.finish(**self.current))
        self.assertIsNone(self.p.observe_stop_ack("STOP_LATCHED", None, **self.current))

    def test_entry_won_stop_does_not_claim_cancelled(self):
        frames = list(self.fixture.exchange().run())
        for frame in frames[:-1]:
            self.observe(frame)
        p = self.p.observe_stop_ack("COMMIT_ENTRY_ALREADY_WON",
                                    frames[1].attempt_id, **self.current)
        self.assertEqual(p["status"], "GENERATING")
        self.assertEqual(self.observe(frames[-1])["status"], "LOCAL_COMMIT_RECORDED")


if __name__ == "__main__":
    unittest.main()
