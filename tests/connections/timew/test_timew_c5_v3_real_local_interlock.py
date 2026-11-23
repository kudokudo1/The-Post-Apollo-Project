#!/usr/bin/env python3
"""DOC 5 / TimeW V3 real local SQLite integration, DENY ONLY.

This tests the merged TimeW v3 ordinary capture store alongside DOC 5's
rollbackable local C5 fixture in disposable directories. It DOES NOT join
their trust, write operator data, issue consent, authorize native commands,
read authentic SwayPX, or create a protected custodian. Even a local SPENT
row + exact saved CURRENT + visually matching geometry is no authority.
"""
from __future__ import annotations

from dataclasses import replace
import math
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "time"))
sys.path.insert(0, str(ROOT / "tests" / "connections" / "timew"))

from MachineV2ExactLogicalGeometry import (  # noqa: E402
    PHASE_CURRENT, PHASE_PENDING, capture_value, read_value,
)
from MachineV2FractionalObservationReview import (  # noqa: E402
    review_untrusted_candidate,
)
from MachineV3LocalExactCaptureStore import (  # noqa: E402
    DB_NAME, LocalCaptureRefused, LocalExactCaptureStore,
)
from TimeWC5SpendFenceReference import (  # noqa: E402
    ACTION, AUDIENCE, ReferenceRefused, TestOnlyC5Fence,
)


def uid():
    return str(uuid.uuid4())


def current(*, x=259, y=92.5, width=1402, height=872):
    return capture_value(PHASE_CURRENT, x=x, y=y, width=width, height=height)


def claim():
    return {
        "audience": AUDIENCE,
        "action": ACTION,
        "grant_id": uid(),
        "operation_id": uid(),
        "selection_sha256": uuid.uuid4().hex * 2,
        "intent_sha256": uuid.uuid4().hex * 2,
        "source_sha256": uuid.uuid4().hex * 2,
        "session_id": uid(),
        "seat_id": "seat0",
        "issuer_epoch": uid(),
        "issued_ms": 1000,
        "expires_ms": 1500,
    }


class V3CaptureC5NonAuthorityTests(unittest.TestCase):
    """Real file-backed local integration, never a production security test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="timew-c5-v3-only-")
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.v3path = root / "post-apollo" / "machine" / DB_NAME
        self.c5path = root / "c5-development-only.db"
        self.v3 = LocalExactCaptureStore(self.v3path)
        self.c5 = TestOnlyC5Fence(self.c5path)
        self.c5.initialize_fixture()
        self.checkpoint_id = uid()
        self.window_key = uid()
        self.item = claim()

    def capture(self, *, value=None):
        return self.v3.save(
            checkpoint_id=self.checkpoint_id, window_key=self.window_key,
            app_id="foot", output_id="DP-1", workspace_id="3",
            value=current() if value is None else value,
        )

    def assert_v3_denies(self, entry):
        self.assertTrue(entry["local_capture_only"])
        for flag in (
            "source_authenticated", "operator_selection_verified",
            "production_restore_allowed", "c5_spent_verified",
            "terminal_receipt_verified", "automatic_retry_allowed",
            "automatic_undo_allowed",
        ):
            self.assertIs(entry[flag], False, flag)
        self.assertEqual(entry["safe_actions"], [])

    def assert_c5_denies(self, outcome):
        for flag in (
            "production_authorized", "native_action_allowed",
            "production_revocation_ack", "retry_allowed", "undo_allowed",
        ):
            self.assertIs(outcome[flag], False, flag)
        self.assertEqual(outcome["safe_actions"], [])

    def assert_observation_denies(self, outcome):
        self.assertTrue(outcome["read_only"])
        for flag in (
            "restore_allowed", "native_action_allowed",
            "selected_surface_authenticated",
            "compositor_source_authenticated", "configure_ack_verified",
            "final_frame_settled", "c5_consent_spent_verified",
        ):
            self.assertIs(outcome[flag], False, flag)
        self.assertTrue(outcome["no_automatic_retry"])
        self.assertTrue(outcome["no_automatic_undo"])
        self.assertEqual(outcome["safe_actions"], [])

    def test_normal_local_capture_and_independent_c5_absence(self):
        capture_id = self.capture()
        entry = self.v3.get(capture_id)
        self.assert_v3_denies(entry)
        self.assertEqual(read_value(entry["value"]), (259, 92.5, 1402, 872))
        self.assert_c5_denies(self.c5.inspect_fixture(self.item["grant_id"]))
        self.assertEqual(
            self.c5.inspect_fixture(self.item["grant_id"])["fixture_state"],
            "ABSENT_UNKNOWN_HOLD",
        )

    def test_active_grant_is_not_authority_for_saved_geometry(self):
        capture_id = self.capture()
        self.assert_c5_denies(self.c5.register_fixture(self.item))
        self.assertEqual(
            self.c5.inspect_fixture(self.item["grant_id"])["fixture_state"],
            "ACTIVE_UNTRUSTED_FIXTURE",
        )
        self.assert_v3_denies(self.v3.get(capture_id))

    def test_local_spent_and_exact_v3_capture_never_authorize(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        spent = self.c5.spend_fixture(self.item, now_ms=1100)
        self.assertEqual(spent["fixture_state"], "SPENT_UNKNOWN_HOLD")
        self.assert_c5_denies(spent)
        self.assert_v3_denies(self.v3.get(capture_id))
        self.assert_c5_denies(self.c5.inspect_fixture(self.item["grant_id"]))
        self.assertEqual(
            self.c5.inspect_fixture(self.item["grant_id"])["fixture_state"],
            "SPENT_UNKNOWN_HOLD",
        )

    def test_real_local_c5_spent_rollback_and_respend_is_still_denied(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        old_bytes = self.c5path.read_bytes()
        self.assert_c5_denies(self.c5.spend_fixture(self.item, now_ms=1100))
        self.assertEqual(
            self.c5.inspect_fixture(self.item["grant_id"])["fixture_state"],
            "SPENT_UNKNOWN_HOLD",
        )
        # The same user's old SQLite image is writable and rollbackable.
        self.c5path.write_bytes(old_bytes)
        self.assertEqual(
            self.c5.inspect_fixture(self.item["grant_id"])["fixture_state"],
            "ACTIVE_UNTRUSTED_FIXTURE",
        )
        replayed_local = self.c5.spend_fixture(self.item, now_ms=1101)
        self.assertEqual(replayed_local["fixture_state"], "SPENT_UNKNOWN_HOLD")
        self.assert_c5_denies(replayed_local)
        self.assert_v3_denies(self.v3.get(capture_id))

    def test_lost_spent_reply_does_not_make_captured_state_retryable(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)  # Model lost response
        reopened = TestOnlyC5Fence(self.c5path)
        result = reopened.inspect_fixture(self.item["grant_id"])
        self.assertEqual(result["fixture_state"], "SPENT_UNKNOWN_HOLD")
        self.assert_c5_denies(result)
        self.assert_v3_denies(LocalExactCaptureStore(self.v3path).get(capture_id))
        with self.assertRaises(ReferenceRefused):
            reopened.spend_fixture(self.item, now_ms=1101)

    def test_c5_store_disappears_but_v3_data_survives(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        self.c5path.unlink()
        self.assert_v3_denies(self.v3.get(capture_id))
        with self.assertRaises(ReferenceRefused):
            self.c5.inspect_fixture(self.item["grant_id"])
        self.assertFalse(self.c5path.exists(), "read must never recreate missing C5 DB")

    def test_valid_ulp_local_capture_tamper_does_not_become_receipt(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        one_ulp = current(y=math.nextafter(92.5, math.inf))
        with sqlite3.connect(self.v3path) as db:
            db.execute(
                "UPDATE exact_captures SET y_bits=? WHERE id=?",
                (format(one_ulp.y_bits, "016x"), capture_id),
            )
            db.commit()
        entry = self.v3.get(capture_id)
        self.assertEqual(entry["value"].y_bits, one_ulp.y_bits)
        self.assertNotEqual(entry["value"].y_bits, current().y_bits)
        self.assert_v3_denies(entry)
        self.assert_c5_denies(self.c5.inspect_fixture(self.item["grant_id"]))

    def test_source_and_selection_cannot_be_inferred_from_window_id(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        entry = self.v3.get(capture_id)
        self.assertEqual(entry["window_key"], self.window_key)
        # C5 fixture selection digest is unrelated to an authentic SwayPX
        # selected native surface; even a matching supplied identifier is not proof.
        self.assert_v3_denies(entry)
        self.assert_c5_denies(self.c5.inspect_fixture(self.item["grant_id"]))

    def test_bad_c5_seat_or_intent_does_not_taint_v3_saved_state(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        for key, other in (
            ("seat_id", "seat1"),
            ("source_sha256", "0" * 64),
            ("selection_sha256", "f" * 64),
            ("intent_sha256", "e" * 64),
            ("operation_id", uid()),
        ):
            with self.subTest(key=key):
                bad = dict(self.item, **{key: other})
                with self.assertRaises(ReferenceRefused):
                    self.c5.spend_fixture(bad, now_ms=1100)
                self.assert_v3_denies(self.v3.get(capture_id))

    def test_expired_local_grant_cannot_reuse_saved_capture(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        with self.assertRaises(ReferenceRefused):
            self.c5.spend_fixture(self.item, now_ms=self.item["expires_ms"])
        self.assert_v3_denies(self.v3.get(capture_id))
        self.assert_c5_denies(self.c5.inspect_fixture(self.item["grant_id"]))

    def test_pre_spend_revoke_and_post_spend_revoke_both_hold(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.assert_c5_denies(self.c5.revoke_fixture(self.item["grant_id"]))
        with self.assertRaises(ReferenceRefused):
            self.c5.spend_fixture(self.item, now_ms=1100)
        self.assert_v3_denies(self.v3.get(capture_id))

        second = claim()
        self.c5.register_fixture(second)
        self.c5.spend_fixture(second, now_ms=1100)
        outcome = self.c5.revoke_fixture(second["grant_id"])
        self.assertEqual(outcome["fixture_state"],
                         "SPENT_REVOCATION_PENDING_UNKNOWN_HOLD")
        self.assert_c5_denies(outcome)
        self.assert_v3_denies(self.v3.get(capture_id))

    def test_exact_matching_ready_values_after_local_spent_still_hold(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        before = self.v3.get(capture_id)["value"]
        target = capture_value(PHASE_PENDING, x=380.25, y=120.5,
                               width=1200, height=700.5)
        after_resize = current(x=259, y=92.5, width=1200, height=700.5)
        final = current(x=380.25, y=120.5, width=1200, height=700.5)
        result = review_untrusted_candidate(
            before_current=before, target_pending=target,
            post_resize_current=after_resize, final_current=final,
            resize_stage="READY_REPORTED", move_stage="READY_REPORTED",
        )
        self.assertEqual(result["status"], "MATCHED_VALUES_UNTRUSTED_HOLD")
        self.assert_observation_denies(result)

    def test_timeout_current_copy_with_local_spent_prevents_followon_move(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        before = self.v3.get(capture_id)["value"]
        target = capture_value(PHASE_PENDING, x=380.25, y=120.5,
                               width=1200, height=700.5)
        after_resize = current(width=1200, height=700.5)
        final = current(x=380.25, y=120.5, width=1200, height=700.5)
        result = review_untrusted_candidate(
            before_current=before, target_pending=target,
            post_resize_current=after_resize, final_current=final,
            resize_stage="TIMEOUT_FORCED", move_stage="READY_REPORTED",
        )
        self.assertEqual(result["status"], "UNKNOWN_HOLD")
        self.assert_observation_denies(result)

    def test_matching_spent_cannot_hide_bit_exact_final_mismatch(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        before = self.v3.get(capture_id)["value"]
        target = capture_value(PHASE_PENDING, x=380.25, y=120.5,
                               width=1200, height=700.5)
        after_resize = current(width=1200, height=700.5)
        final = current(x=380.25, y=math.nextafter(120.5, math.inf),
                        width=1200, height=700.5)
        result = review_untrusted_candidate(
            before_current=before, target_pending=target,
            post_resize_current=after_resize, final_current=final,
            resize_stage="READY_REPORTED", move_stage="READY_REPORTED",
        )
        self.assertEqual(result["status"], "GEOMETRY_MISMATCH_HOLD")
        self.assert_observation_denies(result)

    def test_v3_duplicate_saved_window_rejected_even_with_local_spent(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        with self.assertRaises(LocalCaptureRefused):
            self.capture(value=current(x=260))
        self.assert_v3_denies(self.v3.get(capture_id))

    def test_spend_with_no_local_v3_snapshot_still_no_capture_authority(self):
        self.c5.register_fixture(self.item)
        result = self.c5.spend_fixture(self.item, now_ms=1100)
        self.assert_c5_denies(result)
        self.assertFalse(self.v3path.exists())
        self.assertEqual(self.v3.for_checkpoint(self.checkpoint_id), [])

    def test_fresh_process_reopen_preserves_data_not_consent_proof(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        code = r'''
import sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
from MachineV3LocalExactCaptureStore import LocalExactCaptureStore
from TimeWC5SpendFenceReference import TestOnlyC5Fence
from MachineV2ExactLogicalGeometry import read_value
entry = LocalExactCaptureStore(sys.argv[3]).get(sys.argv[4])
outcome = TestOnlyC5Fence(sys.argv[5]).inspect_fixture(sys.argv[6])
assert read_value(entry["value"]) == (259, 92.5, 1402, 872)
assert entry["production_restore_allowed"] is False
assert entry["source_authenticated"] is False
assert entry["c5_spent_verified"] is False
assert entry["safe_actions"] == []
assert outcome["fixture_state"] == "SPENT_UNKNOWN_HOLD"
assert outcome["native_action_allowed"] is False
assert outcome["safe_actions"] == []
'''
        result = subprocess.run(
            [sys.executable, "-B", "-I", "-c", code,
             str(ROOT / "services" / "time"),
             str(ROOT / "tests" / "connections" / "timew"),
             str(self.v3path), capture_id, str(self.c5path),
             self.item["grant_id"]],
            capture_output=True, timeout=12, check=False,
        )
        self.assertEqual(result.returncode, 0,
                         result.stderr.decode(errors="replace"))

    def test_no_legacy_timew_database_or_native_side_effect(self):
        capture_id = self.capture()
        self.c5.register_fixture(self.item)
        self.c5.spend_fixture(self.item, now_ms=1100)
        self.assert_v3_denies(self.v3.get(capture_id))
        self.assertFalse((self.v3path.parent / "machine.db").exists())
        self.assertFalse(
            (self.v3path.parent / "v2-geometry-operations.db").exists())
        self.assertEqual(tuple(self.v3path.parent.iterdir()), (self.v3path,))


if __name__ == "__main__":
    unittest.main()
