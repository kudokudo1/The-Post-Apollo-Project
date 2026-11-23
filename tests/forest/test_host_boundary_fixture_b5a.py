"""B5a host boundary disposable fixtures. No real sessions, inference or IPC."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import host_boundary_fixture_b5a as b5a
import session_journal_v0 as b1


class HostBoundaryB5aTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        b1.bootstrap_synthetic(self.db)
        self.journal = b1.ForestSessionJournal(self.db)

    def tearDown(self):
        self.db.close()

    def add(self, owner="owner_alpha", tree="CHERRY", title="Synthetic title",
            now=100):
        return self.journal.create_session(
            owner, tree, title, now_ms=now
        )

    def list(self, owner="owner_alpha", tree="CHERRY"):
        return b5a.list_disposable_tree_fixture(
            self.db, owner=owner, tree=tree
        )

    def test_one_read_is_explicitly_unauthenticated(self):
        self.add()
        report = self.list()
        self.assertEqual(len(report["rows"]), 1)
        self.assertEqual(report["status"], "DISPOSABLE_ROWS_UNAUTHENTICATED")
        for flag in ("sourceAuthenticated", "permissionGranted",
                     "canListSessions", "mayDiscloseTitles",
                     "productionAuthority"):
            self.assertIs(report[flag], False)
        self.assertEqual(report["safeActions"], [])
        self.assertNotIn("action", report)
        self.assertNotIn("sessions", report)

    def test_tree_predicate_applied_before_limit(self):
        # One owner has 110 MAPLE rows newer than its CHERRY row.
        # The old B1 owner-only 100-row query would lose CHERRY entirely.
        cherry = self.add(now=100)
        for i in range(110):
            self.add(tree="MAPLE", title="Synthetic Maple " + str(i),
                     now=200+i)
        report = self.list()
        self.assertEqual([r["session_id"] for r in report["rows"]],
                         [cherry["session_id"]])
        self.assertTrue(report["complete_fixture"])

    def test_open_state_predicate_applied_before_limit(self):
        cherry = self.add(now=100)
        for i in range(105):
            s = self.add(title="Paused " + str(i), now=200+i)
            self.journal.set_state("owner_alpha", s["session_id"],
                                   expected_revision=0,
                                   next_state="PAUSED", now_ms=500+i)
        report = self.list()
        self.assertEqual(len(report["rows"]), 1)
        self.assertEqual(report["rows"][0]["session_id"],
                         cherry["session_id"])

    def test_more_than_100_scoped_open_rows_hold_not_partial(self):
        for i in range(101):
            self.add(title="Synthetic " + str(i), now=200+i)
        with self.assertRaisesRegex(b5a.HostFixtureHold, "SNAPSHOT_TOO_LARGE"):
            self.list()

    def test_exactly_100_scoped_open_rows_complete(self):
        for i in range(100):
            self.add(title="Synthetic " + str(i), now=200+i)
        self.assertEqual(len(self.list()["rows"]), 100)

    def test_other_owners_not_read(self):
        self.add(owner="owner_beta", title="Other owner's private title")
        self.add(title="Current fixture")
        report = self.list()
        self.assertEqual([r["title"] for r in report["rows"]],
                         ["Current fixture"])
        self.assertNotIn("owner_alpha", json.dumps(report))
        self.assertNotIn("owner_beta", json.dumps(report))

    def test_no_transcript_body_in_output(self):
        s = self.add()
        self.journal.append_turn(
            "owner_alpha", s["session_id"], expected_revision=0,
            role="user", body="Highly sensitive synthetic turn",
            now_ms=101,
        )
        report = self.list()
        raw = json.dumps(report)
        self.assertNotIn("Highly sensitive synthetic turn", raw)
        self.assertEqual(tuple(report["rows"][0]), b5a.ROW_FIELDS)

    def test_sql_scope_is_parameterized_not_interpreted_as_sql(self):
        self.add(title="Ordinary synthetic")
        for malformed in ("owner_alpha' OR 1=1 --", "", "../private", 42):
            with self.subTest(value=malformed):
                with self.assertRaises(b5a.HostFixtureHold):
                    self.list(owner=malformed)

    def test_unknown_presentation_tree_is_not_canonical(self):
        self.add()
        with self.assertRaisesRegex(
            b5a.HostFixtureHold, "NONCANONICAL_PRESENTATION_TREE"
        ):
            self.list(tree="NEW_TREE")
        with self.assertRaises(b5a.HostFixtureHold):
            self.list(tree="CHERRY' OR 1=1 --")

    def test_invalid_title_control_rejected_completely(self):
        s = self.add()
        self.db.execute(
            "UPDATE forest_sessions SET title=? WHERE session_id=?",
            ("secret\u202etitle", s["session_id"]),
        )
        self.db.commit()
        with self.assertRaisesRegex(b5a.HostFixtureHold, "INVALID_FIXTURE_ROW"):
            self.list()

    def test_invalid_title_length_rejected_completely(self):
        s = self.add()
        self.db.execute(
            "UPDATE forest_sessions SET title=? WHERE session_id=?",
            ("x"*161, s["session_id"]),
        )
        self.db.commit()
        with self.assertRaises(b5a.HostFixtureHold):
            self.list()

    def test_invalid_time_beyond_js_safe_integer_rejected(self):
        s = self.add()
        self.db.execute(
            "UPDATE forest_sessions SET updated_at_ms=? WHERE session_id=?",
            (2**53, s["session_id"]),
        )
        self.db.commit()
        with self.assertRaises(b5a.HostFixtureHold):
            self.list()

    def test_no_automatic_database_bootstrap(self):
        other = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(
                b5a.HostFixtureHold, "UNSUPPORTED_SCHEMA"
            ):
                b5a.list_disposable_tree_fixture(
                    other, owner="owner_alpha", tree="CHERRY"
                )
            self.assertEqual(other.execute("PRAGMA user_version").fetchone()[0],
                             0)
        finally:
            other.close()

    def test_file_backed_database_refused_even_if_valid_b1(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "synthetic.db")
            connection = sqlite3.connect(path)
            try:
                b1.bootstrap_synthetic(connection)
                with self.assertRaisesRegex(
                    b5a.HostFixtureHold, "DISK_OR_ATTACHED_DB_REFUSED"
                ):
                    b5a.list_disposable_tree_fixture(
                        connection, owner="owner_alpha", tree="CHERRY"
                    )
            finally:
                connection.close()

    def test_attached_file_database_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "attached.db")
            self.db.execute("ATTACH DATABASE ? AS extra", (path,))
            self.db.commit()
            with self.assertRaisesRegex(
                b5a.HostFixtureHold, "DISK_OR_ATTACHED_DB_REFUSED"
            ):
                self.list()

    def test_in_transaction_is_refused_without_mutating(self):
        self.db.execute("BEGIN")
        with self.assertRaisesRegex(
            b5a.HostFixtureHold, "ACTIVE_TRANSACTION"
        ):
            self.list()
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()

    def test_input_must_be_real_connection(self):
        with self.assertRaisesRegex(
            b5a.HostFixtureHold, "FIXTURE_DB_REQUIRED"
        ):
            b5a.list_disposable_tree_fixture(
                object(), owner="owner_alpha", tree="CHERRY"
            )

    def test_report_has_bounded_serialized_size(self):
        for i in range(100):
            self.add(title="x"*155 + str(i).zfill(3), now=100+i)
        report = self.list()
        self.assertLessEqual(len(json.dumps(report).encode()),
                             b5a.MAX_FRAME_BYTES)

    def test_egress_blocks_provisional_text_without_sink(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        result = guard.observe({
            "event":"DELTA", "text":"private synthetic response",
            "provisional":True,
        })
        self.assertEqual(result["status"], "BLOCKED_NO_EGRESS")
        self.assertEqual(result["emittedBytes"], 0)
        self.assertFalse(result["permissionGranted"])
        self.assertNotIn("private synthetic response", json.dumps(result))

    def test_egress_counts_utf8_bytes_not_characters(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        result = guard.observe({
            "event":"DELTA", "text":"🚀", "provisional":True,
        })
        self.assertEqual(result["simulatedInputBytesObserved"], 4)
        self.assertEqual(result["emittedBytes"], 0)

    def test_egress_no_provisional_false_bypass(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        for event in (
            {"event":"DELTA", "text":"s", "provisional":False},
            {"event":"DELTA", "text":"s", "provisional":1},
            {"event":"COMPLETE", "text":"s", "provisional":True},
            {"event":"DELTA", "text":"s", "provisional":True,
             "permissionGranted":True},
            {"event":"DELTA", "text":"", "provisional":True},
        ):
            with self.subTest(event=event):
                with self.assertRaises(b5a.HostFixtureHold):
                    guard.observe(event)

    def test_egress_over_budget_holds_without_send(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        guard.observe({"event":"DELTA", "text":"a"*15999,
                       "provisional":True})
        with self.assertRaisesRegex(
            b5a.HostFixtureHold, "PROVISIONAL_BUDGET_EXCEEDED"
        ):
            guard.observe({"event":"DELTA", "text":"aa",
                           "provisional":True})
        result = guard.fence_ack()
        self.assertEqual(result["emittedBytes"], 0)
        self.assertFalse(result["revocationFencedAck"])

    def test_egress_invalid_surrogate_refused(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        with self.assertRaisesRegex(
            b5a.HostFixtureHold, "INVALID_PROVISIONAL_EVENT"
        ):
            guard.observe({"event":"DELTA", "text":"\ud800",
                           "provisional":True})

    def test_revoke_never_claims_fenced_ack(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        requested = guard.begin_revoke()
        self.assertEqual(requested["status"],
                         "REVOKE_REQUESTED_UNKNOWN_HOLD")
        self.assertFalse(requested["revocationFencedAck"])
        with self.assertRaisesRegex(
            b5a.HostFixtureHold, "REVOKED_NO_NEW_ADMISSIONS"
        ):
            guard.observe({"event":"DELTA", "text":"late",
                           "provisional":True})
        ack = guard.fence_ack()
        self.assertEqual(ack["status"], "UNKNOWN_HOLD_NO_NATIVE_FENCE")
        self.assertEqual(ack["emittedBytes"], 0)
        self.assertFalse(ack["revocationFencedAck"])

    def test_revoke_is_irreversible_in_fixture(self):
        guard = b5a.BlockedProvisionalEgressFixture()
        guard.begin_revoke()
        guard.begin_revoke()
        with self.assertRaises(b5a.HostFixtureHold):
            guard.observe({"event":"DELTA", "text":"late",
                           "provisional":True})

    def test_source_never_starts_runtime_or_opens_output(self):
        text = (Path(__file__).resolve().parents[2]
                / "scripts/forest/host_boundary_fixture_b5a.py").read_text()
        for banned in ("subprocess", "socket.", "connect(", "sendall(",
                       "send(", "write(", "open(", "stream_chat(",
                       "ForestTurnBridge(", "os.system", "systemctl",
                       "http.client", "requests.post", "/api/chat"):
            with self.subTest(symbol=banned):
                self.assertNotIn(banned, text)


if __name__ == "__main__":
    unittest.main()
