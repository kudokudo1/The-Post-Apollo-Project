#!/usr/bin/env python3
"""CPU++ SETTINGS/LOCATION M2 navigation, Explore expiry and safety contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cpu = (root / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
location = (root / "widgets/cpuplus/CpuPlusSettingsLocationPane.qml").read_text(encoding="utf-8")
explore = (root / "widgets/cpuplus/CpuPlusExploreLocationPanel.qml").read_text(encoding="utf-8")

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
    "SAVED HOME", "SHARED CONTEXT",
    "NOT SET", "NOT WIRED", "SAVE HOME",
    "HOME SAVED // PERSISTENT", "PLACE STORAGE NOT READY",
    "registry.saveHome(", "registry.canSaveHome", "registry.homePlace",
    "CpuPlusExploreLocationPanel {", "id: explorePanel",
    "explorePanel.editingText", "registry.effectivePlace",
    "registry.contextKind",
):
    assert token in location, token

for token in (
    "EXPLORE LOCATION", "NOT ACTIVE", "EXPIRED // HOME",
    "DESTINATION NAME", "EXPLORATION DURATION",
    "30M", "2H", "1D", "MANUAL",
    "EXPLORE HERE", "RETURN HOME",
    "registry.exploreHere(", "registry.returnHome()",
    "registry.remainingMs", "registry.activeExplore",
    "registry.canChangeExplore", "registry.hasStoredExplore",
    "function onStorageStateChanged()",
):
    assert token in explore, token

# The pane edits Home through one shared service. It is not itself a
# geolocation provider, file writer, weather adapter or alert-point owner.
for forbidden in ("Process {", "FileView {", "JsonAdapter {",
                  "Quickshell.env(", "Qt.openUrlExternally"):
    assert forbidden not in location, forbidden
    assert forbidden not in explore, forbidden

assert explore.count("Keys.onEscapePressed:") == 3
assert "readonly property bool editingText:" in explore
assert "enabled: explorePanel.canExplore" in explore
assert "enabled: explorePanel.canReturnHome" in explore
assert "LOCATION ROUTING" not in explore

assert "import qs.services.location" in cpu
assert "registry: PlaceRegistry" in cpu
assert '!(selectedModeIndex === 4 && settingsLocationPane.editingText)' in cpu
assert "readonly property bool editingText:" in location
assert location.count("Keys.onEscapePressed:") == 3
assert "awaitingSave = true" in location
assert 'locationPane.feedback = "HOME SAVED // PERSISTENT"' in location
assert "function onStorageStateChanged()" in location

# Single canonical writer, versioned policy, atomic disk save and no
# implicit IP-based coordinates or silently redirected alert locations.
store = (root / "services/location/PlaceRegistry.qml").read_text(encoding="utf-8")
policy = (root / "services/location/PlacePolicy.js").read_text(encoding="utf-8")
qmldir = (root / "services/location/qmldir").read_text(encoding="utf-8")
for token in ("pragma Singleton", "atomicWrites: true", "FileView {",
              'Quickshell.dataDir + "/places-v1.json"',
              "function saveHome(", "pendingDocument = result.document",
              "onSaved:", "onSaveFailed:", "PlacePolicy.parse(raw)",
              "PlacePolicy.withHome(",
              "function exploreHere(", "function returnHome(",
              "PlacePolicy.withExplore(", "PlacePolicy.withoutExplore(",
              "readonly property var activeExplore:",
              "readonly property var effectivePlace:",
              "readonly property string contextKind:",
              "clockMs = Date.now()", "running: registry.activeExplore !== null"):
    assert token in store, token
forbidden_store = ("Process {", "Qt.openUrlExternally", "https://", "http://",
                   "POST_APOLLO_NWS_ALERT_POINT")
for token in forbidden_store:
    assert token not in store, token
assert 'singleton PlaceRegistry 1.0 PlaceRegistry.qml' in qmldir
for token in ('const SCHEMA = "post-apollo.places.v1";', 'source:"MANUAL"',
              "function coordinate(", "function parse(", "function withHome(",
              "function withExplore(", "function withoutExplore(",
              "function activeExplore(", "function effectivePlace(",
              "function contextKind("):
    assert token in policy, token

assert 'required property var systemTelemetry' in cpu
assert 'required property var fanControl' in cpu
assert "id: monitorSelectorScroll" in cpu
assert "id: sharedInstrumentScroll" in cpu
assert "function selectSystemSubMode(category)" in cpu
assert "function selectThermalSubMode(mode)" in cpu

print("CPU++ SETTINGS / LOCATION M2 Home + Explore navigation: PASS")
