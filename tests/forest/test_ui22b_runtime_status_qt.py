"""Actual reactive QML consumer, same-thread disposable R4b callback."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
import test_runtime_public_delivery_r4b as fixtures
from runtime_public_delivery_r4b import DeliveryResult, PresentationCorrelation

HERE = Path(__file__).resolve().parent
APP = QGuiApplication.instance() or QGuiApplication([])
HISTORY = subprocess.check_output(
    [sys.executable, "-B", str(HERE / "ui2_m4_public_fixture.py")], text=True)


def ref(binding):
    c = binding.correlation
    return dict(requestId=c.request_id, viewKey=c.view_key, generation=c.generation)


class ReactiveStatusTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LocalDeliveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.current = self.fixture.binding
        self.engine = QQmlEngine()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(
            str(HERE / "ui22b_runtime_status_harness.qml")))
        self.assertTrue(self.component.isReady(), self.component.errorString())
        self.view = self.component.create()
        self.assertIsNotNone(self.view, self.component.errorString())
        self.assertTrue(self.view.setProperty("historyJson", HISTORY))
        self.units = []
        self.call("setupHistory")

    def tearDown(self):
        self.view.deleteLater()
        self.component.deleteLater()
        self.engine.deleteLater()
        APP.processEvents()

    def call(self, method, *args):
        if args:
            self.assertTrue(self.view.setProperty("inputJson", json.dumps(args[0], allow_nan=False)))
        self.assertTrue(QMetaObject.invokeMethod(self.view, method), method)
        # Property bindings must be updated synchronously, no event queue needed.
        self.assertFalse(self.view.property("authority"))

    def label(self, text, state="DISPLAYING"):
        self.assertEqual(self.view.property("viewState"), state)
        self.assertEqual(self.view.property("labelText"), text)
        self.assertEqual(self.view.property("labelVisible"), bool(text))
        if text:
            self.assertGreater(self.view.property("labelHeight"), 0)
        else:
            self.assertEqual(self.view.property("labelHeight"), 0)

    def attach(self):
        self.call("openView")
        self.call("setCurrent", ref(self.current))
        self.call("openLifetime", ref(self.current))
        self.label("", "ATTACHED")

    def callback(self, unit):
        self.units.append(unit)
        self.call("receiveUnit", unit)
        # Deliberately returns None: no delivery receipt.

    def delivery(self, callback=None, resolver=None):
        return self.fixture.delivery(callback=callback or self.callback,
            resolver=resolver or (lambda: self.current))

    def invalidate(self, delivery):
        c = delivery.correlation
        self.call("invalidateLifetime", dict(requestId=c.request_id,
            viewKey=c.view_key, generation=c.generation))

    def pending(self):
        self.attach()
        frames = self.fixture.frames()
        d = self.delivery()
        self.assertIs(d.observe(frames[0]), DeliveryResult.CALLBACK_RETURNED)
        self.label("REQUEST PENDING")
        return d, frames

    def new_view(self):
        self.current = replace(self.fixture.binding,
            operation=replace(self.fixture.binding.operation, operation_id="new-fixture-operation"),
            attachment=replace(self.fixture.binding.attachment, view_generation=2),
            correlation=PresentationCorrelation.fresh(2))
        self.attach()

    def test_default_off_and_explicit_open(self):
        self.label("", "CLOSED")
        self.call("setCurrent", ref(self.current))
        self.call("openLifetime", ref(self.current))
        self.label("", "CLOSED")
        self.call("openView")
        self.label("", "CLOSED")
        self.call("openLifetime", ref(self.current))
        self.label("", "ATTACHED")

    def test_real_callback_and_history_independent(self):
        self.attach()
        d = self.delivery()
        for frame in self.fixture.frames():
            d.observe(frame)
        self.label("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED")
        self.assertEqual(len(self.units), 4)
        self.assertEqual(self.view.property("historyLabel"), "HISTORY SNAPSHOT COMPLETE")
        self.assertEqual(self.view.property("historyCount"), 2)
        self.assertIs(d.withdraw(), DeliveryResult.CALLBACK_RETURNED)
        self.label("", "CLOSED")
        self.assertEqual(self.view.property("historyCount"), 2)

    def test_close_reopen_does_not_restore(self):
        self.pending()
        self.call("closeView")
        self.label("", "CLOSED")
        self.call("openView")
        self.label("", "CLOSED")
        self.call("receiveUnit", self.units[0])
        self.label("", "CLOSED")

    def test_tree_change_clears_without_callback(self):
        self.pending()
        self.call("switchTree")
        self.label("", "CLOSED")
        self.call("openView")
        self.label("", "CLOSED")

    def test_detach_clears_without_callback(self):
        self.pending()
        self.call("detach")
        self.label("", "CLOSED")

    def test_old_status_withdrawal_invalidation_and_open_ignored(self):
        d, _ = self.pending()
        d.withdraw()
        old_ref = ref(self.current)
        self.new_view()
        for unit in self.units:
            self.call("receiveUnit", unit)
        self.call("invalidateLifetime", old_ref)
        self.call("openLifetime", old_ref)
        self.label("", "ATTACHED")

    def test_sequence_gap_closes_current_view(self):
        self.pending()
        bad = dict(self.units[0], sequence=3)
        self.call("receiveUnit", bad)
        self.label("", "UNAVAILABLE")

    def test_callback_throw_after_paint_owner_clear(self):
        self.attach()
        def fail(unit):
            self.callback(unit)
            self.label("REQUEST PENDING")
            raise RuntimeError("fixture callback failure")
        d = self.delivery(callback=fail)
        f = self.fixture.frames()[0]
        self.assertIs(d.observe(f), DeliveryResult.INVALIDATED)
        self.invalidate(d)
        self.label("", "UNAVAILABLE")
        self.assertIs(d.observe(f), DeliveryResult.CLOSED)
        self.assertEqual(len(self.units), 1)

    def test_currentness_loss_before_delivery(self):
        self.attach()
        calls = 0
        def resolve():
            nonlocal calls
            calls += 1
            if calls == 2:
                self.current = None
                self.call("detach")
            return self.current
        d = self.delivery(resolver=resolve)
        self.assertIs(d.observe(self.fixture.frames()[0]), DeliveryResult.INVALIDATED)
        self.invalidate(d)
        self.label("", "CLOSED")
        self.assertEqual(self.units, [])

    def test_one_hundred_fragments_no_extra_label_callbacks(self):
        self.attach()
        frames = self.fixture.frames()
        d = self.delivery()
        for f in frames[:3]:
            d.observe(f)
        for ordinal in range(4, 104):
            self.assertIs(d.observe(replace(frames[3], ordinal=ordinal)), DeliveryResult.NO_UPDATE)
        self.label("GENERATING")
        self.assertEqual(len(self.units), 3)

    def test_compact_label_wrap_and_collapse(self):
        self.attach()
        d = self.delivery()
        for f in self.fixture.frames():
            d.observe(f)
        self.label("LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED")
        normal = self.view.property("labelHeight")
        self.assertTrue(self.view.setProperty("width", 120))
        APP.processEvents()
        self.assertGreaterEqual(self.view.property("labelHeight"), normal)
        self.call("closeView")
        self.label("", "CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
