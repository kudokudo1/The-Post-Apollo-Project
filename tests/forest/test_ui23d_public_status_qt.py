"""Actual offscreen QtQuick status item driven by disposable M4 QML state."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

HERE = Path(__file__).resolve().parent
APP = QGuiApplication.instance() or QGuiApplication([])
FIXTURE = subprocess.check_output(
    [sys.executable, "-B", str(HERE / "ui2_m4_public_fixture.py")], text=True)


class PublicStatusTests(unittest.TestCase):
    def setUp(self):
        self.engine = QQmlEngine()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(
            str(HERE / "ui23d_status_harness.qml")))
        self.assertTrue(self.component.isReady(), self.component.errorString())
        self.view = self.component.create()
        self.assertIsNotNone(self.view, self.component.errorString())
        self.assertTrue(self.view.setProperty("fixtureJson", FIXTURE))
        APP.processEvents()

    def tearDown(self):
        self.view.deleteLater()
        self.component.deleteLater()
        self.engine.deleteLater()
        APP.processEvents()

    def call(self, *methods):
        for method in methods:
            self.assertTrue(QMetaObject.invokeMethod(self.view, method), method)
            APP.processEvents()

    def label(self, expected, visible=True):
        self.assertEqual(self.view.property("labelText"), expected)
        self.assertEqual(self.view.property("statusVisible"), visible)
        self.assertFalse(self.view.property("anyAuthority"))
        self.assertEqual(self.view.property("executionText"),
            "PUBLIC FIXTURE // SEND / STOP LOCKED" if visible else "")

    def partial(self):
        self.call("attach", "openFirst", "receiveFirst")
        self.label("PARTIAL HISTORY // NEXT PAGE AVAILABLE")

    def test_default_hidden(self):
        self.label("", False)

    def test_real_m4_page_statuses(self):
        self.call("attach")
        self.label("HISTORY NOT OPEN")
        self.call("openFirst")
        self.label("HISTORY PAGE PENDING")
        self.call("receiveFirst")
        self.label("PARTIAL HISTORY // NEXT PAGE AVAILABLE")
        self.call("nextPage")
        self.label("HISTORY PAGE PENDING")
        self.call("receiveSecond")
        self.label("HISTORY SNAPSHOT COMPLETE")
        self.assertEqual(self.view.property("messageCount"), 2)

    def test_tree_change_refuses_and_clears(self):
        self.partial()
        self.call("changeTree")
        self.label("HISTORY UNAVAILABLE // OPEN AGAIN")
        self.assertEqual(self.view.property("messageCount"), 0)

    def test_detach_with_pending_page_hides_and_clears(self):
        self.partial()
        self.call("nextPage", "detach", "receiveSecond")
        self.label("", False)
        self.assertEqual(self.view.property("messageCount"), 0)

    def test_refusal_status(self):
        self.partial()
        self.call("refuse")
        self.label("HISTORY UNAVAILABLE // OPEN AGAIN")

    def test_arbitrary_reason_is_never_displayed(self):
        self.call("attach", "arbitraryReason")
        self.label("HISTORY UNAVAILABLE // OPEN AGAIN")

    def test_unknown_state_is_never_displayed(self):
        self.call("attach", "unknownState")
        self.label("HISTORY UNAVAILABLE")

    def test_display_limit_is_explicit(self):
        self.call("attach", "displayLimit")
        self.label("HISTORY DISPLAY LIMIT // SNAPSHOT CLEARED")

    def test_request_exhaustion_is_explicit(self):
        self.call("attach", "requestExhaustion")
        self.label("HISTORY REQUEST REFUSED // NEW VIEW REQUIRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
