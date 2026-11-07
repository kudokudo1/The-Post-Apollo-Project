"""M8l expanded, bounded 4x4 matrix numerical regression tests.

All trajectories are deterministic synthetic test functions. No output here
purports to contain real JPL ephemeris data or a user's natal information.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "weather"))
import celestial_transit_matrix as matrix
from celestial_contract import ContractError

START = datetime(2026, 11, 7, tzinfo=timezone.utc)
NATALS = ["sun", "moon", "mercury", "venus"]
MOVING = ["moon", "mercury", "venus", "mars_barycenter"]


def req(days=1, step=60, natals=None, moving=None, stations=True):
    end = START + timedelta(days=days)
    return {
        "format": matrix.FORMAT,
        "natal_epoch_utc": "2000-03-21T15:20:00Z",
        "start_utc": START.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude_deg": 38.9,
        "longitude_deg": -76.8,
        "expected_ephemeris_sha256": "a" * 64,
        "natal_bodies": NATALS if natals is None else natals,
        "transit_bodies": MOVING if moving is None else moving,
        "sample_minutes": step,
        "aspects_deg": [0, 60, 90],
        "include_stations": stations,
    }


def sources():
    offset = {"moon": 20, "mercury": 80, "venus": 150, "mars_barycenter": 210}
    def make(body):
        if body not in offset:
            raise AssertionError("unknown fixture target")
        def longitude(instant):
            hours = (instant - START).total_seconds() / 3600
            return (offset[body] + hours * 0.25) % 360
        return longitude
    return make


class M8lFourByFourTests(unittest.TestCase):
    def test_four_by_four_supported_but_seven_day_4x4_refused(self):
        self.assertEqual(matrix.MAX_NATAL, 4)
        self.assertEqual(matrix.MAX_MOVING, 4)
        self.assertEqual(matrix.MAX_PAIR_SAMPLES, 2200)
        self.assertEqual(matrix.MAX_TOTAL_STATION_GRID, 3000)
        one = matrix.normalize(req(days=1, step=60))
        self.assertEqual(len(one["natal_bodies"]), 4)
        self.assertEqual(len(one["transit_bodies"]), 4)
        self.assertEqual(len(one["natal_bodies"]) * len(one["transit_bodies"]), 16)
        self.assertEqual(matrix.normalize(req(days=1, step=30))["sample_minutes"], 30)
        with self.assertRaises(ContractError):
            matrix.normalize(req(days=7, step=60))
        with self.assertRaises(ContractError):
            matrix.normalize(req(days=7, step=30))
        for field in ("natal_bodies", "transit_bodies"):
            bad = req()
            bad[field] = ["sun", "moon", "mercury", "venus", "pluto_barycenter"]
            with self.subTest(field=field), self.assertRaises(ContractError):
                matrix.normalize(bad)
        with self.assertRaises(ContractError):
            matrix.normalize(req(days=14, natals=["sun", "venus"],
                                 moving=MOVING))

    def test_four_moving_seven_day_with_three_natal_remains_in_budget(self):
        reduced = matrix.normalize(req(
            days=7, natals=NATALS[:3], moving=MOVING))
        self.assertEqual(len(reduced["natal_bodies"]), 3)
        # 169 samples * 12 unique pairs = 2028 under the original 2200 cap
        self.assertEqual(169 * 12, 2028)
        self.assertEqual((7 * 96 + 1) * 4, 2692)

    def test_one_day_four_by_four_uses_sixteen_pair_counts_but_four_tracks(self):
        request = matrix.normalize(req(days=1, step=60, stations=False))
        natal = {"sun": 10.0, "moon": 55.0,
                 "mercury": 95.0, "venus": 140.0}
        series, cells, events, count = matrix.aggregate(
            request, natal, sources(), START, START + timedelta(days=1))
        self.assertEqual(count, 25)
        self.assertEqual(len(series), 4)
        self.assertEqual(len(cells), 16)
        self.assertEqual({s["id"] for s in series}, set(MOVING))
        self.assertEqual(len({(cell["natal_body"], cell["transit_body"])
                              for cell in cells}), 16)
        self.assertTrue(all(s["sample_count"] == 25 for s in series))
        self.assertTrue(all(len(s["timeline"]) >= 2 for s in series))
        self.assertEqual(len(events), sum(cell["aspect_count"] for cell in cells))
        self.assertTrue(all(e["type"] == "aspect" for e in events))

    def test_stations_not_multiplied_by_number_of_natal_references(self):
        def moving(body):
            def longitude(instant):
                hours = (instant - START).total_seconds() / 3600
                if body == "mars_barycenter":
                    return (240 + 0.01 * (hours - 12) ** 2) % 360
                return (20 + MOVING.index(body) * 40 + hours * 0.1) % 360
            return longitude
        request = matrix.normalize(req(days=1, stations=True))
        natal = {"sun": 12.0, "moon": 45.0,
                 "mercury": 91.0, "venus": 134.0}
        tracks, cells, events, _ = matrix.aggregate(
            request, natal, moving, START, START + timedelta(days=1))
        station = [e for e in events if e["type"] == "station"]
        self.assertEqual(len(station), 1, station)
        self.assertEqual(station[0]["transit_body"], "mars_barycenter")
        self.assertIsNone(station[0]["natal_body"])
        self.assertEqual(station[0]["direction"], "direct")
        self.assertEqual(len(cells), 16)
        self.assertEqual(len(tracks), 4)

    def test_original_privacy_and_exact_source_gate_unchanged(self):
        source = (ROOT / "scripts/weather/celestial_transit_matrix.py").read_text()
        self.assertIn('if digest.lower() != req["expected_ephemeris_sha256"]', source)
        self.assertIn("find_stations(", source)
        self.assertIn("search_crossings(", source)
        self.assertIn("stdin.readline(4097)", source)
        self.assertIn("MAX_OUTPUT_BYTES = 120000", source)
        for forbidden in ("requests.get(", "urllib.request", "load.download(",
                          "sqlite3.connect(", "pickle.dump(", "--birth",
                          "subprocess.run("):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
