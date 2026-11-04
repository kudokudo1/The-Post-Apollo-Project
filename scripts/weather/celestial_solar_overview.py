"""V4d // bounded, compact Sun-centered multi-body JPL position atlas.

Unlike M4's 2-body aspect/event pipeline, this is POSITION DATA ONLY.
The source callback receives an exact JPL Sun->target geometric vector in
Skyfield's true ecliptic of date, at the same UTC grid as the M4 pair.
No network, orbit interpolation, invented targets, or writes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import hypot, isfinite

from celestial_contract import ContractError, FRAME

FORMAT = "post-apollo.weather.solar-overview.v1"
# Each identifier maps to its exact, explicitly named NAIF target. Planetary
# system barycenters are never mislabelled as physical planet centers.
BODIES = (
    "mercury", "venus", "earth", "moon", "mars_barycenter",
    "jupiter_barycenter", "saturn_barycenter",
    "uranus_barycenter", "neptune_barycenter", "pluto_barycenter",
)
MAX_BODIES = len(BODIES)
MAX_SAMPLES = 181
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def normalize_bodies(value):
    if not isinstance(value, list):
        raise ContractError("solar overview bodies must be an explicit list")
    if len(value) > MAX_BODIES or len(value) != len(set(
            v for v in value if isinstance(v, str))):
        raise ContractError("solar overview body list must be unique and bounded")
    if any(not isinstance(v, str) or v not in BODIES for v in value):
        raise ContractError("unsupported solar overview exact NAIF target")
    if value != [body for body in BODIES if body in value]:
        raise ContractError("solar overview body order must be canonical")
    return list(value)


def _millis(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ContractError("solar overview timestamps must be timezone aware")
    return round((value.astimezone(timezone.utc) - EPOCH).total_seconds() * 1000)


def _vector(value, name):
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ContractError(f"{name}: incomplete geometric XYZ")
    numbers = []
    for part in value:
        if isinstance(part, bool) or not isinstance(part, (int, float)):
            raise ContractError(f"{name}: geometric XYZ must be numeric")
        part = float(part)
        if not isfinite(part) or abs(part) > 10000:
            raise ContractError(f"{name}: nonfinite or unbounded geometric XYZ")
        numbers.append(part)
    if not 0 < hypot(*numbers) < 10000:
        raise ContractError(f"{name}: zero or invalid Sun-relative distance")
    return numbers


def build_solar_overview(bodies, moments, state_at):
    """Return compact XYZ series aligned *exactly* to M4's UTC sample grid.

    For 10 bodies x 181 times, repeating per-point timestamps and field names
    wastes space and can exceed the Quickshell 512 KiB collection limit.
    Therefore one times_unix_ms vector defines the index for every body.
    """
    chosen = normalize_bodies(bodies)
    if not chosen:
        raise ContractError("solar overview needs at least one target")
    if (not isinstance(moments, list)
            or not 2 <= len(moments) <= MAX_SAMPLES
            or not callable(state_at)):
        raise ContractError("solar overview requires bounded sample grid")
    stamps = [_millis(moment) for moment in moments]
    if any(stamps[i] <= stamps[i-1] for i in range(1, len(stamps))):
        raise ContractError("solar overview UTC samples must strictly increase")
    if len(stamps) != len(set(stamps)):
        raise ContractError("duplicate solar overview UTC sample")

    series = []
    for body in chosen:
        vectors = [_vector(state_at(body, at), body) for at in moments]
        series.append({"body": body, "vectors_au": vectors})

    return {
        "format": FORMAT,
        "origin": "heliocentric",
        "origin_body": "sun",
        "position_model": "geometric",
        "frame": FRAME,
        "epoch": "exact-m4-grid",
        "units": "AU",
        "source": "same-JPL-kernel-as-M4",
        "sample_count": len(stamps),
        "times_unix_ms": stamps,
        "series": series,
    }
