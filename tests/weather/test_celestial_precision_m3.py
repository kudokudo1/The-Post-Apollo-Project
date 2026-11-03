"""M3 numerical hardening: tangent contacts, close misses, station sensitivity."""
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract
import celestial_dynamics as dynamics

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def days(t):
    return (t - BASE).total_seconds() / 86400


def instant(day):
    return (BASE + timedelta(days=day)).isoformat().replace("+00:00", "Z")


class TangentContactTests(unittest.TestCase):
    def test_grazing_sextile_without_crossing(self):
        # The 60-degree target is touched but never crossed.
        a = lambda t: (60 + 0.25 * (days(t) - 5.3) ** 2) % 360
        b = lambda t: 0.0
        old = dynamics.find_aspect_events(a, b, instant(0), instant(10), 12)
        self.assertFalse(any(e["name"] == "sextile" for e in old))
        found = dynamics.find_tangent_aspect_events(a, b, instant(0), instant(10), 12)
        sextiles = [e for e in found if e["name"] == "sextile"]
        self.assertEqual(len(sextiles), 1)
        e = sextiles[0]
        self.assertEqual(e["contact_kind"], "tangent_candidate")
        self.assertEqual(e["orientation_deg"], 60)
        self.assertLess(e["residual_deg"], 0.00001)
        self.assertLess(abs((dynamics._utc(e["time_utc"]) -
                            dynamics._utc(instant(5.3))).total_seconds()), 2)

    def test_grazing_conjunction_across_360(self):
        a = lambda t: (-0.2 * (days(t) - 4.7) ** 2) % 360
        found = dynamics.find_tangent_aspect_events(
            a, lambda t: 0.0, instant(0), instant(10), 6)
        contacts = [e for e in found if e["name"] == "conjunction"]
        self.assertEqual(len(contacts), 1)
        self.assertLess(contacts[0]["residual_deg"], 0.00001)
        self.assertLess(abs((dynamics._utc(contacts[0]["time_utc"]) -
                             dynamics._utc(instant(4.7))).total_seconds()), 2)

    def test_clear_near_miss_does_not_invent_contact(self):
        a = lambda t: (60 + 0.02 + 0.25 * (days(t) - 5.3) ** 2) % 360
        contacts = dynamics.find_tangent_aspect_events(
            a, lambda t: 0.0, instant(0), instant(10), 12)
        self.assertFalse(any(e["name"] == "sextile" for e in contacts))

    def test_near_miss_within_tolerance_labeled_as_candidate(self):
        a = lambda t: (60 + 0.000003 + 0.25 * (days(t) - 5.3) ** 2) % 360
        contacts = dynamics.find_tangent_aspect_events(
            a, lambda t: 0.0, instant(0), instant(10), 12)
        sextile = next(e for e in contacts if e["name"] == "sextile")
        self.assertGreater(sextile["residual_deg"], 0)
        self.assertGreaterEqual(sextile["angular_tolerance_deg"], sextile["residual_deg"])

    def test_reject_invalid_tolerance_and_high_motion(self):
        for bad in (0, -0.1, float("nan"), True, .5):
            with self.subTest(tolerance=bad), self.assertRaises(contract.ContractError):
                dynamics.find_tangent_aspect_events(
                    lambda t: 60, lambda t: 0, instant(0), instant(10),
                    tangent_tolerance_deg=bad)
        with self.assertRaisesRegex(contract.ContractError, "large relative"):
            dynamics.find_tangent_aspect_events(
                lambda t: (180 * days(t)) % 360,
                lambda t: 0, instant(0), instant(2), 24)

    def test_constant_exact_longitude_is_not_an_instantaneous_event(self):
        contacts = dynamics.find_tangent_aspect_events(
            lambda t: 60, lambda t: 0, instant(0), instant(10), 12)
        self.assertEqual(contacts, [])

    def test_station_times_stable_for_smooth_parabola(self):
        a = lambda t: (100 - 0.05 * (days(t) - 5.33) ** 2) % 360
        times = []
        for window in (1, 3, 6, 12):
            events = dynamics.find_station_events(
                a, instant(0), instant(10), 12, window)
            self.assertEqual(len(events), 1)
            times.append(dynamics._utc(events[0]["time_utc"]))
        self.assertLess((max(times) - min(times)).total_seconds(), 2)


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"), "DE440s integration requires explicit kernel")
class RealKernelTests(unittest.TestCase):
    def test_opt_in_does_not_change_sun_moon_conjunctions(self):
        query = {
            "format": dynamics.FORMAT, "mode": "aspects",
            "start_utc": "2026-10-01T00:00:00Z",
            "end_utc": "2026-11-01T00:00:00Z",
            "bodies": ["moon", "sun"], "step_hours": 6,
        }
        kernel = os.environ["MAGICK_M1_KERNEL"]
        original = dynamics.event_report(query, kernel)
        newer = dynamics.event_report(dict(query, detect_tangents=True), kernel)
        old_crossings = [(e["name"], e["time_utc"]) for e in original["events"]]
        new_crossings = [(e["name"], e["time_utc"]) for e in newer["events"]
                         if e["contact_kind"] == "crossing"]
        self.assertEqual(old_crossings, new_crossings)
        self.assertFalse(newer["complete_for_tangent_contacts"])
        self.assertEqual(newer["tangent_detection"], "sampled_local_extrema_only")
        self.assertTrue(all(e["contact_kind"] in ("crossing", "tangent_candidate")
                            for e in newer["events"]))

    def test_opt_in_requires_boolean_and_aspect_mode(self):
        query = {
            "format": dynamics.FORMAT, "mode": "aspects",
            "start_utc": "2026-10-01T00:00:00Z",
            "end_utc": "2026-10-02T00:00:00Z",
            "bodies": ["moon", "sun"], "detect_tangents": "yes",
        }
        with self.assertRaisesRegex(contract.ContractError, "boolean"):
            dynamics.event_report(query, os.environ["MAGICK_M1_KERNEL"])
        query["detect_tangents"] = True
        query["mode"] = "stations"
        query["bodies"] = ["mercury"]
        with self.assertRaisesRegex(contract.ContractError, "only supports aspects"):
            dynamics.event_report(query, os.environ["MAGICK_M1_KERNEL"])


if __name__ == "__main__":
    unittest.main()
