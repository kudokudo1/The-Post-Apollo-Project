#!/usr/bin/env python3
"""Timezone conversion regression tests; uses host IANA zoneinfo only."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "services/time/TimeZoneConverter.py"
spec = importlib.util.spec_from_file_location("timew_zone_converter", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ConverterTests(unittest.TestCase):
    def test_regular_and_cross_date(self):
        x = module.convert("America/New_York", "Asia/Tokyo", "2026-10-22", "13:19")
        self.assertEqual(x["status"], "READY")
        self.assertIn("2026-10-23 02:19:00", x["options"][0]["destination"])
        self.assertEqual(x["options"][0]["source_offset"], "-0400")
        self.assertEqual(x["options"][0]["destination_offset"], "+0900")

    def test_winter_and_summer_offsets(self):
        winter = module.convert("America/New_York", "UTC", "2026-01-22", "13:00")
        summer = module.convert("America/New_York", "UTC", "2026-07-22", "13:00")
        self.assertEqual(winter["options"][0]["source_offset"], "-0500")
        self.assertEqual(summer["options"][0]["source_offset"], "-0400")
        self.assertIn("18:00", winter["options"][0]["destination"])
        self.assertIn("17:00", summer["options"][0]["destination"])

    def test_gap_explicit(self):
        x = module.convert("America/New_York", "UTC", "2026-03-08", "02:30")
        self.assertEqual(x["status"], "NONEXISTENT_LOCAL_TIME")
        self.assertEqual(x["options"], [])

    def test_fall_overlap_explicit(self):
        x = module.convert("America/New_York", "UTC", "2026-11-01", "01:30")
        self.assertEqual(x["status"], "AMBIGUOUS_LOCAL_TIME")
        self.assertEqual(len(x["options"]), 2)
        self.assertNotEqual(x["options"][0]["utc"], x["options"][1]["utc"])
        self.assertEqual({v["source_offset"] for v in x["options"]},
                         {"-0400", "-0500"})
        self.assertIn("05:30", x["options"][0]["destination"])
        self.assertIn("06:30", x["options"][1]["destination"])

    def test_non_hour_offset(self):
        x = module.convert("Asia/Kathmandu", "UTC", "2026-10-22", "14:45")
        self.assertEqual(x["status"], "READY")
        self.assertEqual(x["options"][0]["source_offset"], "+0545")
        self.assertIn("09:00", x["options"][0]["destination"])

    def test_unchanged_utc(self):
        x = module.convert("UTC", "UTC", "2026-10-22", "19:00")
        self.assertEqual(x["status"], "READY")
        self.assertEqual(len(x["options"]), 1)

    def test_invalid(self):
        values = [
            ("../etc/passwd", "UTC", "2026-10-22", "12:00"),
            ("UTC", "UTC", "2026-02-30", "12:00"),
            ("UTC", "UTC", "2026-10-22", "25:00"),
            ("UTC", "UTC", "1800-01-01", "12:00"),
            ("UTC", "Madeup/Nowhere", "2026-10-22", "12:00"),
        ]
        for args in values:
            with self.subTest(args=args):
                self.assertEqual(module.convert(*args)["options"], [])

    def test_cli_json_and_isolation(self):
        x = subprocess.check_output(
            [sys.executable, "-B", "-I", str(PATH),
             "UTC", "Europe/London", "2026-10-22", "19:00"],
            text=True, timeout=10)
        result = json.loads(x)
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["destination_zone"], "Europe/London")
        self.assertEqual(result["options"][0]["destination_offset"], "+0100")


if __name__ == "__main__":
    unittest.main()
