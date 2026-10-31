#!/usr/bin/env python3
"""Fetch USNO rise/transit/set data for the five practical naked-eye planets.

USNO's Major Solar System Bodies and Bright Stars service is an official HTML
calculator rather than part of the JSON API. This helper uses only the verified
body ids for Mercury, Venus, Mars, Jupiter, and Saturn, parses one local civil
date, and emits bounded JSON for the SKY view.

The service documents one-minute rise/set precision, true-north azimuths,
atmospheric refraction in its apparent-altitude model, and special symbols for
objects continuously above/below the horizon or indeterminate events.
"""
from __future__ import annotations

from datetime import datetime
from html.parser import HTMLParser
import json
import math
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "aa.usno.navy.mil"
ENDPOINT = "https://" + HOST + "/calculated/mrst"
MAX_BYTES = 768 * 1024

PLANETS = (
    ("MERCURY", 1),
    ("VENUS", 2),
    ("MARS", 4),
    ("JUPITER", 5),
    ("SATURN", 6),
)

MONTHS = {
    1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
    7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec",
}


class UsnoOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected USNO redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class VisibleText(HTMLParser):
    """Conservative text extraction preserving table/preformatted line breaks."""

    BREAK_TAGS = {"br", "p", "pre", "tr", "div", "table", "section"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(str(data))

    def text(self) -> str:
        return "".join(self.parts)


def finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def valid_date(value: str) -> bool:
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d")
    except (TypeError, ValueError):
        return False
    return 1800 <= parsed.year <= 2050


def snapped_offset_minutes(value):
    raw = finite(value)
    if raw is None:
        return None
    snapped = round(raw / 15.0) * 15
    if snapped < -720 or snapped > 840:
        return None
    if abs(snapped - raw) > 8:
        return None
    return int(snapped)


def tz_hours_text(offset_minutes: int) -> str:
    hours = abs(offset_minutes) / 60.0
    if abs(hours - round(hours)) < 1e-9:
        return str(int(round(hours)))
    if abs(hours * 2 - round(hours * 2)) < 1e-9:
        return f"{hours:.1f}"
    return f"{hours:.2f}".rstrip("0").rstrip(".")


def request_info(date_value, latitude_value, longitude_value, offset_minutes):
    date = str(date_value or "")
    latitude = finite(latitude_value)
    longitude = finite(longitude_value)
    snapped = snapped_offset_minutes(offset_minutes)
    date_ok = valid_date(date)
    coords_ok = (
        latitude is not None and longitude is not None
        and -90 <= latitude <= 90 and -180 <= longitude <= 180
    )
    offset_ok = snapped is not None
    if not (date_ok and coords_ok and offset_ok):
        return {
            "valid": False,
            "dateValid": date_ok,
            "coordinatesValid": coords_ok,
            "offsetValid": offset_ok,
            "date": date,
            "latitude": latitude,
            "longitude": longitude,
            "offsetMinutes": snapped,
            "key": "",
        }

    key = (
        f"{date}|{latitude:.4f}|{longitude:.4f}|{snapped}"
    )
    return {
        "valid": True,
        "dateValid": True,
        "coordinatesValid": True,
        "offsetValid": True,
        "date": date,
        "latitude": latitude,
        "longitude": longitude,
        "offsetMinutes": snapped,
        "key": key,
    }


def planet_url(body_id: int, info: dict) -> str:
    if not info or not info.get("valid"):
        return ""
    offset = int(info["offsetMinutes"])
    params = {
        "body": str(int(body_id)),
        "date": info["date"],
        "height": "0",
        "label": "Post Apollo Weather",
        "lat": f"{info['latitude']:.4f}",
        "lon": f"{info['longitude']:.4f}",
        "reps": "1",
        "submit": "Get Data",
        "tz": tz_hours_text(offset),
        "tz_sign": "1" if offset >= 0 else "-1",
    }
    return ENDPOINT + "?" + urlencode(params)


def clock_label(value: str) -> str:
    match = re.fullmatch(r"(\d{2}):(\d{2})", str(value or "").strip())
    if not match:
        return "--"
    hour = int(match.group(1))
    minute = int(match.group(2))
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return "--"
    suffix = "PM" if hour >= 12 else "AM"
    hour12 = 12 if hour % 12 == 0 else hour % 12
    return f"{hour12}:{minute:02d} {suffix}"


def visible_lines(raw_html: bytes) -> list[str]:
    parser = VisibleText()
    parser.feed(raw_html.decode("utf-8", "replace"))
    lines = []
    for raw in parser.text().splitlines():
        compact = re.sub(r"\s+", " ", raw).strip()
        if compact:
            lines.append(compact)
    return lines


def parse_normal_tail(tail: str):
    match = re.fullmatch(
        r"(\d{2}:\d{2})\s+(\d{1,3})\s+"
        r"(\d{2}:\d{2})\s+(\d{1,3})([NS])?\s+"
        r"(\d{2}:\d{2})\s+(\d{1,3})",
        str(tail or "").strip(),
    )
    if not match:
        return None

    rise_az = int(match.group(2))
    transit_alt = int(match.group(4))
    set_az = int(match.group(7))
    if not (0 <= rise_az <= 360 and 0 <= set_az <= 360
            and 0 <= transit_alt <= 90):
        return None

    return {
        "status": "NORMAL",
        "rise": match.group(1),
        "riseLabel": clock_label(match.group(1)),
        "riseAzimuth": rise_az,
        "transit": match.group(3),
        "transitLabel": clock_label(match.group(3)),
        "transitAltitude": transit_alt,
        "transitHemisphere": match.group(5) or "",
        "set": match.group(6),
        "setLabel": clock_label(match.group(6)),
        "setAzimuth": set_az,
    }


def special_status(tail: str) -> str:
    text = str(tail or "")
    if "*****" in text:
        return "CONTINUOUSLY ABOVE HORIZON"
    if "----" in text:
        return "CONTINUOUSLY BELOW HORIZON"
    if "?????" in text:
        return "INDETERMINATE"
    return ""


def parse_planet_page(raw_html: bytes, date_value: str,
                      expected_name: str, body_id: int):
    lines = visible_lines(raw_html)
    joined = "\n".join(lines).upper()
    if expected_name.upper() not in joined:
        raise ValueError("USNO body/title mismatch")

    date = datetime.strptime(date_value, "%Y-%m-%d")
    prefix = re.compile(
        rf"^{date.year}\s+{MONTHS[date.month]}\s+0?{date.day}\s+"
        r"\([A-Za-z]{3}\)\s+(.*)$"
    )

    tail = ""
    for line in lines:
        match = prefix.match(line)
        if match:
            tail = match.group(1).strip()
            break
    if not tail:
        raise ValueError("USNO target-date row missing")

    row = {
        "name": expected_name,
        "bodyId": int(body_id),
        "date": date_value,
        "status": "UNAVAILABLE",
        "rise": "",
        "riseLabel": "--",
        "riseAzimuth": None,
        "transit": "",
        "transitLabel": "--",
        "transitAltitude": None,
        "transitHemisphere": "",
        "set": "",
        "setLabel": "--",
        "setAzimuth": None,
    }

    normal = parse_normal_tail(tail)
    if normal:
        row.update(normal)
        return row

    special = special_status(tail)
    if special:
        row["status"] = special
        return row

    row["status"] = "PARTIAL / UNPARSED"
    return row


def fetch_page(opener, url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "Post-Apollo-WeatherStation/0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with opener.open(request, timeout=12) as response:
        actual = urlsplit(response.geturl())
        if (actual.scheme != "https" or actual.hostname != HOST
                or not actual.path.startswith("/calculated/mrst")):
            raise ValueError("Unexpected USNO response URL")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("USNO response too large")
        return payload


def fetch_planets(info: dict):
    opener = build_opener(UsnoOnlyRedirects())
    planets = []
    failed = []

    for name, body_id in PLANETS:
        try:
            raw = fetch_page(opener, planet_url(body_id, info))
            planets.append(
                parse_planet_page(raw, info["date"], name, body_id)
            )
        except (HTTPError, URLError, OSError, ValueError):
            failed.append(name)

    if not planets:
        raise RuntimeError("USNO planet rise/set unavailable")

    by_name = {row["name"]: row for row in planets}
    ordered = [by_name[name] for name, _ in PLANETS if name in by_name]
    return {
        "source": "USNO MRST",
        "date": info["date"],
        "offsetMinutes": info["offsetMinutes"],
        "timezoneHours": info["offsetMinutes"] / 60.0,
        "planets": ordered,
        "failedPlanets": failed,
        "precision": "ONE MINUTE",
        "azimuthReference": "TRUE NORTH",
    }


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4:
        sys.stdout.write(
            '{"error":"USNO PLANET RISE SET INPUTS REQUIRED"}'
        )
        return 2

    info = request_info(args[0], args[1], args[2], args[3])
    if not info["valid"]:
        sys.stdout.write(
            '{"error":"USNO PLANET RISE SET INPUTS INVALID"}'
        )
        return 2

    try:
        result = fetch_planets(info)
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
        return 0
    except RuntimeError:
        sys.stdout.write(
            '{"error":"USNO PLANET RISE SET UNAVAILABLE"}'
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
