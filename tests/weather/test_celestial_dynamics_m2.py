"""MAGICK M2: math edge cases and optional real JPL integration.

Run offline: python3 -m unittest discover -s tests/weather -p 'test_celestial_dynamics_m2.py' -v
Real DE440s: MAGICK_M1_KERNEL=/path/to/de440s.bsp before the same command.
"""
from datetime import datetime, timedelta, timezone
import math
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract
import celestial_dynamics as dynamics
import celestial_solver as solver

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def days(t):
    return (t - T0).total_seconds() / 86400.0


def iso(t):
    return t.isoformat().replace("+00:00", "Z")


def at(day):
    return iso(T0 + timedelta(days=day))


class PureLongitudeTests(unittest.TestCase):
    def test_wraparound_and_actual_longitude_not_three_dimensional_angle(self):
        self.assertAlmostEqual(dynamics.longitude_separation(359, 1), 2)
        self.assertAlmostEqual(dynamics.circular_difference(1, 359), 2)
        self.assertAlmostEqual(dynamics.circular_difference(359, 1), -2)
        self.assertAlmostEqual(dynamics.longitude_separation(1, 181), 180)
        self.assertAlmostEqual(dynamics.longitude_separation(45, 45), 0)

    def test_aspect_orb_and_classification(self):
        actual = dynamics.aspects_at(359, 1, 3)
        self.assertEqual(actual[0]["name"], "conjunction")
        self.assertAlmostEqual(actual[0]["signed_orb_deg"], 2)
        self.assertEqual(dynamics.aspects_at(359, 1, 1), [])
        self.assertEqual(dynamics.aspects_at(0, 60, 0)[0]["name"], "sextile")
        self.assertEqual(dynamics.aspects_at(0, 240, 0)[0]["name"], "trine")
        self.assertEqual(dynamics.aspects_at(0, 180, 0)[0]["name"], "opposition")
        with self.assertRaises(contract.ContractError):
            dynamics.aspects_at(0, 0, float("nan"))
        with self.assertRaises(contract.ContractError):
            dynamics.aspects_at(False, 45)

    def test_exact_conjunction_through_360_wrap(self):
        a = lambda t: (350 + 3 * days(t)) % 360
        b = lambda t: 0
        found = dynamics.find_aspect_events(a, b, at(0), at(5), 12)
        conjunction = [e for e in found if e["name"] == "conjunction"]
        self.assertEqual(len(conjunction), 1)
        self.assertLess(abs((dynamics._utc(conjunction[0]["time_utc"]) -
                             (T0 + timedelta(days=10 / 3))).total_seconds()), 1)
        self.assertLess(conjunction[0]["separation_deg"], .001)

    def test_exact_sextile_orientation_and_boundary_deduplication(self):
        a = lambda t: (6 * days(t)) % 360
        b = lambda t: 0
        found = dynamics.find_aspect_events(a, b, at(0), at(12), 24)
        sextile = [e for e in found if e["name"] == "sextile"]
        self.assertEqual(len(sextile), 1)
        self.assertEqual(sextile[0]["orientation_deg"], 60)
        self.assertLess(abs((dynamics._utc(sextile[0]["time_utc"]) -
                             (T0 + timedelta(days=10))).total_seconds()), 1)
        conjunction = [e for e in found if e["name"] == "conjunction"]
        self.assertEqual(len(conjunction), 1)

    def test_station_both_directions_from_parabolic_longitude(self):
        retro = lambda t: (100 - (days(t) - 5) ** 2) % 360
        direct = lambda t: (100 + (days(t) - 5) ** 2) % 360
        a = dynamics.find_station_events(retro, at(0), at(10), 12, 3)
        b = dynamics.find_station_events(direct, at(0), at(10), 12, 3)
        self.assertEqual([e["name"] for e in a], ["direct_to_retrograde"])
        self.assertEqual([e["name"] for e in b], ["retrograde_to_direct"])
        self.assertLess(abs((dynamics._utc(a[0]["time_utc"]) -
                             (T0 + timedelta(days=5))).total_seconds()), 1)
        self.assertAlmostEqual(a[0]["longitude_deg"], 100, delta=.0001)

    def test_circular_velocity_near_zero_crossing(self):
        a = lambda t: (359 + days(t)) % 360
        self.assertAlmostEqual(dynamics.longitude_rate(a, T0 + timedelta(days=2), 6),
                               1, delta=1e-9)

    def test_refuse_invalid_unbounded_and_ambiguous_queries(self):
        for invalid in [
            ("2026-02-30T00:00:00Z", at(1)),
            (at(1), at(0)),
            (at(0), at(367)),
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(contract.ContractError):
                dynamics.find_aspect_events(lambda t: 0, lambda t: 20, *invalid)
        with self.assertRaisesRegex(contract.ContractError, "too many"):
            dynamics.find_station_events(lambda t: 0, at(0), at(366), 1)
        with self.assertRaisesRegex(contract.ContractError, "large relative"):
            dynamics.find_aspect_events(lambda t: (180 * days(t)) % 360,
                                        lambda t: 0, at(0), at(2), 24)

    def test_no_provider_or_kernel_silently_selected(self):
        query = {"format": dynamics.FORMAT, "mode": "stations",
                 "start_utc": at(0), "end_utc": at(10),
                 "bodies": ["mercury"]}
        with self.assertRaisesRegex(contract.ContractError, "existing local"):
            dynamics.event_report(query, "/missing/kernel/de440s.bsp")
        bad = dict(query, bodies=["earth"])
        with self.assertRaises(contract.ContractError):
            dynamics.event_report(bad, "/missing/kernel/de440s.bsp")
        bad = dict(query, start_utc="2026-01-01T00:00:00-05:00")
        with self.assertRaises(contract.ContractError):
            dynamics.event_report(bad, "/missing/kernel/de440s.bsp")


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"), "real DE440s needed")
class JplDynamicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = os.environ["MAGICK_M1_KERNEL"]

    def test_real_mercury_stations_2026(self):
        query = {
            "format": dynamics.FORMAT,
            "mode": "stations",
            "start_utc": "2026-01-01T00:00:00Z",
            "end_utc": "2026-12-31T00:00:00Z",
            "bodies": ["mercury"],
            "step_hours": 24,
            "rate_window_hours": 6,
        }
        report = dynamics.event_report(query, self.kernel)
        events = report["events"]
        self.assertGreaterEqual(len(events), 4)
        self.assertTrue(any(e["name"] == "direct_to_retrograde" for e in events))
        self.assertTrue(any(e["name"] == "retrograde_to_direct" for e in events))
        self.assertEqual(report["provenance"]["ephemeris_id"], "de440s.bsp")
        self.assertEqual(len(report["provenance"]["ephemeris_sha256"]), 64)
        self.assertFalse(report["complete_for_tangent_contacts"])
        self.assertTrue(all(e["time_utc"].endswith("Z") for e in events))

    def test_real_sun_moon_aspects_agree_with_m1(self):
        query = {
            "format": dynamics.FORMAT, "mode": "aspects",
            "start_utc": "2026-10-01T00:00:00Z",
            "end_utc": "2026-12-01T00:00:00Z",
            "bodies": ["moon", "sun"], "step_hours": 12,
        }
        events = dynamics.event_report(query, self.kernel)["events"]
        self.assertGreaterEqual(len(events), 8)
        self.assertTrue(any(e["name"] == "conjunction" for e in events))
        self.assertTrue(any(e["name"] == "opposition" for e in events))
        chosen = next(e for e in events if e["name"] == "conjunction")
        req = {
            "format": contract.REQUEST_FORMAT, "instant_utc": chosen["time_utc"],
            "origin": "geocentric", "position_model": "apparent",
            "frame": contract.FRAME, "bodies": ["moon", "sun"]
        }
        snapshot = solver.compute_snapshot(req, self.kernel)
        positions = {p["body"]: p["longitude_deg"] for p in snapshot["positions"]}
        self.assertLess(dynamics.longitude_separation(positions["moon"],
                                                      positions["sun"]), .002)


if __name__ == "__main__":
    unittest.main()
