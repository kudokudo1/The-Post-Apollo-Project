#!/usr/bin/env python3
"""DOC 1: two disposable SQLite stores still cannot create independent custody."""
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
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_SPLITSTORE_EXPECTED_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("c3e_split_store_under_test",
          HERE / "C3eSplitStoreRollbackWitnessCI.py")
F = _load("c3e_split_store_existing_ledger_fixture",
          ROOT / "tests/connections/test_connections_c3e_local_development_history_ledger.py")


def _read_in_child(root, guest_snapshot, channel):
    try:
        channel.send({"result": M.compare_ci_only(
            root, local_snapshot=guest_snapshot)})
    except BaseException as exc:
        channel.send({"error": f"{type(exc).__name__}: {exc}"})
    finally:
        channel.close()


def _advance_in_child(root, previous_head, previous_seq, next_snapshot,
                      channel, die_after_commit=False):
    try:
        result = M.advance_ci_only(
            root, old_head=previous_head, old_sequence=previous_seq,
            new_local_snapshot=next_snapshot)
        if die_after_commit:
            os.kill(os.getpid(), signal.SIGKILL)
            os._exit(121)
        channel.send({"result": result})
    except BaseException as exc:
        channel.send({"error": f"{type(exc).__name__}: {exc}"})
    finally:
        channel.close()


class SplitStoreRollbackWitnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_SPLITSTORE_REAL_HOSTED_CI_ONLY")
        cls.ctx = multiprocessing.get_context("fork")

    def setUp(self):
        self.fixture = F.LocalHistoryLedgerTests(
            "test_01_true_signed_continuity_advances_only_dev_head")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.local = M.S.TrustBoundary(
            required_mode=M.S.LOCAL_DEVELOPMENT,
            local_adapter=M.S.LocalSQLiteTestAdapter(
                M.S.L.DevelopmentLedger(self.fixture.work)))
        self.protected = M.S.TrustBoundary(
            required_mode=M.S.PROTECTED_REQUIRED)
        self.shadow = Path(tempfile.mkdtemp(prefix="c3ew-ci-", dir="/run"))
        os.chmod(self.shadow, 0o700)
        self.addCleanup(shutil.rmtree, self.shadow)
        self.before = self.local.read_current_snapshot()
        M.initialize_ci_only(self.shadow, initial_local_snapshot=self.before)

    def local_snap(self):
        return self.local.read_current_snapshot()

    def observe(self, snap=None):
        return M.compare_ci_only(
            self.shadow,
            local_snapshot=self.local_snap() if snap is None else snap)

    def denied(self, result):
        self.assertEqual(result["schema"], M.SCHEMA)
        self.assertEqual(result["status"], M.STATUS)
        self.assertEqual(
            result["next"],
            "HOLD_NO_AUTOMATIC_RETRY_OPERATOR_ENROLLED_CUSTODIAN_REQUIRED",
        )
        self.assertEqual(set(result), {
            "schema", "status", "relation",
            "localObservedHeadSha256", "localObservedSequence",
            "shadowObservedHeadSha256", "shadowObservedSequence",
            "next", *M.DENIED,
        })
        for name in M.DENIED:
            self.assertIs(result[name], False, name)

    def advance(self):
        old = self.before
        next_snap = self.local_snap()
        return M.advance_ci_only(
            self.shadow, old_head=old["testHeadSha256"],
            old_sequence=old["testSequence"], new_local_snapshot=next_snap)

    def _child_request(self, fn, *args):
        recv, send = self.ctx.Pipe(duplex=False)
        try:
            p = self.ctx.Process(target=fn, args=(*args, send))
            p.start()
            send.close()
            self.assertTrue(recv.poll(10), "forked observation process hung")
            result = recv.recv()
            p.join(timeout=5)
            if p.is_alive():
                p.kill()
                p.join(timeout=5)
                self.fail("child hung after response")
            self.assertEqual(p.exitcode, 0)
            return result
        finally:
            recv.close()
            send.close()

    def test_01_initial_split_store_match_is_still_not_protected(self):
        report = self.observe()
        self.assertEqual(report["relation"], M.MATCH)
        self.denied(report)

    def test_02_existing_signed_guest_commit_can_advance_reference(self):
        original = self.local_snap()
        self.fixture.commit()
        out = self.advance()
        self.assertEqual(out["shadowObservedSequence"],
                         original["testSequence"] + 1)
        self.denied(out)
        self.assertEqual(self.observe()["relation"], M.MATCH)

    def test_03_unadvanced_shadow_detects_guest_ahead_but_not_trusted(self):
        self.fixture.commit()
        out = self.observe()
        self.assertEqual(out["relation"], M.AHEAD)
        self.denied(out)

    def test_04_actual_local_restore_detects_stale_guest_vs_retained_shadow(self):
        backup = self.shadow / "precommit-guest-backup"
        shutil.copy2(self.fixture.work / F.M.DB, backup)
        self.fixture.commit()
        self.advance()
        shutil.copyfile(backup, self.fixture.work / F.M.DB)
        out = self.observe()
        self.assertEqual(out["relation"], M.STALE)
        self.assertEqual(out["localObservedSequence"],
                         self.before["testSequence"])
        self.denied(out)

    def test_05_local_replay_can_catch_up_to_same_shadow_head_without_authority(self):
        backup = self.shadow / "precommit-guest-backup"
        shutil.copy2(self.fixture.work / F.M.DB, backup)
        self.fixture.commit()
        first_head = self.local_snap()["testHeadSha256"]
        self.advance()
        shutil.copyfile(backup, self.fixture.work / F.M.DB)
        self.assertEqual(self.observe()["relation"], M.STALE)
        self.fixture.commit()
        out = self.observe()
        self.assertEqual(out["relation"], M.MATCH)
        self.assertEqual(out["localObservedHeadSha256"], first_head)
        self.denied(out)

    def test_06_competing_shadow_update_from_old_head_rejected(self):
        self.fixture.commit()
        self.advance()
        with self.assertRaisesRegex(M.Refused, "FORK_OR_STALE"):
            self.advance()
        self.assertEqual(self.observe()["relation"], M.MATCH)

    def test_07_same_sequence_different_head_detected_as_fork(self):
        raw = dict(self.before, testHeadSha256="f" * 64)
        out = self.observe(raw)
        self.assertEqual(out["relation"], M.FORK)
        self.denied(out)

    def test_08_source_or_mode_substitution_refused(self):
        forged = dict(self.before, source=M.S.PROTECTED_REQUIRED)
        with self.assertRaisesRegex(M.Refused, "SNAPSHOT_REFUSED"):
            self.observe(forged)

    def test_09_extra_positive_claim_is_refused(self):
        forged = dict(self.before, productionAuthority=True)
        with self.assertRaisesRegex(M.Refused, "SNAPSHOT_REFUSED"):
            self.observe(forged)

    def test_10_denial_flag_changed_to_true_is_refused(self):
        forged = dict(self.before, trustedCurrentHeadVerified=True)
        with self.assertRaisesRegex(M.Refused, "SNAPSHOT_REFUSED"):
            self.observe(forged)

    def test_11_bad_sequence_and_head_never_make_reference(self):
        for value in (True, 0, -1, "1"):
            forged = dict(self.before, testSequence=value)
            with self.subTest(value=value), self.assertRaises(M.Refused):
                self.observe(forged)
        for value in ("A" * 64, "f" * 63, True, None):
            forged = dict(self.before, testHeadSha256=value)
            with self.subTest(value=value), self.assertRaises(M.Refused):
                self.observe(forged)

    def test_12_refuse_reinitialization_of_existing_shadow(self):
        with self.assertRaisesRegex(M.Refused, "NO_REINITIALIZATION"):
            M.initialize_ci_only(
                self.shadow, initial_local_snapshot=self.before)

    def test_13_shadow_database_cannot_be_automatically_recreated(self):
        (self.shadow / M.DB).unlink()
        with self.assertRaisesRegex(M.Refused, "MISSING_NO_AUTO_CREATE"):
            self.observe()
        self.assertFalse((self.shadow / M.DB).exists())

    def test_14_shadow_directory_symlink_refused(self):
        alias = self.shadow.parent / (self.shadow.name + "-alias")
        alias.symlink_to(self.shadow, target_is_directory=True)
        self.addCleanup(alias.unlink)
        with self.assertRaisesRegex(M.Refused, "UNSAFE_FIXTURE_ROOT"):
            M.compare_ci_only(alias, local_snapshot=self.before)

    def test_15_shadow_root_outside_disposable_run_refused(self):
        with self.assertRaisesRegex(M.Refused, "UNSAFE_FIXTURE_ROOT"):
            M.compare_ci_only(Path("/var/lib"), local_snapshot=self.before)

    def test_16_protected_mode_still_no_local_sqlite_fallback(self):
        with self.assertRaisesRegex(M.S.Refused, "HOLD_NO_FALLBACK"):
            self.protected.read_current_snapshot()
        self.assertIs(self.protected.protected_required_status()
                      ["protectedCustodianReachable"], False)

    def test_17_witness_process_restart_retains_local_shadow_only(self):
        self.fixture.commit()
        self.advance()
        child = self._child_request(
            _read_in_child, self.shadow, self.local_snap())
        self.assertNotIn("error", child, child)
        self.assertEqual(child["result"]["relation"], M.MATCH)
        self.denied(child["result"])

    def test_18_two_forked_witness_writers_compete_from_same_head(self):
        # Competing caller-provided candidate heads are synthetic, not
        # authenticated source proof. Exactly one compare-and-swap wins.
        proposals = [
            dict(self.before, testSequence=self.before["testSequence"]+1,
                 testHeadSha256="a"*64),
            dict(self.before, testSequence=self.before["testSequence"]+1,
                 testHeadSha256="b"*64),
        ]
        processes, channels = [], []
        for candidate in proposals:
            recv, send = self.ctx.Pipe(duplex=False)
            p = self.ctx.Process(
                target=_advance_in_child,
                args=(self.shadow, self.before["testHeadSha256"],
                      self.before["testSequence"], candidate, send))
            p.start()
            send.close()
            channels.append((recv, send))
            processes.append(p)
        try:
            reports = []
            for (recv, _), p in zip(channels, processes):
                self.assertTrue(recv.poll(10))
                reports.append(recv.recv())
                p.join(timeout=5)
                self.assertEqual(p.exitcode, 0)
            self.assertEqual(sum("result" in x for x in reports), 1)
            self.assertEqual(sum("error" in x for x in reports), 1)
            self.assertIn("FORK_OR_STALE", str(reports))
            self.denied(next(x["result"] for x in reports if "result" in x))
        finally:
            for recv, send in channels:
                recv.close()
                send.close()
            for p in processes:
                if p.is_alive():
                    p.kill()
                    p.join(timeout=5)

    def test_19_lost_ack_after_witness_commit_is_still_hold(self):
        self.fixture.commit()
        recv, send = self.ctx.Pipe(duplex=False)
        p = self.ctx.Process(
            target=_advance_in_child,
            args=(self.shadow, self.before["testHeadSha256"],
                  self.before["testSequence"], self.local_snap(),
                  send, True))
        try:
            p.start()
            send.close()
            p.join(timeout=10)
            if p.is_alive():
                p.kill()
                p.join(timeout=5)
                self.fail("witness writer hung")
            self.assertEqual(p.exitcode, -signal.SIGKILL)
            # A closed pipe becomes readable at EOF, but contains no ACK.
            self.assertTrue(recv.poll(1))
            with self.assertRaises(EOFError):
                recv.recv()
            fresh = self._child_request(
                _read_in_child, self.shadow, self.local_snap())
            self.assertEqual(fresh["result"]["relation"], M.MATCH)
            self.denied(fresh["result"])
        finally:
            recv.close()
            send.close()

    def test_20_same_host_restore_of_both_databases_defeats_shadow_comparison(self):
        # This is the point of the experiment: two DB files on one host are
        # NOT necessarily two independent failure or administrator domains.
        guest_backup = self.shadow / "old-guest-image"
        shadow_backup = self.shadow / "old-shadow-image"
        shutil.copy2(self.fixture.work / F.M.DB, guest_backup)
        shutil.copy2(self.shadow / M.DB, shadow_backup)
        self.fixture.commit()
        self.advance()
        self.assertEqual(self.observe()["relation"], M.MATCH)
        shutil.copyfile(guest_backup, self.fixture.work / F.M.DB)
        shutil.copyfile(shadow_backup, self.shadow / M.DB)
        stale_pair = self.observe()
        self.assertEqual(stale_pair["relation"], M.MATCH)
        self.assertEqual(stale_pair["localObservedSequence"],
                         self.before["testSequence"])
        self.denied(stale_pair)
        print("C3E_TWO_SAME_HOST_DATABASES_ROLLED_BACK_TOGETHER // NO_TRUST")

    def test_21_denied_production_admission_even_if_two_heads_match(self):
        self.assertEqual(self.observe()["relation"], M.MATCH)
        with self.assertRaisesRegex(M.Refused, "NOT_AN_INDEPENDENT_TRUST"):
            M.protected_admission(self.observe())

    def test_22_root_mode_or_runner_mismatch_rejected(self):
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT": "self-hosted"}):
            with self.assertRaisesRegex(M.Refused, "HOSTED_ROOT"):
                M.compare_ci_only(self.shadow, local_snapshot=self.before)
        os.chmod(self.shadow, 0o755)
        try:
            with self.assertRaisesRegex(M.Refused, "UNSAFE_ROOT"):
                self.observe()
        finally:
            os.chmod(self.shadow, 0o700)

    def test_23_direct_shadow_fork_candidate_with_fake_positive_fields_rejected(self):
        forged = dict(self.before, canBeginSignIn=True)
        with self.assertRaisesRegex(M.Refused, "SNAPSHOT_REFUSED"):
            M.advance_ci_only(
                self.shadow,
                old_head=self.before["testHeadSha256"],
                old_sequence=self.before["testSequence"],
                new_local_snapshot=forged)

    def test_24_shadow_db_is_separate_inode_and_original_ledger_unchanged(self):
        guest = self.fixture.work / F.M.DB
        shadow = self.shadow / M.DB
        self.assertNotEqual(guest.resolve(), shadow.resolve())
        self.assertNotEqual(guest.stat().st_ino, shadow.stat().st_ino)
        self.assertEqual(self.local_snap(), self.before)
        self.denied(self.observe())


if __name__ == "__main__":
    unittest.main(verbosity=2)
