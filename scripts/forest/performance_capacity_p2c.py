#!/usr/bin/env python3
"""Forest P2C // opt-in read-only Fedora/Ollama resource observation.

No inference, model load, process control, scheduling, permission, or writes.
System DRM counters are diagnostic hints, NOT safely allocatable free VRAM.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

from ollama_inventory import DEFAULT_ENDPOINT, InventoryFailure, VALID_NAME, inventory
from performance_snapshot_p0 import ProbeFailure, snapshot

SCHEMA = "post-apollo.forest.performance-capacity.readonly-p2c"
MAX_GPU_CARDS = 8
MAX_VALUE_BYTES = 64
MAX_QUANTITY = 2**63 - 1
NUMBER = re.compile(rb"[0-9]+\n?")


class CapacityFailure(Exception):
    """Fixed refusal codes only; no file contents, host paths or exceptions."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _sysfs_uint(path):
    """Read one preselected sysfs decimal counter with strict size bounds."""
    try:
        with open(path, "rb") as source:
            raw = source.read(MAX_VALUE_BYTES + 1)
    except (OSError, ValueError):
        return None
    if len(raw) > MAX_VALUE_BYTES or not NUMBER.fullmatch(raw):
        return None
    value = int(raw)
    return value if value <= MAX_QUANTITY else None


def _gpu_devices(root="/sys/class/drm"):
    """Inspect fixed card slots only; no directory enumeration or processes."""
    result = []
    for i in range(MAX_GPU_CARDS):
        card = "card" + str(i)
        prefix = root + "/" + card + "/device/"
        total = _sysfs_uint(prefix + "mem_info_vram_total")
        used = _sysfs_uint(prefix + "mem_info_vram_used")
        if total is None and used is None:
            continue
        free_hint = (
            total - used
            if (total is not None and used is not None
                and 0 < total and 0 <= used <= total)
            else None
        )
        result.append({
            "card": card,
            "vram_total_bytes_reported": total,
            "vram_used_bytes_reported": used,
            "vram_headroom_bytes_estimated": free_hint,
            "measurement_scope": "DRM_SYSFS_DIAGNOSTIC_ONLY",
            "ollama_device_mapping_verified": False,
        })
    return result


def _process_affinity_threads():
    """Schedulable CPU count, NOT a free CPU capacity measurement."""
    try:
        threads = len(os.sched_getaffinity(0))
    except (OSError, AttributeError, ValueError):
        return None
    return threads if type(threads) is int and 1 <= threads <= 65536 else None


def inspect_capacity(*, endpoint=DEFAULT_ENDPOINT, model=None):
    """GET inventory + GET P0 snapshot + fixed sysfs reads only."""
    if model is not None and (
        type(model) is not str or not VALID_NAME.fullmatch(model)
    ):
        raise CapacityFailure("INVALID_MODEL")
    try:
        listed = inventory(endpoint)
        observed = snapshot(endpoint)
    except (InventoryFailure, ProbeFailure) as exc:
        raise CapacityFailure("LOCAL_OBSERVATION_UNAVAILABLE") from exc

    installed = listed["models"]
    resident = observed["resident_models"]
    if model is None:
        selected = None
    else:
        installed_record = next(
            (entry for entry in installed if entry["name"] == model), None
        )
        resident_record = next(
            (entry for entry in resident if entry["model"] == model), None
        )
        selected = {
            "model": model,
            "installed": installed_record is not None,
            # B0 size is a local artifact size, NOT RAM/VRAM requirement.
            "installed_artifact_bytes_reported": (
                installed_record["size_bytes"] if installed_record else None
            ),
            "resident": resident_record is not None,
            "resident_memory_bytes_reported": (
                resident_record["size_bytes_reported"]
                if resident_record else None
            ),
            "resident_vram_bytes_reported": (
                resident_record["vram_bytes_reported"]
                if resident_record else None
            ),
            "runtime_requirement_calibrated": False,
        }

    devices = _gpu_devices()
    return {
        "schema": SCHEMA,
        "status": "OBSERVED",
        "provider": "ollama",
        "ollama_version": observed["version"],
        "selected_model": selected,
        "installed_models": installed,
        "installed_model_count": listed["model_count"],
        "resident_models": resident,
        "resident_model_count": observed["resident_model_count"],
        "host_visible_cpu_threads": observed["host_visible_cpu_threads"],
        "process_affinity_cpu_threads": _process_affinity_threads(),
        "host_mem_available_mib": observed["host_mem_available_mib"],
        "gpu_devices": devices,
        "gpu_sysfs_status": (
            "COUNTERS_OBSERVED" if devices else "UNAVAILABLE"
        ),
        "gpu_sysfs_device_count": len(devices),
        "gpu_metrics_are_free_allocatable_vram": False,
        "ollama_device_mapping_verified": False,
        "resource_budget_established": False,
        "model_requirements_established": False,
        "exclusive_capacity_reserved": False,
        "generation_requested": False,
        "model_load_requested": False,
        "benchmark_permitted": False,
        "c5_authority": "NOT_EVALUATED",
        "permission_granted": False,
        "production_authority": False,
    }


def _refusal(code):
    return {
        "schema": SCHEMA,
        "status": "UNAVAILABLE",
        "reason": code,
        "generation_requested": False,
        "model_load_requested": False,
        "benchmark_permitted": False,
        "permission_granted": False,
        "production_authority": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Forest P2C: read-only local resource capacity hints"
    )
    parser.add_argument("command", choices=["inspect"])
    parser.add_argument("--model", help="exact installed model name to compare")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args(argv)
    try:
        output = inspect_capacity(endpoint=args.endpoint, model=args.model)
        code = 0
    except CapacityFailure as exc:
        output = _refusal(exc.code)
        code = 2
    print(json.dumps(output, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
