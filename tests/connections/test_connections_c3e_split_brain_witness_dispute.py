#!/usr/bin/env python3
"""DOC 1: competing local witness histories never determine trusted winner."""
from __future__ import annotations

import importlib.util
import multiprocessing
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_SPLIT_BRAIN_TEST_DEPENDENCY_REQUIRED")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


M = _load("c3e_split_brain_under_test",
          HERE / "C3eSplitBrainWitnessDisputeCI.py")
F = _load("c3e_split_brain_existing_local_fixture",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


def _advance_child(root, previous, candidate, sender):
    try:
        out = M.W.advance_ci_only(
            root, old_head=previous["testHeadSha256"],
            old_sequence=previous["testSequence"],
            new_local_snapshot=candidate)
        sender.send({"result": out})
    except BaseException as exc:
        sender.send({"error": f"{type(exc).__name__}: {exc}"})
    finally:
        sender.close()


class LocalWitnessSplitBrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_SPLIT_BRAIN_DISPOSABLE_HOSTED_ROOT_ONLY")
        cls.ctx = multiprocessing.get_context("fork")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.guest = M.W.S.TrustBoundary(
            required_mode=M.W.S.LOCAL_DEVELOPMENT,
            local_adapter=M.W.S.LocalSQLiteTestAdapter(
                M.W.S.L.DevelopmentLedger(self.fixture.work)))
        self.before = self.guest.read_current_snapshot()
        self.left = self._make_root()
        self.right = self._make_root()
        M.W.initialize_ci_only(self.left, initial_local_snapshot=self.before)
        M.W.initialize_ci_only(self.right, initial_local_snapshot=self.before)

    def _make_root(self):
        root = Path(tempfile.mkdtemp(prefix="c3ew-ci-", dir="/run"))
        os.chmod(root, 0o700)
        self.addCleanup(shutil.rmtree, root)
        return root

    def candidate(self, letter):
        return {
            **self.before, "testHeadSha256": letter * 64,
            "testSequence": self.before["testSequence"] + 1,
        }

    def advance(self, root, letter):
        return M.W.advance_ci_only(
            root, old_head=self.before["testHeadSha256"],
            old_sequence=self.before["testSequence"],
            new_local_snapshot=self.candidate(letter))

    def observe(self, root, candidate=None):
        return M.W.compare_ci_only(
            root, local_snapshot=self.before if candidate is None else candidate)

    def fork_two_writers(self, left_candidate=None, right_candidate=None):
        proposals = [
            (self.left, self.candidate("a") if left_candidate is None
             else left_candidate),
            (self.right, self.candidate("b") if right_candidate is None
             else right_candidate),
        ]
        active = []
        try:
            for root, candidate in proposals:
                recv, send = self.ctx.Pipe(duplex=False)
                process = self.ctx.Process(
                    target=_advance_child,
                    args=(root, self.before, candidate, send))
                process.start()
                send.close()
                active.append((process, recv, send))
            result = []
            for process, recv, _ in active:
                self.assertTrue(recv.poll(10), "split writer did not finish")
                result.append(recv.recv())
                process.join(5)
                self.assertEqual(process.exitcode, 0)
            return result
        finally:
            for process, recv, send in active:
                recv.close()
                send.close()
                if process.is_alive():
                    process.kill()
                    process.join(5)

    def denied(self, report):
        self.assertEqual(report["schema"], M.SCHEMA)
        self.assertEqual(report["status"], M.STATUS)
        self.assertEqual(
            report["next"],
            "UNKNOWN_HOLD_NO_AUTOMATIC_RETRY_INDEPENDENT_CUSTODIAN_REQUIRED")
        self.assertIsNone(report["winner"])
        self.assertEqual(report["safeActions"], [])
        self.assertEqual(report["candidateEvidence"],
                         "CALLER_PROVIDED_DISPOSABLE_LOCAL_REPORTS")
        self.assertEqual(set(report), {
            "schema", "status", "dispute",
            "leftLocalCandidateHeadSha256", "leftLocalCandidateSequence",
            "rightLocalCandidateHeadSha256", "rightLocalCandidateSequence",
            "candidateEvidence", "winner", "safeActions", "next",
            *M.DENIED,
        })
        for key in M.DENIED:
            self.assertIs(report[key], False, key)

    def compare(self, left=None, right=None):
        return M.reconcile_ci_only(
            left_observation=self.observe(self.left) if left is None else left,
            right_observation=self.observe(self.right) if right is None else right)

    def test_01_two_concurrent_witnesses_accept_conflicting_heads(self):
        results = self.fork_two_writers()
        self.assertTrue(all("result" in record for record in results), results)
        out = self.compare(self.observe(self.left, self.candidate("a")),
                           self.observe(self.right, self.candidate("b")))
        self.assertEqual(out["dispute"], M.FORK)
        self.denied(out)
        print("C3E_TWO_CLONED_WITNESSES_BOTH_ACCEPT_DIFFERENT_HEADS // HOLD")

    def test_02_same_initial_head_is_not_an_independent_quorum(self):
        out = self.compare()
        self.assertEqual(out["dispute"], M.AGREE)
        self.denied(out)

    def test_03_same_candidate_separately_committed_still_not_trust(self):
        self.advance(self.left, "a")
        self.advance(self.right, "a")
        out = self.compare(self.observe(self.left, self.candidate("a")),
                           self.observe(self.right, self.candidate("a")))
        self.assertEqual(out["dispute"], M.AGREE)
        self.denied(out)

    def test_04_caller_replays_one_report_as_two_witnesses(self):
        copied = self.observe(self.left)
        out = self.compare(copied, dict(copied))
        self.assertEqual(out["dispute"], M.AGREE)
        self.assertIs(out["independentlyEnrolledWitnessVerified"], False)
        self.denied(out)

    def test_05_left_newer_sequence_cannot_be_chosen(self):
        self.advance(self.left, "a")
        out = self.compare(self.observe(self.left, self.candidate("a")),
                           self.observe(self.right))
        self.assertEqual(out["dispute"], M.UNEQUAL)
        self.denied(out)

    def test_06_right_newer_sequence_cannot_be_chosen(self):
        self.advance(self.right, "b")
        out = self.compare(self.observe(self.left),
                           self.observe(self.right, self.candidate("b")))
        self.assertEqual(out["dispute"], M.UNEQUAL)
        self.denied(out)

    def test_07_original_guest_ahead_of_shadow_is_not_witness_vote(self):
        out = self.compare(
            self.observe(self.left, self.candidate("a")),
            self.observe(self.right))
        self.assertEqual(out["dispute"], M.UNTRUSTED)
        self.denied(out)

    def test_08_same_sequence_guest_vs_shadow_head_fork_is_not_vote(self):
        forged_local = dict(
            self.before, testHeadSha256="f" * 64)
        out = self.compare(
            self.observe(self.left, forged_local),
            self.observe(self.right))
        self.assertEqual(out["dispute"], M.UNTRUSTED)
        self.denied(out)

    def test_09_extra_authority_field_refused(self):
        forged = dict(self.observe(self.left), productionAuthority=True)
        with self.assertRaisesRegex(M.Refused, "STATUS_INJECTION"):
            self.compare(forged, self.observe(self.right))

    def test_10_missing_field_refused(self):
        forged = dict(self.observe(self.left))
        del forged["shadowObservedSequence"]
        with self.assertRaisesRegex(M.Refused, "EXTRA_DIAGNOSTIC"):
            self.compare(forged, self.observe(self.right))

    def test_11_wrong_schema_refused(self):
        forged = dict(self.observe(self.left), schema="trusted.production")
        with self.assertRaisesRegex(M.Refused, "STATUS_INJECTION"):
            self.compare(forged, self.observe(self.right))

    def test_12_wrong_status_refused(self):
        forged = dict(self.observe(self.left), status="COMMITTED")
        with self.assertRaisesRegex(M.Refused, "STATUS_INJECTION"):
            self.compare(forged, self.observe(self.right))

    def test_13_wrong_next_refused(self):
        forged = dict(self.observe(self.left), next="AUTO_RETRY_ALLOWED")
        with self.assertRaisesRegex(M.Refused, "STATUS_INJECTION"):
            self.compare(forged, self.observe(self.right))

    def test_14_boolean_sequence_refused(self):
        forged = dict(self.observe(self.left), shadowObservedSequence=True)
        with self.assertRaisesRegex(M.Refused, "INVALID_SEQUENCE"):
            self.compare(forged, self.observe(self.right))

    def test_15_uppercase_head_refused(self):
        forged = dict(self.observe(self.left), shadowObservedHeadSha256="A"*64)
        with self.assertRaisesRegex(M.Refused, "INVALID_HEAD"):
            self.compare(forged, self.observe(self.right))

    def test_16_contradictory_relation_refused(self):
        forged = dict(self.observe(self.left), relation=M.W.STALE)
        with self.assertRaisesRegex(M.Refused, "CONTRADICTORY_LOCAL_RELATION"):
            self.compare(forged, self.observe(self.right))

    def test_17_any_positive_denial_flag_refused(self):
        forged = dict(self.observe(self.left), safeToRetry=True)
        with self.assertRaisesRegex(M.Refused, "STATUS_INJECTION"):
            self.compare(forged, self.observe(self.right))

    def test_18_choose_protected_winner_unconditionally_refuses(self):
        with self.assertRaisesRegex(M.Refused, "CANNOT_PICK_PROTECTED_WINNER"):
            M.choose_protected_winner(self.compare())

    def test_19_two_unenrolled_roots_have_distinct_files_not_distinct_authority(self):
        self.assertNotEqual((self.left / M.W.DB).resolve(),
                            (self.right / M.W.DB).resolve())
        self.denied(self.compare())

    def test_20_both_shadow_files_can_be_rolled_back_to_same_old_head(self):
        old_left = self.left / "backup-left"
        old_right = self.right / "backup-right"
        shutil.copy2(self.left / M.W.DB, old_left)
        shutil.copy2(self.right / M.W.DB, old_right)
        self.advance(self.left, "a")
        self.advance(self.right, "a")
        shutil.copyfile(old_left, self.left / M.W.DB)
        shutil.copyfile(old_right, self.right / M.W.DB)
        out = self.compare()
        self.assertEqual(out["dispute"], M.AGREE)
        self.assertEqual(out["leftLocalCandidateSequence"],
                         self.before["testSequence"])
        self.denied(out)

    def test_21_wrong_type_or_empty_report_refused(self):
        for candidate in (None, False, [], {}, "string"):
            with self.subTest(type=type(candidate).__name__):
                with self.assertRaises(M.Refused):
                    M.reconcile_ci_only(
                        left_observation=candidate,
                        right_observation=self.observe(self.right))

    def test_22_original_protected_c3e_still_refuses_shadow_local_adapter(self):
        protected = M.W.S.TrustBoundary(
            required_mode=M.W.S.PROTECTED_REQUIRED)
        with self.assertRaisesRegex(M.W.S.Refused, "HOLD_NO_FALLBACK"):
            protected.read_current_snapshot()
        self.denied(self.compare())


if __name__ == "__main__":
    unittest.main(verbosity=2)
