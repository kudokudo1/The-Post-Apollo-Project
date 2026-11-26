#!/usr/bin/env python3
"""Verify independent timing receipt and reject invalid capture bounds."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
import cpuplus_stall_clock_witness as witness

class WitnessTests(unittest.TestCase):
    def test_receipt(self):
        with patch.object(witness.time,"monotonic_ns",side_effect=[10_000_000,5_010_000_000]), \
             patch.object(witness.time,"time_ns",side_effect=[100_000_000_000,105_000_000_000]), \
             patch.object(witness.time,"sleep") as sleep:
            self.assertEqual(witness.observe(5),{"schema":"post-apollo-stall-clock-v1",
                "durationSeconds":5,"startWallMs":100000,"endWallMs":105000,"elapsedMs":5000})
            sleep.assert_called_once_with(5)
    def test_bounds(self):
        for invalid in (True,4,121,5.0):
            with self.assertRaises(ValueError):
                witness.observe(invalid)

if __name__=="__main__":
    unittest.main()
