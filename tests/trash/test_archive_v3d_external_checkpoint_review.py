"""Trash++ V3d // offline signed two-root checkpoint contract tests.

All keys are ephemeral in test memory. No filesystem writes, network access,
OS users, live ArchiveStore credentials or production authority.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.trash import archive_v3d_external_checkpoint_review as v3d
from scripts.trash import archive_v3b_signed_rollback_witness as v3b
from scripts.trash.archive_v2_signed_capture import (
    ALLOWED_OWNERS, AUDIENCE, PURPOSE,
)


def _public(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class V3dIndependentCheckpointReviewTests(unittest.TestCase):
    def setUp(self):
        self.owner = sorted(ALLOWED_OWNERS)[0]
        self.grant = "a" * 64
        self.floor_key = Ed25519PrivateKey.generate()
        self.witness_key = Ed25519PrivateKey.generate()
        self.anchor_key = Ed25519PrivateKey.generate()
        self.witness_pin = {
            "rootKeyId": "v3d-test-witness-key",
            "publicKeyBytes": _public(self.witness_key),
            "origin": v3b.PIN_ORIGIN,
        }
        self.anchor_pin = {
            "anchorKeyId": "v3d-test-separate-anchor",
            "publicKeyBytes": _public(self.anchor_key),
            "origin": v3d.PIN_ORIGIN,
        }
        self.floor = {
            "state": "TEST_EXTERNAL_FLOOR_MATCHED_DENY_ONLY",
            "ownerId": self.owner,
            "epoch": 1,
            "sequence": 1,
            "externalFloorSha256": "b" * 64,
            "releaseSha256": "c" * 64,
            "signatureVerified": True,
            "offUidFileObserved": False,
            "externallyProtectedMonotonicAuthorityVerified": False,
            "trustedClockVerified": False,
            "sourceAuthorityVerified": False,
            "captureAllowed": False,
            "productionAllowed": False,
            "restoreAllowed": False,
            "burnAllowed": False,
        }
        self.witness_claim = {
            "schema": v3b.KIND,
            "audience": AUDIENCE,
            "purpose": PURPOSE,
            "policyOrigin": v3b.ORIGIN,
            "rootKeyId": self.witness_pin["rootKeyId"],
            "ownerId": self.owner,
            "grantSha256": self.grant,
            "epoch": 1,
            "floorSequence": 1,
            "floorSha256": "b" * 64,
            "releaseSha256": "c" * 64,
            "witnessSequence": 1,
            "previousWitnessSha256": "",
            "revoked": False,
        }
        self.witness = self.sign_witness(self.witness_claim)
        self.checkpoint_claim = {
            "schema": v3d.KIND,
            "audience": v3d.AUDIENCE,
            "policyOrigin": v3d.ORIGIN,
            "anchorKeyId": self.anchor_pin["anchorKeyId"],
            "ownerId": self.owner,
            "grantSha256": self.grant,
            "checkpointSequence": 1,
            "previousCheckpointSha256": "",
            "witnessSequence": 1,
            "witnessSha256": self.witness_sha(self.witness_claim),
            "epoch": 1,
            "floorSequence": 1,
            "floorSha256": "b" * 64,
            "releaseSha256": "c" * 64,
            "revoked": False,
        }
        self.old = self.sign_checkpoint(self.checkpoint_claim)

    def witness_sha(self, claim):
        return hashlib.sha256(v3b.canonical_claim(claim)).hexdigest()

    def checkpoint_sha(self, claim):
        return hashlib.sha256(v3d.canonical_checkpoint(claim)).hexdigest()

    def sign_witness(self, claim, key=None):
        key = self.witness_key if key is None else key
        return {
            "claim": copy.deepcopy(claim),
            "signatureB64": base64.b64encode(
                key.sign(v3b.canonical_claim(claim))).decode("ascii"),
        }

    def sign_checkpoint(self, claim, key=None):
        key = self.anchor_key if key is None else key
        return {
            "claim": copy.deepcopy(claim),
            "signatureB64": base64.b64encode(
                key.sign(v3d.canonical_checkpoint(claim))).decode("ascii"),
        }

    def evaluate(self, *, old=None, current=None, witness=None,
                 anchor_pin=None, witness_pin=None, floor=None,
                 owner=None, grant=None, floor_key=None):
        return v3d.review(
            self.old if old is None else old,
            self.old if current is None else current,
            self.witness if witness is None else witness,
            anchor_pin=self.anchor_pin if anchor_pin is None else anchor_pin,
            witness_pin=self.witness_pin if witness_pin is None else witness_pin,
            observed_floor=self.floor if floor is None else floor,
            floor_signer_public_key=_public(self.floor_key)
                if floor_key is None else floor_key,
            expected_owner_id=self.owner if owner is None else owner,
            expected_grant_sha256=self.grant if grant is None else grant,
        )

    def assert_hold(self, response):
        self.assertEqual(response["state"], "INDEPENDENT_AUTHORITY_HOLD")
        self.assertTrue(response["readOnly"])
        self.assertTrue(response["requiresIndependentReview"])
        self.assertTrue(response["checkpointSignatureValidOfflineOnly"])
        self.assertTrue(response["witnessSignatureValidFixtureOnly"])
        self.assertIn("independent_checkpoint_custody_unverified",
                      response["holdReasons"])
        self.assertIn("trusted_reference_highwater_unverified",
                      response["holdReasons"])
        for field in (
            "independentAuthorityAuthenticated",
            "externallyProtectedMonotonicAuthorityVerified",
            "trustedReferenceHighwaterVerified", "trustedClockVerified",
            "sourceOwnerAuthorityVerified", "c3eAuthenticatedSourceVerified",
            "c5HumanConsentVerified", "backupCustodyVerified",
            "captureAllowed", "productionAllowed", "restoreAllowed",
            "burnAllowed", "automaticRetryAllowed",
            "automaticRollbackAllowed", "deleteOriginalAllowed",
        ):
            self.assertIs(response[field], False, field)
        self.assertEqual(response["safeActions"], [])

    def advanced(self):
        next_witness = copy.deepcopy(self.witness_claim)
        next_witness["witnessSequence"] = 2
        next_witness["previousWitnessSha256"] = self.witness_sha(
            self.witness_claim)
        signed_witness = self.sign_witness(next_witness)
        next_checkpoint = copy.deepcopy(self.checkpoint_claim)
        next_checkpoint["checkpointSequence"] = 2
        next_checkpoint["previousCheckpointSha256"] = self.checkpoint_sha(
            self.checkpoint_claim)
        next_checkpoint["witnessSequence"] = 2
        next_checkpoint["witnessSha256"] = self.witness_sha(next_witness)
        return next_checkpoint, signed_witness

    def test_valid_two_signer_baseline_never_grants_production(self):
        result = self.evaluate()
        self.assert_hold(result)
        self.assertEqual(result["presentedCheckpointSequenceObserved"], 1)
        self.assertEqual(result["signedWitnessSequenceObserved"], 1)
        self.assertNotIn("signed_checkpoint_sequence_rollback",
                         result["holdReasons"])

    def test_forward_linked_checkpoint_and_witness_still_deny(self):
        checkpoint, signed_witness = self.advanced()
        result = self.evaluate(
            current=self.sign_checkpoint(checkpoint),
            witness=signed_witness)
        self.assert_hold(result)
        self.assertEqual(result["presentedCheckpointSequenceObserved"], 2)
        self.assertNotIn("signed_checkpoint_chain_diverged", result["holdReasons"])
        self.assertNotIn("current_witness_digest_mismatch", result["holdReasons"])

    def test_newer_independent_reference_exposes_signed_old_replay(self):
        checkpoint, signed_witness = self.advanced()
        result = self.evaluate(
            old=self.sign_checkpoint(checkpoint),
            current=self.old, witness=self.witness)
        self.assert_hold(result)
        self.assertIn("signed_checkpoint_sequence_rollback", result["holdReasons"])
        self.assertIn("anchored_witness_sequence_rollback", result["holdReasons"])

    def test_same_sequence_signed_checkpoint_fork_refused(self):
        changed = copy.deepcopy(self.checkpoint_claim)
        changed["revoked"] = True
        result = self.evaluate(current=self.sign_checkpoint(changed))
        self.assert_hold(result)
        self.assertIn("signed_checkpoint_same_sequence_fork", result["holdReasons"])
        self.assertIn("current_revocation_mismatch", result["holdReasons"])

    def test_wrong_predecessor_and_missing_sequence_are_visible(self):
        changed, signed_witness = self.advanced()
        changed["previousCheckpointSha256"] = "d" * 64
        response = self.evaluate(
            current=self.sign_checkpoint(changed), witness=signed_witness)
        self.assertIn("signed_checkpoint_chain_diverged", response["holdReasons"])
        changed["checkpointSequence"] = 3
        response = self.evaluate(
            current=self.sign_checkpoint(changed), witness=signed_witness)
        self.assertIn("signed_checkpoint_chain_gap", response["holdReasons"])

    def test_witness_digest_must_match_independently_signed_checkpoint(self):
        changed = copy.deepcopy(self.checkpoint_claim)
        changed["witnessSha256"] = "e" * 64
        response = self.evaluate(current=self.sign_checkpoint(changed))
        self.assertIn("current_witness_digest_mismatch", response["holdReasons"])
        self.assertIn("anchored_witness_same_sequence_fork",
                      response["holdReasons"])

    def test_wrong_anchor_signer_cannot_forge_checkpoint(self):
        rogue = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_SIGNATURE_REFUSED"):
            self.evaluate(current=self.sign_checkpoint(
                self.checkpoint_claim, rogue))

    def test_witness_forgery_fails_even_with_valid_anchor(self):
        rogue = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_SIGNED_WITNESS_REFUSED"):
            self.evaluate(witness=self.sign_witness(self.witness_claim, rogue))

    def test_same_key_as_witness_or_floor_is_not_an_independent_test_root(self):
        same = dict(self.anchor_pin,
                    publicKeyBytes=_public(self.witness_key))
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_INDEPENDENT_TEST_ROOT_REQUIRED"):
            self.evaluate(anchor_pin=same)
        same = dict(self.anchor_pin, publicKeyBytes=_public(self.floor_key))
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_INDEPENDENT_TEST_ROOT_REQUIRED"):
            self.evaluate(anchor_pin=same)

    def test_owner_or_grant_substitution_refused(self):
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_EXPECTED_POLICY_REFUSED"):
            self.evaluate(grant="wrong")
        other = sorted(ALLOWED_OWNERS)
        if len(other) > 1:
            with self.assertRaisesRegex(v3d.CheckpointRefused,
                                        "V3D_OWNER_GRANT_REFUSED"):
                self.evaluate(owner=other[-1])
        changed = copy.deepcopy(self.checkpoint_claim)
        changed["grantSha256"] = "d" * 64
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_OWNER_GRANT_REFUSED"):
            self.evaluate(current=self.sign_checkpoint(changed))

    def test_revocation_is_not_reversed(self):
        revoked = copy.deepcopy(self.checkpoint_claim)
        revoked["revoked"] = True
        result = self.evaluate(old=self.sign_checkpoint(revoked))
        self.assertIn("irreversible_revocation_reversed",
                      result["holdReasons"])

    def test_signed_release_rollback_and_floor_disagreement(self):
        newer = copy.deepcopy(self.checkpoint_claim)
        newer["epoch"] = 2
        response = self.evaluate(old=self.sign_checkpoint(newer))
        self.assertIn("signed_release_epoch_rollback", response["holdReasons"])
        changed_floor = dict(self.floor, epoch=2, sequence=2,
                             externalFloorSha256="d" * 64)
        response = self.evaluate(floor=changed_floor)
        self.assertIn("current_floor_epoch_mismatch", response["holdReasons"])
        self.assertIn("current_floor_sequence_mismatch", response["holdReasons"])
        self.assertIn("current_floor_digest_mismatch", response["holdReasons"])

    def test_valid_local_pair_swap_cannot_self_certify_custody(self):
        # Attacker who replaces both the old/current caller-supplied evidence
        # with an older signed pair can still get valid signatures. Never
        # mistake that for independent durable storage or high-water proof.
        earlier = self.evaluate(old=self.old, current=self.old)
        self.assert_hold(earlier)
        self.assertIs(earlier["trustedReferenceHighwaterVerified"], False)
        self.assertIs(earlier["externallyProtectedMonotonicAuthorityVerified"],
                      False)

    def test_unknown_claim_field_boolean_counter_and_signature_format_refused(self):
        rogue = copy.deepcopy(self.checkpoint_claim)
        rogue["productionAllowed"] = True
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_CHECKPOINT_SCHEMA_REFUSED"):
            self.evaluate(current={"claim": rogue, "signatureB64": "A" * 88})
        rogue = copy.deepcopy(self.checkpoint_claim)
        rogue["checkpointSequence"] = True
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_CHECKPOINT_FIELDS_REFUSED"):
            v3d.canonical_checkpoint(rogue)
        malformed = copy.deepcopy(self.old)
        malformed["signatureB64"] = "@not-base64"
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_SIGNATURE_ENCODING_REFUSED"):
            self.evaluate(current=malformed)

    def test_pinned_origin_is_not_authenticated_from_caller(self):
        replaced = dict(self.anchor_pin, origin="PRODUCTION_EXTERNAL_AUTHORITY")
        with self.assertRaisesRegex(v3d.CheckpointRefused,
                                    "V3D_INDEPENDENT_TEST_ROOT_REQUIRED"):
            self.evaluate(anchor_pin=replaced)


if __name__ == "__main__":
    unittest.main()
