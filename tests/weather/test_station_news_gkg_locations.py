#!/usr/bin/env python3
"""GDELT GKG article -> mentioned-location lookup contracts."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import io
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/weather/gdelt_gkg_article_locations.py"

spec = importlib.util.spec_from_file_location("gkg_locations", HELPER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.safe_article_url("https://example.org/news/a") ==     "https://example.org/news/a"
for bad in [
    "", "http://example.org/a", "https://localhost/a",
    "https://private.local/a", "https://127.0.0.1/a",
    "https://user:pass@example.org/a",
]:
    assert module.safe_article_url(bad) == "", bad

assert module.canonical_url(
    "https://www.Example.org/story/?utm_source=x&id=7#top"
) == "https://example.org/story?id=7"

seen = module.parse_seen_time("20261031T143712Z")
assert seen == datetime(2026, 10, 31, 14, 37, 12, tzinfo=timezone.utc)
candidates = module.slice_candidates(seen)
assert [x.strftime("%H:%M") for x in candidates] == [
    "14:30", "14:15", "14:45"
]
assert module.slice_url(candidates[0], "English").endswith(
    "/20261031143000.gkg.csv.zip"
)
assert module.slice_url(candidates[0], "Spanish").endswith(
    "/20261031143000.translation.gkg.csv.zip"
)
assert module.feed_suffix("EN") == ".gkg.csv.zip"
assert module.feed_suffix("French") == ".translation.gkg.csv.zip"

raw_locations = (
    "1#Jamaica#JM#JM##18.25#-77.5#JM#51;"
    "4#Kingston, Kingston, Jamaica#JM#JM17#123#17.997#-76.793#-375243#82;"
    "4#Kingston, Jamaica#JM#JM17#123#17.997#-76.793#-375243#410;"
    "5#Kingston, Jamaica#JM#JM17#123#18.00#-76.80#JM17#130;"
)
locations = module.parse_locations(raw_locations)
assert len(locations) == 3
assert locations[0]["type"] == 4
assert locations[0]["typeLabel"] == "WORLD CITY / LANDMARK"
assert locations[0]["featureId"] == "-375243"
assert locations[0]["mentionCount"] == 2
assert locations[0]["firstOffset"] == 82
assert locations[0]["latitude"] == 17.997
assert locations[1]["type"] == 5
assert locations[2]["type"] == 1

article = "https://www.example.org/story/?id=7&utm_source=social"
gkg_document = "https://example.org/story?id=7"
columns = [
    "20261031143000-7",
    "20261031143000",
    "1",
    "example.org",
    gkg_document,
    "",
    "",
    "",
    "",
    "",
    raw_locations,
]
row = "\t".join(columns) + "\n"

buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("20261031143000.gkg.csv", row)

match = module.find_article_in_zip(buffer.getvalue(), article)
assert match is not None
assert match["matchMethod"] == "CANONICAL URL"
assert match["gkgRecordId"] == "20261031143000-7"
assert match["sourceCommonName"] == "example.org"
assert len(match["locations"]) == 3

exact_columns = list(columns)
exact_columns[4] = "https://example.org/exact"
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr(
        "20261031143000.gkg.csv",
        "\t".join(exact_columns) + "\n",
    )
match = module.find_article_in_zip(
    buffer.getvalue(), "https://example.org/exact"
)
assert match is not None
assert match["matchMethod"] == "EXACT URL"

assert module.find_article_in_zip(
    buffer.getvalue(), "https://example.org/missing"
) is None

service = (
    ROOT / "services/weather/GdeltArticleLocationService.qml"
).read_text(encoding="utf-8")
assert "Scope {" in service
assert "GdeltArticleLocationService" not in service
assert "gdelt_gkg_article_locations.py" in service
assert "function request(article)" in service
assert "ARTICLE URL / SEENDATE UNAVAILABLE" in service
assert service.count("Process {") == 1
assert service.count("Timer {") == 0
assert "Qt.openUrlExternally" not in service
assert "WebEngine" not in service

viewer = (
    ROOT / "widgets/weather/StationViewerHost.qml"
).read_text(encoding="utf-8")
assert 'label: stationViewer.locationLoading' in viewer
assert '"LOCATE MENTIONS"' in viewer
assert "signal locateRequested()" in viewer
assert "MENTIONED LOCATIONS // " in viewer
assert "modelData.typeLabel" in viewer
assert "modelData.latitude" in viewer
assert "modelData.longitude" in viewer
assert "MENTIONED PLACES ONLY // NOT VERIFIED EVENT LOCATION" in viewer
assert "Process {" not in viewer
assert "Timer {" not in viewer
assert "Qt.openUrlExternally" not in viewer
assert "import QtWebEngine" not in viewer

discovery = (
    ROOT / "widgets/weather/StationDiscovery.qml"
).read_text(encoding="utf-8")
assert "WeatherServices.GdeltArticleLocationService {" in discovery
assert "id: articleLocationService" in discovery
assert "articleLocationService.request(" in discovery
assert "newsLocationMatchesSelection" in discovery
assert 'ARTICLE → GKG MENTIONED LOCATIONS", state:"CONNECTED"' in discovery
assert 'NEWS → MAP LOCATION HANDOFF", state:"NOT WIRED"' in discovery

policy = (
    ROOT / "widgets/weather/StationViewerPolicy.js"
).read_text(encoding="utf-8")
assert "rawTime: shortText(row.rawTime, 40)" in policy
assert "language: shortText(row.language, 48)" in policy
assert "domain: shortText(row.domain, 100)" in policy

workflow = (
    ROOT / ".github/workflows/weather-teardown-contracts.yml"
).read_text(encoding="utf-8")
assert "python3 tests/weather/test_station_news_gkg_locations.py" in workflow

print("Weather NEWS exact GKG article mentioned-location lookup: PASS")
