"""DOC 6 deny-only native admission diagnostic tests, no real commands."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from native_admission_diagnostic_v0 import (
    REQUIRED, SCHEMA, inspect_evidence_claims,
)


class NativeAdmissionDiagnosticTests(unittest.TestCase):
    def assert_denied(self, report):
        self.assertEqual(report.schema, SCHEMA)
        for field in ("can_begin_sign_in", "can_cancel", "can_recover",
                      "can_connect_provider", "production_authority"):
            self.assertIs(getattr(report, field), False)

    def test_absent_evidence_denied_for_every_action(self):
        for action in ("BEGIN", "STATUS", "CANCEL", "RECOVER"):
            with self.subTest(action=action):
                report = inspect_evidence_claims(action=action, claims=None)
                self.assertEqual(report.state, "NOT_READY")
                self.assertEqual(report.missing, REQUIRED)
                self.assert_denied(report)

    def test_all_positive_claims_still_have_zero_authority(self):
        report = inspect_evidence_claims(
            action="BEGIN", claims={field: True for field in REQUIRED})
        self.assertEqual(report.missing, ())
        self.assertEqual(report.state, "NOT_READY")
        self.assert_denied(report)

    def test_each_missing_contract_is_named(self):
        for field in REQUIRED:
            claims = {name: name != field for name in REQUIRED}
            with self.subTest(field=field):
                report = inspect_evidence_claims(action="CANCEL", claims=claims)
                self.assertEqual(report.missing, (field,))
                self.assert_denied(report)

    def test_unknown_outcome_never_retries_even_with_all_claims_true(self):
        report = inspect_evidence_claims(
            action="RECOVER", claims={field: True for field in REQUIRED},
            command_outcome_unknown=True)
        self.assertEqual(report.state, "UNKNOWN_HOLD")
        self.assert_denied(report)

    def test_missing_data_with_unknown_outcome_remains_hold(self):
        report = inspect_evidence_claims(
            action="STATUS", claims={}, command_outcome_unknown=True)
        self.assertEqual(report.state, "UNKNOWN_HOLD")
        self.assertEqual(report.missing, REQUIRED)
        self.assert_denied(report)

    def test_client_authentication_boolean_is_not_an_evidence_field(self):
        for rogue in ("hostAuthenticated", "canApprove", "signedAuth",
                      "isAdmin", "token", "clientNonce"):
            with self.subTest(rogue=rogue):
                with self.assertRaises(ValueError):
                    inspect_evidence_claims(action="BEGIN", claims={rogue: True})

    def test_malformed_claim_value_cannot_promote_authority(self):
        for bad in (1, "true", None, [], {}, 0):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    inspect_evidence_claims(
                        action="BEGIN", claims={REQUIRED[0]: bad})

    def test_bad_actions_refused(self):
        for action in ("LOGIN", "LOGOUT", "begin", "", None, 0):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    inspect_evidence_claims(action=action, claims={})

    def test_bad_outcome_uncertainty_refused(self):
        for bad in (0, 1, "false", None):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    inspect_evidence_claims(
                        action="BEGIN", claims={}, command_outcome_unknown=bad)

    def test_nonmapping_refused(self):
        for bad in ([], "anything", 3, ("a", True)):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    inspect_evidence_claims(action="BEGIN", claims=bad)

    def test_diagnostic_immutable(self):
        report = inspect_evidence_claims(action="BEGIN", claims={})
        with self.assertRaises(FrozenInstanceError):
            report.production_authority = True
        self.assert_denied(report)

    def test_no_native_actuator_imports_or_calls(self):
        source = (ROOT / "services/identity/native_admission_diagnostic_v0.py"
                  ).read_text(encoding="utf-8")
        import ast
        tree = ast.parse(source)
        external = [node for node in ast.walk(tree)
                    if isinstance(node, ast.Import)]
        self.assertEqual(external, [])
        imported = [alias.name for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                    for alias in node.names]
        self.assertEqual(set(imported), {
            "annotations", "dataclass", "Mapping"})
        self.assertNotIn("socket.", source)
        self.assertNotIn("subprocess.", source)
        self.assertNotIn("SignedIdentityCommandClient(", source)
        self.assertNotIn("IdentityCommandGateway(", source)


if __name__ == "__main__":
    unittest.main()
