"""DOC 5 recovery lookup INTENT generation: source-only hostile tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5ReadOnlyRecoveryPlanReference import (  # noqa: E402
    CUSTODIAN_LOOKUP, NATIVE_LOOKUP, UNCERTAINTIES,
    prepare_unknown_recovery_intents,
)
from test_timew_c5_review_shadow_reference import (  # noqa: E402
    _value, original_fixture,
)


_UNSET = object()


class RecoveryPlans(unittest.TestCase):
    def setUp(self):
        self.original = original_fixture()

    def check_no_authority(self, result):
        for key in (
            "production_authorized", "protected_spent_verified",
            "custodian_current_head_verified",
            "original_human_consent_verified", "native_source_authenticated",
            "terminal_settlement_verified", "native_action_allowed",
            "automatic_second_spend_allowed", "move_continuation_allowed",
            "retry_allowed", "undo_allowed",
        ):
            self.assertIs(getattr(result, key), False, key)
        self.assertEqual(result.safe_actions, ())

    def evaluate(self, *, original=_UNSET, cause="C5_SPENT_REPLY_LOST"):
        out = prepare_unknown_recovery_intents(
            original=self.original if original is _UNSET else original,
            uncertainty=cause,
        )
        self.check_no_authority(out)
        return out

    def test_original_operation_yields_exactly_two_read_only_intents(self):
        out = self.evaluate()
        self.assertEqual(
            out.diagnostic,
            "UNTRUSTED_DUAL_READ_ONLY_LOOKUP_INTENTS_UNKNOWN_HOLD",
        )
        self.assertEqual(len(out.query_intents), 2)
        self.assertEqual(
            tuple(x.role for x in out.query_intents),
            (CUSTODIAN_LOOKUP, NATIVE_LOOKUP),
        )

    def test_both_references_bind_same_original_grant_operation(self):
        out = self.evaluate()
        for x in out.query_intents:
            self.assertEqual(x.original_grant_id, self.original["grant_id"])
            self.assertEqual(x.original_operation_id, self.original["operation_id"])
        self.assertEqual(
            dict(out.query_intents[0].original_binding)["operation_id"],
            self.original["operation_id"],
        )
        self.assertEqual(
            dict(out.query_intents[1].original_binding)["operation_id"],
            self.original["operation_id"],
        )

    def test_separate_custodian_and_native_source_fields(self):
        out = self.evaluate()
        c = dict(out.query_intents[0].original_binding)
        n = dict(out.query_intents[1].original_binding)
        self.assertEqual(c["issuer_epoch"], self.original["issuer_epoch"])
        self.assertEqual(c["grant_id"], self.original["grant_id"])
        self.assertNotIn("before_x_bits", c)
        self.assertNotIn("target_x_bits", c)
        self.assertNotIn("issuer_epoch", n)
        self.assertEqual(n["boot_epoch"], self.original["boot_epoch"])
        self.assertEqual(n["window_key"], self.original["window_key"])
        self.assertEqual(n["surface_generation"], 7)

    def test_before_and_target_exact_binary64_phase_and_bits(self):
        out = self.evaluate()
        b = self.original["before_value"]
        t = self.original["target_value"]
        native = dict(out.query_intents[1].original_binding)
        for phase, source in (("before", b), ("target", t)):
            self.assertEqual(native[phase + "_version"], source.version)
            self.assertEqual(native[phase + "_phase"], source.phase)
            for k in ("x", "y", "width", "height"):
                self.assertEqual(
                    native[phase + "_" + k + "_bits"],
                    getattr(source, k + "_bits"),
                )
        self.assertEqual(_value.read_value(b)[1], 92.5)
        self.assertEqual(_value.read_value(t)[3], 700.5)

    def test_all_known_uncertainty_causes_stay_unknown(self):
        for cause in UNCERTAINTIES:
            with self.subTest(cause=cause):
                out = self.evaluate(cause=cause)
                self.assertEqual(out.uncertainty, cause)
                self.assertEqual(len(out.query_intents), 2)

    def test_invalid_or_instruction_like_causes_have_no_intents(self):
        for cause in (
            "", "DISPATCH_RESIZE", "RETRY_RESIZE", "MOVE_NOW",
            "GRANT_ACTIVE", "SIGNED_FINAL_SETTLED", "REGRANT",
            "UNDO", True, 0, None, ("C5_SPENT_REPLY_LOST",),
        ):
            with self.subTest(cause=cause):
                out = self.evaluate(cause=cause)
                self.assertEqual(out.diagnostic,
                                 "INVALID_RECOVERY_CAUSE_UNKNOWN_HOLD")
                self.assertEqual(out.query_intents, ())
                self.assertIsNone(out.uncertainty)

    def test_missing_or_extra_original_field_never_generates_lookup(self):
        for k in ("operation_id", "selection_sha256", "issuer_epoch",
                  "before_value", "target_value", "output_scale_hex"):
            with self.subTest(field=k):
                invalid = dict(self.original)
                del invalid[k]
                self.assertEqual(
                    self.evaluate(original=invalid).query_intents, (),
                )
        invalid = dict(self.original, signed_native_receipt=True)
        self.assertEqual(self.evaluate(original=invalid).query_intents, ())

    def test_wrong_audience_source_seat_and_spend_claims_refused(self):
        for key, value in (
            ("audience", "post-apollo.connections.c3e.identity"),
            ("action", "native-restore"),
            ("seat_id", "seat\n0"),
            ("operation_id", "not-a-uuid"),
            ("selection_sha256", "g" * 64),
            ("source_sha256", "A" * 64),
            ("issuer_epoch", "guest-only"),
            ("issued_ms", True),
            ("expires_ms", 999999999999999),
        ):
            with self.subTest(key=key):
                altered = dict(self.original, **{key: value})
                out = self.evaluate(original=altered)
                self.assertEqual(out.query_intents, ())
                self.assertEqual(out.diagnostic,
                                 "INVALID_ORIGINAL_UNKNOWN_HOLD")

    def test_bad_geometry_and_out_of_order_steps_refuse_queries(self):
        invalid = dict(self.original, operation_steps=(
            "move", "resize", "observe-after-resize", "verify-final"))
        self.assertEqual(self.evaluate(original=invalid).query_intents, ())
        altered = dict(self.original)
        altered["before_value"] = _value.capture_value(
            _value.PHASE_PENDING, x=259, y=92.5, width=1402, height=872)
        self.assertEqual(self.evaluate(original=altered).query_intents, ())
        altered = dict(self.original)
        altered["target_value"] = _value.capture_value(
            _value.PHASE_CURRENT, x=380.25, y=120.5, width=1200, height=700.5)
        self.assertEqual(self.evaluate(original=altered).query_intents, ())

    def test_invalid_native_context_refuses_queries(self):
        for key, value in (
            ("boot_epoch", "not-a-uuid"),
            ("surface_generation", 0),
            ("surface_generation", True),
            ("output_id", ""),
            ("workspace_id", "workspace\n3"),
            ("output_scale_hex", "1.25"),
            ("output_transform", 8),
            ("output_transform", True),
        ):
            with self.subTest(key=key):
                altered = dict(self.original, **{key: value})
                self.assertEqual(self.evaluate(original=altered).query_intents, ())

    def test_one_ulp_before_and_target_changes_are_not_rounded(self):
        baseline = self.evaluate()
        changed = dict(self.original)
        changed["before_value"] = _value.capture_value(
            _value.PHASE_CURRENT, x=259,
            y=math.nextafter(92.5, math.inf), width=1402, height=872)
        new = self.evaluate(original=changed)
        self.assertNotEqual(
            dict(baseline.query_intents[1].original_binding)["before_y_bits"],
            dict(new.query_intents[1].original_binding)["before_y_bits"],
        )
        target = dict(self.original)
        target["target_value"] = _value.capture_value(
            _value.PHASE_PENDING, x=380.25, y=120.5,
            width=1200, height=math.nextafter(700.5, math.inf))
        other = self.evaluate(original=target)
        self.assertNotEqual(
            dict(baseline.query_intents[1].original_binding)["target_height_bits"],
            dict(other.query_intents[1].original_binding)["target_height_bits"],
        )

    def test_minting_new_operation_does_not_preserve_original_identity(self):
        original = self.evaluate()
        changed = dict(self.original, operation_id=str(uuid.uuid4()))
        different = self.evaluate(original=changed)
        self.assertNotEqual(
            original.query_intents[0].original_operation_id,
            different.query_intents[0].original_operation_id,
        )

    def test_original_input_mutation_cannot_change_frozen_plan(self):
        before = self.evaluate()
        snapshot = before.query_intents[1].original_binding
        self.original["source_sha256"] = "d" * 64
        self.original["target_value"] = _value.capture_value(
            _value.PHASE_PENDING, x=0, y=0, width=100, height=100)
        self.assertEqual(before.query_intents[1].original_binding, snapshot)
        self.assertNotEqual(
            dict(snapshot)["source_sha256"], self.original["source_sha256"],
        )

    def test_frozen_plan_and_query_intents_cannot_be_mutated(self):
        result = self.evaluate()
        with self.assertRaises(FrozenInstanceError):
            result.production_authorized = True
        with self.assertRaises(FrozenInstanceError):
            result.query_intents[0].role = "NATIVE_COMMAND"
        with self.assertRaises(TypeError):
            result.query_intents[1].original_binding[0] = ("new", "value")

    def test_no_untrusted_approval_flags_in_any_output(self):
        for cause in UNCERTAINTIES:
            out = self.evaluate(cause=cause)
            self.assertFalse(hasattr(out, "approved"))
            self.assertFalse(hasattr(out, "sign"))
            self.assertFalse(hasattr(out, "execute"))
            self.assertFalse(hasattr(out, "retry"))
            for x in out.query_intents:
                self.assertFalse(hasattr(x, "send"))
                self.assertFalse(hasattr(x, "execute"))

    def test_expired_spent_grant_still_needs_historical_lookup_not_regrant(self):
        out = self.evaluate(cause="SPENT_BUT_TIMEW_PREPARED")
        self.assertEqual(out.query_intents[0].original_operation_id,
                         self.original["operation_id"])
        self.assertTrue(
            self.original["expires_ms"] < 2000,
            "fixture is expired by a hypothetical later recovery moment",
        )
        self.check_no_authority(out)

    def test_duplicate_lookup_plans_are_deterministic_non_authorizing(self):
        a, b = self.evaluate(), self.evaluate()
        self.assertEqual(a, b)
        self.assertIsNot(a.query_intents, b.query_intents)
        self.assertEqual(a.safe_actions, ())

    def test_untrusted_local_spent_marker_is_not_recovery_evidence(self):
        before = self.evaluate()
        invalid = dict(self.original, local_ledger_spent=True)
        self.assertEqual(self.evaluate(original=invalid).query_intents, ())
        self.assertEqual(before.diagnostic,
                         "UNTRUSTED_DUAL_READ_ONLY_LOOKUP_INTENTS_UNKNOWN_HOLD")

    def test_null_string_and_non_dict_originals_refused(self):
        for invalid in (None, "", [], (), False, 1, "SPENT"):
            with self.subTest(original=invalid):
                out = self.evaluate(original=invalid)
                self.assertEqual(out.query_intents, ())

    def test_all_bindings_are_immutable_flat_data_not_executable_callbacks(self):
        result = self.evaluate()
        for q in result.query_intents:
            self.assertIs(type(q.original_binding), tuple)
            self.assertTrue(all(
                type(k) is str and type(v) in (str, int)
                for k, v in q.original_binding
            ))


if __name__ == "__main__":
    unittest.main()
