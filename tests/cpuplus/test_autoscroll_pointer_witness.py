"""Pointer-target witness validation: candidate geometry != compositor trust."""
from dataclasses import replace
from pathlib import Path
import sys
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/input"))
import AutoscrollPointerWitness as witness

T = 1_000_000_000
LAYOUT = [
    {"name": "DP-2", "x": -1920, "y": 0,
     "width": 1920, "height": 1080, "scale": 1.0},
    {"name": "HDMI-A-1", "x": 0, "y": 0,
     "width": 2560, "height": 1440, "scale": 1.25}
]
EVENT = {"seat": "seat0", "device": "111:222:Mouse",
         "output": "DP-2", "x": 100, "y": 400,
         "target_node": 42, "event_time_ns": T - 10_000_000,
         "generation": 5}


def check(ev=None, before=None, after=None, **kw):
    return witness.check_candidate(
        ev if ev is not None else EVENT,
        before if before is not None else LAYOUT,
        after if after is not None else LAYOUT,
        expected_device=kw.get("device", "111:222:Mouse"),
        expected_seat=kw.get("seat", "seat0"),
        expected_generation=kw.get("generation", 5),
        now_ns=kw.get("now", T),
    )


class PointerWitnessContracts(unittest.TestCase):
    def test_negative_layout_and_local_to_global_position(self):
        result = check()
        self.assertEqual(result.output, "DP-2")
        self.assertEqual((result.global_x, result.global_y), (-1820, 400))
        self.assertEqual(result.target_node, 42)
        self.assertEqual(result.seat, "seat0")
        self.assertFalse(result.source_trusted)
        self.assertFalse(result.overlay_allowed)
        self.assertFalse(result.live_input_allowed)

    def test_valid_geometry_does_not_authorize_input_or_overlay(self):
        record = check()
        self.assertFalse(record.source_trusted)
        self.assertFalse(record.live_input_allowed)
        self.assertFalse(record.overlay_allowed)
        self.assertIsNone(witness.trusted_compositor_pointer_provider())
        with self.assertRaisesRegex(
            witness.WitnessError, "COMPOSITOR_POINTER_TARGET_UNAVAILABLE"
        ):
            witness.require_verified_pointer_provider()

    def test_old_future_and_replayed_witness_refused(self):
        for age in (witness.MAX_EVENT_AGE_NS + 1,
                    -(witness.MAX_FUTURE_SKEW_NS + 1)):
            with self.subTest(age=age):
                ev = dict(EVENT, event_time_ns=T - age)
                with self.assertRaisesRegex(
                    witness.WitnessError, "STALE_OR_FUTURE_WITNESS"
                ):
                    check(ev)
        with self.assertRaisesRegex(witness.WitnessError, "STALE_GENERATION"):
            check(generation=6)

    def test_wrong_device_or_seat_and_missing_target_refused(self):
        with self.assertRaisesRegex(witness.WitnessError, "WRONG_DEVICE_OR_SEAT"):
            check(device="Other:Mouse")
        with self.assertRaisesRegex(witness.WitnessError, "WRONG_DEVICE_OR_SEAT"):
            check(seat="seat1")
        for target in (None, 0, -1, True, "42"):
            with self.subTest(target=target):
                with self.assertRaisesRegex(witness.WitnessError,
                                            "NO_POINTER_TARGET"):
                    check(dict(EVENT, target_node=target))

    def test_changed_monitor_geometry_or_scale_refused(self):
        changed = [dict(LAYOUT[0]),
                   dict(LAYOUT[1], x=-1800)]
        with self.assertRaisesRegex(witness.WitnessError, "OUTPUT_LAYOUT_CHANGED"):
            check(after=changed)
        scaled = [dict(LAYOUT[0], scale=1.5), LAYOUT[1]]
        with self.assertRaisesRegex(witness.WitnessError, "OUTPUT_LAYOUT_CHANGED"):
            check(after=scaled)

    def test_disconnected_or_out_of_bounds_witness_refused(self):
        with self.assertRaisesRegex(witness.WitnessError, "OUTPUT_DISCONNECTED"):
            check(dict(EVENT, output="MISSING"))
        for x, y in ((-1, 0), (1920, 0), (0, 1080),
                     (float("nan"), 1), (0, float("inf"))):
            with self.subTest(x=x, y=y):
                with self.assertRaises(witness.WitnessError):
                    check(dict(EVENT, x=x, y=y))

    def test_ambiguous_monitor_overlap_refused(self):
        layout = [
            dict(LAYOUT[0]),
            dict(LAYOUT[1], x=-1850)
        ]
        with self.assertRaisesRegex(
            witness.WitnessError, "AMBIGUOUS_OUTPUT_OVERLAP"
        ):
            check(before=layout, after=layout)

    def test_duplicate_output_and_bad_layout_refused(self):
        for layout in ([LAYOUT[0], LAYOUT[0]], [],
                       [dict(LAYOUT[0], width=0)],
                       [dict(LAYOUT[0], scale=float("nan"))],
                       [dict(LAYOUT[0], name="../wrong")]):
            with self.assertRaises(witness.WitnessError):
                check(before=layout, after=layout)

    def test_self_proclaimed_authority_cannot_cross_boundary(self):
        for claim in ({"authorized": True}, {"compositor_signed": True},
                      {"runtime_enabled": True}, {"source_trusted": True}):
            with self.subTest(claim=claim):
                with self.assertRaisesRegex(
                    witness.WitnessError, "INVALID_WITNESS_FIELDS"
                ):
                    check(dict(EVENT, **claim))

    def test_no_unverified_environment_override(self):
        code = (ROOT / "services/input/AutoscrollPointerWitness.py").read_text()
        for marker in ("getenv(", "environ[", "shell=True", "swaymsg",
                       "wayland-info", "UInput(", "InputDevice(", "eval("):
            self.assertNotIn(marker, code)


if __name__ == "__main__":
    unittest.main()
