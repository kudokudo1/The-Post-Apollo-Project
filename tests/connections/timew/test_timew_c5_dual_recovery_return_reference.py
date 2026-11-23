"""DOC 5 dual C5/native original-operation return comparison: deny-only."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import math
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5DualRecoveryReturnReference import (  # noqa: E402
    NATIVE_SCHEMA, Comparison, compare_untrusted_recovery_returns,
)
from TimeWC5ReadOnlyRecoveryPlanReference import (  # noqa: E402
    prepare_unknown_recovery_intents,
)
from test_timew_c5_custodian_boundary_reference import (  # noqa: E402
    snapshot as c5_snapshot,
)
from test_timew_c5_review_shadow_reference import (  # noqa: E402
    original_fixture,
)

_DEFAULT = object()


def native_snapshot(original, *, mode="PROTECTED_CANDIDATE",
                    resize="READY_ONLY", move="NONE", present=False,
                    selected=False, head="f" * 64, seq=9):
    before, target = original["before_value"], original["target_value"]
    return {
        "schema": NATIVE_SCHEMA, "source_mode": mode,
        "grant_id": original["grant_id"],
        **{key: original[key] for key in (
            "operation_id", "selection_sha256", "intent_sha256",
            "source_sha256", "session_id", "seat_id", "checkpoint_id",
            "window_key", "boot_epoch", "surface_generation", "output_id",
            "workspace_id", "output_scale_hex", "output_transform")},
        "before_bits": tuple(getattr(before, k + "_bits")
                             for k in ("x", "y", "width", "height")),
        "target_bits": tuple(getattr(target, k + "_bits")
                             for k in ("x", "y", "width", "height")),
        "resize_observation": resize, "move_observation": move,
        "output_present": present, "selected_xdg_frame_claimed": selected,
        "head_sha256": head, "sequence": seq,
    }


class DualReturnTests(unittest.TestCase):
    def setUp(self):
        self.original = original_fixture()
        self.plan = prepare_unknown_recovery_intents(
            original=self.original, uncertainty="NATIVE_RESIZE_ACK_LOST")
        self.c5 = c5_snapshot(self.original)
        self.native = native_snapshot(self.original)

    def evaluate(self, *, plan=_DEFAULT, c5=_DEFAULT, native=_DEFAULT,
                 prior=None):
        result = compare_untrusted_recovery_returns(
            plan=self.plan if plan is _DEFAULT else plan,
            c5_return=self.c5 if c5 is _DEFAULT else c5,
            native_return=self.native if native is _DEFAULT else native,
            last_seen=prior)
        self.assertIs(type(result), Comparison)
        for key in (
            "production_authorized", "external_custody_verified",
            "current_head_verified", "protected_spent_verified",
            "operator_intent_verified", "native_source_verified",
            "configure_ack_verified", "selected_frame_settled",
            "terminal_receipt_verified", "native_action_allowed",
            "second_spend_allowed", "move_allowed", "retry_allowed",
            "undo_allowed",
        ):
            self.assertIs(getattr(result, key), False, key)
        self.assertEqual(result.safe_actions, ())
        return result.diagnostic

    def test_matching_two_protected_candidates_still_unenrolled(self):
        self.assertEqual(
            self.evaluate(), "MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")

    def test_local_c5_history_never_promotes(self):
        c5 = dict(self.c5, source_mode="LOCAL_DEVELOPMENT")
        self.assertEqual(self.evaluate(c5=c5),
                         "LOCAL_DEVELOPMENT_EVIDENCE_UNKNOWN_HOLD")

    def test_native_local_diagnostic_never_promotes(self):
        n = dict(self.native, source_mode="LOCAL_DIAGNOSTIC")
        self.assertEqual(self.evaluate(native=n),
                         "LOCAL_DEVELOPMENT_EVIDENCE_UNKNOWN_HOLD")

    def test_missing_each_return_unknown(self):
        self.assertEqual(self.evaluate(c5=None),
                         "MISSING_C5_HISTORY_UNKNOWN_HOLD")
        self.assertEqual(self.evaluate(native=None),
                         "MISSING_NATIVE_TERMINAL_UNKNOWN_HOLD")

    def test_malformed_evidence_containers_unknown(self):
        for key in ("c5", "native"):
            for bad in (None, "signed", [], (), True, 5):
                with self.subTest(key=key, bad=bad):
                    actual = self.evaluate(**{key: bad})
                    self.assertTrue(actual.endswith("UNKNOWN_HOLD"))

    def test_c5_extra_grant_or_signature_authority_field_rejected(self):
        for field in ("production_authorized", "trusted_spent",
                      "selected_view_settled", "retry_allowed"):
            with self.subTest(field=field):
                c5 = dict(self.c5, **{field: True})
                self.assertEqual(self.evaluate(c5=c5),
                                 "MALFORMED_C5_RESPONSE_UNKNOWN_HOLD")

    def test_native_extra_authority_field_rejected(self):
        for field in ("restore_allowed", "signed_producer",
                      "second_spend_allowed", "native_action_allowed"):
            with self.subTest(field=field):
                n = dict(self.native, **{field: True})
                self.assertEqual(self.evaluate(native=n),
                                 "MALFORMED_NATIVE_RESPONSE_UNKNOWN_HOLD")

    def test_mismatched_c5_grant_operation_source_intent_and_seat(self):
        for key, bad in (
            ("grant_id", str(uuid.uuid4())), ("operation_id", str(uuid.uuid4())),
            ("issuer_epoch", str(uuid.uuid4())),
            ("seat_id", "seat1"), ("selection_sha256", "1" * 64),
            ("intent_sha256", "2" * 64), ("source_sha256", "3" * 64),
            ("session_id", str(uuid.uuid4())),
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    self.evaluate(c5=dict(self.c5, **{key: bad})),
                    "C5_ORIGINAL_INTENT_MISMATCH_UNKNOWN_HOLD")

    def test_cross_domain_c5_identity_or_hospital_refused(self):
        for bad in ("post-apollo.connections.c3e.identity",
                    "post-apollo.hospital.c5"):
            self.assertEqual(
                self.evaluate(c5=dict(self.c5, audience=bad)),
                "C5_ORIGINAL_INTENT_MISMATCH_UNKNOWN_HOLD")

    def test_mismatched_native_selected_window_and_context(self):
        for key, bad in (
            ("selection_sha256", "4" * 64),
            ("intent_sha256", "5" * 64),
            ("source_sha256", "6" * 64),
            ("seat_id", "seat1"),
            ("session_id", str(uuid.uuid4())),
            ("checkpoint_id", str(uuid.uuid4())),
            ("window_key", str(uuid.uuid4())),
            ("boot_epoch", str(uuid.uuid4())),
            ("surface_generation", 12),
            ("output_id", "DP-2"),
            ("workspace_id", "workspace-7"),
            ("output_scale_hex", (1.5).hex()),
            ("output_transform", 1),
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    self.evaluate(native=dict(self.native, **{key: bad})),
                    "NATIVE_ORIGINAL_WINDOW_MISMATCH_UNKNOWN_HOLD")

    def test_mismatched_native_grant_is_not_same_operation(self):
        self.assertEqual(
            self.evaluate(native=dict(self.native, grant_id=str(uuid.uuid4()))),
            "NATIVE_ORIGINAL_GRANT_MISMATCH_UNKNOWN_HOLD")

    def test_exact_one_ulp_before_and_target_bits_are_bound(self):
        before = list(self.native["before_bits"])
        before[1] = (before[1] + 1)
        n = dict(self.native, before_bits=tuple(before))
        self.assertEqual(self.evaluate(native=n),
                         "NATIVE_EXACT_GEOMETRY_MISMATCH_UNKNOWN_HOLD")
        after = list(self.native["target_bits"])
        after[3] += 1
        n = dict(self.native, target_bits=tuple(after))
        self.assertEqual(self.evaluate(native=n),
                         "NATIVE_EXACT_GEOMETRY_MISMATCH_UNKNOWN_HOLD")

    def test_bad_bools_and_forged_ieee_bits_refused(self):
        for field, bad in (
            ("surface_generation", True), ("output_transform", True),
            ("before_bits", (True,) * 4), ("before_bits", (0,) * 3),
            ("target_bits", [0, 0, 0, 0]),
            ("output_present", 1), ("selected_xdg_frame_claimed", 1),
            ("sequence", False), ("head_sha256", "A" * 64),
            ("resize_observation", "SETTLED"), ("move_observation", "MOVE_NOW"),
        ):
            with self.subTest(field=field, bad=bad):
                self.assertEqual(
                    self.evaluate(native=dict(self.native, **{field: bad})),
                    "MALFORMED_NATIVE_RESPONSE_UNKNOWN_HOLD")

    def test_native_ready_timeout_contradiction_is_unknown(self):
        n = native_snapshot(self.original, resize="READY_AND_TIMEOUT",
                            present=True)
        self.assertEqual(self.evaluate(native=n),
                         "CONTRADICTORY_RESIZE_UNKNOWN_HOLD")

    def test_move_ready_timeout_contradiction_is_unknown(self):
        n = native_snapshot(self.original, move="READY_AND_TIMEOUT")
        self.assertEqual(self.evaluate(native=n),
                         "CONTRADICTORY_MOVE_UNKNOWN_HOLD")

    def test_move_after_timeout_current_or_missing_resize_is_denied(self):
        for resize in ("NONE", "TIMEOUT", "CURRENT_SCENE",
                       "OUTPUT_PRESENT"):
            with self.subTest(resize=resize):
                n = native_snapshot(self.original, resize=resize,
                                    move="READY_ONLY", present=True)
                self.assertEqual(
                    self.evaluate(native=n),
                    "MOVE_WITHOUT_SETTLED_RESIZE_UNKNOWN_HOLD")

    def test_ready_then_move_cannot_be_permitted_by_diagnostic_match(self):
        n = native_snapshot(self.original, move="READY_ONLY")
        self.assertEqual(
            self.evaluate(native=n),
            "MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")

    def test_output_present_is_not_selected_xdg_final_frame(self):
        n = native_snapshot(self.original, present=True)
        self.assertEqual(self.evaluate(native=n),
                         "OUTPUT_PRESENT_NOT_SELECTED_FRAME_UNKNOWN_HOLD")

    def test_claimed_selected_xdg_frame_is_not_signed_evidence(self):
        n = native_snapshot(self.original, present=True, selected=True)
        self.assertEqual(self.evaluate(native=n),
                         "CLAIMED_SELECTED_FRAME_NOT_VERIFIED_UNKNOWN_HOLD")

    def test_active_c5_with_native_observation_is_uncertain(self):
        c5 = dict(self.c5, ledger_state="ACTIVE")
        self.assertEqual(
            self.evaluate(c5=c5),
            "NATIVE_EFFECT_WITHOUT_PROVEN_SPENT_UNKNOWN_HOLD")

    def test_revoked_c5_not_equivalent_to_confirmed_undo(self):
        c5 = dict(self.c5, ledger_state="REVOKED")
        self.assertEqual(self.evaluate(c5=c5),
                         "REVOCATION_NOT_A_TERMINAL_RECEIPT_UNKNOWN_HOLD")

    def test_unknown_c5_history_denies(self):
        c5 = dict(self.c5, ledger_state="UNKNOWN")
        self.assertEqual(self.evaluate(c5=c5),
                         "C5_UNKNOWN_HISTORY_UNKNOWN_HOLD")

    def test_prior_c5_head_rollback_detected_but_not_authenticated(self):
        prior = {"c5": {"head_sha256": "a" * 64, "sequence": 8},
                 "native": None}
        self.assertEqual(self.evaluate(prior=prior),
                         "C5_PRIOR_HEAD_ROLLBACK_UNKNOWN_HOLD")

    def test_prior_native_head_fork_detected(self):
        prior = {"c5": None,
                 "native": {"head_sha256": "a" * 64, "sequence": 9}}
        self.assertEqual(self.evaluate(prior=prior),
                         "NATIVE_PRIOR_HEAD_FORK_UNKNOWN_HOLD")

    def test_prior_head_sequence_advance_without_head_change_refused(self):
        prior = {"c5": {"head_sha256": self.c5["head_sha256"],
                        "sequence": 6}, "native": None}
        self.assertEqual(self.evaluate(prior=prior),
                         "C5_UNSUPPORTED_HEAD_ADVANCE_UNKNOWN_HOLD")

    def test_same_seq_same_head_is_not_independent_currentness(self):
        prior = {"c5": {"head_sha256": self.c5["head_sha256"],
                        "sequence": self.c5["sequence"]},
                 "native": {"head_sha256": self.native["head_sha256"],
                            "sequence": self.native["sequence"]}}
        self.assertEqual(self.evaluate(prior=prior),
                         "MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")

    def test_malformed_prior_head_is_not_silently_ignored(self):
        for prior in (
            (), [], "last-known", True, {},
            {"c5": None}, {"c5": True, "native": None},
            {"c5": {"head_sha256": "z" * 64, "sequence": 1},
             "native": None},
        ):
            with self.subTest(prior=prior):
                self.assertEqual(
                    self.evaluate(prior=prior),
                    "INVALID_LOCAL_PRIOR_HEAD_UNKNOWN_HOLD")

    def test_invalid_or_forged_plan_cannot_enable_matching_results(self):
        cases = (
            None, {"query_intents": ()},
            replace(self.plan, production_authorized=True),
            replace(self.plan, safe_actions=("resize",)),
            replace(self.plan, uncertainty=[]),
            replace(self.plan, query_intents=()),
            replace(self.plan, query_intents=tuple(reversed(self.plan.query_intents))),
        )
        for altered in cases:
            with self.subTest(altered=repr(altered)[:40]):
                self.assertEqual(
                    self.evaluate(plan=altered),
                    "INVALID_ORIGINAL_RECOVERY_PLAN_UNKNOWN_HOLD")

    def test_forged_binding_operation_or_exact_bit_refused(self):
        c, n = self.plan.query_intents
        c_bad = replace(
            c, original_operation_id=str(uuid.uuid4()))
        self.assertEqual(
            self.evaluate(plan=replace(self.plan, query_intents=(c_bad, n))),
            "INVALID_ORIGINAL_RECOVERY_PLAN_UNKNOWN_HOLD")
        bits = list(n.original_binding)
        for i, (k, v) in enumerate(bits):
            if k == "before_y_bits":
                bits[i] = (k, True)
                break
        n_bad = replace(n, original_binding=tuple(bits))
        self.assertEqual(
            self.evaluate(plan=replace(self.plan, query_intents=(c, n_bad))),
            "INVALID_ORIGINAL_RECOVERY_PLAN_UNKNOWN_HOLD")

    def test_expired_original_still_requires_read_only_reconciliation(self):
        # The plan deliberately does not expire historical evidence lookups.
        self.assertLess(self.original["expires_ms"], 2000)
        self.assertEqual(
            self.evaluate(),
            "MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD")

    def test_missing_one_entire_source_stays_hold_even_if_other_signed_looking(self):
        c5 = dict(self.c5, terminal_receipt_sha256="d" * 64)
        n = native_snapshot(self.original, present=True, selected=True)
        self.assertEqual(
            self.evaluate(c5=c5, native=None),
            "MISSING_NATIVE_TERMINAL_UNKNOWN_HOLD")
        self.assertEqual(
            self.evaluate(c5=None, native=n),
            "MISSING_C5_HISTORY_UNKNOWN_HOLD")

    def test_immutable_output_and_no_executable_methods(self):
        result = compare_untrusted_recovery_returns(
            plan=self.plan, c5_return=self.c5, native_return=self.native)
        with self.assertRaises(FrozenInstanceError):
            result.native_action_allowed = True
        for key in ("spend", "send", "resize", "move", "retry",
                    "undo", "sign", "fetch", "execute"):
            self.assertFalse(hasattr(result, key))

    def test_original_inputs_are_not_modified(self):
        c = dict(self.c5)
        n = dict(self.native)
        p = self.plan
        self.evaluate()
        self.assertEqual(c, self.c5)
        self.assertEqual(n, self.native)
        self.assertIs(p, self.plan)


if __name__ == "__main__":
    unittest.main()
