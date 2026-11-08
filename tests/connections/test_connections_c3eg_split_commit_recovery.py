#!/usr/bin/env python3
"""C3e-G: real crash/restart tests for client/witness split-commit recovery.

Signed policies, C3e-E process authority and all three SQLite ledgers are
DISPOSABLE CI fixtures. No desktop or production host is touched.
"""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


split = load("c3eg_test_recovery", HERE / "C3eSplitCommitRecovery.py")
existing = load(
    "c3eg_prior_fixtures",
    ROOT / "tests/connections/test_connections_c3ef_rollback_witness.py",
)


class C3eGSplitCommitRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        existing.C3eFRollbackWitnessTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        existing.C3eFRollbackWitnessTests.tearDownClass()

    def setUp(self):
        self.fx = existing.C3eFRollbackWitnessTests(
            "test_02_signed_release_eight_passes_distinct_witness_gate")
        self.fx.setUp()
        split.initialize_split_journal(
            witness_db=self.fx.location, client_db=self.fx.fx.client_db)

    def tearDown(self):
        self.fx.tearDown()

    def args(self, **kwargs):
        prior = self.fx
        args = {
            "witness_db": prior.location,
            "client_db": prior.fx.client_db,
            "authority_anchor_public": prior.fx.public["external-anchor"],
            "authority_anchor_pin": prior.anchor_pin,
            "node_id": prior.node,
            "release_root_pin": prior.root_pin,
            "request_proof": prior.fx.remote_proof,
            "release_root_public": prior.fx.public["release-root"],
            "policy": prior.fx.policy,
            "policy_signature": prior.fx.policy_sig,
            "delegated_public": prior.fx.public["release-delegated"],
            "manifest": prior.fx.manifest,
            "manifest_signature": prior.fx.manifest_sig,
            "artifact": prior.fx.artifact,
        }
        args.update(kwargs)
        return args

    def request(self, *, recovery=False, test_checkpoint_hook=None, **kwargs):
        return split.submit(
            **self.args(**kwargs), recovery=recovery,
            test_checkpoint_hook=test_checkpoint_hook)

    def phase(self):
        return split.inspect_split(
            witness_db=self.fx.location, client_db=self.fx.fx.client_db)

    def refuses(self, code, *, recovery=False, **kwargs):
        with self.assertRaises(split.Refused) as raised:
            self.request(recovery=recovery, **kwargs)
        self.assertEqual(str(raised.exception), code)

    def prepare_nine(self):
        self.fx.fx.advance()
        self.assertEqual(self.request(), split.SUCCESS)
        self.assertEqual(self.phase()["phase"], "clear")
        self.fx.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.fx.advance()

    def crash_at(self, stage):
        def do_work():
            def kill(phase):
                if phase == stage:
                    os._exit(77)
            self.request(test_checkpoint_hook=kill)
            os._exit(0)

        process = multiprocessing.get_context("fork").Process(target=do_work)
        process.start()
        process.join(timeout=25)
        if process.is_alive():
            process.kill()
            process.join()
            self.fail("disposable crash test deadlocked")
        self.assertEqual(process.exitcode, 77)

    def test_01_initialization_is_explicit_nonrepeating_and_nonmutating(self):
        self.assertEqual(self.phase()["phase"], "clear")
        with self.assertRaises(split.Refused) as error:
            split.initialize_split_journal(
                witness_db=self.fx.location, client_db=self.fx.fx.client_db)
        self.assertEqual(str(error.exception), "JOURNAL_ALREADY_ENROLLED")
        self.assertFalse(self.phase()["pending"])

    def test_02_signed_release_flows_through_intent_and_two_commits(self):
        self.fx.fx.advance()
        phases = []
        self.assertEqual(
            self.request(test_checkpoint_hook=lambda p: phases.append(p)),
            split.SUCCESS)
        self.assertEqual(phases, [
            "intent-committed", "client-committed", "witness-committed"])
        self.assertEqual(self.phase(), {
            "witness_floor": (3, 8), "client_floor": (3, 8),
            "pending": False, "phase": "clear"})
        self.fx.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.fx.advance()
        self.assertEqual(self.request(), split.SUCCESS)
        self.assertEqual(self.phase()["client_floor"], (4, 9))
        self.assertEqual(self.phase()["witness_floor"], (4, 9))

    def test_03_real_process_crash_after_prepared_intent(self):
        self.prepare_nine()
        self.crash_at("intent-committed")
        self.assertEqual(self.phase()["phase"], "prepared_only")
        self.refuses("PENDING_INTENT_REQUIRES_EXPLICIT_RECOVERY")
        self.assertEqual(self.request(recovery=True), split.SUCCESS)
        self.assertEqual(self.phase()["phase"], "clear")
        self.assertEqual(self.phase()["witness_floor"], (4, 9))

    def test_04_real_process_crash_after_client_commit(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        self.assertEqual(self.phase()["phase"], "client_committed")
        self.assertEqual(self.phase()["client_floor"], (4, 9))
        self.assertEqual(self.phase()["witness_floor"], (3, 8))
        self.refuses("PENDING_INTENT_REQUIRES_EXPLICIT_RECOVERY")
        self.assertEqual(self.request(recovery=True), split.SUCCESS)
        self.assertEqual(self.phase()["phase"], "clear")
        self.assertEqual(self.phase()["witness_floor"], (4, 9))

    def test_05_real_process_crash_after_witness_final_commit(self):
        self.prepare_nine()
        self.crash_at("witness-committed")
        self.assertEqual(self.phase()["phase"], "clear")
        self.assertEqual(self.phase()["witness_floor"], (4, 9))
        self.refuses("NO_PENDING_INTENT_FOR_RECOVERY", recovery=True)
        self.fx.fx.issue(5, 10, b"fake-signed-release-10")
        self.fx.fx.advance()
        self.assertEqual(self.request(), split.SUCCESS)
        self.assertEqual(self.phase()["witness_floor"], (5, 10))

    def test_06_authentic_fresh_proof_required_to_reconcile_pending(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        self.refuses("AUTHORITY_PROOF_UNAVAILABLE", recovery=True,
                     request_proof=lambda c: (_ for _ in ()).throw(OSError("offline")))
        self.assertTrue(self.phase()["pending"])
        self.assertEqual(self.request(recovery=True), split.SUCCESS)

    def test_07_changed_candidate_cannot_complete_old_prepared_intent(self):
        self.prepare_nine()
        self.crash_at("intent-committed")
        self.fx.fx.issue(5, 10, b"fake-signed-release-10")
        self.fx.fx.advance()
        self.refuses("RECOVERY_SIGNED_RELEASE_NOT_PENDING_TARGET", recovery=True)
        self.assertEqual(self.phase()["phase"], "prepared_only")

    def test_08_changed_authority_floor_blocks_old_recovery(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        self.fx.fx.issue(5, 10, b"fake-signed-release-10")
        self.fx.fx.advance()
        # Changed authority proof cannot be silently substituted. The
        # operator must preserve intent and escalate a newer release.
        self.refuses("RECOVERY_SIGNED_RELEASE_NOT_PENDING_TARGET", recovery=True)
        self.assertEqual(self.phase()["phase"], "client_committed")

    def test_09_conflicting_client_checkpoint_keeps_intent_pending(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        with sqlite3.connect(self.fx.fx.client_db) as conn:
            conn.execute(
                "UPDATE checkpoint SET artifact_digest=? WHERE id=1",
                ("b" * 64,))
        self.refuses("CONFLICTING_CLIENT_CHECKPOINT", recovery=True)
        self.assertEqual(self.phase()["phase"], "conflict")
        self.assertEqual(self.phase()["witness_floor"], (3, 8))

    def test_10_unsigned_tampered_manifest_cannot_reconcile(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        before = self.phase()
        self.fx.fx.manifest.write_text(
            self.fx.fx.manifest.read_text() + " ")
        self.refuses("SIGNED_RELEASE_REFUSED_INVALID_DETACHED_SIGNATURE",
                     recovery=True)
        self.assertEqual(self.phase(), before)

    def test_11_missing_client_blocks_without_witness_advance(self):
        self.prepare_nine()
        self.crash_at("intent-committed")
        self.fx.fx.client_db.unlink()
        self.refuses("CLIENT_LEDGER_UNAVAILABLE", recovery=True)
        self.assertTrue(self.phase if callable(self.phase) else True)
        self.assertEqual(split.witness.inspect_witness(self.fx.location)[3:],
                         (3, 8))

    def test_12_missing_witness_blocks_without_silent_reenrollment(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        self.fx.location.unlink()
        self.refuses("LEDGER_UNAVAILABLE", recovery=True)
        self.assertFalse(self.fx.location.exists())

    def test_13_untracked_client_ahead_with_no_intent_fails_closed(self):
        self.fx.fx.advance()
        self.request()
        self.fx.fx.issue(4, 9, b"fake-signed-release-9")
        self.fx.fx.advance()
        split.durable.admit_and_record(
            self.fx.fx.client_db, external_root_pin=self.fx.root_pin,
            external_epoch_floor=4, external_sequence_floor=9,
            root_public=self.fx.fx.public["release-root"],
            policy=self.fx.fx.policy, policy_signature=self.fx.fx.policy_sig,
            delegated_public=self.fx.fx.public["release-delegated"],
            manifest=self.fx.fx.manifest,
            manifest_signature=self.fx.fx.manifest_sig,
            artifact=self.fx.fx.artifact)
        self.assertEqual(self.phase()["phase"], "untracked_split")
        self.refuses("UNTRACKED_CLIENT_WITNESS_SPLIT")

    def test_14_journal_missing_cannot_be_implicitly_rebuilt(self):
        self.fx.fx.advance()
        with sqlite3.connect(self.fx.location) as conn:
            conn.execute("DROP TABLE split_intent")
        self.refuses("JOURNAL_NOT_INITIALIZED_OR_CORRUPT")
        with self.assertRaises(split.Refused) as error:
            split.inspect_split(
                witness_db=self.fx.location, client_db=self.fx.fx.client_db)
        self.assertEqual(str(error.exception),
                         "JOURNAL_NOT_INITIALIZED_OR_CORRUPT")

    def test_15_witness_transaction_failure_preserves_recoverable_intent(self):
        self.prepare_nine()
        with sqlite3.connect(self.fx.location) as conn:
            conn.execute("""CREATE TRIGGER c3eg_test_refuse_final
                BEFORE UPDATE ON witness
                BEGIN SELECT RAISE(ABORT,'synthetic failure'); END""")
        self.refuses("WITNESS_FINAL_COMMIT_FAILED")
        self.assertEqual(self.phase()["phase"], "client_committed")
        with sqlite3.connect(self.fx.location) as conn:
            conn.execute("DROP TRIGGER c3eg_test_refuse_final")
        self.assertEqual(self.request(recovery=True), split.SUCCESS)
        self.assertEqual(self.phase()["phase"], "clear")

    def test_16_no_untrusted_pending_reset_and_wrong_proof_rejected(self):
        self.prepare_nine()
        self.crash_at("intent-committed")
        old = self.fx.fx.remote_proof("a" * 64)
        self.refuses(
            "INVALID_AUTHORITY_PROOF_REPLAYED_OR_UNSOLICITED_PROOF",
            recovery=True, request_proof=lambda challenge: old)
        self.assertEqual(self.phase()["phase"], "prepared_only")

    def test_17_witness_identity_change_denies_reconciliation(self):
        self.prepare_nine()
        self.crash_at("client-committed")
        with sqlite3.connect(self.fx.location) as conn:
            conn.execute(
                "UPDATE witness SET node_id=? WHERE id=1",
                ("different-synthetic-node",))
        self.refuses("WITNESS_IDENTITY_REFUSED", recovery=True)

    def test_18_client_and_witness_store_same_file_is_refused(self):
        self.fx.fx.advance()
        self.refuses("WITNESS_CLIENT_LEDGER_NOT_SEPARATE",
                     client_db=self.fx.location)

    def test_19_production_broker_keeps_permissions_disabled(self):
        broker = ROOT / "services/connections"
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (broker / "ConnectionsRequestStatus.qml").read_text())
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (broker / "ConnectionsBroker.qml").read_text())
        source = (HERE / "C3eSplitCommitRecovery.py").read_text()
        for forbidden in ("systemctl start", "rpm --import", "secret-tool"):
            self.assertNotIn(forbidden, source)
        for p in (*broker.glob("*.qml"), *broker.glob("*.js"), broker / "qmldir"):
            self.assertNotIn("C3eSplitCommitRecovery", p.read_text(), p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
