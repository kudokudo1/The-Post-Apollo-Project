#!/usr/bin/env python3
"""DOC 1: signed test custodian denials cannot authorize Identity Sign-In."""
from __future__ import annotations

import base64
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "tests/connections/c3e_release_trust"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3E_CUSTODIAN_TEST_SOURCE_MISSING")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


M = _load("c3e_signed_custodian_candidate_under_test",
          HERE / "C3eSignedCustodianCandidateCI.py")
S = _load("c3e_signed_candidate_existing_protected_boundary",
          HERE / "C3eStorageIndependentTrustBoundary.py")


class SignedCustodianCandidateNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if (sys.platform != "linux" or os.geteuid() != 0
                or os.environ.get("GITHUB_ACTIONS") != "true"
                or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
            raise RuntimeError("C3E_CUSTODIAN_TEST_HOSTED_ROOT_CI_ONLY")

    def setUp(self):
        self.key = Ed25519PrivateKey.generate()   # CI only; never enrolled
        self.pub = self.key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw)
        self.request = {
            "schema": M.REQUEST_SCHEMA, "purpose": M.PURPOSE,
            "requestId": "01"*16, "challengeHex": "02"*32,
            "epoch": "03"*16, "previousHeadSha256": "04"*32,
            "previousSequence": 10,
        }
        self.resp = self.sign(self.request)

    def sign(self, request=None, *, key=None, **overrides):
        request = self.request if request is None else request
        body = {
            **request, "schema": M.RESPONSE_SCHEMA,
            "signerRole": M.ROLE,
            "kind": "UNAVAILABLE",
            "settlement": "NONE",
            "challengeState": "UNKNOWN",
            "observedHeadSha256": request["previousHeadSha256"],
            "observedSequence": request["previousSequence"],
            **overrides,
        }
        signer = self.key if key is None else key
        sig = signer.sign(
            b"POSTAPOLLO_C3E_CUSTODIAN_CANDIDATE_CI_V1\x00"
            + M._canonical(body))
        return {
            **body,
            "signatureB64url": base64.urlsafe_b64encode(sig)
                                  .decode("ascii").rstrip("="),
        }

    def inspect(self, req=None, resp=None, pub=None):
        return M.inspect_ci_only(
            request=self.request if req is None else req,
            response=self.resp if resp is None else resp,
            test_public_key=self.pub if pub is None else pub)

    def pair(self, left=None, right=None, req=None, pub=None):
        return M.compare_signed_candidates_ci_only(
            request=self.request if req is None else req,
            left=self.resp if left is None else left,
            right=self.resp if right is None else right,
            test_public_key=self.pub if pub is None else pub)

    def denied(self, record, *, pair=False):
        self.assertEqual(record["schema"], M.REPORT_SCHEMA)
        self.assertEqual(record["status"], M.STATUS)
        self.assertEqual(record["next"],
                         "HOLD_NO_INDEPENDENT_CUSTODIAN_OR_TERMINAL_SETTLEMENT")
        self.assertIsNone(record["winner"])
        self.assertEqual(record["safeActions"], [])
        for k in M.DENIED:
            self.assertIs(record[k], False, k)
        self.assertIs(record["cryptographicTestSignaturesValid"
                             if pair else "cryptographicTestSignatureValid"], True)

    def test_01_signature_verifies_but_has_no_enrolled_root(self):
        out = self.inspect()
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_EQUAL_NOT_TRUSTED_HOLD")
        self.denied(out)

    def test_02_old_signed_candidate_is_stale_not_current(self):
        out = self.inspect(resp=self.sign(observedSequence=9))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_STALE_HEAD_HOLD")
        self.denied(out)

    def test_03_newer_signed_candidate_is_unverified_not_grant(self):
        out = self.inspect(resp=self.sign(observedSequence=11))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_AHEAD_UNVERIFIED_HOLD")
        self.denied(out)

    def test_04_equal_sequence_different_signed_head_is_fork(self):
        out = self.inspect(resp=self.sign(observedHeadSha256="a"*64))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_RESPONSE_EQUAL_SEQUENCE_FORK_HOLD")
        self.denied(out)

    def test_05_two_valid_signatures_from_one_test_key_fork(self):
        left = self.sign(observedHeadSha256="a"*64, observedSequence=11)
        right = self.sign(observedHeadSha256="b"*64, observedSequence=11)
        out = self.pair(left, right)
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_CANDIDATES_SAME_SEQUENCE_FORK_HOLD")
        self.denied(out, pair=True)

    def test_06_same_signed_report_twice_is_not_two_independent_witnesses(self):
        out = self.pair()
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_CANDIDATES_MATCH_STILL_NOT_QUORUM_HOLD")
        self.denied(out, pair=True)

    def test_07_signed_candidates_different_sequence_no_winner(self):
        out = self.pair(self.sign(observedSequence=11),
                        self.sign(observedSequence=12))
        self.assertEqual(out["relation"],
                         "SIGNED_TEST_CANDIDATES_DIFFERENT_SEQUENCE_HOLD")
        self.denied(out, pair=True)

    def test_08_wrong_unenrolled_public_key_fails_signature(self):
        other = Ed25519PrivateKey.generate()
        pub = other.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        with self.assertRaisesRegex(M.Refused, "BAD_TEST_SIGNATURE"):
            self.inspect(pub=pub)

    def test_09_body_tamper_after_signing_refused(self):
        forged = dict(self.resp, observedHeadSha256="a"*64)
        with self.assertRaisesRegex(M.Refused, "BAD_TEST_SIGNATURE"):
            self.inspect(resp=forged)

    def test_10_query_challenge_replacement_fails_exact_binding(self):
        req = dict(self.request, challengeHex="f"*64)
        with self.assertRaisesRegex(M.Refused, "REQUEST_BINDING"):
            self.inspect(req=req)

    def test_11_query_request_id_replay_fails_binding(self):
        req = dict(self.request, requestId="a"*32)
        with self.assertRaisesRegex(M.Refused, "REQUEST_BINDING"):
            self.inspect(req=req)

    def test_12_query_epoch_replacement_fails_binding(self):
        req = dict(self.request, epoch="b"*32)
        with self.assertRaisesRegex(M.Refused, "REQUEST_BINDING"):
            self.inspect(req=req)

    def test_13_query_purpose_spoof_refused(self):
        req = dict(self.request, purpose="postapollo.timew.restore")
        with self.assertRaisesRegex(M.Refused, "QUERY_DOMAIN"):
            self.inspect(req=req)

    def test_14_response_cross_purpose_refused_even_if_resigned(self):
        res = self.sign(purpose="postapollo.hospital.staffing")
        with self.assertRaisesRegex(M.Refused, "REQUEST_BINDING"):
            self.inspect(resp=res)

    def test_15_bad_signer_role_cannot_be_relabelled_root(self):
        res = self.sign(signerRole="PRODUCTION_ROOT")
        with self.assertRaisesRegex(M.Refused, "NOT_DENIAL_ONLY"):
            self.inspect(resp=res)

    def test_16_signed_comitted_authorization_claim_refused(self):
        res = self.sign(kind="COMMITTED")
        with self.assertRaisesRegex(M.Refused, "NOT_DENIAL_ONLY"):
            self.inspect(resp=res)

    def test_17_signed_spent_challenge_is_not_protected_spend(self):
        res = self.sign(challengeState="CONSUMED")
        with self.assertRaisesRegex(M.Refused, "NOT_DENIAL_ONLY"):
            self.inspect(resp=res)

    def test_18_signed_settlement_is_not_approved_terminal_receipt(self):
        res = self.sign(settlement="COMMITTED")
        with self.assertRaisesRegex(M.Refused, "NOT_DENIAL_ONLY"):
            self.inspect(resp=res)

    def test_19_extra_positive_authority_field_refused(self):
        res = self.sign(signInAllowed=True)
        with self.assertRaisesRegex(M.Refused, "RESPONSE_FIELDS"):
            self.inspect(resp=res)

    def test_20_padding_noncanonical_signature_refused(self):
        res = dict(self.resp, signatureB64url=self.resp["signatureB64url"]+"==")
        with self.assertRaisesRegex(M.Refused, "CANONICAL_BASE64URL"):
            self.inspect(resp=res)

    def test_21_mutated_signature_detected(self):
        original = self.resp["signatureB64url"]
        res = dict(self.resp, signatureB64url=("A" if original[0] != "A" else "B") + original[1:])
        with self.assertRaisesRegex(M.Refused, "BAD_TEST_SIGNATURE"):
            self.inspect(resp=res)

    def test_22_boolean_sequence_is_not_int(self):
        res = self.sign(observedSequence=True)
        with self.assertRaisesRegex(M.Refused, "NOT_DENIAL_ONLY"):
            self.inspect(resp=res)

    def test_23_invalid_query_sequence_is_refused(self):
        req = dict(self.request, previousSequence=0)
        with self.assertRaisesRegex(M.Refused, "QUERY_DOMAIN"):
            self.inspect(req=req)

    def test_24_short_public_key_refused(self):
        with self.assertRaisesRegex(M.Refused, "EXACT_TEST_PUBLIC_KEY"):
            self.inspect(pub=b"\x00"*31)

    def test_25_unknown_positive_response_extension_refused(self):
        res = dict(self.resp, currentHistoryAuthorized=True)
        with self.assertRaisesRegex(M.Refused, "RESPONSE_FIELDS"):
            self.inspect(resp=res)

    def test_26_no_prod_admission_even_with_valid_test_signature(self):
        self.denied(self.inspect())
        with self.assertRaisesRegex(M.Refused, "NO_OPERATOR_ENROLLED_ROOT"):
            M.protected_admission(self.resp)

    def test_27_original_protected_mode_has_no_local_fallback(self):
        protected = S.TrustBoundary(required_mode=S.PROTECTED_REQUIRED)
        status = protected.protected_required_status()
        self.assertEqual(status["status"], S.STATUS_HOLD)
        with self.assertRaisesRegex(S.Refused, "HOLD_NO_FALLBACK"):
            protected.read_current_snapshot()

    def test_28_ci_guard_blocks_self_hosted_false_authority(self):
        with mock.patch.dict(os.environ, {"RUNNER_ENVIRONMENT":"self-hosted"}):
            with self.assertRaisesRegex(M.Refused, "DISPOSABLE_ROOT_CI_ONLY"):
                self.inspect()

    def test_29_query_unknown_extension_refused(self):
        req = dict(self.request, forceTrusted=True)
        with self.assertRaisesRegex(M.Refused, "QUERY_FIELDS"):
            self.inspect(req=req)

    def test_30_valid_response_from_different_key_does_not_match_test_pin(self):
        different = Ed25519PrivateKey.generate()
        res = self.sign(key=different)
        with self.assertRaisesRegex(M.Refused, "BAD_TEST_SIGNATURE"):
            self.inspect(resp=res)

    def test_31_hostile_keys_refused_without_comparison(self):
        class HostileKey(str):
            __hash__ = str.__hash__
            def __eq__(self, other):
                raise AssertionError("caller equality must not execute")

        for target in ("request", "response"):
            original = self.request if target == "request" else self.resp
            # Construct an exact-size dict with a single non-plain key.
            bad = {HostileKey(k) if k == "schema" else k: v
                   for k, v in original.items()}
            with self.subTest(target=target):
                with self.assertRaisesRegex(M.Refused, "FIELDS_REFUSED"):
                    self.inspect(**({"req": bad} if target == "request"
                                    else {"resp": bad}))

    def test_32_hostile_values_refused_before_equality(self):
        class HostileValue(str):
            def __eq__(self, other):
                raise AssertionError("caller equality must not execute")
            def __ne__(self, other):
                raise AssertionError("caller inequality must not execute")

        for key in self.request:
            with self.subTest(request=key):
                with self.assertRaisesRegex(M.Refused, "QUERY_DOMAIN"):
                    self.inspect(req=dict(self.request, **{key: HostileValue("x")}))
        for key in self.resp:
            with self.subTest(response=key):
                with self.assertRaises(M.Refused):
                    self.inspect(resp=dict(self.resp, **{key: HostileValue("x")}))
        with self.assertRaises(M.Refused):
            self.pair(right=dict(self.resp, kind=HostileValue("UNAVAILABLE")))

    def test_33_denial_defaults_and_signature_errors_remain_fixed(self):
        with self.assertRaises(TypeError):
            M.DENIED["productionSignInAllowed"] = True
        out = self.inspect()
        out["productionSignInAllowed"] = True
        out["safeActions"].append("SIGN_IN")
        self.denied(self.inspect())
        self.denied(self.pair(), pair=True)
        with self.assertRaisesRegex(M.Refused, "BAD_TEST_SIGNATURE") as caught:
            self.inspect(resp=dict(self.resp, observedHeadSha256="a"*64))
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)
        with mock.patch.object(M.base64, "urlsafe_b64decode",
                               side_effect=ValueError("private fixture")):
            with self.assertRaisesRegex(M.Refused, "SIGNATURE_MALFORMED") as caught:
                self.inspect()
        self.assertIsNone(caught.exception.__cause__)
        self.assertIsNone(caught.exception.__context__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
