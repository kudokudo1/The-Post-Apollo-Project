#!/usr/bin/env python3
"""Weather M8 short-lived volatile frame cache contracts."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/weather_frame_cache.py"

spec = importlib.util.spec_from_file_location("weather_frame_cache", HELPER)
assert spec and spec.loader
frame = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frame)

PNG = frame.PNG_SIGNATURE + b"post-apollo-test-png"

assert frame.allowed_url(
    "lightning",
    "https://nowcoast.noaa.gov/geoserver/observations/"
    "lightning_detection/ows?SERVICE=WMS&REQUEST=GetMap",
)
assert not frame.allowed_url(
    "lightning",
    "https://evil.example/geoserver/observations/lightning_detection/ows",
)
assert frame.allowed_url(
    "mrms-radar",
    "https://mapservices.weather.noaa.gov/eventdriven/rest/services/"
    "radar/radar_base_reflectivity_time/ImageServer/exportImage?f=image",
)
assert not frame.allowed_url(
    "mrms-radar",
    "https://mapservices.weather.noaa.gov/other/exportImage?f=image",
)
assert frame.allowed_url(
    "rainviewer",
    "https://tilecache.rainviewer.com/v2/radar/1793462400/"
    "512/4/2/3/2/1_1.png",
)
assert not frame.allowed_url(
    "rainviewer",
    "https://evilrainviewer.com/v2/radar/1793462400/512/4/2/3/2/1_1.png",
)

original_fetch = frame.fetch_png
frame.fetch_png = lambda source_id, url: PNG

with tempfile.TemporaryDirectory(prefix="post-apollo-m8-") as temp:
    cache_root = Path(temp) / "weather-frame-cache-v1"

    lightning_url = (
        "https://nowcoast.noaa.gov/geoserver/observations/"
        "lightning_detection/ows?SERVICE=WMS&REQUEST=GetMap"
    )
    lightning = frame.store_single_frame(
        "lightning",
        cache_root,
        "38.900|-76.900",
        lightning_url,
        1793462400000,
        {
            "bbox": {
                "west": -80,
                "south": 35,
                "east": -73,
                "north": 42,
            },
            "latestTime": "2026-11-02T10:00:00Z",
            "windowMinutes": 15,
            "resolutionKm": 8,
        },
    )
    assert lightning["ok"] is True
    assert lightning["fileUrl"].startswith("file:")
    assert Path(lightning["fileUrl"].removeprefix("file://")).exists()

    restored = frame.load_single_frame(
        "lightning",
        cache_root,
        "38.900|-76.900",
        2 * 60 * 60 * 1000,
    )
    assert restored["scopeKey"] == "38.900|-76.900"
    assert restored["context"]["windowMinutes"] == 15
    assert restored["observedAtMs"] == 1793462400000

    try:
        frame.load_single_frame(
            "lightning",
            cache_root,
            "39.000|-77.000",
            2 * 60 * 60 * 1000,
        )
        raise AssertionError("cross-location lightning frame cache hydrated")
    except ValueError as error:
        assert str(error) == "SCOPE_MISMATCH"

    metadata_path = cache_root / "lightning" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["receivedAtMs"] = int(time.time() * 1000) - 3 * 60 * 60 * 1000
    metadata_path.write_text(
        json.dumps(metadata, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    try:
        frame.load_single_frame(
            "lightning",
            cache_root,
            "38.900|-76.900",
            2 * 60 * 60 * 1000,
        )
        raise AssertionError("expired lightning cache hydrated")
    except ValueError as error:
        assert str(error) == "CACHE_EXPIRED"

    mrms_url = (
        "https://mapservices.weather.noaa.gov/eventdriven/rest/services/"
        "radar/radar_base_reflectivity_time/ImageServer/exportImage"
        "?bbox=-80,35,-73,42&f=image"
    )
    mrms = frame.store_single_frame(
        "mrms-radar",
        cache_root,
        "manual-radar",
        mrms_url,
        0,
        {
            "bounds": {
                "west": -80,
                "south": 35,
                "east": -73,
                "north": 42,
            },
            "loadedHistoryMinutes": 0,
        },
    )
    assert mrms["sourceId"] == "mrms-radar"
    assert mrms["observedAtMs"] == 0

    tile_url_a = (
        "https://tilecache.rainviewer.com/v2/radar/1793462400/"
        "512/4/2/3/2/1_1.png"
    )
    tile_url_b = (
        "https://tilecache.rainviewer.com/v2/radar/1793462400/"
        "512/4/3/3/2/1_1.png"
    )
    strips = [
        {
            "tileKey": "4/2/3",
            "url": tile_url_a,
            "west": -90,
            "east": -67.5,
            "north": 40,
            "south": 35,
            "sourceY": 0,
            "sourceHeight": 128,
            "sourceSize": 512,
        },
        {
            "tileKey": "4/2/3",
            "url": tile_url_a,
            "west": -90,
            "east": -67.5,
            "north": 35,
            "south": 30,
            "sourceY": 128,
            "sourceHeight": 128,
            "sourceSize": 512,
        },
        {
            "tileKey": "4/3/3",
            "url": tile_url_b,
            "west": -67.5,
            "east": -45,
            "north": 40,
            "south": 35,
            "sourceY": 0,
            "sourceHeight": 128,
            "sourceSize": 512,
        },
    ]
    cached_tiles = frame.store_tile_set(
        "rainviewer",
        cache_root,
        "manual-radar",
        1793462400000,
        {
            "snapshotBounds": {
                "valid": True,
                "west": -90,
                "south": 30,
                "east": -45,
                "north": 40,
            },
            "tileZoom": 4,
            "tileCount": 2,
            "requestedHistoryMinutes": 30,
            "actualHistoryMinutes": 30,
            "selectedFrameTime": 1793462400,
        },
        strips,
    )
    assert len(cached_tiles["strips"]) == 3
    assert all(row["url"].startswith("file:") for row in cached_tiles["strips"])
    tile_files = list((cache_root / "rainviewer").glob("tile-*.png"))
    assert len(tile_files) == 2, "duplicate strips must not duplicate tile bytes"

    restored_tiles = frame.load_tile_set(
        "rainviewer",
        cache_root,
        2 * 60 * 60 * 1000,
    )
    assert len(restored_tiles["strips"]) == 3
    assert restored_tiles["context"]["tileCount"] == 2
    assert restored_tiles["observedAtMs"] == 1793462400000

frame.fetch_png = original_fetch

source = HELPER.read_text(encoding="utf-8")
assert "MAX_IMAGE_BYTES = 16 * 1024 * 1024" in source
assert "MAX_TILE_FILES = 12" in source
assert "RestrictedRedirects" in source
assert "os.replace" in source
assert "os.fsync" in source
assert "SCHEMA = \"post-apollo.weather-frame-cache.v1\"" in source
assert "requests" not in source

runtime = (
    ROOT / "services/weather/WeatherRuntimePolicy.js"
).read_text(encoding="utf-8")
for source_id in ("lightning", "mrms-radar", "rainviewer"):
    assert f'\"{source_id}\": {{' in runtime
assert 'var RETENTION_FRAME_CACHE = "FRAME_CACHE";' in runtime
assert '"FRAME_CACHE_FRESH"' in runtime
assert '"FRAME CACHE // FRESH"' in runtime
assert '"FRAME≤" + limit' in runtime

lightning_service = (
    ROOT / "services/weather/NowcoastLightningService.qml"
).read_text(encoding="utf-8")
assert "property bool usingFrameCache: false" in lightning_service
assert '"load-single"' in lightning_service
assert '"lightning"' in lightning_service
assert lightning_service.count("Process {") == 1
assert lightning_service.count("Timer {") == 2

mrms_service = (
    ROOT / "services/weather/MrmsRadarService.qml"
).read_text(encoding="utf-8")
assert "property bool usingFrameCache: false" in mrms_service
assert '"load-single"' in mrms_service
assert '"fetch-single"' in mrms_service
assert mrms_service.count("Process {") == 1
assert mrms_service.count("Timer {") == 0

rainviewer_service = (
    ROOT / "services/weather/RainViewerRadarService.qml"
).read_text(encoding="utf-8")
assert "property bool usingFrameCache: false" in rainviewer_service
assert '"load-tiles"' in rainviewer_service
assert '"fetch-tiles"' in rainviewer_service
assert rainviewer_service.count("Process {") == 2
assert rainviewer_service.count("Timer {") == 0

station = (
    ROOT / "widgets/weather/StationDiscovery.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.MrmsRadarService {" in station
assert '"usingCache": mrmsRadarService.usingFrameCache' in station
assert '"usingCache": rainViewerRadarService.usingFrameCache' in station
assert "pendingRainViewerDisplay" in station

ground = (
    ROOT / "widgets/weather/StationGround.qml"
).read_text(encoding="utf-8")
assert '"usingCache": lightningService.usingFrameCache' in ground
assert '"FRAME CACHE"' in ground

print("Weather M8 volatile frame cache contracts: PASS")
