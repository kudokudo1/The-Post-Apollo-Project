"""V4d separate multi-body geometric JPL atlas, with bounded CI integration."""
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract
import celestial_solver as solver
import celestial_solar_overview as atlas
import celestial_visual_data as visual

T0 = datetime(2026, 11, 4, tzinfo=timezone.utc)


def query(**overrides):
    row = {
        "format": visual.FORMAT,
        "start_utc": "2026-11-04T00:00:00Z",
        "end_utc": "2026-11-05T00:00:00Z",
        "bodies": ["moon", "sun"],
        "step_hours": 12,
        "include_events": False,
        "include_heliocentric_spatial": True,
        "solar_overview_bodies": list(atlas.BODIES),
    }
    row.update(overrides)
    return row


class SolarOverviewPureTests(unittest.TestCase):
    def test_canonical_exact_target_ids_are_never_planet_center_aliases(self):
        self.assertEqual(len(atlas.BODIES), 10)
        self.assertEqual(len(set(atlas.BODIES)), 10)
        self.assertIn("earth", atlas.BODIES)
        self.assertIn("moon", atlas.BODIES)
        self.assertIn("jupiter_barycenter", atlas.BODIES)
        self.assertNotIn("jupiter", atlas.BODIES)
        self.assertNotIn("mars", atlas.BODIES)
        self.assertNotIn("sun", atlas.BODIES)
        self.assertEqual(atlas.normalize_bodies(list(atlas.BODIES)),
                         list(atlas.BODIES))
        self.assertEqual(atlas.normalize_bodies([]), [])

    def test_reject_invented_body_duplicates_reordering_and_broken_types(self):
        for data in [
            "all", None, {"body": "venus"}, ["sun"], ["mars"],
            ["jupiter"], ["venus", "venus"], ["venus", "mercury"],
            ["earth", "jupiter_barycenter", "EARTH"], [False],
            list(atlas.BODIES) + ["unlisted"], list(atlas.BODIES) + ["moon"]
        ]:
            with self.subTest(data=data), self.assertRaises(contract.ContractError):
                atlas.normalize_bodies(data)

    def test_exact_grid_and_compact_vectors_without_event_pair_expansion(self):
        moments = [T0 + timedelta(hours=12*i) for i in range(3)]
        calls = []
        bodies = ["mercury", "venus", "earth", "moon"]

        def state_at(body, at):
            calls.append((body, at))
            return (bodies.index(body) + 0.25, 0.5, -0.125)

        data = atlas.build_solar_overview(bodies, moments, state_at)
        self.assertEqual(data["format"], atlas.FORMAT)
        self.assertEqual(data["origin"], "heliocentric")
        self.assertEqual(data["position_model"], "geometric")
        self.assertEqual(data["frame"], contract.FRAME)
        self.assertEqual(data["sample_count"], 3)
        self.assertEqual(len(data["series"]), 4)
        self.assertEqual(len(calls), 12)
        self.assertEqual(data["times_unix_ms"][1]-data["times_unix_ms"][0],
                         12*3600*1000)
        self.assertEqual(data["series"][0]["body"], "mercury")
        self.assertEqual(data["series"][0]["vectors_au"][0],
                         [0.25, 0.5, -0.125])
        self.assertEqual(len(data["series"][0]["vectors_au"]), 3)
        self.assertNotIn("relationships", data)
        self.assertNotIn("event_markers", data)

    def test_query_optional_preserves_pair_and_real_event_limits(self):
        base=query()
        normalized=visual.normalize_visual_query(base)
        self.assertEqual(normalized["bodies"], ["moon", "sun"])
        self.assertEqual(normalized["solar_overview_bodies"], list(atlas.BODIES))
        self.assertTrue(normalized["include_heliocentric_spatial"])
        self.assertEqual(normalized["origin"], "geocentric")
        self.assertEqual(normalized["position_model"], "apparent")
        self.assertEqual(normalized["frame"], contract.FRAME)
        self.assertEqual(len(atlas.BODIES), 10)
        no_atlas=dict(base)
        del no_atlas["solar_overview_bodies"]
        self.assertEqual(visual.normalize_visual_query(no_atlas)
                         ["solar_overview_bodies"], [])
        for data in [
            query(solar_overview_bodies=["jupiter"]),
            query(solar_overview_bodies=list(atlas.BODIES),
                  include_heliocentric_spatial=False),
            query(start_utc="2026-01-01T00:00:00Z",
                  end_utc="2026-06-01T00:00:00Z"),
            query(solar_overview_bodies=[None]),
        ]:
            with self.subTest(data=data), self.assertRaises(contract.ContractError):
                visual.normalize_visual_query(data)
        # Multi-body spatial geometry does NOT expand pair event searches.
        with self.assertRaisesRegex(contract.ContractError, "two bodies"):
            visual.normalize_visual_query(query(
                bodies=["moon","sun","mercury"], include_events=True))

    def test_invalid_vectors_zero_source_nonfinite_and_grid_fail_closed(self):
        times = [T0, T0+timedelta(hours=12)]
        for invalid in [(0,0,0), ("1",2,3), (None,0,2),
                        (float("nan"),0,1),(float("inf"),0,1),
                        (10001,0,1),(1,2),(True,1,1)]:
            with self.subTest(invalid=invalid), self.assertRaises(contract.ContractError):
                atlas.build_solar_overview(["earth"],times,lambda body,at:invalid)
        for moments in [
            [times[0]], [times[0],times[0]],
            [times[0],datetime(2026,11,5)], times+[times[0]],
            [T0+timedelta(hours=i) for i in range(182)]
        ]:
            with self.subTest(count=len(moments)), self.assertRaises(contract.ContractError):
                atlas.build_solar_overview(
                    ["earth"], moments, lambda body,at:(1,2,3))

    def test_compact_ninety_day_payload_has_strict_size_budget(self):
        # Real integration additionally measures full M4+spatial response.
        times=[T0+timedelta(hours=12*i) for i in range(181)]
        result=atlas.build_solar_overview(
            list(atlas.BODIES), times,
            lambda body,at:(
                (atlas.BODIES.index(body)+1)*0.9,
                (at-T0).total_seconds()/86400*0.01,
                0.01,
            )
        )
        encoded=json.dumps(result,separators=(",",":"),allow_nan=False)
        self.assertEqual(len(result["series"]),10)
        self.assertEqual(result["sample_count"],181)
        self.assertLess(len(encoded),200000)
        with self.assertRaisesRegex(contract.ContractError,"181"):
            visual.normalize_visual_query(query(
                start_utc="2026-11-01T00:00:00Z",
                end_utc="2027-02-01T00:00:00Z"))


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"),"real DE440s kernel not provided")
class SolarOverviewRealJPLTests(unittest.TestCase):
    def test_full_ninety_day_atlas_matches_m1_and_quickshell_limit(self):
        kernel=os.environ["MAGICK_M1_KERNEL"]
        req=query(
            start_utc="2026-09-19T00:00:00Z",
            end_utc="2026-12-18T00:00:00Z",
            include_events=False,
        )
        result=visual.compute_visual_data(req,kernel)
        self.assertEqual(result["sample_count"],181)
        self.assertEqual(result["query"]["bodies"],["moon","sun"])
        self.assertEqual(len(result["relationships"]),1)
        self.assertEqual(len(result["solar_overview"]["series"]),10)
        self.assertEqual(result["solar_overview"]["sample_count"],181)
        text=json.dumps(result,separators=(",",":"),allow_nan=False)
        # Current one-process QML StdioCollector maximum in
        # services/weather/CelestialVisualService.qml is 524288 chars.
        self.assertLess(len(text),524288)
        self.assertEqual(result["solar_overview"]["times_unix_ms"],
                         [s["unix_ms"] for s in result["series"][0]["samples"]])
        for body in ["mercury","earth","moon","mars_barycenter",
                     "jupiter_barycenter","neptune_barycenter"]:
            entry=next(s for s in result["solar_overview"]["series"]
                       if s["body"]==body)
            for i in [0,90,180]:
                v=entry["vectors_au"][i]
                instant=result["series"][0]["samples"][i]["time_utc"]
                snap=solver.compute_snapshot({
                    "format":contract.REQUEST_FORMAT,
                    "instant_utc":instant,
                    "origin":"heliocentric",
                    "position_model":"geometric",
                    "frame":contract.FRAME,
                    "bodies":[body],
                },kernel)["positions"][0]
                radius=math.hypot(*v)
                lon=math.degrees(math.atan2(v[1],v[0]))%360
                lat=math.degrees(math.atan2(v[2],math.hypot(v[0],v[1])))
                self.assertAlmostEqual(radius,snap["distance_au"],delta=1e-9)
                self.assertAlmostEqual(lon,snap["longitude_deg"],delta=1e-7)
                self.assertAlmostEqual(lat,snap["latitude_deg"],delta=1e-7)


if __name__=="__main__":
    unittest.main()
