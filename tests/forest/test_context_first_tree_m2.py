"""Disposable public-only in-memory SQLite fixtures; no provider calls."""
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from context_first_tree_m2 import (
    ContextRefusal, SessionContextRef, HistoryTurn, select_history,
    snapshot_in_transaction, list_open_metadata_fixture,
)
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from shared_context_b6r1 import TaskContext
from capability_registry_b6r2 import bristlecone_reference_profile, plan_selection


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        bootstrap_synthetic(self.db)
        self.journal = ForestSessionJournal(self.db)
        self.context = TaskContext("fixture-owner", "BRISTLECONE_PINE", None,
                                   "task-1", "execution-1", 1, "INTERACTIVE")
        self.sid = self.journal.create_session(
            self.context.principal_key, self.context.tree_key, "Public fixture",
            now_ms=1)["session_id"]
        self.ref = None
        self.append("user", "First public question")

    def append(self, role, body):
        rev = 0 if self.ref is None else self.ref.expected_revision
        row = self.journal.append_turn(
            self.context.principal_key, self.sid, expected_revision=rev,
            role=role, body=body, provider="ollama" if role == "assistant" else "",
            model="fixture-model" if role == "assistant" else "", now_ms=rev + 2)
        self.ref = SessionContextRef(self.context, self.sid, row["revision"],
                                     row["turn_id"])
        return row

    def read(self, requested=None, current=None, **kwargs):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            return snapshot_in_transaction(
                self.journal, self.ref if requested is None else requested,
                current=self.ref if current is None else current, **kwargs)
        finally:
            self.db.rollback()

    def test_order_and_model_metadata(self):
        self.append("assistant", "Public answer")
        self.append("user", "Next question")
        result = self.read()
        self.assertEqual([r.ordinal for r in result.messages], [1, 2, 3])
        self.assertEqual(result.messages[1].model, "fixture-model")
        self.assertEqual(result.transport_messages()[-1],
                         {"role": "user", "content": "Next question"})
        self.assertEqual(result.omitted_prefix_count, 0)

    def test_projection_copies(self):
        result = self.read()
        result.transport_messages()[0]["content"] = "changed"
        self.assertEqual(result.transport_messages()[0]["content"], "First public question")

    def test_tree_principal_task_generation_mismatch(self):
        for field, value in (("tree_key", "MAPLE"), ("principal_key", "other"),
                             ("task_id", "task-2"), ("generation", 2),
                             ("execution_context_id", "execution-2"),
                             ("origin", "BACKGROUND")):
            with self.subTest(field=field), self.assertRaisesRegex(
                    ContextRefusal, "CONTEXT_CHANGED"):
                self.read(requested=replace(self.ref, context=replace(
                    self.context, **{field: value})))

    def test_matched_references_do_not_override_sql_scope(self):
        for field, value in (("tree_key", "MAPLE"), ("principal_key", "other")):
            ref = replace(self.ref, context=replace(self.context, **{field: value}))
            with self.subTest(field=field), self.assertRaisesRegex(
                    ContextRefusal, "SESSION_SCOPE_MISMATCH"):
                self.read(requested=ref, current=ref)

    def test_clone_refused(self):
        with self.assertRaisesRegex(ContextRefusal, "CLONE_BINDING_UNAVAILABLE"):
            replace(self.ref, context=replace(self.context, clone_key="clone-a"))

    def test_session_mismatch(self):
        ref = replace(self.ref, session_id="not-found")
        with self.assertRaisesRegex(ContextRefusal, "CONTEXT_CHANGED"):
            self.read(requested=ref)
        with self.assertRaisesRegex(ContextRefusal, "SESSION_SCOPE_MISMATCH"):
            self.read(requested=ref, current=ref)

    def test_stale_revision(self):
        stale = self.ref
        self.append("user", "new")
        with self.assertRaisesRegex(ContextRefusal, "STALE_REVISION"):
            self.read(requested=stale, current=stale)

    def test_wrong_latest_user(self):
        ref = replace(self.ref, user_turn_id="wrong")
        with self.assertRaisesRegex(ContextRefusal, "LATEST_USER_MISMATCH"):
            self.read(requested=ref, current=ref)

    def test_latest_assistant_refused(self):
        self.append("assistant", "Public answer")
        with self.assertRaisesRegex(ContextRefusal, "LATEST_USER_MISMATCH"):
            self.read()

    def test_transaction_required(self):
        with self.assertRaisesRegex(ContextRefusal, "TRANSACTION_REQUIRED"):
            snapshot_in_transaction(self.journal, self.ref, current=self.ref)

    def test_pause_refused(self):
        row = self.journal.set_state(
            self.context.principal_key, self.sid,
            expected_revision=self.ref.expected_revision, next_state="PAUSED", now_ms=9)
        self.ref = replace(self.ref, expected_revision=row["revision"])
        with self.assertRaisesRegex(ContextRefusal, "SESSION_NOT_OPEN"):
            self.read()

    def test_oversize_latest_is_not_truncated(self):
        self.append("user", "é" * 2049)
        with self.assertRaisesRegex(ContextRefusal, "LATEST_USER_TOO_LARGE"):
            self.read()
        self.assertEqual(self.journal.turns(self.context.principal_key, self.sid)[-1]["body"],
                         "é" * 2049)

    def test_oversize_old_message_stops_contiguous_suffix(self):
        self.append("assistant", "x" * 5000)
        self.append("user", "new")
        snapshot = self.read()
        self.assertEqual([t.content for t in snapshot.messages], ["new"])
        self.assertEqual(snapshot.omitted_prefix_count, 2)
        self.assertEqual(len(self.journal.turns(self.context.principal_key, self.sid)), 3)

    def test_total_utf8_budget(self):
        for _ in range(5):
            self.append("user", "é" * 2048)
        snapshot = self.read()
        self.assertEqual(len(snapshot.messages), 4)
        self.assertEqual(snapshot.omitted_prefix_count, 2)

    def test_count_budget(self):
        for _ in range(20):
            self.append("user", "public")
        snapshot = self.read()
        self.assertEqual(len(snapshot.messages), 16)
        self.assertEqual(snapshot.omitted_prefix_count, 5)

    def test_malformed_history(self):
        t = self.read().messages[0]
        for rows in ((replace(t, ordinal=2),), (t,t), ()):
            with self.subTest(rows=rows), self.assertRaises(ContextRefusal):
                select_history(self.ref, rows)

    def test_invalid_revision_type(self):
        with self.assertRaises(ContextRefusal):
            replace(self.ref, expected_revision=True)

    def test_scope_before_limit_and_title_not_read(self):
        for owner, tree, ts in (("fixture-owner", "MAPLE", 30),
                                ("other", self.context.tree_key, 40)):
            self.journal.create_session(owner, tree, "other public fixture", now_ms=ts)
        blocked = []
        def authorizer(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and column in ("title", "body"):
                blocked.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(authorizer)
        try:
            rows = list_open_metadata_fixture(self.journal, self.context, limit=1)
            self.assertEqual(rows, ((self.sid, 1, 2),))
            self.assertEqual(blocked, [])
        finally:
            self.db.set_authorizer(None)

    def test_list_open_before_limit(self):
        paused = self.journal.create_session(self.context.principal_key,
            self.context.tree_key, "public paused", now_ms=40)
        self.journal.set_state(self.context.principal_key, paused["session_id"],
                               expected_revision=0, next_state="PAUSED", now_ms=41)
        self.assertEqual(list_open_metadata_fixture(self.journal, self.context, limit=1),
                         ((self.sid, 1, 2),))

    def test_invalid_list_bounds(self):
        for limit in (0, 101, True):
            with self.assertRaises(ContextRefusal):
                list_open_metadata_fixture(self.journal, self.context, limit=limit)

    def test_snapshot_does_not_write(self):
        before = self.db.total_changes
        self.read()
        self.assertEqual(self.db.total_changes, before)


if __name__ == "__main__":
    unittest.main()
