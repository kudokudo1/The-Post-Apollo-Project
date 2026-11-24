#!/usr/bin/env python3
"""Connections Forest B4c // exact signed roles, still DENY ALL native authority."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "services/connections/forest/ForestC5SignedEvidencePreflight.py"
spec = importlib.util.spec_from_file_location("forest_b4c_c5", FILE)
if spec is None or spec.loader is None:
    raise AssertionError("EXACT_SOURCE_REQUIRED")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def public_bytes(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def sample_intent(**edits):
    data = {
        "schema": C.INTENT_SCHEMA,
        "audience": C.AUDIENCE,
        "phase": "COMMIT_GENERATE", "action": "GENERATE",
        "principal": "alice", "tree": "treeA",
        "userTurn": "u123", "attempt": "a123",
        "request": "r123", "grant": "g123",
        "model": "qwen3:1.7b", "revision": 4, "consentEpoch": 12,
        "issuedAtMs": 900, "expiresAtMs": 1200, "challenge": "nonce_0123456789abcd",
        "requesterReleaseSha256": "a" * 64,
        "commitHostReleaseSha256": "b" * 64,
        "requesterPid": 2233, "requesterStartTicks": 998877,
        "requesterUid": 1000, "seatEpoch": 45,
    }
    data.update(edits)
    return data


def signed_pair(data=None, *, source_key=None, review_key=None):
    source_key = source_key or Ed25519PrivateKey.generate()
    review_key = review_key or Ed25519PrivateKey.generate()
    source_public, review_public = public_bytes(source_key), public_bytes(review_key)
    intent_wire = C.canonical_bytes(data or sample_intent())
    intent_digest = hashlib.sha256(intent_wire).hexdigest()

    def record(role, decision, key):
        return C.canonical_bytes({
            "schema": C.RECORD_SCHEMA, "audience": C.AUDIENCE,
            "role": role, "decision": decision,
            "intentSha256": intent_digest,
            "signerKeySha256": hashlib.sha256(key).hexdigest(),
            "consentEpoch": (data or sample_intent())["consentEpoch"],
            "challenge": (data or sample_intent())["challenge"],
        })

    a = record(C.SOURCE_ROLE, "SOURCE_FIXTURE", source_public)
    b = record(C.REVIEW_ROLE, "REVIEW_FIXTURE", review_public)
    return [intent_wire, a, source_key.sign(a), source_public,
            b, review_key.sign(b), review_public]


def verify(parts, *, now=1000):
    return C.verify_unenrolled_role_consistency(*parts, now_ms=now)


class ForestC5SignedEvidencePreflightTests(unittest.TestCase):
    def setUp(self):
        self.pair = signed_pair()

    def assert_hold(self, parts, contains=None):
        with self.assertRaises(C.EvidenceHold) as caught:
            verify(parts)
        if contains:
            self.assertIn(contains, str(caught.exception))

    def test_01_two_real_distinct_signatures_match_but_no_grant(self):
        seen = verify(self.pair)
        self.assertEqual(seen["status"], "TWO_SIGNED_ROLES_MATCH_UNENROLLED_FIXTURE")
        self.assertEqual(seen["safeActions"], [])
        self.assertNotEqual(seen["requesterRolePublicKeySha256Untrusted"],
                            seen["reviewerRolePublicKeySha256Untrusted"])
        for field in C.NO_AUTHORITY:
            self.assertIs(seen[field], False, field)

    def test_02_one_changed_signed_intent_rejected(self):
        for field, new in [
            ("principal", "bob"), ("tree", "treeB"), ("userTurn", "u999"),
            ("attempt", "a999"), ("request", "r999"), ("grant", "g999"),
            ("model", "llama3:8b"), ("revision", 5), ("consentEpoch", 13),
            ("requesterReleaseSha256", "f"*64),
            ("commitHostReleaseSha256", "e"*64),
            ("requesterPid", 5555), ("requesterStartTicks", 33),
            ("requesterUid", 2000), ("seatEpoch", 2),
            ("challenge", "nonce_9999999999abcd"),
        ]:
            with self.subTest(field=field):
                mutated = self.pair.copy()
                mutated[0] = C.canonical_bytes(sample_intent(**{field: new}))
                self.assert_hold(mutated, "SIGNED_INTENT")

    def test_03_different_reviewer_key_or_alias_refused(self):
        alias = self.pair.copy()
        alias[6] = alias[3]
        self.assert_hold(alias, "DISTINCT_SIGNER_KEYS_REQUIRED")
        substituted = self.pair.copy()
        substituted[6] = public_bytes(Ed25519PrivateKey.generate())
        self.assert_hold(substituted, "SIGNED_INTENT_KEY_OR_EPOCH_MISMATCH")

    def test_04_signature_bytes_and_domain_swap_refused(self):
        wrong = self.pair.copy()
        wrong[2] = wrong[5]
        self.assert_hold(wrong, "SIGNATURE_INVALID")
        wrong = self.pair.copy()
        wrong[5] = b"\x01" * 64
        self.assert_hold(wrong, "SIGNATURE_INVALID")
        wrong = self.pair.copy()
        wrong[2] = b"short"
        self.assert_hold(wrong, "SIGNATURE_BOUNDS")

    def test_05_duplicate_json_and_noncanonical_serialization_refused(self):
        bad = self.pair.copy()
        bad[0] = b'{"schema":"x","schema":"y"}'
        self.assert_hold(bad, "DUPLICATE_JSON_KEY")
        bad[0] = self.pair[0].replace(b',"attempt":', b', "attempt":')
        self.assert_hold(bad, "NONCANONICAL_JSON")
        bad[0] = self.pair[0].replace(b',"attempt":', b',"productionAuthority":true,"attempt":')
        self.assert_hold(bad, "EXACT_FIELDS_REQUIRED")

    def test_06_role_and_decision_cannot_be_cross_used(self):
        swapped = self.pair.copy()
        swapped[1], swapped[4] = self.pair[4], self.pair[1]
        self.assert_hold(swapped, "SIGNED_ROLE_DOMAIN_MISMATCH")
        swapped = self.pair.copy()
        swapped[4] = swapped[4].replace(b'REVIEW_FIXTURE', b'HUMAN_APPROVED')
        self.assert_hold(swapped, "SIGNED_ROLE_DOMAIN_MISMATCH")

    def test_07_expired_future_and_unbounded_lease_refused(self):
        for bad in (sample_intent(issuedAtMs=1001),
                    sample_intent(expiresAtMs=1000),
                    sample_intent(expiresAtMs=500000),
                    sample_intent(expiresAtMs=901)):
            with self.subTest(data=bad):
                self.assert_hold(signed_pair(bad), "EXPIRED_FUTURE_OR_UNBOUNDED_LEASE")

    def test_08_other_grant_audiences_and_phases_refused(self):
        for bad in (sample_intent(audience="postapollo.identity.signin.v1"),
                    sample_intent(phase="PREPARE_GENERATE"),
                    sample_intent(action="READ_SESSION"),
                    sample_intent(phase="RESTORE"),
                    sample_intent(model="bad model")):
            with self.subTest(data=bad):
                self.assert_hold(signed_pair(bad))

    def test_09_fields_must_be_correct_types_and_lowercase_sha(self):
        for bad in (sample_intent(revision=True),
                    sample_intent(consentEpoch="12"),
                    sample_intent(requesterUid=False),
                    sample_intent(requesterReleaseSha256="A"*64),
                    sample_intent(challenge="bad!nonce"),
                    sample_intent(requesterPid=0)):
            with self.subTest(data=bad):
                self.assert_hold(signed_pair(bad))

    def test_10_invalid_public_keys_and_sizes_refused(self):
        for index, value in ((3, b"x"), (6, b""), (2, b""),
                             (0, b""), (1, b"")):
            with self.subTest(index=index):
                bad = self.pair.copy()
                bad[index] = value
                self.assert_hold(bad)

    def test_11_signatures_do_not_imply_operator_presence(self):
        for _ in range(2):
            result = verify(signed_pair())
            self.assertIs(result["humanConsentVerified"], False)
            self.assertIs(result["enrolledIssuerRootVerified"], False)
            self.assertIs(result["c5RevocationFenceGranted"], False)
            self.assertIs(result["forestDatabaseCommitAllowed"], False)

    def test_12_no_callers_can_supply_grant_or_trust_flags(self):
        bad = sample_intent()
        bad["productionAuthority"] = True
        self.assert_hold(signed_pair(bad), "EXACT_FIELDS_REQUIRED")
        self.assertFalse(hasattr(C, "issue_grant"))
        self.assertFalse(hasattr(C, "commit_response"))
        self.assertFalse(hasattr(C, "approve_human_consent"))



    def test_13_denial_constants_and_result_isolation(self):
        for name in C.NO_AUTHORITY:
            with self.subTest(name=name):
                with self.assertRaises(TypeError):
                    C.NO_AUTHORITY[name] = True
        result = verify(self.pair)
        result["productionAuthority"] = True
        result["safeActions"].append("COMMIT_GENERATE")
        fresh = verify(self.pair)
        self.assertFalse(fresh["productionAuthority"])
        self.assertEqual(fresh["safeActions"], [])

    def test_14_public_decoder_refusal_does_not_chain(self):
        for wire, reason in (
            (b'{"private":"SYNTHETIC_PRIVATE', "INVALID_JSON"),
            (b'{"private":"SYNTHETIC_PRIVATE\xff"}', "INVALID_JSON"),
            (b'[' * 1500 + b']' * 1500, "INVALID_JSON"),
            (b'{"schema":"a","schema":"b"}', "DUPLICATE_JSON_KEY"),
            (b'{"schema":NaN}', "JSON_CONSTANT_REFUSED"),
        ):
            with self.subTest(reason=reason, size=len(wire)):
                parts = self.pair.copy()
                parts[0] = wire
                with self.assertRaises(C.EvidenceHold) as caught:
                    verify(parts)
                self.assertEqual(str(caught.exception),
                                 "FOREST_B4C_EVIDENCE_HOLD // " + reason)
                self.assertIsNone(caught.exception.__cause__)
                self.assertIsNone(caught.exception.__context__)

    def test_15_canonical_serialization_and_signature_refusals_are_fixed(self):
        nested = []
        for _ in range(1500):
            nested = [nested]
        for value in ({"x": nested}, {"x": object()}, {"x": float("nan")}):
            with self.assertRaises(C.EvidenceHold) as caught:
                C.canonical_bytes(value)
            self.assertEqual(str(caught.exception),
                             "FOREST_B4C_EVIDENCE_HOLD // INVALID_CANONICAL_JSON")
            self.assertIsNone(caught.exception.__cause__)
            self.assertIsNone(caught.exception.__context__)
        parts = self.pair.copy()
        parts[2] = bytes([parts[2][0] ^ 1]) + parts[2][1:]
        with self.assertRaises(C.EvidenceHold) as caught:
            verify(parts)
        self.assertEqual(str(caught.exception),
                         "FOREST_B4C_EVIDENCE_HOLD // SIGNATURE_INVALID")
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)


if __name__ == "__main__":
    unittest.main()
