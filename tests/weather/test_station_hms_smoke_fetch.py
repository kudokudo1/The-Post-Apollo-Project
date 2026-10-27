#!/usr/bin/env python3
"""NOAA HMS latest-product lookup and KML polygon normalization."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/hms_smoke_fetch.py"

spec = importlib.util.spec_from_file_location("hms_smoke_fetch", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

now = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)
candidates = list(module.candidate_urls(now, 2))
assert [day.isoformat() for day, _ in candidates] == [
    "2026-10-27", "2026-10-26", "2026-10-25"
]
assert candidates[0][1].endswith(
    "/KML/2026/10/hms_smoke20261027.kml"
)
assert candidates[2][1].endswith(
    "/KML/2026/10/hms_smoke20261025.kml"
)

assert module.normalize_density("Light") == "light"
assert module.normalize_density("16") == "medium"
assert module.normalize_density("21") == "heavy"

kml = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark>
  <ExtendedData>
    <Data name="Satellite"><value>GOES-EAST</value></Data>
    <Data name="Start"><value>2026300 1200</value></Data>
    <Data name="End"><value>2026300 1800</value></Data>
    <Data name="Density"><value>Heavy</value></Data>
  </ExtendedData>
  <Polygon><outerBoundaryIs><LinearRing><coordinates>
    -77,38,0 -76,38,0 -76,39,0 -77,38,0
  </coordinates></LinearRing></outerBoundaryIs></Polygon>
</Placemark>
<Placemark>
  <description><![CDATA[
    <table><tr><td>Satellite</td><td>GOES-WEST</td></tr>
    <tr><td>Start</td><td>2026300 1300</td></tr>
    <tr><td>End</td><td>2026300 1900</td></tr>
    <tr><td>Density</td><td>Light</td></tr></table>
  ]]></description>
  <MultiGeometry>
    <Polygon><outerBoundaryIs><LinearRing><coordinates>
      179,50 -179,50 -178,51 179,50
    </coordinates></LinearRing></outerBoundaryIs></Polygon>
  </MultiGeometry>
</Placemark>
</Document></kml>"""

parsed = module.parse_kml(kml, "20261027")
assert parsed["analysisDate"] == "20261027"
assert parsed["polygonCount"] == 2
assert parsed["vertexCount"] == 8
assert parsed["truncated"] is False
first, second = parsed["polygons"]
assert first["density"] == "heavy"
assert first["satellite"] == "GOES-EAST"
assert first["start"] == "2026300 1200"
assert first["end"] == "2026300 1800"
assert first["ring"][0] == [-77.0, 38.0]
assert second["density"] == "light"
assert second["satellite"] == "GOES-WEST"
assert second["ring"][1] == [-179.0, 50.0]

source = HELPER.read_text(encoding="utf-8")
assert "Smoke_Polygons/KML" in source
assert "LOOKBACK_DAYS = 7" in source
assert "MAX_BYTES = 8 * 1024 * 1024" in source
assert "MAX_POLYGONS = 1200" in source
assert "MAX_VERTICES = 200_000" in source
assert "HmsOnlyRedirects" in source
assert 'dest.hostname != HOST' in source
assert "datetime.now(timezone.utc)" in source

print("NOAA HMS smoke helper and KML parser: PASS")
