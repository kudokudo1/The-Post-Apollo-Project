#!/usr/bin/env python3
"""Strict pointer-origin candidate checks; NO trusted compositor source yet.

Sway GET_OUTPUTS provides monitor geometry and GET_SEATS provides keyboard
focus. NEITHER proves where the physical cursor is or which surface is under
it. Geometry-consistent candidate data is therefore NOT authorization to
show the overlay, grab a mouse, or inject scrolling.

The only potential live authority is a future independently verified,
compositor-origin pointer-event provider. There is no default, environment
override, self-reported JSON switch or keyboard-focus fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Optional

MAX_EVENT_AGE_NS = 75_000_000
MAX_FUTURE_SKEW_NS = 1_000_000
OUTPUT = re.compile(r"^[A-Za-z0-9_.:+-]{1,120}$")
DEVICE = re.compile(r"^[A-Za-z0-9_.:+-]{1,160}$")
SEAT = re.compile(r"^[A-Za-z0-9_.:+-]{1,100}$")


class WitnessError(Exception):
    pass


@dataclass(frozen=True)
class PointerCandidate:
    """Coordinates checked for internal consistency; NOT trusted evidence."""
    seat: str
    device: str
    output: str
    x: float
    y: float
    global_x: float
    global_y: float
    target_node: int
    event_time_ns: int
    generation: int
    source_trusted: bool = False
    overlay_allowed: bool = False
    live_input_allowed: bool = False


def _number(value):
    return (isinstance(value, (float, int))
            and not isinstance(value, bool)
            and math.isfinite(value))


def _validate_layout(layout):
    if not isinstance(layout, list) or not 1 <= len(layout) <= 16:
        raise WitnessError("INVALID_LAYOUT")
    names = set()
    clean = []
    for item in layout:
        if not isinstance(item, dict):
            raise WitnessError("INVALID_LAYOUT")
        name = item.get("name")
        if not isinstance(name, str) or not OUTPUT.fullmatch(name):
            raise WitnessError("INVALID_OUTPUT")
        if name in names:
            raise WitnessError("DUPLICATE_OUTPUT")
        names.add(name)
        for key in ("x", "y", "width", "height"):
            if not isinstance(item.get(key), int) or isinstance(item.get(key), bool):
                raise WitnessError("INVALID_OUTPUT_GEOMETRY")
        if (not -100000 <= item["x"] <= 100000
                or not -100000 <= item["y"] <= 100000
                or not 1 <= item["width"] <= 16384
                or not 1 <= item["height"] <= 16384):
            raise WitnessError("INVALID_OUTPUT_GEOMETRY")
        scale = item.get("scale")
        if not _number(scale) or not 0.5 <= scale <= 6:
            raise WitnessError("INVALID_OUTPUT_SCALE")
        clean.append((name, item["x"], item["y"], item["width"],
                      item["height"], float(scale)))
    return sorted(clean)


def check_candidate(
    evidence: dict,
    layout_before: list,
    layout_after: list,
    *,
    expected_device: str,
    expected_seat: str,
    expected_generation: int,
    now_ns: int
) -> PointerCandidate:
    """Validate geometry, timing and identity; never confer input authority."""
    before = _validate_layout(layout_before)
    after = _validate_layout(layout_after)
    if before != after:
        raise WitnessError("OUTPUT_LAYOUT_CHANGED")
    if not isinstance(evidence, dict):
        raise WitnessError("INVALID_WITNESS")
    # Reject extra fields instead of silently accepting a forged
    # "authorized":true / "compositor_signed":true flag.
    required = {"seat", "device", "output", "x", "y",
                "target_node", "event_time_ns", "generation"}
    if set(evidence) != required:
        raise WitnessError("INVALID_WITNESS_FIELDS")
    seat, device = evidence["seat"], evidence["device"]
    if (not isinstance(seat, str) or not SEAT.fullmatch(seat)
            or not isinstance(device, str) or not DEVICE.fullmatch(device)
            or seat != expected_seat or device != expected_device):
        raise WitnessError("WRONG_DEVICE_OR_SEAT")
    generation = evidence["generation"]
    if (type(generation) is not int or generation <= 0
            or generation != expected_generation):
        raise WitnessError("STALE_GENERATION")
    target = evidence["target_node"]
    if type(target) is not int or target <= 0:
        raise WitnessError("NO_POINTER_TARGET")
    timestamp = evidence["event_time_ns"]
    if type(timestamp) is not int or type(now_ns) is not int or now_ns < 0:
        raise WitnessError("INVALID_EVENT_TIMESTAMP")
    age = now_ns - timestamp
    if age > MAX_EVENT_AGE_NS or age < -MAX_FUTURE_SKEW_NS:
        raise WitnessError("STALE_OR_FUTURE_WITNESS")
    output = evidence["output"]
    x, y = evidence["x"], evidence["y"]
    if (not isinstance(output, str) or not OUTPUT.fullmatch(output)
            or not _number(x) or not _number(y)):
        raise WitnessError("INVALID_CURSOR_COORDINATE")
    chosen = next((r for r in before if r[0] == output), None)
    if chosen is None:
        raise WitnessError("OUTPUT_DISCONNECTED")
    name, left, top, width, height, _scale = chosen
    if not 0 <= x < width or not 0 <= y < height:
        raise WitnessError("CURSOR_OUTSIDE_OUTPUT")
    gx, gy = left + float(x), top + float(y)
    if sum(
        1 for _, ox, oy, ow, oh, _s in before
        if ox <= gx < ox + ow and oy <= gy < oy + oh
    ) != 1:
        raise WitnessError("AMBIGUOUS_OUTPUT_OVERLAP")
    return PointerCandidate(
        seat, device, output, float(x), float(y), gx, gy,
        target, timestamp, generation
    )


def trusted_compositor_pointer_provider() -> None:
    """None until a real compositor-origin pointer/target feed is verified.

    Intentionally not replaceable by CLI flags or an environment variable.
    Future integration must independently authenticate origin, event linkage
    and pointer-under-cursor target at the triggering middle-button press.
    """
    return None


def require_verified_pointer_provider():
    provider = trusted_compositor_pointer_provider()
    if provider is None:
        raise WitnessError("COMPOSITOR_POINTER_TARGET_UNAVAILABLE")
    return provider
