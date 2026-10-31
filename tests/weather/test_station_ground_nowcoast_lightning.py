#!/usr/bin/env python3
"""NOAA nowCOAST lightning WMS discovery and bounded snapshot contract."""
from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/nowcoast_lightning_snapshot.py"

spec = importlib.util.spec_from_file_location("nowcoast_lightning", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

capabilities = b"""<?xml version="1.0" encoding="UTF-8"?>
<WMS_Capabilities xmlns="http://www.opengis.net/wms">
  <Capability>
    <Layer>
      <Title>NOAA observations</Title>
      <Layer queryable="0">
        <Name>observations:other_layer</Name>
        <Title>Other Weather Layer</Title>
      </Layer>
      <Layer queryable="0">
        <Name>lightning_detection:lightning_strike_density</Name>
        <Title>Lightning Strike Density 15 Minute</Title>
        <Dimension name="time" units="ISO8601" default="current">
          2026-10-31T12:00:00.000Z,2026-10-31T12:15:00.000Z,2026-10-31T12:30:00.000Z
        </Dimension>
      </Layer>
    </Layer>
  </Capability>
</WMS_Capabilities>
"""

root = module.ET.fromstring(capabilities)
layer = module.select_lightning_layer(root)
assert layer["name"] == "lightning_detection:lightning_strike_density"
assert layer["title"] == "Lightning Strike Density 15 Minute"

raw_time, default_time = module.time_dimension_text(layer["node"])
assert default_time == "current"
assert module.latest_time_value(raw_time, default_time) == (
    "2026-10-31T12:30:00.000Z"
)
assert module.latest_time_value(
    "2026-10-31T00:00:00Z/2026-10-31T12:30:00Z/PT15M", ""
) == "2026-10-31T12:30:00Z"
assert module.latest_time_value("", "current") == ""

bbox = module.bounded_box(38.98, -76.50, 320)
assert bbox["west"] < -76.5 < bbox["east"]
assert bbox["south"] < 38.98 < bbox["north"]
assert bbox["east"] <= 0
assert bbox["south"] >= -25
assert bbox["north"] <= 80

url = module.build_map_url(
    layer["name"], bbox, 760, 260, "2026-10-31T12:30:00.000Z"
)
parts = urlsplit(url)
assert parts.scheme == "https"
assert parts.hostname == "nowcoast.noaa.gov"
query = parse_qs(parts.query)
assert query["SERVICE"] == ["WMS"]
assert query["VERSION"] == ["1.1.1"]
assert query["REQUEST"] == ["GetMap"]
assert query["LAYERS"] == [
    "lightning_detection:lightning_strike_density"
]
assert query["SRS"] == ["EPSG:4326"]
assert query["WIDTH"] == ["760"]
assert query["HEIGHT"] == ["260"]
assert query["FORMAT"] == ["image/png"]
assert query["TRANSPARENT"] == ["true"]
assert query["TIME"] == ["2026-10-31T12:30:00.000Z"]

snapshot = module.build_snapshot(
    capabilities, 38.98, -76.50, radius_km=320, width=760, height=260
)
assert snapshot["source"] == "NOAA nowCOAST"
assert snapshot["product"] == "LIGHTNING STRIKE DENSITY"
assert snapshot["layer"] == "lightning_detection:lightning_strike_density"
assert snapshot["windowMinutes"] == 15
assert snapshot["resolutionKm"] == 8
assert snapshot["radiusKm"] == 320
assert snapshot["latestTime"] == "2026-10-31T12:30:00.000Z"
assert snapshot["imageUrl"].startswith(
    "https://nowcoast.noaa.gov/geoserver/observations/"
    "lightning_detection/ows?"
)
datetime.fromisoformat(snapshot["generatedUtc"].replace("Z", "+00:00"))

assert module.validate_coordinate("38.9", -90, 90, "latitude") == 38.9
try:
    module.validate_coordinate("100", -90, 90, "latitude")
    raise AssertionError("invalid latitude accepted")
except ValueError:
    pass

try:
    module.bounded_box(38.9, 30.0, 320)
    raise AssertionError("outside-domain longitude accepted")
except ValueError:
    pass

try:
    module.select_lightning_layer(
        module.ET.fromstring(
            b"<WMS_Capabilities><Layer><Name>x</Name></Layer></WMS_Capabilities>"
        )
    )
    raise AssertionError("missing lightning layer accepted")
except ValueError:
    pass

source = HELPER.read_text(encoding="utf-8")
assert "nowcoast.noaa.gov" in source
assert "/geoserver/observations/lightning_detection/ows" in source
assert "MAX_BYTES = 2 * 1024 * 1024" in source
assert "NowcoastOnlyRedirects" in source
assert "Post-Apollo-WeatherStation/0.8" in source
assert '"TRANSPARENT": "true"' in source
assert "urllib.request" in source
assert "requests" not in source

service = (
    ROOT / "services/weather/NowcoastLightningService.qml"
).read_text(encoding="utf-8")
assert "Scope {" in service
assert "property bool active: true" in service
assert "property string inflightKey" in service
assert "currentKey !== inflightKey" in service
assert "nowcoast_lightning_snapshot.py" in service
assert "interval: 900000" in service
assert "running: lightning.active && lightning.configured" in service
assert service.count("Process {") == 1
assert service.count("Timer {") == 2
assert "Qt.openUrlExternally" not in service

ground = (
    ROOT / "widgets/weather/StationGround.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.NowcoastLightningService {" in ground
assert 'title: "LIGHTNING // NOAA NOWCOAST"' in ground
assert "15-MIN STRIKE DENSITY" in ground
assert "WEATHER FIX = CENTER CROSSHAIR" in ground
assert "DERIVED NLDN / GLD360 PRODUCT" in ground
assert "NOT RAW STRIKE LOCATIONS" in ground
assert "USE OFFICIAL NWS ALERTS FOR WARNING DECISIONS" in ground
start = ground.index('title: "LIGHTNING // NOAA NOWCOAST"')
end = ground.index('title: "HEAT + FIRE WEATHER // NWS CONTEXT"', start)
lightning_ui = ground[start:end]
assert "Process {" not in lightning_ui
assert "curl" not in lightning_ui
assert "Qt.openUrlExternally" not in lightning_ui

workflow = (
    ROOT / ".github/workflows/weather-teardown-contracts.yml"
).read_text(encoding="utf-8")
assert (
    "python3 tests/weather/test_station_ground_nowcoast_lightning.py"
    in workflow
)

print("NOAA nowCOAST lightning WMS snapshot helper + GROUND contract: PASS")
