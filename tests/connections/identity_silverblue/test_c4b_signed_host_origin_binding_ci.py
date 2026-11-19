#!/usr/bin/env python3
"""Third-key signed C4b↔C3e-N fixture binding, never native host authority."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import secrets
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import c4b_signed_host_origin_binding_ci as B
import c4b_c3en_signed_origin_join_ci as J
import test_c4b_c3en_signed_origin_join_ci as F


def sha(data):
    return hashlib.sha256(data).hexdigest()


class C4bThirdKeyHostOriginBindingTests(unittest.TestCase):
    def setUp(self):
        self.inner = F.C4bC3eNSignedOriginJoinTests(
            "test_01_real_nonroot_signed_witness_and_original_c3en_compatible")
        self.inner.setUp()
        self.addCleanup(self.inner.doCleanups)
        self.inner.c4b.server()
        self.inputs = self.inner.args()
        state = self.inner.state
        self.expected_join = {
            "schema": J.SCHEMA,
            "status": J.STATUS,
            "threeDistinctProcessPinsComparedInCI": True,
            "signedCheckpointAndOriginalC3eFloorsMatchInCI": True,
            "controllerHostId": state["hostId"],
            "controllerTransitionSequence": state["transitionSequence"],
            "signedCheckpointSha256": sha(self.inner.c4b.fixture.raw),
            "signedCheckpointSignatureSha256":
                sha(self.inner.c4b.fixture.sig),
            "matchingFloorEpoch": state["minimumReleaseEpoch"],
            "matchingFloorSequence": state["minimumReleaseSequence"],
            **J.NEGATIVE,
        }
        self.host_nonce = secrets.token_bytes(32)
        self.host_signer = Ed25519PrivateKey.generate()
        self.host_pin = sha(self.host_signer.public_key().public_bytes_raw())
        self.raw = B.make_expected_statement_ci_only(
            join_inputs=self.inputs, join_result=self.expected_join,
            host_attestation_challenge=self.host_nonce)
        self.signature = self.host_signer.sign(B.DOMAIN + self.raw)

    def args(self, **overrides):
        params = {
            "join_inputs": self.inputs,
            "controller_ledger_root": self.inner.c4b.fixture.base.root,
            "signed_host_binding": self.raw,
            "host_binding_signature": self.signature,
            "independently_pinned_host_signer": self.host_signer.public_key(),
            "independently_pinned_host_signer_sha256": self.host_pin,
            "independently_issued_host_challenge": self.host_nonce,
        }
        params.update(overrides)
        return params

    def inspect(self, **overrides):
        return B.inspect_signed_host_binding_ci_only(**self.args(**overrides))

    def refuse(self, **overrides):
        with self.assertRaises(B.Refused):
            self.inspect(**overrides)

    def resign(self, update):
        record = json.loads(self.raw)
        record.update(update)
        raw = B._canonical(record)
        return {"signed_host_binding": raw, "host_binding_signature":
                self.host_signer.sign(B.DOMAIN + raw)}

    def test_01_fresh_third_root_signature_binds_exact_ci_snapshots(self):
        result = self.inspect()
        self.assertEqual(result["status"], B.STATUS)
        self.assertTrue(result[
            "signedHostEvidenceMatchesOriginalC3eAndC4bCIOnly"])
        self.assertEqual(result["verifiedC4bCheckpointSha256"],
                         sha(self.inner.c4b.fixture.raw))
        self.assertEqual(result["floorEpoch"],
                         self.inner.state["minimumReleaseEpoch"])
        self.assertTrue(all(v is False for v in B.NEGATIVE.values()))

    def test_02_default_signed_join_is_never_production_authority(self):
        result = self.inspect()
        for key in B.NEGATIVE:
            self.assertIs(result[key], False, key)
        for key in ("grant", "credential", "authorization", "witnessInputs",
                    "canConnectProvider"):
            self.assertNotIn(key, result)
        self.assertNotIn("true", json.dumps(B.NEGATIVE))

    def test_03_wrong_host_signing_public_key_refuses(self):
        self.refuse(independently_pinned_host_signer=
                    Ed25519PrivateKey.generate().public_key())

    def test_04_wrong_host_signing_pin_refuses(self):
        self.refuse(independently_pinned_host_signer_sha256="f" * 64)

    def test_05_wrong_host_binding_signature_refuses(self):
        self.refuse(host_binding_signature=b"\x00" * 64)

    def test_06_new_host_nonce_refuses_old_signed_attestation(self):
        self.refuse(independently_issued_host_challenge=b"\xf0" * 32)

    def test_07_signed_checkpoint_challenge_change_cannot_replay(self):
        changed = {**self.inputs, "fresh_challenge": b"q" * 32}
        self.refuse(join_inputs=changed)

    def test_08_exact_signer_is_not_current_controller_root(self):
        root = self.inner.c4b.fixture.base.rot.previous_root
        self.refuse(independently_pinned_host_signer=root.public_key(),
                    independently_pinned_host_signer_sha256=sha(
                        root.public_key().public_bytes_raw()),
                    host_binding_signature=root.sign(B.DOMAIN + self.raw))

    def test_09_exact_signer_is_not_current_checkpoint_witness(self):
        root = self.inner.c4b.fixture.witness
        self.refuse(independently_pinned_host_signer=root.public_key(),
                    independently_pinned_host_signer_sha256=sha(
                        root.public_key().public_bytes_raw()),
                    host_binding_signature=root.sign(B.DOMAIN + self.raw))

    def test_10_re_signed_snapshot_claims_new_installed_pid_refuses(self):
        self.refuse(**self.resign({"installedStatusPid": 99991}))

    def test_11_re_signed_snapshot_claims_new_protected_pid_refuses(self):
        self.refuse(**self.resign({"protectedWitnessPid": 99992}))

    def test_12_re_signed_snapshot_claims_new_checkpoint_pid_refuses(self):
        self.refuse(**self.resign({"checkpointPeerPid": 99993}))

    def test_13_re_signed_origin_snapshot_hash_substitution_refuses(self):
        self.refuse(**self.resign({"installedOriginEvidenceSha256": "a" * 64}))

    def test_14_re_signed_canonical_opt_snapshot_hash_refuses(self):
        self.refuse(**self.resign({"canonicalOptProofSha256": "a" * 64}))

    def test_15_re_signed_c3e_witness_snapshot_hash_refuses(self):
        self.refuse(**self.resign({"readOnlyC3eWitnessSha256": "a" * 64}))

    def test_16_re_signed_c4b_checkpoint_signature_hash_refuses(self):
        self.refuse(**self.resign({
            "signedCheckpointSignatureSha256": "e" * 64}))

    def test_17_re_signed_witness_key_and_enrollment_hashes_refuse(self):
        self.refuse(**self.resign({"checkpointSignerSha256": "a" * 64}))

    def test_18_re_signed_floor_claim_refuses(self):
        self.refuse(**self.resign({"releaseSequence": 999}))

    def test_19_re_signed_host_id_claim_refuses(self):
        self.refuse(**self.resign({"controllerHostId": "forged-host"}))

    def test_20_extra_authorization_field_refuses_even_if_signed(self):
        self.refuse(**self.resign({"productionAuthority": True}))

    def test_21_duplicate_signed_json_field_refuses(self):
        bad = self.raw.replace(b'"schema":', b'"schema":"fake","schema":', 1)
        self.refuse(signed_host_binding=bad)

    def test_22_noncanonical_signed_bytes_refuse(self):
        bad = json.dumps(json.loads(self.raw), indent=2).encode("ascii")
        self.refuse(signed_host_binding=bad)

    def test_23_oversized_signed_record_refuses(self):
        self.refuse(signed_host_binding=b"x" * (B.MAX_RECORD_BYTES + 1))

    def test_24_wrong_source_c3e_origin_refuses_even_when_signature_valid(self):
        changed = {**self.inputs,
                   "installed_os_evidence": deepcopy(self.inputs["installed_os_evidence"])}
        changed["installed_os_evidence"]["kernel_enforcing"] = "0"
        self.refuse(join_inputs=changed)

    def test_25_changed_protected_c3e_floor_refuses_even_when_signed_old(self):
        changed = {**self.inputs,
                   "read_only_witness_status": dict(self.inputs["read_only_witness_status"])}
        changed["read_only_witness_status"]["observed_release_sequence"] += 1
        self.refuse(join_inputs=changed)

    def test_26_missing_original_protected_owner_source_is_a_hard_error(self):
        original = J.C3EN_PATH
        self.assertTrue(original.is_file())
        self.assertIn("C3eNOriginWitnessHandoff.py", Path(J.__file__).read_text())

    def test_27_real_socket_peer_pid_substitution_refuses(self):
        changed = dict(self.inputs)
        changed["separately_pinned_peer_pid"] += 1
        self.refuse(join_inputs=changed)

    def test_28_committed_controller_root_advance_refuses_stale_binding(self):
        self.inner.c4b.fixture.base.stage()
        self.inner.c4b.fixture.commit()
        self.refuse()

    def test_29_canonical_record_has_only_exact_diagnostic_fields(self):
        data = json.loads(self.raw)
        self.assertEqual(data["schema"], B.SCHEMA)
        self.assertEqual(data["audience"], B.AUDIENCE)
        self.assertEqual(data["scope"], B.SCOPE)
        self.assertEqual(data["hostAttestationChallengeSha256"],
                         sha(self.host_nonce))
        self.assertEqual(data["checkpointChallengeSha256"],
                         sha(self.inner.c4b.fixture.challenge))
        self.assertEqual(data["checkpointSignerSha256"],
                         self.inputs["separately_pinned_witness_sha256"])

    def test_30_source_never_imports_private_key_generation_or_native_grants(self):
        src = Path(B.__file__).read_text()
        for forbidden in ("Ed25519PrivateKey", "systemctl start",
                          "rpm-ostree install", '"hostAuthenticated": True',
                          '"productionAuthority": True'):
            self.assertNotIn(forbidden, src)
        self.assertTrue(all(v is False for v in B.NEGATIVE.values()))

    def test_31_controller_rotation_during_external_verification_refuses(self):
        original = B.J.inspect_ci_only

        def advance_after_signed_socket(**kwargs):
            result = original(**kwargs)
            self.inner.c4b.fixture.base.stage()
            self.inner.c4b.fixture.base.commit()
            return result

        with mock.patch.object(B.J, "inspect_ci_only",
                               side_effect=advance_after_signed_socket):
            with self.assertRaisesRegex(
                    B.Refused,
                    "C4B_C3EN_HOST_BINDING_LEDGER_CHANGED_DURING_VERIFICATION"):
                self.inspect()
        self.assertEqual(self.inner.c4b.fixture.base.current()[
            "transitionSequence"], 5)

    def test_32_controller_ledger_disappears_during_verification_refuses(self):
        original = B.J.inspect_ci_only

        def drop_after_signed_socket(**kwargs):
            result = original(**kwargs)
            (self.inner.c4b.fixture.base.root / B.L.DB_FILE).unlink()
            return result

        with mock.patch.object(B.J, "inspect_ci_only",
                               side_effect=drop_after_signed_socket):
            with self.assertRaisesRegex(
                    B.Refused,
                    "C4B_C3EN_HOST_BINDING_LEDGER_LOST_DURING_VERIFICATION"):
                self.inspect()

    def test_33_same_host_and_checkpoint_nonce_refuses_signed_result(self):
        # The two request domains are separate. A caller must not recycle
        # the same challenge across the signed host evidence and C4b proof.
        self.refuse(independently_issued_host_challenge=
                    self.inputs["fresh_challenge"])

    def test_34_builder_refuses_host_nonce_reuse_before_signing(self):
        with self.assertRaisesRegex(
                B.Refused,
                "C4B_C3EN_HOST_BINDING_DISTINCT_HOST_AND_CHECKPOINT_NONCES_REQUIRED"):
            B.make_expected_statement_ci_only(
                join_inputs=self.inputs, join_result=self.expected_join,
                host_attestation_challenge=self.inputs["fresh_challenge"])

    def test_35_invalid_controller_root_path_type_refuses(self):
        self.refuse(controller_ledger_root=str(
            self.inner.c4b.fixture.base.root))

    def test_36_incomplete_controller_state_refuses(self):
        malformed = dict(self.inputs["controller_state"])
        malformed.pop("minimumReleaseSequence")
        self.refuse(join_inputs={**self.inputs, "controller_state": malformed})

    def test_37_existing_staged_rotation_makes_host_binding_refuse(self):
        self.inner.c4b.fixture.base.stage()
        self.assertIs(self.inner.c4b.fixture.base.current()[
            "pendingIntentExists"], True)
        with self.assertRaisesRegex(
                B.Refused,
                "C4B_C3EN_HOST_BINDING_PENDING_ROTATION_NOT_QUIESCENT"):
            self.inspect()

    def test_38_rotation_staged_during_host_witness_exchange_refuses(self):
        original = B.J.inspect_ci_only

        def stage_during_exchange(**kwargs):
            result = original(**kwargs)
            self.inner.c4b.fixture.base.stage()
            return result

        with mock.patch.object(B.J, "inspect_ci_only",
                               side_effect=stage_during_exchange):
            with self.assertRaisesRegex(
                    B.Refused,
                    "C4B_C3EN_HOST_BINDING_ROTATION_STAGED_DURING_VERIFICATION"):
                self.inspect()
        self.assertIs(self.inner.c4b.fixture.base.current()[
            "pendingIntentExists"], True)
        self.assertEqual(self.inner.c4b.fixture.base.current()[
            "transitionSequence"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
