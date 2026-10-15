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
    matches = [
        line for line in mode_body.splitlines()
        if line.split()[:4] == ["bindsym", "--no-repeat", f"Mod4+grave+{key}", "exec"]
        and line.rstrip().endswith(f'koinoikos_focus.py" move {direction}')
    ]
    assert len(matches) == 1, (key, direction, matches)
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
assert "KeyboardOwnershipCoordinator 1.0 KeyboardOwnershipCoordinator.qml" in require_qmldir
assert 'property string owner: ""' in broker
assert 'owner = "native"' not in broker
assert 'visible.length > 0 ? visible[0].id : ""' in broker
assert 'property string lastWidgetOwner: ""' in broker
assert "lastWidgetOwner = id;" in broker
# Regression: QsWindow/PanelWindow has no trustworthy Item x/y property.
# The actual operator IPC showed Git and Hospital x:null,y:null although
# both surfaces were open and had nonzero dimensions. Python discarded both.
# Derive coordinates from ShellScreen + anchors + margins, not window.x/y.
assert "function panelRect(w)" in broker
assert "const sx = Number(screen.x);" in broker
assert "const sy = Number(screen.y);" in broker
assert "const sw = Number(screen.width);" in broker
assert "const sh = Number(screen.height);" in broker
assert "const ml = Number(margins.left);" in broker
assert "const mr = Number(margins.right);" in broker
assert "const mt = Number(margins.top);" in broker
assert "const mb = Number(margins.bottom);" in broker
assert "anchors.left ? sx + ml" in broker
assert "anchors.right ? sx + sw - ww - mr" in broker
assert "anchors.top ? sy + mt" in broker
assert "anchors.bottom ? sy + sh - wh - mb" in broker
assert "const rect = panelRect(w);" in broker
assert "if (!rect)\n                continue;" in broker
assert "x: Math.round(w.x)" not in broker
assert "y: Math.round(w.y)" not in broker
# Python should remain strict. Null-geometry widgets are not valid targets;
# the broker must produce valid finite anchored coordinates instead.
assert focus.menu_windows({"surfaces": [
    {"id": "git", "x": None, "y": None, "w": 1148, "h": 816},
    {"id": "hospital", "x": None, "y": None, "w": 772, "h": 1346}
]}) == []
fixed = focus.menu_windows({"surfaces": [
    {"id": "hospital", "x": 1540, "y": 30, "w": 772, "h": 1346},
    {"id": "git", "x": 1370, "y": 20, "w": 1148, "h": 816}
]})
assert len(fixed) == 2
assert focus.nearest(fixed, fixed[1], "left") is not None


assert "function advanceWidget()" not in broker
assert "function beginAndAdvance(): bool" not in broker
assert "function advance(): bool" not in broker
assert 'id: relationshipFocus' in shell
for label in ("appcontrol", "hospital", "git", "cpu", "weather", "notifications"):
    assert label in broker, label
    assert 'relationshipFocus.owner === "' + label + '"' in shell

for path, expected in (
    ("widgets/HospitalW.qml", "relationshipFocused ? 0.46"),
    ("widgets/GitW.qml", "root.relationshipFocused ? 0.46"),
    ("widgets/CpuPlusW.qml", "relationshipFocused ? 0.68"),
    ("widgets/weather/WeatherStationW.qml", "relationshipFocused ? 0.58"),
    ("widgets/AppControlW.qml", "relationshipFocused ? 0.68"),
    ("widgets/notifications/NotificationsHubW.qml", "root.relationshipFocused ? 0.70"),
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
# Shared overlay-focus acquisition: open/cursor/Koinoikos choose one menu;
# exclusive keyboard priority is a SHORT acquisition pulse, never a permanent
# condition simply because Git and Hospital are simultaneously open.
ownership = (ROOT / "components/KeyboardOwnershipCoordinator.qml").read_text()
for required in (
    'property string owner: ""',
    'property string boostOwner: ""',
    'function claim(id, reason)',
    'function release(id)',
    'releaseBoost.restart()',
    'onTriggered: coordinator.boostOwner = ""',
):
    assert required in ownership, required
assert 'interval: 120' in ownership
# All Koinoikos candidates must be known to the same logical coordinator.
# Only the three prior Wlr layer-shell consumers may receive the bounded
# Exclusive pulse; stage 1 must not force it onto Weather, CPU or AppControl.
import re

registered = set(re.findall(r'\{ id: "([^"]+)", item: broker\.', broker))
owner_list = ownership.split('readonly property var widgetIds: [', 1)[1].split(']', 1)[0]
supported = set(re.findall(r'"([^"]+)"', owner_list))
assert registered == supported, (registered, supported)
pulse_list = ownership.split('readonly property var pulseIds: [', 1)[1].split(']', 1)[0]
pulsed = set(re.findall(r'"([^"]+)"', pulse_list))
assert pulsed == {"git", "hospital", "notifications"}, pulsed
assert 'if (widgetIds.indexOf(id) < 0)' in ownership
assert 'if (pulseIds.indexOf(id) >= 0)' in ownership
assert 'releaseBoost.stop();' in ownership
assert 'boostOwner = "";' in ownership
shell = (ROOT / "shell.qml").read_text()
assert "KeyboardOwnershipCoordinator {" in shell
assert "property alias controlKeyboardOwner: keyboardOwnership.owner" in shell
assert 'shellRoot.requestControlKeyboard("git", "open")' in shell
assert 'shellRoot.requestControlKeyboard("hospital", "open")' in shell
assert 'shellRoot.requestControlKeyboard("notifications", "open")' in shell
assert 'shellRoot.requestControlKeyboard("git", "pointer")' in shell
assert 'shellRoot.requestControlKeyboard("hospital", "pointer")' in shell
assert 'shellRoot.requestControlKeyboard("notifications", "pointer")' in shell
assert 'keyboardOwnership.release("git")' in shell
assert 'keyboardOwnership.release("hospital")' in shell
assert 'keyboardOwnership.release("notifications")' in shell
assert 'keyboardLock: keyboardOwnership.boostOwner === "git"' in shell
assert 'keyboardLock: keyboardOwnership.boostOwner === "hospital"' in shell
assert 'keyboardLock: keyboardOwnership.boostOwner === "notifications"' in shell
assert '|| (hospitalWindow.menuOpen && gitWindow.menuOpen)' not in shell
assert 'keyboardOwnership.claim(owner, "koinoikos")' in shell
assert 'if (active && owner !== "")' in shell
assert 'owner === "git" || owner === "hospital"' not in shell
assert "function requestControlKeyboard(id, reason)" in shell
assert "relationshipFocus.selectOwner(id);" in shell

for path in ("widgets/GitW.qml", "widgets/HospitalW.qml",
             "widgets/notifications/NotificationsHubW.qml"):
    widget = (ROOT / path).read_text()
    assert 'onHoveredChanged: {' in widget
    assert 'root.keyboardOwnershipRequested();' in widget
    assert 'if (hovered && !root.keyboardActive)' not in widget
    assert "WlrKeyboardFocus.OnDemand" in widget
    assert "WlrKeyboardFocus.None" in widget
    assert "WlrKeyboardFocus.Exclusive" in widget
notifications = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
assert "property bool keyboardActive: false" in notifications
assert "property bool keyboardLock: false" in notifications
assert "WlrKeyboardFocus.OnDemand" in notifications
assert "WlrKeyboardFocus.None" in notifications
assert "WlrKeyboardFocus.Exclusive" in notifications
assert "id: notificationKeyboardAnchor" in notifications
assert "notificationKeyboardAnchor.forceActiveFocus()" in notifications
assert "menuOpen && keyboardActive && !searchInput.activeFocus" in notifications
for shortcut in ('"Tab"', '"Shift+Tab"'):
    assert 'sequence: ' + shortcut in notifications
assert 'notifications: notificationsHubWindow' in shell
assert 'notifications: null' in broker
assert '{ id: "notifications", item: broker.notifications }' in broker
assert (ROOT / "docs/window-keyboard-focus-contract.md").is_file()

# The focus diagnostic IPC is strictly observational: unlike the normal
# router it must not set Koinoikos mode, select a widget, or move Sway focus.
assert "function diagnose(): string" in broker
assert "return broker.diagnosticSnapshot();" in broker
assert "function diagnosticSnapshot()" in broker
assert 'logicalKeyboardOwner: hostOwner' in broker
assert 'focusBoostOwner: boostOwner' in broker
assert 'qtWindowActive:' in broker
assert 'qtActiveFocusItem:' in broker
assert "boostOwner: keyboardOwnership.boostOwner" in shell

# Brave under Git/Hospital is an ordinary native client, not a QS
# Koinoikos candidate. Read-only native-tree focus does NOT establish which
# layer-shell surface actually receives Tab.
import re
candidates = set(re.findall(r'\{ id: "([^"]+)", item: broker\.', broker))
assert candidates == {"appcontrol", "hospital", "git", "cpu",
                      "weather", "notifications"}
assert "brave" not in candidates

diag_path = ROOT / "scripts/focus_diagnostics.py"
diag_src = diag_path.read_text()
assert '("qs", "ipc", "call", "relationshipFocus", "diagnose")' in diag_src
assert 'invoke("swaymsg", "-t", "get_tree")' in diag_src
assert '"swaymsg", "-m", "-t", "subscribe"' in diag_src
assert 'def find_native_focused(tree:' in diag_src
assert 'focusedNativeContainer' in diag_src
# Assert forbidden executable argv patterns, not prose comments about safety.
for disallowed in ('invoke("swaymsg", "focus"',
                   'invoke("swaymsg", "mode"',
                   '"swaymsg", "focus"',
                   '"swaymsg", "mode"'):
    assert disallowed not in diag_src
assert (ROOT / "docs/focus-browser-underlay-test-20261015.md").is_file()

diag_spec = importlib.util.spec_from_file_location("focus_diagnostics", diag_path)
assert diag_spec and diag_spec.loader
diag = importlib.util.module_from_spec(diag_spec)
diag_spec.loader.exec_module(diag)
tree_fixture = {
    "id": 1, "focused": False,
    "nodes": [
        {"id": 2, "focused": False, "nodes": [], "floating_nodes": []},
        {"id": 3, "focused": True, "app_id": "brave-browser",
         "name": "Private page title must not be returned",
         "window_properties": {"class": "Brave-browser"},
         "nodes": [], "floating_nodes": []}
    ], "floating_nodes": []
}
native = diag.find_native_focused(tree_fixture)
assert native["app_id"] == "brave-browser"
assert native["class"] == "Brave-browser"
assert "name" not in native, native
assert diag.find_native_focused({"nodes": [], "floating_nodes": []}) is None
assert diag.summarize_event({"binding": {"command": 'mode "Koinoikos Focus"'}}) \
       == 'binding:mode "Koinoikos Focus"'
assert diag.summarize_event({"change": "focus"}) == "window:focus"

# Stage 2 optional navigation-event trace: default OFF, never consume keys.
# This instrument is not evidence of seat ownership until the operator
# observes the keyboard in an actual Quickshell session above Brave.
assert 'property bool focusKeyTraceEnabled: false' in shell
assert 'target: "focusKeyTrace"' in shell
assert 'function start(): void' in shell
assert 'function stop(): void' in shell
for name, path in (
    ("git", "widgets/GitW.qml"),
    ("hospital", "widgets/HospitalW.qml")
):
    widget = (ROOT / path).read_text()
    assert "property bool focusKeyTraceEnabled: false" in widget
    assert "focusKeyTraceEnabled: shellRoot.focusKeyTraceEnabled" in shell
    assert "function traceFocusNavigation(phase, event)" in widget
    assert 'Qt.Key_Tab, Qt.Key_Backtab' in widget
    assert 'Keys.onShortcutOverride: function(event)' in widget
    assert 'Keys.onPressed: function(event)' in widget
    assert 'onActiveFocusChanged: {' in widget
    assert f'FOCUS_KEY_TRACE // {name} // ' in widget
    # Each of the diagnostic event handlers relinquishes events to the
    # previously existing keyboard and shortcut handlers.
    anchor = "gitKeyboardFocusAnchor" if name == "git" else "keyboardFocusAnchor"
    start = widget.index("id: " + anchor)
    finish = widget.index("anchors.fill: parent", start)
    handlers = widget[start:finish]
    assert handlers.count("event.accepted = false;") == 2
    assert 'Qt.Key_A' not in widget[start:start + 1900]
assert (ROOT / "docs/focus-key-delivery-trace-20261015.md").is_file()

print("KOINOIKOS FOCUS MODE CONTRACTS // PASS")
