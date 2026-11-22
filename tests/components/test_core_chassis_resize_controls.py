#!/usr/bin/env python3
"""Source-only safety contract for the five operator-requested core windows.

Size changes must mutate only their existing QML chassis geometry and preserve
per-page editors/notifications, mapped-window behavior and close authority.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

WINDOWS = (
    ("widgets/TimeW.qml", "timew", "stepWindowSize", "shrinkTimeButton",
     "growTimeButton", "down", "up", 0, (432, 560, 700), (790, 840, 920)),
    ("widgets/ApolloHubW.qml", "hub", "stepWindowSize", "shrinkHubButton",
     "growHubButton", "down", "up", 1, (860, 1000, 1200), (640, 700, 850)),
    ("widgets/GitW.qml", "root", "stepWindowSize", "shrinkGitButton",
     "growGitButton", "down", "up", 1, (1000, 1120, 1360), (720, 790, 920)),
    ("widgets/CpuPlusW.qml", "cpuPlusWindow", "stepWindowSize", "shrinkCpuButton",
     "growCpuButton", "down", "up", 1, (960, 1000, 1180), (834, 834, 980)),
    ("widgets/notifications/NotificationsHubW.qml", "root", "stepWindowWidth",
     "narrowNotificationButton", "widenNotificationButton", "left", "right",
     1, (480, 520, 680), None),
)


def control_block(source, ident):
    lines = source.splitlines()
    hits = [i for i, line in enumerate(lines) if line.strip() == f"id: {ident}"]
    assert len(hits) == 1, (ident, hits)
    idx = hits[0]
    assert lines[idx - 1].strip() == "ResizeButton {" or (
        lines[idx - 1].strip() == "SharedComponents.ResizeButton {"
    ), ident
    start = idx - 1
    indent = lines[start][:len(lines[start]) - len(lines[start].lstrip())]
    end = next(i for i in range(idx + 1, len(lines))
               if lines[i] == indent + "}")
    return "\n".join(lines[start:end+1])


for path, owner, func, low_id, high_id, low_dir, high_dir, default, widths, heights in WINDOWS:
    source = (ROOT / path).read_text(encoding="utf-8")
    assert source.count("PanelWindow {") == 1, path
    assert f"property int resizeLevel: {default}" in source, path
    assert "readonly property var resizeSteps:" in source, path
    assert f"function {func}(delta) {{" in source, path
    func_src = source.split(f"function {func}(delta) {{", 1)[1].split("\n    }", 1)[0]
    assert "if (delta !== -1 && delta !== 1)" in func_src, path
    assert "resizeLevel = Math.max(0, Math.min(resizeSteps.length - 1," in func_src, path
    for forbidden in ("menuOpen =", "selectedMode", "activeFilter =", "activePage =",
                      "save(", "restore(", "reload(", "close(", "refresh(",
                      "NotificationsService.", "gitService."):
        assert forbidden not in func_src, (path, forbidden)
    for w in widths:
        assert f"{w}" in source, (path, w)
    if heights is not None:
        for h in heights:
            assert f"{h}" in source, (path, h)
    assert "screen ? screen.width" in source, (path, "screen clamp")
    for ident, direction, bound in (
        (low_id, low_dir, f"{owner}.resizeLevel > 0"),
        (high_id, high_dir, f"{owner}.resizeLevel < {owner}.resizeSteps.length - 1"),
    ):
        block = control_block(source, ident)
        assert f'direction: "{direction}"' in block, (path, ident)
        # CPU++ formats the comparison across two lines, both sides retained.
        if path == "widgets/CpuPlusW.qml" and ident == high_id:
            assert f"{owner}.resizeLevel" in block
            assert f"< {owner}.resizeSteps.length - 1" in block
        else:
            assert bound in block, (path, ident)
        assert f"{owner}.{func}(delta);" in block, (path, ident)
        assert "onResizeRequested: function(delta)" in block, (path, ident)
        assert not any(f"{x}:" in block for x in ("label", "accentColor", "labelPixelSize"))
    if path in ("widgets/TimeW.qml", "widgets/ApolloHubW.qml", "widgets/GitW.qml",
                "widgets/notifications/NotificationsHubW.qml"):
        assert "visible: true" in source, (path, "mapped window")
        assert "mask: Region {" in source, (path, "closed input mask")
    else:
        assert "visible: menuOpen" in source, (path, "CPU original lifecycle")


notification = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text(encoding="utf-8")
assert "id: notificationHeaderActions" in notification
assert "anchors.rightMargin: notificationHeaderActions.width + 22" in notification
assert "id: closeNotificationsHubButton" in notification
assert "Accessible.name: \"Close Notifications Hub\"" in notification
assert "onCloseRequested: root.close()" in notification
assert "function close() {\n        menuOpen = false;\n    }" in notification
assert "onCloseRequested:\n                                        root.dismissNotification(" in notification, (
    "Card dismiss must remain independent of whole-hub Close"
)
# The hub still uses a compositor-controlled full-height PanelWindow.
for item in ("top: true", "bottom: true", "right: true",
             "implicitWidth: root.panelWidth"):
    assert item in notification, item
assert "implicitHeight: root.panelWidth" not in notification

shared = (ROOT / "components/ResizeButton.qml").read_text(encoding="utf-8")
close = (ROOT / "components/CloseButton.qml").read_text(encoding="utf-8")
for item in ("pressedFillColor: accentColor", "pressedForegroundColor: Colors.black",
             'direction === "right" ? "⮞"', 'direction === "up" ? "⮝"'):
    assert item in shared, item
for item in ('label: "×"', "pressedFillColor: Colors.red",
             "pressedForegroundColor: Colors.black"):
    assert item in close, item

print("Core chassis resize + Notifications whole-hub close contracts: PASS")
