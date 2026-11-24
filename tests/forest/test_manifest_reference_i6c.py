import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import manifest_reference_i6c as M

CONFIG_DIGEST = "sha256:" + "a" * 64
WEIGHT_DIGEST = "sha256:" + "b" * 64
META_DIGEST = "sha256:" + "c" * 64


def descriptor(kind, digest, size):
    return {"mediaType": kind, "digest": digest, "size": size}


def manifest():
    return {"schemaVersion": 2, "mediaType": M.MANIFEST,
            "config": descriptor(M.CONFIG, CONFIG_DIGEST, 42),
            "layers": [descriptor(M.WEIGHT, WEIGHT_DIGEST, 1024),
                       descriptor("application/vnd.ollama.image.template", META_DIGEST, 11)]}


def encoded(value):
    raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return raw, hashlib.sha256(raw).hexdigest()


class ManifestTests(unittest.TestCase):
    def test_hash_exact_bytes_and_resolve_weight(self):
        raw, digest = encoded(manifest())
        ref = M.inspect_manifest(raw, digest)
        self.assertEqual(ref.manifest_digest, "sha256:" + digest)
        self.assertEqual(ref.weight_digest, WEIGHT_DIGEST)
        self.assertEqual(ref.weight_size_bytes_declared, 1024)
        self.assertEqual(ref.layer_count, 2)
        self.assertEqual(M.inspect_manifest(raw, "sha256:" + digest), ref)

    def test_whitespace_changes_hash(self):
        raw, digest = encoded(manifest())
        with self.assertRaisesRegex(M.ManifestRefusal, "MANIFEST_DIGEST_MISMATCH"):
            M.inspect_manifest(raw + b"\n", digest)

    def test_public_projection_and_false_authority(self):
        raw, digest = encoded(manifest())
        result = M.public_status(raw, digest)
        self.assertEqual(result["status"], "REFERENCE_MATCH")
        self.assertTrue(result["manifest_digest_matches_supplied_reference"])
        self.assertTrue(result["single_weight_reference_observed"])
        for key in ("source_authenticated", "installed_artifact_verified",
                    "weight_bytes_verified", "provider_runtime_instance_verified",
                    "runner_mapping_verified", "model_binding_verified",
                    "memory_attributed_to_model", "accelerator_mapping_verified",
                    "resource_requirements_established", "resource_reserved",
                    "generation_requested", "model_load_requested",
                    "permission_granted", "production_authority"):
            self.assertIs(result[key], False)
        self.assertEqual(result["safe_actions"], [])
        output = json.dumps(result)
        for private in (CONFIG_DIGEST, WEIGHT_DIGEST, META_DIGEST, digest):
            self.assertNotIn(private, output)

    def test_refusal_discards_partial_values(self):
        raw, digest = encoded(manifest())
        result = M.public_status(raw, "f"*64)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertFalse(result["manifest_digest_matches_supplied_reference"])
        self.assertFalse(result["single_weight_reference_observed"])
        self.assertIsNone(result["layer_count"])
        self.assertIsNone(result["weight_size_bytes_declared"])

    def test_bad_byte_and_digest_bounds(self):
        for raw in (None, "", bytearray(b"{}"), b"", b"x"*(M.MAX_BYTES+1)):
            with self.assertRaisesRegex(M.ManifestRefusal, "INVALID_MANIFEST_BYTES"):
                M.inspect_manifest(raw, "a"*64)
        for digest in (None, True, "a"*12, "A"*64, "sha256:"+"a"*65):
            with self.assertRaisesRegex(M.ManifestRefusal, "INVALID_EXPECTED_DIGEST"):
                M.inspect_manifest(b"{}", digest)

    def test_strict_json(self):
        for raw in (b'{"schemaVersion":2,"schemaVersion":2}', b'{"x":NaN}',
                    b'\xff', b'not JSON', b'['*5000+b']'*5000):
            with self.assertRaisesRegex(M.ManifestRefusal, "INVALID_MANIFEST_JSON"):
                M.inspect_manifest(raw, hashlib.sha256(raw).hexdigest())

    def test_unsupported_layouts(self):
        for mutation in (
            {"schemaVersion": True}, {"schemaVersion": 1},
            {"mediaType": "application/vnd.ollama.manifest.list.v2+json"},
            {"manifests": []}, {"runner": "ggml"}, {"layers": []},
            {"layers": [manifest()["layers"][0]]*(M.MAX_LAYERS+1)},
        ):
            value = manifest()
            value.update(mutation)
            with self.assertRaisesRegex(M.ManifestRefusal, "UNSUPPORTED_MANIFEST_LAYOUT"):
                M.inspect_manifest(*encoded(value))

    def test_descriptor_validation(self):
        for mutation in ({"size": True}, {"size": -1}, {"size": 2**63},
                         {"digest": "sha256:abc"}, {"mediaType": []}, {"extra": 1}):
            value = manifest()
            value["layers"][0].update(mutation)
            with self.assertRaisesRegex(M.ManifestRefusal, "INVALID_LAYER_DESCRIPTOR"):
                M.inspect_manifest(*encoded(value))

    def test_bad_config(self):
        value = manifest()
        value["config"]["mediaType"] = M.WEIGHT
        with self.assertRaisesRegex(M.ManifestRefusal, "INVALID_CONFIG_REFERENCE"):
            M.inspect_manifest(*encoded(value))

    def test_duplicate_and_multiple_weight_references(self):
        value = manifest()
        value["layers"].append(copy.deepcopy(value["layers"][0]))
        with self.assertRaisesRegex(M.ManifestRefusal, "AMBIGUOUS_LAYER_REFERENCE"):
            M.inspect_manifest(*encoded(value))
        value["layers"][-1]["digest"] = "sha256:"+"d"*64
        with self.assertRaisesRegex(M.ManifestRefusal, "SINGLE_WEIGHT_REFERENCE_REQUIRED"):
            M.inspect_manifest(*encoded(value))

    def test_no_weight_or_zero_weight(self):
        value = manifest()
        value["layers"] = value["layers"][1:]
        with self.assertRaisesRegex(M.ManifestRefusal, "SINGLE_WEIGHT_REFERENCE_REQUIRED"):
            M.inspect_manifest(*encoded(value))
        value = manifest()
        value["layers"][0]["size"] = 0
        with self.assertRaisesRegex(M.ManifestRefusal, "INVALID_WEIGHT_REFERENCE"):
            M.inspect_manifest(*encoded(value))

    def test_unsupported_auxiliary_model_layers(self):
        for kind in ("tensor", "adapter", "projector", "draft", "embed", "unknown"):
            value = manifest()
            value["layers"][1]["mediaType"] = "application/vnd.ollama.image."+kind
            with self.assertRaisesRegex(M.ManifestRefusal, "UNSUPPORTED_LAYER_TYPE"):
                M.inspect_manifest(*encoded(value))
