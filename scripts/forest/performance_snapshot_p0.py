#!/usr/bin/env python3
"""Forest Performance P0 // explicit read-only Ollama/host observation.

No inference, prewarm, session, scheduler, credentials or process control.
Only GET /api/version and /api/ps on literal loopback after CLI invocation.
Resident-model fields are untrusted provider claims, not actual free VRAM.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import socket
import sys
import time

from ollama_inventory import DEFAULT_ENDPOINT, InventoryFailure, VALID_NAME, _target

SCHEMA = "post-apollo.forest.performance-snapshot.readonly-p0"
MAX_BODY_BYTES = 1024 * 1024
MAX_MODELS = 256
MAX_MEMINFO_BYTES = 8192
MAX_QUANTITY = 2**63 - 1
TIMEOUT_SECONDS = 2.5
VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")


class ProbeFailure(Exception):
    """Fixed refusal code. Never disclose remote bodies, URLs or OS exceptions."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate key")
        obj[key] = value
    return obj


def _read_json(host: str, port: int, path: str) -> object:
    """One bounded GET; redirects and other destinations are never followed."""
    if path not in ("/api/version", "/api/ps"):
        raise ProbeFailure("INVALID_PROBE_PATH")
    connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ProbeFailure("OLLAMA_HTTP_ERROR")
        media_type = (response.getheader("Content-Type") or "").split(";", 1)[0]
        if media_type.strip().lower() != "application/json":
            raise ProbeFailure("OLLAMA_CONTENT_TYPE")
        data = response.read(MAX_BODY_BYTES + 1)
        if len(data) > MAX_BODY_BYTES:
            raise ProbeFailure("OLLAMA_RESPONSE_TOO_LARGE")
    except (socket.timeout, TimeoutError) as exc:
        raise ProbeFailure("OLLAMA_TIMEOUT") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise ProbeFailure("OLLAMA_UNAVAILABLE") from exc
    finally:
        connection.close()
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=_unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProbeFailure("OLLAMA_INVALID_JSON") from exc


def _version(payload: object) -> str:
    if type(payload) is not dict or not VERSION.fullmatch(
        payload.get("version") if type(payload.get("version")) is str else ""
    ):
        raise ProbeFailure("OLLAMA_VERSION_INVALID")
    return payload["version"]


def _quantity(value: object, *, allow_none: bool = False, zero: bool = True):
    if allow_none and value is None:
        return None
    if (type(value) is not int or value < (0 if zero else 1)
            or value > MAX_QUANTITY):
        raise ProbeFailure("OLLAMA_RESIDENCY_INVALID")
    return value


def _residency(payload: object) -> list[dict[str, object]]:
    if type(payload) is not dict or type(payload.get("models")) is not list:
        raise ProbeFailure("OLLAMA_RESIDENCY_INVALID")
    records = payload["models"]
    if len(records) > MAX_MODELS:
        raise ProbeFailure("OLLAMA_RESIDENCY_LIMIT")
    seen = set()
    results = []
    for item in records:
        if type(item) is not dict:
            raise ProbeFailure("OLLAMA_RESIDENCY_INVALID")
        name = item.get("name", item.get("model"))
        alias = item.get("model", name)
        if (type(name) is not str or not VALID_NAME.fullmatch(name)
                or alias != name or name in seen):
            raise ProbeFailure("OLLAMA_RESIDENCY_INVALID")
        seen.add(name)
        if "size" not in item:
            raise ProbeFailure("OLLAMA_RESIDENCY_INVALID")
        size = _quantity(item["size"])
        vram = _quantity(item.get("size_vram"), allow_none=True)
        context = _quantity(
            item.get("context_length"), allow_none=True, zero=False)
        results.append({
            "model": name,
            "size_bytes_reported": size,
            "vram_bytes_reported": vram,
            "context_length_reported": context,
        })
    return sorted(results, key=lambda row: row["model"])


def _parse_mem_available(text: object):
    """Return MiB from /proc/meminfo or None; never guess unavailable values."""
    if type(text) is not str or len(text) > MAX_MEMINFO_BYTES:
        return None
    matches = re.findall(r"^MemAvailable:\s+([0-9]+) kB\s*$", text, re.M)
    if len(matches) != 1:
        return None
    value = int(matches[0])
    return value // 1024 if value <= MAX_QUANTITY else None


def _host_memory_available_mib():
    """Fixed, read-only Linux resource hint; container limits may differ."""
    try:
        with open("/proc/meminfo", encoding="ascii") as source:
            return _parse_mem_available(source.read(MAX_MEMINFO_BYTES + 1))
    except (OSError, UnicodeError, ValueError):
        return None


def snapshot(endpoint: str = DEFAULT_ENDPOINT) -> dict[str, object]:
    """Collect observation only. No prompt/generation or persistent writes."""
    try:
        host, port = _target(endpoint)
    except InventoryFailure as exc:
        raise ProbeFailure(exc.reason) from exc
    begin = time.monotonic_ns()
    version = _version(_read_json(host, port, "/api/version"))
    resident = _residency(_read_json(host, port, "/api/ps"))
    elapsed_ns = time.monotonic_ns() - begin
    cpu_threads = os.cpu_count()
    if type(cpu_threads) is not int or not 1 <= cpu_threads <= 65536:
        cpu_threads = None
    vram_total = None
    if all(row["vram_bytes_reported"] is not None for row in resident):
        vram_total = sum(row["vram_bytes_reported"] for row in resident)
    return {
        "schema": SCHEMA,
        "status": "OBSERVED",
        "provider": "ollama",
        "version": version,
        "resident_models": resident,
        "resident_model_count": len(resident),
        "vram_bytes_reported_total": vram_total,
        "host_visible_cpu_threads": cpu_threads,
        "host_mem_available_mib": _host_memory_available_mib(),
        "observer_roundtrip_ms": round(max(0, elapsed_ns) / 1_000_000, 3),
        "measurement_scope": "LOCAL_PROVIDER_AND_HOST_HINTS_ONLY",
        "inference_latency_measured": False,
        "generation_requested": False,
        "model_load_requested": False,
        "governor_decision": "NOT_EVALUATED",
        "production_authority": False,
    }


def _unavailable(code: str) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "status": "UNAVAILABLE",
        "reason": code,
        "resident_models": [],
        "resident_model_count": 0,
        "inference_latency_measured": False,
        "generation_requested": False,
        "model_load_requested": False,
        "production_authority": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Forest P0: read-only local Ollama residency snapshot")
    parser.add_argument("command", choices=["snapshot"])
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args(argv)
    try:
        data = snapshot(args.endpoint)
        status = 0
    except ProbeFailure as exc:
        data = _unavailable(exc.code)
        status = 2
    print(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
