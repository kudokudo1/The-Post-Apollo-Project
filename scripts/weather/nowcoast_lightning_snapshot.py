#!/usr/bin/env python3
"""Discover NOAA nowCOAST lightning WMS and emit one bounded local snapshot URL.

The helper intentionally does not decode raw contractor lightning detections.
It discovers NOAA's public Level-5 lightning-density WMS layer from the
capabilities document, selects the latest advertised time when available, and
emits JSON describing a GetMap request centered on the supplied weather fix.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import sys
import xml.etree.ElementTree as ET
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "nowcoast.noaa.gov"
SERVICE = (
    "https://" + HOST
    + "/geoserver/observations/lightning_detection/ows"
)
CAPABILITIES_URL = SERVICE + "?" + urlencode({
    "SERVICE": "WMS",
    "VERSION": "1.3.0",
    "REQUEST": "GetCapabilities",
})
MAX_BYTES = 2 * 1024 * 1024
DEFAULT_RADIUS_KM = 320.0
DEFAULT_WIDTH = 760
DEFAULT_HEIGHT = 260


class NowcoastOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected nowCOAST redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def local_name(tag: str) -> str:
    return str(tag).rsplit("}", 1)[-1]


def text_of_child(node: ET.Element, name: str) -> str:
    for child in node:
        if local_name(child.tag) == name:
            return str(child.text or "").strip()
    return ""


def validate_coordinate(value, minimum: float, maximum: float, label: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not minimum <= number <= maximum:
        raise ValueError(f"Invalid {label}")
    return number


def layer_candidates(root: ET.Element):
    rows = []
    for node in root.iter():
        if local_name(node.tag) != "Layer":
            continue
        name = text_of_child(node, "Name")
        if not name:
            continue
        title = text_of_child(node, "Title")
        compact = (name + " " + title).lower()
        score = 0
        if "lightning" in compact:
            score += 20
        if "density" in compact:
            score += 10
        if "strike" in compact:
            score += 4
        if "15" in compact:
            score += 1
        rows.append({
            "name": name,
            "title": title or name,
            "score": score,
            "node": node,
        })
    rows.sort(key=lambda row: (-row["score"], row["name"]))
    return rows


def select_lightning_layer(root: ET.Element):
    rows = layer_candidates(root)
    for row in rows:
        if row["score"] >= 20:
            return row
    raise ValueError("Lightning-density WMS layer missing")


def time_dimension_text(layer: ET.Element) -> tuple[str, str]:
    for node in layer.iter():
        if local_name(node.tag) not in {"Dimension", "Extent"}:
            continue
        if str(node.attrib.get("name", "")).strip().lower() != "time":
            continue
        return (
            str(node.text or "").strip(),
            str(node.attrib.get("default", "")).strip(),
        )
    return "", ""


def latest_time_value(raw: str, default: str = "") -> str:
    preferred = str(default or "").strip()
    if preferred and preferred.lower() != "current":
        return preferred

    text = str(raw or "").strip()
    if not text:
        return ""

    # GeoServer commonly advertises comma-separated instants or an ISO
    # start/end/period interval. Use the latest explicit instant when possible.
    if "," in text:
        tokens = [token.strip() for token in text.split(",") if token.strip()]
        return tokens[-1] if tokens else ""

    pieces = [piece.strip() for piece in text.split("/") if piece.strip()]
    if len(pieces) >= 2:
        end = pieces[1]
        return "" if end.lower() == "current" else end

    return "" if text.lower() == "current" else text


def bounded_box(latitude: float, longitude: float, radius_km: float):
    radius = float(radius_km)
    if not math.isfinite(radius) or radius < 50 or radius > 900:
        raise ValueError("Invalid snapshot radius")

    lat_span = radius / 111.0
    cosine = max(0.2, math.cos(math.radians(latitude)))
    lon_span = radius / (111.0 * cosine)

    south = max(-25.0, latitude - lat_span)
    north = min(80.0, latitude + lat_span)
    west = max(-180.0, longitude - lon_span)
    east = min(0.0, longitude + lon_span)
    if not west < east or not south < north:
        raise ValueError("Weather fix outside nowCOAST lightning domain")
    return {
        "west": west,
        "south": south,
        "east": east,
        "north": north,
    }


def build_map_url(layer_name: str, bbox: dict, width: int, height: int,
                  latest_time: str = "") -> str:
    safe_width = int(width)
    safe_height = int(height)
    if not 128 <= safe_width <= 1600 or not 128 <= safe_height <= 1200:
        raise ValueError("Invalid snapshot dimensions")

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetMap",
        "LAYERS": layer_name,
        "STYLES": "",
        "SRS": "EPSG:4326",
        "BBOX": ",".join(
            f"{bbox[key]:.5f}"
            for key in ("west", "south", "east", "north")
        ),
        "WIDTH": str(safe_width),
        "HEIGHT": str(safe_height),
        "FORMAT": "image/png",
        "TRANSPARENT": "true",
    }
    if latest_time:
        params["TIME"] = latest_time
    return SERVICE + "?" + urlencode(params)


def fetch_capabilities() -> bytes:
    opener = build_opener(NowcoastOnlyRedirects())
    request = Request(
        CAPABILITIES_URL,
        headers={
            "User-Agent": "Post-Apollo-WeatherStation/0.8",
            "Accept": "application/xml,text/xml",
        },
    )
    with opener.open(request, timeout=15) as response:
        actual = urlsplit(response.geturl())
        if actual.scheme != "https" or actual.hostname != HOST:
            raise ValueError("Unexpected nowCOAST response host")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("nowCOAST capabilities too large")
        return payload


def build_snapshot(capabilities: bytes, latitude: float, longitude: float,
                   radius_km: float = DEFAULT_RADIUS_KM,
                   width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
    root = ET.fromstring(capabilities)
    layer = select_lightning_layer(root)
    raw_time, default_time = time_dimension_text(layer["node"])
    latest = latest_time_value(raw_time, default_time)
    bbox = bounded_box(latitude, longitude, radius_km)
    image_url = build_map_url(layer["name"], bbox, width, height, latest)
    return {
        "source": "NOAA nowCOAST",
        "product": "LIGHTNING STRIKE DENSITY",
        "layer": layer["name"],
        "layerTitle": layer["title"],
        "latestTime": latest or "LATEST",
        "windowMinutes": 15,
        "resolutionKm": 8,
        "radiusKm": radius_km,
        "bbox": bbox,
        "imageUrl": image_url,
        "generatedUtc": datetime.now(timezone.utc).isoformat()
            .replace("+00:00", "Z"),
    }


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        sys.stdout.write('{"error":"NOWCOAST LIGHTNING LOCATION REQUIRED"}')
        return 2

    try:
        latitude = validate_coordinate(args[0], -90, 90, "latitude")
        longitude = validate_coordinate(args[1], -180, 180, "longitude")
        snapshot = build_snapshot(
            fetch_capabilities(), latitude, longitude
        )
        sys.stdout.write(json.dumps(snapshot, separators=(",", ":")))
        return 0
    except (ValueError, ET.ParseError, HTTPError, URLError, OSError):
        sys.stdout.write('{"error":"NOWCOAST LIGHTNING UNAVAILABLE"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
