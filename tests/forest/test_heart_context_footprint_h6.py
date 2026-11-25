import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_context_footprint_h6 as H


def fixture(arch="granite", **changes):
    info = {"general.architecture": arch}
    for k, v in {
        "block_count": 24, "attention.head_count": 16,
        "attention.head_count_kv": 4, "embedding_length": 2048,
        "context_length": 131072, **changes
    }.items():
        info[arch+"."+k] = v
    return {"model_info": info}


def estimate(payload):
    return H.estimate(json.dumps(payload).encode())


class ContextFootprintTests(unittest.TestCase):
    def test_formula_and_linear_scaling(self):
        out = estimate(fixture())
        self.assertEqual(out["bytes_per_token_fp16_scenario"], 49152)
        self.assertEqual([x["kv_payload_bytes"] for x in out["context_scenarios"]],
                         [25165824, 50331648, 100663296, 201326592, 402653184])

    def test_explicit_widths_precede_embedding_default(self):
        out = estimate(fixture("qwen3", **{"attention.key_length": 64,
                                           "attention.value_length": 128}))
        self.assertEqual(out["bytes_per_token_fp16_scenario"], 36864)
        self.assertEqual(out["key_width_source"], "EXPLICIT_METADATA")
        self.assertEqual(out["value_width_source"], "EXPLICIT_METADATA")

    def test_context_max_filters_scenarios(self):
        out = estimate(fixture(context_length=2048))
        self.assertEqual([x["context_tokens"] for x in out["context_scenarios"]],
                         [512, 1024, 2048])
        self.assertEqual(estimate(fixture(context_length=128))["context_scenarios"], [])

    def test_unknown_architecture_and_special_layout_refuse(self):
        with self.assertRaisesRegex(H.FootprintRefusal, "UNSUPPORTED_ARCHITECTURE"):
            estimate(fixture("granitehybrid"))
        for field in ("attention.sliding_window", "attention.shared_kv_layers",
                      "ssm.state_size", "attention.kv_lora_rank"):
            with self.assertRaisesRegex(H.FootprintRefusal, "SPECIAL_LAYOUT_UNSUPPORTED"):
                estimate(fixture(**{field: 1}))

    def test_missing_invalid_and_nonuniform_dimensions(self):
        for val in (None, True, 0, -1, 1.5, [4, 4], "4", 257):
            with self.assertRaises(H.FootprintRefusal):
                estimate(fixture(**{"attention.head_count_kv": val}))
        with self.assertRaisesRegex(H.FootprintRefusal, "INVALID_HEAD_GROUPS"):
            estimate(fixture(**{"attention.head_count_kv": 3}))
        with self.assertRaisesRegex(H.FootprintRefusal, "HEAD_WIDTH_UNAVAILABLE"):
            estimate(fixture(embedding_length=2047))
        with self.assertRaises(H.FootprintRefusal):
            estimate(fixture(**{"attention.key_length": 0}))

    def test_strict_input(self):
        for raw in (b"", b"x"*(H.MAX_INPUT+1), b'{"model_info":{},"model_info":{}}',
                    b'{"x":NaN}', b'\xff', b'[]', b'{}'):
            with self.assertRaises(H.FootprintRefusal):
                H.estimate(raw)

    def test_no_private_payload_or_authority(self):
        payload = fixture()
        payload["template"] = "PRIVATE_MARKER"
        payload["model_info"]["unrelated"] = "PRIVATE_MARKER"
        out = estimate(payload)
        self.assertNotIn("PRIVATE_MARKER", json.dumps(out))
        for key in ("actual_cache_type_verified", "model_identity_verified",
                    "model_weights_included", "runtime_requirement_established",
                    "allocatable_capacity_established", "resource_reserved",
                    "safe_to_start_inference", "permission_granted", "production_authority"):
            self.assertIs(out[key], False)
        self.assertEqual(out["safe_actions"], [])
