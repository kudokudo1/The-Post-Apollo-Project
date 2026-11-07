"""M8k deterministic numerical tests; synthetic polynomials, never JPL claims."""
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"weather"))
import celestial_transit_matrix as mx
from celestial_contract import ContractError

ZERO=datetime(2026,11,7,tzinfo=timezone.utc)

def request(**updates):
    obj={
        "format":mx.FORMAT,
        "natal_epoch_utc":"2000-03-21T15:20:00Z",
        "start_utc":"2026-11-07T00:00:00Z",
        "end_utc":"2026-11-14T00:00:00Z",
        "latitude_deg":38.9,"longitude_deg":-76.8,
        "expected_ephemeris_sha256":"a"*64,
        "natal_bodies":["sun","venus","mars_barycenter"],
        "transit_bodies":["moon","mercury","jupiter_barycenter"],
        "sample_minutes":60,"aspects_deg":[0,60,90],
        "include_stations":True
    }
    obj.update(updates)
    return obj

def hour(t):return (t-ZERO).total_seconds()/3600

def moving(body):
    if body=="moon":return lambda t:(60+.3*hour(t))%360
    if body=="mercury":return lambda t:(92-.02*hour(t))%360
    if body=="jupiter_barycenter":
        return lambda t:(130+.00005*(hour(t)-72)**2)%360
    raise AssertionError("unexpected target")

class M8kTests(unittest.TestCase):
    def test_matrix_request_limits_are_numerical_not_just_ui(self):
        req=mx.normalize(request())
        self.assertEqual(len(req["natal_bodies"])*len(req["transit_bodies"]),9)
        self.assertEqual(req["sample_minutes"],60)
        bad=[
            {"natal_bodies":[]},
            {"natal_bodies":["sun","venus","moon","mercury"]},
            {"natal_bodies":["sun","sun"]},
            {"natal_bodies":["mars"]},
            {"transit_bodies":[]},
            {"transit_bodies":["moon","moon"]},
            {"transit_bodies":["mars"]},
            {"sample_minutes":15},
            {"sample_minutes":True},
            {"aspects_deg":[45]},
            {"aspects_deg":[60,60]},
            {"aspects_deg":[]},
            {"aspects_deg":[True]},
            {"include_stations":1},
            {"expected_ephemeris_sha256":"invalid"},
            {"latitude_deg":100},
            {"longitude_deg":True},
            {"end_utc":"2026-11-07T00:00:00Z"},
            {"end_utc":"2026-12-09T00:00:00Z"},
            {"start_utc":"2026-11-07T00:00:00-05:00"},
            {"end_utc":"2026-11-21T00:00:00Z"},
            {"end_utc":"2026-12-08T00:00:00Z"},
        ]
        for changes in bad:
            with self.subTest(changes=changes),self.assertRaises(ContractError):
                mx.normalize(request(**changes))
        with self.assertRaises(ContractError):
            mx.normalize({**request(),"birth_name":"private-not-accepted"})
        one=mx.normalize(request(natal_bodies=["sun"],
            transit_bodies=["moon"],end_utc="2026-12-08T00:00:00Z"))
        self.assertEqual(one["transit_bodies"],["moon"])
        less=mx.normalize(request(natal_bodies=["sun","venus"],
            transit_bodies=["moon","mercury"],
            end_utc="2026-11-21T00:00:00Z"))
        self.assertEqual(len(less["natal_bodies"]),2)

    def test_three_by_three_aspect_crossings_preserve_exact_pair_identity(self):
        req=mx.normalize(request(include_stations=False))
        natals={"sun":10.0,"venus":25.0,"mars_barycenter":40.0}
        tracks,cells,events,count=mx.aggregate(
            req,natals,moving,ZERO,ZERO+timedelta(days=7))
        self.assertEqual(len(tracks),3)
        self.assertEqual(len(cells),9)
        self.assertEqual(count,169)
        self.assertEqual([t["id"] for t in tracks],
                         ["moon","mercury","jupiter_barycenter"])
        self.assertTrue(all(t["sample_count"]==169 for t in tracks))
        self.assertEqual(len({(c["natal_body"],c["transit_body"])
                              for c in cells}),9)
        self.assertTrue(all(e["type"]=="aspect" and
                            e["natal_body"] in req["natal_bodies"] and
                            e["transit_body"] in req["transit_bodies"]
                            for e in events))
        self.assertEqual(len(events),sum(c["aspect_count"] for c in cells))
        # Moon starts 10 degrees short of its sextile with natal Sun.
        exact=[e for e in events if
              e["natal_body"]=="sun" and e["transit_body"]=="moon"
              and e["aspect"]=="sextile"]
        self.assertEqual(len(exact),1)
        when=datetime.fromisoformat(exact[0]["utc"].replace("Z","+00:00"))
        self.assertLess(abs((when-(ZERO+timedelta(hours=100/3))).total_seconds()),2)
        self.assertLess(exact[0]["residual_deg"],0.001)
        self.assertEqual(events,sorted(events,key=lambda e:
            (e["utc"],e["transit_body"],e["type"],
             e["natal_body"] or "",e.get("aspect",""))))

    def test_stations_belong_once_to_moving_body_not_natal_pairs(self):
        req=mx.normalize(request(
            natal_bodies=["sun","venus"],transit_bodies=["jupiter_barycenter"],
            aspects_deg=[90],include_stations=True,
            end_utc="2026-11-08T00:00:00Z"
        ))
        def station(_):
            return lambda instant:(200+.01*(hour(instant)-12)**2)%360
        tracks,cells,events,count=mx.aggregate(
            req,{"sun":10.0,"venus":35.0},station,
            ZERO,ZERO+timedelta(days=1))
        stationary=[e for e in events if e["type"]=="station"]
        self.assertEqual(len(stationary),1)
        self.assertIsNone(stationary[0]["natal_body"])
        self.assertEqual(stationary[0]["transit_body"],"jupiter_barycenter")
        self.assertEqual(stationary[0]["direction"],"direct")
        self.assertEqual(len(cells),2)
        self.assertEqual(tracks[0]["sample_count"],25)

    def test_invalid_source_and_overflow_fail_closed(self):
        req=mx.normalize(request(
            natal_bodies=["sun"],transit_bodies=["moon"],
            end_utc="2026-11-08T00:00:00Z",include_stations=False))
        for natals in ({},{ "sun":float("nan")},{"sun":400}):
            with self.assertRaises(ContractError):
                mx.aggregate(req,natals,moving,ZERO,ZERO+timedelta(days=1))
        rapid=lambda body:lambda t:(hour(t)*20)%360
        with self.assertRaises(ContractError):
            mx.aggregate(req,{"sun":10},rapid,ZERO,
                         ZERO+timedelta(days=1))

    def test_no_private_io_or_new_ephemeris_and_station_reuse(self):
        s=(ROOT/"scripts"/"weather"/"celestial_transit_matrix.py").read_text()
        for expected in ("_digest(bsp)","expected_ephemeris_sha256",
                         "search_crossings(","find_stations(",
                         "stdin.readline(4097)",
                         "elevation_m=0.0","frame_latlon(frame)",
                         '"stations_not_natal_pairs": True',
                         "MAX_PAIR_SAMPLES = 2200"):
            self.assertIn(expected,s)
        for forbidden in ("requests.get(", "urllib.request", "load.download(",
                          "sqlite3.connect(", "pickle.dump(", "subprocess.run(",
                          "--birth", "--latitude", "os.system("):
            self.assertNotIn(forbidden,s)

if __name__=="__main__":
    unittest.main()
