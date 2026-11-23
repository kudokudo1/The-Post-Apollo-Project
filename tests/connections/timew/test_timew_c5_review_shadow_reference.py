"""Adversarial DOC 5 C5 exact-value review shadow CI, zero native authority."""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import sys
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5SpendFenceReference import ACTION, AUDIENCE  # noqa: E402
from TimeWC5ReviewShadowReference import (  # noqa: E402
    SHADOW_SCHEMA, STEPS, _value, assess_review_shadow, review_lines,
)


def original_fixture():
    return {
        "schema": SHADOW_SCHEMA, "audience": AUDIENCE, "action": ACTION,
        "grant_id": str(uuid.uuid4()), "operation_id": str(uuid.uuid4()),
        "selection_sha256": "a" * 64, "source_sha256": "b" * 64,
        "intent_sha256": "c" * 64, "session_id": str(uuid.uuid4()),
        "seat_id": "seat0", "issuer_epoch": str(uuid.uuid4()),
        "issued_ms": 1000, "expires_ms": 1400,
        "checkpoint_id": str(uuid.uuid4()), "window_key": str(uuid.uuid4()),
        "boot_epoch": str(uuid.uuid4()), "surface_generation": 7,
        "output_id": "DP-1", "workspace_id": "workspace-2",
        "output_scale_hex": (1.25).hex(), "output_transform": 0,
        "before_value": _value.capture_value(
            _value.PHASE_CURRENT, x=259, y=92.5,
            width=1402, height=872),
        "target_value": _value.capture_value(
            _value.PHASE_PENDING, x=380.25, y=120.5,
            width=1200, height=700.5),
        "operation_steps": STEPS,
    }


def presented_fixture(original):
    return {**original, "review_lines": review_lines(original)}


class ExactReviewShadowTests(unittest.TestCase):
    def setUp(self):
        self.original = original_fixture()
        self.presented = presented_fixture(self.original)

    def evaluate(self, *, original=None, presented=None, now=1200,
                 unlocked=True, alive=True):
        result = assess_review_shadow(
            original=self.original if original is None else original,
            presented=self.presented if presented is None else presented,
            now_ms=now, seat_unlocked=unlocked, surface_alive=alive)
        for flag in (
            "production_authorized", "native_action_allowed",
            "human_consent_verified", "trusted_display_verified",
            "selected_surface_authenticated", "external_custody_verified",
            "spent_grant_verified", "native_terminal_receipt_verified",
            "retry_allowed", "undo_allowed",
        ):
            self.assertIs(result[flag], False)
        self.assertEqual(result["safe_actions"], [])
        return result["diagnostic"]

    def test_matching_full_review_is_still_never_authority(self):
        self.assertEqual(self.evaluate(), "MATCHED_BUT_UNTRUSTED_SHADOW_HOLD")
        text = "\n".join(self.presented["review_lines"])
        self.assertIn("y=92.5", text)
        self.assertIn("height=700.5", text)
        self.assertIn("0x1.", text)
        self.assertIn("observe-after-resize", text)

    def test_forged_extra_human_approval_flag_refuses(self):
        altered = {**self.presented, "operator_clicked_approve": True}
        self.assertEqual(self.evaluate(presented=altered),
                         "INCOMPLETE_OR_EXTRA_REVIEW_FIELDS_HOLD")

    def test_omitted_review_data_refuses(self):
        for field in ("review_lines", "before_value", "target_value",
                      "output_id", "window_key", "selection_sha256",
                      "seat_id", "operation_steps"):
            with self.subTest(field=field):
                altered = dict(self.presented)
                altered.pop(field)
                self.assertEqual(self.evaluate(presented=altered),
                                 "INCOMPLETE_OR_EXTRA_REVIEW_FIELDS_HOLD")

    def test_changed_fraction_versus_integer_is_mismatch(self):
        altered = dict(self.presented)
        altered["before_value"] = _value.capture_value(
            _value.PHASE_CURRENT, x=259, y=92,
            width=1402, height=872)
        self.assertEqual(self.evaluate(presented=altered),
                         "REVIEW_OR_INTENT_MISMATCH_HOLD")

    def test_one_ulp_mismatch_even_when_visually_similar(self):
        altered = dict(self.presented)
        altered["before_value"] = _value.capture_value(
            _value.PHASE_CURRENT, x=259, y=math.nextafter(92.5, 93),
            width=1402, height=872)
        self.assertEqual(self.evaluate(presented=altered),
                         "REVIEW_OR_INTENT_MISMATCH_HOLD")

    def test_changed_target_fraction_is_mismatch(self):
        altered = dict(self.presented)
        altered["target_value"] = _value.capture_value(
            _value.PHASE_PENDING, x=380.25, y=120.5,
            width=1200, height=700)
        self.assertEqual(self.evaluate(presented=altered),
                         "REVIEW_OR_INTENT_MISMATCH_HOLD")

    def test_display_omits_fraction_or_exact_hex_refuses(self):
        for tamper in (
            lambda x: x.replace("y=92.5", "y=92"),
            lambda x: x.replace("[0x1.", "[0x0."),
        ):
            with self.subTest(tamper=tamper.__code__.co_firstlineno):
                altered = dict(self.presented)
                altered["review_lines"] = tuple(tamper(s) for s in
                                                self.presented["review_lines"])
                self.assertEqual(self.evaluate(presented=altered),
                                 "DISPLAY_NOT_EXACT_HOLD")

    def test_list_instead_of_strict_tuple_refuses(self):
        altered = {**self.presented,
                   "review_lines": list(self.presented["review_lines"])}
        self.assertEqual(self.evaluate(presented=altered),
                         "DISPLAY_NOT_EXACT_HOLD")

    def test_different_grant_operation_intent_source_and_issuer_refuses(self):
        cases = {
            "grant_id": str(uuid.uuid4()),
            "operation_id": str(uuid.uuid4()),
            "selection_sha256": "d" * 64,
            "source_sha256": "e" * 64,
            "intent_sha256": "f" * 64,
            "session_id": str(uuid.uuid4()),
            "seat_id": "seat1",
            "issuer_epoch": str(uuid.uuid4()),
            "audience": "postapollo.hospital.room",
            "action": "delete-room",
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                altered = {**self.presented, field: value}
                self.assertIn(
                    self.evaluate(presented=altered),
                    {"REVIEW_OR_INTENT_MISMATCH_HOLD",
                     "INVALID_PRESENTED_REVIEW_HOLD"},
                )

    def test_changed_checkpoint_window_lifetime_and_output_refuses(self):
        cases = {
            "checkpoint_id": str(uuid.uuid4()),
            "window_key": str(uuid.uuid4()),
            "boot_epoch": str(uuid.uuid4()),
            "surface_generation": 8,
            "output_id": "DP-2",
            "workspace_id": "workspace-3",
            "output_scale_hex": (1.5).hex(),
            "output_transform": 1,
            "operation_steps": ("move", "resize", "verify-final"),
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                altered = {**self.presented, field: value}
                self.assertIn(
                    self.evaluate(presented=altered),
                    {"REVIEW_OR_INTENT_MISMATCH_HOLD",
                     "INVALID_PRESENTED_REVIEW_HOLD"},
                )

    def test_changed_binary64_phase_refuses(self):
        altered = dict(self.presented)
        altered["before_value"] = replace(self.original["before_value"],
                                         phase=_value.PHASE_PENDING)
        self.assertEqual(self.evaluate(presented=altered),
                         "INVALID_PRESENTED_REVIEW_HOLD")

    def test_invalid_signed_zero_and_nan_bits_refuse(self):
        for bits in (0x8000000000000000, 0x7ff8000000000000):
            with self.subTest(bits=bits):
                altered = dict(self.presented)
                altered["before_value"] = replace(
                    self.original["before_value"], y_bits=bits)
                self.assertEqual(self.evaluate(presented=altered),
                                 "INVALID_PRESENTED_REVIEW_HOLD")

    def test_bool_generation_transform_and_noncanonical_scale_refuse(self):
        for field, value in (
            ("surface_generation", True),
            ("output_transform", True),
            ("output_scale_hex", "1.25"),
            ("output_scale_hex", "nan"),
        ):
            with self.subTest(field=field, value=value):
                altered = {**self.presented, field: value}
                self.assertEqual(self.evaluate(presented=altered),
                                 "INVALID_PRESENTED_REVIEW_HOLD")

    def test_locked_seat_or_dead_selected_surface_refuses(self):
        self.assertEqual(self.evaluate(unlocked=False),
                         "NO_ACTIVE_SELECTED_SURFACE_OR_UNLOCKED_SEAT_HOLD")
        self.assertEqual(self.evaluate(alive=False),
                         "NO_ACTIVE_SELECTED_SURFACE_OR_UNLOCKED_SEAT_HOLD")
        # Fake truthy values must not masquerade as genuine bools.
        self.assertEqual(self.evaluate(unlocked=1),
                         "NO_ACTIVE_SELECTED_SURFACE_OR_UNLOCKED_SEAT_HOLD")

    def test_expired_or_not_yet_valid_and_invalid_clock_refuses(self):
        for now, diagnostic in (
            (999, "EXPIRED_OR_NOT_YET_VALID_HOLD"),
            (1400, "EXPIRED_OR_NOT_YET_VALID_HOLD"),
            (True, "INVALID_CLOCK_HOLD"),
            (1200.0, "INVALID_CLOCK_HOLD"),
        ):
            with self.subTest(now=now):
                self.assertEqual(self.evaluate(now=now), diagnostic)

    def test_tampered_original_does_not_rewrite_permission(self):
        altered = dict(self.original)
        altered["issuer_epoch"] = "untrusted-host"
        self.assertEqual(self.evaluate(original=altered),
                         "INVALID_ORIGINAL_HOLD")

    def test_generated_display_is_not_proof_of_real_human_view(self):
        # Even an exact generated string is caller-controlled; it proves no
        # trusted compositor frame, physical presence or protected C5 spend.
        altered = presented_fixture(self.original)
        self.assertEqual(self.evaluate(presented=altered),
                         "MATCHED_BUT_UNTRUSTED_SHADOW_HOLD")


if __name__ == "__main__":
    unittest.main()
