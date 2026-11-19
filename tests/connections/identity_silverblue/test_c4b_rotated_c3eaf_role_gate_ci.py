#!/usr/bin/env python3
"""C4b P1 old/new enrollment roots -> C3e-AF signed role continuity tests."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c4b_rotated_c3eaf_role_gate_ci as G
import test_c4b_signed_trust_transition_ci as R
import c4b_c3eaf_enrollment_alignment_ci as C


def pubhex(key):
    return key.public_key().public_bytes_raw().hex()


class RotatedC3eRoleTests(unittest.TestCase):
    def setUp(self):
        self.rot = R.SignedControllerTransitionTests(
            "test_01_dual_signed_rotation_keeps_real_denial_no_authority")
        self.rot.setUp()
        self.addCleanup(self.rot.doCleanups)
        self.c3e_root = Ed25519PrivateKey.generate()
        self.release_root = Ed25519PrivateKey.generate()
        self.witness = Ed25519PrivateKey.generate()
        X = C.A.Z.Y.X
        self.snapshot = {
            "rpmSha256": "a" * 64,
            "entrypointSha256": "b" * 64,
            "exeSha256": "c" * 64,
            "exePath": X.EXECUTABLE,
            "unit": X.UNIT,
            "pid": 2048,
            "startTicks": 987654,
            "uid": 992,
            "gid": 995,
            "cgroup": X.CGROUP,
            "selinux": X.SELINUX,
            "socketPath": X.SOCKET,
        }
        self.role = {
            "schema": C.A.SCHEMA,
            "role": C.A.Z.I.ROLE,
            "purpose": C.A.PURPOSE,
            "hostId": self.rot.fixture.host,
            "releaseEpoch": 3,
            "releaseSequence": 5,
            "releaseRootPublicHex": pubhex(self.release_root),
            "hostWitnessPublicHex": pubhex(self.witness),
            "receiptPublicHex": pubhex(self.rot.fixture.gateway),
            "runtimeSnapshotSha256": hashlib.sha256(
                X._canonical(self.snapshot)).hexdigest(),
        }
        self.sign()

    def sign(self):
        self.encoded = C.A._canonical(self.role)
        self.signature = self.c3e_root.sign(C.A.DOMAIN + self.encoded)

    def params(self, **overrides):
        result = {
            "rotation_inputs": self.rot.params(),
            "c3e_signed_role_enrollment": self.encoded,
            "c3e_role_signature": self.signature,
            "separately_pinned_c3e_enrollment_root": self.c3e_root.public_key(),
            "independently_supplied_runtime_snapshot": self.snapshot,
        }
        result.update(overrides)
        return result

    def check(self, **overrides):
        return G.inspect_rotated_roles_ci_only(**self.params(**overrides))

    def refuse(self, **overrides):
        with self.assertRaises(G.Refused):
            self.check(**overrides)

    def test_01_old_new_and_c3e_distinct_roots_aligned_no_grant(self):
        out = self.check()
        self.assertIs(out["rotatedControllerAndC3eSignedRoleAgreeInCI"], True)
        self.assertIs(out["retiredAndNewControllerRootsRemainSeparateFromC3eRolesInCI"], True)
        self.assertIs(out["freshControllerDenialStillMatchesProtectedRoleEnrollmentInCI"], True)
        self.assertEqual(out["hostId"], self.rot.fixture.host)
        self.assertEqual((out["releaseEpoch"], out["releaseSequence"]), (3, 5))
        for flag in (*G.NEGATIVE, *G.T.NEGATIVE, *G.C.NEGATIVE, *G.C.A.NEGATIVE):
            self.assertIs(out[flag], False, flag)

    def test_02_c3e_root_cannot_alias_retired_c4b_root(self):
        self.c3e_root = self.rot.previous_root
        self.sign()
        self.refuse()

    def test_03_c3e_root_cannot_alias_new_c4b_root(self):
        self.c3e_root = self.rot.proposed_root
        self.sign()
        self.refuse()

    def test_04_c3e_release_signer_cannot_alias_retired_c4b_root(self):
        self.role["releaseRootPublicHex"] = pubhex(self.rot.previous_root)
        self.sign()
        self.refuse()

    def test_05_c3e_witness_cannot_alias_retired_c4b_root(self):
        self.role["hostWitnessPublicHex"] = pubhex(self.rot.previous_root)
        self.sign()
        self.refuse()

    def test_06_c3e_signed_receipt_key_must_match_rotated_controller(self):
        self.role["receiptPublicHex"] = pubhex(Ed25519PrivateKey.generate())
        self.sign()
        self.refuse()

    def test_07_c3e_role_stale_after_rotated_release_advance(self):
        self.rot.next_policy["minimumReleaseSequence"] += 1
        self.rot.next_enrollment["releaseSequence"] += 1
        self.rot.render()
        self.refuse()

    def test_08_c3e_updated_role_accepts_monotonic_release_advance(self):
        self.rot.next_policy["minimumReleaseSequence"] += 1
        self.rot.next_enrollment["releaseSequence"] += 1
        self.rot.render()
        self.role["releaseSequence"] += 1
        self.sign()
        self.assertEqual(self.check()["releaseSequence"], 6)

    def test_09_missing_old_transition_signature_refuses(self):
        kw = self.rot.params(previous_signature=b"\x00" * 64)
        self.refuse(rotation_inputs=kw)

    def test_10_replayed_transition_counter_refuses(self):
        kw = self.rot.params(independently_pinned_transition_sequence=self.rot.sequence + 1)
        self.refuse(rotation_inputs=kw)

    def test_11_retired_revocation_cannot_be_erased(self):
        self.rot.previous_policy["revokedEnrollmentIds"] = ["a" * 32]
        self.rot.render()
        self.refuse()

    def test_12_successor_certificate_must_remain_signed_by_next_root(self):
        self.rot.write_next("signature", b"\x00" * 64)
        self.refuse()

    def test_13_wrong_c3e_enrollment_signature_refuses(self):
        self.refuse(c3e_role_signature=b"\x00" * 64)

    def test_14_runtime_pid_snapshot_swap_refuses(self):
        changed = dict(self.snapshot)
        changed["pid"] += 1
        self.refuse(independently_supplied_runtime_snapshot=changed)

    def test_15_fake_guest_signer_must_not_authorize_c3e(self):
        kw = self.rot.params(serial=b"C4B_ID_CHALLENGE_PROOF // impostor\n")
        self.refuse(rotation_inputs=kw)

    def test_16_partial_rotation_input_refuses(self):
        self.refuse(rotation_inputs={"transition": self.rot.encoded})
        self.refuse(rotation_inputs=None)

    def test_17_wrong_controller_policy_between_two_checks_refuses(self):
        # A different signed new policy is still the wrong transition target.
        kw = self.rot.params()
        kw["next_policy"] = b"{}"
        self.refuse(rotation_inputs=kw)

    def test_18_host_or_scope_changed_in_c3e_role_refuses(self):
        self.role["hostId"] = "postapollo-identity-ci@other-host"
        self.sign()
        self.refuse()

    def test_19_c3e_role_must_not_grant_production_scope(self):
        self.role["purpose"] = "production-login"
        self.sign()
        self.refuse()

    def test_20_no_real_root_store_or_authority_transferred(self):
        source = Path(G.__file__).read_text()
        for token in ("systemctl start", "rpm-ostree install",
                      "Ed25519PrivateKey.generate(", '"hostAuthenticated": True',
                      '"productionAuthority": True'):
            self.assertNotIn(token, source)
        self.assertTrue(all(value is False for value in G.NEGATIVE.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
