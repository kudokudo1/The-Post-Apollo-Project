"""Actual QtQml lifecycle smoke, no Quickshell, provider or real sessions."""
import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

ROOT = Path(__file__).resolve().parents[2]
APP = QGuiApplication.instance() or QGuiApplication([])


class PreviewGateTests(unittest.TestCase):
    def setUp(self):
        self.engine = QQmlEngine()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(
            str(ROOT / "widgets/forest/ui2/PublicPreviewGate.qml")))
        self.assertTrue(self.component.isReady(), self.component.errorString())
        self.gate = self.component.create()
        self.assertIsNotNone(self.gate, self.component.errorString())
        self.assertEqual(self.component.errors(), [])

    def tearDown(self):
        self.gate.deleteLater()
        self.component.deleteLater()
        self.engine.deleteLater()
        APP.processEvents()

    def set(self, **values):
        for key, value in values.items():
            self.assertTrue(self.gate.setProperty(key, value), key)
        APP.processEvents()

    def call(self, method="togglePreview"):
        self.assertTrue(QMetaObject.invokeMethod(self.gate, method))
        APP.processEvents()

    def active(self, expected):
        self.assertEqual(self.gate.property("active"), expected)

    def ready(self):
        self.set(menuOpen=True, treeKey="CHERRY", chatHostTrusted=False,
                 activeSessionCount=0, viewportUsable=True)
        self.assertTrue(self.gate.property("eligible"))
        self.active(False)

    def test_default_closed_and_missing_inputs(self):
        self.active(False)
        self.assertFalse(self.gate.property("eligible"))
        self.call()
        self.set(menuOpen=True, treeKey="CHERRY", viewportUsable=True)
        self.call()
        self.active(False)

    def test_explicit_toggle_and_dismiss(self):
        self.ready()
        self.call()
        self.active(True)
        self.call()
        self.active(False)
        self.call()
        self.call("dismissPreview")
        self.active(False)

    def test_close_and_reopen_does_not_restore(self):
        self.ready()
        self.call()
        self.active(True)
        self.set(menuOpen=False)
        self.active(False)
        self.set(menuOpen=True)
        self.active(False)

    def test_switch_tree_and_return_requires_new_opt_in(self):
        self.ready()
        self.call()
        self.set(treeKey="MAPLE")
        self.active(False)
        self.call()
        self.active(False)
        self.set(treeKey="CHERRY")
        self.active(False)

    def test_connected_host_excludes_preview(self):
        self.ready()
        self.call()
        self.set(chatHostTrusted=True)
        self.active(False)
        self.call()
        self.set(chatHostTrusted=False)
        self.active(False)

    def test_active_session_excludes_preview(self):
        self.ready()
        self.call()
        self.set(activeSessionCount=1)
        self.active(False)
        self.set(activeSessionCount=0)
        self.active(False)

    def test_unknown_session_count_excludes_preview(self):
        self.ready()
        self.call()
        self.set(activeSessionCount=-1)
        self.active(False)
        self.call()
        self.set(activeSessionCount=0)
        self.active(False)

    def test_compact_viewport_loss_resets(self):
        self.ready()
        self.call()
        self.set(viewportUsable=False)
        self.active(False)
        self.set(viewportUsable=True)
        self.active(False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
