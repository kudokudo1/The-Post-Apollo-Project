"""MAGICK M6-A: read-only, renderer-neutral catalogue of actual M4 sky data.

This module only *classifies* source-backed M4 samples and event markers. It
never discovers a new event, downloads an ephemeris, asserts magical effects,
or changes the existing two-body event-search limit. No storage or user data.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from itertools import combinations
import json
import math
import sys

from celestial_contract import ContractError, FRAME
from celestial_dynamics import ASPECTS, _finite, _stamp, _utc, aspects_at, longitude_separation
from celestial_visual_data import (
    FORMAT as M4_FORMAT, MAX_PLOT_SAMPLES, _state, _time_grid,
    _timestamp_ms, normalize_visual_query,
)

FORMAT = "post-apollo.weather.magick-event-catalogue.v1"
MAX_EVENTS = 2048
MAX_INPUT_BYTES = 4 * 1024 * 1024
PROVENANCE_FIELDS = ("engine", "engine_version", "ephemeris_id",
                     "ephemeris_sha256", "time_data_id", "generated_at_utc")
QUERY_FIELDS = ("format", "start_utc", "end_utc", "bodies", "step_hours",
                "rate_window_hours", "orb_degrees", "include_events",
                "detect_tangents", "tangent_tolerance_deg")
STATION_NAMES = frozenset(("direct_to_retrograde", "retrograde_to_direct"))
ASPECT_TARGETS = {(float(angle), name): float(separation)
                  for angle, name, separation in ASPECTS}


def _required_dict(raw, label):
    if not isinstance(raw, dict):
        raise ContractError(f"{label} must be an object")
    return raw


def _utc_time(raw, label):
    if not isinstance(raw, str):
        raise ContractError(f"{label} must be exact UTC")
    return _utc(raw)


def _key(*parts):
    """Stable for the same source/time/geometry; never a personal identity."""
    return sha256(json.dumps(parts, ensure_ascii=True, separators=(",", ":"),
                             sort_keys=True).encode("ascii")).hexdigest()[:24]


def _source_and_query(raw):
    if raw.get("format") != M4_FORMAT:
        raise ContractError("M6-A requires the existing M4 visual-data format")
    query = _required_dict(raw.get("query"), "source query")
    if set(query) != set(QUERY_FIELDS) | {
        "origin", "position_model", "frame"
    }:
        raise ContractError("unexpected or missing M4 query fields")
    reduced = {name: query[name] for name in QUERY_FIELDS
               if query[name] is not None}
    normal = normalize_visual_query(reduced)
    if query != normal:
        raise ContractError("M4 query is not canonical")
    if query["origin"] != "geocentric" or (
        query["position_model"] != "apparent"
    ) or query["frame"] != FRAME:
        raise ContractError("M4 coordinate frame is unsupported")
    source = _required_dict(raw.get("provenance"), "source provenance")
    for field in PROVENANCE_FIELDS:
        if not isinstance(source.get(field), str) or not source[field]:
            raise ContractError(f"missing source {field}")
    if source["engine"] != "skyfield" or not source["ephemeris_id"].endswith(".bsp"):
        raise ContractError("source must identify the JPL/Skyfield calculation")
    if len(source["ephemeris_sha256"]) != 64 or any(
        c not in "0123456789abcdefABCDEF" for c in source["ephemeris_sha256"]
    ):
        raise ContractError("source kernel SHA-256 invalid")
    _utc_time(source["generated_at_utc"], "generated_at_utc")
    return query, source


def _samples(raw, query):
    rows = raw.get("series")
    count = raw.get("sample_count")
    if not isinstance(count, int) or isinstance(count, bool) or (
        not 2 <= count <= MAX_PLOT_SAMPLES
    ):
        raise ContractError("sample count invalid")
    if not isinstance(rows, list) or len(rows) != len(query["bodies"]):
        raise ContractError("source series incomplete")
    grid = _time_grid(_utc(query["start_utc"]),
                      _utc(query["end_utc"]), query["step_hours"])
    if len(grid) != count:
        raise ContractError("sample count does not match M4 time grid")
    expected = [_stamp(t) for t in grid]
    times_ms = [_timestamp_ms(t) for t in grid]
    by_body = {}
    for entry in rows:
        if not isinstance(entry, dict) or entry.get("body") not in query["bodies"]:
            raise ContractError("unexpected source body")
        body = entry["body"]
        if body in by_body:
            raise ContractError("duplicate source body")
        samples = entry.get("samples")
        if not isinstance(samples, list) or len(samples) != count:
            raise ContractError("missing body sample rows")
        for i, sample in enumerate(samples):
            sample = _required_dict(sample, "body sample")
            if sample.get("time_utc") != expected[i] or (
                type(sample.get("unix_ms")) is not int or
                sample["unix_ms"] != times_ms[i]
            ):
                raise ContractError("body sample time mismatch")
            _state(sample, body)
            rate = _finite(sample.get("longitude_rate_deg_per_day"), "longitude rate")
            motion = "direct" if rate > 0 else "retrograde" if rate < 0 else "indeterminate"
            if sample.get("motion") != motion:
                raise ContractError("motion does not match source rate")
        by_body[body] = samples
    if set(by_body) != set(query["bodies"]):
        raise ContractError("source bodies incomplete")
    return by_body, expected, times_ms


def _relationships(raw, query, by_body, expected, times_ms):
    relationships = raw.get("relationships")
    expected_pairs = {tuple(pair) for pair in combinations(query["bodies"], 2)}
    if not isinstance(relationships, list) or len(relationships) != len(expected_pairs):
        raise ContractError("pair relationships incomplete")
    got = set()
    current = []
    for item in relationships:
        item = _required_dict(item, "relationship")
        pair = item.get("bodies")
        if not isinstance(pair, list) or len(pair) != 2:
            raise ContractError("invalid relationship bodies")
        if any(not isinstance(body, str) for body in pair):
            raise ContractError("relationship body IDs must be strings")
        pair = tuple(sorted(pair))
        if pair not in expected_pairs or pair in got:
            raise ContractError("duplicate or unsupported pair")
        got.add(pair)
        rows = item.get("samples")
        if not isinstance(rows, list) or len(rows) != len(expected):
            raise ContractError("relationship samples incomplete")
        for i, point in enumerate(rows):
            point = _required_dict(point, "relationship sample")
            if point.get("time_utc") != expected[i] or (
                type(point.get("unix_ms")) is not int or
                point["unix_ms"] != times_ms[i]
            ):
                raise ContractError("relationship sample time mismatch")
            measured = longitude_separation(
                by_body[pair[0]][i]["longitude_deg"],
                by_body[pair[1]][i]["longitude_deg"],
            )
            given = _finite(point.get("longitude_separation_deg"),
                            "longitude separation", 0, 180)
            if not math.isclose(measured, given, abs_tol=1e-7):
                raise ContractError("relationship separation contradicts source positions")
            aspects = point.get("aspects")
            expected_aspects = aspects_at(
                by_body[pair[0]][i]["longitude_deg"],
                by_body[pair[1]][i]["longitude_deg"], query["orb_degrees"]
            )
            if aspects != expected_aspects:
                raise ContractError("relationship aspects contradict M4 positions")
        last = rows[-1]
        for aspect in last["aspects"]:
            current.append({
                "body_ids": list(pair),
                "sample_time_utc": expected[-1],
                "name": aspect["name"],
                "target_angle_deg": aspect["angle_deg"],
                "separation_deg": aspect["separation_deg"],
                "signed_orb_deg": aspect["signed_orb_deg"],
                "classification": "sampled_within_orb_not_exact_event",
            })
    if got != expected_pairs:
        raise ContractError("missing expected relationship")
    return sorted(current, key=lambda item: (item["body_ids"], item["target_angle_deg"]))


def _event(marker, query, source, ordinal):
    marker = _required_dict(marker, "event marker")
    when = _utc_time(marker.get("time_utc"), "event time")
    if when < _utc(query["start_utc"]) or when > _utc(query["end_utc"]):
        raise ContractError("event outside calculated time window")
    stamp = _stamp(when)
    bodies = marker.get("bodies")
    if not isinstance(bodies, list) or not bodies or any(
        not isinstance(body, str) for body in bodies
    ):
        raise ContractError("event has invalid body IDs")
    if len(set(bodies)) != len(bodies):
        raise ContractError("event body IDs repeated")
    if any(body not in query["bodies"] for body in bodies):
        raise ContractError("event references unrequested body")
    kind = marker.get("type")
    name = marker.get("name")
    if not isinstance(name, str):
        raise ContractError("unnamed source event")

    if kind == "exact_longitude_aspect":
        if len(bodies) != 2:
            raise ContractError("aspect event requires two requested bodies")
        orientation = _finite(marker.get("orientation_deg"), "aspect orientation", 0, 300)
        angle = _finite(marker.get("angle_deg"), "aspect angle", 0, 180)
        if (orientation, name) not in ASPECT_TARGETS or (
            angle != ASPECT_TARGETS[(orientation, name)]
        ):
            raise ContractError("unsupported aspect geometry")
        separation = _finite(marker.get("separation_deg"), "aspect separation", 0, 180)
        if not math.isclose(separation, angle, abs_tol=0.02):
            raise ContractError("aspect crossing not close to source angle")
        contact = marker.get("contact_kind", "crossing")
        if contact not in ("crossing", "tangent_candidate"):
            raise ContractError("unsupported aspect contact kind")
        if contact == "tangent_candidate" and not query["detect_tangents"]:
            raise ContractError("tangent candidate was not requested")
        evidence = ("computed_crossing" if contact == "crossing"
                    else "bounded_grazing_candidate")
        result = {
            "category": "aspect",
            "name": name,
            "classification": evidence,
            "body_ids": sorted(bodies),
            "time_utc": stamp,
            "target_angle_deg": angle,
            "orientation_deg": orientation,
            "source_separation_deg": separation,
        }
        if contact == "tangent_candidate":
            residual = _finite(marker.get("residual_deg"),
                               "candidate residual", 0)
            tolerance = _finite(marker.get("angular_tolerance_deg"),
                                "candidate tolerance", 0, 0.01)
            if tolerance <= 0 or residual > tolerance or not math.isclose(
                tolerance, query["tangent_tolerance_deg"], abs_tol=1e-12
            ):
                raise ContractError("candidate exceeds or contradicts angular tolerance")
            result["candidate_residual_deg"] = residual
            result["candidate_tolerance_deg"] = tolerance
    elif kind == "apparent_longitude_station":
        if len(bodies) != 1 or name not in STATION_NAMES:
            raise ContractError("station marker invalid")
        if marker.get("kind") != "station_estimate" or (
            marker.get("rate_method") != "centered_finite_difference"
        ):
            raise ContractError("station method unspecified")
        result = {
            "category": "motion_station",
            "name": name,
            "classification": "finite_difference_estimate",
            "body_ids": bodies,
            "time_utc": stamp,
            "source_longitude_deg": _finite(
                marker.get("longitude_deg"), "station longitude", 0, 360
            ),
            "rate_window_hours": _finite(
                marker.get("rate_window_hours"), "rate window hours", 0.5, 24
            ),
        }
        if result["source_longitude_deg"] >= 360:
            raise ContractError("station longitude must be below 360")
        if result["rate_window_hours"] != query["rate_window_hours"]:
            raise ContractError("station rate window contradicts source query")
    else:
        raise ContractError("M6-A cannot classify unsupported M4 event marker")

    result["event_id"] = "m6a_" + _key(
        source["ephemeris_sha256"].lower(), result["category"],
        result["name"], result["classification"], result["body_ids"],
        result["time_utc"], result.get("orientation_deg")
    )
    result["source_marker_ordinal"] = ordinal
    return result


def _runs(by_body):
    """Sample runs: endpoints are samples, NOT exact station transition times."""
    output = []
    for body in sorted(by_body):
        rows = by_body[body]
        first = 0
        for i in range(1, len(rows) + 1):
            if i == len(rows) or rows[i]["motion"] != rows[first]["motion"]:
                output.append({
                    "body_id": body,
                    "motion": rows[first]["motion"],
                    "first_sample_utc": rows[first]["time_utc"],
                    "last_sample_utc": rows[i - 1]["time_utc"],
                    "sample_count": i - first,
                    "boundary_precision": "samples_only_not_exact_station",
                })
                first = i
    return output


def build_catalogue(raw):
    """Pure M4 -> M6-A transformation; rejects source loss or ambiguous claims."""
    raw = _required_dict(raw, "M4 source")
    query, source = _source_and_query(raw)
    by_body, times, times_ms = _samples(raw, query)
    states = _relationships(raw, query, by_body, times, times_ms)
    markers = raw.get("event_markers")
    if not isinstance(markers, list) or len(markers) > MAX_EVENTS:
        raise ContractError("event marker count invalid")
    if not query["include_events"] and markers:
        raise ContractError("event search was not requested")
    events = [_event(marker, query, source, i) for i, marker in enumerate(markers)]
    events.sort(key=lambda e: (e["time_utc"], e["event_id"]))
    if len({e["event_id"] for e in events}) != len(events):
        raise ContractError("duplicated source event identity")
    return {
        "format": FORMAT,
        "source_format": M4_FORMAT,
        "source": {
            "engine": source["engine"],
            "engine_version": source["engine_version"],
            "ephemeris_id": source["ephemeris_id"],
            "ephemeris_sha256": source["ephemeris_sha256"],
            "time_data_id": source["time_data_id"],
            "frame": query["frame"],
            "origin": query["origin"],
            "position_model": query["position_model"],
        },
        "window": {
            "start_utc": query["start_utc"],
            "end_utc": query["end_utc"],
            "bodies": query["bodies"],
            "sample_count": len(times),
            "last_sample_utc": times[-1],
            "step_hours": query["step_hours"],
        },
        "search": {
            "requested": query["include_events"],
            "status": "bounded_non_exhaustive" if query["include_events"] else "not_requested",
            "max_search_bodies": 2,
            "tangent_candidates_requested": query["detect_tangents"],
            "no_events_is_not_proof_of_absence": True,
        },
        "events": events,
        "latest_sampled_aspect_states": states,
        "sampled_motion_runs": _runs(by_body),
        "limitations": {
            "ecliptic_longitude_difference_is_not_3d_separation": True,
            "major_aspect_orbs_are_interpretive": True,
            "station_times_are_finite_difference_estimates": True,
            "grazing_candidates_are_not_confirmed_exact_contacts": True,
            "sampled_runs_do_not_have_exact_transition_boundaries": True,
            "search_is_not_complete_for_all_possible_contacts": True,
            "not_an_astrological_interpretation": True,
        },
    }


def main():
    """Read one bounded existing M4 JSON from stdin, print catalogue to stdout."""
    text = sys.stdin.read(MAX_INPUT_BYTES + 1)
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        print("MAGICK M6-A ERROR: M4 input too large", file=sys.stderr)
        return 2
    try:
        result = build_catalogue(json.loads(text))
    except (ContractError, ValueError, TypeError, KeyError,
            OverflowError, json.JSONDecodeError) as exc:
        print(f"MAGICK M6-A ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
