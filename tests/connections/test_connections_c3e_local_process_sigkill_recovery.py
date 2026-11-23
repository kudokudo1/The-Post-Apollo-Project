#!/usr/bin/env python3
"""DOC 1 real Linux process-kill/local recovery, never production settlement."""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_SIGKILL_TEST_DEPENDENCY_REQUIRED")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


M = _load("c3e_real_kill_local_reference",
          HERE / "C3eLocalProcessSigkillRecoveryCI.py")
F = _load("c3e_real_kill_existing_local_tests",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


def _fresh_reader(root, challenge, sender):
    """A second process opens SQLite afresh after the writer is dead."""
    try:
        sender.send(M.reopened_local_observation_ci_only(
            root=root, challenge=challenge))
    except BaseException as exc:
        sender.send({"readerError": f"{type(exc).__name__}: {exc}"})
    finally:
        sender.close()


class RealProcessKillRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_REAL_KILL_HOSTED_ROOT_ONLY")
        cls.ctx = multiprocessing.get_context("fork")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.work = self.fixture.work
        self.challenge = self.fixture.challenge
        self.args = self.fixture.args()
        self.before = self.fixture.ledger.snapshot()
        self.previously_issued = self.fixture.ledger.outcome(self.challenge)
        self.assertEqual(self.previously_issued["developmentOnlyState"], "issued")

    def kill_writer(self, point):
        p = self.ctx.Process(
            target=M.child_writer_sigkill_ci_only,
            kwargs={"root": self.work, "record_args": self.args,
                    "trap_point": point},
        )
        p.start()
        p.join(timeout=15)
        if p.is_alive():
            p.kill()
            p.join(timeout=5)
            self.fail("C3E_TEST_WRITER_FAILED_TO_EXIT")
        self.assertEqual(p.exitcode, -signal.SIGKILL,
                         "must be actual Linux SIGKILL, not a mock crash")

    def fresh_read(self):
        recv, send = self.ctx.Pipe(duplex=False)
        try:
            p = self.ctx.Process(target=_fresh_reader,
                                 args=(self.work, self.challenge, send))
            p.start()
            send.close()
            self.assertTrue(recv.poll(10), "new process did not report")
            value = recv.recv()
            p.join(timeout=5)
            if p.is_alive():
                p.kill()
                p.join(timeout=5)
                self.fail("reader hung")
            self.assertEqual(p.exitcode, 0)
            self.assertNotIn("readerError", value, value)
            return value
        finally:
            recv.close()
            send.close()

    def all_denied(self, report):
        self.assertEqual(report["schema"], M.SCHEMA)
        self.assertEqual(report["status"], M.STATUS)
        self.assertEqual(
            report["next"],
            "HOLD_NO_AUTOMATIC_RETRY_INDEPENDENT_CUSTODIAN_REQUIRED",
        )
        self.assertEqual(
            set(report),
            {"schema", "status", "developmentOnlyObservedState",
             "developmentOnlyObservedHeadSha256",
             "developmentOnlyObservedSequence",
             "developmentOnlyObservedCommittedHeadSha256",
             "next", *M.DENIED},
        )
        for flag in M.DENIED:
            self.assertIs(report[flag], False, flag)

    def test_01_actual_sigkill_before_commit_keeps_local_nonce_issued(self):
        self.kill_writer(M.TRAPS[0])
        result = self.fresh_read()
        self.all_denied(result)
        self.assertEqual(result["developmentOnlyObservedState"], "issued")
        self.assertIsNone(result["developmentOnlyObservedCommittedHeadSha256"])

    def test_02_actual_sigkill_before_commit_keeps_old_history_head(self):
        self.kill_writer(M.TRAPS[0])
        result = self.fresh_read()
        self.assertEqual(result["developmentOnlyObservedSequence"],
                         self.before["previousSequence"])
        self.assertEqual(result["developmentOnlyObservedHeadSha256"],
                         self.before["previousHeadSha256"])
        self.all_denied(result)

    def test_03_actual_sigkill_after_commit_reports_local_consumed(self):
        self.kill_writer(M.TRAPS[1])
        result = self.fresh_read()
        self.assertEqual(result["developmentOnlyObservedState"], "consumed")
        self.assertEqual(result["developmentOnlyObservedSequence"],
                         self.before["previousSequence"] + 1)
        self.all_denied(result)

    def test_04_after_commit_kill_did_not_send_caller_ack(self):
        # SIGKILL exitcode is the only response. Commit persisted, but the
        # caller received no trusted terminal receipt.
        self.kill_writer(M.TRAPS[1])
        result = self.fresh_read()
        self.assertEqual(result["developmentOnlyObservedState"], "consumed")
        self.assertIs(result["signedTerminalReceiptVerified"], False)
        self.assertIs(result["safeToRetry"], False)

    def test_05_before_commit_kill_does_not_prove_protected_noncommit(self):
        self.kill_writer(M.TRAPS[0])
        result = self.fresh_read()
        self.assertIs(result["localStateProvesProtectedNonCommit"], False)
        self.all_denied(result)

    def test_06_after_commit_kill_does_not_prove_protected_commit(self):
        self.kill_writer(M.TRAPS[1])
        result = self.fresh_read()
        self.assertIs(result["localStateProvesProtectedCommit"], False)
        self.all_denied(result)

    def test_07_after_commit_kill_original_challenge_replay_refused_locally(self):
        self.kill_writer(M.TRAPS[1])
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "consumed")
        with self.assertRaisesRegex(F.M.Refused, "ALREADY_CONSUMED"):
            self.fixture.ledger.record(**self.args)

    def test_08_before_commit_kill_preserves_valid_test_proof_for_recovery(self):
        self.kill_writer(M.TRAPS[0])
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "issued")
        # Explicit operator-driven local fixture retry is mechanically
        # possible, but no production retry permission may be inferred.
        local = self.fixture.ledger.record(**self.args)
        self.assertIs(local["productionAuthority"], False)
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "consumed")
        self.assertIs(self.fresh_read()["safeToRetry"], False)

    def test_09_old_local_db_backup_can_undo_actual_killed_committed_process(self):
        backup = self.work / "precommit-fixture-copy"
        shutil.copy2(self.work / F.M.DB, backup)
        self.kill_writer(M.TRAPS[1])
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "consumed")
        # Expected local-only rollback vulnerability. Never a production PASS.
        shutil.copyfile(backup, self.work / F.M.DB)
        old = self.fresh_read()
        self.assertEqual(old["developmentOnlyObservedState"], "issued")
        self.assertEqual(old["developmentOnlyObservedSequence"],
                         self.before["previousSequence"])
        self.assertIs(old["independentRecoveryVerified"], False)
        self.assertIs(old["safeToRetry"], False)

    def test_10_restored_old_db_accepts_replayed_local_signed_fixture(self):
        backup = self.work / "precommit-fixture-copy"
        shutil.copy2(self.work / F.M.DB, backup)
        self.kill_writer(M.TRAPS[1])
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "consumed")
        shutil.copyfile(backup, self.work / F.M.DB)
        replay = self.fixture.ledger.record(**self.args)
        self.assertIs(replay["productionAuthority"], False)
        out = self.fresh_read()
        self.assertEqual(out["developmentOnlyObservedState"], "consumed")
        self.assertIs(out["externalRollbackResistanceVerified"], False)
        print("C3E_REAL_SIGKILL_LOCAL_ROLLBACK_REPLAY // PRODUCTION_HOLD")

    def test_11_killed_child_does_not_promote_prod_broker_or_signin(self):
        self.kill_writer(M.TRAPS[1])
        out = self.fresh_read()
        self.assertIs(out["canBeginSignIn"], False)
        self.assertIs(out["credentialActionsEnabled"], False)
        self.assertIs(out["productionAuthority"], False)
        self.all_denied(out)

    def test_12_recovered_snapshot_is_only_local_diagnostic(self):
        self.kill_writer(M.TRAPS[0])
        out = self.fresh_read()
        self.assertEqual(out["status"], M.STATUS)
        self.assertIs(out["independentlyPersistedPreviousHeadVerified"], False)
        self.assertIs(out["externallyConsumedOneUseChallengeVerified"], False)

    def test_13_production_recovery_admission_unconditionally_refused(self):
        with self.assertRaisesRegex(M.Refused, "NO_PROTECTED_HISTORY"):
            M.protected_recovery_admission()
        with self.assertRaisesRegex(M.Refused, "NO_PROTECTED_HISTORY"):
            M.protected_recovery_admission(self.args)

    def test_14_guard_rejects_self_hosted_or_fake_runner(self):
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "self-hosted"}):
            with self.assertRaises(M.Refused):
                M._guard(self.work)

    def test_15_child_writer_rejects_invalid_trap_before_any_write(self):
        with self.assertRaisesRegex(M.Refused, "EXACT_INPUTS_REQUIRED"):
            M.child_writer_sigkill_ci_only(
                root=self.work, record_args=self.args, trap_point="ALLOW_SIGNIN")
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "issued")

    def test_16_child_writer_rejects_mutated_record_argument_type(self):
        with self.assertRaisesRegex(M.Refused, "EXACT_INPUTS_REQUIRED"):
            M.child_writer_sigkill_ci_only(
                root=self.work, record_args=[], trap_point=M.TRAPS[0])
        self.assertEqual(self.fresh_read()["developmentOnlyObservedState"],
                         "issued")


if __name__ == "__main__":
    unittest.main(verbosity=2)
