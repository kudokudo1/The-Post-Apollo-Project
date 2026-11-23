"""DOC 5 C5 local-history cutover quarantine: hostile source-only checks."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5SpendFenceReference import ACTION, AUDIENCE  # noqa: E402
from TimeWC5LocalHistoryQuarantineReference import (  # noqa: E402
    SCHEMA, FUTURE_DOMAIN, LOCAL_ORIGIN, CANDIDATE_ORIGIN, MAX_RECORDS,
    assess_local_history_cutover_fixture,
)


def uid():
    return str(uuid.uuid4())


def claim():
    return {
        "audience": AUDIENCE, "action": ACTION,
        "grant_id": uid(), "operation_id": uid(),
        "selection_sha256": "a" * 64, "intent_sha256": "b" * 64,
        "source_sha256": "c" * 64, "session_id": uid(), "seat_id": "seat0",
        "issuer_epoch": uid(), "issued_ms": 1000, "expires_ms": 2000,
    }


def local_row(state="SPENT"):
    return {
        "claim": claim(), "source_mode": LOCAL_ORIGIN,
        "local_state": state, "local_head_sha256": uuid.uuid4().hex * 2,
        "local_key_id": uid(),
    }


def proposal():
    return {
        "schema": SCHEMA, "candidate_origin": CANDIDATE_ORIGIN,
        "candidate_domain": FUTURE_DOMAIN, "mode": "FRESH_EMPTY_GENESIS",
        "new_genesis_id": uid(), "new_issuer_epoch": uid(),
        "new_key_id": uid(), "candidate_head_sha256": uuid.uuid4().hex * 2,
        "imported_grant_ids": (), "imported_operation_ids": (),
        "imported_issuer_epochs": (), "imported_key_ids": (),
        "native_authority_requested": False,
        "local_fallback_requested": False,
        "claimed_admin_enrolled": False,
        "claimed_operator_approval": False,
    }


class QuarantineTests(unittest.TestCase):
    def setUp(self):
        self.rows = (local_row("ACTIVE"), local_row("SPENT"),
                     local_row("REVOKED"), local_row("UNKNOWN"))
        self.plan = proposal()

    def assess(self, rows=None, plan=None):
        result = assess_local_history_cutover_fixture(
            local_records=self.rows if rows is None else rows,
            proposal=self.plan if plan is None else plan,
        )
        self.assertEqual(result["safe_actions"], [])
        for k in (
            "archive_copy_performed", "archive_verified",
            "candidate_enrollment_verified", "operator_approval_verified",
            "independent_current_head_verified", "fresh_genesis_activated",
            "legacy_grants_imported", "historical_spent_trusted",
            "protected_spent_verified", "native_action_allowed",
            "production_authorized", "safe_retry_allowed", "undo_allowed",
        ):
            self.assertIs(result[k], False, k)
        return result

    def test_distinct_fresh_candidate_still_unenrolled(self):
        r = self.assess()
        self.assertEqual(r["diagnostic"],
                         "FRESH_GENESIS_CANDIDATE_UNENROLLED_HOLD")
        self.assertEqual(r["untrusted_local_record_count"], 4)

    def test_archive_candidate_is_not_a_verified_copy(self):
        plan = dict(self.plan, mode="ARCHIVE_ONLY")
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LOCAL_ARCHIVE_CANDIDATE_UNVERIFIED_HOLD")

    def test_empty_history_is_not_enrollment(self):
        r = self.assess(rows=())
        self.assertEqual(r["diagnostic"],
                         "FRESH_GENESIS_CANDIDATE_UNENROLLED_HOLD")
        self.assertEqual(r["untrusted_local_record_count"], 0)

    def test_local_spent_and_revoked_states_never_become_authority(self):
        for state in ("ACTIVE", "SPENT", "REVOKED", "UNKNOWN"):
            with self.subTest(state=state):
                r = self.assess(rows=(local_row(state),))
                self.assertEqual(r["diagnostic"],
                                 "FRESH_GENESIS_CANDIDATE_UNENROLLED_HOLD")

    def test_untrusted_admin_and_operator_claims_do_not_upgrade(self):
        for admin, operator in ((False, True), (True, False), (True, True)):
            with self.subTest(admin=admin, operator=operator):
                plan = dict(self.plan, claimed_admin_enrolled=admin,
                            claimed_operator_approval=operator)
                self.assertEqual(
                    self.assess(plan=plan)["diagnostic"],
                    "FRESH_GENESIS_CANDIDATE_UNENROLLED_HOLD")

    def test_native_request_is_denied_even_with_claimed_approval(self):
        plan = dict(self.plan, native_authority_requested=True,
                    claimed_admin_enrolled=True,
                    claimed_operator_approval=True)
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LOCAL_HISTORY_NATIVE_AUTHORITY_REQUEST_REFUSED_HOLD")

    def test_local_fallback_is_denied(self):
        plan = dict(self.plan, local_fallback_requested=True)
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LOCAL_AUTHORITY_FALLBACK_REFUSED_HOLD")

    def test_grant_promotion_is_denied(self):
        plan = dict(self.plan, mode="PROMOTE_LOCAL_GRANTS")
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LEGACY_GRANT_PROMOTION_REFUSED_HOLD")

    def test_local_snapshot_restore_is_denied(self):
        plan = dict(self.plan, mode="RESTORE_LOCAL_BACKUP")
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LOCAL_BACKUP_REPLAY_REFUSED_HOLD")

    def test_importing_any_historical_id_or_key_is_denied(self):
        cases = (
            ("imported_grant_ids", self.rows[1]["claim"]["grant_id"]),
            ("imported_operation_ids", self.rows[1]["claim"]["operation_id"]),
            ("imported_issuer_epochs", self.rows[1]["claim"]["issuer_epoch"]),
            ("imported_key_ids", self.rows[1]["local_key_id"]),
        )
        for key, value in cases:
            with self.subTest(key=key):
                plan = dict(self.plan, **{key: (value,)})
                self.assertEqual(self.assess(plan=plan)["diagnostic"],
                                 "HISTORICAL_CREDENTIAL_IMPORT_REFUSED_HOLD")

    def test_even_unseen_ids_in_authority_import_are_denied(self):
        plan = dict(self.plan, imported_grant_ids=(uid(),))
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "HISTORICAL_CREDENTIAL_IMPORT_REFUSED_HOLD")

    def test_new_genesis_cannot_reuse_old_grant_operation_or_epoch(self):
        for key in ("grant_id", "operation_id", "issuer_epoch"):
            with self.subTest(key=key):
                plan = dict(self.plan,
                            new_genesis_id=self.rows[0]["claim"][key])
                self.assertEqual(self.assess(plan=plan)["diagnostic"],
                                 "LOCAL_IDENTITY_OR_HEAD_REUSE_REFUSED_HOLD")

    def test_new_issuer_epoch_cannot_reuse_old_id_or_epoch(self):
        for key in ("grant_id", "operation_id", "issuer_epoch"):
            with self.subTest(key=key):
                plan = dict(self.plan,
                            new_issuer_epoch=self.rows[0]["claim"][key])
                self.assertEqual(self.assess(plan=plan)["diagnostic"],
                                 "LOCAL_IDENTITY_OR_HEAD_REUSE_REFUSED_HOLD")

    def test_local_signer_key_id_reuse_is_denied(self):
        plan = dict(self.plan, new_key_id=self.rows[2]["local_key_id"])
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LOCAL_IDENTITY_OR_HEAD_REUSE_REFUSED_HOLD")

    def test_local_head_reuse_is_denied(self):
        plan = dict(self.plan,
                    candidate_head_sha256=self.rows[0]["local_head_sha256"])
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LOCAL_IDENTITY_OR_HEAD_REUSE_REFUSED_HOLD")

    def test_duplicate_grant_or_operation_in_local_history_is_ambiguous(self):
        for key in ("grant_id", "operation_id"):
            with self.subTest(key=key):
                row = deepcopy(self.rows[1])
                row["claim"][key] = self.rows[0]["claim"][key]
                self.assertEqual(
                    self.assess(rows=(self.rows[0], row))["diagnostic"],
                    "DUPLICATE_LOCAL_IDENTITY_HOLD")

    def test_wrong_local_origin_must_not_claim_protected_provenance(self):
        for origin in ("PROTECTED", CANDIDATE_ORIGIN, "EXTERNAL_ROOT"):
            with self.subTest(origin=origin):
                row = dict(self.rows[0], source_mode=origin)
                self.assertEqual(
                    self.assess(rows=(row,))["diagnostic"],
                    "MALFORMED_OR_MISLABELED_LOCAL_RECORD_HOLD")

    def test_cross_domain_claims_are_not_importable(self):
        for key, value in (
            ("audience", "post-apollo.connections.c3e.identity"),
            ("action", "hospital.restore"),
            ("grant_id", "invalid"),
            ("intent_sha256", "D" * 64),
            ("seat_id", ""),
            ("issued_ms", True),
            ("expires_ms", 50000),
        ):
            with self.subTest(key=key):
                row = deepcopy(self.rows[0])
                row["claim"][key] = value
                self.assertEqual(
                    self.assess(rows=(row,))["diagnostic"],
                    "MALFORMED_OR_MISLABELED_LOCAL_RECORD_HOLD")

    def test_local_record_extra_authority_claim_refused(self):
        row = dict(self.rows[0], native_authorized=True)
        self.assertEqual(
            self.assess(rows=(row,))["diagnostic"],
            "MALFORMED_OR_MISLABELED_LOCAL_RECORD_HOLD")

    def test_local_claim_extra_protected_spent_claim_refused(self):
        row = deepcopy(self.rows[0])
        row["claim"]["production_spent_verified"] = True
        self.assertEqual(
            self.assess(rows=(row,))["diagnostic"],
            "MALFORMED_OR_MISLABELED_LOCAL_RECORD_HOLD")

    def test_local_head_or_key_malformed_refused(self):
        for key, value in (("local_head_sha256", "BAD"),
                           ("local_key_id", "not-a-uuid"),
                           ("local_state", "SETTLED"),
                           ("local_head_sha256", True)):
            with self.subTest(key=key, value=value):
                row = dict(self.rows[0], **{key: value})
                self.assertEqual(
                    self.assess(rows=(row,))["diagnostic"],
                    "MALFORMED_OR_MISLABELED_LOCAL_RECORD_HOLD")

    def test_proposal_extra_or_missing_fields_refused(self):
        self.assertEqual(
            self.assess(plan=dict(self.plan, production_authorized=True))[
                "diagnostic"], "INVALID_CUTOVER_PROPOSAL_HOLD")
        plan = dict(self.plan)
        del plan["new_issuer_epoch"]
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "INVALID_CUTOVER_PROPOSAL_HOLD")

    def test_proposal_bad_domain_origin_or_schema_refused(self):
        for key, value in (
            ("candidate_domain", "post-apollo.connections.c3e.identity"),
            ("candidate_origin", LOCAL_ORIGIN),
            ("schema", "fake"), ("mode", "ACTIVATE_NOW"),
            ("new_genesis_id", "bad"),
            ("new_key_id", True), ("candidate_head_sha256", "X" * 64),
        ):
            with self.subTest(key=key):
                plan = dict(self.plan, **{key: value})
                self.assertEqual(self.assess(plan=plan)["diagnostic"],
                                 "INVALID_CUTOVER_PROPOSAL_HOLD")

    def test_proposal_boolean_flags_must_be_real_bools(self):
        for key in (
            "native_authority_requested", "local_fallback_requested",
            "claimed_admin_enrolled", "claimed_operator_approval",
        ):
            with self.subTest(key=key):
                plan = dict(self.plan, **{key: "true"})
                self.assertEqual(self.assess(plan=plan)["diagnostic"],
                                 "INVALID_CUTOVER_PROPOSAL_HOLD")

    def test_import_lists_are_bounded_duplicate_free_tuples(self):
        for value in ([uid()], (uid(), uid(), "bad"),
                      (uid(),) * 2, tuple(uid() for _ in range(129))):
            with self.subTest(value_type=type(value).__name__, size=len(value)):
                plan = dict(self.plan, imported_grant_ids=value)
                self.assertEqual(self.assess(plan=plan)["diagnostic"],
                                 "INVALID_CUTOVER_PROPOSAL_HOLD")

    def test_local_record_limit_and_tuple_only(self):
        self.assertEqual(self.assess(rows=[])["diagnostic"],
                         "INVALID_LOCAL_RECORD_CONTAINER_HOLD")
        self.assertEqual(
            self.assess(rows=tuple(local_row() for _ in
                                   range(MAX_RECORDS + 1)))["diagnostic"],
            "INVALID_LOCAL_RECORD_CONTAINER_HOLD")

    def test_proposal_string_not_interpreted_as_dict(self):
        self.assertEqual(self.assess(plan="independent hardware")["diagnostic"],
                         "INVALID_CUTOVER_PROPOSAL_HOLD")

    def test_archive_only_cannot_import_keys(self):
        plan = dict(self.plan, mode="ARCHIVE_ONLY",
                    imported_key_ids=(self.rows[0]["local_key_id"],))
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "HISTORICAL_CREDENTIAL_IMPORT_REFUSED_HOLD")

    def test_claimed_approval_does_not_redeem_promoted_grants(self):
        plan = dict(self.plan, mode="PROMOTE_LOCAL_GRANTS",
                    claimed_operator_approval=True,
                    claimed_admin_enrolled=True)
        self.assertEqual(self.assess(plan=plan)["diagnostic"],
                         "LEGACY_GRANT_PROMOTION_REFUSED_HOLD")


if __name__ == "__main__":
    unittest.main()
