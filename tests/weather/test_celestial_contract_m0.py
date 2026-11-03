"""M0 contract edge tests.

Run: python3 -m unittest discover -s tests/weather -p 'test_celestial_contract_m0.py'
"""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "weather"))
import celestial_contract as contract


class CelestialContractTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "format": contract.REQUEST_FORMAT,
            "instant_utc": "2026-11-03T11:45:00Z",
            "origin": "geocentric",
            "position_model": "apparent",
            "frame": contract.FRAME,
            "bodies": ["moon", "sun"],
        }
        self.snapshot = {
            "format": contract.SNAPSHOT_FORMAT,
            "request": self.request,
            "tdb_jd": 2461717.99,  # fixture only, not an astronomical assertion
            "provenance": {
                "engine": "fixture", "engine_version": "0-test",
                "ephemeris_id": "fixture", "ephemeris_sha256": "a" * 64,
                "time_data_id": "fixture", "generated_at_utc": "2026-11-03T11:46:00Z",
            },
            "positions": [
                {"body": "moon", "longitude_deg": 315.0, "latitude_deg": 3.0, "distance_au": .0026},
                {"body": "sun", "longitude_deg": 220.0, "latitude_deg": 0.0, "distance_au": 1.0},
            ],
        }

    def reject_request(self, field, value):
        raw = copy.deepcopy(self.request)
        raw[field] = value
        with self.assertRaises(contract.ContractError):
            contract.normalize_request(raw)

    def test_canonical_request_and_utc(self):
        normalized = contract.normalize_request(self.request)
        self.assertEqual(normalized["instant_utc"], "2026-11-03T11:45:00.000000Z")
        self.assertEqual(normalized["bodies"], ["moon", "sun"])
        self.assertIsNone(normalized["observer"])
        self.assertEqual(contract.utc_instant("2026-11-03T11:45:00.125Z"),
                         "2026-11-03T11:45:00.125000Z")

    def test_strict_time_prevents_dst_ambiguity(self):
        for value in ["2026-11-03 11:45", "2026-11-03T11:45:00-05:00",
                      "2026-02-30T11:45:00Z", "2026-11-03T24:00:00Z", None]:
            with self.subTest(value=value):
                self.reject_request("instant_utc", value)

    def test_unknown_mixed_or_duplicate_bodies_rejected(self):
        for items in [["moon", "moon"], ["sun", "earth"], ["moon", "fake"], [], "moon"]:
            with self.subTest(items=items):
                self.reject_request("bodies", items)
        self.reject_request("frame", "ICRF")
        self.reject_request("position_model", "unknown")

    def test_observer_is_explicit_and_numeric(self):
        raw = copy.deepcopy(self.request)
        raw["origin"] = "topocentric"
        raw["observer"] = {"latitude_deg": 38.9, "longitude_deg": -76.7, "elevation_m": 0}
        self.assertEqual(contract.normalize_request(raw)["observer"]["longitude_deg"], -76.7)
        raw["observer"]["latitude_deg"] = True
        with self.assertRaises(contract.ContractError):
            contract.normalize_request(raw)
        raw["observer"]["latitude_deg"] = 91
        with self.assertRaises(contract.ContractError):
            contract.normalize_request(raw)
        self.reject_request("observer", {"latitude_deg": 0, "longitude_deg": 0, "elevation_m": 0})

    def test_heliocentric_requires_geometric_model(self):
        raw = copy.deepcopy(self.request)
        raw["origin"] = "heliocentric"
        with self.assertRaises(contract.ContractError):
            contract.normalize_request(raw)
        raw["position_model"] = "geometric"
        raw["bodies"] = ["moon", "earth"]
        self.assertEqual(contract.normalize_request(raw)["origin"], "heliocentric")
        raw["bodies"] = ["sun"]
        with self.assertRaises(contract.ContractError):
            contract.normalize_request(raw)

    def test_valid_snapshot(self):
        result = contract.validate_snapshot(self.snapshot)
        self.assertEqual(result["body_count"], 2)
        self.assertEqual(result["request"]["origin"], "geocentric")

    def test_snapshot_rejects_fake_or_mismatched_measurements(self):
        cases = [
            ("longitude_deg", 360), ("longitude_deg", -0.01),
            ("latitude_deg", 92), ("distance_au", -1),
            ("distance_au", float("nan")), ("longitude_deg", True),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                raw = copy.deepcopy(self.snapshot)
                raw["positions"][0][field] = value
                with self.assertRaises(contract.ContractError):
                    contract.validate_snapshot(raw)
        raw = copy.deepcopy(self.snapshot)
        raw["positions"][1]["body"] = "moon"
        with self.assertRaises(contract.ContractError):
            contract.validate_snapshot(raw)
        raw = copy.deepcopy(self.snapshot)
        del raw["positions"][0]["longitude_deg"]
        with self.assertRaises(contract.ContractError):
            contract.validate_snapshot(raw)

    def test_snapshot_requires_reproducible_provenance(self):
        raw = copy.deepcopy(self.snapshot)
        raw["provenance"]["ephemeris_sha256"] = "not-a-hash"
        with self.assertRaises(contract.ContractError):
            contract.validate_snapshot(raw)
        raw = copy.deepcopy(self.snapshot)
        del raw["provenance"]["time_data_id"]
        with self.assertRaises(contract.ContractError):
            contract.validate_snapshot(raw)


if __name__ == "__main__":
    unittest.main()
