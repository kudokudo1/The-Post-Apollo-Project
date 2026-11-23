#!/usr/bin/env python3
"""DOC 4 C5-H3: hostile exact-operator-review shape and no-authority cases."""
from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services/connections/hospital"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import HospitalNativeIssuerCore as C
import HospitalC5ExactConsentProbe as P


class C5H3UntrustedEvidence(unittest.TestCase):
    def setUp(self):
        self.now = 1700000000
        self.policy = {
            "operatorUid": 1000,
            "hostId": "c" * 64,
            "minimumPolicyGeneration": 9,
        }
        self.request = {
            "schema": C.REQUEST_SCHEMA,
            "roomId": "hospital-room-04",
            "action": "TRASH",
        }
        self.prepared = {
            "schema": C.PREPARED_SCHEMA,
            "requestNonce": C.b64(bytes(range(32))),
            "action": "TRASH",
            "roomId": "hospital-room-04",
            "patientId": "patient-04",
            "repository": "kudokudo1/The-Post-Apollo-Project",
            "expectedRevision": 37,
            "expectedDigest": "d" * 64,
            "state": "ACTIVE",
            "blockers": [],
            "canTrash": True,
            "canRestore": False,
            "retentionApproved": True,
            "legalHold": False,
            "policyGeneration": 9,
            "writerInstance": "protected-px-001",
            "expiresAt": self.now + 28,
        }

    def review(self):
        return P.build_review(
            self.request, self.prepared, self.policy,
            operator_uid=1000,
            seat_id="logind-seat0-c2",
            host_id="c" * 64,
            now=self.now,
        )

    def claim(self, reference=None):
        ref = reference or self.review()
        review = ref["review"]
        return {
            "schema": P.CLAIM_SCHEMA,
            "reviewDigest": ref["reviewDigest"],
            "requestNonce": review["requestNonce"],
            "action": review["action"],
            "roomId": review["roomId"],
            "operatorUid": review["operatorUid"],
            "seatId": review["seatId"],
            "hostId": review["hostId"],
            "agentReleaseDigest": "a" * 64,
            "claimedVisible": True,
            "claimedConfirmed": True,
            "shownAt": self.now + 1,
            "confirmedAt": self.now + 2,
        }

    def probe(self, claim=None, *, now=None, reference=None):
        ref = self.review() if reference is None else reference
        return P.inspect_untrusted_claim(
            ref,
            C.canonical(self.claim(ref) if claim is None else claim),
            now=self.now + 4 if now is None else now,
        )

    def assert_hold(self, result):
        self.assertIs(result["externalConsentProducerAuthenticated"], False)
        self.assertIs(result["humanConsentVerified"], False)
        self.assertIs(result["independentHistoryVerified"], False)
        self.assertIs(result["signingAllowed"], False)
        self.assertIs(result["nativeRoomMutationAllowed"], False)
        self.assertIs(result["productionAuthorized"], False)
        self.assertEqual(result["safeActions"], [])

    def test_01_review_matches_exact_validated_px_source_shape(self):
        r = self.review()
        value = r["review"]
        self.assertEqual(set(value), P.REVIEW_FIELDS)
        self.assertEqual(value["action"], "TRASH")
        self.assertEqual(value["purpose"], "HOSPITAL_ROOM_TRASH")
        self.assertEqual(value["roomId"], "hospital-room-04")
        self.assertEqual(value["patientId"], "patient-04")
        self.assertEqual(value["expectedRevision"], 37)
        self.assertEqual(value["expectedDigest"], "d" * 64)
        self.assertEqual(value["requestNonce"], self.prepared["requestNonce"])
        self.assertEqual(value["operatorUid"], 1000)
        self.assertEqual(value["seatId"], "logind-seat0-c2")
        self.assertEqual(value["hostId"], "c" * 64)
        self.assertIs(value["originalPreserved"], True)
        self.assertIs(value["burnAllowed"], False)
        self.assertEqual(r["reviewDigest"], hashlib.sha256(
            P.DOMAIN + C.canonical(value)).hexdigest())

    def test_02_perfect_fake_confirmation_never_authorizes(self):
        outcome = self.probe()
        self.assertTrue(outcome["claimMatchesReview"])
        self.assertEqual(outcome["status"], "MATCHING_CLAIM_UNTRUSTED_HOLD")
        self.assert_hold(outcome)

    def test_03_nonce_rotation_changes_review_digest(self):
        prior = self.review()["reviewDigest"]
        self.prepared["requestNonce"] = C.b64(bytes(range(31, -1, -1)))
        self.assertNotEqual(prior, self.review()["reviewDigest"])

    def test_04_room_identity_changes_review_digest(self):
        prior = self.review()["reviewDigest"]
        self.request["roomId"] = "hospital-room-05"
        self.prepared["roomId"] = "hospital-room-05"
        self.assertNotEqual(prior, self.review()["reviewDigest"])

    def test_05_graph_revision_and_policy_epoch_each_change_digest(self):
        for field, value in (
            ("expectedDigest", "e" * 64),
            ("expectedRevision", 38),
            ("policyGeneration", 10),
        ):
            with self.subTest(field=field):
                old = self.prepared[field]
                prior = self.review()["reviewDigest"]
                self.prepared[field] = value
                self.assertNotEqual(prior, self.review()["reviewDigest"])
                self.prepared[field] = old

    def test_06_legal_hold_and_retention_denial_fail_source_review(self):
        for field, value in (("legalHold", True), ("retentionApproved", False)):
            with self.subTest(field=field):
                self.prepared[field] = value
                with self.assertRaises(C.Refused):
                    self.review()
                self.prepared[field] = not value

    def test_07_wrong_action_or_ineligible_room_fails_source_review(self):
        self.request["action"] = "RESTORE"
        self.prepared["action"] = "RESTORE"
        with self.assertRaises(C.Refused):
            self.review()

    def test_08_operator_or_host_outside_claimed_policy_fails(self):
        for kwargs in (
            {"operator_uid": 1001, "host_id": "c" * 64},
            {"operator_uid": 1000, "host_id": "f" * 64},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(C.Refused):
                    P.build_review(
                        self.request, self.prepared, self.policy,
                        seat_id="logind-seat0-c2", now=self.now, **kwargs)

    def test_09_expired_source_review_fails(self):
        self.prepared["expiresAt"] = self.now
        with self.assertRaises(C.Refused):
            self.review()

    def test_10_wrong_claimed_nonce_never_matches(self):
        c = self.claim()
        c["requestNonce"] = C.b64(bytes(range(31, -1, -1)))
        result = self.probe(c)
        self.assertFalse(result["claimMatchesReview"])
        self.assert_hold(result)

    def test_11_wrong_room_action_or_uid_never_matches(self):
        for field, value in (
            ("roomId", "hospital-room-99"),
            ("action", "RESTORE"),
            ("operatorUid", 1001),
            ("seatId", "logind-seat1-c4"),
            ("hostId", "f" * 64),
        ):
            with self.subTest(field=field):
                c = self.claim()
                c[field] = value
                result = self.probe(c)
                self.assertFalse(result["claimMatchesReview"])
                self.assert_hold(result)

    def test_12_wrong_digest_cannot_match(self):
        c = self.claim()
        c["reviewDigest"] = "0" * 64
        self.assertFalse(self.probe(c)["claimMatchesReview"])

    def test_13_cancel_or_not_shown_cannot_match(self):
        for field in ("claimedVisible", "claimedConfirmed"):
            c = self.claim()
            c[field] = False
            self.assertFalse(self.probe(c)["claimMatchesReview"])

    def test_14_after_expiry_cannot_match(self):
        c = self.claim()
        result = self.probe(c, now=self.prepared["expiresAt"])
        self.assertFalse(result["claimMatchesReview"])
        self.assert_hold(result)

    def test_15_future_and_reordered_times_cannot_match(self):
        for shown, confirmed in (
            (self.now + 20, self.now + 2),
            (self.now + 1, self.now + 29),
            (self.now + 11, self.now + 12),
        ):
            with self.subTest(shown=shown):
                c = self.claim()
                c.update(shownAt=shown, confirmedAt=confirmed)
                self.assertFalse(self.probe(c)["claimMatchesReview"])

    def test_16_duplicate_json_claim_fields_refused(self):
        raw = C.canonical(self.claim()).replace(
            b'"action":', b'"action":"RESTORE","action":', 1)
        with self.assertRaises(C.Refused):
            P.inspect_untrusted_claim(
                self.review(), raw, now=self.now + 4)

    def test_17_noncanonical_json_and_extraneous_authority_flag_refused(self):
        for raw in (
            b" " + C.canonical(self.claim()),
            C.canonical({**self.claim(), "productionAuthorized": True}),
        ):
            with self.subTest(raw=raw[:10]):
                with self.assertRaises(C.Refused):
                    P.inspect_untrusted_claim(
                        self.review(), raw, now=self.now + 4)

    def test_18_malformed_release_digest_and_boolean_uid_refused(self):
        for field, value in (
            ("agentReleaseDigest", "trusted-agent"),
            ("operatorUid", True),
            ("claimedConfirmed", 1),
        ):
            with self.subTest(field=field):
                c = self.claim()
                c[field] = value
                with self.assertRaises(C.Refused):
                    self.probe(c)

    def test_19_tampered_reference_is_refused(self):
        r = self.review()
        r["review"]["patientId"] = "changed-patient"
        with self.assertRaises(C.Refused):
            self.probe(reference=r)

    def test_20_fake_agent_release_hash_never_creates_trust(self):
        c = self.claim()
        for fake_release in ("0" * 64, "f" * 64):
            c["agentReleaseDigest"] = fake_release
            result = self.probe(c)
            self.assertTrue(result["claimMatchesReview"])
            self.assert_hold(result)

    def test_21_never_accept_arbitrary_modes_or_prod_controls(self):
        for kw in ({}, {"provider": object()}, {"approved": True}):
            with self.assertRaises(C.Refused):
                P.production_admission(**kw)

    def test_22_no_runtime_import_or_unsafe_fixture_producer(self):
        service = (
            ROOT / "services/connections/hospital/HospitalNativeIssuerService.py"
        ).read_text()
        self.assertNotIn("HospitalC5ExactConsentProbe", service)
        self.assertNotIn("test_only", service)
        self.assertNotIn("C5H3_ALLOW", service)
        self.assertNotIn("--consent-evidence-override", service)


if __name__ == "__main__":
    unittest.main(verbosity=2)
