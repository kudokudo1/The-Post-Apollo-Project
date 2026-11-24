#!/usr/bin/env python3
"""DOC 3 Forest C5 boundary: reject local fallback, fake trust and unsigned session."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from services.connections.forest import ForestC5SignedEvidencePreflight as S  # noqa
from services.connections.forest import ForestC5AuthorityBoundary as C  # noqa


def _original_samples():
    spec = importlib.util.spec_from_file_location(
        "forest_c5_original_samples_boundary",
        ROOT / "tests/connections/test_connections_forest_c5_signed_role_preflight.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("SIGNED_ROLE_SAMPLE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SAMPLES = _original_samples()


class ForestC5StorageIndependentBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.intent = SAMPLES.sample_intent(request="r_0123456789abcdef")
        self.intentwire = S.canonical_bytes(self.intent)
        self.binding = {
            "owner_key": self.intent["principal"],
            "tree_key": self.intent["tree"],
            "session_id": "sessionA",
            "user_turn_id": self.intent["userTurn"],
            "attempt_id": self.intent["attempt"],
            "request_id": self.intent["request"],
            "model_key": self.intent["model"],
            "expected_revision": self.intent["revision"],
        }
        self.local = C.ForestC5AuthorityBoundary(required_mode=C.MODE_REFERENCE)
        self.protected = C.ForestC5AuthorityBoundary(required_mode=C.MODE_PROTECTED)

    def ref(self, binding=None, wire=None):
        return self.local.inspect_reference_binding(
            self.intentwire if wire is None else wire,
            self.binding if binding is None else binding,
        )

    def hold(self, reason, binding=None, wire=None):
        with self.assertRaises(C.ForestC5Hold) as captured:
            self.ref(binding=binding, wire=wire)
        self.assertIn(reason, str(captured.exception))

    def assert_denied(self, result):
        self.assertEqual(result["safeActions"], [])
        for field in C.NO_AUTHORITY:
            self.assertIs(result[field], False, field)

    def test_01_protected_mode_returns_only_unavailable_hold(self):
        status = self.protected.status()
        self.assertEqual(status["status"], C.STATUS_HOLD)
        self.assertEqual(status["requiredMode"], C.MODE_PROTECTED)
        self.assert_denied(status)

    def test_02_development_mode_is_not_trusted_custody(self):
        status = self.local.status()
        self.assertEqual(status["status"], C.STATUS_HOLD)
        self.assert_denied(status)

    def test_03_matching_b4c_fields_still_missing_signed_session(self):
        result = self.ref()
        self.assertEqual(result["status"], C.STATUS_REFERENCE)
        self.assertTrue(result["signedIntentMissingForestSessionId"])
        self.assertTrue(result["bindingSourceCallerControlled"])
        self.assertFalse(result["forestSessionIdentitySigned"])
        self.assert_denied(result)

    def test_04_two_different_sessions_cannot_be_cryptographically_distinguished(self):
        a = self.ref()
        b = self.ref(binding=dict(self.binding, session_id="sessionB"))
        self.assertEqual(a["intentSha256ObservedUntrusted"],
                         b["intentSha256ObservedUntrusted"])
        self.assertNotEqual(a["forestBindingSha256ObservedUntrusted"],
                            b["forestBindingSha256ObservedUntrusted"])
        self.assertTrue(b["signedIntentMissingForestSessionId"])
        self.assert_denied(b)

    def test_05_mismatched_signed_forest_fields_refuse(self):
        for field, replacement in (
            ("owner_key", "bob"), ("tree_key", "treeB"),
            ("user_turn_id", "t999"), ("attempt_id", "a999"),
            ("request_id", "r_9876543210abcdef"),
            ("model_key", "llama3:8b"), ("expected_revision", 42),
        ):
            with self.subTest(field=field):
                self.hold("REFERENCE_BINDING_MISMATCH_" + field,
                          binding=dict(self.binding, **{field: replacement}))

    def test_06_exact_binding_fields_only(self):
        for bad in (
            dict(self.binding, productionAuthority=True),
            {k: v for k, v in self.binding.items() if k != "session_id"},
        ):
            self.hold("EXACT_FOREST_BINDING_FIELDS_REQUIRED", binding=bad)
        self.hold("EXACT_FOREST_BINDING_FIELDS_REQUIRED", binding=[])

    def test_07_boolean_revision_never_integer(self):
        self.hold("INVALID_EXPECTED_REVISION",
                  binding=dict(self.binding, expected_revision=True))
        self.hold("INVALID_EXPECTED_REVISION",
                  binding=dict(self.binding, expected_revision=-1))

    def test_08_malformed_owner_or_session_rejected(self):
        self.hold("INVALID_owner_key",
                  binding=dict(self.binding, owner_key="a/b"))
        self.hold("INVALID_session_id",
                  binding=dict(self.binding, session_id="bad session"))
        self.hold("INVALID_session_id",
                  binding=dict(self.binding, session_id=None))

    def test_09_request_identifier_length_enforced(self):
        self.hold("FOREST_REQUEST_ID_LENGTH_MISMATCH",
                  binding=dict(self.binding, request_id="short"))
        self.hold("INVALID_request_id",
                  binding=dict(self.binding, request_id="contains/slash"))

    def test_10_model_identifier_grammar_not_sanitized(self):
        self.assert_denied(self.ref())
        self.hold("INVALID_MODEL_KEY",
                  binding=dict(self.binding, model_key="qwen3 model"))
        self.hold("INVALID_MODEL_KEY",
                  binding=dict(self.binding, model_key=True))

    def test_11_original_signed_intent_noncanonical_refused(self):
        bad = self.intentwire.replace(b',"attempt":', b', "attempt":')
        self.assertNotEqual(bad, self.intentwire)
        self.hold("UNTRUSTED_INTENT_INVALID", wire=bad)

    def test_12_duplicate_or_unknown_intent_keys_refused(self):
        self.hold("UNTRUSTED_INTENT_INVALID",
                  wire=b'{"schema":"a","schema":"b"}')
        self.hold("UNTRUSTED_INTENT_INVALID",
                  wire=S.canonical_bytes(dict(self.intent, fakePermit=True)))

    def test_13_wrong_phase_action_or_audience_refused(self):
        for update in (
            {"phase": "PREPARE_GENERATE"},
            {"action": "READ_SESSION"},
            {"audience": "postapollo.timew.restore.v1"},
        ):
            with self.subTest(update=update):
                self.hold("UNTRUSTED_INTENT_INVALID",
                          wire=S.canonical_bytes(dict(self.intent, **update)))

    def test_14_expired_intent_can_only_be_inspected_not_authorized(self):
        self.assertGreater(50000, self.intent["expiresAtMs"])
        result = self.ref()
        self.assert_denied(result)
        self.assertFalse(result["forestProtectedTerminalReconciled"])

    def test_15_unknown_mode_is_rejected(self):
        for mode in ("PRODUCTION", "", True, None):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(C.ForestC5Hold, "UNKNOWN_TRUST_MODE"):
                    C.ForestC5AuthorityBoundary(required_mode=mode)

    def test_16_fake_backend_local_ledger_and_remote_endpoint_refused(self):
        fake = object()
        for parameter in (
            {"backend": fake}, {"local_ledger": fake},
            {"remote_endpoint": "https://trusted.example.invalid"},
            {"trusted_root": "f" * 64},
        ):
            with self.subTest(parameter=parameter):
                with self.assertRaisesRegex(C.ForestC5Hold,
                                            "CALLER_PROVIDED_TRUST_SOURCE_REFUSED"):
                    C.ForestC5AuthorityBoundary(
                        required_mode=C.MODE_PROTECTED, **parameter)

    def test_17_protected_mode_refuses_reference_inspection(self):
        with self.assertRaisesRegex(
                C.ForestC5Hold, "PROTECTED_MODE_REFUSES_UNTRUSTED"):
            self.protected.inspect_reference_binding(self.intentwire, self.binding)

    def test_18_all_semantic_operations_fail_closed_in_both_modes(self):
        methods = (
            "read_current_trust_snapshot", "prepare_generate",
            "acquire_commit_permit", "lookup_terminal_outcome",
            "settle_terminal_receipt", "request_revocation",
            "authorize_read_session", "authorize_list_sessions",
            "authorize_disclose_session_titles", "authorize_tool_execution",
            "production_admission",
        )
        for obj in (self.local, self.protected):
            for name in methods:
                with self.subTest(mode=obj.status()["requiredMode"], operation=name):
                    with self.assertRaises(C.ForestC5Hold):
                        getattr(obj, name)(self.binding, trusted=True)

    def test_19_no_mutation_of_shared_denial_flags(self):
        with self.assertRaises(TypeError):
            C.NO_AUTHORITY["forestDatabaseCommitAllowed"] = True
        with self.assertRaises(TypeError):
            C.SIGNED_EQUIVALENTS["session_id"] = "sessionId"

    def test_20_mutating_diagnostic_cannot_change_next_result(self):
        result = self.ref()
        result["productionAuthority"] = True
        result["safeActions"].append("COMMIT_GENERATE")
        fresh = self.ref()
        self.assert_denied(fresh)
        self.assertFalse(self.protected.status()["productionAuthority"])


    def test_21_listing_and_title_entitlements_have_distinct_refusals(self):
        expected = (
            ("authorize_read_session", "READ_SESSION_SEPARATE_PROTECTED_POLICY_REQUIRED"),
            ("authorize_list_sessions", "LIST_SESSIONS_SEPARATE_PROTECTED_POLICY_REQUIRED"),
            ("authorize_disclose_session_titles", "SESSION_TITLES_SEPARATE_PROTECTED_CONSENT_REQUIRED"),
        )
        for authority in (self.local, self.protected):
            for method, code in expected:
                with self.subTest(mode=authority.status()["requiredMode"], action=method):
                    with self.assertRaisesRegex(C.ForestC5Hold, code):
                        getattr(authority, method)()

    def test_22_forged_single_session_read_cannot_upgrade_to_enumeration(self):
        forged = {
            "action": "READ_SESSION", "requestId": "r_0123456789abcdef",
            "sessionId": "secretSession", "authenticated": True,
            "approved": True, "permissionGranted": True,
            "safeActions": ["LIST_SESSIONS"],
        }
        for authority in (self.local, self.protected):
            with self.assertRaisesRegex(
                C.ForestC5Hold, "LIST_SESSIONS_SEPARATE_PROTECTED_POLICY_REQUIRED"
            ) as refusal:
                authority.authorize_list_sessions(forged)
            self.assertNotIn("secretSession", str(refusal.exception))
            self.assertFalse(authority.status()["forestListSessionsPermissionGranted"])

    def test_23_forged_listing_grant_cannot_upgrade_to_private_title_read(self):
        forged = {
            "action": "LIST_SESSIONS", "treeKey": "CHERRY",
            "generation": 99, "requestId": "r_0123456789abcdef",
            "sourceAuthenticated": True, "permissionGranted": True,
            "canReadSession": True, "mayDiscloseTitles": True,
            "private_title": "SYNTHETIC_PRIVATE_SESSION_TITLE",
        }
        for authority in (self.local, self.protected):
            with self.assertRaisesRegex(
                C.ForestC5Hold, "SESSION_TITLES_SEPARATE_PROTECTED_CONSENT_REQUIRED"
            ) as refusal:
                authority.authorize_disclose_session_titles(forged)
            self.assertNotIn(forged["private_title"], str(refusal.exception))
            self.assertFalse(authority.status()["forestPrivateTitleDisclosureGranted"])

    def test_24_valid_looking_forestw_metadata_never_sets_title_authority(self):
        fake = {
            "schema": "postapollo.forest.list-sessions-ui.v1",
            "action": "LIST_SESSIONS", "status": "READ_ONLY", "complete": True,
            "requestId": "r_0123456789abcdef", "treeKey": "CHERRY",
            "generation": 4, "sessions": [{
                "session_id": "sessionA", "tree_key": "CHERRY",
                "title": "SYNTHETIC_PRIVATE_SESSION_TITLE",
                "state": "OPEN", "revision": 3,
                "created_at_ms": 1000, "updated_at_ms": 1001,
            }],
        }
        for authority in (self.local, self.protected):
            with self.assertRaises(C.ForestC5Hold) as result:
                authority.authorize_list_sessions(fake, verified_peer=True)
            with self.assertRaises(C.ForestC5Hold) as result2:
                authority.authorize_disclose_session_titles(
                    fake, current_consent=True, authenticated_provider=True
                )
            for refusal in (result.exception, result2.exception):
                self.assertNotIn(fake["sessions"][0]["title"], str(refusal))
            self.assert_denied(authority.status())

    def test_25_diagnostic_result_mutation_does_not_promote_list_or_titles(self):
        out = self.ref()
        out["forestListSessionsPermissionGranted"] = True
        out["forestPrivateTitleDisclosureGranted"] = True
        out["safeActions"].extend(["LIST_SESSIONS", "DISCLOSE_TITLES"])
        for authority in (self.local, self.protected):
            fresh = authority.status()
            self.assert_denied(fresh)
            for name in ("authorize_list_sessions",
                         "authorize_disclose_session_titles"):
                with self.assertRaises(C.ForestC5Hold):
                    getattr(authority, name)(out)

    def test_26_global_list_and_title_authority_flags_are_immutable(self):
        for name in ("forestListSessionsPermissionGranted",
                     "forestPrivateTitleDisclosureGranted"):
            with self.subTest(name=name):
                self.assertFalse(C.NO_AUTHORITY[name])
                with self.assertRaises(TypeError):
                    C.NO_AUTHORITY[name] = True


if __name__ == "__main__":
    unittest.main()
