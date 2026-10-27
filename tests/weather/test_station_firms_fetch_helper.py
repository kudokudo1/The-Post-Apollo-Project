#!/usr/bin/env python3
"""FIRMS helper keeps MAP_KEY out of argv/UI and constrains provider requests."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/firms_area_fetch.py"
SERVICE = ROOT / "services/weather/FirmsHotspotService.qml"

spec = importlib.util.spec_from_file_location("firms_area_fetch", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

key = "abcDEF_1234567890"
url = module.request_url(
    "VIIRS_NOAA21_NRT",
    "-100.0000,20.0000,-50.0000,50.0000",
    "1",
    key,
)
assert url.startswith("https://firms.modaps.eosdis.nasa.gov/api/area/csv/")
assert f"/{key}/VIIRS_NOAA21_NRT/" in url
assert url.endswith("/-100.0000,20.0000,-50.0000,50.0000/1")

for source in ("VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT", "VIIRS_SNPP_NRT"):
    assert module.request_url(
        source, "-80,20,-70,30", "1", key
    ).startswith("https://firms.modaps.eosdis.nasa.gov/")

for args in (
    ("BAD_SOURCE", "-80,20,-70,30", "1", key),
    ("VIIRS_NOAA21_NRT", "-80,20,-70,30", "2", key),
    ("VIIRS_NOAA21_NRT", "-180,-90,180,90", "1", key),
    ("VIIRS_NOAA21_NRT", "-80,20,-70,30", "1", "bad/key"),
):
    try:
        module.request_url(*args)
    except ValueError:
        pass
    else:
        raise AssertionError(f"expected rejection: {args[:3]}")

source = HELPER.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")
assert 'os.environ.get("POST_APOLLO_FIRMS_MAP_KEY"' in source
assert "sys.argv" not in source or "argv[1]" in source
assert "print(" not in source, "helper must never print an exception containing secret URL"
assert "urllib" in source
assert "4 * 1024 * 1024" in source
assert "Unexpected FIRMS redirect" in source
assert "POST_APOLLO_FIRMS_MAP_KEY" in service

command_start = service.index("fetchProcess.command = [")
command_end = service.index("];", command_start)
command = service[command_start:command_end]
assert "mapKey" not in command
assert "POST_APOLLO_FIRMS_MAP_KEY" not in command
assert "firms.modaps.eosdis.nasa.gov" not in command
assert "firms_area_fetch.py" in command

print("FIRMS secret-safe bounded fetch helper: PASS")
