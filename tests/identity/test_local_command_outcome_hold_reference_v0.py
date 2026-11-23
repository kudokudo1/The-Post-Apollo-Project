"""DOC 6 local durable UNKNOWN_HOLD negative reference tests.

All SQLite databases and child processes are disposable test fixtures.
No native command or user-account provider is contacted.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from local_command_outcome_hold_reference_v0 import (
    OutcomeHoldRefused, SCHEMA, TestOnlyLocalOutcomeFence,
)

_FIXTURE = """
CREATE TABLE command_attempt(
    slot INTEGER PRIMARY KEY CHECK(slot=1),
    attempt_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('BEGIN','STATUS','CANCEL','RECOVER')),
    request_digest TEXT
);
PRAGMA user_version=1;
"""
ID_A = "a" * 32
ID_B = "b" * 32
REQUEST_ID = "signed_host_request_00001"


class TestOnlyOutcomeHoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="doc6-hold-ci-")
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "outcome.sqlite"
        with sqlite3.connect(self.db_path) as db:
            db.executescript(_FIXTURE)
        self.store = TestOnlyLocalOutcomeFence(self.db_path)

    def assert_held(self, state):
        self.assertEqual(state.schema, SCHEMA)
        self.assertEqual(state.state, "UNKNOWN_HOLD")
        self.assertEqual(state.safe_actions, ())
        for field in ("can_begin_sign_in", "can_cancel", "can_recover",
                      "can_connect_provider", "issuer_reconciled",
                      "production_authority"):
            self.assertIs(getattr(state, field), False)

    def test_preexisting_empty_store_never_means_clear_to_send(self):
        state = self.store.inspect()
        self.assert_held(state)
        self.assertEqual(state.reason, "EMPTY_OR_ROLLED_BACK_LOCAL_HISTORY")

    def test_write_ahead_ambiguity_persists_across_new_object(self):
        before = self.store.reserve_before_possible_send(
            attempt_id=ID_A, action="BEGIN")
        self.assert_held(before)
        self.assertEqual(before.reason, "LOCAL_ATTEMPT_UNSETTLED")
        reopened = TestOnlyLocalOutcomeFence(self.db_path).inspect()
        self.assert_held(reopened)
        self.assertEqual(reopened.attempt_id, ID_A)
        self.assertEqual(reopened.action, "BEGIN")

    def test_new_python_process_recovers_hold_without_reissuing_command(self):
        self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")
        code = (
            "import sys;"
            "from pathlib import Path;"
            "sys.path.insert(0, sys.argv[2]);"
            "from local_command_outcome_hold_reference_v0 import TestOnlyLocalOutcomeFence;"
            "r=TestOnlyLocalOutcomeFence(Path(sys.argv[1])).inspect();"
            "print(r.state, r.action, r.can_begin_sign_in)"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", code,
             str(self.db_path), str(ROOT / "services" / "identity")],
            check=True, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.stdout.strip(), "UNKNOWN_HOLD BEGIN False")

    def test_duplicate_attempt_is_not_idempotent_approval(self):
        self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")
        with self.assertRaises(OutcomeHoldRefused):
            self.store.reserve_before_possible_send(
                attempt_id=ID_A, action="BEGIN")
        self.assert_held(self.store.inspect())

    def test_second_action_is_denied_after_prior_unknown(self):
        self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")
        with self.assertRaises(OutcomeHoldRefused):
            self.store.reserve_before_possible_send(
                attempt_id=ID_B, action="CANCEL", request_id=REQUEST_ID)
        self.assertEqual(self.store.inspect().action, "BEGIN")

    def test_concurrent_process_reservations_one_wins_never_two(self):
        code = (
            "import sys;"
            "from pathlib import Path;"
            "sys.path.insert(0, sys.argv[2]);"
            "from local_command_outcome_hold_reference_v0 import "
            "TestOnlyLocalOutcomeFence,OutcomeHoldRefused;"
            "s=TestOnlyLocalOutcomeFence(Path(sys.argv[1]));"
            "s.reserve_before_possible_send(attempt_id=sys.argv[3], action='BEGIN')"
        )
        procs = [
            subprocess.Popen(
                [sys.executable, "-B", "-c", code,
                 str(self.db_path), str(ROOT / "services" / "identity"), n],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for n in (ID_A, ID_B)
        ]
        for proc in procs:
            proc.communicate(timeout=15)
        self.assertEqual(sorted(p.returncode for p in procs), [0, 1])
        self.assert_held(self.store.inspect())
        self.assertIn(self.store.inspect().attempt_id, (ID_A, ID_B))
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM command_attempt").fetchone()[0], 1)

    def test_local_backup_rollback_is_not_absence_proof(self):
        backup = self.db_path.with_suffix(".backup")
        shutil.copyfile(self.db_path, backup)
        self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")
        shutil.copyfile(backup, self.db_path)
        status = self.store.inspect()
        self.assert_held(status)
        self.assertEqual(status.reason, "EMPTY_OR_ROLLED_BACK_LOCAL_HISTORY")

    def test_missing_database_fails_closed_and_never_auto_creates(self):
        self.db_path.unlink()
        self.assert_held(self.store.inspect())
        with self.assertRaises(OutcomeHoldRefused):
            self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")
        self.assertFalse(self.db_path.exists())

    def test_corrupt_database_fails_closed(self):
        self.db_path.write_bytes(b"not a sqlite database")
        self.assert_held(self.store.inspect())
        with self.assertRaises(OutcomeHoldRefused):
            self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")

    def test_unversioned_schema_fails_closed(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute("PRAGMA user_version=2")
        self.assert_held(self.store.inspect())
        with self.assertRaises(OutcomeHoldRefused):
            self.store.reserve_before_possible_send(attempt_id=ID_A, action="BEGIN")

    def test_each_supported_action_retains_unresolved_local_hold(self):
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            with self.subTest(action=action):
                with sqlite3.connect(self.db_path) as db:
                    db.execute("DELETE FROM command_attempt")
                result = self.store.reserve_before_possible_send(
                    attempt_id=ID_A, action=action,
                    request_id=None if action == "BEGIN" else REQUEST_ID)
                self.assert_held(result)
                self.assertEqual(self.store.inspect().action, action)

    def test_raw_host_request_id_is_not_stored(self):
        self.store.reserve_before_possible_send(
            attempt_id=ID_A, action="CANCEL", request_id=REQUEST_ID)
        raw = self.db_path.read_bytes()
        self.assertNotIn(REQUEST_ID.encode(), raw)
        self.assert_held(self.store.inspect())

    def test_rejects_wrong_request_binding_or_action(self):
        for action, rid in (("BEGIN", REQUEST_ID), ("CANCEL", None),
                            ("RECOVER", ""), ("STATUS", "unsafe/token")):
            with self.subTest(action=action, rid=rid):
                with self.assertRaises(OutcomeHoldRefused):
                    self.store.reserve_before_possible_send(
                        attempt_id=ID_A, action=action, request_id=rid)
        for bad in ("LOGIN", "login", "", None, 5):
            with self.subTest(bad=bad):
                with self.assertRaises(OutcomeHoldRefused):
                    self.store.reserve_before_possible_send(
                        attempt_id=ID_A, action=bad)

    def test_refuses_malformed_attempt_ids(self):
        for value in (0, None, "", "a" * 31, "A" * 32, "b" * 33):
            with self.subTest(value=value):
                with self.assertRaises(OutcomeHoldRefused):
                    self.store.reserve_before_possible_send(
                        attempt_id=value, action="BEGIN")

    def test_invalid_persisted_row_never_authorizes(self):
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO command_attempt VALUES (1, ?, 'BEGIN', NULL)",
                ("bad",))
        report = self.store.inspect()
        self.assert_held(report)
        self.assertEqual(report.reason, "INVALID_LOCAL_HISTORY")

    def test_no_native_dispatch_or_authority_completion_api(self):
        import local_command_outcome_hold_reference_v0 as module
        self.assertFalse(hasattr(TestOnlyLocalOutcomeFence, "send"))
        self.assertFalse(hasattr(TestOnlyLocalOutcomeFence, "clear"))
        self.assertFalse(hasattr(TestOnlyLocalOutcomeFence, "settle"))
        self.assertFalse(hasattr(TestOnlyLocalOutcomeFence, "retry"))
        ast_root = ast.parse(Path(module.__file__).read_text())
        native_imports = []
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Import):
                native_imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                native_imports.append(node.module)
        for prohibited in ("socket", "subprocess", "desktop_signed_command_client_v0",
                           "desktop_command_gateway_v0", "cryptography"):
            self.assertNotIn(prohibited, native_imports)
        self.assert_held(self.store.inspect())


if __name__ == "__main__":
    unittest.main()
