"""M4 graph-data contract, edge cases, and optional real JPL integration.

No Qt/GUI dependencies. Real integration needs MAGICK_M1_KERNEL=/path/de440s.bsp.
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
import celestial_visual_data as visual

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def day(moment):
    return (moment - T0).total_seconds() / 86400


def instant(offset):
    return (T0 + timedelta(days=offset)).isoformat().replace("+00:00", "Z")


def query(*bodies, start=None, end=None, **options):
    return {
        "format": visual.FORMAT,
        "start_utc": start or instant(0),
        "end_utc": end or instant(4),
        "bodies": list(bodies),
        **options,
    }


def synthetic(body, at):
    if body == "moon":
        lon = (350 + 15 * day(at)) % 360
    elif body == "sun":
        lon = (10 + day(at)) % 360
    elif body == "mercury":
        lon = (100 - (day(at) - 2.5) ** 2) % 360
    else:
        raise AssertionError("unknown synthetic body")
    return {"longitude_deg": lon, "latitude_deg": 1.25, "distance_au": 1.0}


class PureVisualDataTests(unittest.TestCase):
    def test_curve_unwrap_and_velocity_and_epoch(self):
        result = visual.build_visual_model(
            query("moon", start=instant(0), end=instant(2), step_hours=24),
            synthetic,
        )
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(result["query"]["origin"], "geocentric")
        self.assertEqual(result["query"]["position_model"], "apparent")
        self.assertEqual(len(result["relationships"]), 0)
        self.assertEqual(len(result["event_markers"]), 0)
        points = result["series"][0]["samples"]
        self.assertEqual([p["longitude_deg"] for p in points], [350, 5, 20])
        self.assertEqual([p["unwrapped_longitude_deg"] for p in points],
                         [350, 365, 380])
        for row in points:
            self.assertAlmostEqual(row["longitude_rate_deg_per_day"], 15, delta=1e-9)
            self.assertEqual(row["motion"], "direct")
            self.assertTrue(row["time_utc"].endswith("Z"))
            self.assertIsInstance(row["unix_ms"], int)
        self.assertEqual(points[1]["unix_ms"] - points[0]["unix_ms"], 86400000)

    def test_relationships_are_synchronized_to_same_time(self):
        result = visual.build_visual_model(
            query("sun", "moon", step_hours=12, orb_degrees=10), synthetic)
        self.assertEqual(result["query"]["bodies"], ["moon", "sun"])
        self.assertEqual(len(result["series"]), 2)
        relationship = result["relationships"][0]
        self.assertEqual(relationship["bodies"], ["moon", "sun"])
        self.assertEqual(len(relationship["samples"]), result["sample_count"])
        moon = result["series"][0]["samples"]
        sun = result["series"][1]["samples"]
        for index, sample in enumerate(relationship["samples"]):
            self.assertEqual(sample["time_utc"], moon[index]["time_utc"])
            self.assertEqual(sample["unix_ms"], sun[index]["unix_ms"])
            self.assertAlmostEqual(
                sample["longitude_separation_deg"],
                dynamics.longitude_separation(moon[index]["longitude_deg"],
                                               sun[index]["longitude_deg"]))

    def test_event_markers_and_station_direction(self):
        result = visual.build_visual_model(
            query("mercury", start=instant(0), end=instant(5),
                  include_events=True, step_hours=12), synthetic)
        self.assertEqual(len(result["series"]), 1)
        events = result["event_markers"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "direct_to_retrograde")
        self.assertEqual(events[0]["kind"], "station_estimate")
        self.assertEqual(events[0]["bodies"], ["mercury"])
        self.assertLess(abs((dynamics._utc(events[0]["time_utc"]) -
                             dynamics._utc(instant(2.5))).total_seconds()), 2)
        self.assertTrue(any(s["motion"] == "retrograde"
                            for s in result["series"][0]["samples"]))

    def test_pair_exact_event_and_source_method(self):
        def align(body, at):
            position = (50 + 2 * (day(at) - 5)) if body == "moon" else 50
            return {
                "longitude_deg": position % 360,
                "latitude_deg": 0,
                "distance_au": 1,
            }
        result = visual.build_visual_model(
            query("moon", "sun", start=instant(0), end=instant(10),
                  step_hours=12, include_events=True), align)
        hits = [e for e in result["event_markers"]
                if e["type"] == "exact_longitude_aspect"
                and e["name"] == "conjunction"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["contact_kind"], "crossing")
        self.assertEqual(hits[0]["bodies"], ["moon", "sun"])
        self.assertLess(abs((dynamics._utc(hits[0]["time_utc"]) -
                             dynamics._utc(instant(5))).total_seconds()), 2)
        self.assertFalse(result["limitations"]["sampling_proves_event_completeness"])

    def test_missing_and_nonfinite_data_rejected(self):
        base = query("moon")
        bad_rows = [
            {}, {"longitude_deg": 0, "latitude_deg": 0},
            {"longitude_deg": float("nan"), "latitude_deg": 0,
             "distance_au": 1},
            {"longitude_deg": 360, "latitude_deg": 0,
             "distance_au": 1},
            {"longitude_deg": 2, "latitude_deg": 95,
             "distance_au": 1},
            {"longitude_deg": 2, "latitude_deg": 1,
             "distance_au": 0},
            {"longitude_deg": False, "latitude_deg": 1,
             "distance_au": 1},
        ]
        for row in bad_rows:
            with self.subTest(row=row), self.assertRaises(contract.ContractError):
                visual.build_visual_model(base, lambda body, moment: row)

    def test_bounded_query_and_strict_time(self):
        cases = [
            query("moon", end=instant(100), step_hours=3),
            query("moon", end=instant(4), step_hours=0),
            query("earth"),
            query("moon", end=instant(367)),
            query("moon", start="2026-01-01T00:00:00-05:00"),
            query("moon", "moon"),
            query("moon", extra_user_data="secret"),
        ]
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(contract.ContractError):
                visual.normalize_visual_query(raw)
        with self.assertRaisesRegex(contract.ContractError, "two bodies"):
            visual.normalize_visual_query(
                query("sun", "moon", "mercury", include_events=True))
        with self.assertRaisesRegex(contract.ContractError, "requires two bodies"):
            visual.normalize_visual_query(
                query("moon", detect_tangents=True, include_events=True))

    def test_unreasonable_angular_alias_rejected(self):
        def quick(body, at):
            return {"longitude_deg": (180 * day(at)) % 360,
                    "latitude_deg": 0, "distance_au": 1}
        with self.assertRaisesRegex(contract.ContractError, "aliases"):
            visual.build_visual_model(
                query("moon", end=instant(3), step_hours=24), quick)

    def test_explicit_kernel_required_without_location_guess(self):
        with self.assertRaisesRegex(contract.ContractError, "existing local"):
            visual.compute_visual_data(query("sun"), "/missing/de440s.bsp")


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"),
                     "real JPL DE440s required")
class JplVisualDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel = os.environ["MAGICK_M1_KERNEL"]

    def test_samples_equal_m1_snapshot_at_same_utc_instant(self):
        request = query("sun", "moon", start="2026-11-01T00:00:00Z",
                        end="2026-11-03T00:00:00Z", step_hours=12)
        result = visual.compute_visual_data(request, self.kernel)
        self.assertEqual(result["sample_count"], 5)
        self.assertEqual(result["provenance"]["ephemeris_id"], "de440s.bsp")
        self.assertEqual(len(result["provenance"]["ephemeris_sha256"]), 64)
        self.assertEqual(len(result["relationships"]), 1)
        for series in result["series"]:
            for point in series["samples"]:
                req = {"format": contract.REQUEST_FORMAT,
                       "instant_utc": point["time_utc"],
                       "origin": "geocentric", "position_model": "apparent",
                       "frame": contract.FRAME, "bodies": [series["body"]]}
                single = solver.compute_snapshot(req, self.kernel)["positions"][0]
                self.assertAlmostEqual(point["longitude_deg"],
                                       single["longitude_deg"], delta=1e-9)
                self.assertAlmostEqual(point["latitude_deg"],
                                       single["latitude_deg"], delta=1e-9)
                self.assertAlmostEqual(point["distance_au"],
                                       single["distance_au"], delta=1e-12)

    def test_event_markers_match_m2_for_real_moon_sun(self):
        start, end = "2026-10-01T00:00:00Z", "2026-10-25T00:00:00Z"
        query_m4 = query("moon", "sun", start=start, end=end,
                         step_hours=12, include_events=True)
        model = visual.compute_visual_data(query_m4, self.kernel)
        aspect_markers = [(e["name"], e["time_utc"])
                          for e in model["event_markers"]
                          if e["type"] == "exact_longitude_aspect"]
        m2 = dynamics.event_report({
            "format": dynamics.FORMAT, "mode": "aspects",
            "start_utc": start, "end_utc": end,
            "bodies": ["moon", "sun"], "step_hours": 12,
        }, self.kernel)
        self.assertTrue(aspect_markers)
        self.assertEqual(aspect_markers,
                         [(e["name"], e["time_utc"]) for e in m2["events"]])
        self.assertEqual(model["query"]["frame"], contract.FRAME)


if __name__ == "__main__":
    unittest.main()
