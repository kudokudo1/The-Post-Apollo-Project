#!/usr/bin/env python3
"""C4b Package 1: signed root rotation, revocation and replay-refusal tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_controller_owned_policy_intake_ci as F
import c4b_signed_trust_transition_ci as T
import controller_owned_policy_intake_ci as P
import controller_pinned_enrollment_gate_ci as E


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SignedControllerTransitionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = F.ControllerOwnedPolicyIntakeTests(
            "test_01_exact_fixture_signed_gateway_nonce_and_pins_no_grant")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.previous_root = self.fixture.root
        self.proposed_root = Ed25519PrivateKey.generate()
        self.previous_policy = dict(self.fixture.policy)
        self.next_policy = dict(self.fixture.policy)
        self.next_policy["rootPublicSha256"] = sha(
            self.proposed_root.public_key().public_bytes_raw())
        self.next_policy["revokedEnrollmentIds"] = ["b" * 32]
        self.next_enrollment = dict(self.fixture.enrollment)
        self.next_dir = self.fixture.directory / "next-controller"
        self.next_dir.mkdir(mode=0o700)
        self.chain_head = "d" * 64
        self.sequence = 4
        self.identifier = "c" * 32
        self.render()

    def write_next(self, key, raw):
        path = self.next_dir / P.FILES[key][0]
        path.write_bytes(raw)
        path.chmod(0o600)

    def render(self):
        self.previous_raw = json.dumps(
            self.previous_policy, sort_keys=True, separators=(",", ":"),
        ).encode("ascii")
        self.next_raw = json.dumps(
            self.next_policy, sort_keys=True, separators=(",", ":"),
        ).encode("ascii")
        self.write_next("root",
                        self.proposed_root.public_key().public_bytes_raw())
        self.write_next("policy", self.next_raw)
        signed_enrollment = E.canonical(self.next_enrollment)
        self.write_next("enrollment", signed_enrollment)
        self.write_next("signature",
                        self.proposed_root.sign(E.DOMAIN + signed_enrollment))
        self.event = {
            "schema": T.SCHEMA,
            "audience": T.AUDIENCE,
            "action": T.ACTION,
            "transitionId": self.identifier,
            "transitionSequence": self.sequence + 1,
            "previousTransitionSha256": self.chain_head,
            "hostId": self.previous_policy["hostId"],
            "previousPolicySha256": sha(self.previous_raw),
            "nextPolicySha256": sha(self.next_raw),
            "previousRootSha256": sha(
                self.previous_root.public_key().public_bytes_raw()),
            "nextRootSha256": sha(
                self.proposed_root.public_key().public_bytes_raw()),
            "previousFloorEpoch": self.previous_policy["minimumReleaseEpoch"],
            "previousFloorSequence": self.previous_policy["minimumReleaseSequence"],
            "nextFloorEpoch": self.next_policy["minimumReleaseEpoch"],
            "nextFloorSequence": self.next_policy["minimumReleaseSequence"],
        }
        self.resign()

    def resign(self):
        self.encoded = T.canonical(self.event)
        self.old_sig = self.previous_root.sign(T.DOMAIN + self.encoded)
        self.new_sig = self.proposed_root.sign(T.DOMAIN + self.encoded)

    def params(self, **overrides):
        kw = {
            "previous_policy": self.previous_raw,
            "next_policy": self.next_raw,
            "transition": self.encoded,
            "previous_root": self.previous_root.public_key(),
            "proposed_root": self.proposed_root.public_key(),
            "previous_signature": self.old_sig,
            "proposed_signature": self.new_sig,
            "independently_pinned_previous_policy_sha256": sha(self.previous_raw),
            "independently_pinned_previous_transition_sha256": self.chain_head,
            "independently_pinned_transition_sequence": self.sequence,
            "independently_expected_transition_id": self.identifier,
            "next_controller_dir": self.next_dir,
            "serial": self.fixture.serial,
            "controller_challenge": self.fixture.nonce,
        }
        kw.update(overrides)
        return kw

    def check(self, **overrides):
        return T.inspect_rotation_ci_only(**self.params(**overrides))

    def refuse(self, **overrides):
        with self.assertRaises(T.Refused):
            self.check(**overrides)

    def test_01_dual_signed_rotation_keeps_real_denial_no_authority(self):
        result = self.check()
        self.assertIs(result["dualSignedControllerRootTransitionCheckedInCI"], True)
        self.assertIs(result["successorEnrollmentStillSignsRealChallengeDenialInCI"], True)
        self.assertIs(result["monotonicTransitionAndRevocationContinuityCheckedInCI"], True)
        self.assertEqual(result["transitionSequence"], self.sequence + 1)
        self.assertEqual(result["nextControllerRootSha256"],
                         self.next_policy["rootPublicSha256"])
        self.assertTrue(all(v is False for v in {
            **T.NEGATIVE, **P.NEGATIVE, **E.NEGATIVE}.values()))

    def test_02_replayed_transition_after_sequence_advance_refuses(self):
        self.refuse(independently_pinned_transition_sequence=self.sequence + 1)

    def test_03_gapped_transition_chain_refuses(self):
        self.refuse(independently_pinned_transition_sequence=self.sequence - 2)

    def test_04_wrong_previous_chain_head_refuses(self):
        self.refuse(independently_pinned_previous_transition_sha256="0" * 64)

    def test_05_wrong_transition_id_refuses(self):
        self.refuse(independently_expected_transition_id="a" * 32)

    def test_06_unpinned_previous_policy_hash_refuses(self):
        self.refuse(independently_pinned_previous_policy_sha256="0" * 64)

    def test_07_wrong_old_root_refuses_even_if_new_root_signed(self):
        impostor = Ed25519PrivateKey.generate().public_key()
        self.refuse(previous_root=impostor)

    def test_08_wrong_proposed_root_refuses_even_if_old_root_signed(self):
        impostor = Ed25519PrivateKey.generate().public_key()
        self.refuse(proposed_root=impostor)

    def test_09_previous_root_signature_tamper_refuses(self):
        self.refuse(previous_signature=b"\x00" * 64)

    def test_10_proposed_root_signature_tamper_refuses(self):
        self.refuse(proposed_signature=b"\x00" * 64)

    def test_11_same_root_reuse_refuses(self):
        self.refuse(proposed_root=self.previous_root.public_key())

    def test_12_signed_production_action_scope_refuses(self):
        self.event["action"] = "ENABLE_CREDENTIALS"
        self.resign()
        self.refuse()

    def test_13_duplicate_json_field_refuses(self):
        raw = self.encoded.replace(b'"schema":',
                                   b'"schema":"forged","schema":', 1)
        self.refuse(transition=raw)

    def test_14_noncanonical_signed_json_refuses(self):
        self.refuse(transition=json.dumps(self.event, indent=2).encode())

    def test_15_changed_host_during_root_rotation_refuses(self):
        self.next_policy["hostId"] = "postapollo-identity-ci@other-host"
        self.render()
        self.refuse()

    def test_16_release_floor_downgrade_refuses(self):
        self.next_policy["minimumReleaseSequence"] -= 1
        self.render()
        self.refuse()

    def test_17_signed_release_change_without_floor_advance_refuses(self):
        self.next_policy["releaseSha256"] = "f" * 64
        self.render()
        self.refuse()

    def test_18_revocation_erase_refuses_even_with_both_signatures(self):
        self.previous_policy["revokedEnrollmentIds"] = ["a" * 32]
        self.render()
        self.refuse()

    def test_19_valid_monotonic_floor_advance_and_retained_revocations(self):
        self.next_policy["minimumReleaseSequence"] += 1
        self.next_enrollment["releaseSequence"] += 1
        self.render()
        out = self.check()
        self.assertEqual(out["releaseSequence"], 6)

    def test_20_next_controller_certificate_signed_by_old_root_refuses(self):
        enrollment = E.canonical(self.next_enrollment)
        self.write_next("signature",
                        self.previous_root.sign(E.DOMAIN + enrollment))
        self.refuse()

    def test_21_next_policy_file_swapped_after_dual_signature_refuses(self):
        self.write_next("policy", b"{}")
        self.refuse()

    def test_22_missing_next_bundle_refuses(self):
        (self.next_dir / P.FILES["root"][0]).unlink()
        self.refuse()

    def test_23_forged_guest_key_for_correct_nonce_refuses(self):
        impostor = Ed25519PrivateKey.generate()
        denial = F._canonical({
            "schema": F.LEGACY_RECEIPT_SCHEMA,
            "state": "UNAVAILABLE", "requestId": None,
        }) + b"\n"
        proof = F.ReceiptIssuer(impostor).seal(
            "BEGIN", None, self.fixture.nonce, denial)
        serial = self.fixture.proof(
            impostor.public_key().public_bytes_raw(), proof)
        self.refuse(serial=serial)

    def test_24_replayed_guest_nonce_refuses(self):
        self.refuse(controller_challenge=F.V.generate_controller_challenge())

    def test_25_changed_policy_and_event_without_external_cursor_refuses(self):
        former_digest = sha(self.previous_raw)
        self.previous_policy["releaseSha256"] = "a" * 64
        self.render()
        self.refuse(
            independently_pinned_previous_policy_sha256=former_digest)

    def test_26_rejected_bad_types_and_boolean_sequence(self):
        self.refuse(previous_signature="not bytes")
        self.refuse(independently_pinned_transition_sequence=True)
        self.refuse(independently_expected_transition_id=None)

    def test_27_same_user_controlled_files_do_not_create_external_authority(self):
        source = Path(T.__file__).read_text()
        for forbidden in (
            "Ed25519PrivateKey.generate(",
            "systemctl start", "rpm-ostree install",
            '"hostAuthenticated": True', '"productionAuthority": True',
            "credentialActionsEnabled: true",
        ):
            self.assertNotIn(forbidden, source)
        for flag in ("protectedTransitionHistoryVerified",
                     "operatorControlledRootCustodyVerified",
                     "independentHostKernelAndSeatWitnessVerified"):
            self.assertIs(T.NEGATIVE[flag], False)
        # A read-only CI verifier has no authoritative consume operation.
        self.assertFalse(hasattr(T, "commit_transition"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
