"""MAGICK M0: dependency-free wire contract for computed celestial states.

No ephemeris is calculated here. No network, UI, location inference or storage.
The M1 engine must fill the state from a named, versioned ephemeris.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import re

REQUEST_FORMAT = "post-apollo.weather.celestial-request.v1"
SNAPSHOT_FORMAT = "post-apollo.weather.celestial-snapshot.v1"
FRAME = "true-ecliptic-of-date"
ORIGINS = frozenset(("geocentric", "topocentric", "heliocentric"))
POSITION_MODELS = frozenset(("apparent", "geometric"))
BODIES = frozenset((
    "sun", "moon", "earth", "mercury", "venus", "mars",
    "jupiter_barycenter", "saturn_barycenter", "uranus_barycenter",
    "neptune_barycenter", "pluto_barycenter",
))
_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$")
_SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


class ContractError(ValueError):
    """Reject ambiguous or incomplete scientific data rather than guessing."""


def _object(value, name):
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object")
    return value


def _number(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be a number")
    number = float(value)
    if not math.isfinite(number) or (low is not None and number < low) or (
        high is not None and number > high
    ):
        raise ContractError(f"{name} out of range")
    return number


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} must be nonempty text")
    return value.strip()


def utc_instant(value):
    """Parse an explicit UTC instant only, never infer a local/DST offset."""
    if not isinstance(value, str) or not _TIME_PATTERN.fullmatch(value):
        raise ContractError("instant_utc must be an ISO 8601 UTC timestamp ending Z")
    try:
        date = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ContractError("invalid UTC calendar time") from exc
    if date.year < 1 or date.tzinfo != timezone.utc:
        raise ContractError("invalid UTC calendar time")
    return date.isoformat(timespec="microseconds").replace("+00:00", "Z")


def normalize_request(value):
    """Return canonical JSON-compatible request, or fail closed."""
    row = _object(value, "request")
    if row.get("format") != REQUEST_FORMAT:
        raise ContractError("unsupported request format")
    instant = utc_instant(row.get("instant_utc"))
    origin = row.get("origin")
    model = row.get("position_model")
    if not isinstance(origin, str) or origin not in ORIGINS:
        raise ContractError("unsupported origin")
    if not isinstance(model, str) or model not in POSITION_MODELS:
        raise ContractError("unsupported position_model")
    if origin == "heliocentric" and model != "geometric":
        raise ContractError("heliocentric coordinates require geometric model")
    if row.get("frame") != FRAME:
        raise ContractError("unsupported frame")

    bodies = row.get("bodies")
    if not isinstance(bodies, list) or not bodies or any(
        not isinstance(body, str) or body not in BODIES for body in bodies
    ) or len(set(bodies)) != len(bodies):
        raise ContractError("bodies must be a nonempty unique list of supported IDs")
    center_body = "earth" if origin in ("geocentric", "topocentric") else "sun"
    if center_body in bodies:
        raise ContractError("cannot give angular coordinates for the origin body")

    observer = row.get("observer")
    if origin == "topocentric":
        obs = _object(observer, "observer")
        if set(obs) != {"latitude_deg", "longitude_deg", "elevation_m"}:
            raise ContractError("topocentric observer requires latitude, longitude and elevation")
        observer = {
            "latitude_deg": _number(obs["latitude_deg"], "latitude_deg", -90, 90),
            "longitude_deg": _number(obs["longitude_deg"], "longitude_deg", -180, 180),
            "elevation_m": _number(obs["elevation_m"], "elevation_m"),
        }
    elif observer is not None:
        raise ContractError("observer is only permitted for topocentric origin")
    return {
        "format": REQUEST_FORMAT,
        "instant_utc": instant,
        "origin": origin,
        "position_model": model,
        "frame": FRAME,
        "bodies": sorted(bodies),
        "observer": observer,
    }


def validate_snapshot(value):
    """Validate M1's result before QML/graph consumers see a position."""
    row = _object(value, "snapshot")
    if row.get("format") != SNAPSHOT_FORMAT:
        raise ContractError("unsupported snapshot format")
    request = normalize_request(row.get("request"))
    tdb_jd = _number(row.get("tdb_jd"), "tdb_jd", 0)
    provenance = _object(row.get("provenance"), "provenance")
    if set(provenance) != {
        "engine", "engine_version", "ephemeris_id",
        "ephemeris_sha256", "time_data_id", "generated_at_utc"
    }:
        raise ContractError("incomplete provenance")
    for field in ("engine", "engine_version", "ephemeris_id", "time_data_id"):
        _text(provenance[field], field)
    if not isinstance(provenance["ephemeris_sha256"], str) or not (
        _SHA256_PATTERN.fullmatch(provenance["ephemeris_sha256"])
    ):
        raise ContractError("ephemeris_sha256 must be a SHA-256 hex digest")
    utc_instant(provenance["generated_at_utc"])
    positions = row.get("positions")
    if not isinstance(positions, list):
        raise ContractError("positions must be a list")
    ids = []
    for position in positions:
        entry = _object(position, "position")
        body = entry.get("body")
        if not isinstance(body, str) or body not in BODIES:
            raise ContractError("unknown position body")
        ids.append(body)
        for field in ("longitude_deg", "latitude_deg", "distance_au"):
            if field not in entry:
                raise ContractError(f"missing {field}")
        longitude = _number(entry["longitude_deg"], "longitude_deg", 0, 360)
        if longitude == 360:
            raise ContractError("longitude_deg must be less than 360")
        _number(entry["latitude_deg"], "latitude_deg", -90, 90)
        _number(entry["distance_au"], "distance_au", 0)
        if "longitude_rate_deg_per_day" in entry:
            _number(entry["longitude_rate_deg_per_day"], "longitude_rate_deg_per_day")
    if len(ids) != len(set(ids)) or sorted(ids) != request["bodies"]:
        raise ContractError("positions must match requested bodies exactly")
    return {"request": request, "tdb_jd": tdb_jd, "body_count": len(positions)}
