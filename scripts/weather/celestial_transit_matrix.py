"""MAGICK M8k/M8l // Bounded multi-natal-body x transit-body JPL event matrix.

One explicit request over stdin; no saved natal records, downloads,
background searches, or observer inference. Reuses M8f angular crossings and
M8i station detection against one exact BSP and one natal observer.

Stations belong to the *moving body*, not to each natal reference. They are
returned once; aspect contacts explicitly name both natal and transit bodies.
Numerical brackets do not constitute astronomical or predictive accuracy.
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
    search as search_crossings,
)
from celestial_transit_multi import (
    find_stations, MAX_STATION_RATE_SAMPLES, STATION_RATE_STEP,
)

FORMAT = "post-apollo.weather.magick-natal-transit-matrix.m8k.v1"
RESULT_FORMAT = "post-apollo.weather.magick-natal-transit-matrix-result.m8k.v1"
MAX_NATAL = 4
MAX_MOVING = 4
MAX_PAIR_SAMPLES = 2200
MAX_TOTAL_STATION_GRID = 3000
MAX_EVENTS = 150
MAX_OUTPUT_BYTES = 120000
KEYS = frozenset((
    "format", "natal_epoch_utc", "start_utc", "end_utc",
    "latitude_deg", "longitude_deg", "expected_ephemeris_sha256",
    "natal_bodies", "transit_bodies", "sample_minutes",
    "aspects_deg", "include_stations",
))


def normalize(raw):
    if not isinstance(raw, dict) or set(raw) != KEYS or raw["format"] != FORMAT:
        raise ContractError("unsupported or incomplete matrix request")
    birth = parse_utc(raw["natal_epoch_utc"])
    start = parse_utc(raw["start_utc"])
    end = parse_utc(raw["end_utc"])
    if end <= start or end - start > timedelta(days=31):
        raise ContractError("matrix window must be positive, at most 31 days")
    natal = raw["natal_bodies"]
    moving = raw["transit_bodies"]
    for values, limit, label in (
        (natal, MAX_NATAL, "natal"),
        (moving, MAX_MOVING, "transit"),
    ):
        if (not isinstance(values, list) or not 1 <= len(values) <= limit
                or any(type(x) is not str or x not in BODY_IDS for x in values)
                or len(set(values)) != len(values)):
            raise ContractError("invalid exact JPL " + label + " selection")
    step = raw["sample_minutes"]
    if type(step) is not int or step not in STEPS:
        raise ContractError("30/60-minute source cadence required")
    count = math.ceil((end - start).total_seconds() / (step * 60)) + 1
    if count * len(natal) * len(moving) > MAX_PAIR_SAMPLES:
        raise ContractError("matrix pair-sample budget exceeded")
    aspect_list = raw["aspects_deg"]
    if (not isinstance(aspect_list, list) or not 1 <= len(aspect_list) <= 5
            or any(type(x) is not int or x not in ASPECTS for x in aspect_list)
            or len(set(aspect_list)) != len(aspect_list)):
        raise ContractError("invalid aspect selections")
    if type(raw["include_stations"]) is not bool:
        raise ContractError("station flag must be boolean")
    rate_samples = (
        math.ceil((end - start).total_seconds() /
                  STATION_RATE_STEP.total_seconds()) + 1
    )
    if raw["include_stations"] and (
        rate_samples > MAX_STATION_RATE_SAMPLES
        or rate_samples * len(moving) > MAX_TOTAL_STATION_GRID
    ):
        raise ContractError("station rate search budget exceeded")
    digest = raw["expected_ephemeris_sha256"]
    if type(digest) is not str or SHA_RE.fullmatch(digest) is None:
        raise ContractError("exact verified natal kernel hash required")
    return {
        "format": FORMAT,
        "natal_epoch_utc": raw["natal_epoch_utc"],
        "start_utc": raw["start_utc"], "end_utc": raw["end_utc"],
        "latitude_deg": _number(raw["latitude_deg"], -90, 90, "latitude"),
        "longitude_deg": _number(raw["longitude_deg"], -180, 180, "longitude"),
        "expected_ephemeris_sha256": digest.lower(),
        "natal_bodies": natal[:], "transit_bodies": moving[:],
        "sample_minutes": step,
        "aspects_deg": sorted(aspect_list),
        "include_stations": raw["include_stations"],
    }


def aggregate(req, natal_longitudes, moving_for_body, start, end):
    """Pure numerical aggregation; works with source-backed or test samplers.

    Plot a moving body only once. Contacts are per natal/moving pair.
    Station events belong once to the moving body and have natal_body=None.
    """
    if set(natal_longitudes) != set(req["natal_bodies"]) or any(
        type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v < 360
        for v in natal_longitudes.values()
    ):
        raise ContractError("incomplete source-derived natal longitudes")
    tracks, cells, events = [], [], []
    sample_count = math.ceil(
        (end - start).total_seconds() / (req["sample_minutes"] * 60)) + 1
    for moving_body in req["transit_bodies"]:
        moving = moving_for_body(moving_body)
        track = None
        for natal_body in req["natal_bodies"]:
            points, contacts, count = search_crossings(
                moving, natal_longitudes[natal_body], start, end,
                req["sample_minutes"], req["aspects_deg"])
            if count != sample_count or not 2 <= len(points) <= 300:
                raise ContractError("matrix track budget or completeness failure")
            if track is None:
                track = [{
                    "epoch_utc": row["epoch_utc"],
                    "longitude_deg": row["longitude_deg"]
                } for row in points]
            cells.append({
                "natal_body": natal_body, "transit_body": moving_body,
                "aspect_count": len(contacts),
            })
            for row in contacts:
                events.append({
                    **row, "type": "aspect",
                    "natal_body": natal_body,
                    "transit_body": moving_body,
                })
        tracks.append({
            "id": moving_body, "sample_count": sample_count,
            "timeline": track,
        })
        if req["include_stations"]:
            for event in find_stations(
                moving, start, end, req["sample_minutes"]):
                events.append({
                    **event, "natal_body": None,
                    "transit_body": moving_body,
                })
    if len(events) > MAX_EVENTS:
        raise ContractError("too many source events for bounded matrix")
    events.sort(key=lambda e: (
        e["utc"], e["transit_body"], e["type"],
        e["natal_body"] or "", e.get("aspect", "")))
    return tracks, cells, events, sample_count


def compute(raw, kernel_path):
    req = normalize(raw)
    bsp = _kernel_file(kernel_path)
    digest = _digest(bsp)
    if digest.lower() != req["expected_ephemeris_sha256"]:
        raise ContractError("matrix BSP does not match natal source")
    version, load_file, loader, wgs84, frame = _import_skyfield()
    kernel = None
    try:
        kernel = load_file(str(bsp))
        timescale = loader.timescale(builtin=True)
        observer = _target(kernel, "earth") + wgs84.latlon(
            latitude_degrees=req["latitude_deg"],
            longitude_degrees=req["longitude_deg"],
            elevation_m=0.0,
        )
        sources = {}
        def source(body):
            if body in sources:
                return sources[body]
            target = _target(kernel, body)
            @lru_cache(maxsize=4096)
            def longitude(instant):
                t = timescale.from_datetime(instant)
                p = _position(observer, target, t, "apparent")
                _, lon, _ = p.frame_latlon(frame)
                angle = float(lon.degrees) % 360
                if not math.isfinite(angle):
                    raise ContractError("JPL apparent longitude unavailable")
                return angle
            sources[body] = longitude
            return longitude

        birth = parse_utc(req["natal_epoch_utc"])
        natal = {body: source(body)(birth)
                 for body in req["natal_bodies"]}
        start = parse_utc(req["start_utc"])
        end = parse_utc(req["end_utc"])
        tracks, cells, events, sample_count = aggregate(
            req, natal, source, start, end)
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
            "natal_bodies": req["natal_bodies"],
            "natal_longitudes": [
                {"id": body, "longitude_deg": round(natal[body], 8)}
                for body in req["natal_bodies"]
            ],
            "transit_bodies": req["transit_bodies"],
            "start_utc": req["start_utc"],
            "end_utc": req["end_utc"],
            "sample_minutes": req["sample_minutes"],
            "sample_count": sample_count,
            "aspects_deg": req["aspects_deg"],
            "include_stations": req["include_stations"],
            "series": tracks, "matrix": cells, "events": events,
            "limitations": {
                "crossing_search_not_tangency_complete": True,
                "station_search_not_all_turns_guaranteed": True,
                "station_rate_scan_interval_minutes_max": 15,
                "station_velocity_central_difference_minutes": 20,
                "station_time_bracket_seconds": 60,
                "contact_time_precision_seconds": 1,
                "stations_not_natal_pairs": True,
                "chart_uses_respective_equinoxes_of_date": True,
                "medical_or_spiritual_causality_claim": False,
            },
        }
    finally:
        if kernel is not None:
            kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Private multi-natal/transit JPL event matrix")
    parser.add_argument("--kernel", required=True)
    args = parser.parse_args(argv)
    try:
        line = sys.stdin.readline(4097)
        if not line or len(line) > 4096 or not line.endswith("\n"):
            raise ContractError("bounded single-line stdin request required")
        result = compute(json.loads(line), args.kernel)
        payload = json.dumps(result, separators=(",", ":"), allow_nan=False)
        if len(payload.encode("utf-8")) > MAX_OUTPUT_BYTES:
            raise ContractError("bounded event matrix output exceeded")
        sys.stdout.write(payload + "\n")
    except (ContractError, OSError, ImportError, json.JSONDecodeError) as exc:
        print(f"MAGICK MATRIX ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
