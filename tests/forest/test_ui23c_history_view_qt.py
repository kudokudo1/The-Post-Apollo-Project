"""Actual QtQml binding lifecycle with existing disposable M4 producer output."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

HERE = Path(__file__).resolve().parent
APP = QGuiApplication.instance() or QGuiApplication([])
FIXTURE = subprocess.check_output(
    [sys.executable, "-B", str(HERE / "ui2_m4_public_fixture.py")], text=True)


class HistoryViewTests(unittest.TestCase):
    def setUp(self):
        self.engine = QQmlEngine()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(
            str(HERE / "ui23c_history_qml_harness.qml")))
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

    def check_view(self, state, count=0, pending=False):
        self.assertEqual(self.view.property("state"), state)
        self.assertEqual(self.view.property("messageCount"), count)
        self.assertEqual(self.view.property("hasRequest"), pending)
        self.assertFalse(self.view.property("authority"))

    def partial(self):
        self.call("setupView", "openFirst", "receiveFirst")
        self.check_view("PARTIAL", 1)

    def test_attachment_alone_is_not_a_request(self):
        self.check_view("CLOSED")
        self.call("openFirst", "receiveFirst")
        self.check_view("CLOSED")
        self.call("setupView")
        self.check_view("CLOSED")

    def test_actual_m4_two_pages_update_qml_bindings(self):
        self.call("setupView", "openFirst")
        self.check_view("PENDING", pending=True)
        self.assertEqual(self.view.property("cursor"), 0)
        self.call("receiveFirst")
        self.check_view("PARTIAL", 1)
        self.assertEqual(self.view.property("lastDirection"), "outgoing")
        self.call("nextPage")
        self.check_view("PENDING", 1, True)
        self.assertEqual(self.view.property("cursor"), 1)
        self.call("receiveSecond")
        self.check_view("COMPLETE", 2)
        self.assertTrue(self.view.property("complete"))
        self.assertEqual(self.view.property("lastDirection"), "incoming")
        self.assertEqual(self.view.property("lastBody"), "Public reply\nsecond line 🌲")

    def test_tree_change_clears(self):
        self.partial()
        self.call("changeTree")
        self.check_view("UNAVAILABLE")

    def test_revision_change_clears(self):
        self.partial()
        self.call("changeRevision")
        self.check_view("UNAVAILABLE")

    def test_generation_change_clears(self):
        self.partial()
        self.call("changeGeneration")
        self.check_view("UNAVAILABLE")

    def test_session_change_clears(self):
        self.partial()
        self.call("changeSession")
        self.check_view("UNAVAILABLE")

    def test_local_view_change_clears(self):
        self.partial()
        self.call("changeView")
        self.check_view("UNAVAILABLE")

    def test_detach_and_reattach_do_not_restore(self):
        self.partial()
        self.call("nextPage", "detach", "receiveSecond")
        self.check_view("CLOSED")
        self.call("reattach")
        self.check_view("CLOSED")
        self.call("receiveSecond")
        self.check_view("UNAVAILABLE")

    def test_stale_page_while_pending_clears(self):
        self.partial()
        self.call("nextPage", "receiveFirst")
        self.check_view("UNAVAILABLE")

    def test_host_refusal_clears_pending_and_rows(self):
        self.partial()
        self.call("nextPage", "reject")
        self.check_view("UNAVAILABLE")

    def test_close_history_clears(self):
        self.partial()
        self.call("close")
        self.check_view("CLOSED")
        self.call("openFirst")
        self.check_view("UNAVAILABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
