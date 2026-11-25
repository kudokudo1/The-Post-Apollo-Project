"""R4b uses real R4a/R3/B3 fixture, recording callback only; no UI sender."""
import json
import sys
import threading
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import test_runtime_public_status_r4 as fixtures
from runtime_public_delivery_r4b import (
    PresentationCorrelation, FixtureDeliveryBinding, LocalFixtureDelivery,
    DeliveryResult,
)


class LocalDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.PublicRuntimeStatusTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.corr = PresentationCorrelation.fresh(self.fixture.att.view_generation)
        self.binding = FixtureDeliveryBinding(self.fixture.op, self.fixture.att,
                                             self.fixture.binding, self.corr)
        self.current = self.binding
        self.units = []

    def delivery(self, resolver=None, callback=None):
        return LocalFixtureDelivery(self.binding,
            resolve_current=resolver or (lambda: self.current),
            deliver=callback or self.units.append)

    def frames(self):
        return list(self.fixture.fixture.exchange().run())

    def test_real_runtime_only_transition_units_and_no_internal_data(self):
        frames = self.frames()
        d = self.delivery()
        results = [d.observe(f) for f in frames]
        self.assertEqual(results, [DeliveryResult.CALLBACK_RETURNED] * 3
            + [DeliveryResult.NO_UPDATE, DeliveryResult.CALLBACK_RETURNED])
        self.assertEqual([u["sequence"] for u in self.units], [1, 2, 3, 4])
        self.assertEqual([u["statusPacket"]["status"] for u in self.units],
            ["REQUEST_PENDING", "PREPARING", "GENERATING", "LOCAL_COMMIT_RECORDED"])
        for u in self.units:
            self.assertEqual(set(u), {"requestId", "viewKey", "generation",
                                     "sequence", "kind", "statusPacket"})
            self.assertEqual(u["requestId"], self.corr.request_id)
            self.assertEqual(u["viewKey"], self.corr.view_key)
            self.assertEqual(u["generation"], self.corr.generation)
        wire = json.dumps(self.units)
        for secret in (frames[1].attempt_id, self.fixture.op.context_ref.session_id,
                       self.fixture.op.context_ref.user_turn_id, "fixture reply",
                       "recipient-secret", "bark-secret"):
            self.assertNotIn(secret, wire)
        self.assertIs(d.finish(), DeliveryResult.NO_UPDATE)
        self.assertEqual(len(self.units), 4)

    def test_many_deltas_do_not_trigger_callbacks(self):
        frames = self.frames()
        d = self.delivery()
        for f in frames[:3]:
            d.observe(f)
        for ordinal in range(4, 104):
            self.assertIs(d.observe(replace(frames[3], ordinal=ordinal)),
                          DeliveryResult.NO_UPDATE)
        self.assertEqual(len(self.units), 3)
        d.observe(replace(frames[-1], ordinal=104))
        self.assertEqual([u["sequence"] for u in self.units], [1, 2, 3, 4])

    def test_changed_recipient_between_projection_and_delivery_refuses(self):
        calls = 0
        def resolve():
            nonlocal calls
            calls += 1
            return (self.binding if calls == 1 else replace(self.binding,
                attachment=replace(self.binding.attachment, recipient_id="new")))
        d = self.delivery(resolve)
        self.assertIs(d.observe(self.frames()[0]), DeliveryResult.INVALIDATED)
        self.assertEqual(self.units, [])
        self.assertIs(d.withdraw(), DeliveryResult.CLOSED)

    def test_old_withdrawal_and_status_never_target_new_view(self):
        frames = self.frames()
        d = self.delivery()
        d.observe(frames[0])
        newer = PresentationCorrelation.fresh(2)
        self.current = replace(self.binding, correlation=newer,
                               attachment=replace(self.binding.attachment,
                                                  view_generation=2))
        self.assertIs(d.withdraw(), DeliveryResult.INVALIDATED)
        self.assertIs(d.observe(frames[1]), DeliveryResult.CLOSED)
        self.assertEqual(len(self.units), 1)
        self.assertNotEqual(self.units[0]["viewKey"], newer.view_key)

    def test_explicit_current_withdrawal_is_one_ordered_null_unit(self):
        frames = self.frames()
        d = self.delivery()
        d.observe(frames[0])
        self.assertIs(d.withdraw(), DeliveryResult.CALLBACK_RETURNED)
        self.assertEqual(self.units[-1]["kind"], "WITHDRAW")
        self.assertIsNone(self.units[-1]["statusPacket"])
        self.assertEqual(self.units[-1]["sequence"], 2)
        self.assertIs(d.withdraw(), DeliveryResult.CLOSED)
        self.assertIs(d.observe(frames[1]), DeliveryResult.CLOSED)

    def test_provenance_loss_closes_without_callback_even_if_restored(self):
        frames = self.frames()
        d = self.delivery()
        d.observe(frames[0])
        self.current = None
        self.assertIs(d.observe(frames[1]), DeliveryResult.INVALIDATED)
        self.current = self.binding
        self.assertIs(d.observe(frames[1]), DeliveryResult.CLOSED)
        self.assertEqual(len(self.units), 1)

    def test_lost_terminal_and_late_frame_not_promoted(self):
        frames = self.frames()
        d = self.delivery()
        for f in frames[:-1]:
            d.observe(f)
        self.assertIs(d.finish(), DeliveryResult.CALLBACK_RETURNED)
        self.assertEqual(self.units[-1]["statusPacket"]["status"], "UNKNOWN_HOLD")
        self.assertIs(d.observe(frames[-1]), DeliveryResult.INVALIDATED)
        self.assertEqual(self.units[-1]["statusPacket"]["status"], "UNKNOWN_HOLD")

    def test_stop_ack_not_terminal_and_abort_remains_unknown(self):
        x = self.fixture.fixture.exchange()
        g = x.run()
        d = self.delivery()
        for _ in range(4):
            f = next(g)
            d.observe(f)
        ack = x.request_stop(self.fixture.op, f.attempt_id)
        d.observe_stop_ack(ack, f.attempt_id)
        self.assertEqual(self.units[-1]["statusPacket"]["status"], "STOP_REQUESTED")
        self.assertIs(d.observe_stop_ack(ack, f.attempt_id), DeliveryResult.NO_UPDATE)
        d.observe(list(g)[-1])
        self.assertEqual(self.units[-1]["statusPacket"]["status"], "UNKNOWN_HOLD")

    def test_callback_failure_invalidates_without_retry(self):
        def callback(unit):
            self.units.append(unit)
            raise RuntimeError("private error after callback")
        d = self.delivery(callback=callback)
        f = self.frames()[0]
        self.assertIs(d.observe(f), DeliveryResult.INVALIDATED)
        self.assertIs(d.observe(f), DeliveryResult.CLOSED)
        self.assertEqual(len(self.units), 1)
        self.assertNotIn("private error", json.dumps(self.units))

    def test_reentrant_callback_invalidates_without_second_unit(self):
        def callback(unit):
            self.units.append(unit)
            self.assertIs(d.withdraw(), DeliveryResult.INVALIDATED)
        d = self.delivery(callback=callback)
        self.assertIs(d.observe(self.frames()[0]), DeliveryResult.INVALIDATED)
        self.assertEqual(len(self.units), 1)
        self.assertIs(d.finish(), DeliveryResult.CLOSED)

    def test_reentrant_withdrawal_cannot_report_callback_success(self):
        def callback(unit):
            self.units.append(unit)
            self.assertIs(d.finish(), DeliveryResult.INVALIDATED)
        d = self.delivery(callback=callback)
        self.assertIs(d.withdraw(), DeliveryResult.INVALIDATED)
        self.assertEqual(len(self.units), 1)
        self.assertEqual(self.units[0]["kind"], "WITHDRAW")
        self.assertIs(d.withdraw(), DeliveryResult.CLOSED)

    def test_non_none_callback_result_invalidates_not_acknowledges(self):
        def callback(unit):
            self.units.append(unit)
            return True
        d = self.delivery(callback=callback)
        self.assertIs(d.observe(self.frames()[0]), DeliveryResult.INVALIDATED)
        self.assertEqual(len(self.units), 1)
        self.assertIs(d.finish(), DeliveryResult.CLOSED)

    def test_async_callback_refuses_at_construction(self):
        async def callback(unit):
            self.units.append(unit)
        with self.assertRaisesRegex(ValueError, "INVALID_DELIVERY_DEPENDENCY"):
            self.delivery(callback=callback)
        self.assertEqual(self.units, [])

    def test_wrong_thread_refuses_without_mutation(self):
        d = self.delivery()
        f = self.frames()[0]
        errors = []
        def other():
            try:
                d.observe(f)
            except ValueError as exc:
                errors.append(str(exc))
        worker = threading.Thread(target=other)
        worker.start()
        worker.join()
        self.assertEqual(errors, ["WRONG_OWNER_THREAD"])
        self.assertEqual(self.units, [])
        self.assertIs(d.observe(f), DeliveryResult.CALLBACK_RETURNED)

    def test_sequence_exhaustion_invalidates_without_wrap_or_callback(self):
        # Exercise the boundary directly; no billions of fixture units.
        frames = self.frames()
        d = self.delivery()
        d._sequence = 2**53 - 2
        self.assertIs(d.observe(frames[0]), DeliveryResult.CALLBACK_RETURNED)
        self.assertEqual(self.units[-1]["sequence"], 2**53 - 1)
        self.assertIs(d.observe(frames[1]), DeliveryResult.INVALIDATED)
        self.assertEqual(len(self.units), 1)
        self.assertIs(d.withdraw(), DeliveryResult.CLOSED)

    def test_generation_rejects_bool_and_unsafe_integer(self):
        for generation in (True, 0, -1, 2**53, 1.0):
            with self.subTest(generation=generation):
                with self.assertRaises(ValueError):
                    PresentationCorrelation.fresh(generation)

    def test_invalid_correlation_or_generation_refuses(self):
        with self.assertRaises(ValueError):
            PresentationCorrelation("operation", "view", 1)
        with self.assertRaises(ValueError):
            replace(self.binding, correlation=PresentationCorrelation.fresh(2))


if __name__ == "__main__":
    unittest.main()
