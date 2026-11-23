#!/usr/bin/env python3
"""Forest P2B // opt-in one-shot synthetic Ollama latency benchmark.

No request on import. CLI requires explicit operator acknowledgments.
No prompts, answers, reasoning or private data in output; no persistence,
process control, model pulls, unloads, retries, tools, C5 or ForestW.
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import sys
import time

from ollama_inventory import InventoryFailure, VALID_NAME, _target, inventory
from performance_snapshot_p0 import ProbeFailure, snapshot

SCHEMA = "post-apollo.forest.performance-benchmark.p2b"
PROMPT = "Reply with exactly the word READY."
NUM_CTX = 2048
NUM_PREDICT = 32
MAX_LINE = 65536
MAX_STREAM_BYTES = 524288
MAX_FRAMES = 512
MAX_OUTPUT_BYTES = 4096
MAX_NANOSECONDS = 10**15
MAX_COUNT = 10000000
CONNECT_TIMEOUT_SECONDS = 45
TOTAL_DEADLINE_SECONDS = 120
HEADROOM_MIB = 512


class BenchmarkRefusal(Exception):
    """Only expose fixed codes; never expose external exceptions or bodies."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _int(value, name, *, maximum=1000000, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise BenchmarkRefusal("INVALID_" + name)
    return value


def _json_object(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    try:
        parsed = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise BenchmarkRefusal("INVALID_STREAM_JSON") from exc
    if type(parsed) is not dict:
        raise BenchmarkRefusal("INVALID_STREAM_SCHEMA")
    return parsed


def _timings(final):
    """Validate all mandatory provider metrics, keep optional cache count null."""
    result = {}
    for key in ("total_duration", "load_duration", "prompt_eval_duration",
                "eval_duration"):
        value = _int(final.get(key), "PROVIDER_METRIC",
                     maximum=MAX_NANOSECONDS)
        result[key.replace("_duration", "_ms")] = round(value / 1000000, 3)
    for key in ("prompt_eval_count", "eval_count"):
        result[key] = _int(final.get(key), "PROVIDER_COUNT",
                           maximum=MAX_COUNT)
    cached = final.get("prompt_eval_cached_count")
    result["prompt_eval_cached_count"] = (
        None if cached is None else
        _int(cached, "PROVIDER_CACHE_COUNT", maximum=MAX_COUNT)
    )
    ev = final["eval_duration"]
    n = final["eval_count"]
    result["generated_tokens_per_second"] = (
        round(n * 1000000000 / ev, 3) if n > 0 and ev > 0 else None
    )
    return result


def _stream_one(*, host, port, model):
    """One POST; consume answer transiently and emit *only numeric metadata*."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": True,
        "think": False,
        "options": {"num_ctx": NUM_CTX, "num_predict": NUM_PREDICT},
    }, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    connection = http.client.HTTPConnection(
        host, port, timeout=CONNECT_TIMEOUT_SECONDS
    )
    start = time.monotonic_ns()
    headers_at = None
    first_content_at = None
    terminal_at = None
    total_bytes = 0
    total_output = 0
    frames = 0
    final = None
    try:
        connection.request("POST", "/api/chat", body=payload, headers={
            "Content-Type": "application/json", "Accept": "application/x-ndjson"
        })
        response = connection.getresponse()
        headers_at = time.monotonic_ns()
        if response.status != 200:
            raise BenchmarkRefusal("OLLAMA_HTTP_ERROR")
        media = (response.getheader("Content-Type") or "").split(";", 1)[0]
        if media.strip().lower() not in ("application/x-ndjson",
                                         "application/json"):
            raise BenchmarkRefusal("OLLAMA_STREAM_CONTENT_TYPE")
        while True:
            remaining_ns = (
                TOTAL_DEADLINE_SECONDS * 1000000000
                - (time.monotonic_ns() - start)
            )
            if remaining_ns <= 0:
                raise BenchmarkRefusal("BENCHMARK_DEADLINE")
            if connection.sock is not None:
                connection.sock.settimeout(
                    min(CONNECT_TIMEOUT_SECONDS,
                        max(0.001, remaining_ns / 1000000000))
                )
            line = response.readline(MAX_LINE + 1)
            observed_at = time.monotonic_ns()
            if observed_at - start > TOTAL_DEADLINE_SECONDS * 1000000000:
                raise BenchmarkRefusal("BENCHMARK_DEADLINE")
            if not line:
                break
            total_bytes += len(line)
            frames += 1
            if (len(line) > MAX_LINE or not line.endswith(b"\n")
                    or total_bytes > MAX_STREAM_BYTES or frames > MAX_FRAMES):
                raise BenchmarkRefusal("STREAM_LIMIT")
            packet = _json_object(line)
            if type(packet.get("done")) is not bool:
                raise BenchmarkRefusal("INVALID_STREAM_SCHEMA")
            if "model" in packet and packet["model"] != model:
                raise BenchmarkRefusal("MODEL_MISMATCH")
            if packet.get("error"):
                raise BenchmarkRefusal("OLLAMA_STREAM_ERROR")
            msg = packet.get("message", {})
            if type(msg) is not dict:
                raise BenchmarkRefusal("INVALID_STREAM_SCHEMA")
            if msg.get("tool_calls"):
                raise BenchmarkRefusal("TOOL_CALL_FORBIDDEN")
            if msg.get("thinking"):
                raise BenchmarkRefusal("THINKING_OUTPUT_FORBIDDEN")
            if "role" in msg and msg["role"] != "assistant":
                raise BenchmarkRefusal("INVALID_STREAM_SCHEMA")
            content = msg.get("content", "")
            if type(content) is not str:
                raise BenchmarkRefusal("INVALID_STREAM_SCHEMA")
            try:
                data_size = len(content.encode("utf-8"))
            except UnicodeError as exc:
                raise BenchmarkRefusal("INVALID_STREAM_SCHEMA") from exc
            total_output += data_size
            if total_output > MAX_OUTPUT_BYTES:
                raise BenchmarkRefusal("OUTPUT_LIMIT")
            if content and first_content_at is None:
                first_content_at = observed_at
            if packet["done"]:
                if final is not None:
                    raise BenchmarkRefusal("MULTIPLE_TERMINAL_FRAMES")
                if packet.get("model") != model:
                    raise BenchmarkRefusal("MODEL_MISMATCH")
                if packet.get("done_reason") not in (None, "stop"):
                    raise BenchmarkRefusal("OUTPUT_TRUNCATED")
                final = packet
                terminal_at = observed_at
            elif final is not None:
                raise BenchmarkRefusal("TRAILING_STREAM_FRAME")
        if final is None:
            raise BenchmarkRefusal("STREAM_INCOMPLETE")
        if first_content_at is None:
            raise BenchmarkRefusal("EMPTY_VISIBLE_OUTPUT")
        provider = _timings(final)
        return {
            "headers_latency_ms": round((headers_at - start) / 1000000, 3),
            "first_visible_content_ms": round(
                (first_content_at - start) / 1000000, 3
            ),
            "client_complete_ms": round((terminal_at - start) / 1000000, 3),
            "provider_total_ms": provider["total_ms"],
            "provider_load_ms": provider["load_ms"],
            "provider_prompt_eval_count": provider["prompt_eval_count"],
            "provider_prompt_eval_ms": provider["prompt_eval_ms"],
            "provider_prompt_cached_count": provider[
                "prompt_eval_cached_count"
            ],
            "provider_eval_count": provider["eval_count"],
            "provider_eval_ms": provider["eval_ms"],
            "provider_generated_tokens_per_second": provider[
                "generated_tokens_per_second"
            ],
        }
    except (socket.timeout, TimeoutError) as exc:
        raise BenchmarkRefusal("OLLAMA_TIMEOUT") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise BenchmarkRefusal("OLLAMA_UNAVAILABLE") from exc
    finally:
        connection.close()


def _checked_residency(report, model, scenario):
    resident = report["resident_models"]
    other = [r for r in resident if r["model"] != model]
    if other:
        raise BenchmarkRefusal("OTHER_RESIDENT_MODELS")
    entry = next((r for r in resident if r["model"] == model), None)
    if scenario == "cold" and entry is not None:
        raise BenchmarkRefusal("COLD_MODEL_ALREADY_RESIDENT")
    if scenario == "warm" and entry is None:
        raise BenchmarkRefusal("WARM_MODEL_NOT_RESIDENT")
    return entry


def benchmark_one(
    *, model, scenario, endpoint="http://127.0.0.1:11434",
    operator_approved=False, capacity_reviewed=False,
    no_competing_inference=False, required_host_mib=None,
    required_accelerator_mib=None, verified_free_accelerator_mib=None,
    expected_runtime="gpu",
):
    """Explicit ONE request max; no retries, persistence or shared authority."""
    if not (operator_approved is True and capacity_reviewed is True
            and no_competing_inference is True):
        raise BenchmarkRefusal("OPERATOR_APPROVAL_REQUIRED")
    if type(model) is not str or not VALID_NAME.fullmatch(model):
        raise BenchmarkRefusal("INVALID_MODEL")
    if scenario not in ("cold", "warm"):
        raise BenchmarkRefusal("INVALID_SCENARIO")
    if expected_runtime not in ("cpu", "gpu"):
        raise BenchmarkRefusal("INVALID_RUNTIME")
    ram = _int(required_host_mib, "REQUIRED_HOST_MIB", minimum=1)
    gpu_need = _int(required_accelerator_mib, "REQUIRED_ACCELERATOR_MIB")
    gpu_free = _int(verified_free_accelerator_mib, "VERIFIED_FREE_ACCELERATOR_MIB")
    if gpu_free < gpu_need or (
        expected_runtime == "gpu" and gpu_need == 0
    ) or (expected_runtime == "cpu" and gpu_need != 0):
        raise BenchmarkRefusal("CAPACITY_NOT_ESTABLISHED")
    try:
        host, port = _target(endpoint)
    except InventoryFailure as exc:
        raise BenchmarkRefusal(exc.reason) from exc
    try:
        installed = inventory(endpoint)
        if model not in {row["name"] for row in installed["models"]}:
            raise BenchmarkRefusal("MODEL_NOT_INSTALLED")
        before = snapshot(endpoint)
        pre_resident = _checked_residency(before, model, scenario)
        free_ram = before["host_mem_available_mib"]
        if type(free_ram) is not int or free_ram < ram + HEADROOM_MIB:
            raise BenchmarkRefusal("HOST_CAPACITY_NOT_ESTABLISHED")
        if pre_resident is not None and (
                expected_runtime == "gpu"
                and (pre_resident["vram_bytes_reported"] is None
                     or pre_resident["vram_bytes_reported"] == 0)):
            raise BenchmarkRefusal("RUNTIME_MISMATCH")
    except (InventoryFailure, ProbeFailure) as exc:
        raise BenchmarkRefusal("PREFLIGHT_UNAVAILABLE") from exc
    measurements = _stream_one(host=host, port=port, model=model)
    try:
        after = snapshot(endpoint)
    except ProbeFailure as exc:
        raise BenchmarkRefusal("POST_SNAPSHOT_UNAVAILABLE") from exc
    post_resident = _checked_residency(after, model, "warm")
    if before["version"] != after["version"]:
        raise BenchmarkRefusal("OLLAMA_VERSION_CHANGED")
    if (expected_runtime == "gpu" and (
            post_resident["vram_bytes_reported"] is None
            or post_resident["vram_bytes_reported"] == 0)
        ) or (expected_runtime == "cpu"
              and post_resident["vram_bytes_reported"] != 0):
        raise BenchmarkRefusal("RUNTIME_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": "COMPLETE",
        "scenario": scenario,
        "model": model,
        "ollama_version": before["version"],
        "requested_context_tokens": NUM_CTX,
        "requested_output_tokens": NUM_PREDICT,
        "requested_thinking": False,
        "concurrency": 1,
        "before_resident": pre_resident is not None,
        "after_resident": True,
        "before_host_mem_available_mib": free_ram,
        "before_resident_vram_bytes_reported": (
            pre_resident["vram_bytes_reported"] if pre_resident else None
        ),
        **measurements,
        "c5_authority": "NOT_EVALUATED",
        "permission_granted": False,
        "production_authority": False,
    }


def refusal(code):
    return {
        "schema": SCHEMA, "status": "REFUSED", "reason": code,
        "c5_authority": "NOT_EVALUATED",
        "permission_granted": False, "production_authority": False,
        "inference_complete": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Forest P2B: one synthetic inference attempt, opt-in only")
    parser.add_argument("command", choices=["one"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--scenario", choices=("cold", "warm"), required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--operator-approved", action="store_true")
    parser.add_argument("--capacity-reviewed", action="store_true")
    parser.add_argument("--no-competing-inference", action="store_true")
    parser.add_argument("--required-host-mib", type=int)
    parser.add_argument("--required-accelerator-mib", type=int)
    parser.add_argument("--verified-free-accelerator-mib", type=int)
    parser.add_argument("--expected-runtime", choices=("cpu", "gpu"),
                        default="gpu")
    args = parser.parse_args(argv)
    try:
        result = benchmark_one(
            model=args.model, scenario=args.scenario, endpoint=args.endpoint,
            operator_approved=args.operator_approved,
            capacity_reviewed=args.capacity_reviewed,
            no_competing_inference=args.no_competing_inference,
            required_host_mib=args.required_host_mib,
            required_accelerator_mib=args.required_accelerator_mib,
            verified_free_accelerator_mib=args.verified_free_accelerator_mib,
            expected_runtime=args.expected_runtime,
        )
        exit_code = 0
    except KeyboardInterrupt:
        result, exit_code = refusal("CANCELLED"), 2
    except BenchmarkRefusal as exc:
        result, exit_code = refusal(exc.code), 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
