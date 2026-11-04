#!/usr/bin/env python3
"""Opt-in visible-viewport street raster tiles, never a provider-coverage feed.

OSMF standard tile policy: identifiable User-Agent, © OpenStreetMap attribution
in the UI, conditional requests + expiry metadata, no prefetch/offline archive,
one currently viewed viewport only, no person/company fields in requests.
OSMF standard server is best-effort, not a commercial-production SLA.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://tile.openstreetmap.org"
USER_AGENT = "Post-Apollo-CompanyNetwork/0.1 (+https://github.com/kudokudo1/The-Post-Apollo-Project)"
DEFAULT_TTL = 7 * 86400
MAX_BODY = 1_200_000
MAX_TILES = 96
MAX_NETWORK = 32
MAX_ZOOM = 17
MIN_ZOOM = 3
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class TileError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def safe_cache_root(create=False):
    base = os.environ.get("XDG_CACHE_HOME", "")
    parent = Path(base) if base else Path.home() / ".cache"
    if not parent.is_absolute() or ".." in parent.parts:
        raise TileError("UNSAFE_CACHE_ROOT")
    if not parent.exists() or parent.is_symlink() or not parent.is_dir():
        raise TileError("UNSAFE_CACHE_ROOT")
    root = parent / "post-apollo-company-streets"
    if not root.exists() and not root.is_symlink():
        if not create:
            return None
        root.mkdir(mode=0o700)
    st = root.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise TileError("UNSAFE_CACHE_DIRECTORY")
    return root


def require_file(path):
    if not path.exists() and not path.is_symlink():
        return False
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise TileError("UNSAFE_CACHE_FILE")
    return True


def atomic_bytes(path, payload):
    fd, temp = tempfile.mkstemp(prefix=".tile-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if fd >= 0:
            os.close(fd)
        if os.path.exists(temp):
            os.unlink(temp)


def clamp(value, low, high):
    return max(low, min(high, value))


def world(lon, lat, zoom):
    scale = 256 * 2 ** zoom
    sin = math.sin(math.radians(clamp(lat, -85.05112878, 85.05112878)))
    x = clamp((lon + 180) / 360, 0, 1) * scale
    y = clamp(0.5 - math.log((1 + sin) / (1 - sin)) / (4 * math.pi), 0, 1) * scale
    return x, y


def validate_request(request):
    if type(request) is not dict or set(request) != {
        "enable", "lon", "lat", "zoom", "width", "height"
    }:
        raise TileError("INVALID_REQUEST")
    if request["enable"] is not True:
        raise TileError("CONSENT_REQUIRED")
    lon, lat = request["lon"], request["lat"]
    z, w, h = request["zoom"], request["width"], request["height"]
    if (type(lon) not in (int, float) or type(lat) not in (int, float)
            or not math.isfinite(lon) or not math.isfinite(lat)
            or not -180 <= lon <= 180 or not -85.05112878 <= lat <= 85.05112878
            or type(z) is not int or not MIN_ZOOM <= z <= MAX_ZOOM
            or type(w) is not int or type(h) is not int
            or not 100 <= w <= 2700 or not 100 <= h <= 1600):
        raise TileError("INVALID_REQUEST")
    return float(lon), float(lat), z, w, h


def visible_tiles(lon, lat, zoom, width, height):
    cx, cy = world(lon, lat, zoom)
    count = 2 ** zoom
    xmin = max(0, math.floor((cx-width/2)/256))
    xmax = min(count-1, math.floor((cx+width/2-0.0001)/256))
    ymin = max(0, math.floor((cy-height/2)/256))
    ymax = min(count-1, math.floor((cy+height/2-0.0001)/256))
    rows = [(zoom, x, y) for y in range(ymin, ymax+1)
            for x in range(xmin, xmax+1)]
    if len(rows) > MAX_TILES:
        raise TileError("VIEWPORT_TOO_LARGE")
    # Only tile rectangles intersecting the currently visible viewport.
    rows.sort(key=lambda t: (t[1]*256+128-cx)**2+(t[2]*256+128-cy)**2)
    return rows


def tile_paths(root, z, x, y):
    key = f"{z}-{x}-{y}"
    return root / f"{key}.png", root / f"{key}.json"


def metadata(meta):
    if require_file(meta):
        try:
            with meta.open("rb") as file:
                raw = file.read(5120)
            data = json.loads(raw)
            if type(data) is dict:
                return data
        except (OSError, ValueError, UnicodeError):
            return {}
    return {}


def expiry(headers):
    control = headers.get("Cache-Control", "")
    match = re.search(r"(?:^|,)\s*max-age=(\d+)", control, re.I)
    if match:
        return time.time() + clamp(int(match.group(1)), 0, 30*86400)
    expires = headers.get("Expires", "")
    if expires:
        try:
            at = parsedate_to_datetime(expires)
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            return max(time.time(), at.timestamp())
        except (ValueError, TypeError, OverflowError):
            pass
    return time.time() + DEFAULT_TTL


def cached(path, meta, now=None):
    if not require_file(path):
        return False
    data = metadata(meta)
    now = time.time() if now is None else now
    if type(data.get("expires")) in (int,float):
        return data["expires"] > now
    # Older cache entries without usable HTTP metadata are held ≥7 days.
    return path.stat().st_mtime + DEFAULT_TTL > now


def fetch_one(root, tile):
    z, x, y = tile
    path, meta_path = tile_paths(root, z, x, y)
    if cached(path, meta_path):
        return {"z":z, "x":x, "y":y, "path":str(path)}
    old = metadata(meta_path)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/png",
    }
    if type(old.get("etag")) is str and old["etag"]:
        headers["If-None-Match"] = old["etag"]
    if type(old.get("lastModified")) is str and old["lastModified"]:
        headers["If-Modified-Since"] = old["lastModified"]
    url = f"{BASE}/{z}/{x}/{y}.png"
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=5) as response:
            body = response.read(MAX_BODY+1)
            if len(body) > MAX_BODY or not body.startswith(PNG_SIGNATURE):
                raise TileError("INVALID_TILE")
            if "image/png" not in response.headers.get("Content-Type", ""):
                raise TileError("INVALID_TILE")
            atomic_bytes(path, body)
            info = {
                "expires": expiry(response.headers),
                "etag": response.headers.get("ETag", ""),
                "lastModified": response.headers.get("Last-Modified", "")
            }
            atomic_bytes(meta_path, json.dumps(info, separators=(",", ":")).encode())
    except HTTPError as err:
        if err.code == 304 and require_file(path):
            info = {
                "expires": expiry(err.headers),
                "etag": err.headers.get("ETag", old.get("etag", "")),
                "lastModified": err.headers.get("Last-Modified",
                                                old.get("lastModified", ""))
            }
            atomic_bytes(meta_path, json.dumps(info, separators=(",", ":")).encode())
        elif err.code == 429:
            return None  # Respect provider throttling; no retry loop.
        else:
            return None
    except (URLError, OSError, TileError, TimeoutError):
        return None
    return {"z":z, "x":x, "y":y, "path":str(path)}


def run(request):
    lon, lat, zoom, width, height = validate_request(request)
    tiles = visible_tiles(lon, lat, zoom, width, height)
    root = safe_cache_root(create=True)
    results = []
    to_fetch = []
    for tile in tiles:
        path, meta_path = tile_paths(root, *tile)
        if cached(path, meta_path):
            results.append({"z":tile[0], "x":tile[1], "y":tile[2], "path":str(path)})
        else:
            to_fetch.append(tile)
    allowed = to_fetch[:MAX_NETWORK]
    if allowed:
        # No speculative requests: all tiles touch the current viewport.
        with ThreadPoolExecutor(max_workers=3) as pool:
            for item in pool.map(lambda tile: fetch_one(root, tile), allowed):
                if item is not None:
                    results.append(item)
    return {"ok":True,"source":"© OpenStreetMap contributors",
            "tiles":results, "visibleCount":len(tiles),
            "loadedCount":len(results),
            "partial":len(results)<len(tiles)}


def main():
    try:
        payload = sys.stdin.buffer.readline(2049)
        if not payload or len(payload)>2048 or not payload.endswith(b"\n"):
            raise TileError("INVALID_REQUEST")
        request = json.loads(payload)
        answer = run(request)
        print(json.dumps(answer, separators=(",", ":")))
        return 0
    except TileError as err:
        print(json.dumps({"ok":False,"error":err.code}))
        return 2
    except (OSError, TypeError, ValueError, OverflowError):
        print(json.dumps({"ok":False,"error":"TILES_UNAVAILABLE"}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
