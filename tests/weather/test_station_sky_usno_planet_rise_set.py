#!/usr/bin/env python3
"""USNO naked-eye planet rise/transit/set helper and SKY integration contract."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/usno_planet_rise_set.py"

spec = importlib.util.spec_from_file_location("usno_planets", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.PLANETS == (
    ("MERCURY", 1),
    ("VENUS", 2),
    ("MARS", 4),
    ("JUPITER", 5),
    ("SATURN", 6),
)

assert module.valid_date("2026-10-31") is True
assert module.valid_date("2051-01-01") is False
assert module.valid_date("2026-02-30") is False
assert module.snapped_offset_minutes(-240.868) == -240
assert module.snapped_offset_minutes(330.2) == 330
assert module.snapped_offset_minutes(345.1) == 345
assert module.snapped_offset_minutes(-730) is None
assert module.tz_hours_text(-240) == "4"
assert module.tz_hours_text(330) == "5.5"
assert module.tz_hours_text(345) == "5.75"

info = module.request_info("2026-10-31", 38.9, -77.0, -240.868)
assert info["valid"] is True
assert info["key"] == "2026-10-31|38.9000|-77.0000|-240"
assert info["offsetMinutes"] == -240

url = module.planet_url(1, info)
parts = urlsplit(url)
assert parts.scheme == "https"
assert parts.hostname == "aa.usno.navy.mil"
assert parts.path == "/calculated/mrst"
query = parse_qs(parts.query)
assert query["body"] == ["1"]
assert query["date"] == ["2026-10-31"]
assert query["lat"] == ["38.9000"]
assert query["lon"] == ["-77.0000"]
assert query["height"] == ["0"]
assert query["reps"] == ["1"]
assert query["tz"] == ["4"]
assert query["tz_sign"] == ["-1"]
assert query["label"] == ["Post Apollo Weather"]

east = module.request_info("2026-10-31", 28.6, 77.2, 330)
east_query = parse_qs(urlsplit(module.planet_url(2, east)).query)
assert east_query["tz"] == ["5.5"]
assert east_query["tz_sign"] == ["1"]

mercury = b"""<!doctype html><html><body><pre>
Astronomical Applications Department
U. S. Naval Observatory

Mercury

Post Apollo Weather
Time Zone: 4h 00m west of Greenwich

Date               Rise  Az.       Transit Alt.       Set  Az.
(Zone)
                   h  m   deg       h  m  deg         h  m   deg
2026 Oct 31 (Sat)  07:11  73        13:57 62S        20:42 287
</pre></body></html>"""

row = module.parse_planet_page(
    mercury, "2026-10-31", "MERCURY", 1
)
assert row["name"] == "MERCURY"
assert row["bodyId"] == 1
assert row["status"] == "NORMAL"
assert row["rise"] == "07:11"
assert row["riseLabel"] == "7:11 AM"
assert row["riseAzimuth"] == 73
assert row["transit"] == "13:57"
assert row["transitLabel"] == "1:57 PM"
assert row["transitAltitude"] == 62
assert row["transitHemisphere"] == "S"
assert row["set"] == "20:42"
assert row["setLabel"] == "8:42 PM"
assert row["setAzimuth"] == 287

continuous_below = b"""<html><body><pre>
Venus
2026 Oct 31 (Sat)  ----
</pre></body></html>"""
row = module.parse_planet_page(
    continuous_below, "2026-10-31", "VENUS", 2
)
assert row["status"] == "CONTINUOUSLY BELOW HORIZON"
assert row["riseLabel"] == "--"
assert row["setLabel"] == "--"

continuous_above = b"""<html><body><pre>
Mars
2026 Oct 31 (Sat)  *****
</pre></body></html>"""
assert module.parse_planet_page(
    continuous_above, "2026-10-31", "MARS", 4
)["status"] == "CONTINUOUSLY ABOVE HORIZON"

indeterminate = b"""<html><body><pre>
Jupiter
2026 Oct 31 (Sat)  ?????
</pre></body></html>"""
assert module.parse_planet_page(
    indeterminate, "2026-10-31", "JUPITER", 5
)["status"] == "INDETERMINATE"

partial = b"""<html><body><pre>
Saturn
2026 Oct 31 (Sat)  provider changed this row
</pre></body></html>"""
assert module.parse_planet_page(
    partial, "2026-10-31", "SATURN", 6
)["status"] == "PARTIAL / UNPARSED"

try:
    module.parse_planet_page(
        mercury, "2026-10-31", "VENUS", 2
    )
    raise AssertionError("body/title mismatch accepted")
except ValueError:
    pass

assert module.clock_label("00:05") == "12:05 AM"
assert module.clock_label("12:00") == "12:00 PM"
assert module.clock_label("23:59") == "11:59 PM"
assert module.clock_label("24:00") == "--"

source = HELPER.read_text(encoding="utf-8")
assert 'HOST = "aa.usno.navy.mil"' in source
assert '"/calculated/mrst"' in source
assert "MAX_BYTES = 768 * 1024" in source
assert "UsnoOnlyRedirects" in source
assert "Post-Apollo-WeatherStation/0.9" in source
assert "Unexpected USNO response URL" in source
assert "urllib.request" in source
assert "requests" not in source
assert "selenium" not in source.lower()
assert "beautifulsoup" not in source.lower()

service = (
    ROOT / "services/weather/UsnoPlanetRiseSetService.qml"
).read_text(encoding="utf-8")
assert "Scope {" in service
assert "property bool active: true" in service
assert "property string date" in service
assert "property var offsetMinutes" in service
assert "property string inflightKey" in service
assert "property string loadedKey" in service
assert "usno_planet_rise_set.py" in service
assert "currentKey !== inflightKey" in service
assert "currentKey === loadedKey" in service
assert service.count("Process {") == 1
assert service.count("Timer {") == 1
assert "interval: 250" in service
assert "repeat: false" in service
assert "repeat: true" not in service
assert "Qt.openUrlExternally" not in service
assert "WebEngine" not in service

sky = (
    ROOT / "widgets/weather/StationSky.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.UsnoPlanetRiseSetService {" in sky
assert "date: sky.astronomySummary.date" in sky
assert "offsetMinutes: sky.moonCivilOffsetMinutes" in sky
assert 'title: "PLANET CLOCK // USNO RISE + TRANSIT + SET"' in sky
assert "MERCURY + VENUS + MARS + JUPITER + SATURN" in sky
assert "modelData.riseLabel" in sky
assert "modelData.transitLabel" in sky
assert "modelData.setLabel" in sky
assert "modelData.riseAzimuth" in sky
assert "modelData.transitAltitude" in sky
assert "modelData.setAzimuth" in sky
assert "AZIMUTH TRUE NORTH" in sky
assert "USNO MODELS ATMOSPHERIC REFRACTION" in sky
assert "CURRENT POSITION ABOVE USES CELNAV" in sky

start = sky.index(
    'title: "PLANET CLOCK // USNO RISE + TRANSIT + SET"'
)
end = sky.index(
    'title: "TWILIGHT // SOLAR WINDOWS"', start
)
planet_ui = sky[start:end]
assert "Process {" not in planet_ui
assert "Timer {" not in planet_ui
assert "curl" not in planet_ui
assert "Qt.openUrlExternally" not in planet_ui

workflow = (
    ROOT / ".github/workflows/weather-teardown-contracts.yml"
).read_text(encoding="utf-8")
assert (
    "python3 tests/weather/test_station_sky_usno_planet_rise_set.py"
    in workflow
)

print("Weather SKY USNO planet rise/transit/set clock: PASS")
