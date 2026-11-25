"""Disposable synchronous Qt JS callback witness, no installed UI or host.

The actual Runtime producer calls the actual UI2 consumer on the same
Python/Qt owner thread. Only allowlisted R4b units and local correlation
cross the JS boundary. No model service, private journal, or network.
"""
from dataclasses import replace
import json
from pathlib import Path
import sys
import threading
import unittest

from PySide6.QtCore import QCoreApplication
from PySide6.QtQml import QJSEngine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "forest"))
import test_runtime_public_delivery_r4b as fixtures
from runtime_public_delivery_r4b import DeliveryResult, PresentationCorrelation

APP = QCoreApplication.instance() or QCoreApplication([])


def ref_of(binding):
    if binding is None:
        return None
    c = binding.correlation
    return {"requestId": c.request_id, "viewKey": c.view_key,
            "generation": c.generation}


class SynchronousConsumerWitness(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LocalDeliveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.original = self.fixture.binding
        self.current = self.original
        self.engine = QJSEngine()
        self.thread = threading.get_ident()
        self.units = []
        self.snapshots = []
        source = ROOT / "widgets/forest/ui2/PublicRuntimeStatusDisplay.js"
        self.evaluate(source.read_text(encoding="utf-8"))
        self.evaluate("var fixtureConsumer = createConsumer();")
        self.assertEqual(self.call("open", ref_of(self.original),
                                   ref_of(self.current))["state"], "ATTACHED")

    def evaluate(self, code):
        value = self.engine.evaluate(code)
        if value.isError():
            # Only fixed test diagnostics, not arbitrary JS error content.
            raise AssertionError("QT_CONSUMER_EVALUATION_FAILED")
        return value

    def call(self, method, *args):
        # Fixed method names and JSON-only local fixture values; never
        # evaluate model text or an untrusted JS source as executable code.
        self.assertIn(method, ("open", "observe", "receive", "invalidate", "close"))
        payload = json.dumps(args, ensure_ascii=True, allow_nan=False)
        quoted = json.dumps(payload, ensure_ascii=True)
        result = self.evaluate("JSON.stringify(fixtureConsumer." + method
                               + ".apply(fixtureConsumer, JSON.parse("
                               + quoted + ")))")
        snapshot = json.loads(result.toString())
        for flag in ("sourceAuthenticated", "permissionGranted",
                     "productionAuthority", "modelExecutionPermitted",
                     "sendEnabled", "stopEnabled"):
            self.assertIs(snapshot[flag], False)
        self.assertEqual(snapshot["safeActions"], [])
        return snapshot

    def callback(self, unit):
        self.assertEqual(threading.get_ident(), self.thread)
        self.units.append(unit)
        self.snapshots.append(self.call("receive", unit, ref_of(self.current)))
        # Runtime requires None, not a JS snapshot or delivery acknowledgement.

    def make_delivery(self, resolver=None, callback=None):
        return self.fixture.delivery(resolver=resolver or (lambda: self.current),
                                     callback=callback or self.callback)

    def apply(self, delivery, method, *args):
        result = getattr(delivery, method)(*args)
        if result is DeliveryResult.INVALIDATED:
            c = delivery.correlation
            self.call("invalidate", {"requestId": c.request_id,
                "viewKey": c.view_key, "generation": c.generation})
        return result

    def state(self):
        return self.call("observe", ref_of(self.current))

    def new_view(self):
        # Independent fixture owner explicitly chooses a fresh lifetime.
        # Never re-open or replay the original operation.
        self.current = replace(self.original,
            operation=replace(self.original.operation, operation_id="new-fixture-operation"),
            attachment=replace(self.original.attachment, view_generation=2),
            correlation=PresentationCorrelation.fresh(2))
        ref = ref_of(self.current)
        self.assertEqual(self.call("open", ref, ref)["state"], "ATTACHED")

    def test_real_runtime_callback_and_ordered_withdrawal(self):
        d = self.make_delivery()
        for frame in self.fixture.frames():
            self.apply(d, "observe", frame)
        self.assertEqual([s["status"] for s in self.snapshots],
            ["REQUEST_PENDING", "PREPARING", "GENERATING", "LOCAL_COMMIT_RECORDED"])
        self.assertEqual(self.state()["label"],
                         "LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED")
        self.assertEqual([u["sequence"] for u in self.units], [1, 2, 3, 4])
        self.assertIs(self.apply(d, "withdraw"), DeliveryResult.CALLBACK_RETURNED)
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertEqual(self.units[-1]["sequence"], 5)
        self.assertIsNone(self.units[-1]["statusPacket"])

    def test_no_callback_on_one_hundred_fragments(self):
        frames = self.fixture.frames()
        d = self.make_delivery()
        for f in frames[:3]:
            self.apply(d, "observe", f)
        for ordinal in range(4, 104):
            self.assertIs(self.apply(d, "observe", replace(frames[3], ordinal=ordinal)),
                          DeliveryResult.NO_UPDATE)
        self.assertEqual(len(self.snapshots), 3)
        self.apply(d, "observe", replace(frames[-1], ordinal=104))
        self.assertEqual(self.state()["status"], "LOCAL_COMMIT_RECORDED")
        self.assertEqual([u["sequence"] for u in self.units], [1, 2, 3, 4])

    def test_change_between_projection_and_callback_invalidates_old_view(self):
        calls = 0
        def resolve():
            nonlocal calls
            calls += 1
            if calls == 4:
                # The second event was projected but cannot be delivered.
                self.current = None
            return self.current
        d = self.make_delivery(resolver=resolve)
        frames = self.fixture.frames()
        self.assertIs(self.apply(d, "observe", frames[0]), DeliveryResult.CALLBACK_RETURNED)
        self.assertIs(self.apply(d, "observe", frames[1]), DeliveryResult.INVALIDATED)
        self.assertEqual(len(self.snapshots), 1)
        self.assertEqual(self.state()["state"], "UNAVAILABLE")
        self.assertEqual(self.state()["label"], "")
        self.assertIs(self.apply(d, "observe", frames[2]), DeliveryResult.CLOSED)

    def test_callback_throws_after_paint_owner_clears_matching_lifetime(self):
        def fail_after_paint(unit):
            self.callback(unit)
            raise RuntimeError("synthetic callback failure")
        d = self.make_delivery(callback=fail_after_paint)
        f = self.fixture.frames()[0]
        self.assertIs(self.apply(d, "observe", f), DeliveryResult.INVALIDATED)
        self.assertEqual(self.snapshots[-1]["status"], "REQUEST_PENDING")
        self.assertEqual(self.state()["state"], "UNAVAILABLE")
        self.assertEqual(self.state()["label"], "")
        self.assertIs(self.apply(d, "observe", f), DeliveryResult.CLOSED)
        self.assertEqual(len(self.units), 1)

    def test_old_unit_and_withdrawal_cannot_clear_new_view(self):
        d = self.make_delivery()
        self.apply(d, "observe", self.fixture.frames()[0])
        self.apply(d, "withdraw")
        old_status, old_withdraw = self.units
        self.new_view()
        self.assertEqual(self.call("receive", old_status,
                                   ref_of(self.current))["state"], "ATTACHED")
        self.assertEqual(self.call("receive", old_withdraw,
                                   ref_of(self.current))["state"], "ATTACHED")
        self.assertEqual(self.call("invalidate", ref_of(self.original))["state"], "ATTACHED")

    def test_failed_callback_after_view_switch_never_clears_new_view(self):
        def switch_then_fail(unit):
            self.new_view()
            self.callback(unit)
            raise RuntimeError("synthetic failure")
        d = self.make_delivery(callback=switch_then_fail)
        self.assertIs(self.apply(d, "observe", self.fixture.frames()[0]),
                      DeliveryResult.INVALIDATED)
        self.assertEqual(self.snapshots[-1]["state"], "ATTACHED")
        self.assertEqual(self.state()["state"], "ATTACHED")

    def test_independent_detach_clears_without_a_withdrawal_callback(self):
        d = self.make_delivery()
        frames = self.fixture.frames()
        self.apply(d, "observe", frames[0])
        self.current = None
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertIs(self.apply(d, "observe", frames[1]), DeliveryResult.INVALIDATED)
        self.assertEqual(len(self.units), 1)
        self.assertEqual(self.state()["label"], "")

    def test_missing_terminal_stays_unknown_no_late_promotion(self):
        frames = self.fixture.frames()
        d = self.make_delivery()
        for f in frames[:-1]:
            self.apply(d, "observe", f)
        self.assertIs(self.apply(d, "finish"), DeliveryResult.CALLBACK_RETURNED)
        self.assertEqual(self.state()["status"], "UNKNOWN_HOLD")
        self.assertIs(self.apply(d, "observe", frames[-1]), DeliveryResult.INVALIDATED)
        self.assertEqual(self.state()["state"], "UNAVAILABLE")
        self.assertEqual(self.snapshots[-1]["status"], "UNKNOWN_HOLD")

    def test_stop_ack_does_not_claim_cancellation(self):
        x = self.fixture.fixture.fixture.exchange()
        g = x.run()
        d = self.make_delivery()
        for _ in range(4):
            frame = next(g)
            self.apply(d, "observe", frame)
        ack = x.request_stop(self.original.operation, frame.attempt_id)
        self.apply(d, "observe_stop_ack", ack, frame.attempt_id)
        self.assertEqual(self.state()["label"], "STOP REQUESTED // OUTCOME PENDING")
        self.apply(d, "observe", list(g)[-1])
        self.assertEqual(self.state()["status"], "UNKNOWN_HOLD")
        self.assertEqual(self.fixture.fixture.fixture.status(), ("ABORTED",))


if __name__ == "__main__":
    unittest.main(verbosity=2)
