#!/usr/bin/env python3
"""NASA GSFC eclipse calendar parser and SKY integration contract."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/nasa_eclipse_calendar.py"

spec = importlib.util.spec_from_file_location("nasa_eclipses", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.page_url(2026).endswith("/OH/OH2026.html")
assert module.page_url(2027).endswith("/OH/OH2027.html")
try:
    module.page_url(1900)
    raise AssertionError("unsupported year accepted")
except ValueError:
    pass

fixture_2026 = b"""<!doctype html><html><body>
<h1>Eclipses During 2026</h1>
<p>2026 Feb 17: Annular Solar Eclipse</p>
<p>2026 Mar 03: Total Lunar Eclipse</p>
<p>2026 Aug 12: Total Solar Eclipse</p>
<p>2026 Aug 28: Partial Lunar Eclipse</p>
<p>2027 Feb 06: Annular Solar Eclipse</p>
</body></html>"""

rows = module.parse_page(fixture_2026, 2026)
assert len(rows) == 4
assert [row["event"] for row in rows] == [
    "ANNULAR SOLAR ECLIPSE",
    "TOTAL LUNAR ECLIPSE",
    "TOTAL SOLAR ECLIPSE",
    "PARTIAL LUNAR ECLIPSE",
]
assert rows[0]["date"] == "2026-02-17"
assert rows[-1]["date"] == "2026-08-28"
assert rows[0]["sourcePage"].endswith("/OH/OH2026.html")

fixture_2027 = b"""<html><body>
2027 Feb 06: Annular Solar Eclipse
2027 Feb 20: Penumbral Lunar Eclipse
2027 Jul 18: Penumbral Lunar Eclipse
2027 Aug 02: Total Solar Eclipse
2027 Aug 17: Penumbral Lunar Eclipse
</body></html>"""
rows_2027 = module.parse_page(fixture_2027, 2027)
assert len(rows_2027) == 5
assert rows_2027[0]["phase"] == "ANNULAR"
assert rows_2027[0]["body"] == "SOLAR"
assert rows_2027[1]["phase"] == "PENUMBRAL"
assert rows_2027[1]["body"] == "LUNAR"

now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
summary = module.summarize([rows, rows_2027], now)
assert summary["source"] == "NASA GSFC ECLIPSE WEB SITE"
assert summary["localVisibility"] is False
assert summary["exactMaximumTime"] is False
assert summary["dateScope"] == "GLOBAL UTC CALENDAR DATE"
assert summary["eventCount"] == 5
assert summary["nextSolar"]["date"] == "2027-02-06"
assert summary["nextSolar"]["event"] == "ANNULAR SOLAR ECLIPSE"
assert summary["nextLunar"]["date"] == "2027-02-20"
assert summary["nextLunar"]["event"] == "PENUMBRAL LUNAR ECLIPSE"
assert summary["events"][0]["daysUntil"] > 0
assert all(row["daysUntil"] >= 0 for row in summary["events"])

source = HELPER.read_text(encoding="utf-8")
assert 'HOST = "eclipse.gsfc.nasa.gov"' in source
assert '"/OH/OH{year}.html"' in source
assert "MAX_BYTES = 2 * 1024 * 1024" in source
assert "NasaOnlyRedirects" in source
assert "Post-Apollo-WeatherStation/1.1" in source
assert "Unexpected NASA eclipse response URL" in source
assert "requests" not in source
assert "selenium" not in source.lower()

service = (
    ROOT / "services/weather/NasaEclipseService.qml"
).read_text(encoding="utf-8")
assert "Scope {" in service
assert "property bool active: true" in service
assert "nasa_eclipse_calendar.py" in service
assert "property bool localVisibility: false" in service
assert "property bool exactMaximumTime: false" in service
assert service.count("Process {") == 1
assert service.count("Timer {") == 2
assert "interval: 43200000" in service
assert "interval: 250" in service
assert "running: eclipses.active" in service
assert "Qt.openUrlExternally" not in service
assert "WebEngine" not in service

sky = (
    ROOT / "widgets/weather/StationSky.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.NasaEclipseService {" in sky
assert 'title: "ECLIPSES // NASA GSFC"' in sky
assert "NEXT SOLAR" in sky
assert "NEXT LUNAR" in sky
assert "eclipseService.nextSolar" in sky
assert "eclipseService.nextLunar" in sky
assert "EXACT MAXIMUM TIME, CONTACTS, MAGNITUDE + OBSCURATION ARE NOT NORMALIZED HERE" in sky
assert "GLOBAL ECLIPSE ≠ VISIBLE FROM WEATHER FIX" in sky
assert "LOCAL VISIBILITY + CONTACT CIRCUMSTANCES REMAIN A SEPARATE FUTURE LAYER" in sky

start = sky.index('title: "ECLIPSES // NASA GSFC"')
end = sky.index('title: "SKY NOW // USNO CELESTIAL FIX"', start)
eclipse_ui = sky[start:end]
assert "Process {" not in eclipse_ui
assert "Timer {" not in eclipse_ui
assert "curl" not in eclipse_ui
assert "Qt.openUrlExternally" not in eclipse_ui

workflow = (
    ROOT / ".github/workflows/weather-teardown-contracts.yml"
).read_text(encoding="utf-8")
assert "python3 tests/weather/test_station_sky_nasa_eclipses.py" in workflow

print("Weather SKY NASA GSFC eclipse calendar: PASS")
