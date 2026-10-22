#!/usr/bin/env python3
"""Contracts for Weather Station graphical-effect teardown safety."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PAGES = (
    ROOT / "widgets" / "weather" / "StationHome.qml",
    ROOT / "widgets" / "weather" / "StationGround.qml",
    ROOT / "widgets" / "weather" / "StationSky.qml",
    ROOT / "widgets" / "weather" / "StationSpace.qml",
)

for page in PAGES:
    text = page.read_text(encoding="utf-8")

    # The separated pages currently do not need source-sampling shadows.
    # If effects are added during later visual polish, they must use the
    # shared teardown-safe wrappers rather than raw DropShadow sources.
    assert not re.search(r"(?m)^\s*DropShadow\s*\{", text), (
        f"{page.name} must not use direct DropShadow sources"
    )

print("Weather Station shader teardown contracts: PASS")
