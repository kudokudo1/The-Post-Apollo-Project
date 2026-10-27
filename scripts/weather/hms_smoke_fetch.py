#!/usr/bin/env python3
"""Fetch and normalize the latest available NOAA HMS smoke KML product.

The helper tries the current UTC day and a bounded recent lookback because the
daily analyst product can be finalized after the nominal observation date.
It emits JSON only. No shell interpolation or third-party provider is used.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "satepsanone.nesdis.noaa.gov"
BASE = "https://" + HOST + "/pub/FIRE/web/HMS/Smoke_Polygons/KML"
MAX_BYTES = 8 * 1024 * 1024
LOOKBACK_DAYS = 7
MAX_POLYGONS = 1200
MAX_VERTICES = 200_000


class HmsOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected HMS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def candidate_urls(now: datetime, lookback: int = LOOKBACK_DAYS):
    current = now.astimezone(timezone.utc)
    for offset in range(max(0, int(lookback)) + 1):
        day = current.date() - timedelta(days=offset)
        ymd = day.strftime("%Y%m%d")
        yield (
            day,
            f"{BASE}/{day:%Y}/{day:%m}/hms_smoke{ymd}.kml",
        )


def normalize_density(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {"heavy", "21"}:
        return "heavy"
    if value in {"medium", "16"}:
        return "medium"
    if value in {"light", "5"}:
        return "light"
    return "unknown"


def description_fields(raw: str) -> dict[str, str]:
    plain = html.unescape(re.sub(r"<[^>]*>", " ", str(raw or "")))
    plain = re.sub(r"\s+", " ", plain).strip()
    result: dict[str, str] = {}
    keys = ("Satellite", "Start", "End", "Density")
    for key in keys:
        pattern = (
            rf"\b{key}\b\s*[:=]?\s*(.*?)"
            rf"(?=\s+\b(?:Satellite|Start|End|Density)\b\s*[:=]?|$)"
        )
        match = re.search(pattern, plain, flags=re.IGNORECASE)
        if match:
            result[key.lower()] = match.group(1).strip(" :;|")
    return result


def placemark_fields(placemark: ET.Element) -> dict[str, str]:
    fields: dict[str, str] = {}
    for node in placemark.iter():
        name = local_name(node.tag)
        if name == "Data":
            key = str(node.attrib.get("name", "")).strip().lower()
            value = ""
            for child in node:
                if local_name(child.tag) == "value":
                    value = child.text or ""
                    break
            if key:
                fields[key] = str(value).strip()
        elif name == "SimpleData":
            key = str(node.attrib.get("name", "")).strip().lower()
            if key:
                fields[key] = str(node.text or "").strip()
        elif name == "description":
            for key, value in description_fields(node.text or "").items():
                fields.setdefault(key, value)
    return fields


def parse_coordinates(raw: str):
    points = []
    for token in re.split(r"\s+", str(raw or "").strip()):
        if not token:
            continue
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        points.append([lon, lat])
    if len(points) < 3:
        return []
    if points[0] != points[-1]:
        points.append(points[0][:])
    return points


def outer_rings(polygon: ET.Element):
    rings = []
    for outer in polygon.iter():
        if local_name(outer.tag) != "outerBoundaryIs":
            continue
        for node in outer.iter():
            if local_name(node.tag) == "coordinates":
                ring = parse_coordinates(node.text or "")
                if ring:
                    rings.append(ring)
                break
    if rings:
        return rings

    # Defensive fallback for KML producers that omit the outerBoundary wrapper.
    for node in polygon.iter():
        if local_name(node.tag) == "coordinates":
            ring = parse_coordinates(node.text or "")
            if ring:
                rings.append(ring)
                break
    return rings


def parse_kml(raw: bytes, analysis_date: str):
    root = ET.fromstring(raw)
    polygons = []
    total_vertices = 0
    truncated = False
    serial = 0

    for placemark in root.iter():
        if local_name(placemark.tag) != "Placemark":
            continue
        fields = placemark_fields(placemark)
        density = normalize_density(fields.get("density", ""))
        satellite = fields.get("satellite", "").strip()[:120]
        start = fields.get("start", "").strip()[:80]
        end = fields.get("end", "").strip()[:80]

        for polygon in placemark.iter():
            if local_name(polygon.tag) != "Polygon":
                continue
            for ring in outer_rings(polygon):
                if len(polygons) >= MAX_POLYGONS or total_vertices + len(ring) > MAX_VERTICES:
                    truncated = True
                    break
                serial += 1
                polygons.append({
                    "id": f"hms-{analysis_date}-{serial}",
                    "density": density,
                    "satellite": satellite or "NOT LISTED",
                    "start": start,
                    "end": end,
                    "ring": ring,
                })
                total_vertices += len(ring)
            if truncated:
                break
        if truncated:
            break

    return {
        "analysisDate": analysis_date,
        "polygons": polygons,
        "polygonCount": len(polygons),
        "vertexCount": total_vertices,
        "truncated": truncated,
    }


def fetch_latest(now: datetime):
    opener = build_opener(HmsOnlyRedirects())
    for day, url in candidate_urls(now):
        request = Request(
            url,
            headers={
                "User-Agent": "Post-Apollo-WeatherStation/0.4",
                "Accept": "application/vnd.google-earth.kml+xml,application/xml,text/xml",
            },
        )
        try:
            with opener.open(request, timeout=15) as response:
                actual = urlsplit(response.geturl())
                if actual.scheme != "https" or actual.hostname != HOST:
                    raise ValueError("Unexpected HMS response host")
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise ValueError("HMS response too large")
            result = parse_kml(payload, day.strftime("%Y%m%d"))
            result["source"] = "NOAA HMS"
            result["ageDays"] = (now.astimezone(timezone.utc).date() - day).days
            return result
        except HTTPError as error:
            if error.code == 404:
                continue
        except (URLError, OSError, ValueError, ET.ParseError):
            continue
    raise RuntimeError("HMS smoke unavailable")


def main() -> int:
    try:
        result = fetch_latest(datetime.now(timezone.utc))
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception:
        # Keep provider/network detail out of UI; service retains last-good data.
        sys.stdout.write('{"error":"HMS SMOKE UNAVAILABLE"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
