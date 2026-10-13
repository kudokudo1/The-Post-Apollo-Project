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
    assert focus.move("right")  # Legacy owner falls back to first widget ONLY.
    assert seen == [("select", "hospital")], seen
    seen.clear()

    focus.snapshot = lambda: {"active": True, "owner": "closed", "surfaces": menus}
    assert focus.move("right")
    assert seen == [("select", "hospital")], seen
    seen.clear()

    focus.snapshot = lambda: {"active": True, "owner": "", "surfaces": []}
    assert not focus.move("right")
    assert seen == [], seen

    focus.snapshot = lambda: None
    assert not focus.move("right")  # No QS = no-op; not native focus.
    assert seen == [], seen

    focus.snapshot = lambda: {"active": False, "owner": "", "surfaces": menus}
    assert not focus.move("right")
    assert seen == [], seen
finally:
    focus.snapshot, focus.qs, focus.command = saved_snapshot, saved_qs, saved_command

sway = (ROOT / "config/sway/koinoikos-focus.conf").read_text()
for expected in (
    "Mod4+grave exec", 'mode "Koinoikos Focus"',
    "bindsym Escape", "swaymsg mode default",
    "bindsym h exec", "bindsym j exec", "bindsym k exec",
    "bindsym l exec", "bindsym Left", "bindsym Right",
    "bindsym Up", "bindsym Down",
):
    assert expected in sway, expected
assert "Mod4+Shift+grave" not in sway, "Shift must not be required for Koinoikos entry"
router_source = (ROOT / "scripts/koinoikos_focus.py").read_text()
assert "swaymsg" not in router_source, "Widget focus must not invoke native Sway focus"
assert "native_windows" not in router_source
assert '"native":' not in router_source

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
