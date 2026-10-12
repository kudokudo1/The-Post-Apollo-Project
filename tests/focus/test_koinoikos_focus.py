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


def node(con_id, x, y, focused=False):
    return {
        "type": "con", "id": con_id, "app_id": "kitty",
        "window": None, "focused": focused,
        "rect": {"x": x, "y": y, "width": 300, "height": 200},
        "nodes": [], "floating_nodes": [],
    }


tree = {
    "type": "root",
    "nodes": [
        {"type": "output", "nodes": [
            {"type": "workspace", "visible": True,
             "nodes": [node(11, 0, 0, True), node(12, 400, 0)],
             "floating_nodes": [node(13, 0, 300)]},
            {"type": "workspace", "visible": False,
             "nodes": [node(14, 800, 0)], "floating_nodes": []},
        ], "floating_nodes": []},
    ], "floating_nodes": [],
}
native, selected = focus.native_windows(tree)
assert selected == "native:11"
assert [n["con_id"] for n in native] == [11, 12, 13]
origin = native[0]
assert focus.nearest(native, origin, "right")["con_id"] == 12
assert focus.nearest(native, origin, "down")["con_id"] == 13
assert focus.nearest(native, origin, "left") is None
assert focus.nearest(native, origin, "up") is None

menus = focus.menu_windows({"surfaces": [
    {"id": "hospital", "x": 1200, "y": 0, "w": 500, "h": 700},
    {"id": "bad", "x": 0, "y": 0, "w": -1, "h": 700},
]})
assert len(menus) == 1 and menus[0]["id"] == "hospital"
assert focus.nearest(native + menus, native[1], "right")["id"] == "hospital"

sway = (ROOT / "config/sway/koinoikos-focus.conf").read_text()
for expected in (
    "Mod4+Shift+grave", 'mode "Koinoikos Focus"',
    "bindsym Escape", "swaymsg mode default",
    "bindsym h exec", "bindsym j exec", "bindsym k exec",
    "bindsym l exec", "bindsym Left", "bindsym Right",
    "bindsym Up", "bindsym Down",
):
    assert expected in sway, expected

broker = (ROOT / "components/RelationshipFocusBroker.qml").read_text()
shell = (ROOT / "shell.qml").read_text()
for expected in (
    'target: "relationshipFocus"', "function begin(): bool",
    "function end(): void", "function snapshot(): string",
    "function select(id: string): bool",
    "previousOwnerRestorationRequested",
):
    assert expected in broker, expected
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
