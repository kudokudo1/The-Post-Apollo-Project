#!/usr/bin/env python3
"""Source contracts for the isolated TimeW M1 chassis.

These are source-level checks, not proof of a rendered QML/live desktop.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
window = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
clock = (ROOT / "modules/Clock.qml").read_text(encoding="utf-8")
preview = (ROOT / "timew_click_preview.qml").read_text(encoding="utf-8")
finance = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")

# Real shared components, standalone preview, no duplicate control system.
for name in ("PanelWindow {", "WindowPanelFrame {", "ActionButton {",
             "ModeButton {", "SystemClock {"):
    assert name in window, name
assert 'import "widgets"' in preview and 'import "modules"' in preview
assert "Scope {" in preview and "TimeW {" in preview
assert "Clock {" in preview and "timeWindow: timewWindow" in preview
assert "screen: previewDockWindow.screen" in preview
# Integrated bar clock still owns one visible dock, now paired with TimeW.
clock_section = shell.split("        // Clock and TimeW.", 1)
assert len(clock_section) == 2, "Missing TimeW dock section"
clock_section = clock_section[1].split("        // Notifications", 1)[0]
assert shell.count("            Clock {") == 1, "Duplicate bar clock"
assert "width: clockDock.width" in clock_section
assert "height: clockDock.height" in clock_section
assert "id: clockDock" in clock_section
assert "timeWindow: timewWindow" in clock_section
assert "TimeW {" in clock_section
assert "id: timewWindow" in clock_section
assert 'screen: Quickshell.screens.find(s => s.name === "DP-5")' in clock_section
assert "keyboardActive: !relationshipFocus.active" in clock_section
assert "relationshipFocusModeActive: relationshipFocus.active" in clock_section
assert "anchors.fill: parent" not in clock_section, "Clock uses self-sized geometry"
assert shell.index("        // Clock and TimeW.") < shell.index("        // Notifications")


# No accidental clock-format or dock-chassis rewrite.
assert "property bool is24Hour: false" in clock
assert "property var timeWindow: null" in clock
assert "onRightClicked: {" in clock
assert "clockArea.is24Hour = !clockArea.is24Hour;" in clock
assert "onLeftClicked: {" in clock
assert "clockArea.timeWindow.toggle();" in clock
assert 'console.log("clockButton clicked");' in clock
assert "SystemClock.Seconds" in clock
assert "implicitHeight: 50" in clock

# The M1 window uses a known existing size rather than a new global metric.
for dim in ("frameWidth: 432", "frameHeight: 768", "glowGutter: 12"):
    assert dim in finance and dim in window, dim
assert "visible: true" in window
assert "width: timew.menuOpen ? timew.frameWidth : 0" in window
assert "height: timew.menuOpen ? timew.frameHeight : 0" in window
assert "WlrKeyboardFocus.OnDemand" in window
assert "WlrKeyboardFocus.Exclusive" not in window
assert "focusable: standardKeysAvailable" in window
assert "relationshipFocusModeActive" in window
assert "relationshipFocused" in window

# Mode changes and Escape are actual UI interactions.
for mode in ('id: "clock"', 'id: "calc"', 'id: "tools"',
             'id: "machine"'):
    assert mode in window, mode
assert "function chooseMode(index)" in window
assert "function cycleMainMode(direction)" in window
assert "onTriggered: timew.chooseMode(index)" in window
assert "onMenuOpenChanged:" in window
assert "Keys.onShortcutOverride:" in window
assert "Keys.onPressed:" in window
for key in ("Tab", "Shift+Tab", "Esc"):
    assert 'sequence: "' + key + '"' in window
assert "onLeftClicked: timew.menuOpen = false" in window

# TimeW-specific white identity and screenshot-corrected top alignment.
# Preserve the 8px right-dock top inset; adding 50px for dock height placed
# the TimeW frame too low in the 2026-10-22 operator screenshot.
assert "anchors.topMargin: 8" in shell
assert "implicitHeight: 50" in clock
assert "    margins {\n        top: 8\n        right: 13\n    }" in window
assert "top: 8 + 50 - timew.glowGutter" not in window
assert "readonly property color semanticColor: Colors.white" in window
assert "glowColor: timew.semanticColor" in window
assert "borderColor: timew.semanticColor" in window
assert "idlePrimaryColor: timew.semanticColor" in window
assert 'text: timew.selectedName + " // TIMEW"\n                        color: timew.semanticColor' in window
# TimeW displays the tested local-time formatter using its preexisting
# SystemClock tick. There is no second timer, backend, or global preference.
assert 'import "../services/hub/ApolloHubTimePolicy.js" as LocalTimePolicy' in window
assert "LocalTimePolicy.snapshot(localClock.date.getTime(), use24Hour)" in window
assert window.count("SystemClock {") == 1
assert window.count("Timer {") == 1
assert "interval: 30000" in window
assert "running: timew.menuOpen && timew.selectedMode === \"clock\"" in window
assert "property bool use24Hour: true" in window
# Clock-page presentation: 24H retains PM, 12H retains leading zero;
# the time/control are orange in 24H and cyan in 12H (not chassis white).
assert "readonly property color clockReadoutColor:" in window
assert "use24Hour ? Colors.orange : Colors.cyan" in window
assert "readonly property string clockReadoutText:" in window
assert "localTimeSnapshot.state === \"ready\"" in window
assert "use24Hour ? localTimeSnapshot.time24" in window
assert "localTimeSnapshot.time12.slice(0, 8)" in window
assert '+ "//" + localTimeSnapshot.meridiem' in window
assert 'text: timew.clockReadoutText' in window
assert 'color: timew.clockReadoutColor' in window
assert 'accentColor: timew.clockReadoutColor' in window
assert "text: timew.localTimeSnapshot.displayTime" not in window
assert "text: timew.localTimeSnapshot.dateLabel" in window
assert "text: timew.localTimeSnapshot.utcOffsetLabel" in window
# Both local display modes now share the exact same font size.
assert "font.pixelSize: 22" in window
assert "font.pixelSize: timew.use24Hour ? 22 : 19" not in window
# The world-clock adapter reuses SystemClock seconds and only invokes the
# system's zone database via a read-only, fixed argv date command while open.
assert 'import Quickshell.Io' in window
assert 'import "../services/time/WorldClockPolicy.js" as WorldClockPolicy' in window
assert "readonly property var worldZones:" in window
for zone in ("UTC", "America/New_York", "Europe/London", "Asia/Tokyo"):
    assert '"'+zone+'"' in window, zone
assert "WorldClockPolicy.snapshot(localClock.date.getTime()," in window
assert 'command: ["date", "+%z"]' in window
assert 'environment: { TZ: worldLookupZone, LC_ALL: "C" }' in window
assert "Process {" in window
assert window.count("Process {") == 4
assert "worldLookup.running" in window
assert 'onLeftClicked:' in window
assert 'timew.chooseWorldZone(modelData.id)' in window
assert 'text: timew.worldTimeSnapshot.readout' in window
assert 'text: timew.worldClockReady' in window
assert 'text: "WORLD // CURRENT TIME"' in window
# Keep exactly four presets, plus WORLD as the searchable-mode selector.
assert 'property bool worldModeActive: false' in window
assert 'property string selectedQuickZone: "UTC"' in window
assert 'property string selectedSearchedZone: ""' in window
assert 'property string selectedWorldZone: "UTC"' in window
assert 'property string worldSearchQuery: ""' in window
assert 'import QtQuick.Controls' in window
assert 'import "../services/time/WorldZoneSearch.js" as WorldZoneSearch' in window
assert 'zoneCatalogLookup.exec(["timedatectl", "list-timezones", "--no-pager"])' in window
assert 'WorldZoneSearch.parseCatalog(this.text)' in window
assert 'WorldZoneSearch.search(worldZoneCatalog, worldSearchQuery,' in window
assert 'WorldZoneSearch.MAX_ZONES, worldCountryIndex)' in window
assert '120, worldCountryIndex)' not in window
assert 'WorldZoneSearch.parseCountryZones(worldCountryZoneTable, worldCountryNames)' in window
assert 'WorldZoneSearch.parseCountryNames(this.text)' in window
assert 'isoCountryLookup.exec(["cat", "/usr/share/zoneinfo/iso3166.tab"])' in window
assert 'zoneCountryLookup.exec(["cat", "/usr/share/zoneinfo/zone.tab"])' in window
assert 'property bool worldCountryLookupStarted: false' in window
assert 'function loadWorldCountryMetadata()' in window
assert 'loadWorldCountryMetadata();' in window
assert 'worldCountryLookupStarted = true;' in window
# ListView virtualizes many search hits while the host NeonScrollBar
# represents overflow rather than stretching TimeW past its frame.
assert 'id: worldSearchResults' in window
assert 'ListView {' in window
assert 'NeonScrollBar {' in window
assert 'flickable: worldSearchResults' in window
assert 'handleStyle: "star"' in window
assert 'handleColor: Colors.magenta' in window
assert 'handleBorderColor: Colors.magenta' in window
assert 'handleColor: Colors.white' not in window
assert 'geometryMode: "viewport"' in window
# The ListView reserves a separate gutter: its right edge is five px
# shy of the popup edge after the star track, while the rail begins
# only three px inward, leaving two px between rows and star rail.
assert 'id: worldSearchRail' in window
assert 'rightMargin: worldSearchRail.crossExtent + 5' in window
assert 'x: worldSearchPopup.width - width - 3' in window
assert 'y: worldSearchResults.y' in window
assert 'height: worldSearchResults.height' in window
assert 'Math.min(212, 34' in window
assert 'id: worldSearchCount' in window
assert 'top: worldSearchCount.bottom' in window
assert 'topMargin: 4' in window
assert '"ITEMS // "' in window
assert '"MATCHES // "' in window
assert '+ timew.worldSearchMatches.length' in window
assert 'modelData.country + " // "' in window
assert 'modelData.label + " // "' not in window
assert 'interactive: contentHeight > height' in window
assert 'model: timew.worldSearchMatches' in window
assert 'modelData.country' in window
assert 'TYPE CITY OR COUNTRY' in window
assert 'WorldZoneSearch.contains(worldZoneCatalog, zoneId)' in window
assert 'function toggleWorldMode()' in window
assert 'function selectWorldSearchResult(zoneId)' in window
assert 'placeholderText: "SEARCH CITY / TIME ZONE"' in window
assert 'id: worldSearchInput' in window
assert 'id: worldSearchPopup' in window
assert 'timew.worldSearchMatches[0].id' in window
assert 'timew.selectWorldSearchResult(' in window
assert 'available: !timew.worldModeActive' not in window
assert 'if (worldModeActive\n                || !worldZones.some' not in window
assert 'worldModeActive = false;\n        selectedQuickZone = zoneId;' in window
assert 'dismissWorldSearchPopup();\n        selectActiveZone(zoneId);' in window
assert 'selected: !timew.worldModeActive' in window
assert 'label: "WORLD"' in window
assert 'selected: timew.worldModeActive' in window
# The WORLD selector is the leftmost of five *enabled* choices, while
# the arrow sits LEFT of a shorter search field.
strip = window.split('id: worldZoneStrip', 1)[1]
assert strip.index('id: worldModeButton') < strip.index('model: timew.worldZones')
assert 'id: worldDropdownArrow' in window
assert 'label: "▾"' in window
assert 'onLeftClicked: timew.toggleWorldDropdown()' in window
assert 'id: worldSearchRow' in window
assert 'worldSearchRow.width' in window
assert '- worldDropdownArrow.width' in window
assert 'function toggleWorldDropdown()' in window
assert 'function dismissWorldSearchPopup()' in window
assert 'function openWorldSearchPopup()' in window
assert 'onPressed: timew.openWorldSearchPopup()' in window
# Typing is magenta and the Qt 6 cursor delegate renders orange.
search_field = window.split('TextField {\n                                    id: worldSearchInput', 1)[1].split('background: Rectangle', 1)[0]
assert 'color: Colors.magenta' in search_field
assert 'cursorDelegate: Rectangle {' in search_field
assert 'width: 2\n                                        color: Colors.orange' in search_field
# Popup is painted above the footer and below the shortcuts, so all
# five buttons still accept clicks with results visible.
assert 'z: timew.worldSearchPopupOpen ? 20 : 0' in window
assert 'y: worldZoneStrip.y + worldZoneStrip.height' in window
assert 'visible: !(timew.selectedMode === "clock"' in window
# Passive TapHandler keeps other controls usable. Clicking elsewhere in
# the menu closes the results and releases editor focus.
assert 'gesturePolicy: TapHandler.DragThreshold' in window
assert 'onTapped: function(point, button)' in window
assert 'const withinSearch =' in window
assert 'const withinPopup =' in window
assert 'if (!withinSearch && !withinPopup)' in window
assert 'timew.dismissWorldSearchPopup();' in window
assert 'worldSearchInput.focus = false;' in window
assert 'onLeftClicked: timew.toggleWorldMode()' in window
assert 'standardKeysAvailable && !worldSearchInput.activeFocus' in window
assert 'enabled: timew.navigationKeysAvailable' in window
assert 'WORLD // SELECT A SEARCH RESULT' in window
assert '"ZONE DIRECTORY UNAVAILABLE"' in window
assert window.count('onTextEdited:') == 1
# No dynamic command composition or arbitrary typed TZ values.
assert 'command: ["date", "+%z"]' in window
assert 'worldLookup.exec({' in window
assert 'environment: { TZ: worldLookupZone, LC_ALL: "C" }' in window
assert '["sh", "-c"' not in window
assert '["bash", "-c"' not in window
assert 'LOCAL + WORLD // LIVE // CONVERTER NEXT' in window
assert "label: timew.use24Hour ? \"24H\" : \"12H\"" in window
assert "onLeftClicked: timew.use24Hour = !timew.use24Hour" in window
assert "fillColor: Colors.black" in window
assert "border.color: Colors.cyan" in window
assert "accentColor: Colors.red" in window

# Universal visual language remains: magenta header, cyan divider, borderless modes.
assert 'text: "TIME // W"' in window
assert "color: Colors.magenta" in window
assert "id: headerDivider" in window
assert "height: 2\n                color: Colors.cyan" in window
assert "bordered: false" in window
assert "trackDefaultGlowsLocally: true" in window

# The shared destructive Close is the real U+00D7 X, red in idle and hover.
start = window.index("id: closeButton")
end = window.index("onLeftClicked: timew.menuOpen = false", start)
close = window[start:end]
for prop in ('label: "×"', "labelPixelSize: 22", "destructive: true",
             "accentColor: Colors.red", "hoverForegroundColor: Colors.red",
             "hoverBorderColor: Colors.red"):
    assert prop in close, prop

# This milestone must not pretend to implement a timer, background capture,
# Sway control or durable state. Future milestones must update these contracts.
assert "NO SCREENSHOTS OR RESTORATION ACTIVE" in window
assert "STOPWATCH + TIMERS // NOT CONNECTED" in window
assert "FOUNDATION PREVIEW // UI ONLY" in window
for primitive in ("JsonAdapter {", "FileView {", "swaymsg",
                  "grim ", "onTriggered: capture", "kill -",
                  '["sh", "-c"', '["bash", "-c"'):
    assert primitive not in window, primitive

print("TIMEW M1 SOURCE CONTRACTS: PASS (runtime preview still required)")
