"""R5 host uses real UI2 reactive QML and real B1/B3/M4 disposable journal."""
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts/forest"))
import runtime_public_conversation_r5 as r5
from runtime_public_conversation_r5 import PublicConversationHost, FixtureHostRefusal
from runtime_public_delivery_r4b import PresentationCorrelation

APP = QGuiApplication.instance() or QGuiApplication([])


class ConnectedPublicConversation(unittest.TestCase):
    def setUp(self):
        self.engine = QQmlEngine()
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(
            str(HERE / "ui22b_runtime_status_harness.qml")))
        self.assertTrue(self.component.isReady(), self.component.errorString())
        self.view = self.component.create()
        self.assertIsNotNone(self.view, self.component.errorString())
        self.current = None
        self.units = []
        self.mode = "normal"
        self.call("openView")
        self.host = PublicConversationHost(open_lifetime=self.open_lifetime,
            current_view=lambda: self.current, receive_unit=self.receive,
            invalidate_lifetime=self.invalidate)
        self.addCleanup(self.host.close)

    def tearDown(self):
        self.host.close()
        self.view.deleteLater()
        self.component.deleteLater()
        self.engine.deleteLater()
        APP.processEvents()

    def call(self, method, value=None):
        if value is not None:
            self.assertTrue(self.view.setProperty("inputJson", json.dumps(value)))
        self.assertTrue(QMetaObject.invokeMethod(self.view, method))
        self.assertFalse(self.view.property("authority"))

    def open_lifetime(self, ref):
        self.current = PresentationCorrelation(ref["requestId"], ref["viewKey"],
                                               ref["generation"])
        self.call("setCurrent", ref)
        self.call("openLifetime", ref)
        return self.view.property("viewState") == "ATTACHED"

    def invalidate(self, ref):
        self.call("invalidateLifetime", ref)

    def receive(self, unit):
        self.units.append(unit)
        if self.mode == "switch":
            self.mode = "normal"
            self.replacement = PresentationCorrelation.fresh(10)
            self.open_lifetime(dict(requestId=self.replacement.request_id,
                viewKey=self.replacement.view_key, generation=10))
        self.call("receiveUnit", unit)
        if self.mode == "throw":
            self.mode = "normal"
            raise RuntimeError("fixture failure after painting")
        # A refusal on the still-current consumer fails locally, not a receipt.
        if self.current and unit["viewKey"] == self.current.view_key:
            expected = "DISPLAYING" if unit["kind"] == "STATUS" else "CLOSED"
            if self.view.property("viewState") != expected:
                raise RuntimeError("fixture consumer refused")

    def finish_turn(self):
        for _ in range(8):
            outcome = self.host.advance()
            if outcome != "ACTIVE":
                self.assertEqual(outcome, "TERMINAL")
                return
        self.fail("bounded fake turn did not terminate")

    def history_text(self):
        return [m["text"] for m in self.host.history_page()["messages"]]

    def render_history(self, limit):
        first = self.host.history_page(limit=limit)
        second = self.host.history_page(after=limit, limit=limit,
            expected_revision=first["revision"], expected_view=self.current)
        def page(frame):
            return {"ref": dict(requestId=frame["requestId"], treeKey=frame["treeKey"],
                generation=frame["generation"], sessionId=frame["sessionId"],
                revision=frame["revision"], limit=limit), "frame": frame}
        self.assertTrue(self.view.setProperty("historyJson",
            json.dumps([page(first), page(second)])))
        self.call("setupHistory")
        self.assertEqual(self.view.property("historyLabel"), "HISTORY SNAPSHOT COMPLETE")
        return self.view.property("historyCount")

    def test_r7d_c_actual_writer_order_separate_fixture(self):
        events = []
        db = self.host._db
        def audit(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and (table, column) in (
                    ("forest_sessions", "title"), ("forest_turns", "body")):
                events.append(column.upper())
            if action == sqlite3.SQLITE_INSERT and table in (
                    "forest_turns", "forest_attempts_b3"):
                events.append("APPEND_SQL" if table == "forest_turns" else "RESERVE_SQL")
            return sqlite3.SQLITE_OK
        def spy(label, fn):
            def call(*a, **kw):
                events.append(label)
                return fn(*a, **kw)
            return call
        db.set_authorizer(audit)
        try:
            with patch.object(self.host, "_open", spy("VIEW_OPEN", self.host._open)), \
                 patch.object(self.host, "_view", spy("VIEW_CURRENT", self.host._view)), \
                 patch.object(self.host._journal, "append_turn",
                              spy("APPEND_CALL", self.host._journal.append_turn)), \
                 patch.object(r5, "TaskContext", spy("CONTEXT", r5.TaskContext)), \
                 patch.object(r5.RuntimeExchange, "run", spy("GENERATOR", r5.RuntimeExchange.run)), \
                 patch.object(self.host, "_fake_stream", spy("FAKE_STREAM", self.host._fake_stream)):
                self.host.start_next()
                for a, b in zip(("VIEW_OPEN", "VIEW_CURRENT", "TITLE", "APPEND_CALL",
                                 "APPEND_SQL", "CONTEXT"),
                                ("VIEW_CURRENT", "TITLE", "APPEND_CALL", "APPEND_SQL",
                                 "CONTEXT", "GENERATOR")):
                    self.assertLess(events.index(a), events.index(b))
                self.assertNotIn("RESERVE_SQL", events)
                self.assertNotIn("FAKE_STREAM", events)
                self.assertEqual(db.execute("SELECT revision FROM forest_sessions").fetchone(), (1,))
                self.assertEqual(self.host.advance(), "ACTIVE")  # REQUESTED
                self.assertNotIn("RESERVE_SQL", events)
                before = len(events)
                self.assertEqual(self.host.advance(), "ACTIVE")  # RESERVED
                reservation = events[before:]
                self.assertLess(reservation.index("BODY"), reservation.index("RESERVE_SQL"))
                self.assertNotIn("TITLE", reservation)
                self.assertNotIn("FAKE_STREAM", events)
                self.assertEqual(db.execute("SELECT expected_revision,status FROM forest_attempts_b3").fetchall(),
                                 [(1, "RESERVED")])
                self.finish_turn()
                self.assertLess(events.index("RESERVE_SQL"), events.index("FAKE_STREAM"))
        finally:
            db.set_authorizer(None)
        self.assertEqual(db.execute("SELECT revision FROM forest_sessions").fetchone(), (2,))
        self.assertEqual(db.execute("SELECT expected_revision,status FROM forest_attempts_b3").fetchall(),
                         [(1, "COMMITTED")])
        self.assertEqual(db.execute("SELECT role FROM forest_turns ORDER BY ordinal").fetchall(),
                         [("user",), ("assistant",)])

    def test_two_explicit_turns_actual_status_history_and_stop(self):
        self.host.start_next()
        self.finish_turn()
        self.assertEqual(self.view.property("labelText"),
                         "LOCAL COMMIT RECORDED // DELIVERY UNCONFIRMED")
        self.assertEqual(self.view.property("historyCount"), 0)
        self.assertEqual(self.render_history(1), 2)
        old = self.units[-1]
        old_ref = self.current
        self.host.start_next()
        with self.assertRaises(FixtureHostRefusal):
            self.host.stop(old_ref)
        self.call("receiveUnit", old)
        self.assertEqual(self.view.property("viewState"), "ATTACHED")
        self.finish_turn()
        self.assertEqual(self.view.property("historyCount"), 2)
        self.assertEqual(self.render_history(2), 4)
        self.assertEqual(self.history_text(), [
            "What is a Tree?", "Public fixture: a Tree is a Forest agent identity.",
            "What does its journal preserve?", "Public fixture: committed conversation turns."])
        self.host.start_next()
        for _ in range(4):
            self.assertEqual(self.host.advance(), "ACTIVE")
        self.assertEqual(self.view.property("labelText"), "GENERATING")
        self.host.stop(self.current)
        self.assertEqual(self.view.property("labelText"), "STOP REQUESTED // OUTCOME PENDING")
        self.finish_turn()
        self.assertEqual(self.view.property("labelText"), "UNKNOWN HOLD // NO AUTOMATIC RETRY")
        self.assertEqual(self.view.property("historyCount"), 4)
        self.assertEqual(self.history_text()[-1], "Public STOP demonstration")
        self.assertEqual(len(self.history_text()), 5)
        # Verify committed SQLite bytes independently of status display.
        with sqlite3.connect(self.host._path) as db:
            self.assertEqual(db.execute("SELECT status FROM forest_attempts_b3 "
                "ORDER BY created_at_ms").fetchall(),
                [("COMMITTED",), ("COMMITTED",), ("ABORTED",)])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM forest_turns "
                "WHERE role='assistant'").fetchone()[0], 2)

    def test_explicit_reopen_preserves_committed_pair_and_fresh_next_lifetime(self):
        self.host.start_next()
        self.finish_turn()
        old_ref = self.current
        old_status = self.units[-1]
        original_db = self.host._db
        original_session = self.host._session
        self.assertEqual(self.host.reopen_journal(), "JOURNAL_REOPENED")
        with self.assertRaises(sqlite3.ProgrammingError):
            original_db.execute("SELECT 1")
        self.assertIsNot(self.host._db, original_db)
        self.assertEqual(self.host._session, original_session)
        self.assertEqual(self.view.property("labelText"), "")
        with self.assertRaises(FixtureHostRefusal):
            self.host.advance()
        with self.assertRaises(FixtureHostRefusal):
            self.host.history_page()
        with self.assertRaises(FixtureHostRefusal):
            self.host.reopen_journal()
        self.host.start_next()
        self.assertNotEqual(self.current, old_ref)
        self.call("receiveUnit", old_status)
        self.assertEqual(self.view.property("viewState"), "ATTACHED")
        self.finish_turn()
        self.assertEqual(self.render_history(2), 4)
        self.assertEqual(self.history_text(), [
            "What is a Tree?", "Public fixture: a Tree is a Forest agent identity.",
            "What does its journal preserve?", "Public fixture: committed conversation turns."])

    def test_continuation_rejects_changed_revision_and_view(self):
        self.host.start_next()
        for _ in range(4):
            self.assertEqual(self.host.advance(), "ACTIVE")
        first = self.host.history_page(limit=1)
        old_ref = self.current
        self.assertEqual(first["revision"], 1)
        with self.assertRaisesRegex(FixtureHostRefusal, "HISTORY_CONTINUATION_UNAVAILABLE"):
            self.host.history_page(after=1, limit=1)
        self.finish_turn()
        with self.assertRaisesRegex(FixtureHostRefusal, "HISTORY_CONTINUATION_UNAVAILABLE"):
            self.host.history_page(after=1, limit=1,
                expected_revision=first["revision"], expected_view=old_ref)
        fresh = self.host.history_page(limit=1)
        page = self.host.history_page(after=1, limit=1,
            expected_revision=fresh["revision"], expected_view=old_ref)
        self.assertEqual(page["messages"][0]["role"], "assistant")
        self.assertNotEqual(fresh["requestId"], page["requestId"])
        self.host.start_next()
        current = self.host.history_page(limit=1)
        with self.assertRaisesRegex(FixtureHostRefusal, "HISTORY_CONTINUATION_UNAVAILABLE"):
            self.host.history_page(after=1, limit=1,
                expected_revision=current["revision"], expected_view=old_ref)
        self.finish_turn()

    def test_reopen_refuses_active_or_aborted_turn(self):
        self.host.start_next()
        self.host.advance()
        with self.assertRaisesRegex(FixtureHostRefusal, "REOPEN_UNAVAILABLE"):
            self.host.reopen_journal()
        for _ in range(3):
            self.host.advance()
        self.host.stop(self.current)
        self.finish_turn()
        with self.assertRaisesRegex(FixtureHostRefusal, "REOPEN_UNAVAILABLE"):
            self.host.reopen_journal()
        with self.assertRaises(FixtureHostRefusal):
            self.host.start_next()

    def test_callback_failure_after_paint_does_not_retry_or_cancel_execution(self):
        self.host.start_next()
        self.mode = "throw"
        self.assertEqual(self.host.advance(), "ACTIVE")
        self.assertEqual(self.view.property("viewState"), "UNAVAILABLE")
        self.finish_turn()
        self.assertEqual(len(self.units), 1)
        with self.assertRaises(FixtureHostRefusal):
            self.host.history_page()
        with sqlite3.connect(self.host._path) as db:
            self.assertEqual(db.execute("SELECT status FROM forest_attempts_b3").fetchone(),
                             ("COMMITTED",))

    def test_callback_switch_without_throw_keeps_new_view_and_stops_old_delivery(self):
        self.host.start_next()
        self.mode = "switch"
        self.assertEqual(self.host.advance(), "ACTIVE")
        self.assertEqual(self.view.property("viewState"), "ATTACHED")
        self.finish_turn()
        self.assertEqual(len(self.units), 1)
        self.assertEqual(self.view.property("viewState"), "ATTACHED")

    def test_detach_independent_of_execution_and_no_stale_status(self):
        self.host.start_next()
        self.host.advance()
        self.current = None
        self.call("detach")
        self.host.observe_view()
        self.assertEqual(self.view.property("viewState"), "CLOSED")
        self.finish_turn()
        self.assertEqual(len(self.units), 1)
        self.assertEqual(self.view.property("labelText"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
