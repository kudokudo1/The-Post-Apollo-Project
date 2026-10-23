#!/usr/bin/env python3
"""Difference regressions including DST folds, gaps, time zones and sign."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

FILE = Path(__file__).resolve().parents[2] / "services/time/TimeDifference.py"
spec = importlib.util.spec_from_file_location("timew_diff", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class DifferenceTests(unittest.TestCase):
    def check(self, *args):
        return mod.difference(*args)

    def test_same_instant_across_zones(self):
        x = self.check("America/New_York", "2026-10-22", "13:19",
                       "Asia/Tokyo", "2026-10-23", "02:19")
        self.assertEqual(x["status"], "READY")
        self.assertEqual(len(x["options"]), 1)
        self.assertEqual(x["options"][0]["total_minutes"], 0)

    def test_positive_and_negative(self):
        args = ("UTC", "2026-10-22", "10:00", "UTC", "2026-10-25", "12:15")
        x = self.check(*args)
        self.assertEqual(x["options"][0]["total_minutes"], 3 * 1440 + 135)
        self.assertEqual({k: x["options"][0][k] for k in ("sign", "days", "hours", "minutes")},
                         {"sign": "+", "days": 3, "hours": 2, "minutes": 15})
        y = self.check(*args[3:], *args[:3])
        self.assertEqual(y["options"][0]["total_minutes"], -(3 * 1440 + 135))
        self.assertEqual((y["options"][0]["sign"], y["options"][0]["days"]),
                         ("-", 3))

    def test_spring_forward_elapsed_not_wall(self):
        x = self.check("America/New_York", "2026-03-08", "01:30",
                       "America/New_York", "2026-03-08", "03:30")
        self.assertEqual(x["status"], "READY")
        self.assertEqual(x["options"][0]["total_minutes"], 60)
        self.assertIn("EST (-0500)", x["options"][0]["start"])
        self.assertIn("EDT (-0400)", x["options"][0]["end"])

    def test_gap_at_either_endpoint(self):
        a = self.check("America/New_York", "2026-03-08", "02:30",
                       "UTC", "2026-03-08", "12:00")
        b = self.check("UTC", "2026-03-08", "12:00",
                       "America/New_York", "2026-03-08", "02:30")
        self.assertEqual(a["status"], "START_NONEXISTENT_LOCAL_TIME")
        self.assertEqual(b["status"], "END_NONEXISTENT_LOCAL_TIME")
        self.assertEqual(a["options"], [])

    def test_ambiguous_start_has_two_choices(self):
        x = self.check("America/New_York", "2026-11-01", "01:30",
                       "UTC", "2026-11-01", "07:30")
        self.assertEqual(x["status"], "AMBIGUOUS_LOCAL_TIME")
        self.assertTrue(x["ambiguous_start"])
        self.assertFalse(x["ambiguous_end"])
        self.assertEqual([option["total_minutes"] for option in x["options"]],
                         [120, 60])
        self.assertEqual({o["start"][-12:].strip() for o in x["options"]},
                         {"EDT (-0400)", "EST (-0500)"})

    def test_two_ambiguous_endpoints_have_four_combinations(self):
        x = self.check("America/New_York", "2026-11-01", "01:30",
                       "America/New_York", "2026-11-01", "01:30")
        self.assertEqual(len(x["options"]), 4)
        self.assertTrue(x["ambiguous_start"] and x["ambiguous_end"])
        self.assertEqual(sorted(o["total_minutes"] for o in x["options"]),
                         [-60, 0, 0, 60])

    def test_quarter_hour_offset(self):
        x = self.check("Asia/Kathmandu", "2026-10-22", "14:45",
                       "UTC", "2026-10-22", "10:00")
        self.assertEqual(x["options"][0]["total_minutes"], 60)

    def test_inputs_and_unavailable_zones(self):
        cases = [
            ("America/Bad;rm", "2026-10-22", "10:00", "UTC", "2026-10-22", "10:00"),
            ("UTC", "2026-02-30", "10:00", "UTC", "2026-10-22", "10:00"),
            ("UTC", "2026-10-22", "25:00", "UTC", "2026-10-22", "10:00"),
            ("UTC", "2026-10-22", "10:00", "UTC", "2026-10-22", "99:00"),
            ("UTC", "1800-01-01", "12:00", "UTC", "2026-10-22", "10:00"),
            ("UTC", "2026-10-22", "10:00", "Invalid/Planet", "2026-10-22", "10:00"),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(self.check(*args)["options"], [])

    def test_isolated_cli_json(self):
        process = subprocess.check_output(
            [sys.executable, "-B", "-I", str(FILE),
             "UTC", "2026-10-22", "10:00", "UTC", "2026-10-22", "13:30"],
            text=True, timeout=10)
        result = json.loads(process)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["options"][0]["total_minutes"], 210)


if __name__ == "__main__":
    unittest.main()
