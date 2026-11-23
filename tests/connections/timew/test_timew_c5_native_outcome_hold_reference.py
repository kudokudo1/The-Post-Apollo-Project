"""DOC 5: synthetic SPENT ↔ SwayPX stage ambiguity, all cases deny."""
from __future__ import annotations

from dataclasses import replace
import sys
from pathlib import Path
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from TimeWC5SpendFenceReference import ACTION, AUDIENCE  # noqa: E402
from TimeWC5ReviewShadowReference import (  # noqa: E402
    SHADOW_SCHEMA, STEPS, _value,
)
from TimeWC5NativeOutcomeHoldReference import (  # noqa: E402
    EVENT_KINDS, evaluate_native_outcome_shadow, original_event_context,
)


def original():
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


def events_for(o, *kinds):
    context = original_event_context(o)
    return tuple({"kind": kind, "context": dict(context)} for kind in kinds)


SPENT = "C5_SPENT_REPORTED"
RESIZE = "RESIZE_DISPATCH_REPORTED"
READY = "RESIZE_READY_CALLBACK"
TIMEOUT = "RESIZE_TIMER_TIMEOUT"
CURRENT = "RESIZE_CURRENT_COPIED"
SCENE = "RESIZE_SCENE_ARRANGED"
PRESENT = "RESIZE_PRESENT_REPORTED"
MOVE = "MOVE_DISPATCH_REPORTED"


class NativeOutcomeHoldTests(unittest.TestCase):
    def setUp(self):
        self.original = original()

    def evaluate(self, kinds=(), *, ledger="SPENT", journal="DISPATCHING",
                 now=1200, raw=None, original_override=None):
        o = self.original if original_override is None else original_override
        trace = events_for(o, *kinds) if raw is None else raw
        result = evaluate_native_outcome_shadow(
            original=o, ledger_state=ledger, journal_stage=journal,
            events=trace, now_ms=now,
        )
        for flag in (
            "production_authorized", "native_action_allowed",
            "human_consent_verified", "trusted_source_verified",
            "protected_spent_verified", "terminal_settlement_verified",
            "revocation_acknowledged", "move_continuation_allowed",
            "retry_allowed", "undo_allowed",
        ):
            self.assertIs(result[flag], False)
        self.assertEqual(result["safe_actions"], [])
        return result["diagnostic"]

    def test_spent_with_local_prepared_is_unknown(self):
        self.assertEqual(self.evaluate((SPENT,), journal="PREPARED"),
                         "SPENT_BUT_LOCAL_PREPARED_UNKNOWN_HOLD")

    def test_spent_local_prepared_but_resize_said_sent_is_unknown(self):
        self.assertEqual(self.evaluate((SPENT, RESIZE), journal="PREPARED"),
                         "SPENT_WITH_PREPARED_AND_EFFECT_UNKNOWN_HOLD")

    def test_real_normal_stage_pattern_never_proves_terminal(self):
        self.assertEqual(self.evaluate((SPENT, RESIZE, READY, CURRENT, SCENE)),
                         "CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD")

    def test_fake_normal_presentation_remains_untrusted(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, READY, CURRENT, SCENE, PRESENT)),
            "PRESENT_REPORTED_BUT_UNAUTHENTICATED_HOLD")

    def test_real_timeout_then_current_and_scene_remain_unknown(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, TIMEOUT, CURRENT, SCENE)),
            "TIMEOUT_CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD")

    def test_timeout_followed_by_late_ready_does_not_clear_taint(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, TIMEOUT, READY, CURRENT, SCENE,
                           PRESENT)),
            "TIMEOUT_CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD")

    def test_timeout_with_no_current_is_still_unknown(self):
        self.assertEqual(self.evaluate((SPENT, RESIZE, TIMEOUT)),
                         "RESIZE_TIMEOUT_UNKNOWN_HOLD")

    def test_followon_move_after_timeout_always_holds(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, TIMEOUT, CURRENT, SCENE, MOVE)),
            "FOLLOWON_MOVE_AFTER_TIMEOUT_UNKNOWN_HOLD")

    def test_move_even_after_normal_reported_present_never_authorized(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, READY, CURRENT, SCENE,
                           PRESENT, MOVE, "MOVE_PRESENT_REPORTED")),
            "MOVE_REPORTED_WITHOUT_TRUSTED_TERMINAL_UNKNOWN_HOLD")

    def test_move_without_prior_resize_holds(self):
        self.assertEqual(self.evaluate((SPENT, MOVE)), "MOVE_WITHOUT_RESIZE_HOLD")

    def test_move_callback_without_dispatch_holds(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, "MOVE_READY_CALLBACK")),
            "MOVE_CALLBACK_WITHOUT_DISPATCH_HOLD")

    def test_resize_callback_before_dispatch_holds(self):
        for event in (READY, TIMEOUT, CURRENT, SCENE, PRESENT):
            with self.subTest(event=event):
                self.assertEqual(
                    self.evaluate((SPENT, event)),
                    "RESIZE_CALLBACK_WITHOUT_DISPATCH_HOLD")

    def test_resize_dispatch_before_spent_report_refuses(self):
        self.assertEqual(self.evaluate((RESIZE, SPENT)),
                         "RESIZE_BEFORE_SPENT_REPORT_HOLD")

    def test_second_grant_spend_and_resize_attempts_refuse(self):
        self.assertEqual(
            self.evaluate((SPENT, "SECOND_SPEND_REPORTED")),
            "SECOND_SPEND_ATTEMPT_HOLD")
        self.assertEqual(
            self.evaluate((SPENT, SPENT)),
            "DUPLICATE_OR_REVOKED_SPEND_HOLD")
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, "SECOND_RESIZE_REPORTED")),
            "SECOND_RESIZE_ATTEMPT_HOLD")
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, RESIZE)),
            "DUPLICATE_RESIZE_DISPATCH_HOLD")

    def test_wrong_ledger_state_with_resize_effect_refuses(self):
        for state in ("ACTIVE", "REVOKED", "UNKNOWN"):
            with self.subTest(state=state):
                self.assertEqual(
                    self.evaluate((SPENT, RESIZE), ledger=state),
                    "EFFECT_WITHOUT_SPENT_LEDGER_UNKNOWN_HOLD")

    def test_post_spend_revocation_never_acknowledges_cancel(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, "C5_REVOKE_REQUESTED", CURRENT)),
            "POST_SPENT_REVOCATION_UNKNOWN_HOLD")

    def test_revocation_before_spend_blocks_spend(self):
        self.assertEqual(
            self.evaluate(("C5_REVOKE_REQUESTED", SPENT), ledger="ACTIVE"),
            "DUPLICATE_OR_REVOKED_SPEND_HOLD")

    def test_lost_ack_after_dispatch_stays_unknown(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, "ACK_LOST_REPORTED")),
            "LOST_ACK_OR_HOST_EXIT_UNKNOWN_HOLD")

    def test_host_exit_after_spend_stays_unknown(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE, "HOST_EXIT_REPORTED")),
            "LOST_ACK_OR_HOST_EXIT_UNKNOWN_HOLD")

    def test_missing_spent_record_never_implies_unspent_permission(self):
        self.assertEqual(self.evaluate(()),
                         "NO_SPENT_EVIDENCE_UNKNOWN_HOLD")
        self.assertEqual(self.evaluate((SPENT,)),
                         "SPENT_WITHOUT_RESIZE_EVIDENCE_UNKNOWN_HOLD")

    def test_expiry_after_spend_does_not_allow_retry(self):
        self.assertEqual(
            self.evaluate((SPENT, RESIZE), now=1400),
            "EXPIRED_OR_NOT_YET_ISSUED_RECOVERY_HOLD")
        self.assertEqual(
            self.evaluate((SPENT, RESIZE), now=999),
            "EXPIRED_OR_NOT_YET_ISSUED_RECOVERY_HOLD")

    def test_wrong_grant_seat_surface_and_exact_binary64_geometry_refuses(self):
        for key, value in (
            ("grant_id", str(uuid.uuid4())),
            ("operation_id", str(uuid.uuid4())),
            ("issuer_epoch", str(uuid.uuid4())),
            ("seat_id", "seat1"),
            ("session_id", str(uuid.uuid4())),
            ("selection_sha256", "f" * 64),
            ("source_sha256", "f" * 64),
            ("intent_sha256", "f" * 64),
            ("checkpoint_id", str(uuid.uuid4())),
            ("window_key", str(uuid.uuid4())),
            ("boot_epoch", str(uuid.uuid4())),
            ("surface_generation", 8),
            ("output_id", "DP-2"),
            ("workspace_id", "workspace-9"),
            ("output_scale_hex", (1.5).hex()),
            ("output_transform", 2),
            ("before_value", _value.capture_value(
                _value.PHASE_CURRENT, x=259, y=92.0,
                width=1402, height=872)),
            ("target_value", _value.capture_value(
                _value.PHASE_PENDING, x=380.25, y=120.5,
                width=1200, height=700.0)),
        ):
            with self.subTest(key=key):
                trace = list(events_for(self.original, SPENT, RESIZE))
                trace[1]["context"][key] = value
                self.assertEqual(
                    self.evaluate(raw=tuple(trace)),
                    "CHANGED_OPERATION_OR_SOURCE_HOLD")

    def test_invalid_event_shape_and_forged_trust_flag_rejected(self):
        base = list(events_for(self.original, SPENT))
        base[0]["native_action_allowed"] = True
        self.assertEqual(self.evaluate(raw=tuple(base)),
                         "MALFORMED_EVENT_HOLD")
        base = list(events_for(self.original, SPENT))
        base[0]["context"]["attested"] = True
        self.assertEqual(self.evaluate(raw=tuple(base)),
                         "MALFORMED_EVENT_HOLD")

    def test_invalid_event_container_and_excessive_trace_refuse(self):
        self.assertEqual(self.evaluate(raw=[]),
                         "INVALID_EVENT_CONTAINER_HOLD")
        self.assertEqual(
            self.evaluate(raw=events_for(self.original, *([SPENT] * 65))),
            "INVALID_EVENT_CONTAINER_HOLD")

    def test_unsupported_stage_and_boolean_clock_refuse(self):
        self.assertEqual(self.evaluate(journal="RESTORED"),
                         "INVALID_JOURNAL_STAGE_HOLD")
        self.assertEqual(self.evaluate(ledger="AUTHORIZED"),
                         "INVALID_LEDGER_STATE_HOLD")
        self.assertEqual(self.evaluate(now=True),
                         "INVALID_CLOCK_HOLD")

    def test_forged_original_invalid_and_wrong_purpose_refuse(self):
        o = dict(self.original)
        o["action"] = "post-apollo.hospital.restore"
        self.assertEqual(self.evaluate(original_override=o, raw=()),
                         "INVALID_ORIGINAL_HOLD")

    def test_even_complete_fixture_journal_and_perfect_events_remain_hold(self):
        self.assertEqual(self.evaluate(
            (SPENT, RESIZE, READY, CURRENT, SCENE, PRESENT,
             MOVE, "MOVE_READY_CALLBACK", "MOVE_CURRENT_COPIED",
             "MOVE_SCENE_ARRANGED", "MOVE_PRESENT_REPORTED"),
            journal="FIXTURE_COMPLETE"),
            "MOVE_REPORTED_WITHOUT_TRUSTED_TERMINAL_UNKNOWN_HOLD")

    def test_fixed_event_set_contains_no_authority_signal(self):
        forbidden = ("APPROVE", "AUTHORIZE", "SIGNED", "CONSENT_GRANTED",
                     "PRODUCTION", "SETTLED_PROVEN")
        for k in EVENT_KINDS:
            self.assertFalse(any(token in k for token in forbidden))
        self.assertEqual(self.evaluate(raw=events_for(
            self.original, "C5_SPENT_REPORTED", "RESIZE_DISPATCH_REPORTED",
            "RESIZE_TIMER_TIMEOUT", "RESIZE_CURRENT_COPIED")),
            "TIMEOUT_CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD")


if __name__ == "__main__":
    unittest.main()
