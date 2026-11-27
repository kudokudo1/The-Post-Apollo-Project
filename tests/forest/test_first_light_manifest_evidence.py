"""Synthetic metadata classifier tests only; no network or artifact access."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import first_light_stage1 as stage
import first_light_manifest_evidence as evidence


def fixture():
    return {"schemaVersion": 2,
            "config": {"mediaType": "application/vnd.docker.container.image.v1+json",
                       "digest": "sha256:"+"a"*64, "size": 8},
            "layers": [{"mediaType": "application/vnd.ollama.image.model",
                        "digest": "sha256:"+"b"*64, "size": 16}]}


def classify(obj):
    raw = json.dumps(obj).encode()
    with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(raw).hexdigest()):
        return evidence.classify(raw)


class EvidenceTests(unittest.TestCase):
    def test_pin_before_json_and_no_file_or_network_access(self):
        raw = json.dumps(fixture()).encode()
        with patch.object(evidence.json, "loads", side_effect=AssertionError("parsed")):
            with self.assertRaisesRegex(stage.Hold, "^MANIFEST_DIGEST$"):
                evidence.classify(raw)
        with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(raw).hexdigest()), \
             patch("builtins.open", side_effect=AssertionError("opened")), \
             patch.object(stage.http.client, "HTTPSConnection", side_effect=AssertionError("network")):
            report = evidence.classify(raw)
        self.assertEqual(report["original_refusal"], "NONE")
        self.assertEqual(report["bounded_size_sum"], 24)
        self.assertTrue(report["aggregate_within_cap"])

    def test_optional_unknown_fields_never_disclosed_or_accepted(self):
        obj = fixture()
        obj["layers"][0].update({"from": "fixture-secret-path", "name": "fixture-name",
                                 "fixture-unknown-key": "fixture-secret-value",
                                 "urls": ["https://example.invalid/fixture"]})
        report = classify(obj)
        self.assertEqual(report["original_refusal"], "BLOB_DESCRIPTOR_KEYS")
        item = report["descriptors"][1]
        self.assertEqual(item["role"], "MODEL")
        self.assertEqual(item["unknown_key_count"], 2)
        self.assertEqual(item["from_kind"], "BOUNDED_STRING")
        self.assertEqual(item["name_kind"], "BOUNDED_STRING")
        rendered = json.dumps(report)
        for raw in ("fixture-secret-path", "fixture-name", "fixture-unknown-key",
                    "fixture-secret-value", "example.invalid", "sha256:"+"b"*64):
            self.assertNotIn(raw, rendered)
        self.assertEqual(report["bounded_size_sum"], 24)

    def test_size_and_digest_failure_classes(self):
        for size, kind in ((0, "ZERO"), (-1, "NEGATIVE"), (True, "NONINTEGER"),
                           (stage.MODEL_LIMIT+1, "OVER_CAP")):
            obj = fixture()
            obj["layers"][0]["size"] = size
            report = classify(obj)
            self.assertEqual(report["original_refusal"], "BLOB_SIZE")
            self.assertEqual(report["descriptors"][1]["size_kind"], kind)
            self.assertIsNone(report["bounded_size_sum"])
        obj = fixture()
        obj["layers"][0]["digest"] = obj["config"]["digest"]
        self.assertTrue(classify(obj)["duplicate_valid_digest"])
        obj["layers"][0]["digest"] = "invalid"
        self.assertFalse(classify(obj)["descriptors"][1]["digest_format_valid"])
        obj = fixture()
        obj["layers"][0]["size"] = stage.MODEL_LIMIT
        self.assertEqual(classify(obj)["original_refusal"], "MODEL_BYTE_LIMIT")
        self.assertFalse(classify(obj)["aggregate_within_cap"])

    def test_nonfinite_json_refuses_before_strict_parser(self):
        for token in (b"NaN", b"Infinity", b"-Infinity", b"1e999", b"-1E999"):
            for raw in (b'{"schemaVersion":2,"config":{"size":' + token + b'},"layers":[{}]}',
                        b'{"schemaVersion":2,"config":{},"layers":[{"name":[{"nested":'
                        + token + b'}]}]}'):
                with self.subTest(token=token, raw=raw):
                    with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(raw).hexdigest()), \
                         patch.object(stage, "parse_manifest", side_effect=AssertionError("parsed")):
                        with self.assertRaisesRegex(stage.Hold, "^MANIFEST_JSON$"):
                            evidence.classify(raw)

    def test_finite_float_does_not_relax_descriptor_policy(self):
        obj = fixture()
        obj["layers"][0]["size"] = 16.0
        report = classify(obj)
        self.assertEqual(report["original_refusal"], "BLOB_SIZE")
        self.assertEqual(report["descriptors"][1]["size_kind"], "NONINTEGER")
        self.assertIsNone(report["bounded_size_sum"])
        self.assertFalse(report["aggregate_within_cap"])
        obj = fixture()
        obj["layers"][0]["name"] = 1e308
        report = classify(obj)
        self.assertEqual(report["original_refusal"], "BLOB_DESCRIPTOR_KEYS")
        self.assertEqual(report["descriptors"][1]["name_kind"], "NONSTRING")
        self.assertNotIn("1e+308", json.dumps(report))

    def test_shape_duplicate_json_and_metadata_bounds(self):
        obj = fixture()
        obj["layers"] *= 17
        report = classify(obj)
        self.assertEqual(report["original_refusal"], "MANIFEST_SHAPE")
        self.assertEqual(report["descriptors"], [])
        raw = b'{"schemaVersion":2,"schemaVersion":2}'
        with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(stage.Hold, "^DUPLICATE_JSON_KEY$"):
                evidence.classify(raw)
        raw = b"x"*(stage.MANIFEST_LIMIT+1)
        with patch.object(stage, "MANIFEST_SHA", hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(stage.Hold, "^MANIFEST_DIGEST$"):
                evidence.classify(raw)
        obj = fixture()
        obj["layers"][0].update({"from": [], "name": "x"*513,
                                 "mediaType": "fixture-unknown-media"})
        item = classify(obj)["descriptors"][1]
        self.assertEqual(item["from_kind"], "NONSTRING")
        self.assertEqual(item["name_kind"], "LONG_STRING")
        self.assertEqual(item["role"], "UNKNOWN")
        self.assertNotIn("fixture-unknown-media", json.dumps(item))


if __name__ == "__main__":
    unittest.main()
