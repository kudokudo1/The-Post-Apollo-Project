"""Autoscroll engine: stationary sustained rate, cancellation, target safety."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/input"))
from AutoscrollMouseEngine import (MouseAutoscroll, BTN_LEFT, BTN_RIGHT,
                                    BTN_MIDDLE, speed, MAX_SPEED_PX_S)


class MouseEngine(unittest.TestCase):
    def test_button_toggles_rate_mode_without_replaying_middle(self):
        e = MouseAutoscroll()
        self.assertTrue(e.key_event(BTN_MIDDLE, 1, 1.0, "seat0:17"))
        self.assertTrue(e.active)
        self.assertTrue(e.key_event(BTN_MIDDLE, 0, 1.001, "seat0:17"))
        self.assertTrue(e.motion(0, 140))
        first = e.tick(1.020, 19, "seat0:17")
        second = e.tick(1.040, 20, "seat0:17")
        self.assertLess(first[0], 0)
        self.assertLess(second[0], 0)
        # Same displacement: scroll persists without any new mouse motion.
        self.assertTrue(e.active)
        self.assertTrue(e.key_event(BTN_MIDDLE, 1, 1.050, "seat0:17"))
        self.assertFalse(e.active)
        self.assertEqual(e.tick(1.060, 10, "seat0:17"), (0, 0))
        self.assertTrue(e.key_event(BTN_MIDDLE, 0, 1.070, "seat0:17"))

    def test_deadzone_speed_reversal_and_horizontal(self):
        self.assertEqual(speed(15), 0)
        self.assertEqual(speed(-15), 0)
        self.assertGreater(speed(200), speed(40))
        self.assertLessEqual(speed(90000), MAX_SPEED_PX_S)
        e = MouseAutoscroll()
        e.key_event(BTN_MIDDLE, 1, 0, "focus")
        e.motion(200, -150)
        v,h = e.tick(0.016, 16, "focus")
        self.assertGreater(v, 0)
        self.assertGreater(h, 0)
        e.motion(-400, 300)
        v,h = e.tick(0.032, 16, "focus")
        self.assertLess(v, 0)
        self.assertLess(h, 0)

    def test_idle_motion_and_left_click_pass_through(self):
        e = MouseAutoscroll()
        self.assertFalse(e.motion(6, 5))
        self.assertFalse(e.key_event(BTN_LEFT, 1, 0, "focus"))
        self.assertFalse(e.key_event(BTN_LEFT, 0, 0, "focus"))
        self.assertTrue(e.key_event(BTN_MIDDLE, 1, 0, "focus"))
        self.assertTrue(e.key_event(BTN_RIGHT, 1, .01, "focus"))
        self.assertFalse(e.active)
        self.assertTrue(e.key_event(BTN_RIGHT, 0, .02, "focus"))
        self.assertFalse(e.key_event(BTN_RIGHT, 1, .03, "focus"))

    def test_focus_change_or_loss_stops_emission(self):
        for target in ("other-window", None):
            e = MouseAutoscroll()
            e.key_event(BTN_MIDDLE, 1, 0, "app")
            e.motion(0, 300)
            self.assertEqual(e.tick(.015, 15, target), (0, 0))
            self.assertFalse(e.active)
            self.assertEqual(e.last_stop, "focus_lost")

    def test_timeout_and_invalid_frame_fail_closed(self):
        for dt, now, reason in ((101, .200, "stale_tick"),
                                (16, 181.0, "time_limit")):
            e = MouseAutoscroll()
            e.key_event(BTN_MIDDLE, 1, 0, "app")
            e.motion(0, 300)
            self.assertEqual(e.tick(now, dt, "app"), (0,0))
            self.assertFalse(e.active)
            self.assertEqual(e.last_stop, reason)

    def test_middle_without_focus_never_enters_mode(self):
        e = MouseAutoscroll()
        self.assertTrue(e.key_event(BTN_MIDDLE, 1, 0, None))
        self.assertFalse(e.active)
        self.assertTrue(e.key_event(BTN_MIDDLE, 0, .01, None))

    def test_invalid_motion_cancels(self):
        e = MouseAutoscroll()
        e.key_event(BTN_MIDDLE, 1, 0, "app")
        self.assertTrue(e.motion(float("nan"), 5))
        self.assertFalse(e.active)
        self.assertEqual(e.last_stop, "invalid_motion")

    def test_service_shutdown_clears_active_state(self):
        e = MouseAutoscroll()
        e.key_event(BTN_MIDDLE, 1, 0, "app")
        e.motion(0, 200)
        e.cancel("service_stopped")
        self.assertFalse(e.active)
        self.assertIsNone(e.anchor_target)
        self.assertEqual(e.tick(.05, 16, "app"), (0, 0))


if __name__ == "__main__":
    unittest.main()
