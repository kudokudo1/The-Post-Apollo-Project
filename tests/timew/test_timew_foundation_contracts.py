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
assert window.count("Process {") == 1
assert "worldLookup.running" in window
assert 'onLeftClicked: timew.chooseWorldZone(modelData.id)' in window
assert 'text: timew.worldTimeSnapshot.readout' in window
assert 'text: timew.worldClockReady' in window
assert 'text: "WORLD // CURRENT TIME"' in window
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
