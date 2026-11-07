"""MAGICK M8f // Offline JPL transit timeline and refined aspect crossings.

A bounded, deliberately requested one-transit-body vs one-natal-body search.
The natal longitude and all transit samples come from the same exact JPL BSP,
observer, apparent topocentric model and true ecliptic of each event date.
It computes refined *crossings*, not predictions or a guaranteed exhaustive
search for grazing/tangential contacts inside one sampling interval.

One bounded JSON request via stdin. No downloads, cache, logs of personal
birth inputs, profile writes, or implicit clock/location choices.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import re
import sys

from celestial_contract import ContractError
from celestial_natal_chart import BODY_IDS, _number
from celestial_solver import _digest, _import_skyfield, _kernel_file, _position, _target

FORMAT = "post-apollo.weather.magick-transit-timeline.m8f.v1"
RESULT_FORMAT = "post-apollo.weather.magick-transit-timeline-result.m8f.v1"
ASPECTS = {0: "conjunction", 60: "sextile", 90: "square",
           120: "trine", 180: "opposition"}
STEPS = (30, 60)
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00Z$")
SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")
KEYS = frozenset((
    "format", "natal_epoch_utc", "start_utc", "end_utc",
    "latitude_deg", "longitude_deg", "expected_ephemeris_sha256",
    "natal_body", "transit_body", "sample_minutes", "aspects_deg",
))


def parse_utc(value):
    if not isinstance(value, str) or UTC_RE.fullmatch(value) is None:
        raise ContractError("explicit whole-minute UTC timestamp required")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("invalid UTC calendar time") from exc
    if not (1901 <= stamp.year <= 2099 and stamp.tzinfo == timezone.utc):
        raise ContractError("unsupported ephemeris calendar year")
    return stamp


def normalize(raw):
    if not isinstance(raw, dict) or set(raw) != KEYS or raw["format"] != FORMAT:
        raise ContractError("unsupported or incomplete transit request")
    natal = parse_utc(raw["natal_epoch_utc"])
    start = parse_utc(raw["start_utc"])
    end = parse_utc(raw["end_utc"])
    if end <= start or end - start > timedelta(days=31):
        raise ContractError("transit window must be greater than 0, at most 31 days")
    step = raw["sample_minutes"]
    if isinstance(step, bool) or not isinstance(step, int) or step not in STEPS:
        raise ContractError("sample minutes must be 30 or 60")
    if math.ceil((end - start).total_seconds() / (step * 60)) + 1 > 1500:
        raise ContractError("too many transit samples")
    aspects = raw["aspects_deg"]
    if (not isinstance(aspects, list) or not aspects
            or len(aspects) > len(ASPECTS)
            or any(isinstance(x, bool) or not isinstance(x, int)
                   or x not in ASPECTS for x in aspects)
            or len(set(aspects)) != len(aspects)):
        raise ContractError("named aspect angles required")
    natal_body, transit_body = raw["natal_body"], raw["transit_body"]
    if natal_body not in BODY_IDS or transit_body not in BODY_IDS:
        raise ContractError("unknown or imprecise JPL target")
    expected = raw["expected_ephemeris_sha256"]
    if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
        raise ContractError("exact natal ephemeris SHA-256 is required")
    lat = _number(raw["latitude_deg"], -90, 90, "latitude")
    lon = _number(raw["longitude_deg"], -180, 180, "longitude")
    return {
        "format": FORMAT,
        "natal_epoch_utc": raw["natal_epoch_utc"],
        "start_utc": raw["start_utc"],
        "end_utc": raw["end_utc"],
        "latitude_deg": lat, "longitude_deg": lon,
        "expected_ephemeris_sha256": expected.lower(),
        "natal_body": natal_body, "transit_body": transit_body,
        "sample_minutes": step, "aspects_deg": sorted(aspects),
    }


def signed_step(a, b):
    """Shortest signed angular step in degrees, for consecutive close samples."""
    if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in (a, b)):
        raise ContractError("nonfinite angular sample")
    return ((b - a + 180) % 360) - 180


def contact_targets(aspects):
    """All directed longitude differences whose absolute separation is aspect."""
    result = []
    for aspect in aspects:
        if aspect in (0, 180):
            result.append((float(aspect), ASPECTS[aspect]))
        else:
            result.append((float(aspect), ASPECTS[aspect]))
            result.append((-float(aspect), ASPECTS[aspect]))
    return result


def _timestamp(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _refine(sampler, origin, left, right, left_phase, left_raw,
            target, tolerance_seconds=1):
    """Bisection on an unwrapped local angular branch with <1s time bracket."""
    t0, t1 = left, right
    f0 = left_phase - target
    raw0 = left_raw
    for _ in range(35):
        if (t1 - t0).total_seconds() <= tolerance_seconds:
            break
        mid = t0 + (t1 - t0) / 2
        lon = sampler(mid)
        raw = (lon - origin) % 360
        half = left_phase + signed_step(left_raw, raw)
        fm = half - target
        if fm == 0:
            t0 = mid
            t1 = mid
            break
        if f0 * fm <= 0:
            t1 = mid
        else:
            t0 = mid
            f0 = fm
            raw0 = raw
            left_phase = half
            left_raw = raw
    guess = t0 + (t1 - t0) / 2
    residual = abs(signed_step(target % 360, (sampler(guess) - origin) % 360))
    return guess, residual


def search(sampler, natal_longitude, start, end, sample_minutes, aspects):
    """Return plot samples and refined *crossing* times from one sampled body.

    Derivatives can reverse near stations; sign-bracket search catches repeat
    crossings when separated by at least one sampling step. Tangential/grazing
    contacts without a sign crossing are NOT guaranteed to be detected.
    """
    if (not callable(sampler) or not math.isfinite(natal_longitude)
            or not 0 <= natal_longitude < 360
            or end <= start or sample_minutes not in STEPS):
        raise ContractError("invalid transit timeline")
    requested_targets = contact_targets(aspects)
    all_samples = []
    points = []
    events = []
    cursor = start
    stride = max(1, 360 // sample_minutes)
    index = 0
    last_raw = None
    last_phase = None
    while True:
        longitude = sampler(cursor)
        if (isinstance(longitude, bool) or
                not isinstance(longitude, (float, int)) or
                not math.isfinite(longitude) or
                not 0 <= longitude < 360):
            raise ContractError("ephemeris returned invalid longitude")
        raw = (longitude - natal_longitude) % 360
        phase = raw if last_phase is None else last_phase + signed_step(last_raw, raw)
        if last_raw is not None and abs(signed_step(last_raw, raw)) > 90:
            raise ContractError("angular motion too fast for bounded sampling")
        record = {"epoch_utc": _timestamp(cursor),
                  "longitude_deg": round(longitude, 8),
                  "relative_unwrapped_deg": round(phase, 8)}
        if index % stride == 0 or cursor >= end:
            points.append(record)
        if all_samples:
            previous = all_samples[-1]
            for base, aspect_name in requested_targets:
                lo = min(previous["phase"], phase)
                hi = max(previous["phase"], phase)
                for turn in range(math.floor((lo - base) / 360),
                                  math.ceil((hi - base) / 360) + 1):
                    target = base + 360 * turn
                    left_value, right_value = previous["phase"] - target, phase - target
                    if left_value * right_value > 0:
                        continue
                    if abs(left_value) < 1e-10:
                        instant = previous["instant"]
                        residual = abs(signed_step(target % 360, previous["raw"]))
                    elif abs(right_value) < 1e-10:
                        instant = cursor
                        residual = abs(signed_step(target % 360, raw))
                    else:
                        instant, residual = _refine(
                            sampler, natal_longitude, previous["instant"], cursor,
                            previous["phase"], previous["raw"], target)
                    events.append({
                        "utc": _timestamp(instant), "aspect": aspect_name,
                        "aspect_target_deg": abs(base),
                        "direction": "prograde" if phase > previous["phase"]
                        else "retrograde" if phase < previous["phase"] else "stationary",
                        "residual_deg": round(residual, 8),
                    })
        all_samples.append({"instant": cursor, "raw": raw, "phase": phase})
        if cursor >= end:
            break
        last_raw, last_phase = raw, phase
        cursor = min(end, cursor + timedelta(minutes=sample_minutes))
        index += 1
    # Adjacent intervals can both touch the same exact sample timestamp.
    events.sort(key=lambda row: (row["utc"], row["aspect"]))
    unique = []
    for row in events:
        if not any(row["utc"] == old["utc"] and row["aspect"] == old["aspect"]
                   for old in unique[-4:]):
            unique.append(row)
    return points, unique, len(all_samples)


def compute(raw, kernel_path):
    request = normalize(raw)
    path = _kernel_file(kernel_path)
    digest = _digest(path)
    if digest.lower() != request["expected_ephemeris_sha256"]:
        raise ContractError("transit BSP differs from verified natal BSP")
    version, load_file, loader, wgs84, ecliptic_frame = _import_skyfield()
    kernel = None
    try:
        kernel = load_file(str(path))
        ts = loader.timescale(builtin=True)
        origin = _target(kernel, "earth") + wgs84.latlon(
            latitude_degrees=request["latitude_deg"],
            longitude_degrees=request["longitude_deg"], elevation_m=0.0)
        natal_target = _target(kernel, request["natal_body"])
        transit_target = _target(kernel, request["transit_body"])
        def position(body, instant):
            t = ts.from_datetime(instant)
            result = _position(origin, body, t, "apparent")
            _, lon, _ = result.frame_latlon(ecliptic_frame)
            angle = float(lon.degrees) % 360
            if not math.isfinite(angle):
                raise ContractError("JPL angular value unavailable")
            return angle
        natal_epoch = parse_utc(request["natal_epoch_utc"])
        natal_angle = position(natal_target, natal_epoch)
        start = parse_utc(request["start_utc"])
        end = parse_utc(request["end_utc"])
        points, events, samples = search(
            lambda time: position(transit_target, time), natal_angle,
            start, end, request["sample_minutes"], request["aspects_deg"])
        return {
            "format": RESULT_FORMAT, "source": {
                "engine": "skyfield", "engine_version": version,
                "ephemeris_sha256": digest.lower(),
                "position_model": "topocentric-apparent",
                "coordinate_frame": "true-ecliptic-of-date",
            },
            "observer": {"latitude_deg": request["latitude_deg"],
                         "longitude_deg": request["longitude_deg"],
                         "elevation_m": 0.0},
            "natal_epoch_utc": request["natal_epoch_utc"],
            "natal_body": request["natal_body"],
            "natal_longitude_deg": round(natal_angle, 8),
            "transit_body": request["transit_body"],
            "start_utc": request["start_utc"], "end_utc": request["end_utc"],
            "sample_minutes": request["sample_minutes"],
            "sample_count": samples,
            "timeline": points,
            "contacts": events,
            "limitations": {
                "crossing_search_not_tangency_complete": True,
                "contact_time_precision_seconds": 1,
                "chart_uses_respective_equinoxes_of_date": True,
                "medical_or_spiritual_causality_claim": False,
            },
        }
    except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("JPL timeline calculation unavailable") from exc
    finally:
        if kernel is not None:
            kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private bounded JPL transit timeline")
    parser.add_argument("--kernel", required=True)
    args = parser.parse_args(argv)
    try:
        line = sys.stdin.readline(4097)
        if not line or len(line) > 4096 or not line.endswith("\n"):
            raise ContractError("one bounded newline-terminated stdin request required")
        value = compute(json.loads(line), args.kernel)
        json.dump(value, sys.stdout, separators=(",", ":"), allow_nan=False)
        print()
    except (ContractError, OSError, ImportError, json.JSONDecodeError) as exc:
        print(f"MAGICK TRANSIT ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
