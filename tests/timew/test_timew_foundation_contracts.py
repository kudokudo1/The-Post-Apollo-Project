#!/usr/bin/env python3
"""Source contracts for the isolated TimeW M1 chassis.

These are source-level checks, not proof of a rendered QML/live desktop.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
window = (ROOT / "widgets/TimeW.qml").read_text(encoding="utf-8")
clock = (ROOT / "modules/Clock.qml").read_text(encoding="utf-8")
preview = (ROOT / "tests/timew/timew_preview.qml").read_text(encoding="utf-8")
finance = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")

# Real shared components, standalone preview, no duplicate control system.
for name in ("PanelWindow {", "WindowPanelFrame {", "ActionButton {",
             "ModeButton {", "SystemClock {"):
    assert name in window, name
assert 'import "../../widgets"' in preview
assert "Scope {" in preview and "TimeW {" in preview
assert "menuOpen: true" in preview
assert "Clock {}" in shell  # The existing bar clock remains mounted.

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

# Existing TimeW visual language: header, cyan divider, unbordered main modes.
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
for primitive in ("Process {", "JsonAdapter {", "FileView {", "swaymsg",
                  "grim ", "onTriggered: capture", "kill -"):
    assert primitive not in window, primitive

print("TIMEW M1 SOURCE CONTRACTS: PASS (runtime preview still required)")
