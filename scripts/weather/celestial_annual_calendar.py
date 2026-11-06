"""MAGICK M7b: source-bound annual Moon phases and 24 solar terms.

An explicit existing JPL kernel and Skyfield are required. No network, cache,
installation, filesystem write, location inference, or synthetic phase dates.
A date's Moon icon is the phase sampled at that date's local 12:00 noon.
Precise phase/solar-term crossings are separately reported in UTC.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
import math
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from celestial_contract import ContractError
from celestial_solver import _digest, _import_skyfield, _kernel_file, _target

FORMAT = "post-apollo.weather.magick-annual-atlas.m7b.v1"
PHASES = (
    "new", "waxing-crescent", "first-quarter", "waxing-gibbous",
    "full", "waning-gibbous", "last-quarter", "waning-crescent",
)
MAJOR_PHASES = ("new", "first-quarter", "full", "last-quarter")
# Solar longitude measured from the March equinox in 15-degree increments.
# Names are traditional East Asian solar-term references, not local forecasts.
SOLAR_TERMS = (
    "spring-equinox", "clear-and-bright", "grain-rain",
    "start-of-summer", "grain-full", "grain-in-ear",
    "summer-solstice", "minor-heat", "major-heat",
    "start-of-autumn", "end-of-heat", "white-dew",
    "autumn-equinox", "cold-dew", "frost-descent",
    "start-of-winter", "minor-snow", "major-snow",
    "winter-solstice", "minor-cold", "major-cold",
    "start-of-spring", "rain-water", "awakening-of-insects",
)
MAJOR_SOLAR = frozenset((0, 6, 12, 18))
UTC = timezone.utc


def year_zone(year, zone):
    if isinstance(year, bool) or not isinstance(year, int) or not 1901 <= year <= 2099:
        raise ContractError("year must be an integer between 1901 and 2099")
    if not isinstance(zone, str) or len(zone) > 64 or not re.fullmatch(
        r"[A-Za-z0-9_+\-]+(?:/[A-Za-z0-9_+\-]+)*", zone
    ):
        raise ContractError("explicit IANA time zone is required")
    try:
        tz = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise ContractError("unsupported IANA time zone") from exc
    return tz


def utc_label(moment):
    if not isinstance(moment, datetime) or moment.tzinfo is None:
        raise ContractError("source event timestamp must have time zone")
    return moment.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def phase_band(angle):
    if isinstance(angle, bool) or not isinstance(angle, (int, float)) or not math.isfinite(angle):
        raise ContractError("Moon phase angle must be finite")
    if angle < 0 or angle >= 360:
        raise ContractError("Moon phase angle outside 0..360")
    return PHASES[int((angle + 22.5) // 45) % 8]


def assemble(year, zone, daily, lunar_events, solar_events, provenance):
    """Pure, independently testable contract for an already-measured ephemeris."""
    tz = year_zone(year, zone)
    if not isinstance(daily, list) or not isinstance(lunar_events, list) or not isinstance(solar_events, list):
        raise ContractError("annual source arrays required")
    start = date(year, 1, 1)
    stop = date(year + 1, 1, 1)
    count = (stop - start).days
    if len(daily) != count or not isinstance(provenance, dict) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", str(provenance.get("ephemeris_sha256", ""))
    ):
        raise ContractError("complete year and JPL source proof required")
    result_days = []
    for n, item in enumerate(daily):
        expected = (start + timedelta(days=n)).isoformat()
        if not isinstance(item, dict) or item.get("date") != expected:
            raise ContractError("every local date must be present in order")
        angle, illum = item.get("phase_angle_deg"), item.get("illumination")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
               for v in (angle, illum)) or not 0 <= angle < 360 or not 0 <= illum <= 100:
            raise ContractError("invalid measured lunar phase or illumination")
        result_days.append({
            "date": expected, "day_index": n, "month": (start + timedelta(days=n)).month,
            "phase_angle_deg": round(angle, 4), "illumination": round(illum, 3),
            "phase_id": phase_band(angle),
        })

    def validate_event(item, kind):
        if not isinstance(item, dict) or not isinstance(item.get("time_utc"), str):
            raise ContractError("event provenance/time missing")
        try:
            moment = datetime.fromisoformat(item["time_utc"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ContractError("event time invalid") from exc
        if moment.tzinfo is None or not start <= moment.astimezone(tz).date() < stop:
            raise ContractError("event falls outside selected local year")
        name = item.get("id")
        if kind == "moon" and name not in MAJOR_PHASES:
            raise ContractError("unknown lunar event")
        if kind == "solar" and name not in SOLAR_TERMS:
            raise ContractError("unknown solar term")
        record = {"kind": kind, "id": name, "date": moment.astimezone(tz).date().isoformat(),
                  "time_utc": utc_label(moment)}
        if kind == "solar":
            index = SOLAR_TERMS.index(name)
            if item.get("longitude_deg") != index * 15:
                raise ContractError("solar term not at labelled longitude")
            record.update({"longitude_deg": index * 15, "major": index in MAJOR_SOLAR})
        return record

    moon = [validate_event(x, "moon") for x in lunar_events]
    sun = [validate_event(x, "solar") for x in solar_events]
    if not 45 <= len(moon) <= 54 or len(sun) != 24 or len({x["id"] for x in sun}) != 24:
        raise ContractError("annual lunar events or 24 solar terms incomplete")
    if any(items[n]["time_utc"] <= items[n-1]["time_utc"] for items in (moon, sun)
           for n in range(1, len(items))):
        raise ContractError("events must be strictly ordered")
    return {
        "format": FORMAT, "year": year, "timezone": zone, "day_basis": "local-noon",
        "moon_phase_basis": "geocentric-apparent-ecliptic-longitude",
        "solar_term_basis": "geocentric-apparent-solar-longitude-15-degrees",
        "source": provenance.copy(), "days": result_days,
        "lunar_events": moon, "solar_terms": sun,
        "calendar_markers": {
            "daily_moon": [{"date": x["date"], "phase_id": x["phase_id"],
                            "illumination": x["illumination"]} for x in result_days],
            "events": sorted(moon + sun, key=lambda x: (x["time_utc"], x["kind"])),
        },
    }


def compute(year, zone, kernel_path):
    """Only the established local JPL/Skyfield stack supplies actual measurements."""
    tz = year_zone(year, zone)
    path = _kernel_file(kernel_path)
    version, load_file, loader, unused_wgs84, ecliptic_frame = _import_skyfield()
    from skyfield import almanac
    import numpy as np
    try:
        kernel = load_file(str(path))
    except Exception as exc:
        raise ContractError("cannot open local JPL kernel") from exc
    try:
        ts = loader.timescale(builtin=True)
        earth, sun, moon = (_target(kernel, name) for name in ("earth", "sun", "moon"))
        start = datetime(year, 1, 1, tzinfo=tz).astimezone(UTC)
        end = datetime(year + 1, 1, 1, tzinfo=tz).astimezone(UTC)
        left, right = ts.from_datetime(start), ts.from_datetime(end)

        days = []
        for n in range((date(year + 1, 1, 1) - date(year, 1, 1)).days):
            day = date(year, 1, 1) + timedelta(days=n)
            noon = datetime.combine(day, time(12, 0), tz).astimezone(UTC)
            t = ts.from_datetime(noon)
            angle = float(almanac.moon_phase(kernel, t).degrees) % 360.0
            illuminated = float(earth.at(t).observe(moon).fraction_illuminated(sun)) * 100.0
            days.append({"date": day.isoformat(), "phase_angle_deg": angle,
                         "illumination": illuminated})

        moon_times, moon_codes = almanac.find_discrete(left, right, almanac.moon_phases(kernel))
        moon_events = [
            {"id": MAJOR_PHASES[int(code)], "time_utc": utc_label(t.utc_datetime())}
            for t, code in zip(moon_times, moon_codes)
        ]

        def solar_index(t):
            # Exactly the same true-ecliptic-of-date apparent position frame
            # used by M1. A crossing increments by 15 degrees; no year fractions.
            e = earth.at(t).observe(sun).apparent()
            lon = e.frame_latlon(ecliptic_frame)[1].degrees % 360.0
            return np.floor(np.asarray(lon) / 15.0).astype(int)

        solar_index.step_days = 3.0
        solar_times, solar_codes = almanac.find_discrete(left, right, solar_index)
        solar_events = [
            {"id": SOLAR_TERMS[int(code)], "longitude_deg": 15 * int(code),
             "time_utc": utc_label(t.utc_datetime())}
            for t, code in zip(solar_times, solar_codes)
        ]
        return assemble(year, zone, days, moon_events, solar_events, {
            "engine": "skyfield", "engine_version": version, "ephemeris_id": path.name,
            "ephemeris_sha256": _digest(path), "time_data_id": f"skyfield-{version}-builtin",
            "generated_at_utc": utc_label(datetime.now(UTC)),
        })
    except (ArithmeticError, IndexError, KeyError, ValueError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("JPL ephemeris coverage or search unavailable") from exc
    finally:
        kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline MAGICK annual Sun/Moon atlas")
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--timezone", default="UTC")
    args = parser.parse_args(argv)
    try:
        value = compute(args.year, args.timezone, args.kernel)
    except (ContractError, OSError, ImportError) as exc:
        print(f"MAGICK ANNUAL ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(value, sys.stdout, separators=(",", ":"), allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
