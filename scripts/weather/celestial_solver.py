"""MAGICK M1: deterministic offline JPL SPK celestial positions.

Requires Skyfield 1.55 and a caller-supplied local .bsp ephemeris file.
This module never downloads kernels, guesses coordinates, or writes user data.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from celestial_contract import (
    ContractError, SNAPSHOT_FORMAT, normalize_request, validate_snapshot,
)

# Exact NAIF IDs. A system barycenter is deliberately not relabeled as a planet.
NAIF_IDS = {
    "sun": 10, "moon": 301, "earth": 399,
    "mercury": 199, "venus": 299, "mars": 499,
    "mars_barycenter": 4,
    "jupiter_barycenter": 5, "saturn_barycenter": 6,
    "uranus_barycenter": 7, "neptune_barycenter": 8,
    "pluto_barycenter": 9,
}


def _kernel_file(path):
    """No implicit downloads or path guessing; enforce a caller-owned kernel."""
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ContractError("kernel path is required")
    kernel = Path(path).expanduser()
    if not kernel.is_file() or kernel.suffix.lower() != ".bsp":
        raise ContractError("kernel must be an existing local .bsp file")
    return kernel


def _digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _import_skyfield():
    try:
        import skyfield
        from skyfield.api import load_file, load, wgs84
        from skyfield.framelib import ecliptic_frame
    except ImportError as exc:
        raise ContractError("Skyfield is required (install skyfield==1.55 in an isolated environment)") from exc
    return skyfield.__version__, load_file, load, wgs84, ecliptic_frame


def _target(ephemeris, body):
    """Resolve by NAIF ID; never accept a silent center/barycenter alias."""
    try:
        return ephemeris[NAIF_IDS[body]]
    except (KeyError, ValueError) as exc:
        raise ContractError(
            f"kernel has no exact target for {body} (NAIF {NAIF_IDS[body]}); "
            "request a specifically named barycenter where appropriate"
        ) from exc


def _observer(ephemeris, request, wgs84):
    origin = request["origin"]
    if origin == "heliocentric":
        return _target(ephemeris, "sun")
    earth = _target(ephemeris, "earth")
    if origin == "topocentric":
        point = request["observer"]
        return earth + wgs84.latlon(
            latitude_degrees=point["latitude_deg"],
            longitude_degrees=point["longitude_deg"],
            elevation_m=point["elevation_m"],
        )
    return earth


def _position(origin_vector, target, t, mode):
    if mode == "apparent":
        # Light travel, aberration, and gravitational deflection included.
        return origin_vector.at(t).observe(target).apparent()
    # Instantaneous geometric vector. observe() would be wrong: it always
    # applies light-time correction even without a later apparent() call.
    return (target - origin_vector).at(t)


def compute_snapshot(raw_request, kernel_path):
    """Compute ecliptic coordinates from an explicit kernel and request.

    All times are normalized UTC input, evaluated in Skyfield TDB. Frame
    is Skyfield's true ecliptic/equinox of date; barycenters stay labeled.
    """
    request = normalize_request(raw_request)
    path = _kernel_file(kernel_path)
    version, load_file, loader, wgs84, ecliptic_frame = _import_skyfield()
    try:
        kernel = load_file(str(path))
    except Exception as exc:
        raise ContractError("cannot load JPL SPK .bsp kernel") from exc
    try:
        # builtin=True prevents Skyfield from making network requests.
        ts = loader.timescale(builtin=True)
        instant = datetime.fromisoformat(request["instant_utc"].replace("Z", "+00:00"))
        t = ts.from_datetime(instant)
        origin_vector = _observer(kernel, request, wgs84)
        positions = []
        for body in request["bodies"]:
            target = _target(kernel, body)
            p = _position(origin_vector, target, t, request["position_model"])
            lat, lon, distance = p.frame_latlon(ecliptic_frame)
            positions.append({
                "body": body,
                "longitude_deg": float(lon.degrees) % 360.0,
                "latitude_deg": float(lat.degrees),
                "distance_au": float(distance.au),
            })
        snapshot = {
            "format": SNAPSHOT_FORMAT,
            "request": request,
            "tdb_jd": float(t.tdb),
            "provenance": {
                "engine": "skyfield",
                "engine_version": version,
                "ephemeris_id": path.name,
                "ephemeris_sha256": _digest(path),
                "time_data_id": f"skyfield-{version}-builtin-timescale",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds").replace("+00:00", "Z"),
            },
            "positions": positions,
        }
        validate_snapshot(snapshot)
        return snapshot
    except (ValueError, KeyError, IndexError, ArithmeticError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError(
            "ephemeris target or timestamp is outside this kernel's supported coverage"
        ) from exc
    finally:
        kernel.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline JPL/Skyfield celestial-position calculator")
    parser.add_argument("--kernel", required=True,
                        help="Explicit local JPL SPK .bsp kernel path")
    parser.add_argument("--request", default="-",
                        help="JSON request file or '-' for stdin")
    args = parser.parse_args(argv)
    try:
        if args.request == "-":
            request = json.load(sys.stdin)
        else:
            with open(args.request, encoding="utf-8") as source:
                request = json.load(source)
        result = compute_snapshot(request, args.kernel)
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"MAGICK CELESTIAL ERROR: {exc}", file=sys.stderr)
        return 2
    json.dump(result, sys.stdout, separators=(",", ":"), allow_nan=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
