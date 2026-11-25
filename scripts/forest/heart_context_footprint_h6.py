#!/usr/bin/env python3
"""H6: offline dense-attention FP16 KV payload scenarios, not admission."""
import argparse
import json
import sys

from performance_snapshot_p0 import _unique_pairs

SCHEMA = "post-apollo.forest.heart-context-footprint.h6"
MAX_INPUT = 2 * 1024 * 1024
CONTEXTS = (512, 1024, 2048, 4096, 8192)
ARCHITECTURES = ("granite", "qwen3")


class FootprintRefusal(ValueError):
    pass


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise FootprintRefusal("INVALID_MODEL_DIMENSION")
    return value


def estimate(raw):
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_INPUT:
        raise FootprintRefusal("INPUT_LIMIT")
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise FootprintRefusal("INVALID_METADATA_JSON") from None
    if type(payload) is not dict or type(payload.get("model_info")) is not dict:
        raise FootprintRefusal("MODEL_METADATA_UNAVAILABLE")
    info = payload["model_info"]
    arch = info.get("general.architecture")
    if type(arch) is not str or arch not in ARCHITECTURES:
        raise FootprintRefusal("UNSUPPORTED_ARCHITECTURE")
    prefix = arch + "."
    # Restrict to a scalar uniform attention scenario. Do not interpret
    # special layouts as ordinary dense KV, or silently use scalar defaults
    # for missing/nonuniform head counts.
    unsupported = (
        "attention.sliding_window", "attention.sliding_window_pattern",
        "attention.shared_kv_layers", "attention.kv_lora_rank",
        "attention.key_length_swa", "attention.value_length_swa",
        "attention.key_length_mla", "attention.value_length_mla",
        "full_attention_interval", "ssm.state_size", "nextn_predict_layers",
    )
    if any(prefix + key in info for key in unsupported):
        raise FootprintRefusal("SPECIAL_LAYOUT_UNSUPPORTED")

    def get(key, minimum, maximum):
        return _integer(info.get(prefix + key), minimum, maximum)

    layers = get("block_count", 1, 256)
    heads = get("attention.head_count", 1, 256)
    kv = get("attention.head_count_kv", 1, heads)
    if heads % kv:
        raise FootprintRefusal("INVALID_HEAD_GROUPS")
    embedding = get("embedding_length", 1, 65536)
    context = get("context_length", 1, 2**31 - 1)

    def head_width(key):
        if prefix + key in info:
            return get(key, 1, 4096), "EXPLICIT_METADATA"
        if embedding % heads:
            raise FootprintRefusal("HEAD_WIDTH_UNAVAILABLE")
        return _integer(embedding // heads, 1, 4096), "EMBEDDING_DIVIDED_BY_HEADS"

    key_width, key_source = head_width("attention.key_length")
    value_width, value_source = head_width("attention.value_length")
    # One sequence, two bytes per scalar, all layers, no padding or
    # allocation overhead. Actual cache type and placement are unknown.
    per_token = layers * kv * (key_width + value_width) * 2
    return {
        **base(),
        "status": "ESTIMATED_SCENARIO",
        "architecture_reported": arch,
        "key_width_source": key_source,
        "value_width_source": value_source,
        "bytes_per_token_fp16_scenario": per_token,
        "context_scenarios": [
            {"context_tokens": n, "kv_payload_bytes": n * per_token}
            for n in CONTEXTS if n <= context
        ],
    }


def base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "UNAUTHENTICATED_METADATA_DENSE_FP16_KV_SCENARIO",
        "sequences_assumed": 1,
        "bytes_per_scalar_assumed": 2,
        "actual_cache_type_verified": False,
        "actual_cache_placement_verified": False,
        "model_identity_verified": False,
        "model_weights_included": False,
        "allocator_overhead_included": False,
        "runtime_requirement_established": False,
        "allocatable_capacity_established": False,
        "resource_reserved": False,
        "safe_to_start_inference": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def main():
    parser = argparse.ArgumentParser(description="H6: estimate hypothetical KV payload from local metadata JSON on stdin")
    parser.parse_args()
    try:
        data, code = estimate(sys.stdin.buffer.read(MAX_INPUT + 1)), 0
    except FootprintRefusal as exc:
        data, code = {**base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except (OSError, KeyboardInterrupt):
        data, code = {**base(), "status": "UNAVAILABLE", "reason": "INPUT_UNAVAILABLE"}, 2
    print(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
