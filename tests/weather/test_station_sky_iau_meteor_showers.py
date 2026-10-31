#!/usr/bin/env python3
"""IAU MDC established meteor-shower catalog and SKY integration contract."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/iau_meteor_showers.py"

spec = importlib.util.spec_from_file_location("iau_meteors", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.normalize_angle(361) == 1
assert module.normalize_angle(-1) == 359
assert module.status_number(" 1") == 1
assert module.status_number("x") is None
assert module.angle_in_range(218, 180, 240) is True
assert module.angle_in_range(355, 350, 15) is True
assert module.angle_in_range(5, 350, 15) is True
assert module.angle_in_range(180, 350, 15) is False
assert module.angle_in_range(20, 30, 10) is False

now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
solar = module.solar_longitude_deg(now)
assert 217.0 < solar < 220.0, solar

target = 220.0
peak = module.next_solar_longitude_time(now, target)
assert peak > now
assert abs(module.signed_angle_delta(
    target, module.solar_longitude_deg(peak)
)) < 0.01

alt = module.radiant_altitude(
    52.0, 14.0, 38.9, -77.0, now
)
assert alt is not None
assert -90 <= alt <= 90

fixture = {
    "source": "IAU Meteor Data Center",
    "version": "2026-10-23",
    "data": [
        {
            "IAUNo": "00002",
            "Code": "STA",
            "s": " 1",
            "Name": "Southern Taurids",
            "solution": [
                {
                    "AdNo": "001",
                    "sub.date": "2020-01-01",
                    "s": " 1",
                    "activity": "annual",
                    "LoSb": 180.0,
                    "LoSe": 240.0,
                    "LoS": 220.0,
                    "Ra": 52.0,
                    "De": 14.0,
                    "Vg": 28.0,
                    "Parent body": "2P/Encke",
                    "Ote": "V"
                }
            ]
        },
        {
            "IAUNo": "00004",
            "Code": "GEM",
            "s": " 1",
            "Name": "Geminids",
            "solution": [
                {
                    "AdNo": "001",
                    "sub.date": "2022-01-01",
                    "s": " 1",
                    "activity": "annual",
                    "LoSb": 250.0,
                    "LoSe": 270.0,
                    "LoS": 262.0,
                    "Ra": 112.0,
                    "De": 33.0,
                    "Vg": 35.0,
                    "Parent body": "3200 Phaethon",
                    "Ote": "V"
                }
            ]
        },
        {
            "IAUNo": "00999",
            "Code": "BAD",
            "s": " 0",
            "Name": "Working-list shower",
            "solution": [
                {
                    "AdNo": "001",
                    "sub.date": "2025-01-01",
                    "activity": "annual",
                    "LoSb": 200,
                    "LoSe": 230,
                    "LoS": 218,
                    "Ra": 10,
                    "De": 10
                }
            ]
        },
        {
            "IAUNo": "00005",
            "Code": "NOB",
            "s": " 1",
            "Name": "No-bounds shower",
            "solution": [
                {
                    "AdNo": "001",
                    "sub.date": "2024-01-01",
                    "activity": "annual",
                    "LoSb": None,
                    "LoSe": None,
                    "LoS": 225.0,
                    "Ra": 20.0,
                    "De": -5.0,
                    "Vg": 44.0,
                    "Parent body": "",
                    "Ote": "T"
                }
            ]
        }
    ]
}

rows = module.parse_catalog(fixture)
assert len(rows) == 3
assert [row["code"] for row in rows] == ["STA", "GEM", "NOB"]

summary = module.summarize(fixture, now, 38.9, -77.0)
assert summary["source"] == "IAU Meteor Data Center"
assert summary["version"] == "2026-10-23"
assert summary["catalogCount"] == 3
assert summary["activeCount"] == 1
assert summary["active"][0]["code"] == "STA"
assert summary["active"][0]["active"] is True
assert summary["active"][0]["parentBody"] == "2P/Encke"
assert summary["active"][0]["radiantAltitude"] is not None
assert len(summary["upcoming"]) == 3
assert summary["upcoming"][0]["daysToPeak"] >= 0
assert summary["note"].startswith("PEAK UTC IS LOCALLY DERIVED")

source = HELPER.read_text(encoding="utf-8")
assert 'HOST = "iaumdc.astro.sk"' in source
assert "streamestablisheddata.json" in source
assert "MAX_BYTES = 8 * 1024 * 1024" in source
assert "IauOnlyRedirects" in source
assert "Post-Apollo-WeatherStation/1.0" in source
assert "Unexpected IAU MDC response URL" in source
assert "requests" not in source
assert "selenium" not in source.lower()

service = (
    ROOT / "services/weather/IauMeteorShowerService.qml"
).read_text(encoding="utf-8")
assert "Scope {" in service
assert "property bool active: true" in service
assert "property string inflightKey" in service
assert "iau_meteor_showers.py" in service
assert "currentKey !== inflightKey" in service
assert service.count("Process {") == 1
assert service.count("Timer {") == 2
assert "interval: 21600000" in service
assert "interval: 250" in service
assert "running: meteors.active && meteors.configured" in service
assert "Qt.openUrlExternally" not in service
assert "WebEngine" not in service

sky = (
    ROOT / "widgets/weather/StationSky.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.IauMeteorShowerService {" in sky
assert 'title: "METEOR SHOWERS // IAU MDC"' in sky
assert "ACTIVE NOW // " in sky
assert "NEXT PEAKS" in sky
assert "modelData.radiantAltitude" in sky
assert "modelData.peakUtc" in sky
assert "modelData.parentBody" in sky
assert "IAU MDC ACTIVITY IS CATALOG/STREAM CONTEXT" in sky
assert "NOT A LOCAL OBSERVED RATE OR ZHR CLAIM" in sky
assert "RADIANT ABOVE HORIZON ≠ GOOD VIEWING" in sky

start = sky.index('title: "METEOR SHOWERS // IAU MDC"')
end = sky.index('title: "TWILIGHT // SOLAR WINDOWS"', start)
meteor_ui = sky[start:end]
assert "Process {" not in meteor_ui
assert "Timer {" not in meteor_ui
assert "curl" not in meteor_ui
assert "Qt.openUrlExternally" not in meteor_ui

workflow = (
    ROOT / ".github/workflows/weather-teardown-contracts.yml"
).read_text(encoding="utf-8")
assert "python3 tests/weather/test_station_sky_iau_meteor_showers.py" in workflow

print("Weather SKY IAU MDC meteor shower activity + peak calendar: PASS")
