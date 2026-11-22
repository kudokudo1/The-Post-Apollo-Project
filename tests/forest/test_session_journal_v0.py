"""Forest B1 // synthetic only: no user files, agent keys or host permissions."""
import importlib.util
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[2] / "scripts/forest/session_journal_v0.py"
spec = importlib.util.spec_from_file_location("forest_journal_v0", FILE)
assert spec and spec.loader
journal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = journal
spec.loader.exec_module(journal)


class SyntheticJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="forest-b1-synthetic-")
        self.path = Path(self.temp.name) / "synthetic.db"
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA synchronous=FULL")
        journal.bootstrap_synthetic(self.db)
        self.store = journal.ForestSessionJournal(self.db)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def session(self, owner="principal_a", tree="CHERRY"):
        return self.store.create_session(owner, tree, "Synthetic study", now_ms=100)

    def test_no_automatic_database_setup_or_migration(self):
        other = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(journal.JournalRefusal, "UNSUPPORTED_SCHEMA"):
                journal.ForestSessionJournal(other)
            self.assertEqual(other.execute("PRAGMA user_version").fetchone()[0], 0)
            other.execute("CREATE TABLE existing (id INTEGER)")
            with self.assertRaisesRegex(journal.JournalRefusal, "EXISTING_DATABASE"):
                journal.bootstrap_synthetic(other)
            self.assertEqual(other.execute("PRAGMA user_version").fetchone()[0], 0)
        finally:
            other.close()

    def test_session_persists_after_connection_closes(self):
        item = self.session()
        uid = item["session_id"]
        self.assertEqual(item["state"], "OPEN")
        self.assertEqual(item["revision"], 0)
        self.store.append_turn("principal_a", uid, expected_revision=0,
                               role="user", body="Remember the project decisions",
                               now_ms=101)
        self.store.append_turn("principal_a", uid, expected_revision=1,
                               role="assistant", body="Synthetic response",
                               provider="ollama", model="qwen3:1.7b", now_ms=102)
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.store = journal.ForestSessionJournal(self.db)
        self.assertEqual(self.store.session("principal_a", uid)["revision"], 2)
        turns = self.store.turns("principal_a", uid)
        self.assertEqual([row["role"] for row in turns], ["user", "assistant"])
        self.assertEqual([row["ordinal"] for row in turns], [1, 2])
        self.assertEqual(turns[1]["model"], "qwen3:1.7b")

    def test_model_can_change_without_creating_another_session(self):
        uid = self.session()["session_id"]
        self.store.append_turn("principal_a", uid, expected_revision=0,
                               role="assistant", body="First response",
                               provider="ollama", model="qwen3:1.7b", now_ms=101)
        self.store.append_turn("principal_a", uid, expected_revision=1,
                               role="assistant", body="Second response",
                               provider="ollama", model="ibm/granite4:small-h",
                               now_ms=102)
        turns = self.store.turns("principal_a", uid)
        self.assertEqual([r["model"] for r in turns],
                         ["qwen3:1.7b", "ibm/granite4:small-h"])
        self.assertEqual(len(self.store.sessions("principal_a")), 1)

    def test_owner_scope_filters_reads_and_mutations(self):
        uid = self.session()["session_id"]
        self.session("principal_b", "MAPLE")
        for operation in (
            lambda: self.store.session("principal_b", uid),
            lambda: self.store.turns("principal_b", uid),
            lambda: self.store.append_turn("principal_b", uid,
                                           expected_revision=0, role="user",
                                           body="untrusted", now_ms=101),
            lambda: self.store.set_state("principal_b", uid,
                                         expected_revision=0, next_state="PAUSED",
                                         now_ms=101),
        ):
            with self.assertRaisesRegex(journal.JournalRefusal, "NOT_FOUND"):
                operation()
        self.assertEqual(len(self.store.sessions("principal_a")), 1)
        self.assertEqual(len(self.store.sessions("principal_b")), 1)

    def test_stale_revision_fails_without_lost_turn(self):
        uid = self.session()["session_id"]
        self.store.append_turn("principal_a", uid, expected_revision=0,
                               role="user", body="First writer", now_ms=101)
        with self.assertRaisesRegex(journal.JournalRefusal, "STALE_REVISION"):
            self.store.append_turn("principal_a", uid, expected_revision=0,
                                   role="assistant", body="Stale writer",
                                   provider="ollama", model="m1", now_ms=102)
        self.assertEqual(len(self.store.turns("principal_a", uid)), 1)
        self.assertEqual(self.store.session("principal_a", uid)["revision"], 1)

    def test_two_connections_do_not_duplicate_stale_writes(self):
        uid = self.session()["session_id"]
        second_db = sqlite3.connect(self.path, timeout=1)
        try:
            second = journal.ForestSessionJournal(second_db)
            self.store.append_turn("principal_a", uid, expected_revision=0,
                                   role="user", body="A", now_ms=101)
            with self.assertRaisesRegex(journal.JournalRefusal, "STALE_REVISION"):
                second.append_turn("principal_a", uid, expected_revision=0,
                                   role="user", body="B", now_ms=101)
            self.assertEqual([r["body"] for r in second.turns("principal_a", uid)], ["A"])
        finally:
            second_db.close()

    def test_failed_second_write_rolls_back_first_insert(self):
        uid = self.session()["session_id"]
        self.db.execute(
            "CREATE TRIGGER synthetic_fail BEFORE UPDATE ON forest_sessions "
            "BEGIN SELECT RAISE(ABORT,'disposable failure'); END")
        self.db.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            self.store.append_turn("principal_a", uid, expected_revision=0,
                                   role="user", body="Should not survive",
                                   now_ms=101)
        self.assertEqual(self.store.turns("principal_a", uid), [])
        self.assertEqual(self.store.session("principal_a", uid)["revision"], 0)

    def test_explicit_pause_resume_and_archival(self):
        uid = self.session()["session_id"]
        paused = self.store.set_state("principal_a", uid, expected_revision=0,
                                      next_state="PAUSED", now_ms=101)
        self.assertEqual(paused["revision"], 1)
        with self.assertRaisesRegex(journal.JournalRefusal, "SESSION_NOT_OPEN"):
            self.store.append_turn("principal_a", uid, expected_revision=1,
                                   role="user", body="No", now_ms=102)
        active = self.store.set_state("principal_a", uid, expected_revision=1,
                                      next_state="OPEN", now_ms=102)
        self.assertEqual(active["state"], "OPEN")
        archived = self.store.set_state("principal_a", uid, expected_revision=2,
                                        next_state="ARCHIVED", now_ms=103)
        self.assertEqual(archived["state"], "ARCHIVED")
        with self.assertRaisesRegex(journal.JournalRefusal, "INVALID_TRANSITION"):
            self.store.set_state("principal_a", uid, expected_revision=3,
                                 next_state="OPEN", now_ms=104)

    def test_backward_clock_and_bad_revision_denied(self):
        uid = self.session()["session_id"]
        with self.assertRaisesRegex(journal.JournalRefusal, "TIME_ROLLBACK"):
            self.store.append_turn("principal_a", uid, expected_revision=0,
                                   role="user", body="Old", now_ms=99)
        with self.assertRaisesRegex(journal.JournalRefusal, "INVALID_REVISION"):
            self.store.append_turn("principal_a", uid, expected_revision=True,
                                   role="user", body="Bool revision", now_ms=101)
        self.assertEqual(self.store.session("principal_a", uid)["revision"], 0)

    def test_invalid_text_and_identifiers_fail_closed(self):
        for name in ("", "../secret", "foo bar", "🚫"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(journal.JournalRefusal, "INVALID_IDENTIFIER"):
                    self.store.create_session(name, "CHERRY", "Title", now_ms=100)
        uid = self.session()["session_id"]
        for body in ("\x00secret", "a" * 16001, "\ud800"):
            with self.subTest(body=repr(body)[:15]):
                with self.assertRaisesRegex(journal.JournalRefusal, "INVALID_TEXT"):
                    self.store.append_turn("principal_a", uid, expected_revision=0,
                                           role="user", body=body, now_ms=101)
        self.assertEqual(self.store.turns("principal_a", uid), [])

    def test_invalid_model_identity_or_role_rejected(self):
        uid = self.session()["session_id"]
        kwargs = {"owner": "principal_a", "session_id": uid,
                  "expected_revision": 0, "body": "Synthetic", "now_ms": 101}
        for attrs, reason in (
            ({"role": "user", "provider": "ollama"}, "UNEXPECTED_MODEL_IDENTITY"),
            ({"role": "user", "provider": None}, "INVALID_MODEL_IDENTITY"),
            ({"role": "assistant", "provider": "", "model": "m"}, "INVALID_IDENTIFIER"),
            ({"role": "system"}, "INVALID_ROLE"),
        ):
            with self.subTest(attrs=attrs):
                with self.assertRaisesRegex(journal.JournalRefusal, reason):
                    self.store.append_turn(**kwargs, **attrs)
        self.assertEqual(self.store.turns("principal_a", uid), [])

    def test_query_pagination_and_bounds(self):
        uid = self.session()["session_id"]
        for i in range(3):
            self.store.append_turn("principal_a", uid, expected_revision=i,
                                   role="user", body=str(i), now_ms=101+i)
        self.assertEqual(
            [row["ordinal"] for row in self.store.turns("principal_a", uid,
                                                       after=1, limit=2)],
            [2, 3]
        )
        for limit in (-1, 0, 101, True):
            with self.assertRaisesRegex(journal.JournalRefusal, "INVALID_PAGE"):
                self.store.turns("principal_a", uid, limit=limit)
        with self.assertRaisesRegex(journal.JournalRefusal, "INVALID_LIMIT"):
            self.store.sessions("principal_a", limit=1000)

    def test_unknown_session_does_not_create_rows(self):
        with self.assertRaisesRegex(journal.JournalRefusal, "NOT_FOUND"):
            self.store.turns("principal_a", "s_deadbeef")
        self.assertEqual(self.store.sessions("principal_a"), [])

    def test_plaintext_storage_is_synthetic_and_not_a_security_claim(self):
        script = FILE.read_text()
        self.assertIn("NO production data path", script)
        self.assertIn("owner_key is a scope filter, NOT authentication", script)
        self.assertNotIn("os.makedirs", script)
        self.assertNotIn("Quickshell", script)
        self.assertNotIn("HospitalRoom", script)


if __name__ == "__main__":
    unittest.main()
