#!/usr/bin/env python3
"""Fetch and normalize IAU Meteor Data Center established meteor showers.

The MDC catalog is defined in solar longitude rather than fixed calendar dates.
This helper keeps that scientific representation, derives approximate UTC peak
times from the current solar longitude, and adds a local radiant-altitude
snapshot for the Weather Station coordinate fix.

No claim is made about observed meteor rate, cloud cover, moon interference,
or whether a catalog shower will be visually obvious from the user's site.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "iaumdc.astro.sk"
ENDPOINT = (
    "https://" + HOST
    + "/downloads/lists_shw_data/streamestablisheddata.json"
)
MAX_BYTES = 8 * 1024 * 1024
MEAN_SOLAR_RATE = 0.98564736
ACTIVE_MARGIN_DEG = 1.0
MAX_ACTIVE = 12
MAX_UPCOMING = 12


class IauOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected IAU MDC redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def short_text(value, limit: int) -> str:
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def status_number(value):
    text = str(value or "").strip()
    try:
        return int(text)
    except ValueError:
        return None


def normalize_angle(value):
    number = finite(value)
    if number is None:
        return None
    return number % 360.0


def signed_angle_delta(target, origin):
    a = normalize_angle(target)
    b = normalize_angle(origin)
    if a is None or b is None:
        return None
    return ((a - b + 180.0) % 360.0) - 180.0


def forward_angle_delta(target, origin):
    a = normalize_angle(target)
    b = normalize_angle(origin)
    if a is None or b is None:
        return None
    return (a - b) % 360.0


def angle_in_range(value, start, end, margin=0.0):
    current = normalize_angle(value)
    first = normalize_angle(start)
    last = normalize_angle(end)
    extra = max(0.0, float(margin))
    if current is None or first is None or last is None:
        return False

    span = (last - first) % 360.0
    if span > 300.0:
        return False

    position = (current - first) % 360.0
    if position <= span:
        return True

    before = (first - current) % 360.0
    after = (current - last) % 360.0
    return before <= extra or after <= extra


def julian_day(when: datetime) -> float:
    dt = when.astimezone(timezone.utc)
    year = dt.year
    month = dt.month
    day_fraction = (
        dt.day
        + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60.0)
           / 60.0) / 24.0
    )
    if month <= 2:
        year -= 1
        month += 12
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    return (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day_fraction + b - 1524.5
    )


def solar_longitude_deg(when: datetime) -> float:
    """Approximate geocentric apparent solar ecliptic longitude."""
    jd = julian_day(when)
    days = jd - 2451545.0
    mean_long = (280.46646 + 0.98564736 * days) % 360.0
    anomaly = math.radians((357.52911 + 0.98560028 * days) % 360.0)
    center = (
        1.914602 * math.sin(anomaly)
        + 0.019993 * math.sin(2 * anomaly)
        + 0.000289 * math.sin(3 * anomaly)
    )
    omega = math.radians(125.04 - 0.052954 * days)
    apparent = mean_long + center - 0.00569 - 0.00478 * math.sin(omega)
    return apparent % 360.0


def next_solar_longitude_time(now: datetime, target_deg: float) -> datetime:
    current = solar_longitude_deg(now)
    forward = forward_angle_delta(target_deg, current)
    if forward is None:
        raise ValueError("Invalid solar longitude")
    guess = now + timedelta(days=forward / MEAN_SOLAR_RATE)

    for _ in range(6):
        actual = solar_longitude_deg(guess)
        error = signed_angle_delta(target_deg, actual)
        if error is None:
            break
        guess += timedelta(days=error / MEAN_SOLAR_RATE)
        if abs(error) < 0.0002:
            break

    if guess < now - timedelta(minutes=10):
        guess += timedelta(days=365.2422)
        for _ in range(4):
            actual = solar_longitude_deg(guess)
            error = signed_angle_delta(target_deg, actual)
            if error is None:
                break
            guess += timedelta(days=error / MEAN_SOLAR_RATE)
    return guess.astimezone(timezone.utc)


def gmst_degrees(when: datetime) -> float:
    jd = julian_day(when)
    t = (jd - 2451545.0) / 36525.0
    value = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - t * t * t / 38710000.0
    )
    return value % 360.0


def radiant_altitude(ra_deg, dec_deg, latitude_deg, longitude_deg,
                     when: datetime):
    ra = finite(ra_deg)
    dec = finite(dec_deg)
    lat = finite(latitude_deg)
    lon = finite(longitude_deg)
    if None in (ra, dec, lat, lon):
        return None
    if not (-90 <= dec <= 90 and -90 <= lat <= 90 and -180 <= lon <= 180):
        return None

    lst = (gmst_degrees(when) + lon) % 360.0
    hour_angle = math.radians(((lst - ra + 180.0) % 360.0) - 180.0)
    dec_r = math.radians(dec)
    lat_r = math.radians(lat)
    sine = (
        math.sin(lat_r) * math.sin(dec_r)
        + math.cos(lat_r) * math.cos(dec_r) * math.cos(hour_angle)
    )
    altitude = math.degrees(math.asin(max(-1.0, min(1.0, sine))))
    return altitude


def parse_submission_date(value: str):
    text = str(value or "")
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().toordinal()
    except ValueError:
        match = text[:4]
        return int(match) * 366 if match.isdigit() else 0


def canonical_solution(shower):
    solutions = shower.get("solution")
    if not isinstance(solutions, list):
        return None
    candidates = []
    for row in solutions:
        if not isinstance(row, dict):
            continue
        if str(row.get("activity", "")).strip().lower() != "annual":
            continue
        peak = normalize_angle(row.get("LoS"))
        ra = finite(row.get("Ra"))
        dec = finite(row.get("De"))
        if peak is None or ra is None or dec is None:
            continue

        score = 0
        if finite(row.get("LoSb")) is not None and finite(row.get("LoSe")) is not None:
            score += 10
        if finite(row.get("Vg")) is not None:
            score += 3
        if short_text(row.get("Parent body"), 120):
            score += 2
        technique = short_text(
            row.get("Ote") if row.get("Ote") is not None else row.get("OTe"),
            20,
        ).upper()
        if "V" in technique:
            score += 1

        candidates.append((
            score,
            parse_submission_date(row.get("sub.date")),
            row,
        ))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def normalize_shower(shower, solution):
    if status_number(shower.get("s")) != 1:
        return None

    name = short_text(shower.get("Name"), 96)
    code = short_text(shower.get("Code"), 12).upper()
    iau_no = short_text(shower.get("IAUNo"), 24)
    if not name or not iau_no:
        return None

    peak = normalize_angle(solution.get("LoS"))
    ra = finite(solution.get("Ra"))
    dec = finite(solution.get("De"))
    if peak is None or ra is None or dec is None:
        return None

    begin = normalize_angle(solution.get("LoSb"))
    end = normalize_angle(solution.get("LoSe"))
    speed = finite(solution.get("Vg"))
    parent = short_text(solution.get("Parent body"), 120)
    technique = short_text(
        solution.get("Ote") if solution.get("Ote") is not None
        else solution.get("OTe"),
        20,
    ).upper()

    return {
        "iauNo": iau_no,
        "code": code,
        "name": name,
        "solarBegin": begin,
        "solarEnd": end,
        "solarPeak": peak,
        "ra": ra % 360.0,
        "dec": dec,
        "speedKmS": speed,
        "parentBody": parent,
        "technique": technique,
        "submissionDate": short_text(solution.get("sub.date"), 20),
    }


def parse_catalog(root):
    if not isinstance(root, dict) or not isinstance(root.get("data"), list):
        raise ValueError("Invalid IAU MDC shower catalog")

    rows = []
    seen = set()
    for shower in root["data"]:
        if not isinstance(shower, dict):
            continue
        solution = canonical_solution(shower)
        if solution is None:
            continue
        row = normalize_shower(shower, solution)
        if row is None or row["iauNo"] in seen:
            continue
        seen.add(row["iauNo"])
        rows.append(row)

    if not rows:
        raise ValueError("IAU MDC established shower catalog empty")
    return rows


def enrich(row, now, current_solar, latitude, longitude):
    peak_time = next_solar_longitude_time(now, row["solarPeak"])
    days_to_peak = (peak_time - now).total_seconds() / 86400.0
    altitude = radiant_altitude(
        row["ra"], row["dec"], latitude, longitude, now
    )
    active = (
        row["solarBegin"] is not None
        and row["solarEnd"] is not None
        and angle_in_range(
            current_solar,
            row["solarBegin"],
            row["solarEnd"],
            ACTIVE_MARGIN_DEG,
        )
    )
    peak_delta = signed_angle_delta(row["solarPeak"], current_solar)
    return {
        **row,
        "active": active,
        "peakDeltaDeg": peak_delta,
        "daysToPeak": days_to_peak,
        "peakUtc": peak_time.isoformat().replace("+00:00", "Z"),
        "radiantAltitude": altitude,
        "radiantAboveHorizon": altitude is not None and altitude > 0,
    }


def summarize(root, now, latitude, longitude):
    rows = parse_catalog(root)
    current_solar = solar_longitude_deg(now)
    enriched = [
        enrich(row, now, current_solar, latitude, longitude)
        for row in rows
    ]

    active = [row for row in enriched if row["active"]]
    active.sort(key=lambda row: (
        0 if row["radiantAboveHorizon"] else 1,
        abs(row["peakDeltaDeg"]) if row["peakDeltaDeg"] is not None else 999,
        -row["radiantAltitude"] if row["radiantAltitude"] is not None else 999,
        row["name"],
    ))

    upcoming = sorted(
        enriched,
        key=lambda row: (
            row["daysToPeak"],
            row["name"],
        ),
    )

    return {
        "source": short_text(root.get("source"), 80) or "IAU Meteor Data Center",
        "version": short_text(root.get("version"), 32),
        "catalogCount": len(rows),
        "solarLongitude": current_solar,
        "generatedUtc": now.astimezone(timezone.utc)
            .isoformat().replace("+00:00", "Z"),
        "activeCount": len(active),
        "active": active[:MAX_ACTIVE],
        "upcoming": upcoming[:MAX_UPCOMING],
        "note": "PEAK UTC IS LOCALLY DERIVED FROM IAU SOLAR LONGITUDE",
    }


def fetch_catalog():
    opener = build_opener(IauOnlyRedirects())
    request = Request(
        ENDPOINT,
        headers={
            "User-Agent": "Post-Apollo-WeatherStation/1.0",
            "Accept": "application/json",
        },
    )
    with opener.open(request, timeout=15) as response:
        actual = urlsplit(response.geturl())
        if (
            actual.scheme != "https"
            or actual.hostname != HOST
            or not actual.path.endswith("/streamestablisheddata.json")
        ):
            raise ValueError("Unexpected IAU MDC response URL")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("IAU MDC response too large")
        return json.loads(payload.decode("utf-8"))


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        sys.stdout.write('{"error":"IAU METEOR LOCATION REQUIRED"}')
        return 2

    latitude = finite(args[0])
    longitude = finite(args[1])
    if (
        latitude is None or longitude is None
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        sys.stdout.write('{"error":"IAU METEOR LOCATION INVALID"}')
        return 2

    try:
        result = summarize(
            fetch_catalog(),
            datetime.now(timezone.utc),
            latitude,
            longitude,
        )
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
        return 0
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError):
        sys.stdout.write('{"error":"IAU METEOR CATALOG UNAVAILABLE"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
