"""Trash++ V3e // offline signed retrieval, challenge and rollback refusal.

Ephemeral test keys in memory; no network, no local files, no production pins.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import secrets
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.trash import archive_v3e_retrieval_envelope_review as v3e
from scripts.trash import archive_v3d_external_checkpoint_review as v3d
import test_archive_v3d_external_checkpoint_review as v3dtests


def pub(key):
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)


class V3eSignedRetrievalReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture = v3dtests.V3dIndependentCheckpointReviewTests("runTest")
        self.fixture.setUp()
        self.key = Ed25519PrivateKey.generate()
        self.responder_pin = {
            "responderKeyId": "v3e-test-independent-responder",
            "publicKeyBytes": pub(self.key),
            "origin": v3e.PIN_ORIGIN,
        }
        self.request = {
            "schema": v3e.REQUEST_KIND,
            "audience": v3e.AUDIENCE,
            "policyOrigin": v3e.ORIGIN,
            "ownerId": self.fixture.owner,
            "grantSha256": self.fixture.grant,
            "nonce": secrets.token_hex(32),
            "minimumCheckpointSequence": 1,
        }
        self.old = self.fixture.old
        self.current = self.fixture.old
        self.signed_witness = self.fixture.witness
        self.receipt = self.make_receipt()

    def sha(self, checkpoint):
        return hashlib.sha256(
            v3d.canonical_checkpoint(checkpoint["claim"])).hexdigest()

    def sign(self, claim, key=None):
        key = self.key if key is None else key
        return {
            "claim": copy.deepcopy(claim),
            "signatureB64": base64.b64encode(
                key.sign(v3e.canonical_response(claim))).decode("ascii"),
        }

    def make_receipt(self, *, current=None, old=None, request=None):
        current = self.current if current is None else current
        old = self.old if old is None else old
        request = self.request if request is None else request
        claim = {
            "schema": v3e.RESPONSE_KIND,
            "audience": v3e.AUDIENCE,
            "policyOrigin": v3e.ORIGIN,
            "responderKeyId": self.responder_pin["responderKeyId"],
            "requestSha256": hashlib.sha256(
                v3e.canonical_request(request)).hexdigest(),
            "nonce": request["nonce"],
            "referenceCheckpointSha256": self.sha(old),
            "checkpointSha256": self.sha(current),
            "checkpointSequence": current["claim"]["checkpointSequence"],
            "transportStatus": "TEST_CHECKPOINT_AVAILABLE",
        }
        return self.sign(claim)

    def evaluate(self, *, request=None, response=None, old=None,
                 current=None, witness=None, responder_pin=None):
        return v3e.review(
            self.request if request is None else request,
            self.receipt if response is None else response,
            self.old if old is None else old,
            self.current if current is None else current,
            self.signed_witness if witness is None else witness,
            responder_pin=(self.responder_pin if responder_pin is None
                           else responder_pin),
            anchor_pin=self.fixture.anchor_pin,
            witness_pin=self.fixture.witness_pin,
            observed_floor=self.fixture.floor,
            floor_signer_public_key=pub(self.fixture.floor_key),
            expected_owner_id=self.fixture.owner,
            expected_grant_sha256=self.fixture.grant,
        )

    def assert_hold(self, result):
        self.assertEqual(result["state"], "RETRIEVAL_AUTHORITY_HOLD")
        self.assertTrue(result["readOnly"])
        self.assertTrue(result["requiresIndependentReview"])
        for field in (
            "independentResponderAuthenticated",
            "authenticatedRetrievalChannelVerified",
            "durableReplayProtectionVerified",
            "independentAuthorityAuthenticated",
            "externallyProtectedMonotonicAuthorityVerified",
            "trustedReferenceHighwaterVerified",
            "trustedClockVerified", "sourceOwnerAuthorityVerified",
            "c3eAuthenticatedSourceVerified", "c5HumanConsentVerified",
            "backupCustodyVerified", "captureAllowed", "productionAllowed",
            "restoreAllowed", "burnAllowed", "automaticRetryAllowed",
            "automaticRollbackAllowed", "deleteOriginalAllowed",
        ):
            self.assertIs(result[field], False, field)
        self.assertEqual(result["safeActions"], [])
        self.assertIn("network_transport_not_implemented", result["holdReasons"])
        self.assertIn("independent_checkpoint_storage_unverified",
                      result["holdReasons"])

    def test_valid_signed_offline_response_still_denies_every_action(self):
        out = self.evaluate()
        self.assert_hold(out)
        self.assertTrue(out["offlineResponseSignatureValid"])
        self.assertTrue(out["offlineChallengeBindingValid"])
        self.assertTrue(out["offlineCheckpointBindingValid"])
        self.assertEqual(out["observedCheckpointSequence"], 1)

    def test_valid_forward_checkpoint_response_still_denies(self):
        advanced, witness = self.fixture.advanced()
        current = self.fixture.sign_checkpoint(advanced)
        response = self.make_receipt(current=current)
        out = self.evaluate(response=response, current=current,
                            witness=witness)
        self.assert_hold(out)
        self.assertEqual(out["observedCheckpointSequence"], 2)
        self.assertNotIn("signed_checkpoint_chain_diverged",
                         out["holdReasons"])

    def test_missing_unavailable_or_truncated_response_refuses(self):
        for broken in (None, {}, {"transportStatus": "UNAVAILABLE"}):
            with self.subTest(broken=broken):
                with self.assertRaises(v3e.RetrievalRefused):
                    v3e.review(
                        self.request, broken, self.old, self.current,
                        self.signed_witness,
                        responder_pin=self.responder_pin,
                        anchor_pin=self.fixture.anchor_pin,
                        witness_pin=self.fixture.witness_pin,
                        observed_floor=self.fixture.floor,
                        floor_signer_public_key=pub(self.fixture.floor_key),
                        expected_owner_id=self.fixture.owner,
                        expected_grant_sha256=self.fixture.grant,
                    )

    def test_signed_response_for_different_nonce_is_refused(self):
        changed = dict(self.request, nonce=secrets.token_hex(32))
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_CHALLENGE_MISMATCH_REFUSED"):
            self.evaluate(request=changed)

    def test_wrong_nonce_even_with_original_request_digest_refuses(self):
        changed = dict(self.receipt["claim"], nonce=secrets.token_hex(32))
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_CHALLENGE_MISMATCH_REFUSED"):
            self.evaluate(response=self.sign(changed))

    def test_old_signed_response_for_new_request_floor_is_refused(self):
        changed = dict(self.request, minimumCheckpointSequence=2)
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_CHALLENGE_MISMATCH_REFUSED"):
            self.evaluate(request=changed)

    def test_new_request_but_old_checkpoint_creates_hard_hold(self):
        requested = dict(self.request, minimumCheckpointSequence=2)
        response = self.make_receipt(request=requested)
        out = self.evaluate(request=requested, response=response)
        self.assert_hold(out)
        self.assertIn("checkpoint_below_requested_floor", out["holdReasons"])

    def test_tampered_response_digests_are_rejected_even_if_signed(self):
        for field in ("checkpointSha256", "referenceCheckpointSha256"):
            changed = dict(self.receipt["claim"], **{field: "f" * 64})
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                        v3e.RetrievalRefused,
                        "V3E_RESPONSE_CHECKPOINT_BINDING_REFUSED"):
                    self.evaluate(response=self.sign(changed))

    def test_tampered_checkpoint_sequence_rejected_even_if_signed(self):
        changed = dict(self.receipt["claim"], checkpointSequence=2)
        with self.assertRaisesRegex(
                v3e.RetrievalRefused,
                "V3E_RESPONSE_CHECKPOINT_BINDING_REFUSED"):
            self.evaluate(response=self.sign(changed))

    def test_forged_response_signature_refused(self):
        forged = self.sign(self.receipt["claim"],
                           Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_SIGNATURE_REFUSED"):
            self.evaluate(response=forged)

    def test_responder_key_must_differ_from_all_other_signers(self):
        for key in (self.fixture.anchor_key,
                    self.fixture.witness_key, self.fixture.floor_key):
            with self.subTest(key=key):
                pin = dict(self.responder_pin, publicKeyBytes=pub(key))
                with self.assertRaisesRegex(
                        v3e.RetrievalRefused,
                        "V3E_SEPARATE_TEST_RESPONDER_REQUIRED"):
                    self.evaluate(responder_pin=pin)

    def test_claimed_production_origin_is_rejected(self):
        forged_origin = dict(self.responder_pin, origin="PRODUCTION_AUTHORITY")
        with self.assertRaisesRegex(
                v3e.RetrievalRefused,
                "V3E_SEPARATE_TEST_RESPONDER_REQUIRED"):
            self.evaluate(responder_pin=forged_origin)
        altered = dict(self.receipt["claim"], policyOrigin="PRODUCTION")
        with self.assertRaisesRegex(
                v3e.RetrievalRefused,
                "V3E_RESPONSE_FIELDS_REFUSED"):
            self.evaluate(response={"claim": altered, "signatureB64": "A"*88})

    def test_owner_and_grant_request_substitution_refused(self):
        bad = dict(self.request, grantSha256="d" * 64)
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_REQUEST_OWNER_GRANT_REFUSED"):
            self.evaluate(request=bad)

    def test_noncanonical_signatures_and_unknown_fields_refused(self):
        malformed = dict(self.receipt, signatureB64="broken")
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_SIGNATURE_ENCODING_REFUSED"):
            self.evaluate(response=malformed)
        extra = dict(self.receipt["claim"], approved=True)
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_RESPONSE_SCHEMA_REFUSED"):
            v3e.canonical_response(extra)

    def test_invalid_bool_counter_and_short_nonce_refused(self):
        invalid = dict(self.request, minimumCheckpointSequence=True)
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_REQUEST_FIELDS_REFUSED"):
            v3e.canonical_request(invalid)
        invalid = dict(self.request, nonce="not-a-nonce")
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_REQUEST_FIELDS_REFUSED"):
            v3e.canonical_request(invalid)

    def test_retrieval_does_not_erase_v3d_signed_rollback_hold(self):
        newer, signed_witness = self.fixture.advanced()
        newer_signed = self.fixture.sign_checkpoint(newer)
        receipt = self.make_receipt(old=newer_signed)
        out = self.evaluate(old=newer_signed, response=receipt)
        self.assert_hold(out)
        self.assertIn("signed_checkpoint_sequence_rollback",
                      out["holdReasons"])
        self.assertIn("retrieved_checkpoint_older_than_reference",
                      out["holdReasons"])

    def test_wrong_checkpoint_witness_signature_refuses(self):
        rogue = self.fixture.sign_witness(
            self.fixture.witness_claim, Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(v3e.RetrievalRefused,
                                    "V3E_CHECKPOINT_VERIFICATION_REFUSED"):
            self.evaluate(witness=rogue)

    def test_pair_substitution_cannot_establish_external_custody(self):
        # Even a perfectly consistent, signature-valid old pair and nonce-
        # matched response is no proof that the host could not replace all of
        # these inputs. The offline implementation MUST keep a permanent hold.
        out = self.evaluate()
        self.assert_hold(out)
        self.assertIs(out["independentAuthorityAuthenticated"], False)
        self.assertIn("trusted_reference_highwater_unverified",
                      out["holdReasons"])
        self.assertIn("retrieval_replay_history_unverified",
                      out["holdReasons"])

    def test_same_signed_response_reuse_cannot_claim_single_use(self):
        first = self.evaluate()
        second = self.evaluate()
        self.assert_hold(first)
        self.assert_hold(second)
        self.assertFalse(first["durableReplayProtectionVerified"])
        self.assertIn("challenge_entropy_and_single_use_unverified",
                      second["holdReasons"])


if __name__ == "__main__":
    unittest.main()
