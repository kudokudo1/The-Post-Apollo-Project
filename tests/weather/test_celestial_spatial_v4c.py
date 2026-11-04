"""V4c Sun-centered geometric spatial contract and optional real DE440s test."""
from datetime import datetime, timedelta, timezone
import math
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract
import celestial_solver as solver
import celestial_spatial_data as spatial
import celestial_visual_data as visual

T0 = datetime(2026, 11, 4, 0, 0, tzinfo=timezone.utc)


def query(**kwargs):
    return {
        "format": visual.FORMAT,
        "start_utc": "2026-11-04T00:00:00Z",
        "end_utc": "2026-11-05T00:00:00Z",
        "bodies": ["sun", "moon"],
        "step_hours": 12,
        "include_events": False,
        "include_heliocentric_spatial": True,
        **kwargs,
    }


class HelioSpatialPureTests(unittest.TestCase):
    def test_opt_in_is_boolean_and_m4_default_remains_compatible(self):
        self.assertTrue(
            visual.normalize_visual_query(query())["include_heliocentric_spatial"]
        )
        base = query()
        del base["include_heliocentric_spatial"]
        self.assertFalse(
            visual.normalize_visual_query(base)["include_heliocentric_spatial"]
        )
        for bad in [None, 1, "true", [], {}]:
            req = query()
            req["include_heliocentric_spatial"] = bad
            with self.subTest(bad=bad), self.assertRaises(contract.ContractError):
                visual.normalize_visual_query(req)

    def test_sun_origin_and_geometric_xyz_use_same_utc_samples(self):
        times = [T0, T0 + timedelta(hours=12), T0 + timedelta(hours=24)]
        called = []

        def measured(body, moment):
            called.append((body, moment))
            self.assertEqual(body, "moon")
            index = times.index(moment)
            return [index + 1.0, -0.5, 0.25]

        result = spatial.build_spatial_series(["moon", "sun"], times, measured)
        self.assertEqual(result["format"], spatial.FORMAT)
        self.assertEqual(result["frame"], contract.FRAME)
        self.assertEqual(result["origin"], "heliocentric")
        self.assertEqual(result["origin_body"], "sun")
        self.assertEqual(result["position_model"], "geometric")
        self.assertEqual(result["sample_count"], 3)
        self.assertEqual(len(called), 3)
        moon = result["series"][0]["samples"]
        sun = result["series"][1]["samples"]
        self.assertEqual([r["x_au"] for r in moon], [1, 2, 3])
        self.assertEqual([r["distance_au"] for r in sun], [0, 0, 0])
        self.assertTrue(all((r["x_au"], r["y_au"], r["z_au"]) == (0, 0, 0)
                            for r in sun))
        self.assertEqual(
            moon[1]["unix_ms"], int(times[1].timestamp() * 1000))
        self.assertEqual(
            moon[1]["time_utc"], "2026-11-04T12:00:00.000000Z")
        for row in moon:
            self.assertAlmostEqual(
                row["distance_au"],
                math.hypot(row["x_au"], row["y_au"], row["z_au"]),
                delta=1e-12,
            )

    def test_rejects_zero_nonorigin_nan_missing_nonutc_and_unbounded(self):
        times = [T0, T0 + timedelta(hours=12)]
        cases = [
            lambda _: (0, 0, 0),
            lambda _: (float("nan"), 0, 1),
            lambda _: (float("inf"), 0, 1),
            lambda _: (10001, 0, 1),
            lambda _: (None, 0, 1),
            lambda _: (1, 2),
            lambda _: "1,2,3",
        ]
        for measured in cases:
            with self.subTest(measured=measured), self.assertRaises(
                    contract.ContractError):
                spatial.build_spatial_series(
                    ["moon"], times, lambda body, when: measured(when))
        for bodies, dates in [
            (["moon", "moon"], times),
            (["moon"] * 5, times),
            (["moon"], [T0, T0]),
            (["moon"], [T0, datetime(2026, 11, 5)]),
            (["moon"], [T0]),
        ]:
            with self.subTest(bodies=bodies, dates=dates), self.assertRaises(
                    contract.ContractError):
                spatial.build_spatial_series(
                    bodies, dates, lambda body, when: (1, 0, 0))

    def test_no_implicit_kernel_discovery_or_download(self):
        with self.assertRaisesRegex(contract.ContractError, "existing local"):
            visual.compute_visual_data(query(), "/missing/de440s.bsp")


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"), "JPL kernel not provided")
class HelioSpatialRealJPLTests(unittest.TestCase):
    def test_heliocentric_vector_matches_independent_m1_geometric_snapshot(self):
        kernel = os.environ["MAGICK_M1_KERNEL"]
        response = visual.compute_visual_data(query(), kernel)
        self.assertEqual(response["query"]["origin"], "geocentric")
        self.assertEqual(response["query"]["position_model"], "apparent")
        self.assertEqual(response["query"]["include_heliocentric_spatial"], True)
        self.assertIn("heliocentric_spatial", response)
        data = response["heliocentric_spatial"]
        self.assertEqual(data["origin"], "heliocentric")
        self.assertEqual(data["position_model"], "geometric")
        self.assertEqual(data["sample_count"], response["sample_count"])
        sun = next(s for s in data["series"] if s["body"] == "sun")
        moon = next(s for s in data["series"] if s["body"] == "moon")
        self.assertTrue(all(s["distance_au"] == 0 for s in sun["samples"]))

        for row in (moon["samples"][0], moon["samples"][-1]):
            snapshot = solver.compute_snapshot({
                "format": contract.REQUEST_FORMAT,
                "instant_utc": row["time_utc"],
                "origin": "heliocentric",
                "position_model": "geometric",
                "frame": contract.FRAME,
                "bodies": ["moon"],
            }, kernel)
            position = snapshot["positions"][0]
            self.assertEqual(position["body"], "moon")
            x, y, z = row["x_au"], row["y_au"], row["z_au"]
            r = math.hypot(x, y, z)
            lon = math.degrees(math.atan2(y, x)) % 360
            lat = math.degrees(math.atan2(z, math.hypot(x, y)))
            self.assertAlmostEqual(r, position["distance_au"], delta=1e-9)
            self.assertAlmostEqual(lon, position["longitude_deg"], delta=1e-7)
            self.assertAlmostEqual(lat, position["latitude_deg"], delta=1e-7)
        # The Sun-relative range to the Moon is of order 1 AU, unlike
        # the small geocentric Earth-Moon range. They must not be conflated.
        moon_geo = next(s for s in response["series"] if s["body"] == "moon")
        self.assertGreater(moon["samples"][0]["distance_au"], 0.9)
        self.assertLess(moon_geo["samples"][0]["distance_au"], 0.01)


if __name__ == "__main__":
    unittest.main()
