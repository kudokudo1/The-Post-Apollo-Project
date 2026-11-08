#!/usr/bin/env python3
"""C3e-I: operator-supervised CI-only recovery, real child crashes and GPG."""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import sqlite3
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    assert sp and sp.loader
    obj = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(obj)
    return obj


ci = load("c3ei_supervised", HERE / "C3eSupervisedSupersession.py")
prev = load(
    "c3ei_operator_fixture",
    ROOT / "tests/connections/test_connections_c3eh_operator_recovery_gate.py",
)


class C3eISupervisedSupersessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prev.C3eHOperatorRecoveryGateTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        prev.C3eHOperatorRecoveryGateTests.tearDownClass()

    def setUp(self):
        self.fx = prev.C3eHOperatorRecoveryGateTests(
            "test_01_strict_operator_approval_authenticates_pending_and_new_release")
        self.fx.setUp()
        self.opts = self.fx.args()
        ci.initialize(
            witness_db=self.opts["witness_db"],
            client_db=self.opts["client_db"],
        )

    def tearDown(self):
        self.fx.tearDown()

    def ready(self):
        self.fx.prepare()
        self.assertEqual(self.status()["phase"], "legacy_pending")
        # C3e-G pending release 9, newer authority+operator-signed release 10.
        self.assertEqual(self.fx.fx.phase()["phase"], "client_committed")

    def status(self):
        return ci.inspect(
            witness_db=self.opts["witness_db"],
            client_db=self.opts["client_db"],
        )

    def execute(self, *, recovery=False, hook=None, **overrides):
        params = self.fx.args()
        params.update(overrides)
        return ci.execute(
            **params, recovery=recovery, test_checkpoint_hook=hook)

    def refused(self, code, *, recovery=False, **kwargs):
        with self.assertRaises(ci.Refused) as e:
            self.execute(recovery=recovery, **kwargs)
        self.assertEqual(str(e.exception), code)

    def crash(self, stage):
        def child():
            def kill(marker):
                if marker == stage:
                    os._exit(73)
            self.execute(hook=kill)
            os._exit(0)
        p = multiprocessing.get_context("fork").Process(target=child)
        p.start()
        p.join(timeout=40)
        if p.is_alive():
            p.kill()
            p.join()
            self.fail("disposable child deadlocked")
        self.assertEqual(p.exitcode, 73)

    def test_01_enrollment_explicit_and_no_pending_refused(self):
        self.refused("OPERATOR_PREFLIGHT_REFUSED_NO_PENDING_INTENT")
        with self.assertRaises(ci.Refused) as e:
            ci.initialize(
                witness_db=self.opts["witness_db"],
                client_db=self.opts["client_db"])
        self.assertEqual(str(e.exception),
                         "SUPERSESSION_JOURNAL_ALREADY_INITIALIZED")

    def test_02_operator_signature_allows_test_only_two_commit_supersession(self):
        self.ready()
        self.assertEqual(self.execute(), ci.SUCCESS)
        st = self.status()
        self.assertEqual(st["phase"], "clear")
        self.assertFalse(st["legacy_intent_pending"])
        self.assertFalse(st["supersession_pending"])
        self.assertEqual(st["witness_floor"], (5, 10))
        self.assertEqual(st["client_floor"], (5, 10))

    def test_03_process_dies_after_supersession_prepare_and_recovers(self):
        self.ready()
        self.crash("supersession-prepared")
        self.assertEqual(self.status()["phase"], "prepared_only")
        self.refused("SUPERSESSION_PENDING_REQUIRES_EXPLICIT_RECOVERY")
        self.assertEqual(self.execute(recovery=True), ci.SUCCESS)
        self.assertEqual(self.status()["phase"], "clear")
        self.assertEqual(self.status()["witness_floor"], (5, 10))

    def test_04_process_dies_after_new_client_commit_and_recovers(self):
        self.ready()
        self.crash("supersession-client-committed")
        before = self.status()
        self.assertEqual(before["phase"], "client_committed")
        self.assertEqual(before["client_floor"], (5, 10))
        self.assertEqual(before["witness_floor"], (3, 8))
        self.assertEqual(self.execute(recovery=True), ci.SUCCESS)
        self.assertEqual(self.status()["phase"], "clear")
        self.assertEqual(self.status()["client_floor"], (5, 10))
        self.assertEqual(self.status()["witness_floor"], (5, 10))

    def test_05_process_dies_after_witness_final_commit(self):
        self.ready()
        self.crash("supersession-witness-committed")
        self.assertEqual(self.status()["phase"], "clear")
        self.assertEqual(self.status()["witness_floor"], (5, 10))
        self.refused("OPERATOR_PREFLIGHT_REFUSED_NO_PENDING_INTENT",
                     recovery=True)

    def test_06_retry_without_explicit_recovery_refuses(self):
        self.ready()
        self.crash("supersession-prepared")
        before = self.status()
        self.refused("SUPERSESSION_PENDING_REQUIRES_EXPLICIT_RECOVERY")
        self.assertEqual(self.status(), before)

    def test_07_replacement_signed_approval_cannot_consume_old_intent(self):
        self.ready()
        self.crash("supersession-prepared")
        # Same protected context but different signed bytes. The journal
        # pins the exact approval and cannot silently substitute it.
        self.fx.sign_approval(changes={
            "expires_at": int(time.time()) + 80,
        })
        self.refused("RECOVERY_APPROVAL_OR_TARGET_MISMATCH",
                     recovery=True)
        self.assertTrue(self.status()["supersession_pending"])

    def test_08_changed_signed_candidate_cannot_reconcile(self):
        self.ready()
        self.crash("supersession-prepared")
        self.fx.fx.fx.issue(6, 11, b"fake-signed-release-11")
        self.fx.fx.fx.advance()
        self.refused(
            "OPERATOR_PREFLIGHT_REFUSED_SIGNED_APPROVAL_CONTEXT_MISMATCH",
            recovery=True,
        )
        self.assertTrue(self.status()["supersession_pending"])

    def test_09_forged_approval_and_wrong_pins_refuse_before_prepare(self):
        self.ready()
        self.fx.signature_path.write_bytes(b"not a signature")
        self.refused("OPERATOR_PREFLIGHT_REFUSED_OPERATOR_SIGNATURE_REFUSED")
        self.assertFalse(self.status()["supersession_pending"])

    def test_10_conflicting_client_after_prepare_is_not_silently_reset(self):
        self.ready()
        self.crash("supersession-client-committed")
        with sqlite3.connect(self.opts["client_db"]) as db:
            db.execute("UPDATE checkpoint SET artifact_digest=? WHERE id=1",
                       ("d" * 64,))
        self.refused("OPERATOR_PREFLIGHT_REFUSED_RECOVERY_CLIENT_NOT_AT_SIGNED_TARGET",
                     recovery=True)
        self.assertEqual(self.status()["phase"], "conflict")

    def test_11_failed_witness_final_commit_keeps_both_journals(self):
        self.ready()
        with sqlite3.connect(self.opts["witness_db"]) as db:
            db.execute("""CREATE TRIGGER c3ei_fail_final
                BEFORE UPDATE ON witness BEGIN
                SELECT RAISE(ABORT, 'simulated final failure'); END""")
        self.refused("WITNESS_SUPERSESSION_COMMIT_FAILED")
        st = self.status()
        self.assertEqual(st["phase"], "client_committed")
        self.assertTrue(st["supersession_pending"])
        self.assertTrue(st["legacy_intent_pending"])
        with sqlite3.connect(self.opts["witness_db"]) as db:
            db.execute("DROP TRIGGER c3ei_fail_final")
        self.assertEqual(self.execute(recovery=True), ci.SUCCESS)

    def test_12_missing_witness_denies_without_bootstrap(self):
        self.ready()
        self.crash("supersession-client-committed")
        self.opts["witness_db"].unlink()
        self.refused("OPERATOR_PREFLIGHT_REFUSED_WITNESS_LEDGER_UNAVAILABLE",
                     recovery=True)
        self.assertFalse(self.opts["witness_db"].exists())

    def test_13_missing_client_denies_without_bootstrap(self):
        self.ready()
        self.crash("supersession-prepared")
        self.opts["client_db"].unlink()
        self.refused("OPERATOR_PREFLIGHT_REFUSED_CLIENT_LEDGER_UNAVAILABLE",
                     recovery=True)
        self.assertFalse(self.opts["client_db"].exists())

    def test_14_missing_supersession_journal_denies(self):
        self.ready()
        with sqlite3.connect(self.opts["witness_db"]) as db:
            db.execute("DROP TABLE supersession_intent")
        self.refused("SUPERSESSION_JOURNAL_UNAVAILABLE")

    def test_15_wrong_node_and_root_can_never_commit_a_supersession(self):
        self.ready()
        self.refused(
            "OPERATOR_PREFLIGHT_REFUSED_RECOVERY_STATE_REFUSED_WITNESS_IDENTITY_REFUSED",
            node_id="synthetic-other-node")
        self.assertEqual(self.status()["witness_floor"], (3, 8))

    def test_16_new_authority_challenge_required_on_crash_retry(self):
        self.ready()
        self.crash("supersession-prepared")
        old = self.fx.fx.fx.remote_proof("f" * 64)
        self.refused(
            "OPERATOR_PREFLIGHT_REFUSED_FRESH_AUTHORITY_REFUSED_INVALID_AUTHORITY_PROOF_REPLAYED_OR_UNSOLICITED_PROOF",
            recovery=True,
            request_proof=lambda _: old,
        )
        self.assertTrue(self.status()["supersession_pending"])

    def test_17_test_only_gate_blocks_production_connections_authority(self):
        broker = ROOT / "services/connections"
        self.assertIn("readonly property bool hostAuthenticated: false",
                      (broker / "ConnectionsRequestStatus.qml").read_text())
        self.assertIn("readonly property bool credentialActionsEnabled: false",
                      (broker / "ConnectionsBroker.qml").read_text())
        path = HERE / "C3eSupervisedSupersession.py"
        source = path.read_text()
        for forbidden in ("systemctl start", "rpm --import", "secret-tool"):
            self.assertNotIn(forbidden, source)
        for f in (*broker.glob("*.qml"), *broker.glob("*.js"), broker / "qmldir"):
            self.assertNotIn("C3eSupervisedSupersession", f.read_text(), f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
