"""MAGICK M8h // Bounded multi-transit JPL lines, angular crossings and stations.

Read-only, single explicit UTC request over stdin. Reuses M8f sampling/root
refinement and the M8b Skyfield/JPL position source; no new provider or saved
natal data. At most three moving bodies relative to one selected natal body.

Stations are zero crossings of a *finite-difference apparent longitude rate*,
numerically bracketed to <=60 seconds. Grazing/tangential events, physical
one-second accuracy and all-planet searches are explicitly NOT claimed.
"""
from __future__ import annotations

import argparse
from datetime import timedelta
from functools import lru_cache
import json
import math
import sys

from celestial_contract import ContractError
from celestial_natal_chart import _number
from celestial_solver import _digest, _import_skyfield, _kernel_file, _position, _target
from celestial_transit_timeline import (
    ASPECTS, BODY_IDS, SHA_RE, STEPS, _timestamp, parse_utc,
    search as search_crossings, signed_step,
)

FORMAT = "post-apollo.weather.magick-transit-multi.m8h.v1"
RESULT_FORMAT = "post-apollo.weather.magick-transit-multi-result.m8h.v1"
KEYS = frozenset((
    "format", "natal_epoch_utc", "start_utc", "end_utc",
    "latitude_deg", "longitude_deg", "expected_ephemeris_sha256",
    "natal_body", "transit_bodies", "sample_minutes",
    "aspects_deg", "include_stations",
))
MAX_BODIES = 3
MAX_EVENTS = 150
HALF_WINDOW = timedelta(minutes=10)


def normalize(raw):
    if not isinstance(raw, dict) or set(raw) != KEYS or raw["format"] != FORMAT:
        raise ContractError("incomplete multi-transit source request")
    natal = parse_utc(raw["natal_epoch_utc"])
    start, end = parse_utc(raw["start_utc"]), parse_utc(raw["end_utc"])
    if end <= start or end - start > timedelta(days=31):
        raise ContractError("search window must be positive and <=31 days")
    bodies = raw["transit_bodies"]
    if (not isinstance(bodies, list) or not 1 <= len(bodies) <= MAX_BODIES
            or any(not isinstance(x, str) or x not in BODY_IDS for x in bodies)
            or len(bodies) != len(set(bodies))):
        raise ContractError("select one to three distinct exact JPL bodies")
    if raw["natal_body"] not in BODY_IDS:
        raise ContractError("unknown natal JPL body")
    aspects = raw["aspects_deg"]
    if (not isinstance(aspects, list) or not aspects
            or len(aspects) > len(ASPECTS)
            or any(type(a) is not int or a not in ASPECTS for a in aspects)
            or len(set(aspects)) != len(aspects)):
        raise ContractError("select at least one supported aspect angle")
    minutes = raw["sample_minutes"]
    if type(minutes) is not int or minutes not in STEPS:
        raise ContractError("30 or 60 minute sample interval required")
    count = math.ceil((end - start).total_seconds() / (minutes * 60)) + 1
    if count > 1500:
        raise ContractError("sample count exceeds bounded search")
    if type(raw["include_stations"]) is not bool:
        raise ContractError("station flag must be boolean")
    source_hash = raw["expected_ephemeris_sha256"]
    if not isinstance(source_hash, str) or not SHA_RE.fullmatch(source_hash):
        raise ContractError("verified JPL ephemeris hash required")
    return {
        "format": FORMAT,
        "natal_epoch_utc": raw["natal_epoch_utc"],
        "start_utc": raw["start_utc"],
        "end_utc": raw["end_utc"],
        "latitude_deg": _number(raw["latitude_deg"], -90, 90, "latitude"),
        "longitude_deg": _number(raw["longitude_deg"], -180, 180, "longitude"),
        "expected_ephemeris_sha256": source_hash.lower(),
        "natal_body": raw["natal_body"],
        "transit_bodies": bodies[:],
        "sample_minutes": minutes,
        "aspects_deg": sorted(aspects),
        "include_stations": raw["include_stations"],
    }


def _speed(sampler, instant):
    """Finite-difference angular speed in degrees/day around one instant."""
    left = sampler(instant - HALF_WINDOW)
    right = sampler(instant + HALF_WINDOW)
    if any(type(v) not in (int, float) or not math.isfinite(v)
           or not 0 <= v < 360 for v in (left, right)):
        raise ContractError("unverified ephemeris in station estimate")
    return signed_step(left, right) * 72.0


def find_stations(sampler, start, end, minutes):
    """Bracketing-only direct/retrograde turns in one bounded UTC interval.

    This cannot find a pair of turns fully inside one sampling interval.
    The rate is a 20-minute central difference, not exact instantaneous speed.
    """
    if not callable(sampler) or end <= start or minutes not in STEPS:
        raise ContractError("invalid station search")
    current = start
    previous = _speed(sampler, current)
    found = []
    stride = timedelta(minutes=minutes)
    while current < end:
        nxt = min(end, current + stride)
        after = _speed(sampler, nxt)
        bracket = None
        if previous * after < 0:
            bracket = (current, nxt, previous, after)
        elif abs(previous) < 1e-10 and start < current < end:
            before = _speed(sampler, current - timedelta(minutes=5))
            later = _speed(sampler, current + timedelta(minutes=5))
            if before * later < 0:
                bracket = (current - timedelta(minutes=5),
                           current + timedelta(minutes=5), before, later)
        if bracket:
            left, right, vl, vr = bracket
            direction = "direct" if vl < 0 < vr else "retrograde"
            for _ in range(18):
                if (right - left).total_seconds() <= 60:
                    break
                middle = left + (right - left) / 2
                vm = _speed(sampler, middle)
                if vl * vm <= 0:
                    right = middle
                else:
                    left, vl = middle, vm
            root = left + (right - left) / 2
            if start <= root <= end and all(
                abs((root - event["instant"]).total_seconds()) > 120
                for event in found
            ):
                found.append({
                    "instant": root, "utc": _timestamp(root),
                    "type": "station", "direction": direction,
                    "longitude_deg": round(sampler(root), 8),
                    "velocity_deg_day": round(_speed(sampler, root), 8),
                    "uncertainty_seconds": 60,
                })
        current, previous = nxt, after
    return [{k: v for k, v in row.items() if k != "instant"} for row in found]


def aggregate(req, natal, source_for_body, start, end):
    """Pure aggregation from validated source-callables, useful for regression."""
    if not (isinstance(natal, (int, float)) and math.isfinite(natal)
            and 0 <= natal < 360):
        raise ContractError("invalid natal source longitude")
    series, events = [], []
    for body in req["transit_bodies"]:
        moving = source_for_body(body)
        points, contacts, count = search_crossings(
            moving, natal, start, end,
            req["sample_minutes"], req["aspects_deg"])
        if not 2 <= len(points) <= 300 or not 2 <= count <= 1500:
            raise ContractError("multi transit sample budget exceeded")
        series.append({
            "id": body, "sample_count": count,
            "timeline": points,
        })
        for event in contacts:
            events.append({
                **event, "type": "aspect", "natal_body": req["natal_body"],
                "transit_body": body,
            })
        if req["include_stations"]:
            for event in find_stations(
                moving, start, end, req["sample_minutes"]):
                events.append({
                    **event, "natal_body": req["natal_body"],
                    "transit_body": body,
                })
    if len(events) > MAX_EVENTS:
        raise ContractError("too many events in bounded search")
    events.sort(key=lambda e: (
        e["utc"], e["transit_body"], e["type"],
        e.get("aspect", "")))
    return series, events


def compute(raw, kernel_path):
    req = normalize(raw)
    path = _kernel_file(kernel_path)
    digest = _digest(path)
    if digest.lower() != req["expected_ephemeris_sha256"]:
        raise ContractError("multi transit BSP differs from the natal BSP")
    version, load_file, loader, wgs84, frame = _import_skyfield()
    kernel = None
    try:
        kernel = load_file(str(path))
        timescale = loader.timescale(builtin=True)
        origin = _target(kernel, "earth") + wgs84.latlon(
            latitude_degrees=req["latitude_deg"],
            longitude_degrees=req["longitude_deg"], elevation_m=0.0,
        )

        def source(body):
            target = _target(kernel, body)
            @lru_cache(maxsize=4096)
            def angle(instant):
                t = timescale.from_datetime(instant)
                pos = _position(origin, target, t, "apparent")
                _, longitude, _ = pos.frame_latlon(frame)
                value = float(longitude.degrees) % 360
                if not math.isfinite(value):
                    raise ContractError("JPL apparent longitude unavailable")
                return value
            return angle

        natal = source(req["natal_body"])(
            parse_utc(req["natal_epoch_utc"]))
        start, end = parse_utc(req["start_utc"]), parse_utc(req["end_utc"])
        series, events = aggregate(req, natal, source, start, end)
        return {
            "format": RESULT_FORMAT,
            "source": {
                "engine": "skyfield", "engine_version": version,
                "ephemeris_sha256": digest.lower(),
                "position_model": "topocentric-apparent",
                "coordinate_frame": "true-ecliptic-of-date",
            },
            "observer": {
                "latitude_deg": req["latitude_deg"],
                "longitude_deg": req["longitude_deg"], "elevation_m": 0.0,
            },
            "natal_epoch_utc": req["natal_epoch_utc"],
            "natal_body": req["natal_body"],
            "natal_longitude_deg": round(natal, 8),
            "start_utc": req["start_utc"], "end_utc": req["end_utc"],
            "transit_bodies": req["transit_bodies"],
            "sample_minutes": req["sample_minutes"],
            "aspects_deg": req["aspects_deg"],
            "include_stations": req["include_stations"],
            "series": series, "events": events,
            "limitations": {
                "crossing_search_not_tangency_complete": True,
                "station_search_not_all_turns_guaranteed": True,
                "station_velocity_central_difference_minutes": 20,
                "station_time_bracket_seconds": 60,
                "contact_time_precision_seconds": 1,
                "chart_uses_respective_equinoxes_of_date": True,
                "medical_or_spiritual_causality_claim": False,
            },
        }
    except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("JPL multi transit calculation unavailable") from exc
    finally:
        if kernel is not None:
            kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Private bounded multi-body JPL transit search")
    parser.add_argument("--kernel", required=True)
    args = parser.parse_args(argv)
    try:
        line = sys.stdin.readline(4097)
        if not line or len(line) > 4096 or not line.endswith("\n"):
            raise ContractError("bounded newline-terminated stdin request required")
        result = compute(json.loads(line), args.kernel)
        payload = json.dumps(result, separators=(",", ":"), allow_nan=False)
        if len(payload.encode("utf-8")) > 120000:
            raise ContractError("source result exceeds bounded output")
        sys.stdout.write(payload + "\n")
    except (ContractError, OSError, ImportError, json.JSONDecodeError) as exc:
        print(f"MAGICK MULTI TRANSIT ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
