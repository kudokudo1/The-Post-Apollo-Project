#!/usr/bin/env python3
"""C4b Package 1: disposable root-owned real Linux trust-store boundary."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c4b_root_owned_controller_ledger_ci as L
import test_c4b_signed_trust_transition_ci as R


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class C4bRootOwnedControllerLedgerTests(unittest.TestCase):
    def setUp(self):
        self.rot = R.SignedControllerTransitionTests(
            "test_01_dual_signed_rotation_keeps_real_denial_no_authority")
        self.rot.setUp()
        self.addCleanup(self.rot.doCleanups)
        self.root = Path(tempfile.mkdtemp(prefix=L.DIR_PREFIX, dir="/run"))
        self.root.chmod(0o700)
        self.addCleanup(lambda: shutil.rmtree(self.root))
        self._bootstrap()

    def _bootstrap(self):
        L.initialize_for_disposable_ci(
            self.root,
            initial_controller_policy=self.rot.previous_raw,
            initial_controller_root_public=
                self.rot.previous_root.public_key().public_bytes_raw(),
            initial_transition_sha256=self.rot.chain_head,
            initial_transition_sequence=self.rot.sequence,
        )

    def stage(self, **changes):
        opts = {
            "transition_id": self.rot.identifier,
            "next_root_sha256": self.rot.event["nextRootSha256"],
            "next_policy_sha256": self.rot.event["nextPolicySha256"],
        }
        opts.update(changes)
        return L.stage_rotation_intent_for_disposable_ci(self.root, **opts)

    def args(self, **changes):
        opts = {
            "next_policy": self.rot.next_raw,
            "next_root_public": self.rot.proposed_root.public_key().public_bytes_raw(),
            "transition": self.rot.encoded,
            "previous_signature": self.rot.old_sig,
            "proposed_signature": self.rot.new_sig,
            "next_controller_dir": self.rot.next_dir,
            "serial": self.rot.fixture.serial,
            "controller_challenge": self.rot.fixture.nonce,
        }
        opts.update(changes)
        return opts

    def commit(self, **changes):
        return L.verify_and_commit_rotation_ci_only(
            self.root, **self.args(**changes))

    def refuse(self, **changes):
        with self.assertRaises(L.Refused):
            self.commit(**changes)

    def current(self):
        return L.inspect_current_ci_only(self.root)

    def test_01_root_only_staged_dual_signature_consumes_once(self):
        baseline = self.current()
        self.assertEqual(baseline["transitionSequence"], 4)
        self.assertFalse(baseline["pendingIntentExists"])
        self.stage()
        self.assertTrue(self.current()["pendingIntentExists"])
        result = self.commit()
        self.assertTrue(result["rootOwnedDisposableControllerRotationCommittedInCi"])
        self.assertTrue(result["singlePrivilegedTestIntentConsumedInCi"])
        updated = self.current()
        self.assertEqual(updated["transitionSequence"], 5)
        self.assertEqual(updated["controllerRootSha256"],
                         sha(self.rot.proposed_root.public_key().public_bytes_raw()))
        self.assertFalse(updated["pendingIntentExists"])
        self.assertTrue(all(value is False for value in {
            **L.NEGATIVE, **L.T.NEGATIVE, **L.P.NEGATIVE,
            **L.E.NEGATIVE}.values()))

    def test_02_once_committed_same_transition_replay_refuses(self):
        self.stage()
        self.commit()
        before = self.current()
        self.refuse()
        self.assertEqual(self.current(), before)

    def test_03_unprivileged_linux_uid_cannot_read_root_owned_ledger(self):
        runuser = shutil.which("runuser")
        self.assertIsNotNone(runuser, "Linux runuser required for real UID witness")
        path = self.root / L.DB_FILE
        denied = subprocess.run(
            [runuser, "-u", "nobody", "--", "/usr/bin/test", "-r", str(path)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False)
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(self.root.stat().st_uid, 0)
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)
        self.assertEqual(path.stat().st_uid, 0)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_04_nonroot_supervisor_refuses_even_with_fake_env_flag(self):
        with mock.patch.object(L.os, "geteuid", return_value=1000):
            with self.assertRaises(L.Refused):
                self.current()
            with self.assertRaises(L.Refused):
                self.stage()

    def test_05_missing_database_is_not_silently_created(self):
        (self.root / L.DB_FILE).unlink()
        with self.assertRaises(L.Refused):
            self.current()
        self.assertFalse((self.root / L.DB_FILE).exists())

    def test_06_existing_ledger_refuses_second_bootstrap(self):
        with self.assertRaises(L.Refused):
            self._bootstrap()

    def test_07_path_outside_exact_run_scope_refuses(self):
        with self.assertRaises(L.Refused):
            L.inspect_current_ci_only(self.rot.fixture.directory)

    def test_08_symlinked_root_path_refuses(self):
        alias = self.root.with_name(L.DIR_PREFIX + "alias-" + self.root.name[-10:])
        alias.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(alias.unlink)
        with self.assertRaises(L.Refused):
            L.inspect_current_ci_only(alias)

    def test_09_world_readable_state_file_refuses(self):
        path = self.root / L.DB_FILE
        path.chmod(0o644)
        self.addCleanup(path.chmod, 0o600)
        with self.assertRaises(L.Refused):
            self.current()

    def test_10_hardlinked_database_refuses(self):
        extra = self.root / "same-database"
        os.link(self.root / L.DB_FILE, extra)
        self.addCleanup(extra.unlink)
        with self.assertRaises(L.Refused):
            self.current()

    def test_11_wrong_staged_transition_id_refuses_without_consuming(self):
        self.stage(transition_id="a" * 32)
        self.refuse()
        self.assertTrue(self.current()["pendingIntentExists"])

    def test_12_wrong_staged_next_root_refuses_without_consuming(self):
        self.stage(next_root_sha256="f" * 64)
        self.refuse()
        self.assertTrue(self.current()["pendingIntentExists"])

    def test_13_wrong_staged_next_policy_refuses_without_consuming(self):
        self.stage(next_policy_sha256="0" * 64)
        self.refuse()
        self.assertTrue(self.current()["pendingIntentExists"])

    def test_14_no_staged_root_authority_refuses(self):
        self.refuse()
        self.assertFalse(self.current()["pendingIntentExists"])

    def test_15_duplicate_pending_intent_does_not_override_first(self):
        self.stage()
        with self.assertRaises(L.Refused):
            self.stage(transition_id="a" * 32)
        self.assertTrue(self.current()["pendingIntentExists"])
        self.commit()

    def test_16_invalid_old_signature_refuses_without_cursor_move(self):
        self.stage()
        self.refuse(previous_signature=b"\x00" * 64)
        self.assertEqual(self.current()["transitionSequence"], self.rot.sequence)
        self.assertTrue(self.current()["pendingIntentExists"])
        self.commit()

    def test_17_invalid_new_signature_refuses_without_cursor_move(self):
        self.stage()
        self.refuse(proposed_signature=b"\x00" * 64)
        self.assertEqual(self.current()["transitionSequence"], self.rot.sequence)
        self.commit()

    def test_18_stale_signed_transition_number_refuses(self):
        self.rot.event["transitionSequence"] -= 1
        self.rot.resign()
        self.stage()
        self.refuse()
        self.assertEqual(self.current()["transitionSequence"], self.rot.sequence)

    def test_19_controller_host_swap_refuses_without_commit(self):
        self.rot.next_policy["hostId"] = "postapollo-identity-ci@wrong-machine"
        self.rot.render()
        self.stage()
        self.refuse()
        self.assertTrue(self.current()["pendingIntentExists"])

    def test_20_rotated_release_floor_downgrade_refuses_without_commit(self):
        self.rot.next_policy["minimumReleaseSequence"] -= 1
        self.rot.render()
        self.stage()
        self.refuse()
        self.assertEqual(self.current()["transitionSequence"], 4)

    def test_21_revocation_erasure_refuses_even_with_both_root_signatures(self):
        # Re-bootstrap a SECOND isolated ledger *after* selecting the prior
        # revoked policy. This tests actual monotonic revocation continuity,
        # not just a mismatch with a previously bootstrapped controller.
        self.rot.previous_policy["revokedEnrollmentIds"] = ["a" * 32]
        self.rot.next_policy["revokedEnrollmentIds"] = []
        self.rot.render()
        revoked_root = Path(tempfile.mkdtemp(prefix=L.DIR_PREFIX, dir="/run"))
        revoked_root.chmod(0o700)
        self.addCleanup(lambda: shutil.rmtree(revoked_root))
        L.initialize_for_disposable_ci(
            revoked_root, initial_controller_policy=self.rot.previous_raw,
            initial_controller_root_public=
                self.rot.previous_root.public_key().public_bytes_raw(),
            initial_transition_sha256=self.rot.chain_head,
            initial_transition_sequence=self.rot.sequence,
        )
        L.stage_rotation_intent_for_disposable_ci(
            revoked_root, transition_id=self.rot.identifier,
            next_root_sha256=self.rot.event["nextRootSha256"],
            next_policy_sha256=self.rot.event["nextPolicySha256"],
        )
        with self.assertRaises(L.Refused):
            L.verify_and_commit_rotation_ci_only(revoked_root, **self.args())
        state = L.inspect_current_ci_only(revoked_root)
        self.assertEqual(state["transitionSequence"], 4)
        self.assertTrue(state["pendingIntentExists"])

    def test_27_monotonic_revocation_addition_commits_once(self):
        self.rot.next_policy["revokedEnrollmentIds"] = ["b" * 32, "c" * 32]
        self.rot.render()
        self.stage()
        self.commit()
        connection = L._connect(self.root)
        try:
            _, stored_policy, _ = L._read(connection)
        finally:
            connection.close()
        self.assertEqual(stored_policy["revokedEnrollmentIds"],
                         ["b" * 32, "c" * 32])
        self.refuse()

    def test_22_policy_bundle_changed_after_staging_refuses(self):
        self.stage()
        self.rot.write_next("policy", b"{}")
        self.refuse()
        self.assertEqual(self.current()["transitionSequence"], 4)

    def test_23_new_root_identity_mismatch_refuses(self):
        self.stage()
        self.refuse(next_root_public=
                    self.rot.previous_root.public_key().public_bytes_raw())
        self.assertTrue(self.current()["pendingIntentExists"])

    def test_24_same_root_must_not_be_trusted_after_checkout_restore(self):
        self.stage()
        self.commit()
        # A restored previous checkout carries old signed bytes, but the
        # root-owned cursor has already moved forward.
        with self.assertRaises(L.Refused):
            self.stage()
        self.assertEqual(self.current()["transitionSequence"], 5)

    def test_25_corrupted_db_state_refuses_without_resetting_state(self):
        path = self.root / L.DB_FILE
        with path.open("r+b") as stream:
            stream.seek(0)
            stream.write(b"INVALID-SQLITE")
            stream.flush()
            os.fsync(stream.fileno())
        with self.assertRaises(L.Refused):
            self.current()
        self.assertTrue(path.exists())

    def test_26_guard_disallows_production_or_local_host_use(self):
        source = Path(L.__file__).read_text()
        for forbidden in (
            "systemctl start", "rpm-ostree install", "Ed25519PrivateKey.generate(",
            '"hostAuthenticated": True', '"productionAuthority": True',
            "credentialActionsEnabled: true",
        ):
            self.assertNotIn(forbidden, source)
        self.assertFalse(any(L.NEGATIVE.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
