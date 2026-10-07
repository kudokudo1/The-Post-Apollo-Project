#!/usr/bin/env python3
"""Contracts for Weather Station graphical-effect teardown safety."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STATION = ROOT / "widgets" / "weather" / "StationHome.qml"

text = STATION.read_text(encoding="utf-8")

for band in ("spaceBand", "skyBand", "groundBand"):
    pattern = re.compile(
        rf"""DropShadow\s*\{{.*?
        anchors\.fill:\s*{band}.*?
        source:\s*
        {band}\.Window\.window\s*!==\s*null\s*
        \?\s*{band}\s*
        :\s*null.*?
        visible:\s*source\s*!==\s*null
        """,
        re.S | re.X,
    )
    assert pattern.search(text), (
        f"{band} shadow must disconnect its ShaderEffect source "
        "when the source item leaves its window"
    )

print("Weather Station shader teardown contracts: PASS")
