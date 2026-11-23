"""Identity DOC 6 protected-outcome *candidate* semantic shadow tests.

All candidate sources are caller-controlled Python fixtures. No C3e/C4b/C5
authority, native host, network connection, browser, credential or operator
gesture exists in this test.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from native_outcome_candidate_shadow_v0 import (
    CandidateRefused, OriginalCommandBinding, SCHEMA,
    inspect_candidate_once,
)

HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64
HEX_D = "d" * 64
HEX_E = "e" * 64
HEX_F = "f" * 64


def original(action="BEGIN"):
    return OriginalCommandBinding(
        attempt_id="1" * 32,
        action=action,
        request_digest=None if action == "BEGIN" else HEX_A,
        nonce_digest=HEX_B,
        host_instance_digest=HEX_C,
        seat_digest=HEX_D,
        session_digest=HEX_E,
        challenge_digest=HEX_F,
        history_digest="0" * 64,
        issuer_epoch=3,
        minimum_sequence=7,
    )


def claim(expected, result="CLAIMED_NO_EFFECT"):
    return {
        "schema": SCHEMA,
        "attemptId": expected.attempt_id,
        "action": expected.action,
        "requestDigest": expected.request_digest,
        "nonceDigest": expected.nonce_digest,
        "hostInstanceDigest": expected.host_instance_digest,
        "seatDigest": expected.seat_digest,
        "sessionDigest": expected.session_digest,
        "challengeDigest": expected.challenge_digest,
        "historyDigest": expected.history_digest,
        "issuerEpoch": expected.issuer_epoch,
        "sequence": expected.minimum_sequence,
        "claimedResult": result,
    }


class NegativeOutcomeCandidateShadowTests(unittest.TestCase):
    def assert_hold(self, report, *, calls=None):
        self.assertEqual(report.schema, SCHEMA)
        self.assertEqual(report.state, "UNKNOWN_HOLD")
        self.assertEqual(report.safe_actions, ())
        if calls is not None:
            self.assertEqual(report.lookup_count, calls)
        for attr in (
            "can_retry", "can_begin_sign_in", "can_cancel", "can_recover",
            "can_connect_provider", "original_host_authenticated",
            "original_operator_consented", "issuer_reconciled",
            "terminal_receipt_authenticated", "production_authority",
        ):
            self.assertIs(getattr(report, attr), False)

    def test_provider_absent_is_hold_with_zero_lookup(self):
        self.assert_hold(inspect_candidate_once(
            original=original(), provider=None), calls=0)

    def test_noncallable_provider_is_not_a_lookup(self):
        for value in ("provider", 1, {}, []):
            with self.subTest(provider=repr(value)):
                report = inspect_candidate_once(
                    original=original(), provider=value)
                self.assert_hold(report, calls=0)
                self.assertEqual(
                    report.reason, "INDEPENDENT_PROVIDER_NOT_AVAILABLE")

    def test_provider_exception_is_hold_with_one_call_no_retry(self):
        calls = []
        def fails(binding):
            calls.append(binding)
            raise TimeoutError("unknown remote outcome")
        result = inspect_candidate_once(original=original(), provider=fails)
        self.assert_hold(result, calls=1)
        self.assertEqual(result.reason, "PROVIDER_FAILED_OR_UNAVAILABLE")
        self.assertEqual(len(calls), 1)

    def test_matching_claimed_no_effect_remains_unknown_no_retry(self):
        expected = original()
        calls = []
        def provider(binding):
            calls.append(binding)
            return claim(expected, "CLAIMED_NO_EFFECT")
        result = inspect_candidate_once(original=expected, provider=provider)
        self.assert_hold(result, calls=1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], expected)
        self.assertEqual(result.reason, "MATCHED_CLAIM_STILL_UNTRUSTED")

    def test_all_claimed_terminal_outcomes_still_unknown(self):
        for result_name in ("CLAIMED_COMMITTED", "CLAIMED_ABORTED",
                            "CLAIMED_UNKNOWN", "CLAIMED_NO_EFFECT"):
            with self.subTest(claim=result_name):
                expected = original()
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: claim(expected, result_name))
                self.assert_hold(report, calls=1)

    def test_each_native_action_matches_only_its_original_request(self):
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            with self.subTest(action=action):
                expected = original(action)
                result = inspect_candidate_once(
                    original=expected, provider=lambda _: claim(expected))
                self.assert_hold(result, calls=1)
                self.assertEqual(result.reason, "MATCHED_CLAIM_STILL_UNTRUSTED")

    def test_wrong_issuer_epoch_sequence_rollback_conflicts(self):
        expected = original("CANCEL")
        for field, value in (
            ("issuerEpoch", 2), ("issuerEpoch", 4), ("sequence", 6)):
            with self.subTest(field=field, value=value):
                candidate = claim(expected)
                candidate[field] = value
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: candidate)
                self.assert_hold(report, calls=1)
                self.assertEqual(report.reason, "CONFLICTING_UNTRUSTED_CANDIDATE")

    def test_every_original_binding_mismatch_is_hold(self):
        expected = original("RECOVER")
        for field, value in (
            ("attemptId", "2" * 32),
            ("action", "CANCEL"),
            ("requestDigest", "9" * 64),
            ("nonceDigest", "9" * 64),
            ("hostInstanceDigest", "9" * 64),
            ("seatDigest", "9" * 64),
            ("sessionDigest", "9" * 64),
            ("challengeDigest", "9" * 64),
            ("historyDigest", "9" * 64),
        ):
            with self.subTest(field=field):
                candidate = claim(expected)
                candidate[field] = value
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: candidate)
                self.assert_hold(report, calls=1)
                self.assertEqual(report.reason, "CONFLICTING_UNTRUSTED_CANDIDATE")

    def test_extra_authority_claim_refused_without_fallback(self):
        for extra in ("productionAuthority", "safeToRetry", "hostAuthenticated",
                      "operatorConsented", "signedReceipt", "canBeginSignIn",
                      "accessToken", "trustedSource"):
            with self.subTest(extra=extra):
                expected = original()
                candidate = claim(expected)
                candidate[extra] = True
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: candidate)
                self.assert_hold(report, calls=1)
                self.assertEqual(report.reason, "MALFORMED_UNTRUSTED_CANDIDATE")

    def test_missing_fields_and_wrong_schema_refused(self):
        expected = original()
        for key in claim(expected):
            with self.subTest(missing=key):
                candidate = claim(expected)
                del candidate[key]
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: candidate)
                self.assert_hold(report, calls=1)
                self.assertEqual(report.reason, "MALFORMED_UNTRUSTED_CANDIDATE")
        candidate = claim(expected)
        candidate["schema"] = "other-purpose"
        report = inspect_candidate_once(
            original=expected, provider=lambda _: candidate)
        self.assert_hold(report, calls=1)

    def test_invalid_types_and_malformed_digests_refused(self):
        expected = original()
        for field, invalid in (
            ("attemptId", "Z" * 32), ("action", "LOGIN"),
            ("nonceDigest", "X" * 64), ("historyDigest", "0" * 63),
            ("sequence", True), ("issuerEpoch", True),
            ("claimedResult", "AUTHENTICATED"),
            ("requestDigest", False),
        ):
            with self.subTest(field=field):
                candidate = claim(expected)
                candidate[field] = invalid
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: candidate)
                self.assert_hold(report, calls=1)
                self.assertEqual(report.reason, "MALFORMED_UNTRUSTED_CANDIDATE")

    def test_non_dict_provider_result_refused(self):
        expected = original()
        for candidate in (None, [], (), "result", b"result", 4):
            with self.subTest(candidate=repr(candidate)):
                report = inspect_candidate_once(
                    original=expected, provider=lambda _: candidate)
                self.assert_hold(report, calls=1)
                self.assertEqual(report.reason, "MALFORMED_UNTRUSTED_CANDIDATE")

    def test_invalid_original_binding_is_refused_before_lookup(self):
        valid = original()
        for field, value in (
            ("attempt_id", "A" * 32), ("action", "LOGIN"),
            ("request_digest", HEX_A), ("issuer_epoch", 0),
            ("minimum_sequence", 0), ("minimum_sequence", True),
            ("nonce_digest", "x"), ("seat_digest", None),
        ):
            with self.subTest(field=field):
                fields = {name: getattr(valid, name) for name in
                          valid.__dataclass_fields__}
                fields[field] = value
                with self.assertRaises(CandidateRefused):
                    OriginalCommandBinding(**fields)

    def test_bad_original_object_never_calls_provider(self):
        calls = []
        with self.assertRaises(CandidateRefused):
            inspect_candidate_once(
                original={"attempt": "self-report"},
                provider=lambda _: calls.append(True))
        self.assertEqual(calls, [])

    def test_result_is_immutable_and_has_no_settlement_api(self):
        expected = original()
        report = inspect_candidate_once(
            original=expected, provider=lambda _: claim(expected))
        with self.assertRaises(FrozenInstanceError):
            report.production_authority = True
        self.assertFalse(hasattr(report, "settle"))
        self.assertFalse(hasattr(report, "clear_hold"))
        self.assertFalse(hasattr(report, "approve"))
        self.assertFalse(hasattr(report, "retry"))
        self.assert_hold(report, calls=1)

    def test_no_native_actuator_or_issuer_imports(self):
        source = (ROOT / "services/identity/native_outcome_candidate_shadow_v0.py"
                  ).read_text(encoding="utf-8")
        root = ast.parse(source)
        imported = []
        for node in ast.walk(root):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        for banned in ("socket", "sqlite3", "subprocess", "cryptography",
                       "desktop_signed_command_client_v0",
                       "desktop_command_gateway_v0",
                       "local_command_outcome_hold_reference_v0"):
            self.assertNotIn(banned, imported)
        self.assertNotIn("sendall(", source)
        self.assertNotIn("safe_to_retry=True", source)
        self.assertNotIn("production_authority=True", source)


if __name__ == "__main__":
    unittest.main()
