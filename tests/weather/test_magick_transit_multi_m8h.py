"""M8h multi-body angular search and finite-difference station contracts.

Analytical trajectories below are ONLY deterministic test fixtures. They are
not real planetary observations or claims about actual transit dates.
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

ORIGIN = datetime(2026, 11, 7, 0, 0, tzinfo=timezone.utc)


def request(**updates):
    obj = {
        "format": multi.FORMAT,
        "natal_epoch_utc": "2000-03-21T15:20:00Z",
        "start_utc": "2026-11-07T00:00:00Z",
        "end_utc": "2026-11-14T00:00:00Z",
        "latitude_deg": 38.9, "longitude_deg": -76.8,
        "expected_ephemeris_sha256": "a"*64,
        "natal_body": "sun",
        "transit_bodies": ["moon", "venus", "mercury"],
        "sample_minutes": 60,
        "aspects_deg": [0, 60, 90, 120, 180],
        "include_stations": True,
    }
    obj.update(updates)
    return obj


def hours(t):
    return (t - ORIGIN).total_seconds()/3600


def linear(start_deg, rate_deg_per_hour):
    return lambda t: (start_deg + rate_deg_per_hour * hours(t)) % 360


def parabola(positive=True):
    sign = 1 if positive else -1
    return lambda t: (100 + sign * 0.1 * (hours(t)-6)**2) % 360


class M8hTest(unittest.TestCase):
    def test_bounded_request(self):
        r=multi.normalize(request())
        self.assertEqual(r["transit_bodies"], ["moon","venus","mercury"])
        self.assertEqual(r["aspects_deg"], [0,60,90,120,180])
        for edit in (
            {"format":"invalid"},
            {"natal_body":"mars"},
            {"transit_bodies":[]},
            {"transit_bodies":["moon"]*2},
            {"transit_bodies":["moon","venus","mercury","sun"]},
            {"transit_bodies":["mars"]},
            {"sample_minutes":15},
            {"sample_minutes":True},
            {"include_stations":1},
            {"aspects_deg":[]},
            {"aspects_deg":[90,90]},
            {"aspects_deg":[45]},
            {"aspects_deg":[True]},
            {"start_utc":"2026-02-29T00:00:00Z"},
            {"end_utc":"2026-11-07T00:00:00Z"},
            {"end_utc":"2026-12-14T00:00:00Z"},
            {"latitude_deg":True},
            {"latitude_deg":100.0},
            {"longitude_deg":-200.0},
            {"expected_ephemeris_sha256":"unverified"},
        ):
            with self.subTest(edit=edit):
                with self.assertRaises(ContractError):
                    multi.normalize(request(**edit))
        with self.assertRaises(ContractError):
            multi.normalize({**request(),"birth_name":"not accepted"})

    def test_direct_station_bracket(self):
        events=multi.find_stations(
            parabola(True), ORIGIN, ORIGIN+timedelta(hours=12), 60)
        self.assertEqual(len(events),1,events)
        self.assertEqual(events[0]["type"],"station")
        self.assertEqual(events[0]["direction"],"direct")
        when=datetime.fromisoformat(events[0]["utc"].replace("Z","+00:00"))
        self.assertLess(abs((when-(ORIGIN+timedelta(hours=6))).total_seconds()),60)
        self.assertEqual(events[0]["uncertainty_seconds"],60)
        self.assertLess(abs(events[0]["velocity_deg_day"]),0.5)

    def test_retrograde_station_and_no_spurious_constant_station(self):
        backward=multi.find_stations(parabola(False), ORIGIN,
                    ORIGIN+timedelta(hours=12),30)
        self.assertEqual(len(backward),1,backward)
        self.assertEqual(backward[0]["direction"],"retrograde")
        self.assertEqual(multi.find_stations(linear(21,0),ORIGIN,
                         ORIGIN+timedelta(hours=12),60),[])
        self.assertEqual(multi.find_stations(linear(300,0.2),ORIGIN,
                         ORIGIN+timedelta(hours=12),60),[])

    def test_three_body_aggregation_order_and_filtered_aspects(self):
        chosen={"moon":linear(45,2),"venus":parabola(True),
                "mercury":linear(21,0)}
        req=multi.normalize(request(
            end_utc="2026-11-07T18:00:00Z",
            aspects_deg=[60],
            transit_bodies=["moon","venus","mercury"]))
        tracks,events=multi.aggregate(req,10,lambda body:chosen[body],
                         ORIGIN,ORIGIN+timedelta(hours=18))
        self.assertEqual([s["id"] for s in tracks],
                         ["moon","venus","mercury"])
        self.assertEqual(len(tracks),3)
        self.assertTrue(all(s["sample_count"]==19 for s in tracks))
        self.assertTrue(all(s["timeline"][0]["epoch_utc"]==
                         "2026-11-07T00:00:00Z" for s in tracks))
        self.assertEqual(events,sorted(events,key=lambda e:
                         (e["utc"],e["transit_body"],e["type"],
                          e.get("aspect",""))))
        aspect=[e for e in events if e["type"]=="aspect"]
        station=[e for e in events if e["type"]=="station"]
        self.assertTrue(any(e["transit_body"]=="moon" and
                            e["aspect"]=="sextile" for e in aspect))
        self.assertTrue(all(e["aspect_target_deg"]==60 for e in aspect))
        self.assertTrue(any(e["transit_body"]=="venus" and
                            e["direction"]=="direct" for e in station))
        self.assertFalse(any(e["transit_body"]=="mercury" and
                             e["type"]=="station" for e in events))

    def test_can_disable_stations_and_aspect_filter_is_not_decorative(self):
        req=multi.normalize(request(
            end_utc="2026-11-07T12:00:00Z",
            transit_bodies=["venus"],
            aspects_deg=[120],include_stations=False))
        tracks,events=multi.aggregate(
            req,10,lambda _:parabola(True),
            ORIGIN,ORIGIN+timedelta(hours=12))
        self.assertEqual(len(tracks),1)
        self.assertFalse(any(e["type"]=="station" for e in events))
        self.assertFalse(any(e.get("aspect") in ("square","sextile")
                             for e in events))

    def test_bounded_privacy_existing_skyfield_and_numerical_source(self):
        s=(ROOT/"scripts/weather/celestial_transit_multi.py").read_text()
        self.assertIn('if digest.lower() != req["expected_ephemeris_sha256"]',s)
        self.assertIn("search_crossings(",s)
        self.assertIn("from celestial_transit_timeline import",s)
        self.assertIn('origin, target, t, "apparent"',s)
        self.assertIn("frame_latlon(frame)",s)
        self.assertIn("stdin.readline(4097)",s)
        self.assertIn("if len(payload.encode(\"utf-8\")) > 120000:",s)
        self.assertIn("station_search_not_all_turns_guaranteed",s)
        for forbid in ("requests.get(", "urllib.request",
                       "sqlite3.connect(", "pickle.dump(",
                       "load.download(", "--birth", "--latitude", "subprocess.run("):
            self.assertNotIn(forbid,s)


if __name__=="__main__":
    unittest.main()
