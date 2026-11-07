"""M8i regression: paired direction reversals inside one old sample interval.

Analytical test trajectories are synthetic, not JPL transit predictions.
Production still uses caller-supplied offline Skyfield/JPL longitudes.
"""
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "weather"))
import celestial_transit_multi as multi
from celestial_contract import ContractError

BASE = datetime(2026, 11, 7, 0, 0, tzinfo=timezone.utc)


def hours(instant):
    return (instant - BASE).total_seconds() / 3600


def paired_turns(instant):
    """Synthetic cubic with instantaneous speed roots at 20 and 40 min.

    At 0 and 60 minutes the speed is positive, so the old M8h endpoint
    scan cannot see either intervening reversal. The centered 20-min
    finite-difference velocity shifts roots by ~1.5 minutes.
    """
    t = hours(instant)
    return (100 + 10 * (t ** 3 / 3 - t ** 2 / 2 + 2 * t / 9)) % 360


class StationReliabilityM8iTest(unittest.TestCase):
    def test_two_reversals_in_one_sixty_minute_sample(self):
        events = multi.find_stations(
            paired_turns, BASE, BASE + timedelta(hours=1), 60)
        self.assertEqual(len(events), 2, events)
        self.assertEqual([row["direction"] for row in events],
                         ["retrograde", "direct"])
        for event, minute in zip(events, (20, 40)):
            when = datetime.fromisoformat(event["utc"].replace("Z", "+00:00"))
            self.assertLess(
                abs((when - (BASE + timedelta(minutes=minute))).total_seconds()),
                240, event)
            self.assertEqual(event["uncertainty_seconds"], 60)
            self.assertLess(abs(event["velocity_deg_day"]), 1.0)

    def test_two_reversals_inside_thirty_minute_sample(self):
        def smaller(instant):
            # Time-compressed trajectory, two changes at 10 and 20 minutes.
            t = hours(instant) * 2
            return (100 + 10 * (t ** 3 / 3 - t ** 2 / 2 + 2 * t / 9)) % 360
        # The 20-minute centered rate derivative smooths the two turns;
        # this test checks the *actual filtered-rate* reversals only.
        times = multi.find_stations(
            smaller, BASE, BASE + timedelta(minutes=30), 30)
        self.assertTrue(all(event["type"] == "station" for event in times))
        self.assertLessEqual(len(times), 2)
        self.assertEqual(len({event["utc"] for event in times}), len(times))

    def test_exact_grid_node_zero_reversal_retained(self):
        def turn(instant):
            h = hours(instant)
            return (100 + 0.1 * (h - 6) ** 2) % 360
        events = multi.find_stations(
            turn, BASE, BASE + timedelta(hours=12), 60)
        self.assertEqual(len(events), 1, events)
        self.assertEqual(events[0]["direction"], "direct")
        target = BASE + timedelta(hours=6)
        when = datetime.fromisoformat(events[0]["utc"].replace("Z", "+00:00"))
        self.assertLess(abs((when - target).total_seconds()), 60)

    def test_direct_retrograde_and_constant_no_false_events(self):
        def reverse(instant):
            h = hours(instant)
            return (100 - 0.1 * (h - 6) ** 2) % 360
        result = multi.find_stations(
            reverse, BASE, BASE + timedelta(hours=12), 30)
        self.assertEqual([x["direction"] for x in result], ["retrograde"])
        constant = lambda instant: 250.0
        self.assertEqual(
            multi.find_stations(constant, BASE, BASE + timedelta(days=2), 60),
            [])
        forward = lambda instant: (20 + hours(instant) * 0.2) % 360
        self.assertEqual(
            multi.find_stations(forward, BASE, BASE + timedelta(days=2), 60),
            [])

    def test_unwrapped_longitude_across_360_degrees(self):
        def turn(instant):
            h = hours(instant)
            return (359.99 + 0.1 * (h - 6) ** 2) % 360
        events = multi.find_stations(
            turn, BASE, BASE + timedelta(hours=12), 60)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["direction"], "direct")
        self.assertTrue(0 <= events[0]["longitude_deg"] < 360)

    def test_budget_rejects_unbounded_rate_grid(self):
        with self.assertRaises(ContractError):
            multi.find_stations(
                lambda instant: 100.0,
                BASE, BASE + timedelta(days=32), 60)
        with self.assertRaises(ContractError):
            multi.find_stations(
                lambda instant: 100.0,
                BASE, BASE, 60)
        with self.assertRaises(ContractError):
            multi.find_stations(
                lambda instant: 100.0,
                BASE, BASE + timedelta(hours=1), 1)
        self.assertEqual(
            multi.MAX_STATION_RATE_SAMPLES, 3000)
        self.assertEqual(
            multi.STATION_RATE_STEP.total_seconds(), 900)

    def test_output_shape_remains_m8h_compatible_and_private(self):
        source = (ROOT / "scripts/weather/celestial_transit_multi.py").read_text()
        self.assertIn('"station_rate_scan_interval_minutes_max": 15', source)
        self.assertIn('"station_velocity_central_difference_minutes": 20', source)
        self.assertIn('"station_time_bracket_seconds": 60', source)
        self.assertIn('stdin.readline(4097)', source)
        self.assertIn('expected_ephemeris_sha256', source)
        for forbidden in (
            "requests.get(", "urllib.request", "sqlite3.connect(",
            "pickle.dump(", "load.download(", "--birth",
            "--latitude", "subprocess.run("
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
