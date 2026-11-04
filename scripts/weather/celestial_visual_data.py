"""MAGICK M4: read-only, renderer-neutral celestial graph and timeline data.

The numerical source is the merged M1/M2/M3 JPL-backed engine. This module
does not fetch files, poll clocks, store journals, render UI or infer location.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import lru_cache
from itertools import combinations
import json
import sys

from celestial_contract import (
    ContractError, FRAME, REQUEST_FORMAT, normalize_request,
)
from celestial_dynamics import (
    _finite, _stamp, _time_grid, _utc, aspects_at, circular_difference,
    find_aspect_events, find_station_events, find_tangent_aspect_events,
    longitude_rate, longitude_separation,
)
from celestial_solver import (
    _digest, _import_skyfield, _kernel_file, _observer, _position, _target,
)
from celestial_spatial_data import build_spatial_series

FORMAT = "post-apollo.weather.celestial-visual-data.v1"
MAX_BODIES = 4
MAX_PLOT_SAMPLES = 721
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
QUERY_FIELDS = frozenset((
    "format", "start_utc", "end_utc", "bodies", "step_hours",
    "rate_window_hours", "orb_degrees", "include_events", "detect_tangents",
    "tangent_tolerance_deg", "include_heliocentric_spatial",
))


def _boolean(value, name):
    if not isinstance(value, bool):
        raise ContractError(f"{name} must be boolean")
    return value


def _timestamp_ms(value):
    return round((value - EPOCH).total_seconds() * 1000)


def normalize_visual_query(raw):
    """Validate every external knob before opening a kernel or creating series."""
    if not isinstance(raw, dict) or set(raw) - QUERY_FIELDS:
        raise ContractError("query must be an object with supported fields only")
    if raw.get("format") != FORMAT:
        raise ContractError("unsupported visual-data query format")
    bodies = raw.get("bodies")
    if not isinstance(bodies, list) or not 1 <= len(bodies) <= MAX_BODIES:
        raise ContractError("choose one to four supported bodies")
    req = normalize_request({
        "format": REQUEST_FORMAT,
        "instant_utc": raw.get("start_utc"),
        "origin": "geocentric",
        "position_model": "apparent",
        "frame": FRAME,
        "bodies": bodies,
    })
    start, end = _utc(raw["start_utc"]), _utc(raw.get("end_utc"))
    step = _finite(raw.get("step_hours", 12), "step_hours", 1, 24)
    grid = _time_grid(start, end, step)
    if len(grid) > MAX_PLOT_SAMPLES:
        raise ContractError("too many graph samples; shorten range or increase step_hours")
    rate_window = _finite(raw.get("rate_window_hours", 6),
                          "rate_window_hours", 0.5, 24)
    orb = _finite(raw.get("orb_degrees", 6), "orb_degrees", 0, 30)
    include_events = _boolean(raw.get("include_events", False), "include_events")
    include_spatial = _boolean(
        raw.get("include_heliocentric_spatial", False),
        "include_heliocentric_spatial",
    )
    detect_tangents = _boolean(raw.get("detect_tangents", False), "detect_tangents")
    tolerance = _finite(raw.get("tangent_tolerance_deg", 0.00001),
                        "tangent_tolerance_deg", 0, 0.01)
    if tolerance <= 0:
        raise ContractError("tangent_tolerance_deg must be positive")
    if include_events and len(bodies) > 2:
        raise ContractError("event search is limited to two bodies per request")
    if detect_tangents and (not include_events or len(bodies) != 2):
        raise ContractError("tangent search requires two bodies and include_events")
    return {
        "format": FORMAT,
        "start_utc": _stamp(start),
        "end_utc": _stamp(end),
        "bodies": req["bodies"],
        "origin": "geocentric",
        "position_model": "apparent",
        "frame": FRAME,
        "step_hours": step,
        "rate_window_hours": rate_window,
        "orb_degrees": orb,
        "include_events": include_events,
        "include_heliocentric_spatial": include_spatial,
        "detect_tangents": detect_tangents,
        "tangent_tolerance_deg": tolerance if detect_tangents else None,
    }


def _state(value, body):
    """Reject missing or nonphysical data instead of charting zero placeholders."""
    if not isinstance(value, dict):
        raise ContractError(f"{body}: missing state object")
    for field in ("longitude_deg", "latitude_deg", "distance_au"):
        if field not in value:
            raise ContractError(f"{body}: missing {field}")
    lon = _finite(value["longitude_deg"], "longitude_deg", 0, 360)
    lat = _finite(value["latitude_deg"], "latitude_deg", -90, 90)
    distance = _finite(value["distance_au"], "distance_au", 0)
    if lon >= 360 or distance <= 0:
        raise ContractError(f"{body}: invalid angular or distance measurement")
    return {"longitude_deg": lon, "latitude_deg": lat, "distance_au": distance}


def build_visual_model(raw_query, state_at):
    """Pure adapter: state_at(body, aware_utc_datetime) -> measured coordinates.

    Callers can unit-test with analytical trajectories; production binds
    this callback to a single loaded JPL kernel and Skyfield timescale.
    """
    query = normalize_visual_query(raw_query)
    if not callable(state_at):
        raise ContractError("state_at must be a measured-coordinate callback")
    grid = _time_grid(_utc(query["start_utc"]), _utc(query["end_utc"]),
                      query["step_hours"])
    bodies = query["bodies"]

    @lru_cache(maxsize=16384)
    def state(body, moment):
        return _state(state_at(body, moment), body)

    def longitude(body, moment):
        return state(body, moment)["longitude_deg"]

    series = []
    for body in bodies:
        samples = []
        last_lon = None
        last_unwrapped = None
        for t in grid:
            point = state(body, t)
            lon = point["longitude_deg"]
            if last_lon is None:
                unwrapped = lon
            else:
                delta = circular_difference(lon, last_lon)
                if abs(delta) >= 90:
                    raise ContractError("graph sampling aliases angular motion")
                unwrapped = last_unwrapped + delta
            velocity = longitude_rate(
                lambda when: longitude(body, when), t, query["rate_window_hours"])
            samples.append({
                "time_utc": _stamp(t),
                "unix_ms": _timestamp_ms(t),
                **point,
                "unwrapped_longitude_deg": unwrapped,
                "longitude_rate_deg_per_day": velocity,
                "motion": ("direct" if velocity > 0 else
                           "retrograde" if velocity < 0 else "indeterminate"),
            })
            last_lon, last_unwrapped = lon, unwrapped
        series.append({"body": body, "samples": samples})

    by_body = {item["body"]: item["samples"] for item in series}
    relationships = []
    for body_a, body_b in combinations(bodies, 2):
        pair_samples = []
        for left, right in zip(by_body[body_a], by_body[body_b]):
            a, b = left["longitude_deg"], right["longitude_deg"]
            pair_samples.append({
                "time_utc": left["time_utc"],
                "unix_ms": left["unix_ms"],
                "longitude_separation_deg": longitude_separation(a, b),
                "aspects": aspects_at(a, b, query["orb_degrees"]),
            })
        relationships.append({
            "bodies": [body_a, body_b],
            "samples": pair_samples,
            "angular_measure": "shortest_ecliptic_longitude_difference",
        })

    markers = []
    if query["include_events"]:
        start, end = query["start_utc"], query["end_utc"]
        for body in bodies:
            stations = find_station_events(
                lambda t, body=body: longitude(body, t),
                start, end, query["step_hours"], query["rate_window_hours"])
            for event in stations:
                markers.append({**event, "bodies": [body], "kind": "station_estimate"})
        if len(bodies) == 2:
            a, b = bodies
            crossing = find_aspect_events(
                lambda t: longitude(a, t), lambda t: longitude(b, t),
                start, end, query["step_hours"])
            for event in crossing:
                markers.append({
                    **event, "bodies": [a, b], "contact_kind": "crossing",
                })
            if query["detect_tangents"]:
                tangent = find_tangent_aspect_events(
                    lambda t: longitude(a, t), lambda t: longitude(b, t),
                    start, end, query["step_hours"],
                    query["tangent_tolerance_deg"])
                for candidate in tangent:
                    if not any(
                        marker.get("type") == "exact_longitude_aspect"
                        and marker.get("name") == candidate["name"]
                        and marker.get("orientation_deg") == candidate["orientation_deg"]
                        and abs((_utc(marker["time_utc"]) -
                                 _utc(candidate["time_utc"])).total_seconds()) < 60
                        for marker in markers
                    ):
                        markers.append({**candidate, "bodies": [a, b]})
        markers.sort(key=lambda event: (event["time_utc"], event["type"],
                                        ",".join(event["bodies"])))

    return {
        "format": FORMAT,
        "query": query,
        "sample_count": len(grid),
        "series": series,
        "relationships": relationships,
        "event_markers": markers,
        "units": {
            "longitude": "degrees", "unwrapped_longitude": "degrees",
            "latitude": "degrees", "distance": "AU",
            "angular_velocity": "degrees/day", "time": "UTC+unix_ms",
        },
        "limitations": {
            "orb_is_interpretive_tolerance": True,
            "longitude_aspects_are_not_3d_sky_angles": True,
            "sampling_proves_event_completeness": False,
            "tangent_candidates_are_exact_contacts": False,
            "station_times_are_finite_difference_estimates": True,
        },
    }


def compute_visual_data(query, kernel_path):
    """Resolve one official local kernel, time scale and source fingerprint."""
    normalized = normalize_visual_query(query)
    path = _kernel_file(kernel_path)
    version, load_file, loader, wgs84, frame = _import_skyfield()
    try:
        kernel = load_file(str(path))
    except Exception as exc:
        raise ContractError("cannot load JPL SPK kernel") from exc
    try:
        ts = loader.timescale(builtin=True)
        reference = normalize_request({
            "format": REQUEST_FORMAT,
            "instant_utc": normalized["start_utc"],
            "origin": "geocentric", "position_model": "apparent",
            "frame": FRAME, "bodies": normalized["bodies"],
        })
        observer = _observer(kernel, reference, wgs84)
        targets = {body: _target(kernel, body) for body in normalized["bodies"]}

        def measure(body, moment):
            t = ts.from_datetime(moment)
            position = _position(observer, targets[body], t, "apparent")
            lat, lon, distance = position.frame_latlon(frame)
            return {
                "longitude_deg": float(lon.degrees) % 360,
                "latitude_deg": float(lat.degrees),
                "distance_au": float(distance.au),
            }

        try:
            result = build_visual_model(query, measure)
        except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
            if isinstance(exc, ContractError):
                raise
            raise ContractError("JPL kernel coverage or numerical evaluation unavailable") from exc
        # V4c: an independent coordinate product from the SAME SPK/kernel,
        # exact UTC samples, targets and loader. Apparent geocentric M4 is
        # retained without alteration. Sun-relative vectors are instantaneous
        # geometric differences, not light-time-adjusted positions.
        if normalized["include_heliocentric_spatial"]:
            sun_origin = _target(kernel, "sun")
            moments = [
                _utc(sample["time_utc"])
                for sample in result["series"][0]["samples"]
            ]

            def heliocentric_xyz(body, moment):
                t = ts.from_datetime(moment)
                position = _position(sun_origin, targets[body], t, "geometric")
                return tuple(float(value) for value in position.frame_xyz(frame).au)

            result["heliocentric_spatial"] = build_spatial_series(
                normalized["bodies"], moments, heliocentric_xyz,
            )

        result["provenance"] = {
            "engine": "skyfield", "engine_version": version,
            "ephemeris_id": path.name, "ephemeris_sha256": _digest(path),
            "time_data_id": f"skyfield-{version}-builtin-timescale",
            "generated_at_utc": _stamp(datetime.now(timezone.utc)),
        }
        return result
    finally:
        kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="MAGICK M4 chart data backend")
    parser.add_argument("--kernel", required=True, help="Explicit local .bsp kernel")
    sources = parser.add_mutually_exclusive_group()
    sources.add_argument("--query", default=None,
                         help="JSON query file or '-' for stdin")
    sources.add_argument("--query-json", default=None,
                         help="Bounded JSON query as one argv value (no shell)")
    args = parser.parse_args(argv)
    try:
        if args.query_json is not None:
            if len(args.query_json) > 4096:
                raise ContractError("query-json exceeds 4096 characters")
            query = json.loads(args.query_json)
        elif args.query is None or args.query == "-":
            query = json.load(sys.stdin)
        else:
            with open(args.query, encoding="utf-8") as source:
                query = json.load(source)
        result = compute_visual_data(query, args.kernel)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"MAGICK VISUAL DATA ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, separators=(",", ":"), allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
