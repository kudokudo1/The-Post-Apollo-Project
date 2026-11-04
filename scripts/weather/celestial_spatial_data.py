"""MAGICK V4c // heliocentric geometric spatial samples from a single JPL kernel.

Read-only: the M4 adapter owns the kernel, UTC grid and provenance.
This module validates measured Sun-relative XYZ vectors supplied by M1's
geometric Skyfield path; it does NOT turn apparent geocentric coordinates into
heliocentric positions. No network, kernel discovery or storage here.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from celestial_contract import ContractError, FRAME

FORMAT = "post-apollo.weather.heliocentric-spatial.v1"
MAX_BODIES = 4
MAX_SAMPLES = 721
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _number(value, name, *, allow_zero=True):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be a finite numeric measurement")
    number = float(value)
    if not math.isfinite(number) or abs(number) > 10000:
        raise ContractError(f"{name} outside bounded JPL spatial range")
    if not allow_zero and number <= 0:
        raise ContractError(f"{name} must be positive")
    return number


def _utc(moment):
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise ContractError("spatial sample requires an aware UTC instant")
    return moment.astimezone(timezone.utc)


def _time_text(moment):
    return _utc(moment).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _ms(moment):
    return round((_utc(moment) - EPOCH).total_seconds() * 1000)


def build_spatial_series(bodies, moments, state_at):
    """Use only explicitly measured geometric Sun->body XYZ in AU.

    state_at(body, UTC instant) returns (x_au,y_au,z_au) transformed to
    Skyfield's true-ecliptic-and-equinox-of-date frame at that exact instant.
    Sun is a special zero-vector because it *is* the specified origin.
    """
    if (not isinstance(bodies, list) or not 1 <= len(bodies) <= MAX_BODIES
            or len(bodies) != len(set(bodies))
            or not all(isinstance(b, str) and b for b in bodies)):
        raise ContractError("spatial bodies must be unique and bounded")
    if (not isinstance(moments, list) or not 2 <= len(moments) <= MAX_SAMPLES
            or not callable(state_at)):
        raise ContractError("spatial samples/callback invalid")
    previous = None
    times = []
    for moment in moments:
        aware = _utc(moment)
        ms = _ms(aware)
        if previous is not None and ms <= previous:
            raise ContractError("spatial UTC times must increase strictly")
        previous = ms
        times.append(aware)

    series = []
    for body in bodies:
        samples = []
        for moment in times:
            if body == "sun":
                vector = (0.0, 0.0, 0.0)
            else:
                vector = state_at(body, moment)
            if not isinstance(vector, (list, tuple)) or len(vector) != 3:
                raise ContractError(f"{body}: missing geometric XYZ vector")
            x, y, z = (_number(value, f"{body} spatial component")
                       for value in vector)
            radius = math.hypot(x, y, z)
            if body == "sun":
                if x != 0 or y != 0 or z != 0:
                    raise ContractError("Sun origin must have zero XYZ")
            elif not math.isfinite(radius) or radius <= 0:
                raise ContractError(f"{body}: invalid heliocentric distance")
            samples.append({
                "time_utc": _time_text(moment),
                "unix_ms": _ms(moment),
                "x_au": x,
                "y_au": y,
                "z_au": z,
                "distance_au": radius,
            })
        series.append({"body": body, "samples": samples})

    return {
        "format": FORMAT,
        "origin": "heliocentric",
        "origin_body": "sun",
        "position_model": "geometric",
        "frame": FRAME,
        "epoch": "per-sample-UTC",
        "units": "AU",
        "source": "same-JPL-kernel-as-M4",
        "sample_count": len(times),
        "series": series,
    }
