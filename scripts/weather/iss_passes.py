#!/usr/bin/env python3
"""Fetch ISS pass geometry plus CelesTrak orbital-element provenance.

Pass geometry comes from the unauthenticated iss-in.space JSON endpoint, which
documents Skyfield/SGP4 predictions from CelesTrak TLE data. CelesTrak is also
queried directly for NORAD 25544 so the Weather Station can expose the orbital
element epoch used as source-freshness context.

This helper does not claim optical visibility. It returns geometric horizon
passes only: rise, culmination, set, azimuth, elevation, range and duration.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

PASS_HOST = "iss-in.space"
CELESTRAK_HOST = "celestrak.org"
NORAD_ID = 25544
MAX_BYTES = 2 * 1024 * 1024
MAX_PASSES = 8


class HostOnlyRedirects(HTTPRedirectHandler):
    def __init__(self, host: str):
        super().__init__()
        self.host = host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != self.host:
            raise ValueError("Unexpected provider redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def validate_coordinate(value, minimum, maximum, label):
    number = finite(value)
    if number is None or number < minimum or number > maximum:
        raise ValueError(f"Invalid {label}")
    return number


def iso_millis(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def utc_label(value):
    millis = iso_millis(value)
    if millis is None:
        return "--"
    dt = datetime.fromtimestamp(millis / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%MZ")


def direction(value):
    text = " ".join(str(value or "").split()).upper()
    return text[:8] if text else "--"


def event_object(value, require_degrees=True):
    if not isinstance(value, dict):
        return None
    time = str(value.get("time") or "").strip()
    millis = iso_millis(time)
    azimuth = finite(value.get("azimuth"))
    degrees = finite(value.get("degrees"))
    distance = finite(value.get("distance"))
    if millis is None or azimuth is None or not 0 <= azimuth <= 360:
        return None
    if require_degrees and (degrees is None or not -5 <= degrees <= 90):
        return None
    if distance is not None and distance < 0:
        distance = None
    return {
        "time": time,
        "timeUtc": utc_label(time),
        "timeMillis": millis,
        "degrees": degrees,
        "azimuth": azimuth,
        "direction": direction(value.get("direction")),
        "distanceKm": distance,
    }


def normalize_pass(row, now_ms):
    if not isinstance(row, dict):
        return None
    rise = event_object(row.get("rise"))
    peak = event_object(row.get("culminate"))
    set_event = event_object(row.get("set"))
    if not rise or not peak or not set_event:
        return None
    if not (rise["timeMillis"] < peak["timeMillis"] < set_event["timeMillis"]):
        return None

    duration = finite(row.get("length"))
    if duration is None or duration <= 0:
        duration = (set_event["timeMillis"] - rise["timeMillis"]) / 1000.0
    if duration <= 0 or duration > 3600:
        return None

    if set_event["timeMillis"] < now_ms:
        return None

    return {
        "rise": rise,
        "culminate": peak,
        "set": set_event,
        "durationSeconds": int(round(duration)),
        "durationLabel": str(row.get("length_mins") or "").strip()
            or f"{int(duration // 60)}:{int(duration % 60):02d}",
        "minutesUntilRise": max(
            0.0, (rise["timeMillis"] - now_ms) / 60000.0
        ),
        "geometricPass": True,
        "visibilityEvaluated": False,
    }


def parse_passes(root, now):
    if not isinstance(root, list):
        raise ValueError("Invalid ISS pass response")
    now_ms = int(now.astimezone(timezone.utc).timestamp() * 1000)
    rows = []
    for raw in root:
        item = normalize_pass(raw, now_ms)
        if item is not None:
            rows.append(item)
    rows.sort(key=lambda item: item["rise"]["timeMillis"])
    if not rows:
        raise ValueError("No upcoming ISS passes returned")
    return rows[:MAX_PASSES]


def parse_celestrak(root):
    if not isinstance(root, list) or not root or not isinstance(root[0], dict):
        raise ValueError("Invalid CelesTrak ISS response")
    row = root[0]
    catnr = row.get("NORAD_CAT_ID")
    try:
        catnr = int(catnr)
    except (TypeError, ValueError):
        raise ValueError("Invalid CelesTrak NORAD id")
    if catnr != NORAD_ID:
        raise ValueError("Unexpected CelesTrak object")

    epoch = str(row.get("EPOCH") or "").strip()
    if iso_millis(epoch) is None:
        raise ValueError("CelesTrak ISS epoch missing")

    return {
        "objectName": " ".join(str(row.get("OBJECT_NAME") or "ISS").split())[:80],
        "noradId": catnr,
        "elementEpoch": epoch,
        "elementEpochUtc": utc_label(epoch),
        "meanMotion": finite(row.get("MEAN_MOTION")),
        "inclination": finite(row.get("INCLINATION")),
        "eccentricity": finite(row.get("ECCENTRICITY")),
    }


def fetch_json(host, url, user_agent):
    opener = build_opener(HostOnlyRedirects(host))
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    with opener.open(request, timeout=15) as response:
        actual = urlsplit(response.geturl())
        if actual.scheme != "https" or actual.hostname != host:
            raise ValueError("Unexpected provider response host")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("Provider response too large")
        return json.loads(payload.decode("utf-8"))


def pass_url(latitude, longitude):
    return (
        "https://" + PASS_HOST + "/api/passes/"
        + quote(f"{latitude:.5f}", safe="-")
        + "/" + quote(f"{longitude:.5f}", safe="-")
    )


def celestrak_url():
    return (
        "https://" + CELESTRAK_HOST
        + "/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON"
    )


def build_result(pass_root, celestrak_root, now):
    passes = parse_passes(pass_root, now)
    orbit = parse_celestrak(celestrak_root)
    return {
        "source": "ISS-IN.SPACE",
        "orbitalSource": "CELESTRAK",
        "predictionModel": "SKYFIELD + SGP4 (PROVIDER DOCUMENTED)",
        "generatedUtc": now.astimezone(timezone.utc)
            .isoformat().replace("+00:00", "Z"),
        "geometricPassOnly": True,
        "visibilityEvaluated": False,
        "orbit": orbit,
        "passes": passes,
        "passCount": len(passes),
    }


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        sys.stdout.write('{"error":"ISS PASS LOCATION REQUIRED"}')
        return 2

    try:
        latitude = validate_coordinate(args[0], -90, 90, "latitude")
        longitude = validate_coordinate(args[1], -180, 180, "longitude")
        now = datetime.now(timezone.utc)
        pass_root = fetch_json(
            PASS_HOST,
            pass_url(latitude, longitude),
            "Post-Apollo-WeatherStation/1.2",
        )
        celestrak_root = fetch_json(
            CELESTRAK_HOST,
            celestrak_url(),
            "Post-Apollo-WeatherStation/1.2",
        )
        result = build_result(pass_root, celestrak_root, now)
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
        return 0
    except (
        HTTPError, URLError, OSError, ValueError, json.JSONDecodeError
    ):
        sys.stdout.write('{"error":"ISS PASS DATA UNAVAILABLE"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
