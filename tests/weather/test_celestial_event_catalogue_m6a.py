"""MAGICK M6-A source event catalogue: no fake events, no new JPL worker.

Run:
    python3 -m unittest discover -s tests/weather \
      -p 'test_celestial_event_catalogue_m6a.py' -v
Optional real JPL:
    MAGICK_M1_KERNEL=/path/to/de440s.bsp python3 -m unittest ...
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract
import celestial_dynamics as dynamics
import celestial_visual_data as visual
import celestial_event_catalogue as catalogue

ORIGIN = datetime(2026, 1, 1, tzinfo=timezone.utc)
PROVENANCE = {
    "engine": "skyfield",
    "engine_version": "1.55",
    "ephemeris_id": "de440s.bsp",
    "ephemeris_sha256": "a" * 64,
    "time_data_id": "skyfield-1.55-builtin-timescale",
    "generated_at_utc": "2026-11-04T14:15:00.000000Z",
}


def day(t):
    return (t - ORIGIN).total_seconds() / 86400


def instant(n):
    return (ORIGIN + timedelta(days=n)).isoformat().replace("+00:00", "Z")


def request(*bodies, days=10, include_events=True, **extra):
    return {
        "format": visual.FORMAT,
        "start_utc": instant(0),
        "end_utc": instant(days),
        "bodies": list(bodies),
        "step_hours": 12,
        "include_events": include_events,
        **extra,
    }


def measure(body, at):
    d = day(at)
    if body == "moon":
        longitude = (18 * d) % 360
    elif body == "sun":
        longitude = 0
    elif body == "mercury":
        longitude = (100 - (d - 5) ** 2) % 360
    elif body == "venus":
        longitude = (150 + 2 * d) % 360
    else:
        raise AssertionError(body)
    return {"longitude_deg": longitude,
            "latitude_deg": 1.0, "distance_au": 1.0}


def model(*bodies, **options):
    source = visual.build_visual_model(request(*bodies, **options), measure)
    source["provenance"] = dict(PROVENANCE)
    return source


class M6aContractTests(unittest.TestCase):
    def test_catalogue_contains_5_major_aspect_crossings_from_m4(self):
        original = model("moon", "sun")
        result = catalogue.build_catalogue(original)
        self.assertEqual(result["format"], catalogue.FORMAT)
        self.assertEqual(result["source_format"], visual.FORMAT)
        self.assertEqual(result["window"]["bodies"], ["moon", "sun"])
        self.assertEqual(result["window"]["sample_count"], 21)
        self.assertEqual(result["source"]["frame"], contract.FRAME)
        self.assertEqual(result["source"]["ephemeris_sha256"], "a" * 64)
        self.assertEqual(result["search"]["status"], "bounded_non_exhaustive")
        major = [e for e in result["events"] if e["category"] == "aspect"]
        self.assertEqual({e["name"] for e in major},
                         {"conjunction", "sextile", "square",
                          "trine", "opposition"})
        self.assertTrue(all(e["classification"] == "computed_crossing"
                            for e in major))
        self.assertTrue(all(e["event_id"].startswith("m6a_") for e in major))
        self.assertTrue(all(e["body_ids"] == ["moon", "sun"] for e in major))
        self.assertTrue(all("time_utc" in e for e in major))
        self.assertFalse(any(e["category"] == "eclipse" for e in result["events"]))
        self.assertTrue(result["limitations"]["not_an_astrological_interpretation"])
        self.assertTrue(result["limitations"]["search_is_not_complete_for_all_possible_contacts"])

    def test_stations_are_estimates_and_not_pairwise_edges(self):
        result = catalogue.build_catalogue(model("mercury"))
        events = result["events"]
        self.assertEqual(len(events), 1)
        station = events[0]
        self.assertEqual(station["category"], "motion_station")
        self.assertEqual(station["classification"], "finite_difference_estimate")
        self.assertEqual(station["name"], "direct_to_retrograde")
        self.assertEqual(station["body_ids"], ["mercury"])
        self.assertEqual(station["rate_window_hours"], 6.0)
        self.assertLess(abs((dynamics._utc(station["time_utc"]) -
                             dynamics._utc(instant(5))).total_seconds()), 2)
        runs = [r for r in result["sampled_motion_runs"]
                if r["body_id"] == "mercury"]
        self.assertTrue(any(r["motion"] == "retrograde" for r in runs))
        self.assertTrue(all(r["boundary_precision"] ==
                            "samples_only_not_exact_station" for r in runs))
        self.assertEqual(result["latest_sampled_aspect_states"], [])

    def test_four_body_sampled_relationships_are_not_faked_event_search(self):
        result = catalogue.build_catalogue(model(
            "moon", "sun", "mercury", "venus", include_events=False))
        self.assertEqual(len(result["window"]["bodies"]), 4)
        self.assertEqual(result["search"]["status"], "not_requested")
        self.assertFalse(result["search"]["requested"])
        self.assertEqual(result["events"], [])
        self.assertTrue(result["sampled_motion_runs"])
        self.assertLessEqual(len(result["latest_sampled_aspect_states"]), 6 * 2)
        self.assertTrue(result["limitations"]["search_is_not_complete_for_all_possible_contacts"])

    def test_latest_within_orb_is_state_not_exact_contact(self):
        original = model("moon", "sun", days=2)
        result = catalogue.build_catalogue(original)
        current = result["latest_sampled_aspect_states"]
        # Day 2: Moon 36°, Sun 0°; at default 6° orb: no active major aspect.
        self.assertEqual(current, [])
        # Day 0: exact conjunction from M4 source. It appears in events,
        # not as an aspect state at the different latest sample.
        self.assertTrue(any(e["name"] == "conjunction" for e in result["events"]))
        near = model("moon", "sun", days=3, orb_degrees=6)
        final = catalogue.build_catalogue(near)
        self.assertTrue(any(s["name"] == "sextile"
                            for s in final["latest_sampled_aspect_states"]))
        self.assertTrue(all(s["classification"] ==
                            "sampled_within_orb_not_exact_event"
                            for s in final["latest_sampled_aspect_states"]))

    def test_stable_ids_independent_of_event_list_order(self):
        raw = model("moon", "sun")
        a = catalogue.build_catalogue(raw)
        b = catalogue.build_catalogue(deepcopy(raw))
        self.assertEqual(a["events"], b["events"])
        shuffled = deepcopy(raw)
        shuffled["event_markers"].reverse()
        c = catalogue.build_catalogue(shuffled)
        self.assertEqual([e["event_id"] for e in a["events"]],
                         [e["event_id"] for e in c["events"]])
        changed = deepcopy(raw)
        changed["provenance"]["ephemeris_sha256"] = "b" * 64
        d = catalogue.build_catalogue(changed)
        self.assertNotEqual([e["event_id"] for e in a["events"]],
                            [e["event_id"] for e in d["events"]])

    def test_distinct_grazing_candidate_never_masquerades_as_crossing(self):
        raw = model("moon", "sun", detect_tangents=True)
        sample = next(e for e in raw["event_markers"] if e["name"] == "sextile")
        candidate = deepcopy(sample)
        candidate["contact_kind"] = "tangent_candidate"
        candidate["residual_deg"] = 0.000001
        candidate["angular_tolerance_deg"] = 0.00001
        raw["event_markers"].append(candidate)
        events = catalogue.build_catalogue(raw)["events"]
        self.assertTrue(any(e["classification"] == "bounded_grazing_candidate"
                            for e in events))
        self.assertTrue(any(e["classification"] == "computed_crossing"
                            for e in events))
        bad = deepcopy(raw)
        bad["event_markers"][-1]["residual_deg"] = 0.5
        with self.assertRaisesRegex(contract.ContractError, "tolerance"):
            catalogue.build_catalogue(bad)
        not_requested = deepcopy(raw)
        not_requested["query"]["detect_tangents"] = False
        not_requested["query"]["tangent_tolerance_deg"] = None
        with self.assertRaisesRegex(contract.ContractError, "not requested"):
            catalogue.build_catalogue(not_requested)
        wrong_tolerance = deepcopy(raw)
        wrong_tolerance["event_markers"][-1]["angular_tolerance_deg"] = 0.001
        with self.assertRaisesRegex(contract.ContractError, "tolerance"):
            catalogue.build_catalogue(wrong_tolerance)

    def test_station_rate_settings_and_body_metadata_must_match_source(self):
        station = model("mercury")
        changed = deepcopy(station)
        changed["event_markers"][0]["rate_window_hours"] = 12.0
        with self.assertRaisesRegex(contract.ContractError, "rate window"):
            catalogue.build_catalogue(changed)
        bad = deepcopy(station)
        bad["event_markers"][0]["bodies"] = [[]]
        with self.assertRaisesRegex(contract.ContractError, "body IDs"):
            catalogue.build_catalogue(bad)

    def test_reject_source_time_provenance_and_pair_tampering(self):
        original = model("moon", "sun")
        cases = []
        def mutate(action):
            copy = deepcopy(original)
            action(copy)
            cases.append(copy)
        mutate(lambda x: x.update(format="fake"))
        mutate(lambda x: x["provenance"].update(ephemeris_sha256="fake"))
        mutate(lambda x: x["query"].update(origin="heliocentric"))
        mutate(lambda x: x["query"].update(bodies=["moon", "sun", "venus"]))
        mutate(lambda x: x.update(sample_count=999))
        mutate(lambda x: x["series"][0]["samples"][0].update(time_utc=instant(2)))
        mutate(lambda x: x["series"][0]["samples"][0].update(motion="retrograde"))
        mutate(lambda x: x["relationships"][0]["samples"][0].update(
            longitude_separation_deg=87))
        mutate(lambda x: x["relationships"][0]["samples"][0].update(aspects=[]))
        mutate(lambda x: x["event_markers"][0].update(name="eclipse"))
        mutate(lambda x: x["event_markers"][0].update(time_utc=instant(30)))
        mutate(lambda x: x["event_markers"].append(deepcopy(x["event_markers"][0])))
        for index, case in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(contract.ContractError):
                catalogue.build_catalogue(case)

    def test_source_only_without_event_search_is_explicit(self):
        original = model("moon", "sun", include_events=False)
        result = catalogue.build_catalogue(original)
        self.assertEqual(result["events"], [])
        self.assertEqual(result["search"]["status"], "not_requested")
        tampered = deepcopy(original)
        tampered["event_markers"] = [{"type":"invented"}]
        with self.assertRaisesRegex(contract.ContractError, "not requested"):
            catalogue.build_catalogue(tampered)

    def test_command_line_accepts_m4_json_without_writing_files(self):
        raw = model("moon", "sun", days=2)
        script = Path(catalogue.__file__)
        run = subprocess.run([sys.executable, str(script)], input=json.dumps(raw),
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        parsed = json.loads(run.stdout)
        self.assertEqual(parsed["format"], catalogue.FORMAT)
        self.assertTrue(parsed["events"])
        bad = subprocess.run([sys.executable, str(script)], input='{"hello":1}',
                             capture_output=True, text=True, timeout=15)
        self.assertEqual(bad.returncode, 2)
        self.assertEqual(bad.stdout, "")
        self.assertIn("MAGICK M6-A ERROR:", bad.stderr)


@unittest.skipUnless(os.environ.get("MAGICK_M1_KERNEL"),
                     "official JPL DE440s kernel not provided")
class RealJplCatalogueTests(unittest.TestCase):
    def test_real_jpl_event_catalogue_retains_source_without_exaggeration(self):
        raw = visual.compute_visual_data({
            "format":visual.FORMAT,
            "start_utc":"2026-10-01T00:00:00Z",
            "end_utc":"2026-10-25T00:00:00Z",
            "bodies":["moon","sun"],
            "step_hours":12,
            "include_events":True,
        }, os.environ["MAGICK_M1_KERNEL"])
        cat = catalogue.build_catalogue(raw)
        self.assertEqual(cat["source"]["ephemeris_id"], "de440s.bsp")
        self.assertEqual(cat["source"]["ephemeris_sha256"],
                         raw["provenance"]["ephemeris_sha256"])
        self.assertEqual(len(cat["events"]), len(raw["event_markers"]))
        self.assertGreaterEqual(len(cat["events"]), 4)
        self.assertTrue(all(e["category"] in ("aspect", "motion_station")
                            for e in cat["events"]))
        self.assertTrue(all(e["classification"] != "physical_force"
                            for e in cat["events"]))


if __name__ == "__main__":
    unittest.main()
