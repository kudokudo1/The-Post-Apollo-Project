"""M4 public fixture history tests; no live DB, network or runtime."""
from dataclasses import replace
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext, BarkAttachment
from session_journal_v0 import ForestSessionJournal, bootstrap_synthetic
from context_first_tree_m2 import ContextRefusal
from history_public_fixture_m4 import (
    PublicViewRef, ListRef, HistoryPageRef, list_public_fixture_in_transaction,
    history_public_fixture_in_transaction, MAX_FRAME_BYTES, _size,
    FixtureHistoryAliases, ReadOnlyHistoryScope,
)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "public.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(lambda: self.db.close())
        bootstrap_synthetic(self.db)
        self.j = ForestSessionJournal(self.db)
        self.ctx = TaskContext("fixture-owner", "bristlecone", None,
                               "task-a", "exec-a", 1, "INTERACTIVE")
        self.attachment = BarkAttachment(self.ctx, "bark-a", "requester-a",
            "release-a", "seat-a", "recipient-a", "BRISTLECONE_PINE", 1)
        self.view = PublicViewRef(self.attachment, "fixture_request_001")
        self.sid = self.j.create_session("fixture-owner", "bristlecone",
                                        "not used in display", now_ms=1)["session_id"]
        self.rev = 0

    def add(self, role, text):
        result = self.j.append_turn("fixture-owner", self.sid, expected_revision=self.rev,
            role=role, body=text, provider="ollama" if role == "assistant" else "",
            model="model-a" if role == "assistant" else "", now_ms=self.rev + 2)
        self.rev = result["revision"]
        return result

    def page(self, after=0, limit=16):
        return HistoryPageRef(self.view, self.sid, self.rev, after, limit)

    def read(self, ref=None, current=None, fn=history_public_fixture_in_transaction):
        ref = self.page() if ref is None else ref
        self.db.execute("BEGIN")
        try:
            return fn(self.j, ref, current=ref if current is None else current)
        finally:
            self.db.rollback()

    def test_empty_session(self):
        result = self.read()
        self.assertEqual(result["messages"], [])
        self.assertTrue(result["complete"])

    def test_history_includes_durable_reply_and_no_model_metadata(self):
        self.add("user", "Public question")
        self.add("assistant", "Public reply\nsecond line")
        result = self.read()
        self.assertEqual([r["role"] for r in result["messages"]], ["user","assistant"])
        self.assertEqual(result["messages"][1]["text"], "Public reply\nsecond line")
        self.assertEqual(set(result["messages"][1]), {"turn_id","ordinal","role","text"})
        self.assertEqual(set(result), {"schema","requestId","treeKey","generation",
                                      "sessionId","revision","messages","complete"})
        self.assertTrue(result["complete"])

    def test_page_continuity(self):
        for i in range(5):
            self.add("user", f"Public {i}")
        first = self.read(self.page(limit=2))
        self.assertFalse(first["complete"])
        second = self.read(replace(self.page(after=2, limit=2),
                                  view=replace(self.view, request_id="fixture_request_002")))
        third = self.read(self.page(after=4, limit=2))
        self.assertEqual([r["ordinal"] for p in (first,second,third)
                          for r in p["messages"]], [1,2,3,4,5])
        self.assertTrue(third["complete"])

    def test_lookahead_body_not_read_until_its_page(self):
        self.add("user", "Public first")
        self.add("assistant", "Public next")
        # Synthetic corruption: SQLite cannot decode this text as UTF-8.
        self.db.execute("UPDATE forest_turns SET body=CAST(X'FF' AS TEXT) "
                        "WHERE session_id=? AND ordinal=2", (self.sid,))
        self.db.commit()
        first = self.read(self.page(limit=1))
        self.assertEqual([r["text"] for r in first["messages"]], ["Public first"])
        self.assertFalse(first["complete"])
        with self.assertRaisesRegex(ContextRefusal, "STORAGE_REFUSED"):
            self.read(self.page(after=1, limit=1))

    def test_lookahead_gap_refused_before_body_read(self):
        for text in ("Public first", "Public second", "Public third"):
            self.add("user", text)
        self.db.execute("DELETE FROM forest_turns WHERE session_id=? AND ordinal=2",
                        (self.sid,))
        self.db.commit()
        denied = []
        def auth(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and column in ("body", "title"):
                denied.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(auth)
        try:
            with self.assertRaisesRegex(ContextRefusal, "INVALID_HISTORY_ORDER"):
                self.read(self.page(limit=1))
            self.assertEqual(denied, [])
        finally:
            self.db.set_authorizer(None)

    def test_empty_page_does_not_query_body(self):
        self.add("user", "Public first")
        denied = []
        def auth(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and column in ("body", "title"):
                denied.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(auth)
        try:
            page = self.read(self.page(after=1))
            self.assertEqual(page["messages"], [])
            self.assertTrue(page["complete"])
            self.assertEqual(denied, [])
        finally:
            self.db.set_authorizer(None)

    def test_frame_cap_preserves_full_rows(self):
        for _ in range(6):
            self.add("user", "é" * 8000)
        first = self.read()
        self.assertLessEqual(_size(first), MAX_FRAME_BYTES)
        self.assertFalse(first["complete"])
        self.assertGreater(len(first["messages"]), 0)
        self.assertTrue(all(r["text"] == "é"*8000 for r in first["messages"]))
        after = first["messages"][-1]["ordinal"]
        second = self.read(self.page(after=after))
        self.assertTrue(second["complete"])
        self.assertEqual(len(first["messages"]) + len(second["messages"]), 6)

    def test_old_revision_rejected_between_pages(self):
        self.add("user", "Public question")
        stale = self.page()
        self.add("assistant", "Public reply")
        with self.assertRaisesRegex(ContextRefusal, "STALE_REVISION"):
            self.read(stale)

    def test_scope_before_body(self):
        self.add("user", "Public question")
        for ctx in (replace(self.ctx, tree_key="maple"),
                    replace(self.ctx, principal_key="other")):
            view = replace(self.view, attachment=replace(self.attachment, context=ctx))
            ref = replace(self.page(), view=view)
            denied = []
            def auth(action, table, column, *_):
                if action == sqlite3.SQLITE_READ and column in ("body","title"):
                    denied.append(column)
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            self.db.set_authorizer(auth)
            try:
                with self.assertRaisesRegex(ContextRefusal, "SESSION_SCOPE_MISMATCH"):
                    self.read(ref)
                self.assertEqual(denied, [])
            finally:
                self.db.set_authorizer(None)

    def test_view_changes_refuse(self):
        original = self.page()
        for field, value in (("recipient_id","recipient-b"),("view_generation",2),
                             ("seat_id","seat-b"),("release_id","release-b")):
            changed = replace(self.view, attachment=replace(self.attachment, **{field:value}))
            with self.subTest(field=field), self.assertRaisesRegex(ContextRefusal,"VIEW_CHANGED"):
                self.read(original, replace(original, view=changed))
        with self.assertRaisesRegex(ContextRefusal,"VIEW_CHANGED"):
            self.read(original, replace(original, after=1))

    def test_detached_and_clone_refused(self):
        with self.assertRaisesRegex(ContextRefusal,"INVALID_VIEW"):
            PublicViewRef(self.attachment.detach(), self.view.request_id)
        with self.assertRaisesRegex(ContextRefusal,"INVALID_VIEW"):
            PublicViewRef(replace(self.attachment,context=replace(self.ctx,clone_key="clone-a")),
                          self.view.request_id)

    def test_invalid_cursor(self):
        with self.assertRaisesRegex(ContextRefusal,"INVALID_CURSOR"):
            self.read(self.page(after=1))

    def test_unsafe_controls_refused_not_changed(self):
        self.add("user", "Public\u202e text")
        with self.assertRaisesRegex(ContextRefusal,"INVALID_DISPLAY_TEXT"):
            self.read()
        self.assertEqual(self.j.turns("fixture-owner",self.sid)[0]["body"],"Public\u202e text")

    def test_history_order_gap_refused(self):
        self.add("user","one")
        self.add("assistant","two")
        self.db.execute("DELETE FROM forest_turns WHERE ordinal=1")
        self.db.commit()
        with self.assertRaisesRegex(ContextRefusal,"INVALID_HISTORY_ORDER"):
            self.read()

    def test_restart_new_task_preserves_committed_history(self):
        self.add("user","Public question")
        self.add("assistant","Public reply")
        old = self.page()
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.j = ForestSessionJournal(self.db)
        ctx = replace(self.ctx, task_id="task-b", execution_context_id="exec-b", generation=2)
        view = PublicViewRef(replace(self.attachment, context=ctx, view_generation=2),
                             "fixture_request_002")
        current = replace(old, view=view)
        with self.assertRaisesRegex(ContextRefusal,"VIEW_CHANGED"):
            self.read(old, current)
        self.assertEqual([x["text"] for x in self.read(current)["messages"]],
                         ["Public question","Public reply"])
        self.assertEqual(self.j.session("fixture-owner",self.sid)["revision"],2)

    def test_list_scope_title_body_denial(self):
        self.j.create_session("fixture-owner","maple","other",now_ms=100)
        self.j.create_session("other","bristlecone","other",now_ms=101)
        denied = []
        def auth(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and column in ("title","body"):
                denied.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(auth)
        try:
            frame = self.read(ListRef(self.view,1), fn=list_public_fixture_in_transaction)
            self.assertEqual(frame["sessions"], [{"session_id":self.sid,"title":"Public conversation",
                                                  "revision":0,"updated_at_ms":1}])
            self.assertEqual(set(frame),{"schema","requestId","treeKey","generation","sessions"})
            self.assertEqual(denied,[])
        finally:
            self.db.set_authorizer(None)

    def test_paused_history_refused(self):
        self.j.set_state("fixture-owner",self.sid,expected_revision=0,next_state="PAUSED",now_ms=2)
        self.rev = 1
        with self.assertRaisesRegex(ContextRefusal,"SESSION_NOT_OPEN"):
            self.read()

    def test_no_transaction_refused(self):
        with self.assertRaisesRegex(ContextRefusal,"TRANSACTION_REQUIRED"):
            history_public_fixture_in_transaction(self.j,self.page(),current=self.page())

    def test_read_does_not_mutate(self):
        self.add("user","Public question")
        before = self.db.total_changes
        self.read()
        self.read(ListRef(self.view),fn=list_public_fixture_in_transaction)
        self.assertEqual(self.db.total_changes,before)

    def test_bad_page_limits_and_bool(self):
        for kwargs in ({"limit":0},{"limit":17},{"after":True},{"revision":True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ContextRefusal):
                replace(self.page(),**kwargs)



class ReadOnlyAliasTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "r6-public.sqlite"
        self.db = sqlite3.connect(self.path)
        self.addCleanup(lambda: self.db.close())
        bootstrap_synthetic(self.db)
        self.j = ForestSessionJournal(self.db)
        self.sid = self.j.create_session("fixture-owner", "cherry",
                                        "Not a public title", now_ms=1)["session_id"]
        self.attachment = BarkAttachment(
            TaskContext("fixture-owner", "cherry", None, "history-task-a",
                        "read-context-a", 1, "INTERACTIVE"),
            "bark-a", "requester-a", "release-a", "seat-a", "recipient-a",
            "CHERRY", 1)
        self.aliases = FixtureHistoryAliases("fixture-owner", self.sid)
        self.rev = 0
        self.ids = []

    def add(self, role, text):
        row = self.j.append_turn("fixture-owner", self.sid,
            expected_revision=self.rev, role=role, body=text,
            provider="ollama" if role == "assistant" else "",
            model="fixture-model" if role == "assistant" else "",
            now_ms=self.rev + 2)
        self.rev = row["revision"]
        self.ids.append(row["turn_id"])

    def transaction(self, method, *args, **kwargs):
        self.db.execute("BEGIN")
        try:
            return method(self.j, *args, **kwargs)
        finally:
            self.db.rollback()

    def scope(self, attachment=None, *, current=None, view_key="a"*32):
        attachment = self.attachment if attachment is None else attachment
        return self.transaction(self.aliases.scope_in_transaction, attachment,
            current_attachment=attachment if current is None else current,
            view_key=view_key)

    def page(self, scope, *, current=None, request_id="b"*32, after=0, limit=2):
        return self.transaction(self.aliases.page_in_transaction, scope,
            current=scope if current is None else current,
            request_id=request_id, after=after, limit=limit)

    def test_metadata_offer_never_reads_title_or_body(self):
        self.add("user", "Public question")
        reads = []
        def auth(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and column in ("body", "title"):
                reads.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(auth)
        try:
            scope = self.scope()
            self.assertEqual(reads, [])
            self.assertEqual(scope.public_fields(), {
                "treeKey":"CHERRY", "generation":1, "sessionId":scope.session_alias,
                "revision":1, "viewKey":"a"*32})
            self.assertNotEqual(scope.session_alias, self.sid)
        finally:
            self.db.set_authorizer(None)

    def test_empty_and_two_page_projection_no_raw_identifiers(self):
        empty = self.page(self.scope())
        self.assertTrue(empty["complete"])
        self.assertEqual(empty["messages"], [])
        for role, text in (("user","One"), ("assistant","Two"),
                           ("user","Three"), ("assistant","Four")):
            self.add(role, text)
        scope = self.scope()
        first = self.page(scope)
        second = self.page(scope, request_id="c"*32, after=2)
        rows = first["messages"] + second["messages"]
        self.assertFalse(first["complete"])
        self.assertTrue(second["complete"])
        self.assertEqual([r["ordinal"] for r in rows], [1,2,3,4])
        self.assertEqual([r["text"] for r in rows], ["One","Two","Three","Four"])
        self.assertEqual(first["sessionId"], scope.session_alias)
        self.assertEqual(second["requestId"], "c"*32)
        self.assertEqual(len({r["turn_id"] for r in rows}), 4)
        for r in rows:
            self.assertRegex(r["turn_id"], r"^[0-9a-f]{32}$")
            self.assertNotIn(r["turn_id"], self.ids + [scope.session_alias])
        self.assertEqual(self.page(scope, request_id="d"*32)["messages"],
                         first["messages"])

    def test_reopen_same_connection_owner_preserves_aliases_without_new_turn(self):
        self.add("user", "Public question")
        self.add("assistant", "Public answer")
        old = self.scope()
        first = self.page(old)
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.j = ForestSessionJournal(self.db)
        ctx = replace(self.attachment.context, task_id="history-task-b",
                      execution_context_id="read-context-b", generation=2)
        self.attachment = replace(self.attachment, context=ctx, view_generation=2)
        fresh = self.scope(view_key="c"*32)
        self.assertEqual(fresh.session_alias, old.session_alias)
        self.assertEqual(fresh.revision, 2)
        with self.assertRaisesRegex(ContextRefusal, "VIEW_CHANGED"):
            self.page(old, current=fresh)
        before = self.db.total_changes
        reopened = self.page(fresh, request_id="d"*32)
        self.assertEqual(reopened["messages"], first["messages"])
        self.assertEqual(reopened["generation"], 2)
        self.assertEqual(self.db.total_changes, before)

    def test_stale_revision_and_wrong_alias_before_body(self):
        self.add("user", "Public question")
        old = self.scope()
        self.add("assistant", "Public answer")
        reads = []
        def auth(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and column in ("body", "title"):
                reads.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(auth)
        try:
            with self.assertRaisesRegex(ContextRefusal, "STALE_REVISION"):
                self.page(old)
            wrong = replace(old, session_alias="e"*32)
            with self.assertRaisesRegex(ContextRefusal, "VIEW_CHANGED"):
                self.page(wrong)
            self.assertEqual(reads, [])
        finally:
            self.db.set_authorizer(None)

    def test_attachment_exact_currentness_and_tree_scope(self):
        for changed in (self.attachment.detach(),
                replace(self.attachment, recipient_id="recipient-b"),
                replace(self.attachment, context=replace(
                    self.attachment.context, tree_key="maple")),
                replace(self.attachment, context=replace(
                    self.attachment.context, principal_key="other")),
                replace(self.attachment, requested_tree="MAPLE"),
                replace(self.attachment, context=replace(
                    self.attachment.context, clone_key="clone-a"))):
            with self.assertRaises(ContextRefusal):
                self.scope(current=changed)
            if changed.recipient_id != "recipient-b":
                with self.assertRaises(ContextRefusal):
                    self.scope(changed)
        with self.assertRaisesRegex(ContextRefusal, "TRANSACTION_REQUIRED"):
            self.aliases.scope_in_transaction(self.j, self.attachment,
                current_attachment=self.attachment, view_key="a"*32)

    def test_fixed_trial_limits_and_ascii_refusal(self):
        self.add("user", "Public question")
        self.add("assistant", "Non ASCII \u00e9")
        scope = self.scope()
        for kwargs in ({"limit":3}, {"limit":True}, {"after":True},
                       {"request_id":"not-a-token"}):
            with self.assertRaises(ContextRefusal):
                self.page(scope, **kwargs)
        with self.assertRaisesRegex(ContextRefusal, "INVALID_R6_FIXTURE_TEXT"):
            self.page(scope)
        self.assertEqual(self.aliases._turn_aliases, {})
        for _ in range(4):
            self.add("user", "Extra row")
        with self.assertRaises(ContextRefusal):
            self.scope()

    def test_collision_refuses_without_partial_mapping(self):
        self.add("user", "One")
        self.add("assistant", "Two")
        scope = self.scope()
        with patch("history_public_fixture_m4.secrets.token_hex",
                   side_effect=["f"*32, "f"*32]):
            with self.assertRaisesRegex(ContextRefusal, "PUBLIC_ALIAS_COLLISION"):
                self.page(scope)
        self.assertEqual(self.aliases._turn_aliases, {})
        self.assertEqual(len(self.page(scope)["messages"]), 2)


if __name__ == "__main__":
    unittest.main()
