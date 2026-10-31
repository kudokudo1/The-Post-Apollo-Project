#!/usr/bin/env python3
"""ISS pass prediction, CelesTrak provenance and SKY integration contract."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/iss_passes.py"

spec = importlib.util.spec_from_file_location("iss_passes", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.NORAD_ID == 25544
assert module.validate_coordinate("38.9", -90, 90, "latitude") == 38.9
try:
    module.validate_coordinate("100", -90, 90, "latitude")
    raise AssertionError("invalid latitude accepted")
except ValueError:
    pass

url = module.pass_url(38.9, -77.0)
parts = urlsplit(url)
assert parts.scheme == "https"
assert parts.hostname == "iss-in.space"
assert parts.path == "/api/passes/38.90000/-77.00000"

c_url = module.celestrak_url()
parts = urlsplit(c_url)
assert parts.scheme == "https"
assert parts.hostname == "celestrak.org"
assert "CATNR=25544" in parts.query
assert "FORMAT=JSON" in parts.query

now = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
pass_fixture = [
    {
        "length": 420,
        "length_mins": "7:00",
        "rise": {
            "time": "2026-10-31T13:00:00Z",
            "degrees": 0,
            "azimuth": 214,
            "direction": "SW",
            "distance": 2600,
        },
        "culminate": {
            "time": "2026-10-31T13:03:30Z",
            "degrees": 43,
            "azimuth": 142,
            "direction": "SE",
            "distance": 559,
        },
        "set": {
            "time": "2026-10-31T13:07:00Z",
            "degrees": 0,
            "azimuth": 71,
            "direction": "ENE",
            "distance": 2600,
        },
    },
    {
        "length": 300,
        "length_mins": "5:00",
        "rise": {
            "time": "2026-10-31T15:00:00Z",
            "degrees": 0,
            "azimuth": 300,
            "direction": "NW",
            "distance": 2700,
        },
        "culminate": {
            "time": "2026-10-31T15:02:30Z",
            "degrees": 18,
            "azimuth": 5,
            "direction": "N",
            "distance": 1200,
        },
        "set": {
            "time": "2026-10-31T15:05:00Z",
            "degrees": 0,
            "azimuth": 60,
            "direction": "ENE",
            "distance": 2700,
        },
    },
]

passes = module.parse_passes(pass_fixture, now)
assert len(passes) == 2
assert passes[0]["rise"]["timeUtc"] == "2026-10-31 13:00Z"
assert passes[0]["culminate"]["degrees"] == 43
assert passes[0]["culminate"]["direction"] == "SE"
assert passes[0]["durationSeconds"] == 420
assert passes[0]["durationLabel"] == "7:00"
assert 59.9 < passes[0]["minutesUntilRise"] < 60.1
assert passes[0]["geometricPass"] is True
assert passes[0]["visibilityEvaluated"] is False

orbit_fixture = [{
    "OBJECT_NAME": "ISS (ZARYA)",
    "NORAD_CAT_ID": 25544,
    "EPOCH": "2026-10-31T08:20:11.123456",
    "MEAN_MOTION": 15.49,
    "INCLINATION": 51.64,
    "ECCENTRICITY": 0.0003,
}]
orbit = module.parse_celestrak(orbit_fixture)
assert orbit["objectName"] == "ISS (ZARYA)"
assert orbit["noradId"] == 25544
assert orbit["elementEpochUtc"].startswith("2026-10-31 08:20Z")
assert orbit["meanMotion"] == 15.49
assert orbit["inclination"] == 51.64

result = module.build_result(pass_fixture, orbit_fixture, now)
assert result["source"] == "ISS-IN.SPACE"
assert result["orbitalSource"] == "CELESTRAK"
assert result["predictionModel"] == "SKYFIELD + SGP4 (PROVIDER DOCUMENTED)"
assert result["geometricPassOnly"] is True
assert result["visibilityEvaluated"] is False
assert result["passCount"] == 2
assert result["orbit"]["noradId"] == 25544

bad_order = [{
    "rise": {"time":"2026-10-31T13:05:00Z","degrees":0,"azimuth":1},
    "culminate": {"time":"2026-10-31T13:03:00Z","degrees":30,"azimuth":2},
    "set": {"time":"2026-10-31T13:07:00Z","degrees":0,"azimuth":3},
    "length":120,
}]
try:
    module.parse_passes(bad_order, now)
    raise AssertionError("bad pass ordering accepted")
except ValueError:
    pass

try:
    module.parse_celestrak([{
        "OBJECT_NAME":"OTHER",
        "NORAD_CAT_ID":123,
        "EPOCH":"2026-10-31T08:20:11Z",
    }])
    raise AssertionError("wrong NORAD id accepted")
except ValueError:
    pass

source = HELPER.read_text(encoding="utf-8")
assert 'PASS_HOST = "iss-in.space"' in source
assert 'CELESTRAK_HOST = "celestrak.org"' in source
assert "CATNR=25544" in source
assert "FORMAT=JSON" in source
assert "MAX_BYTES = 2 * 1024 * 1024" in source
assert "HostOnlyRedirects" in source
assert "Post-Apollo-WeatherStation/1.2" in source
assert "requests" not in source
assert "selenium" not in source.lower()

service = (
    ROOT / "services/weather/IssPassService.qml"
).read_text(encoding="utf-8")
assert "Scope {" in service
assert "property bool active: true" in service
assert "property string inflightKey" in service
assert "iss_passes.py" in service
assert "currentKey !== inflightKey" in service
assert "interval: 7200000" in service
assert "interval: 250" in service
assert service.count("Process {") == 1
assert service.count("Timer {") == 2
assert "running: iss.active && iss.configured" in service
assert "Qt.openUrlExternally" not in service
assert "WebEngine" not in service

sky = (
    ROOT / "widgets/weather/StationSky.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.IssPassService {" in sky
assert 'title: "ISS PASSES // SKYFIELD + SGP4"' in sky
assert "ISS NORAD 25544" in sky
assert "modelData.culminate.degrees" in sky
assert "modelData.rise.direction" in sky
assert "modelData.set.direction" in sky
assert "CELESTRAK ELEMENT EPOCH SHOWN FOR PROVENANCE" in sky
assert "OPTICAL VISIBILITY NOT EVALUATED" in sky
assert "GEOMETRIC HORIZON PASSES ONLY" in sky

start = sky.index('title: "ISS PASSES // SKYFIELD + SGP4"')
end = sky.index('title: "MOON // USNO EPHEMERIS"', start)
iss_ui = sky[start:end]
assert "Process {" not in iss_ui
assert "Timer {" not in iss_ui
assert "curl" not in iss_ui
assert "Qt.openUrlExternally" not in iss_ui

workflow = (
    ROOT / ".github/workflows/weather-teardown-contracts.yml"
).read_text(encoding="utf-8")
assert "python3 tests/weather/test_station_sky_iss_passes.py" in workflow

print("Weather SKY ISS geometric passes + CelesTrak provenance: PASS")
