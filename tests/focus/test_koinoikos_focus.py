#!/usr/bin/env python3
"""Offline contract tests for the opt-in Koinoikos native/QS focus bridge."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "koinoikos_focus", ROOT / "scripts/koinoikos_focus.py")
assert spec and spec.loader
focus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(focus)


# Only open, positive-size registered Quickshell surfaces are eligible.
menus = focus.menu_windows({"surfaces": [
    {"id": "hospital", "x": 1200, "y": 0, "w": 500, "h": 700},
    {"id": "git", "x": 1900, "y": 0, "w": 400, "h": 700},
    {"id": "hidden", "x": 0, "y": 0, "w": -1, "h": 700},
]})
assert [m["id"] for m in menus] == ["hospital", "git"]
assert focus.nearest(menus, menus[0], "right")["id"] == "git"
assert focus.nearest(menus, menus[1], "right") is None

# Runtime router contract: native Sway focus must NEVER be called, even when
# QS disappears, the selected widget closes, or an arrow reaches the edge.
seen = []
saved_snapshot, saved_qs, saved_command = focus.snapshot, focus.qs, focus.command

def spy_qs(method, *args):
    seen.append((method, *args))
    return 0, "true"

def forbid_sway(*args, **kwargs):
    raise AssertionError(f"Widget focus must not run Sway commands: {args}")

focus.qs = spy_qs
focus.command = forbid_sway
try:
    focus.snapshot = lambda: {"active": True, "owner": "hospital", "surfaces": menus}
    assert focus.move("right")
    assert seen == [("select", "git")], seen
    seen.clear()

    focus.snapshot = lambda: {"active": True, "owner": "git", "surfaces": menus}
    assert not focus.move("right")
    assert seen == [], seen

    focus.snapshot = lambda: {"active": True, "owner": "native", "surfaces": menus}
    assert focus.move("right")  # Unknown owner anchors AND moves on first arrow.
    assert seen == [("select", "git")], seen
    seen.clear()

    focus.snapshot = lambda: {"active": True, "owner": "closed", "surfaces": menus}
    assert focus.move("right")  # Closed owner also moves on the first arrow.
    assert seen == [("select", "git")], seen
    seen.clear()

    focus.snapshot = lambda: {"active": True, "owner": "", "surfaces": []}
    assert not focus.move("right")
    assert seen == [], seen

    focus.snapshot = lambda: None
    assert not focus.move("right")  # No QS = no-op; not native focus.
    assert seen == [], seen

    # First held direction begins the QS session and actually navigates.
    snapshots = iter([
        {"active": False, "owner": "", "surfaces": menus},
        {"active": True, "owner": "hospital", "surfaces": menus},
    ])
    focus.snapshot = lambda: next(snapshots)
    assert focus.move("right")
    assert seen == [("begin",), ("select", "git")], seen
    seen.clear()
finally:
    focus.snapshot, focus.qs, focus.command = saved_snapshot, saved_qs, saved_command

sway = (ROOT / "config/sway/koinoikos-focus.conf").read_text()
assert 'bindsym Mod4+grave mode "Koinoikos Focus"' in sway
assert "Mod4+Shift+grave" not in sway
assert "bindsym Mod4+grave exec" not in sway, "Prefix must not switch widget focus"
assert 'koinoikos_focus.py" cycle' not in sway, "Unintended prefix-cycle action must be removed"
assert "bindsym Escape" not in sway, "No sticky Escape-driven mode"
mode_body = sway.split('mode "Koinoikos Focus" {', 1)[1]
for key, direction in (
    ("Left", "left"), ("Right", "right"), ("Up", "up"), ("Down", "down"),
    ("h", "left"), ("l", "right"), ("k", "up"), ("j", "down"),
):
    expected = f'bindsym --no-repeat Mod4+grave+{key} exec python3 '
    assert expected in mode_body, expected
    assert f'koinoikos_focus.py" move {direction}' in mode_body
for physical_release in ("Mod4+grave", "Super_L", "Super_R"):
    assert f"bindsym --release {physical_release} exec" in mode_body
assert mode_body.count('koinoikos_focus.py" exit') == 3

router_source = (ROOT / "scripts/koinoikos_focus.py").read_text()
assert "swaymsg" not in router_source, "Widget focus must not invoke native Sway focus"
assert "native_windows" not in router_source
assert "beginAndAdvance" not in router_source
assert '"cycle"' not in router_source

# No Sway or Qt action on Super+grave alone; first direction invokes begin
# followed by selection, and release ends the transient broker session.
saved_qs = focus.qs
calls = []
def capture_qs(method, *args):
    calls.append((method, *args))
    return 0, "true"
focus.qs = capture_qs
try:
    assert focus.main(["exit"]) == 0
    assert calls == [("end",)], calls
finally:
    focus.qs = saved_qs

broker = (ROOT / "components/RelationshipFocusBroker.qml").read_text()
shell = (ROOT / "shell.qml").read_text()
for expected in (
    'target: "relationshipFocus"', "function begin(): bool",
    "function end(): void", "function snapshot(): string",
    "function select(id: string): bool",
    "previousOwnerRestorationRequested",
):
    assert expected in broker, expected
require_qmldir = (ROOT / "components/qmldir").read_text(encoding="utf-8")
assert "RelationshipFocusBroker 1.0 RelationshipFocusBroker.qml" in require_qmldir
assert 'property string owner: ""' in broker
assert 'owner = "native"' not in broker
assert 'visible.length > 0 ? visible[0].id : ""' in broker
assert 'property string lastWidgetOwner: ""' in broker
assert "lastWidgetOwner = id;" in broker
assert "function advanceWidget()" not in broker
assert "function beginAndAdvance(): bool" not in broker
assert "function advance(): bool" not in broker
assert 'id: relationshipFocus' in shell
for label in ("appcontrol", "hospital", "git", "cpu", "weather"):
    assert label in broker, label
    assert 'relationshipFocus.owner === "' + label + '"' in shell

for path, expected in (
    ("widgets/HospitalW.qml", "relationshipFocused ? 0.46"),
    ("widgets/GitW.qml", "root.relationshipFocused ? 0.46"),
    ("widgets/CpuPlusW.qml", "relationshipFocused ? 0.68"),
    ("widgets/weather/WeatherStationW.qml", "relationshipFocused ? 0.58"),
    ("widgets/AppControlW.qml", "relationshipFocused ? 0.68"),
):
    data = (ROOT / path).read_text(encoding="utf-8")
    assert "property bool relationshipFocusModeActive: false" in data, path
    assert "property bool relationshipFocused: false" in data, path
    assert expected in data, path

# Previously accepted intra-menu keys and compositor routing remain separate.
hospital = (ROOT / "widgets/HospitalW.qml").read_text()
assert 'sequence: "Tab"' in hospital
assert 'sequence: "Shift+Tab"' in hospital
assert 'onActivated: root.cycleBed(-1)' in hospital
assert 'onActivated: root.cycleBed(1)' in hospital
assert 'sequence: "Ctrl+Tab"' in shell
assert '!relationshipFocus.active' in shell
print("KOINOIKOS FOCUS MODE CONTRACTS // PASS")
