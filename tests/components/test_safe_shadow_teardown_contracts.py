#!/usr/bin/env python3
"""Shared contracts for QtQuick graphical-effect source teardown."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

SAFE_PATH = ROOT / "components" / "SafeDropShadow.qml"
QMLDIR_PATH = ROOT / "components" / "qmldir"

safe = SAFE_PATH.read_text(encoding="utf-8")
qmldir = QMLDIR_PATH.read_text(encoding="utf-8")

for needle in (
    "property Item safeSource: null",
    "readonly property bool sourceAttached:",
    "safeSource.Window.window !== null",
    "source: sourceAttached ? safeSource : null",
    "visible: requestedVisible && sourceAttached",
):
    assert needle in safe, f"SafeDropShadow missing teardown contract: {needle!r}"

assert "SafeDropShadow 1.0 SafeDropShadow.qml" in qmldir

SURFACES = {
    "components/DockButton.qml": 1,
    "components/ConversationFeed.qml": 6,
    "components/NeonScrollBar.qml": 1,
    "widgets/notifications/NotificationsHubW.qml": 13,
    "widgets/weather/StationHome.qml": 3,
}

for relative, minimum_safe_count in SURFACES.items():
    text = (ROOT / relative).read_text(encoding="utf-8")
    safe_count = len(re.findall(r"(?m)^\s*SafeDropShadow\s*\{", text))
    assert safe_count >= minimum_safe_count, (
        f"{relative} must keep its direct effects on SafeDropShadow "
        f"(expected at least {minimum_safe_count}, found {safe_count})"
    )
    assert not re.search(r"(?m)^\s*DropShadow\s*\{", text), (
        f"{relative} reintroduced an unguarded direct DropShadow source"
    )

dock = (ROOT / "components" / "DockButton.qml").read_text(encoding="utf-8")
assert "safeSource: dockButton.contentGlowSource" in dock
assert "readonly property point sourceOrigin: sourceAttached" in dock
assert "? dockButton.contentGlowSource.mapToItem(contentLayer, 0, 0)" in dock
assert "requestedVisible: dockButton.contentGlowEnabled" in dock

LAYER_SURFACES = (
    "widgets/GitW.qml",
    "components/ConversationFeed.qml",
)

for relative in LAYER_SURFACES:
    text = (ROOT / relative).read_text(encoding="utf-8")
    assert "layer.effect: DropShadow {" in text, (
        f"{relative} must remain covered while it owns layer-backed shadows"
    )
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("layer.enabled:"):
            continue
        assert "Window.window !== null" in stripped, (
            f"{relative} layer effect gate is missing window teardown guard: "
            f"{stripped}"
        )

print("Shared graphical-effect teardown contracts: PASS")

scrollbar = (ROOT / "components" / "NeonScrollBar.qml").read_text(encoding="utf-8")
assert "safeSource: handleLoader.item" in scrollbar
assert "requestedVisible:" in scrollbar
assert "root.dropHandleGlow" in scrollbar
