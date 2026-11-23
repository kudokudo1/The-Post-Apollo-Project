#!/usr/bin/env python3
"""DOC 1: CI-only storage switch tests. Protected mode NEVER uses SQLite."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "tests/connections/c3e_release_trust"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_STORAGE_TEST_DEPENDENCY_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("c3e_storage_independent_boundary",
         SRC / "C3eStorageIndependentTrustBoundary.py")
F = load("c3e_storage_original_local_fixture",
         ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


class StorageBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_STORAGE_DISPOSABLE_HOSTED_GITHUB_CI_REQUIRED")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.local = M.LocalSQLiteTestAdapter(
            M.L.DevelopmentLedger(self.fixture.work))
        self.dev = M.TrustBoundary(required_mode=M.LOCAL_DEVELOPMENT,
                                   local_adapter=self.local)
        self.protected = M.TrustBoundary(required_mode=M.PROTECTED_REQUIRED)

    def denied(self, result):
        self.assertIs(type(result), dict)
        self.assertEqual(result["schema"], M.SCHEMA)
        for key in M.DENIED:
            self.assertIs(result[key], False, key)

    def test_01_local_current_snapshot_is_diagnostic(self):
        out = self.dev.read_current_snapshot()
        self.denied(out)
        self.assertEqual(out["status"], M.STATUS_LOCAL)
        self.assertEqual(out["testSequence"], self.fixture.seq)
        self.assertEqual(out["testHeadSha256"], self.fixture.head)

    def test_02_local_challenge_diagnostic_never_trusted(self):
        issued = self.dev.issue_challenge(
            host=self.fixture.f.doc["hostId"],
            release_epoch=self.fixture.f.doc["releaseEpoch"],
            release_seq=self.fixture.f.doc["releaseSequence"],
            now_ms=1000, ttl_ms=2000)
        self.denied(issued)
        self.assertEqual(issued["status"], M.STATUS_LOCAL)
        self.assertEqual(len(issued["testChallenge"]), 32)

    def test_03_local_commit_reuses_verified_history_contract(self):
        out = self.dev.commit_signed_history(**self.fixture.args())
        self.denied(out)
        self.assertEqual(out["testSequence"], self.fixture.seq + 1)
        self.assertEqual(
            out["testHeadSha256"],
            self.fixture.ledger.snapshot()["previousHeadSha256"])

    def test_04_local_outcome_only_diagnostic(self):
        before = self.dev.lookup_terminal_outcome(self.fixture.challenge)
        self.denied(before)
        self.assertEqual(before["testState"], "issued")
        self.dev.commit_signed_history(**self.fixture.args())
        after = self.dev.lookup_terminal_outcome(self.fixture.challenge)
        self.denied(after)
        self.assertEqual(after["testState"], "consumed")

    def test_05_replay_still_refused_in_current_local_image(self):
        self.dev.commit_signed_history(**self.fixture.args())
        with self.assertRaisesRegex(M.L.Refused, "ALREADY_CONSUMED"):
            self.dev.commit_signed_history(**self.fixture.args())

    def test_06_signed_history_tamper_refused(self):
        args = self.fixture.args()
        args["signed_history_record"] += b"x"
        with self.assertRaisesRegex(M.L.Refused, "EXISTING_SIGNED_VERIFIER_REFUSED"):
            self.dev.commit_signed_history(**args)

    def test_07_unknown_issued_nonce_refused(self):
        with self.assertRaisesRegex(M.L.Refused, "CHALLENGE_UNKNOWN"):
            self.dev.lookup_terminal_outcome(b"\x14" * 32)

    def test_08_local_lost_ack_requires_query_no_autoretry(self):
        args = self.fixture.args()
        args["fault"] = "lost_ack"
        with self.assertRaisesRegex(M.UnknownAfterCommit, "QUERY_OUTCOME"):
            self.dev.commit_signed_history(**args)
        self.assertEqual(
            self.dev.lookup_terminal_outcome(self.fixture.challenge)["testState"],
            "consumed")
        with self.assertRaisesRegex(M.L.Refused, "ALREADY_CONSUMED"):
            self.dev.commit_signed_history(**self.fixture.args())

    def test_09_unknown_mode_refused(self):
        with self.assertRaisesRegex(M.Refused, "UNKNOWN_TRUST_MODE"):
            M.TrustBoundary(required_mode="production", local_adapter=self.local)

    def test_10_boolean_mode_refused(self):
        with self.assertRaisesRegex(M.Refused, "UNKNOWN_TRUST_MODE"):
            M.TrustBoundary(required_mode=True)

    def test_11_development_mode_requires_explicit_local_adapter(self):
        with self.assertRaisesRegex(M.Refused, "EXPLICIT_LOCAL_CI_ADAPTER"):
            M.TrustBoundary(required_mode=M.LOCAL_DEVELOPMENT)

    def test_12_fake_backend_not_accepted_as_local(self):
        with self.assertRaisesRegex(M.Refused, "ONLY_KNOWN_DISPOSABLE_LOCAL_LEDGER"):
            M.LocalSQLiteTestAdapter(object())

    def test_13_protected_mode_refuses_local_adapter(self):
        with self.assertRaisesRegex(M.Refused, "REFUSES_LOCAL_ADAPTER"):
            M.TrustBoundary(required_mode=M.PROTECTED_REQUIRED,
                            local_adapter=self.local)

    def test_14_protected_status_is_explicit_hold(self):
        out = self.protected.protected_required_status()
        self.denied(out)
        self.assertEqual(out["status"], M.STATUS_HOLD)
        self.assertEqual(out["source"], M.PROTECTED_REQUIRED)

    def test_15_protected_read_refuses_without_sqlite_fallback(self):
        with mock.patch.object(self.local, "snapshot",
                               side_effect=AssertionError("local called")):
            with self.assertRaisesRegex(M.Refused, "HOLD_NO_FALLBACK"):
                self.protected.read_current_snapshot()

    def test_16_protected_issue_refuses_without_sqlite_fallback(self):
        with self.assertRaisesRegex(M.Refused, "HOLD_NO_FALLBACK"):
            self.protected.issue_challenge(
                host="host", release_epoch=1, release_seq=1,
                now_ms=100, ttl_ms=1000)

    def test_17_protected_commit_refuses_without_sqlite_fallback(self):
        with self.assertRaisesRegex(M.Refused, "HOLD_NO_FALLBACK"):
            self.protected.commit_signed_history(**self.fixture.args())

    def test_18_protected_outcome_refuses_without_sqlite_fallback(self):
        with self.assertRaisesRegex(M.Refused, "HOLD_NO_FALLBACK"):
            self.protected.lookup_terminal_outcome(self.fixture.challenge)

    def test_19_protected_admission_unconditionally_refused(self):
        for boundary in (self.dev, self.protected):
            with self.assertRaisesRegex(M.Refused, "NO_PROTECTED_AUTHORITY"):
                boundary.protected_admission()

    def test_20_no_enrollment_revocation_authority(self):
        for boundary in (self.dev, self.protected):
            with self.assertRaisesRegex(M.Refused, "NO_AUTHORIZED_ENROLLMENT"):
                boundary.revoke_enrollment("fake-root")

    def test_21_bad_local_snapshot_authority_flag_refused(self):
        bad = self.fixture.ledger.snapshot()
        bad["productionAuthority"] = True
        with mock.patch.object(self.local._ledger, "snapshot", return_value=bad):
            with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
                self.dev.read_current_snapshot()

    def test_22_missing_local_snapshot_field_refused(self):
        bad = self.fixture.ledger.snapshot()
        bad.pop("testEpoch")
        with mock.patch.object(self.local._ledger, "snapshot", return_value=bad):
            with self.assertRaisesRegex(M.Refused, "UNEXPECTED_BACKEND_FIELDS"):
                self.dev.read_current_snapshot()

    def test_23_invalid_local_snapshot_epoch_refused(self):
        bad = self.fixture.ledger.snapshot()
        bad["testEpoch"] = "fixture"  # Cannot invent an approved key epoch.
        with mock.patch.object(self.local._ledger, "snapshot", return_value=bad):
            with self.assertRaisesRegex(M.Refused, "SNAPSHOT_MALFORMED"):
                self.dev.read_current_snapshot()

    def test_24_backend_commit_claims_real_authority_refused(self):
        bad = self.fixture.ledger.record(**self.fixture.args())
        bad["hostAuthenticated"] = True
        with mock.patch.object(self.local, "commit", return_value=bad):
            with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
                self.dev.commit_signed_history(**self.fixture.args())

    def test_25_backend_outcome_invents_grant_refused(self):
        bad = self.fixture.ledger.outcome(self.fixture.challenge)
        bad["credentialActionsEnabled"] = True
        with mock.patch.object(self.local, "outcome", return_value=bad):
            with self.assertRaisesRegex(M.Refused, "AUTHORITY_PROMOTION"):
                self.dev.lookup_terminal_outcome(self.fixture.challenge)

    def test_26_protected_mode_never_admits_remote_looking_object(self):
        class ClaimedRemote:
            certified = True
            status = "PROTECTED_CUSTODIAN_VERIFIED"
        with self.assertRaisesRegex(M.Refused, "REFUSES_LOCAL_ADAPTER"):
            M.TrustBoundary(required_mode=M.PROTECTED_REQUIRED,
                            local_adapter=ClaimedRemote())

    def test_27_development_mode_cannot_claim_protected_status(self):
        with self.assertRaisesRegex(M.Refused, "MODE_NOT_PROTECTED"):
            self.dev.protected_required_status()

    def test_28_local_database_image_rollback_remains_nonauthoritative(self):
        import shutil
        backup = self.fixture.work / "c3e-storage-old-local-fixture"
        shutil.copy2(self.fixture.work / M.L.DB, backup)
        original = self.dev.commit_signed_history(**self.fixture.args())
        self.denied(original)
        shutil.copyfile(backup, self.fixture.work / M.L.DB)
        fresh = M.TrustBoundary(
            required_mode=M.LOCAL_DEVELOPMENT,
            local_adapter=M.LocalSQLiteTestAdapter(
                M.L.DevelopmentLedger(self.fixture.work)))
        replay = fresh.commit_signed_history(**self.fixture.args())
        self.denied(replay)
        self.assertEqual(replay["testHeadSha256"], original["testHeadSha256"])
        self.denied(self.protected.protected_required_status())
        print("C3E_STORAGE_LOCAL_ROLLBACK_REPLAY // PROTECTED_AUTHORITY_STILL_HOLD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
