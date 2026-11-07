"""MAGICK M8b // Source-bound, offline tropical natal chart computation.

Explicit UTC instant and geodetic observer, existing JPL BSP / Skyfield only.
No birth data file, download, cached profile, forecast substitute, or network.
Positions follow exact NAIF labels; outer planets are barycenter *positions*.
Whole-sign/equal houses use a physically calculated ascendant. Sidereal
requests fail closed until an independently verified ayanamsa is specified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import re
import sys

from celestial_contract import ContractError
from celestial_solver import _digest, _import_skyfield, _kernel_file, _position, _target, NAIF_IDS

FORMAT = "post-apollo.weather.magick-natal-chart.m8a.v1"
REQUEST_FORMAT = "post-apollo.weather.magick-natal-request.m8b.v1"
BODY_IDS = (
    "sun", "moon", "mercury", "venus", "mars_barycenter",
    "jupiter_barycenter", "saturn_barycenter", "uranus_barycenter",
    "neptune_barycenter", "pluto_barycenter",
)
ALLOWED_HOUSES = ("whole-sign", "equal")
UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
REQUEST_KEYS = {
    "format", "epoch_utc", "latitude_deg", "longitude_deg",
    "zodiac", "house_system",
}


def _number(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ContractError(f"{label} must be a numeric degree value")
    if not math.isfinite(value) or not low <= value <= high:
        raise ContractError(f"{label} outside accepted range")
    return float(value)


def normalize(raw):
    if not isinstance(raw, dict) or set(raw) != REQUEST_KEYS:
        raise ContractError("natal request must contain exactly the named fields")
    if raw.get("format") != REQUEST_FORMAT:
        raise ContractError("unsupported natal request format")
    stamp = raw.get("epoch_utc")
    if not isinstance(stamp, str) or not UTC_PATTERN.fullmatch(stamp):
        raise ContractError("explicit full UTC event timestamp required")
    try:
        event = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("UTC calendar date invalid") from exc
    if not 1901 <= event.year <= 2099 or event.tzinfo != timezone.utc:
        raise ContractError("year or UTC offset unsupported")
    lat = _number(raw.get("latitude_deg"), -90, 90, "latitude")
    lon = _number(raw.get("longitude_deg"), -180, 180, "longitude")
    if raw.get("zodiac") != "tropical":
        raise ContractError("sidereal natal charts unavailable pending verified ayanamsa")
    houses = raw.get("house_system")
    if houses not in ALLOWED_HOUSES:
        raise ContractError("only whole-sign and equal houses are implemented")
    return {
        "format": REQUEST_FORMAT, "epoch_utc": stamp,
        "latitude_deg": lat, "longitude_deg": lon,
        "zodiac": "tropical", "house_system": houses,
    }


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _rotate(matrix, vector):
    return tuple(sum(matrix[row][col] * vector[col] for col in range(3))
                 for row in range(3))


def _angle(vector):
    if not all(math.isfinite(x) for x in vector):
        raise ContractError("invalid celestial frame vector")
    if math.hypot(vector[0], vector[1]) < 1e-11:
        raise ContractError("degenerate ecliptic intersection")
    return math.degrees(math.atan2(vector[1], vector[0])) % 360


def angles_from_frame(latitude_deg, longitude_deg, gast_hours, equator_to_ecliptic):
    """Pure geometry using the same true equinox for GAST and both frames.

    Equatorial vectors are in the *true equator/equinox of date*. The supplied
    rotation maps that frame into the *true ecliptic/equinox of date*.

    Ascendant: eastern intersection of the local horizon and ecliptic.
    MC: upper-meridian intersection, selected by RA at local sidereal time.
    """
    latitude = math.radians(_number(latitude_deg, -90, 90, "latitude"))
    longitude = _number(longitude_deg, -180, 180, "longitude")
    gast = _number(gast_hours, 0, 24, "Greenwich apparent sidereal time")
    if not isinstance(equator_to_ecliptic, (list, tuple)) or len(equator_to_ecliptic) != 3:
        raise ContractError("equinox/ecliptic rotation required")
    for row in equator_to_ecliptic:
        if len(row) != 3 or any(not isinstance(x, (float, int)) or
                               not math.isfinite(x) for x in row):
            raise ContractError("invalid celestial frame rotation")
    theta = math.radians((gast * 15 + longitude) % 360)
    zenith_equator = (
        math.cos(latitude) * math.cos(theta),
        math.cos(latitude) * math.sin(theta),
        math.sin(latitude),
    )
    east_equator = (-math.sin(theta), math.cos(theta), 0.0)
    upper_meridian_equator = (math.cos(theta), math.sin(theta), 0.0)
    zenith = _rotate(equator_to_ecliptic, zenith_equator)
    east = _rotate(equator_to_ecliptic, east_equator)
    upper = _rotate(equator_to_ecliptic, upper_meridian_equator)

    north_ecliptic = (0.0, 0.0, 1.0)
    rise = _cross(north_ecliptic, zenith)
    if math.hypot(*rise) < 1e-9:
        raise ContractError("Ascendant undefined at this polar geometry")
    if _dot(rise, east) < 0:
        rise = tuple(-v for v in rise)
    meridian = _cross(north_ecliptic, east)
    if math.hypot(*meridian) < 1e-9:
        raise ContractError("Midheaven undefined at this observer geometry")
    if _dot(meridian, upper) < 0:
        meridian = tuple(-v for v in meridian)
    return _angle(rise), _angle(meridian)


def house_cusps(ascendant_deg, house_system):
    asc = _number(ascendant_deg, 0, 360, "Ascendant")
    if asc == 360 or house_system not in ALLOWED_HOUSES:
        raise ContractError("house system or ascendant unsupported")
    first = math.floor(asc / 30) * 30 if house_system == "whole-sign" else asc
    return [(first + 30 * i) % 360 for i in range(12)]


def compute(raw_request, kernel_path):
    request = normalize(raw_request)
    path = _kernel_file(kernel_path)
    version, load_file, loader, wgs84, ecliptic_frame = _import_skyfield()
    from skyfield.framelib import true_equator_and_equinox_of_date
    from skyfield.functions import T, mxm

    try:
        kernel = load_file(str(path))
    except Exception as exc:
        raise ContractError("cannot load caller-owned JPL BSP") from exc
    try:
        ts = loader.timescale(builtin=True)
        moment = datetime.fromisoformat(request["epoch_utc"].replace("Z", "+00:00"))
        t = ts.from_datetime(moment)
        # GAST is Earth-rotation angle in the true equator/equinox-of-date.
        # Pair it with the true frame rotation rather than a J2000 frame.
        rotation = mxm(ecliptic_frame.rotation_at(t),
                       T(true_equator_and_equinox_of_date.rotation_at(t)))
        ascendant, midheaven = angles_from_frame(
            request["latitude_deg"], request["longitude_deg"],
            float(t.gast), rotation,
        )

        origin = _target(kernel, "earth") + wgs84.latlon(
            latitude_degrees=request["latitude_deg"],
            longitude_degrees=request["longitude_deg"],
            elevation_m=0.0,
        )
        positions = []
        for name in BODY_IDS:
            point = _position(origin, _target(kernel, name), t, "apparent")
            lat, lon, dist = point.frame_latlon(ecliptic_frame)
            value = float(lon.degrees) % 360.0
            latitude_value = float(lat.degrees)
            distance_value = float(dist.au)
            if not (math.isfinite(value) and math.isfinite(latitude_value) and
                    math.isfinite(distance_value) and distance_value > 0):
                raise ContractError("nonfinite JPL position")
            positions.append({
                "id": name, "naif_id": NAIF_IDS[name],
                "longitude_deg": value, "latitude_deg": latitude_value,
                "distance_au": distance_value,
            })

        return {
            "format": FORMAT,
            "epoch_utc": request["epoch_utc"],
            "origin": "topocentric",
            "frame": "true-ecliptic-of-date",
            "position_model": "apparent",
            "zodiac": request["zodiac"],
            "house_system": request["house_system"],
            "ascendant_deg": ascendant,
            "mc_deg": midheaven,
            "house_cusps_deg": house_cusps(ascendant, request["house_system"]),
            "positions": positions,
            "observer": {
                "latitude_deg": request["latitude_deg"],
                "longitude_deg": request["longitude_deg"],
                "elevation_m": 0.0,
            },
            "provenance": {
                "engine": "skyfield", "engine_version": version,
                "ephemeris_id": path.name,
                "ephemeris_sha256": _digest(path),
                "time_data_id": f"skyfield-{version}-builtin-timescale",
                "house_method": "true-equinox-horizon-meridian-geometric",
                "generated_at_utc": datetime.now(timezone.utc)
                .isoformat(timespec="seconds").replace("+00:00", "Z"),
            },
        }
    except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("JPL target, time or observer calculation unavailable") from exc
    finally:
        kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Source-bound private natal chart")
    parser.add_argument("--kernel", required=True)
    args = parser.parse_args(argv)
    try:
        # One bounded JSON line, not argv (which leaks birth details to ps).
        line = sys.stdin.readline(2049)
        if not line or len(line) > 2048 or not line.endswith("\n"):
            raise ContractError("bounded newline-terminated stdin request required")
        payload = json.loads(line)
        result = compute(payload, args.kernel)
    except (ContractError, OSError, ImportError, json.JSONDecodeError) as exc:
        print(f"MAGICK NATAL ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, separators=(",", ":"), allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
