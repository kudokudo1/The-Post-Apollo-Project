#!/usr/bin/env python3
"""DOC 1 C3e: hostile CI-only SQLite history and rollback demonstration.

Explicitly shows why local atomicity is useful AND why a rollbackable local DB
must never become a real independently custodied Sign-In authorization source.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_LOCAL_TEST_DEPENDENCY_REQUIRED")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("c3e_local_history_development_ledger",
         HERE / "C3eLocalDevelopmentHistoryLedger.py")
F = load("c3e_local_history_original_signed_test",
         ROOT / "tests/connections/test_connections_c3e_operator_witness_history_continuity.py")


class LocalHistoryLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0 or
                os.environ.get("GITHUB_ACTIONS") != "true" or
                os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_LOCAL_DISPOSABLE_ROOT_GITHUB_ONLY")

    def setUp(self):
        self.f = F.C3eWitnessHistoryContinuityTests(
            "test_01_signed_next_head_and_all_grants_still_false")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.work = Path(tempfile.mkdtemp(prefix="c3er-ci-localhistory-", dir="/run"))
        self.work.chmod(0o700)
        self.addCleanup(shutil.rmtree, self.work, True)
        M.initialize_ci_only(self.work)
        self.ledger = M.DevelopmentLedger(self.work)
        self.head = self.ledger.snapshot()["previousHeadSha256"]
        self.seq = self.ledger.snapshot()["previousSequence"]
        self.challenge = self.issue()
        self.sign_for(self.challenge)
        self.assertEqual(self.ledger.outcome(self.challenge)["developmentOnlyState"],
                         "issued")

    def issue(self, **kw):
        values = dict(host=self.f.doc["hostId"],
                      release_epoch=self.f.doc["releaseEpoch"],
                      release_seq=self.f.doc["releaseSequence"],
                      now_ms=1000, ttl_ms=4000)
        return self.ledger.issue(**{**values, **kw})

    def sign_for(self, challenge, *, head=None, seq=None):
        self.f.doc["previousHeadSha256"] = self.head if head is None else head
        self.f.doc["historySequence"] = (self.seq if seq is None else seq) + 1
        self.f.doc["challengeSha256"] = hashlib.sha256(challenge).hexdigest()
        self.f.updated()

    def args(self, challenge=None, **changes):
        if challenge is None:
            challenge = self.challenge
        f = self.f
        arguments = dict(
            challenge=challenge,
            enrollment_inputs=dict(f.inputs),
            signed_history_record=f.frame,
            history_signature=f.signature,
            pinned_history_authority=f.signer.public_key(),
            expected_history_authority_sha256=f.doc["historyAuthoritySha256"],
            revoked_history_authority_sha256=(),
            now_ms=1100,
        )
        return {**arguments, **changes}

    def commit(self, **changes):
        return self.ledger.record(**self.args(**changes))

    def refused(self, reason, **changes):
        with self.assertRaisesRegex(M.Refused, reason):
            self.commit(**changes)

    def assert_denied(self, output):
        self.assertEqual(output["status"], M.STATUS)
        for name in M.DENIED:
            self.assertIs(output[name], False, name)

    def test_01_true_signed_continuity_advances_only_dev_head(self):
        result = self.commit()
        self.assert_denied(result)
        self.assertIs(result["developmentOnlyHeadAdvanced"], True)
        self.assertEqual(result["nextHistorySequence"], self.seq + 1)
        self.assertEqual(self.ledger.snapshot()["previousHeadSha256"],
                         result["nextHistoryHeadSha256"])
        self.assertEqual(self.ledger.outcome(self.challenge)["developmentOnlyState"],
                         "consumed")

    def test_02_signed_proof_replay_refused(self):
        self.commit()
        self.refused("ALREADY_CONSUMED")

    def test_03_signed_record_tamper_does_not_spend(self):
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED",
                     signed_history_record=self.f.frame + b"x")
        self.assertEqual(self.ledger.outcome(self.challenge)["developmentOnlyState"],
                         "issued")

    def test_04_wrong_history_authority_pin_refused(self):
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED",
                     expected_history_authority_sha256="0" * 64)

    def test_05_wrong_previous_head_even_when_signed_refused(self):
        self.f.doc["previousHeadSha256"] = "f" * 64
        self.f.updated()
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED")

    def test_06_skipped_sequence_even_when_signed_refused(self):
        self.f.doc["historySequence"] += 2
        self.f.updated()
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED")

    def test_07_different_challenge_even_when_signed_refused(self):
        self.f.doc["challengeSha256"] = hashlib.sha256(b"another").hexdigest()
        self.f.updated()
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED")

    def test_08_wrong_signed_release_refused(self):
        self.f.doc["releaseSequence"] += 1
        self.f.updated()
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED")

    def test_09_expired_issued_challenge_refused(self):
        self.refused("CHALLENGE_EXPIRED", now_ms=5000)

    def test_10_unknown_challenge_not_created_by_consume(self):
        self.refused("CHALLENGE_UNKNOWN", challenge=b"\x22" * 32)

    def test_11_missing_database_never_auto_bootstraps(self):
        (self.work / M.DB).unlink()
        with self.assertRaises((M.Refused, M.R.Refused)):
            M.DevelopmentLedger(self.work)
        self.assertFalse((self.work / M.DB).exists())

    def test_12_duplicate_bootstrap_refused(self):
        with self.assertRaisesRegex(M.Refused, "EXISTS_NO_REINIT"):
            M.initialize_ci_only(self.work)

    def test_13_crash_before_commit_rolls_back_both(self):
        self.refused("SIMULATED_CRASH_BEFORE_COMMIT", fault="before_commit")
        self.assertEqual(self.ledger.snapshot()["previousSequence"], self.seq)
        self.assertEqual(self.ledger.outcome(self.challenge)["developmentOnlyState"],
                         "issued")
        self.assert_denied(self.commit())

    def test_14_ack_lost_after_commit_must_query(self):
        with self.assertRaisesRegex(M.UnknownAfterCommit, "QUERY_OUTCOME"):
            self.commit(fault="lost_ack")
        outcome = self.ledger.outcome(self.challenge)
        self.assert_denied(outcome)
        self.assertEqual(outcome["developmentOnlyState"], "consumed")
        self.refused("ALREADY_CONSUMED")

    def test_15_old_concurrent_challenge_cannot_fork_current_head(self):
        second = self.issue()
        self.commit()
        self.sign_for(second)
        self.refused("HISTORY_STALE_OR_FORK", challenge=second)

    def test_16_new_challenge_can_follow_successful_dev_head(self):
        first = self.commit()
        second = self.issue()
        self.sign_for(second, head=first["nextHistoryHeadSha256"],
                      seq=first["nextHistorySequence"])
        out = self.ledger.record(**self.args(challenge=second))
        self.assertEqual(out["nextHistorySequence"], self.seq + 2)
        self.assert_denied(out)

    def test_17_local_backup_restore_replays_same_valid_proof(self):
        """Expected SECURITY FAILURE of local-only antirollback, not a PASS grant."""
        before = self.work / "old-local-backup.fixture"
        shutil.copy2(self.work / M.DB, before)
        first = self.commit()
        self.assertEqual(self.ledger.outcome(self.challenge)["developmentOnlyState"],
                         "consumed")
        shutil.copyfile(before, self.work / M.DB)  # simulation of same-UID rollback
        restored = M.DevelopmentLedger(self.work)
        self.assertEqual(restored.outcome(self.challenge)["developmentOnlyState"],
                         "issued")
        again = restored.record(**self.args())
        self.assertEqual(again["nextHistoryHeadSha256"],
                         first["nextHistoryHeadSha256"])
        self.assert_denied(again)
        print("C3E_LOCAL_ROLLBACK_VULNERABILITY_DEMONSTRATED // NO_PROD_AUTHORITY")

    def test_18_world_writable_db_refused(self):
        (self.work / M.DB).chmod(0o666)
        with self.assertRaises(M.R.Refused):
            M.DevelopmentLedger(self.work)

    def test_19_symlink_db_swap_refused(self):
        original = self.work / M.DB
        backup = self.work / "fixture-db.backup"
        original.rename(backup)
        original.symlink_to(backup)
        with self.assertRaises(M.R.Refused):
            M.DevelopmentLedger(self.work)

    def test_20_local_ledger_disabled_without_github_runtime(self):
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with self.assertRaises(M.R.Refused):
                M.DevelopmentLedger(self.work)

    def test_21_local_ledger_disabled_without_hosted_runner(self):
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "self-hosted"}):
            with self.assertRaises(M.R.Refused):
                M.DevelopmentLedger(self.work)

    def test_22_bad_boolean_clock_or_ttl_refused(self):
        with self.assertRaisesRegex(M.Refused, "ISSUANCE_FIELDS_INVALID"):
            self.issue(now_ms=True)
        with self.assertRaisesRegex(M.Refused, "ISSUANCE_FIELDS_INVALID"):
            self.issue(ttl_ms=True)

    def test_23_wrong_expected_host_refused_before_signer(self):
        changed = dict(self.f.inputs)
        changed["expected_host_id"] = "substituted-host"
        self.refused("RELEASE_OR_HOST_MISMATCH", enrollment_inputs=changed)

    def test_24_no_production_admission_entry_point(self):
        with self.assertRaisesRegex(M.Refused, "NEVER_AUTHORIZES_PRODUCTION"):
            self.ledger.production_admission()

    def test_25_snapshot_never_promotes_authority(self):
        self.assert_denied(self.ledger.snapshot())
        self.assert_denied(self.ledger.outcome(self.challenge))

    def test_26_two_racing_commits_one_wins(self):
        args = self.args()
        def try_once(_):
            try:
                return M.DevelopmentLedger(self.work).record(**args)
            except M.Refused as exc:
                return str(exc)
        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(try_once, range(2)))
        self.assertEqual(
            sum(type(x) is dict for x in outcomes), 1, outcomes)
        self.assertEqual(
            sum("ALREADY_CONSUMED" in x for x in outcomes if type(x) is str),
            1, outcomes)
        self.assertEqual(self.ledger.snapshot()["previousSequence"], self.seq + 1)

    def test_27_invalid_signed_authority_field_refused(self):
        self.f.doc["productionAuthority"] = True
        self.f.updated()
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED")

    def test_28_revoked_history_signer_refused(self):
        self.refused("EXISTING_SIGNED_VERIFIER_REFUSED",
                     revoked_history_authority_sha256=(
                         self.f.doc["historyAuthoritySha256"],))


if __name__ == "__main__":
    unittest.main(verbosity=2)
