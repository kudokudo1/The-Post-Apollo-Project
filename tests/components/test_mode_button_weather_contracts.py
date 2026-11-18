#!/usr/bin/env python3
"""Weather Station main navigation now uses the native seven SUBJECTS families."""

from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
station = (root / "widgets/weather/WeatherStationW.qml").read_text(encoding="utf-8")
family_rail = (root / "widgets/weather/StationWorkspaceFamilyRail.qml").read_text(encoding="utf-8")
index_rail = (root / "widgets/weather/StationSubjectRail.qml").read_text(encoding="utf-8")
workspace = (root / "widgets/weather/StationWorkspaceSurface.qml").read_text(encoding="utf-8")
navigation = (root / "widgets/weather/StationWorkspaceNavigationPolicy.js").read_text(encoding="utf-8")
station_nav = (root / "widgets/weather/StationSubjectNavigator.qml").read_text(encoding="utf-8")

assert station.count("ModeButton {") == 0
assert "id: railColumn" not in station
assert "mainModes:" not in station
assert "subjectBrowserToggle" not in station
assert "StationWorkspaceFamilyRail {" in station
assert "StationSubjectRail {" in station
assert 'width: 160' in station
assert family_rail.count("ModeButton {") == 1
assert index_rail.count("ModeButton {") == 1
assert "model: Workspace.FAMILIES" in family_rail
assert 'onTriggered:' in family_rail
# This was changed in the merged W27 SERVICES-follow-family feature.
# Recheck that current family switching owns its real canonical policy.
assert 'familyRail.navigator.chooseFamily(modelData.id)' in family_rail
assert "function chooseFamily(targetFamily)" in station_nav
assert "Workspace.familySwitchTarget(currentPath,targetFamily)" in station_nav
assert "model: surface.activeTabs" in workspace

family_ids = re.findall(r'\{id:"(home|weather|cosmos|earth|media|magick|tools)",label:', navigation)
assert family_ids[:7] == ["home","weather","cosmos","earth","media","magick","tools"]

for token in ("function cycleMainMode(direction)","function moveNavigationCursor(direction)",
              "function activateNavigationCursor()","subjectNavigator.cycleSubjects(direction);",
              "subjectNavigator.moveCursor(direction);","subjectNavigator.activateCursor();"):
    assert token in station, token

print("Weather SUBECTS family navigation contracts: PASS")
