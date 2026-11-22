#!/usr/bin/env python3
"""Forest B4c // two already-reviewed fixtures share an exact intent (NO GRANT)."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load_exact(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise RuntimeError("EXACT_FOREST_FIXTURE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = load_exact("forest_b4c_fixture_bridge",
               "tests/connections/forest_b4c_fixture_interop.py")
SAMPLES = load_exact("forest_b4c_existing_signed_tests",
                     "tests/connections/test_connections_forest_c5_signed_role_preflight.py")
S = B.SIGNED
F = B.FENCE


class ForestB4cFixtureInteropTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.fence = F.UntrustedFenceReference(Path(self.tmp.name) / "issuer.sqlite")
        self.addCleanup(self.fence.close)
        self.fence.seed_test_scope("alice", "treeA", 12)

    def translate(self, parts=None, now=1000):
        return B.fixture_intent_from_signed_bytes_only(
            *(parts if parts is not None else SAMPLES.signed_pair()), now_ms=now,
        )

    def test_01_same_signed_commit_binds_both_reference_contracts(self):
        parts = SAMPLES.signed_pair()
        fixture, diag = self.translate(parts)
        self.assertEqual(fixture["model"], "qwen3:1.7b")
        self.assertEqual(fixture["epoch"], 12)
        self.assertEqual(fixture["expiresAt"], 1200)
        self.assertEqual(fixture["issuerWitness"],
                         hashlib.sha256(parts[0]).hexdigest())
        self.assertEqual(fixture["attempt"], "a123")
        self.assertEqual(fixture["request"], "r123")
        self.assertEqual(fixture["grant"], "g123")
        self.assertEqual(fixture["revision"], 4)
        self.assertEqual(diag["safeActions"], [])
        for k in S.NO_AUTHORITY:
            self.assertIs(diag[k], False, k)

    def test_02_admit_first_revocation_cannot_ack_pending(self):
        f, _ = self.translate()
        permit = self.fence.prepare_test_only(f, now=1000)
        self.assertGreater(permit, 0)
        self.assertEqual(
            self.fence.request_revocation_test_only("alice", "treeA", 12),
            "REVOCATION_WAITING_FOR_FENCE")
        self.assertEqual(self.fence.mark_unknown_on_recovery_test_only(), 1)
        self.assertEqual(
            self.fence.request_revocation_test_only("alice", "treeA", 12),
            "REVOCATION_WAITING_FOR_FENCE")
        with self.assertRaises(F.FenceHold):
            self.fence.prepare_test_only(f, now=1000)

    def test_03_revocation_first_refuses_exact_signed_fixture(self):
        f, _ = self.translate()
        self.assertEqual(
            self.fence.request_revocation_test_only("alice", "treeA", 12),
            "SIMULATED_REVOCATION_ACK")
        with self.assertRaisesRegex(F.FenceHold, "SCOPE_REVOKED"):
            self.fence.prepare_test_only(f, now=1000)

    def test_04_all_reserved_attempt_and_binding_fields_preserved(self):
        original, _ = self.translate()
        for field, value in (
            ("principal", "bob"), ("tree", "otherTree"),
            ("userTurn", "u200"), ("attempt", "a200"),
            ("request", "r200"), ("grant", "g200"),
            ("model", "hf.co/models/qwen3:1.7b"), ("revision", 5),
            ("consentEpoch", 13), ("requesterReleaseSha256", "c" * 64),
            ("commitHostReleaseSha256", "d" * 64),
            ("requesterPid", 3333), ("requesterStartTicks", 22222),
            ("requesterUid", 2000), ("seatEpoch", 46),
            ("challenge", "nonce_new456789abcd"), ("issuedAtMs", 800),
            ("expiresAtMs", 1100),
        ):
            with self.subTest(field=field):
                change, _ = self.translate(
                    SAMPLES.signed_pair(SAMPLES.sample_intent(**{field: value})))
                self.assertNotEqual(change["issuerWitness"], original["issuerWitness"])
                if field in ("principal", "tree", "userTurn", "attempt", "request",
                             "grant", "model", "revision", "consentEpoch", "expiresAtMs"):
                    # These appear as *exact*, not normalized, legacy values.
                    mapped = {"consentEpoch": "epoch",
                              "expiresAtMs": "expiresAt"}.get(field, field)
                    self.assertEqual(change[mapped], value)

    def test_05_existing_signature_cannot_approve_mutated_commit(self):
        base = SAMPLES.signed_pair()
        for field, value in (
            ("principal", "eve"), ("tree", "treeB"), ("model", "llama3:8b"),
            ("attempt", "a999"), ("consentEpoch", 14), ("seatEpoch", 60),
            ("requesterReleaseSha256", "e" * 64),
        ):
            with self.subTest(field=field):
                corrupted = base.copy()
                corrupted[0] = S.canonical_bytes(
                    SAMPLES.sample_intent(**{field: value}))
                with self.assertRaises(S.EvidenceHold):
                    self.translate(corrupted)

    def test_06_exact_model_grammar_agrees_and_preserves_colons(self):
        self.assertEqual(S.MODEL.pattern, F.MODEL_SYNTAX.pattern)
        self.assertEqual(S.MODEL.flags, F.MODEL_SYNTAX.flags)
        for model in ("qwen3:1.7b", "hf.co/user/model:Q4_K_M",
                      "llama3.2:1b", "granite4:small-h"):
            with self.subTest(model=model):
                value, _ = self.translate(
                    SAMPLES.signed_pair(SAMPLES.sample_intent(model=model)))
                self.assertEqual(value["model"], model)
                self.assertTrue(F._canonical_intent(value))

    def test_07_ambiguous_model_format_and_wrong_phase_refused(self):
        for changed in (
            {"model": "name with spaces"}, {"model": "model\ninjected"},
            {"model": "💥"}, {"phase": "PREPARE_GENERATE"},
            {"action": "READ_SESSION"},
            {"audience": "postapollo.identity.signin.v1"},
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(S.EvidenceHold):
                    self.translate(SAMPLES.signed_pair(
                        SAMPLES.sample_intent(**changed)))

    def test_08_unenrolled_keys_can_sign_but_cannot_grant_any_action(self):
        for _ in range(3):
            fixture, diagnostic = self.translate(SAMPLES.signed_pair())
            self.assertTrue(B.FIXTURE_ONLY)
            self.assertFalse(B.PRODUCTION_AUTHORITY)
            self.assertTrue(diagnostic["issuerRolesAreFixtureControlled"])
            self.assertFalse(diagnostic["humanConsentVerified"])
            self.assertFalse(diagnostic["installedRequesterVerified"])
            self.assertFalse(diagnostic["forestDatabaseCommitAllowed"])
            self.assertFalse(diagnostic["c5RevocationFenceGranted"])
            self.assertFalse(diagnostic["productionAuthority"])
            self.assertNotIn("productionAuthority", fixture)

    def test_09_expiry_is_milliseconds_not_legacy_seconds(self):
        fixture, _ = self.translate()
        self.assertEqual(fixture["expiresAt"], 1200)
        with self.assertRaises(S.EvidenceHold):
            self.translate(SAMPLES.signed_pair(), now=1200)
        with self.assertRaises(F.FenceHold):
            self.fence.prepare_test_only(fixture, now=1200)
        with self.assertRaises(S.EvidenceHold):
            self.translate(SAMPLES.signed_pair(
                SAMPLES.sample_intent(expiresAtMs=900)))

    def test_10_wrong_signed_key_or_reviewer_domain_refused(self):
        base = SAMPLES.signed_pair()
        for mutate in ("alias", "swapped", "bad_sig"):
            changed = base.copy()
            if mutate == "alias":
                changed[6] = changed[3]
            elif mutate == "swapped":
                changed[1], changed[4] = changed[4], changed[1]
            else:
                changed[5] = b"\x00" * 64
            with self.subTest(mutate=mutate):
                with self.assertRaises(S.EvidenceHold):
                    self.translate(changed)

    def test_11_no_implicit_READ_or_tools_from_generate_signature(self):
        _, diag = self.translate()
        for forbidden in ("forestReadSessionAllowed", "forestToolExecutionAllowed",
                          "forestDatabaseCommitAllowed", "productionAuthority"):
            self.assertFalse(diag[forbidden])
        self.assertEqual(diag["safeActions"], [])

    def test_12_legacy_wrong_model_refused_without_sanitization(self):
        valid, _ = self.translate()
        for model in ("space bad", "", "❤️", "bad\nname", "@" * 200):
            with self.subTest(model=model):
                bad = dict(valid, model=model)
                with self.assertRaisesRegex(F.FenceHold, "INVALID_MODEL_IDENTIFIER"):
                    F._canonical_intent(bad)


if __name__ == "__main__":
    unittest.main()
