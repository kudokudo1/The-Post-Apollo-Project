"""MAGICK M2: astronomical longitude aspects, retrograde motion, and stations.

This is numerical geometry over a caller-supplied M1 JPL kernel, NOT an
astrological interpretation or a claim about cause/meaning. No QML, network,
location inference, user records, or persistent background service.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import sys

from celestial_contract import (
    BODIES, ContractError, FRAME, REQUEST_FORMAT, normalize_request, utc_instant,
)
from celestial_solver import (
    _digest, _import_skyfield, _kernel_file, _observer, _position, _target,
)

FORMAT = "post-apollo.weather.celestial-events.v1"
ASPECTS = (
    (0.0, "conjunction", 0.0),
    (60.0, "sextile", 60.0),
    (90.0, "square", 90.0),
    (120.0, "trine", 120.0),
    (180.0, "opposition", 180.0),
    (240.0, "trine", 120.0),
    (270.0, "square", 90.0),
    (300.0, "sextile", 60.0),
)
MAX_DAYS = 366
MAX_SAMPLES = 4096
ROOT_TOLERANCE_SECONDS = 1.0


def _finite(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ContractError(f"{name} must be finite numeric")
    x = float(value)
    if not math.isfinite(x) or (low is not None and x < low) or (
        high is not None and x > high
    ):
        raise ContractError(f"{name} is invalid")
    return x


def _utc(value):
    return datetime.fromisoformat(utc_instant(value).replace("Z", "+00:00"))


def _stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _longitude(value):
    return _finite(value, "longitude_deg", 0.0, 360.0) % 360.0


def circular_difference(a, b):
    """Shortest signed delta a-b, in [-180,180)."""
    return ((_longitude(a) - _longitude(b) + 180) % 360) - 180


def longitude_separation(a, b):
    """Smallest separation of longitudes, not actual 3-D sky separation."""
    return abs(circular_difference(a, b))


def aspects_at(a, b, orb_degrees=6.0):
    """Interpretive aspect names matched to measured ecliptic longitudes."""
    orb = _finite(orb_degrees, "orb_degrees", 0, 30)
    separation = longitude_separation(a, b)
    results = []
    for angle, name in ((0, "conjunction"), (60, "sextile"), (90, "square"),
                        (120, "trine"), (180, "opposition")):
        error = separation - angle
        if abs(error) <= orb:
            results.append({"name": name, "angle_deg": angle,
                            "separation_deg": separation,
                            "signed_orb_deg": error})
    return results


def _phase(a, b):
    return (_longitude(a) - _longitude(b)) % 360.0


def _near_unwrapped(raw_phase, reference):
    return raw_phase + 360.0 * round((reference - raw_phase) / 360.0)


def _time_grid(start, end, step_hours):
    if start.tzinfo != timezone.utc or end.tzinfo != timezone.utc:
        raise ContractError("search grid must use UTC")
    span = (end - start).total_seconds()
    if span <= 0 or span > MAX_DAYS * 86400:
        raise ContractError("search must be positive and at most 366 days")
    step = _finite(step_hours, "step_hours", 1, 24) * 3600
    pieces = math.ceil(span / step)
    if pieces + 1 > MAX_SAMPLES:
        raise ContractError("too many samples; use a smaller time range")
    return [start + timedelta(seconds=min(i * step, span))
            for i in range(pieces + 1)]


def _bisect_zero(fn, lo, hi, y_lo, y_hi, tolerance_seconds=ROOT_TOLERANCE_SECONDS):
    if abs(y_lo) <= 1e-12:
        return lo
    if abs(y_hi) <= 1e-12:
        return hi
    if y_lo * y_hi > 0:
        raise ContractError("root is not bracketed")
    for _ in range(80):
        mid = lo + (hi - lo) / 2
        if (hi - lo).total_seconds() <= tolerance_seconds:
            return mid
        y_mid = _finite(fn(mid), "root function")
        if abs(y_mid) <= 1e-12:
            return mid
        if y_lo * y_mid <= 0:
            hi, y_hi = mid, y_mid
        else:
            lo, y_lo = mid, y_mid
    raise ContractError("root refinement did not converge")


def _deduplicate(events):
    output = []
    for event in sorted(events, key=lambda e: (e["time_utc"], e["type"], e.get("name", ""))):
        if output and event["type"] == output[-1]["type"] and (
            event.get("name") == output[-1].get("name")
        ) and abs((_utc(event["time_utc"]) - _utc(output[-1]["time_utc"])).total_seconds()) <= 2:
            continue
        output.append(event)
    return output


def find_aspect_events(lon_a_at, lon_b_at, start_utc, end_utc, step_hours=12):
    """Find crossed exact aspect angles. Fine sampling avoids missed reversals.

    A tangential contact without a sign change can be missed: this scan is
    bracket-based, not a proof of exhaustive all-contact detection.
    """
    grid = _time_grid(_utc(start_utc), _utc(end_utc), step_hours)
    phases = [_phase(lon_a_at(t), lon_b_at(t)) for t in grid]
    unwrapped = [phases[0]]
    for prev, cur in zip(phases, phases[1:]):
        delta = ((cur - prev + 180) % 360) - 180
        if abs(delta) >= 90:
            raise ContractError("large relative motion per interval: reduce step_hours")
        unwrapped.append(unwrapped[-1] + delta)
    events = []
    for i in range(len(grid) - 1):
        lo, hi = unwrapped[i], unwrapped[i + 1]
        bottom, top = min(lo, hi), max(lo, hi)
        for phase, name, angle in ASPECTS:
            k_min = math.ceil((bottom - phase - 1e-10) / 360)
            k_max = math.floor((top - phase + 1e-10) / 360)
            for k in range(k_min, k_max + 1):
                target = phase + 360 * k
                def residual(t, target=target, lo=lo, hi=hi):
                    reference = lo + (hi - lo) * (
                        (t - grid[i]).total_seconds()
                        / (grid[i + 1] - grid[i]).total_seconds()
                    )
                    return _near_unwrapped(_phase(lon_a_at(t), lon_b_at(t)), reference) - target
                t = _bisect_zero(residual, grid[i], grid[i + 1],
                                 lo - target, hi - target)
                events.append({
                    "type": "exact_longitude_aspect",
                    "name": name, "angle_deg": angle,
                    "orientation_deg": phase,
                    "time_utc": _stamp(t),
                    "separation_deg": longitude_separation(lon_a_at(t), lon_b_at(t)),
                })
    return _deduplicate(events)


def longitude_rate(lon_at, at, window_hours=6):
    """Central finite-difference apparent longitude velocity (degrees/day)."""
    half_window = timedelta(hours=_finite(window_hours, "window_hours", 0.5, 24))
    change = circular_difference(lon_at(at + half_window), lon_at(at - half_window))
    if abs(change) >= 90:
        raise ContractError("angular motion aliases across rate window")
    return change / (2 * half_window.total_seconds() / 86400)


def find_station_events(lon_at, start_utc, end_utc, step_hours=12, rate_window_hours=6):
    """Find direct/retrograde station crossings; time is finite-difference estimate."""
    grid = _time_grid(_utc(start_utc), _utc(end_utc), step_hours)
    velocities = [longitude_rate(lon_at, t, rate_window_hours) for t in grid]
    events = []
    for i in range(len(grid) - 1):
        v0, v1 = velocities[i:i + 2]
        if v0 * v1 > 0:
            continue
        if abs(v0) <= 1e-12 and abs(v1) <= 1e-12:
            continue
        t = _bisect_zero(lambda at: longitude_rate(lon_at, at, rate_window_hours),
                         grid[i], grid[i + 1], v0, v1)
        sample_before = longitude_rate(lon_at, t - timedelta(hours=2), rate_window_hours)
        sample_after = longitude_rate(lon_at, t + timedelta(hours=2), rate_window_hours)
        if sample_before == sample_after or sample_before * sample_after >= 0:
            continue
        events.append({
            "type": "apparent_longitude_station",
            "name": "direct_to_retrograde" if sample_before > 0 else "retrograde_to_direct",
            "time_utc": _stamp(t),
            "longitude_deg": _longitude(lon_at(t)),
            "rate_method": "centered_finite_difference",
            "rate_window_hours": float(rate_window_hours),
        })
    return _deduplicate(events)


def event_report(query, kernel_path):
    """Use one SPK load and one time scale for the entire bounded sweep."""
    if not isinstance(query, dict):
        raise ContractError("query must be an object")
    if query.get("format") != FORMAT:
        raise ContractError("unsupported event query version")
    mode = query.get("mode")
    if mode not in ("aspects", "stations"):
        raise ContractError("mode must be aspects or stations")
    bodies = query.get("bodies")
    if not isinstance(bodies, list) or len(bodies) != (2 if mode == "aspects" else 1):
        raise ContractError("mode requires exactly two bodies for aspects or one for stations")
    req = normalize_request({
        "format": REQUEST_FORMAT,
        "instant_utc": query.get("start_utc"),
        "origin": "geocentric",
        "position_model": "apparent",
        "frame": FRAME,
        "bodies": bodies,
    })
    start, end = _utc(query.get("start_utc")), _utc(query.get("end_utc"))
    step = _finite(query.get("step_hours", 12), "step_hours", 1, 24)
    grid = _time_grid(start, end, step)
    rate_window = _finite(query.get("rate_window_hours", 6),
                          "rate_window_hours", 0.5, 24)
    path = _kernel_file(kernel_path)
    version, load_file, loader, wgs84, ecliptic_frame = _import_skyfield()
    try:
        kernel = load_file(str(path))
    except Exception as exc:
        raise ContractError("cannot load JPL SPK kernel") from exc
    try:
        ts = loader.timescale(builtin=True)
        earth = _observer(kernel, req, wgs84)
        targets = {body: _target(kernel, body) for body in bodies}
        def lon(body, at):
            t = ts.from_datetime(at)
            pos = _position(earth, targets[body], t, "apparent")
            latitude, longitude, distance = pos.frame_latlon(ecliptic_frame)
            return float(longitude.degrees) % 360
        try:
            if mode == "aspects":
                events = find_aspect_events(
                    lambda t: lon(bodies[0], t), lambda t: lon(bodies[1], t),
                    _stamp(start), _stamp(end), step)
            else:
                events = find_station_events(lambda t: lon(bodies[0], t),
                    _stamp(start), _stamp(end), step, rate_window)
        except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
            if isinstance(exc, ContractError):
                raise
            raise ContractError("kernel coverage or numerical evaluation unavailable") from exc
        return {
            "format": FORMAT,
            "query": {
                "start_utc": _stamp(start),
                "end_utc": _stamp(end),
                "mode": mode,
                "bodies": bodies,
                "origin": "geocentric",
                "position_model": "apparent",
                "frame": FRAME,
                "step_hours": step,
                "rate_window_hours": rate_window if mode == "stations" else None,
            },
            "provenance": {
                "engine": "skyfield", "engine_version": version,
                "ephemeris_id": path.name, "ephemeris_sha256": _digest(path),
                "time_data_id": f"skyfield-{version}-builtin-timescale",
                "generated_at_utc": _stamp(datetime.now(timezone.utc)),
            },
            "search_method": "sampled_bracket_and_bisection",
            "complete_for_tangent_contacts": False,
            "time_tolerance_seconds": ROOT_TOLERANCE_SECONDS,
            "events": events,
        }
    finally:
        kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="MAGICK M2 longitude events")
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--query", default="-", help="JSON query path or stdin")
    args = parser.parse_args(argv)
    try:
        if args.query == "-":
            query = json.load(sys.stdin)
        else:
            with open(args.query, encoding="utf-8") as fp:
                query = json.load(fp)
        result = event_report(query, args.kernel)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"MAGICK DYNAMICS ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, separators=(",", ":"), allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
