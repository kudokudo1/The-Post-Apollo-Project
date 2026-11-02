#!/usr/bin/env python3
"""Bounded durable frame cache for Weather Station volatile imagery.

This is operational fallback, not history. It stores only the latest short-lived
frame/tile set for approved Weather providers and refuses arbitrary URLs/paths.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import os
import re
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SCHEMA = "post-apollo.weather-frame-cache.v1"
VERSION = 1
MAX_IMAGE_BYTES = 16 * 1024 * 1024
MAX_METADATA_BYTES = 256 * 1024
MAX_TILE_FILES = 12
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

SOURCES = {
    "lightning": {"kind": "single", "max_age_ms": 2 * 60 * 60 * 1000},
    "mrms-radar": {"kind": "single", "max_age_ms": 2 * 60 * 60 * 1000},
    "rainviewer": {"kind": "tiles", "max_age_ms": 2 * 60 * 60 * 1000},
}

def safe_text(value, maximum=256):
    text = str(value if value is not None else "")
    if any(ord(ch) < 32 for ch in text):
        raise ValueError("CONTROL_CHARACTER")
    return text[:maximum]

def positive_millis(value, allow_zero=False):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("INVALID_TIME")
    integer = int(number)
    if integer < 0 or (integer == 0 and not allow_zero):
        raise ValueError("INVALID_TIME")
    return integer

def cache_root(value):
    path = Path(str(value)).expanduser()
    if not path.is_absolute() or path.name != "weather-frame-cache-v1":
        raise ValueError("WEATHER_FRAME_CACHE_ROOT_REQUIRED")
    return path

def source_dir(root, source_id):
    if source_id not in SOURCES:
        raise ValueError("UNKNOWN_SOURCE")
    directory = cache_root(root) / source_id
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass
    return directory

def allowed_url(source_id, value):
    url = safe_text(value, 4096)
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        return False
    host = parts.hostname.lower()
    path = parts.path

    if source_id == "lightning":
        return (
            host == "nowcoast.noaa.gov"
            and path == "/geoserver/observations/lightning_detection/ows"
        )
    if source_id == "mrms-radar":
        return (
            host == "mapservices.weather.noaa.gov"
            and path == (
                "/eventdriven/rest/services/radar/"
                "radar_base_reflectivity_time/ImageServer/exportImage"
            )
        )
    if source_id == "rainviewer":
        return (
            re.fullmatch(r"(?:[a-z0-9-]+\.)*rainviewer\.com", host) is not None
            and re.fullmatch(
                r"/v\d+/radar/\d+/512/[1-7]/\d+/\d+/2/1_1\.png",
                path,
            ) is not None
        )
    return False

class RestrictedRedirects(HTTPRedirectHandler):
    def __init__(self, source_id):
        super().__init__()
        self.source_id = source_id

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_url(self.source_id, newurl):
            raise ValueError("UNSAFE_REDIRECT")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch_png(source_id, url):
    if not allowed_url(source_id, url):
        raise ValueError("UNSAFE_URL")
    opener = build_opener(RestrictedRedirects(source_id))
    request = Request(
        url,
        headers={
            "User-Agent": "Post-Apollo-WeatherStation/0.9",
            "Accept": "image/png,image/*;q=0.8",
        },
    )
    with opener.open(request, timeout=20) as response:
        actual = response.geturl()
        if not allowed_url(source_id, actual):
            raise ValueError("UNSAFE_RESPONSE_URL")
        payload = response.read(MAX_IMAGE_BYTES + 1)
        if len(payload) > MAX_IMAGE_BYTES:
            raise ValueError("FRAME_TOO_LARGE")
        if not payload.startswith(PNG_SIGNATURE):
            raise ValueError("FRAME_NOT_PNG")
        return payload

def atomic_bytes(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".frame-", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)

def atomic_json(path, value):
    raw = (json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n").encode()
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError("METADATA_TOO_LARGE")
    atomic_bytes(path, raw)

def file_url(path):
    return path.resolve().as_uri()

def frame_filename(received_at_ms):
    return f"frame-{int(received_at_ms)}.png"

def read_json(path):
    payload = path.read_bytes()
    if len(payload) > MAX_METADATA_BYTES:
        raise ValueError("METADATA_TOO_LARGE")
    value = json.loads(payload.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("INVALID_METADATA")
    return value

def validate_metadata_common(value, source_id, max_age_ms):
    if value.get("schema") != SCHEMA or int(value.get("version", 0)) != VERSION:
        raise ValueError("INVALID_SCHEMA")
    if value.get("sourceId") != source_id:
        raise ValueError("SOURCE_MISMATCH")
    received = positive_millis(value.get("receivedAtMs"))
    age = max(0, int(time.time() * 1000) - received)
    source_limit = SOURCES[source_id]["max_age_ms"]
    requested_limit = int(max_age_ms)
    effective_limit = min(source_limit, requested_limit)
    if effective_limit <= 0 or age > effective_limit:
        raise ValueError("CACHE_EXPIRED")
    return received

def bounded_context(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("INVALID_CONTEXT")
    raw = json.dumps(value, separators=(",", ":"))
    if len(raw.encode()) > 32768:
        raise ValueError("CONTEXT_TOO_LARGE")
    return json.loads(raw)

def cleanup_files(directory, keep):
    for path in directory.glob("*.png"):
        if path.name not in keep:
            path.unlink(missing_ok=True)

def store_single_frame(source_id, root, scope_key, remote_url, observed_at_ms, context):
    spec = SOURCES.get(source_id)
    if not spec or spec["kind"] != "single":
        raise ValueError("SINGLE_SOURCE_REQUIRED")
    scope = safe_text(scope_key, 256)
    if not scope:
        raise ValueError("SCOPE_REQUIRED")
    observed = positive_millis(observed_at_ms, allow_zero=True)
    directory = source_dir(root, source_id)
    payload = fetch_png(source_id, remote_url)
    received = int(time.time() * 1000)
    filename = frame_filename(received)
    frame_path = directory / filename
    atomic_bytes(frame_path, payload)
    metadata = {
        "schema": SCHEMA,
        "version": VERSION,
        "sourceId": source_id,
        "scopeKey": scope,
        "receivedAtMs": received,
        "observedAtMs": observed,
        "frameFile": filename,
        "context": bounded_context(context),
    }
    try:
        atomic_json(directory / "metadata.json", metadata)
    except Exception:
        frame_path.unlink(missing_ok=True)
        raise
    cleanup_files(directory, {filename})
    return {
        "ok": True,
        "sourceId": source_id,
        "scopeKey": scope,
        "receivedAtMs": received,
        "observedAtMs": observed,
        "fileUrl": file_url(frame_path),
        "context": metadata["context"],
    }

def load_single_frame(source_id, root, scope_key, max_age_ms):
    spec = SOURCES.get(source_id)
    if not spec or spec.kind != "single":
        raise ValueError("SINGLE_SOURCE_REQUIRED")
    scope = safe_text(scope_key, 256)
    directory = source_dir(root, source_id)
    metadata = read_json(directory / "metadata.json")
    received = validate_metadata_common(metadata, source_id, max_age_ms)
    if safe_text(metadata.get("scopeKey"), 256) != scope:
        raise ValueError("SCOPE_MISMATCH")
    filename = safe_text(metadata.get("frameFile"), 128)
    if not re.fullmatch(r"frame-\d+\.png", filename):
        raise ValueError("INVALID_FRAME_FILE")
    frame_path = directory / filename
    if frame_path.is_symlink():
        raise ValueError("FRAME_SYMLINK")
    payload = frame_path.read_bytes()
    if len(payload) > MAX_IMAGE_BYTES or not payload.startswith(PNG_SIGNATURE):
        raise ValueError("INVALID_FRAME_BYTES")
    return {
        "ok": True,
        "sourceId": source_id,
        "scopeKey": scope,
        "receivedAtMs": received,
        "observedAtMs": positive_millis(
            metadata.get("observedAtMs", 0), allow_zero=True
        ),
        "fileUrl": file_url(frame_path),
        "context": bounded_context(metadata.get("context")),
    }

def sanitize_strips(value):
    if not isinstance(value, list) or not value or len(value) > 96:
        raise ValueError("INVALID_STRIPS")
    out = []
    unique = {}
    for row in value:
        if not isinstance(row, dict):
            raise ValueError("INVALID_STRIP")
        tile_key = safe_text(row.get("tileKey"), 64)
        url = safe_text(row.get("url"), 4096)
        if not tile_key or not allowed_url("rainviewer", url):
            raise ValueError("INVALID_TILE")
        if tile_key not in unique:
            unique[tile_key] = url
        for key in ("west", "east", "north", "south", "sourceY",
                    "sourceHeight", "sourceSize"):
            number = float(row.get(key))
            if not math.isfinite(number):
                raise ValueError("INVALID_STRIP_GEOMETRY")
        out.append({
            "tileKey": tile_key,
            "url": url,
            "west": float(row["west"]),
            "east": float(row["east"]),
            "north": float(row["north"]),
            "south": float(row["south"]),
            "sourceY": float(row["sourceY"]),
            "sourceHeight": float(row["sourceHeight"]),
            "sourceSize": float(row["sourceSize"]),
        })
    if len(unique) > MAX_TILE_FILES:
        raise ValueError("TOO_MANY_TILES")
    return out, unique

def store_tile_set(source_id, root, scope_key, observed_at_ms, context, strips):
    spec = SOURCES.get(source_id)
    if not spec or spec["kind"] != "tiles" or source_id != "rainviewer":
        raise ValueError("TILE_SOURCE_REQUIRED")
    scope = safe_text(scope_key, 256)
    if not scope:
        raise ValueError("SCOPE_REQUIRED")
    observed = positive_millis(observed_at_ms, allow_zero=True)
    clean_strips, unique = sanitize_strips(strips)
    directory = source_dir(root, source_id)
    received = int(time.time() * 1000)

    local_urls = {}
    keep = set()
    created = []
    try:
        for tile_key, remote_url in unique.items():
            digest = hashlib.sha256(
                (tile_key + "|" + remote_url).encode()
            ).hexdigest()[:20]
            filename = f"tile-{received}-{digest}.png"
            frame_path = directory / filename
            atomic_bytes(frame_path, fetch_png(source_id, remote_url))
            local_urls[tile_key] = file_url(frame_path)
            keep.add(filename)
            created.append(frame_path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise

    local_strips = []
    for row in clean_strips:
        copy = dict(row)
        copy["url"] = local_urls[row["tileKey"]]
        local_strips.append(copy)

    metadata = {
        "schema": SCHEMA,
        "version": VERSION,
        "sourceId": source_id,
        "scopeKey": scope,
        "receivedAtMs": received,
        "observedAtMs": observed,
        "context": bounded_context(context),
        "strips": local_strips,
        "frameFiles": sorted(keep),
    }
    try:
        atomic_json(directory / "metadata.json", metadata)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    cleanup_files(directory, keep)
    return {
        "ok": True,
        "sourceId": source_id,
        "scopeKey": scope,
        "receivedAtMs": received,
        "observedAtMs": observed,
        "context": metadata["context"],
        "strips": local_strips,
    }

def load_tile_set(source_id, root, max_age_ms):
    spec = SOURCES.get(source_id)
    if not spec or spec["kind"] != "tiles":
        raise ValueError("TILE_SOURCE_REQUIRED")
    directory = source_dir(root, source_id)
    metadata = read_json(directory / "metadata.json")
    received = validate_metadata_common(metadata, source_id, max_age_ms)
    scope = safe_text(metadata.get("scopeKey"), 256)
    if source_id == "rainviewer" and scope != "manual-radar":
        raise ValueError("SCOPE_MISMATCH")
    strips = metadata.get("strips")
    if not isinstance(strips, list) or not strips or len(strips) > 96:
        raise ValueError("INVALID_STRIPS")
    validated = []
    for row in strips:
        if not isinstance(row, dict):
            raise ValueError("INVALID_STRIP")
        url = safe_text(row.get("url"), 4096)
        parts = urlsplit(url)
        if parts.scheme != "file":
            raise ValueError("NONLOCAL_TILE")
        path = Path(unquote(parts.path))
        if path.parent != directory or not path.name.startswith("tile-"):
            raise ValueError("TILE_PATH_ESCAPE")
        if path.is_symlink():
            raise ValueError("TILE_SYMLINK")
        payload = path.read_bytes()
        if len(payload) > MAX_IMAGE_BYTES or not payload.startswith(PNG_SIGNATURE):
            raise ValueError("INVALID_TILE_BYTES")
        copy = dict(row)
        copy["url"] = file_url(path)
        validated.append(copy)
    return {
        "ok": True,
        "sourceId": source_id,
        "scopeKey": scope,
        "receivedAtMs": received,
        "observedAtMs": positive_millis(
            metadata.get("observedAtMs", 0), allow_zero=True
        ),
        "context": bounded_context(metadata.get("context")),
        "strips": validated,
    }

def emit(value):
    sys.stdout.write(json.dumps(value, separators=(",", ":")))

def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if not args:
            raise ValueError("COMMAND_REQUIRED")
        command = args.pop(0)

        if command == "load-single" and len(args) == 4:
            source_id, root, scope_key, max_age = args
            emit(load_single_frame(source_id, root, scope_key, int(max_age)))
            return 0

        if command == "fetch-single" and len(args) == 6:
            source_id, root, scope_key, url, observed_ms, context_json = args
            context = json.loads(context_json)
            emit(store_single_frame(
                source_id, root, scope_key, url,
                int(observed_ms), context
            ))
            return 0

        if command == "load-tiles" and len(args) == 3:
            source_id, root, max_age = args
            emit(load_tile_set(source_id, root, int(max_age)))
            return 0

        if command == "fetch-tiles" and len(args) == 6:
            source_id, root, scope_key, observed_ms, context_json, strips_json = args
            emit(store_tile_set(
                source_id, root, scope_key, int(observed_ms),
                json.loads(context_json), json.loads(strips_json)
            ))
            return 0

        raise ValueError("INVALID_ARGUMENTS")
    except (ValueError, OSError, HTTPError, URLError, json.JSONDecodeError):
        emit({"ok": False, "error": "WEATHER FRAME CACHE UNAVAILABLE"})
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
