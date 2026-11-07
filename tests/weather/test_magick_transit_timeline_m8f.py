"""M8f independent source-contract and synthetic numerical crossing checks.

Fixture functions are analytical angular trajectories, never claimed to be
actual astronomical predictions. Full JPL kernel comparison is a separate
operator acceptance gate.
"""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "weather"))
import celestial_transit_timeline as transit
from celestial_contract import ContractError

ORIGIN = datetime(2026, 11, 7, 0, 0, tzinfo=timezone.utc)


def request(**kw):
    r = {
        "format": transit.FORMAT,
        "natal_epoch_utc": "2000-03-21T15:20:00Z",
        "start_utc": "2026-11-07T00:00:00Z",
        "end_utc": "2026-11-14T00:00:00Z",
        "latitude_deg": 38.9, "longitude_deg": -76.8,
        "expected_ephemeris_sha256": "a" * 64,
        "natal_body": "venus", "transit_body": "moon",
        "sample_minutes": 60,
        "aspects_deg": [0, 60, 90, 120, 180],
    }
    r.update(kw)
    return r


def linear(start_angle, speed_per_hour):
    def value(t):
        delta = (t - ORIGIN).total_seconds() / 3600
        return (start_angle + delta * speed_per_hour) % 360
    return value


class M8fTransitTest(unittest.TestCase):
    def test_strict_request_and_no_profile_guess(self):
        n = transit.normalize(request())
        self.assertEqual(n["natal_body"], "venus")
        self.assertEqual(n["aspects_deg"], [0, 60, 90, 120, 180])
        self.assertEqual(n["latitude_deg"], 38.9)
        for change in (
            {"format": "fake"},
            {"natal_body": "not-a-body"},
            {"transit_body": "mars"},
            {"start_utc": "2026-11-07T00:00:00-05:00"},
            {"end_utc": "2026-11-07T00:00:00Z"},
            {"end_utc": "2026-12-14T00:00:00Z"},
            {"end_utc": "2026-02-29T00:00:00Z"},
            {"sample_minutes": 15},
            {"sample_minutes": True},
            {"aspects_deg": []},
            {"aspects_deg": [45]},
            {"aspects_deg": [90, 90]},
            {"latitude_deg": 92},
            {"longitude_deg": -185},
            {"latitude_deg": True},
            {"expected_ephemeris_sha256": "wrong"},
        ):
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    transit.normalize(request(**change))
        with self.assertRaises(ContractError):
            transit.normalize({**request(), "birth_name": "secret"})

    def test_conjunction_through_zero_360_wrap_refines_exact_utc(self):
        # Natal longitude 350°, transit starts 340° and advances 2°/hour.
        # Exact conjunction is 5 hours after the start.
        samples, contacts, total = transit.search(
            linear(340, 2), 350, ORIGIN, ORIGIN+timedelta(hours=12),
            60, [0])
        self.assertEqual(total, 13)
        self.assertEqual(len(samples), 3, "six-hour plot cadence")
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["utc"], "2026-11-07T05:00:00Z")
        self.assertEqual(contacts[0]["aspect"], "conjunction")
        self.assertEqual(contacts[0]["direction"], "prograde")
        self.assertLess(contacts[0]["residual_deg"], 0.001)

    def test_retrograde_square_crossing_and_signed_angular_math(self):
        _, contacts, _ = transit.search(
            linear(115, -2), 20, ORIGIN, ORIGIN+timedelta(hours=6),
            30, [90])
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["utc"], "2026-11-07T02:30:00Z")
        self.assertEqual(contacts[0]["aspect"], "square")
        self.assertEqual(contacts[0]["direction"], "retrograde")
        self.assertAlmostEqual(transit.signed_step(359, 1), 2)
        self.assertAlmostEqual(transit.signed_step(1, 359), -2)

    def test_opposition_and_waning_sextile_targets(self):
        _, opposition, _ = transit.search(
            linear(187, 2), 10, ORIGIN, ORIGIN+timedelta(hours=6),
            60, [180])
        self.assertEqual(len(opposition), 1)
        self.assertEqual(opposition[0]["utc"], "2026-11-07T01:30:00Z")
        _, waning, _ = transit.search(
            linear(304, -2), 10, ORIGIN, ORIGIN+timedelta(hours=5),
            60, [60])
        # -60° longitude difference is the other directed sextile.
        self.assertEqual(len(waning), 1)
        self.assertEqual(waning[0]["utc"], "2026-11-07T02:00:00Z")
        self.assertEqual(waning[0]["aspect"], "sextile")

    def test_multiple_cyclic_crossings_are_retained_and_deduplicated(self):
        # Reversal across 90° generates repeated exact squares.
        def wave(t):
            h = (t-ORIGIN).total_seconds()/3600
            return (100 + 10 * math.sin(math.pi*h/4)) % 360
        _, contacts, _ = transit.search(
            wave, 10, ORIGIN, ORIGIN+timedelta(hours=16), 30, [90])
        times = [r["utc"] for r in contacts]
        self.assertEqual(len(times), len(set(times)))
        self.assertGreaterEqual(len(times), 4)
        self.assertTrue(all(x["aspect"] == "square" for x in contacts))

    def test_constant_body_has_no_false_crossings(self):
        points, contacts, count = transit.search(
            linear(21, 0), 10, ORIGIN, ORIGIN+timedelta(days=2), 60, [0, 90])
        self.assertEqual(contacts, [])
        self.assertEqual(count, 49)
        self.assertEqual(points[0]["epoch_utc"], "2026-11-07T00:00:00Z")
        self.assertEqual(points[-1]["epoch_utc"], "2026-11-09T00:00:00Z")

    def test_no_network_or_birth_store_and_exact_kernel_identity(self):
        text=(ROOT / "scripts/weather/celestial_transit_timeline.py").read_text()
        self.assertIn("_digest(path)", text)
        self.assertIn('if digest.lower() != request["expected_ephemeris_sha256"]', text)
        self.assertIn('origin, body, t, "apparent"', text)
        self.assertIn("frame_latlon(ecliptic_frame)", text)
        self.assertIn("stdin.readline(4097)", text)
        self.assertIn("crossing_search_not_tangency_complete", text)
        for forbidden in ("requests.get(", "urllib.request", "sqlite3.connect(",
                          "open('/home", "pickle.dump(", "os.system(",
                          "load.download(", "--latitude", "--birth"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
