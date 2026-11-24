#!/usr/bin/env python3
"""DOC 3 // exact proposed issuer/recipient/revocation fixture is NEVER authority."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.connections.forest import ForestC5NativeDisclosureHandoffPreflight as H
from services.connections.forest import ForestC5ProvisionalDisclosurePreflight as D
from services.connections.forest import ForestC5ExactSessionV1Preflight as V
from services.connections.forest import ForestC5SignedEvidencePreflight as S

PRIVATE_TEXT = "SYNTHETIC_PRIVATE_MODEL_OUTPUT_NEVER_DISCLOSE"


class ForestC5NativeDisclosureHandoffNegativeTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "schema": V.INTENT_SCHEMA_V1, "audience": S.AUDIENCE,
            "phase": "COMMIT_GENERATE", "action": "GENERATE",
            "principal": "alice", "tree": "treeA", "sessionId": "sessionA",
            "userTurn": "u123", "attempt": "a123", "request": "r123",
            "grant": "g123", "model": "qwen3:1.7b", "revision": 4,
            "consentEpoch": 12, "issuedAtMs": 900, "expiresAtMs": 1200,
            "challenge": "nonce_0123456789abcd",
            "requesterReleaseSha256": "a" * 64,
            "commitHostReleaseSha256": "b" * 64,
            "requesterPid": 2233, "requesterStartTicks": 998877,
            "requesterUid": 1000, "seatEpoch": 45,
        }
        self.original_wire = S.canonical_bytes(self.original)
        self.candidate = {
            "schema": D.SCHEMA, "audience": D.AUDIENCE,
            "phase": D.PHASE, "action": D.PHASE,
            "commitIntentSha256": hashlib.sha256(self.original_wire).hexdigest(),
            "principal": "alice", "tree": "treeA", "sessionId": "sessionA",
            "userTurn": "u123", "attempt": "a123", "model": "qwen3:1.7b",
            "revision": 4, "consentEpoch": 12,
            "disclosureRequest": "disc_request_1234567890",
            "disclosureCandidateId": "disc_candidate_1234567890",
            "disclosureNonce": "disc_nonce_1234567890",
            "disclosureEpoch": 3, "recipientInstance": "forest_terminal_1",
            "recipientReleaseSha256": "c" * 64, "recipientSeatEpoch": 45,
            "maxBytes": 16000, "issuedAtMs": 1000, "expiresAtMs": 1100,
        }
        self.candidate_wire = S.canonical_bytes(self.candidate)
        self.issuer = {
            "schema": H.ISSUER_SCHEMA, "audience": H.HANDOFF_AUDIENCE,
            "action": D.PHASE,
            "candidateSha256": hashlib.sha256(self.candidate_wire).hexdigest(),
            "commitIntentSha256": hashlib.sha256(self.original_wire).hexdigest(),
            "permitId": "p_provisional_1", "issuerInstance": "issuer_original_1",
            "issuerReleaseSha256": "f" * 64, "issuerEpoch": 4,
            "consentEpoch": 12, "disclosureEpoch": 3, "oneUseGeneration": 6,
            "revocationGeneration": 7, "recipientInstance": "forest_terminal_1",
            "recipientReleaseSha256": "c" * 64, "recipientSeatEpoch": 45,
            "maxBytes": 16000, "issuedAtMs": 1000, "expiresAtMs": 1100,
        }
        self.recipient = {
            "schema": H.RECIPIENT_SCHEMA, "audience": H.HANDOFF_AUDIENCE,
            "issuerInstance": "issuer_original_1",
            "permitId": "p_provisional_1", "recipientInstance": "forest_terminal_1",
            "recipientReleaseSha256": "c" * 64, "recipientSeatEpoch": 45,
            "processPid": 2233, "processStartTicks": 98765, "processUid": 1000,
            "hostBootId": "hostboot_1", "peerEvidenceDigest": "d" * 64,
        }
        self.revocation = {
            "schema": H.REVOCATION_SCHEMA, "audience": H.HANDOFF_AUDIENCE,
            "issuerInstance": "issuer_original_1", "permitId": "p_provisional_1",
            "issuerEpoch": 4, "oneUseGeneration": 6, "revocationGeneration": 7,
            "state": "ACTIVE", "claimedEmittedBytes": 12,
            "highestChunkSequence": 2, "drainedChunkSequence": 1,
            "inFlightSends": 1, "observedAtMs": 1050,
        }

    def inspect(self, issuer=None, recipient=None, revocation=None,
                *, candidate=None, original=None, now=1000,
                raw_issuer=None, raw_recipient=None, raw_revocation=None):
        return H.inspect_untrusted_native_handoff_fixture(
            self.candidate_wire if candidate is None else candidate,
            self.original_wire if original is None else original,
            S.canonical_bytes(self.issuer if issuer is None else issuer)
                if raw_issuer is None else raw_issuer,
            S.canonical_bytes(self.recipient if recipient is None else recipient)
                if raw_recipient is None else raw_recipient,
            S.canonical_bytes(self.revocation if revocation is None else revocation)
                if raw_revocation is None else raw_revocation,
            now_ms=now)

    def reject(self, reason, **kwargs):
        with self.assertRaises(H.HandoffHold) as caught:
            self.inspect(**kwargs)
        self.assertIn(reason, str(caught.exception))
        self.assertNotIn(PRIVATE_TEXT, str(caught.exception))

    def no_authority(self, data):
        self.assertEqual(data["safeActions"], [])
        self.assertIsNone(data["emitEvent"])
        self.assertEqual(data["emittedBytes"], 0)
        for key in H.NO_AUTHORITY:
            self.assertIs(data[key], False, key)
        for text in (
            PRIVATE_TEXT, "alice", "sessionA", "p_provisional_1",
            "forest_terminal_1", "hostboot_1", "qwen3:1.7b",
        ):
            self.assertNotIn(text, str(data))

    def test_01_all_claims_match_and_active_still_no_token_release(self):
        data = self.inspect()
        self.assertEqual(data["claimedRevocationStateUntrusted"], "ACTIVE")
        self.assertTrue(data["claimedScopeStructurallyConsistent"])
        self.no_authority(data)

    def test_02_fake_revoked_and_drained_claim_never_grants(self):
        data = self.inspect(revocation=dict(
            self.revocation, state="REVOKED", revocationGeneration=8,
            inFlightSends=0, drainedChunkSequence=2))
        self.assertEqual(data["claimedRevocationStateUntrusted"], "REVOKED")
        self.no_authority(data)

    def test_03_fake_revoking_claim_never_grants(self):
        data = self.inspect(revocation=dict(
            self.revocation, state="REVOKING", revocationGeneration=8))
        self.assertEqual(data["claimedRevocationStateUntrusted"], "REVOKING")
        self.no_authority(data)

    def test_04_commit_action_cannot_substitute_for_disclosure(self):
        self.reject("COMMIT_PERMISSION_CANNOT_BECOME_DISCLOSURE",
                    issuer=dict(self.issuer, action="COMMIT_GENERATE"))

    def test_05_original_c5_v1_intent_must_be_structurally_valid(self):
        original = dict(self.original, phase="DISCLOSE_PROVISIONAL")
        self.reject("ORIGINAL_CANDIDATE_INVALID",
                    original=S.canonical_bytes(original))

    def test_06_original_c5_scope_mismatch_rejected(self):
        original = dict(self.original, sessionId="otherSession")
        self.reject("ORIGINAL_CANDIDATE_INVALID",
                    original=S.canonical_bytes(original))

    def test_07_new_disclosure_candidate_changes_hash_binding(self):
        changed = dict(self.candidate, recipientInstance="differentRecipient")
        self.reject("ISSUER_CANDIDATE_OR_ORIGINAL_INTENT_MISMATCH",
                    candidate=S.canonical_bytes(changed))
        # If caller recalculates claimed digest, still no independent grant.
        candidate = dict(self.candidate, recipientInstance="differentRecipient")
        wire = S.canonical_bytes(candidate)
        issuer = dict(self.issuer,
            candidateSha256=hashlib.sha256(wire).hexdigest(),
            recipientInstance="differentRecipient")
        recipient = dict(self.recipient, recipientInstance="differentRecipient")
        result = self.inspect(candidate=wire, issuer=issuer, recipient=recipient)
        self.no_authority(result)

    def test_08_forged_issuer_candidate_digest_refused(self):
        self.reject("ISSUER_CANDIDATE_OR_ORIGINAL_INTENT_MISMATCH",
                    issuer=dict(self.issuer, candidateSha256="e" * 64))

    def test_09_forged_commit_intent_digest_refused(self):
        self.reject("ISSUER_CANDIDATE_OR_ORIGINAL_INTENT_MISMATCH",
                    issuer=dict(self.issuer, commitIntentSha256="e" * 64))

    def test_10_issuer_disclosure_epoch_or_consent_epoch_refused(self):
        for key in ("consentEpoch", "disclosureEpoch"):
            with self.subTest(key=key):
                self.reject("ISSUER_CANDIDATE_OR_ORIGINAL_INTENT_MISMATCH",
                            issuer=dict(self.issuer, **{key: self.issuer[key] + 1}))

    def test_11_commit_grant_and_correlation_cannot_be_reused_as_permit(self):
        for value in (
            self.original["grant"], self.original["request"],
            self.candidate["disclosureRequest"], self.candidate["disclosureNonce"],
        ):
            with self.subTest(value=value):
                self.reject("PERMIT_ID_REUSES_REQUEST_OR_COMMIT_GRANT",
                            issuer=dict(self.issuer, permitId=value))

    def test_12_issuer_recipient_release_instance_seat_and_budget_are_bound(self):
        changes = {
            "recipientInstance": "otherRecipient",
            "recipientReleaseSha256": "f" * 64,
            "recipientSeatEpoch": 46, "maxBytes": 16001,
        }
        for key,value in changes.items():
            with self.subTest(key=key):
                self.reject("ISSUER_RECIPIENT_OR_BUDGET_SCOPE_MISMATCH",
                            issuer=dict(self.issuer, **{key:value}))

    def test_13_claimed_issuer_lease_must_not_extend_candidate(self):
        self.reject("ISSUER_CANNOT_EXTEND_DISCLOSURE_CANDIDATE_LEASE",
                    issuer=dict(self.issuer, expiresAtMs=1101))
        self.reject("ISSUER_CANNOT_EXTEND_DISCLOSURE_CANDIDATE_LEASE",
                    issuer=dict(self.issuer, issuedAtMs=999))

    def test_14_claimed_issuer_lifetime_check_does_not_authenticate_clock(self):
        self.reject("ISSUER_FIXTURE_TIME_NOT_CURRENT",
                    issuer=dict(self.issuer, expiresAtMs=1030), now=1030)
        self.reject("ISSUER_FIXTURE_TIME_NOT_CURRENT",
                    issuer=dict(self.issuer, issuedAtMs=1010), now=1000)

    def test_15_forged_positive_permission_and_consent_flags_are_extra_fields(self):
        for injected in (
            ("protectedIssuerAuthenticated", True),
            ("humanConsentVerified", True),
            ("safeToEmitProvisionalText", True),
            ("nativePermitGranted", True),
        ):
            with self.subTest(injected=injected):
                self.reject("INVALID_ISSUER_WIRE",
                            issuer=dict(self.issuer, **dict([injected])))

    def test_16_recipient_swap_at_process_boundary_denied(self):
        for key,value in (
            ("recipientInstance", "otherRecipient"), ("permitId", "otherPermit"),
            ("issuerInstance", "otherIssuer"),
            ("recipientReleaseSha256", "e" * 64),
            ("recipientSeatEpoch", 49),
        ):
            with self.subTest(key=key):
                self.reject("RECIPIENT_CLAIM_MISMATCH_" + key,
                            recipient=dict(self.recipient, **{key:value}))

    def test_17_invalid_process_claim_refused(self):
        for key,value in (
            ("processPid", 0), ("processStartTicks", True),
            ("recipientSeatEpoch", -1), ("processUid", False),
        ):
            with self.subTest(key=key):
                self.reject("INVALID_RECIPIENT_PROCESS_UID" if key == "processUid"
                            else "INVALID_RECIPIENT_" + key,
                            recipient=dict(self.recipient, **{key:value}))

    def test_18_made_up_peer_digest_is_still_untrusted_even_if_well_shaped(self):
        recipient = dict(self.recipient, peerEvidenceDigest="9" * 64,
                         hostBootId="fabricated_boot_1")
        self.no_authority(self.inspect(recipient=recipient))
        self.reject("INVALID_PEER_EVIDENCE",
                    recipient=dict(self.recipient, peerEvidenceDigest="fake"))

    def test_19_forged_recipient_positive_authentication_rejected(self):
        self.reject("INVALID_RECIPIENT_WIRE",
                    recipient=dict(self.recipient, authenticated=True))

    def test_20_wrong_revocation_permit_issuer_epoch_or_generation_refused(self):
        for key,value in (
            ("permitId", "otherPermit"), ("issuerInstance", "otherIssuer"),
            ("issuerEpoch", 5), ("oneUseGeneration", 7),
        ):
            with self.subTest(key=key):
                self.reject("REVOCATION_CLAIM_MISMATCH_" + key,
                            revocation=dict(self.revocation, **{key:value}))

    def test_21_revocation_claimed_byte_overflow_refused(self):
        self.reject("CLAIMED_STREAM_EXCEEDS_BOUND",
                    revocation=dict(self.revocation, claimedEmittedBytes=16001))

    def test_22_drain_sequence_cannot_exceed_highest_chunk_sequence(self):
        self.reject("IMPOSSIBLE_DRAIN_SEQUENCE",
                    revocation=dict(self.revocation, drainedChunkSequence=3))

    def test_23_active_state_cannot_report_advanced_revocation_epoch(self):
        self.reject("ACTIVE_WITH_CHANGED_REVOCATION_GENERATION",
                    revocation=dict(self.revocation, revocationGeneration=8))

    def test_24_revocation_needs_higher_generation(self):
        self.reject("REVOCATION_WITHOUT_ADVANCING_GENERATION",
                    revocation=dict(self.revocation, state="REVOKING"))
        self.reject("REVOCATION_WITHOUT_ADVANCING_GENERATION",
                    revocation=dict(self.revocation, state="REVOKED",
                                    inFlightSends=0, drainedChunkSequence=2))

    def test_25_revoked_ack_with_sends_in_flight_refused(self):
        self.reject("REVOKED_ACK_CLAIMS_IN_FLIGHT_OUTPUT",
                    revocation=dict(self.revocation, state="REVOKED",
                                    revocationGeneration=8,
                                    drainedChunkSequence=2, inFlightSends=1))

    def test_26_revoked_ack_with_undrained_chunk_refused(self):
        self.reject("REVOKED_ACK_CLAIMS_IN_FLIGHT_OUTPUT",
                    revocation=dict(self.revocation, state="REVOKED",
                                    revocationGeneration=8, inFlightSends=0,
                                    drainedChunkSequence=1))

    def test_27_fake_complete_revoke_ack_is_not_authenticated(self):
        self.no_authority(self.inspect(revocation=dict(
            self.revocation, state="REVOKED", revocationGeneration=8,
            inFlightSends=0, drainedChunkSequence=2, claimedEmittedBytes=0)))

    def test_28_forged_revocation_recovery_and_budget_flags_rejected(self):
        for name in ("nativeRevocationAuthenticated",
                     "outputDrained", "budgetEnforced"):
            with self.subTest(name=name):
                self.reject("INVALID_REVOCATION_WIRE",
                            revocation=dict(self.revocation, **{name: True}))

    def test_29_duplicate_keys_noncanonical_and_extra_fields_refused(self):
        raw=S.canonical_bytes(self.issuer)
        duplicated=raw.replace(
            b'"schema":',
            b'"schema":"postapollo.forest.c5-disclosure-issuer-handoff.fixture-v0","schema":',1)
        self.reject("INVALID_ISSUER_WIRE",raw_issuer=duplicated)
        self.reject("INVALID_ISSUER_WIRE",
                    raw_issuer=raw.replace(b':',b': ',1))
        self.reject("INVALID_RECIPIENT_WIRE",
                    recipient=dict(self.recipient, privateText=PRIVATE_TEXT))
        self.reject("INVALID_REVOCATION_WIRE",
                    revocation=dict(self.revocation, text=PRIVATE_TEXT))

    def test_30_invalid_domain_across_roles_refused(self):
        for field, value, expected in (
            ("issuer", dict(self.issuer,audience=S.AUDIENCE), "ISSUER_DOMAIN_MISMATCH"),
            ("recipient",dict(self.recipient,schema=H.ISSUER_SCHEMA), "RECIPIENT_DOMAIN_MISMATCH"),
            ("revocation",dict(self.revocation,audience=D.AUDIENCE), "REVOCATION_DOMAIN_MISMATCH"),
        ):
            with self.subTest(field=field):
                self.reject(expected,**{field:value})

    def test_31_unexpected_revocation_state_denied(self):
        self.reject("INVALID_REVOCATION_STATE",
                    revocation=dict(self.revocation,state="COMMIT_CONFIRMED"))

    def test_32_true_one_use_replay_protection_cannot_be_claimed_by_fixture(self):
        # Replaying identical records is indistinguishable to a pure parser.
        # Both diagnostic checks HOLD. Native issuer must own a persistent
        # consumed-permit counter; NO test fixture can supply that fact.
        a=self.inspect()
        b=self.inspect()
        self.assertEqual(a,b)
        self.no_authority(a)

    def test_33_source_contains_no_native_actuation_or_allowing_path(self):
        source = (ROOT / "services/connections/forest/ForestC5NativeDisclosureHandoffPreflight.py").read_text()
        for forbidden in (
            "sqlite3.connect(", "subprocess.", "socket.socket(",
            "Ed25519PrivateKey", "stream_chat(", "requests.post(",
            '"safeToEmitProvisionalText": True', '"productionAuthority": True',
        ):
            self.assertNotIn(forbidden,source)
        self.assertIn('"emitEvent": None',source)
        self.assertIn('"emittedBytes": 0',source)


    def test_34_malformed_handoff_wires_do_not_retain_decoder_error_chain(self):
        raw = ('{"private":"' + PRIVATE_TEXT + '",').encode("ascii")
        for field, reason in (
            ("raw_issuer", "INVALID_ISSUER_WIRE"),
            ("raw_recipient", "INVALID_RECIPIENT_WIRE"),
            ("raw_revocation", "INVALID_REVOCATION_WIRE"),
            ("candidate", "ORIGINAL_CANDIDATE_INVALID"),
            ("original", "ORIGINAL_CANDIDATE_INVALID"),
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(H.HandoffHold, reason) as exc:
                    self.inspect(**{field: raw})
                self.assertIsNone(exc.exception.__cause__)
                self.assertIsNone(exc.exception.__context__)
                self.assertNotIn(PRIVATE_TEXT, str(exc.exception))


if __name__ == "__main__":
    unittest.main()
