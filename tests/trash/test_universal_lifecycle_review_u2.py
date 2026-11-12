"""Trash++ U2: review-only, metadata-only cross-widget lifecycle gates."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/trash/universal_lifecycle_review_u2.py"
spec = importlib.util.spec_from_file_location("trashpp_lifecycle_u2", SOURCE)
u2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u2)

HASH = "a" * 64
OTHER_HASH = "f" * 64


def request(**changes):
    record = {
        "schema": u2.SCHEMA,
        "operation": "trash",
        "ownerId": "trashpp-managed-copy",
        "resourceId": "managed-item:123",
        "expectedRevision": HASH,
        "resourceScope": "managed-copy",
        "resourceState": "active",
        "revisionWitnessState": "reported_stable",
        "retentionState": "eligible",
        "dependencyState": "none_reported",
        "recoveryState": "restore_test_reported",
        "writerState": "stable_reported",
        "destinationState": "empty_reported",
        "confirmationState": "second_click_reported",
        "ownerGrantState": "reported",
    }
    record.update(changes)
    return record


class UniversalLifecycleU2Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = request()

    def check_deny(self, value, *reasons):
        self.assertEqual(value["schema"], u2.SCHEMA)
        self.assertEqual(value["state"], "DENY_ONLY_OWNER_REVIEW")
        self.assertTrue(value["readOnly"])
        self.assertTrue(value["requiresIndependentOwnerReview"])
        self.assertFalse(value["sourceBytesRead"])
        self.assertEqual(value["safeActions"], [])
        for field in ("ownerAuthorityVerified", "sourceRevisionVerified",
                      "retentionVerified", "dependenciesVerified",
                      "restoreVerified", "humanConsentVerified",
                      "captureAllowed", "trashAllowed", "restoreAllowed",
                      "burnAllowed", "productionAllowed",
                      "deleteOriginalAllowed"):
            self.assertIs(value[field], False, field)
        self.assertEqual(value["holdReasons"], sorted(set(value["holdReasons"])))
        self.assertTrue(set(reasons).issubset(set(value["holdReasons"])))

    def test_all_reported_green_still_unconditionally_denies(self):
        original = copy.deepcopy(self.fixture)
        result = u2.review(self.fixture)
        self.check_deny(result, "owner_execution_not_connected",
                        "owner_identity_not_authenticated",
                        "revision_witness_not_authenticated",
                        "permission_and_consent_not_authenticated")
        self.assertTrue(result["profileRecognized"])
        self.assertEqual(result["reviewProfile"], "disposable")
        self.assertEqual(self.fixture, original)

    def test_request_result_never_leaks_resource_id_revision_or_payload(self):
        source_id = "SECRET_MARKER_DO_NOT_ECHO_101"
        candidate = request(resourceId=source_id, expectedRevision=OTHER_HASH)
        output = str(u2.review(candidate))
        self.assertNotIn(source_id, output)
        self.assertNotIn(OTHER_HASH, output)
        self.assertNotIn("managed-item:123", output)

    def test_source_owned_weather_and_notes_cannot_be_written_through_review(self):
        for owner, profile in (("weather-events", "evidence"),
                               ("weather-dossiers", "evidence"),
                               ("demo-scrape", "evidence"),
                               ("apollo-hub-notes", "personal"),
                               ("apollo-hub-todo", "personal")):
            with self.subTest(owner=owner):
                reply = u2.review(request(ownerId=owner,
                                          resourceScope="source-owned"))
                self.check_deny(reply, "source_owned_writer_not_delegated",
                                "protected_information_owner_review_required")
                self.assertEqual(reply["reviewProfile"], profile)

    def test_high_risk_owner_families_are_never_downgraded(self):
        cases = {
            "hospital": "regulated", "company": "business",
            "social": "personal", "finance": "regulated",
            "identity": "security", "time-machine": "evidence",
        }
        for owner, risk in cases.items():
            for operation in ("trash", "restore", "burn"):
                with self.subTest(owner=owner, operation=operation):
                    reply = u2.review(request(
                        operation=operation, ownerId=owner,
                        resourceScope="source-owned",
                        resourceState="trashed" if operation != "trash"
                        else "active"))
                    self.check_deny(
                        reply, "protected_information_owner_review_required",
                        "source_owned_writer_not_delegated")
                    self.assertEqual(reply["reviewProfile"], risk)

    def test_unknown_owner_never_acquires_implied_authority(self):
        reply = u2.review(request(ownerId="fake-hospital-admin"))
        self.check_deny(reply, "owner_review_profile_missing")
        self.assertFalse(reply["profileRecognized"])
        self.assertEqual(reply["reviewProfile"], "unregistered")

    def test_spoofed_owner_scope_fails_closed(self):
        reply = u2.review(request(ownerId="hospital",
                                  resourceScope="managed-copy"))
        self.check_deny(reply, "owner_scope_mismatch",
                        "protected_information_owner_review_required")

    def test_protected_archive_is_immutable_even_under_gio_profile(self):
        reply = u2.review(request(resourceScope="protected-archive"))
        self.check_deny(reply, "owner_scope_mismatch",
                        "protected_archive_is_read_only")

    def test_explicit_untrusted_permission_report_is_not_authority(self):
        reported = u2.review(request(ownerGrantState="reported"))
        self.check_deny(reported, "permission_and_consent_not_authenticated")
        absent = u2.review(request(ownerGrantState="absent"))
        self.check_deny(absent, "owner_grant_not_reported")

    def test_lease_and_revision_reports_are_not_signatures(self):
        reply = u2.review(request(revisionWitnessState="unverified",
                                  writerState="concurrent"))
        self.check_deny(reply, "revision_not_reported_stable",
                        "writer_state_unresolved",
                        "revision_witness_not_authenticated")

    def test_retention_and_hold_refusal(self):
        for state in ("unknown", "hold", "mandatory"):
            with self.subTest(state=state):
                result = u2.review(request(retentionState=state))
                self.check_deny(result, "retention_unknown_or_protected")

    def test_dependency_refusal(self):
        for state in ("linked", "unknown"):
            with self.subTest(state=state):
                self.check_deny(
                    u2.review(request(dependencyState=state)),
                    "dependencies_unresolved")

    def test_trash_requires_active_and_tested_restore_report(self):
        self.check_deny(
            u2.review(request(resourceState="unknown",
                              recoveryState="copy_reported")),
            "resource_not_confirmed_active",
            "recoverable_restore_not_demonstrated")

    def test_restore_requires_trashed_verified_and_no_target_conflict(self):
        response = u2.review(request(
            operation="restore", resourceState="trashed",
            recoveryState="unknown", destinationState="occupied"))
        self.check_deny(response, "restoration_not_demonstrated",
                        "restore_destination_conflict_unresolved")
        complete = u2.review(request(
            operation="restore", resourceState="trashed"))
        self.check_deny(complete, "owner_execution_not_connected")

    def test_restore_unknown_destination_is_not_silently_overwritten(self):
        response = u2.review(request(
            operation="restore", resourceState="active",
            destinationState="unknown"))
        self.check_deny(response, "resource_not_confirmed_trashed",
                        "restore_destination_conflict_unresolved")

    def test_burn_requires_trashed_scope_and_separate_receipt(self):
        initial = u2.review(request(operation="burn",
                                    confirmationState="first_click"))
        self.check_deny(initial, "resource_not_confirmed_in_trash",
                        "two_step_burn_unverified",
                        "owner_signed_burn_receipt_not_available",
                        "permanent_deletion_authority_unavailable")
        second = u2.review(request(operation="burn",
                                   resourceState="trashed",
                                   confirmationState="second_click_reported"))
        self.check_deny(second, "owner_signed_burn_receipt_not_available",
                        "permanent_deletion_authority_unavailable")

    def test_missing_or_extra_schema_fields_refused(self):
        for update in ({"approved": True}, {"payload": "private"},
                       {"privateKey": "secret"}, {"burnAllowed": True},
                       {"sourceAuthorization": "verified"}):
            with self.subTest(update=update):
                payload = request(**update)
                with self.assertRaisesRegex(
                        u2.LifecycleReviewRefused,
                        "^U2_REQUEST_SCHEMA_REFUSED$"):
                    u2.review(payload)
        missing = request()
        del missing["ownerGrantState"]
        with self.assertRaisesRegex(u2.LifecycleReviewRefused,
                                    "^U2_REQUEST_SCHEMA_REFUSED$"):
            u2.review(missing)

    def test_invalid_action_and_spoofed_strong_status_refused(self):
        for change, code in (
            ({"operation": "delete"}, "U2_OPERATION_REFUSED"),
            ({"operation": "archive"}, "U2_OPERATION_REFUSED"),
            ({"ownerGrantState": "verified"}, "U2_UNTRUSTED_STATUS_REFUSED"),
            ({"sourceRevisionState": "verified"}, "U2_REQUEST_SCHEMA_REFUSED"),
            ({"retentionState": True}, "U2_UNTRUSTED_STATUS_REFUSED"),
            ({"writerState": "frozen"}, "U2_UNTRUSTED_STATUS_REFUSED"),
            ({"confirmationState": 2}, "U2_UNTRUSTED_STATUS_REFUSED"),
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(
                        u2.LifecycleReviewRefused, "^" + code + "$"):
                    u2.review(request(**change))

    def test_invalid_identity_digests_and_file_paths_refused(self):
        for change in (
            {"resourceId": "../../hospital/files"},
            {"resourceId": "/tmp/private.db"},
            {"resourceId": "a" * 201},
            {"resourceId": ""},
            {"resourceId": True},
            {"ownerId": "../hospital"},
            {"ownerId": "unknown spaces"},
            {"expectedRevision": OTHER_HASH.upper()},
            {"expectedRevision": "x" * 64},
            {"expectedRevision": True},
        ):
            with self.subTest(change=change):
                with self.assertRaisesRegex(
                        u2.LifecycleReviewRefused,
                        "^U2_IDENTITY_OR_REVISION_REFUSED$"):
                    u2.review(request(**change))

    def test_sensitive_input_not_in_fixed_error(self):
        secret = "PRIVATE_PATIENT_DATA"
        with self.assertRaises(u2.LifecycleReviewRefused) as context:
            u2.review(request(resourceId=secret + "/file"))
        self.assertNotIn(secret, str(context.exception))

    def test_review_profile_cannot_be_extended_at_runtime(self):
        with self.assertRaises(TypeError):
            u2.OWNER_REVIEW_PROFILES["fake"] = ("managed-copy", "disposable")
        self.check_deny(
            u2.review(request(ownerId="fake")),
            "owner_review_profile_missing")

    def test_no_mutating_backends_or_live_cli_in_contract(self):
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('raise SystemExit(1)', source)
        for forbidden in ("subprocess.run(", "os.unlink(", "os.remove(",
                          ".execute(", ".commit(", "shutil.rmtree(",
                          "gio trash", "ArchiveStore(",
                          "Process {", "requests.post("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
