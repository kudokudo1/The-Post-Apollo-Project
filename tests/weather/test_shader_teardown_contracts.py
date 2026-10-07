#!/usr/bin/env python3
"""Contracts for Weather Station graphical-effect teardown safety."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STATION = ROOT / "widgets" / "weather" / "StationHome.qml"

text = STATION.read_text(encoding="utf-8")

for band in ("spaceBand", "skyBand", "groundBand"):
    pattern = re.compile(
        rf"""SafeDropShadow\s*\{{.*?
        anchors\.fill:\s*{band}.*?
        safeSource:\s*{band}
        """,
        re.S | re.X,
    )
    assert pattern.search(text), (
        f"{band} shadow must use the shared teardown-safe source wrapper"
    )

assert not re.search(r"(?m)^\s*DropShadow\s*\{", text), (
    "Weather Station must not regress to direct DropShadow sources"
)

print("Weather Station shader teardown contracts: PASS")
