#!/usr/bin/env python3
"""TimeW elapsed duration regression suite; no system mutations."""
from importlib import util
from pathlib import Path
import json
import subprocess
import sys
import unittest

FILE = Path(__file__).resolve().parents[2] / "services/time/TimeArithmetic.py"
spec = util.spec_from_file_location("timew_elapsed_math", FILE)
math = util.module_from_spec(spec)
spec.loader.exec_module(math)


class ArithmeticTests(unittest.TestCase):
    def calc(self, zone="UTC", date="2026-10-22", time="13:19",
             action="add", days="0", hours="0", minutes="0"):
        return math.arithmetic(zone, date, time, action, days, hours, minutes)

    def test_day_rollover_and_subtraction(self):
        x = self.calc(hours="12")
        self.assertEqual(x["status"], "READY")
        self.assertIn("2026-10-23 01:19:00", x["options"][0]["result"])
        y = self.calc(action="subtract", hours="24")
        self.assertIn("2026-10-21 13:19:00", y["options"][0]["result"])
        self.assertEqual(y["elapsed_minutes"], -1440)

    def test_24_hours_elapsed_is_not_wall_day_across_dst(self):
        x = self.calc("America/New_York", "2026-03-07", "12:00",
                      days="1")
        self.assertEqual(x["status"], "READY")
        self.assertIn("2026-03-08 13:00:00", x["options"][0]["result"])
        self.assertIn("EDT (-0400)", x["options"][0]["result"])
        y = self.calc("America/New_York", "2026-11-01", "00:30",
                      hours="2")
        self.assertIn("2026-11-01 01:30:00 EST (-0500)",
                      y["options"][0]["result"])

    def test_nonexistent_hour_rejected(self):
        x = self.calc("America/New_York", "2026-03-08", "02:30", hours="1")
        self.assertEqual(x["status"], "NONEXISTENT_LOCAL_TIME")
        self.assertEqual(x["options"], [])

    def test_ambiguous_hour_both_folds(self):
        x = self.calc("America/New_York", "2026-11-01", "01:30", hours="1")
        self.assertEqual(x["status"], "AMBIGUOUS_LOCAL_TIME")
        self.assertEqual(len(x["options"]), 2)
        self.assertIn("01:30:00 EST (-0500)", x["options"][0]["result"])
        self.assertIn("02:30:00 EST (-0500)", x["options"][1]["result"])

    def test_partial_hour_and_minute(self):
        x = self.calc("Asia/Kathmandu", "2026-10-22", "23:45",
                      minutes="30")
        self.assertIn("2026-10-23 00:15:00", x["options"][0]["result"])
        x = self.calc("UTC", "2026-10-22", "00:05", "subtract",
                      "1", "0", "15")
        self.assertIn("2026-10-20 23:50:00", x["options"][0]["result"])

    def test_zero_duration_is_stable(self):
        x = self.calc(days="0", hours="0", minutes="0")
        self.assertEqual(x["status"], "READY")
        self.assertEqual(x["elapsed_minutes"], 0)
        self.assertEqual(x["options"][0]["source"], x["options"][0]["result"])

    def test_invalid_or_unbounded(self):
        invalid = [
            {"zone": "../etc/passwd"}, {"zone": "Nowhere/Nobody"},
            {"date": "2026-02-31"}, {"time": "24:00"},
            {"action": "multiply"}, {"days": "-1"}, {"days": "9999"},
            {"hours": "1000"}, {"minutes": "60"}, {"minutes": "hello"},
            {"days": ""}, {"time": "13:19//PM"}, {"date": "1800-01-01"},
        ]
        for patch in invalid:
            with self.subTest(patch=patch):
                self.assertEqual(self.calc(**patch)["options"], [])

    def test_cli_json(self):
        data = subprocess.check_output(
            [sys.executable, "-B", "-I", str(FILE),
             "America/New_York", "2026-10-22", "13:19",
             "add", "0", "12", "0"], text=True, timeout=10)
        parsed = json.loads(data)
        self.assertEqual(parsed["status"], "READY")
        self.assertIn("2026-10-23 01:19:00", parsed["options"][0]["result"])


if __name__ == "__main__":
    unittest.main()
