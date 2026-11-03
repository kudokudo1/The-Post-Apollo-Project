#!/usr/bin/env python3
"""CPU++ SETTINGS/LOCATION M0 navigation and no-write contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cpu = (root / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
location = (root / "widgets/cpuplus/CpuPlusSettingsLocationPane.qml").read_text(encoding="utf-8")

# Preserve all original mode positions and add SETTINGS only at the end.
modes = cpu[cpu.index("readonly property var modes: ["):cpu.index("function open()")]
offsets = [modes.index('name: "' + name + '"') for name in (
    "FAVORITES", "PROCESS", "THERMAL", "SYSTEM", "SETTINGS"
)]
assert offsets == sorted(offsets)
assert modes.count('name: "SETTINGS"') == 1
assert 'symbol: "⚙"' in modes
assert "model: cpuPlusWindow.modes" in cpu
assert "cpuPlusWindow.selectMode(index);" in cpu

for token in (
    'property string settingsSubMode: "LOCATION"',
    'name: "LOCATION", key: "LOCATION", symbol: "⌖"',
    "function selectSettingsSubMode(key)",
    "settingsSubModes.some(",
    "settingsSubMode = next;",
    "id: settingsCategorySummary",
    "cpuPlusWindow.settingsSubModes",
    "cpuPlusWindow.settingsSubMode === String(modelData.key)",
    "cpuPlusWindow.selectSettingsSubMode(modelData.key)",
    "CpuPlusSettingsLocationPane {",
    "id: settingsLocationPane",
    'cpuPlusWindow.settingsSubMode === "LOCATION"',
):
    assert token in cpu, token

for token in (
    "HOME LOCATION", "EXPLORE LOCATION", "SHARED CONTEXT",
    "NOT CONNECTED", "NOT ACTIVE", "NOT WIRED",
    "NO LOCATION IS READ, SAVED OR CHANGED BY THIS MENU YET.",
):
    assert token in location, token

# This milestone must not silently own geolocation, provider sessions,
# emergency alert targeting or changes to machine-wide settings.
for forbidden in (
    "Process {", "FileView {", "JsonAdapter {", "MouseArea {",
    "onClicked:", "Quickshell.env(", "Qt.openUrlExternally",
):
    assert forbidden not in location, forbidden

assert 'required property var systemTelemetry' in cpu
assert 'required property var fanControl' in cpu
assert "id: monitorSelectorScroll" in cpu
assert "id: sharedInstrumentScroll" in cpu
assert "function selectSystemSubMode(category)" in cpu
assert "function selectThermalSubMode(mode)" in cpu

print("CPU++ SETTINGS / LOCATION M0 navigation and no-write boundary: PASS")
