#!/usr/bin/env python3
"""Fetch one bounded NASA FIRMS Area API CSV request.

The FIRMS MAP_KEY is read only from POST_APOLLO_FIRMS_MAP_KEY. It is never
accepted as argv, printed, or embedded in repository state.
"""
from __future__ import annotations

import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

KEY_RE = re.compile(r"[A-Za-z0-9_-]{8,128}\Z")
BBOX_RE = re.compile(
    r"-?\d{1,3}(?:\.\d{1,6})?,-?\d{1,2}(?:\.\d{1,6})?,"
    r"-?\d{1,3}(?:\.\d{1,6})?,-?\d{1,2}(?:\.\d{1,6})?\Z"
)
ALLOWED_SOURCES = {
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "VIIRS_SNPP_NRT",
}
HOST = "firms.modaps.eosdis.nasa.gov"


def validate_bbox(raw: str) -> str:
    text = raw.strip()
    if not BBOX_RE.fullmatch(text):
        raise ValueError("Invalid FIRMS bounds")
    west, south, east, north = [float(value) for value in text.split(",")]
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Invalid FIRMS bounds")
    if east - west > 60.0001 or north - south > 40.0001:
        raise ValueError("FIRMS bounds too wide")
    return text


def request_url(source: str, bbox: str, days: str, key: str) -> str:
    if source not in ALLOWED_SOURCES:
        raise ValueError("Unsupported FIRMS source")
    if days != "1":
        raise ValueError("Only one-day FIRMS requests are allowed")
    if not KEY_RE.fullmatch(key):
        raise ValueError("Invalid FIRMS MAP_KEY")
    area = validate_bbox(bbox)
    return (
        "https://" + HOST + "/api/area/csv/"
        + key + "/" + source + "/" + area + "/" + days
    )


class FirmsOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected FIRMS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        return 2

    key = os.environ.get("POST_APOLLO_FIRMS_MAP_KEY", "").strip()
    try:
        endpoint = request_url(argv[1], argv[2], argv[3], key)
        request = Request(
            endpoint,
            headers={
                "User-Agent": "Post-Apollo-WeatherStation/0.3",
                "Accept": "text/csv",
            },
        )
        opener = build_opener(FirmsOnlyRedirects())
        with opener.open(request, timeout=15) as response:
            actual = urlsplit(response.geturl())
            if actual.scheme != "https" or actual.hostname != HOST:
                raise ValueError("Unexpected FIRMS response host")
            payload = response.read(4 * 1024 * 1024 + 1)
            if len(payload) > 4 * 1024 * 1024:
                raise ValueError("FIRMS response too large")
        sys.stdout.buffer.write(payload)
        return 0
    except (HTTPError, URLError, OSError, ValueError):
        # Do not print exceptions: urllib errors may contain the secret URL.
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
