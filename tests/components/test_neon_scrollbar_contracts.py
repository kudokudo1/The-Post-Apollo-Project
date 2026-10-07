#!/usr/bin/env python3
"""Static contracts for the reusable NeonScrollBar component."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ('property string handleStyle: "bar"', "single switchable handle-style API"),
    ('String(root.handleStyle || "").toLowerCase() === "star"', "star style selection"),
    ("property color railColor: Colors.cyan", "canonical cyan rail default"),
    ("property color handleColor: Colors.magenta", "canonical magenta handle default"),
    ("property int railWidth: 3", "canonical rail width"),
    ("property int barHandleWidth: 7", "canonical bar handle width"),
    ("property int minimumHandleHeight: 24", "canonical minimum handle height"),
    ("property int starHandleSize: 14", "canonical star handle size"),
    ("property real railOpacity: 0.82", "canonical rail opacity"),
    ("property real barGlowIdleOpacity: 0.42", "canonical bar glow"),
    ("property real starGlowIdleOpacity: 0.52", "canonical star glow"),
    ("property Component railDecoration: null", "semantic rail decoration extension point"),
    ("property bool interactive: true", "interaction toggle"),
    ("property bool wheelEnabled: true", "wheel toggle"),
    ("property bool preserveDragOffset: false", "grab-offset drag mode"),
    ("property int pointerCursorShape: Qt.PointingHandCursor", "configurable pointer cursor"),
    ('property string handleGlowStyle: "rectangular"', "switchable handle glow implementation"),
    ("property real handleDropGlowRadius: 10", "safe drop-shadow radius"),
    ("property int handleDropGlowSamples: 13", "safe drop-shadow samples"),
    ("property bool autoHide: true", "visibility policy"),
    ("sourceComponent:", "single loader-backed handle"),
):
    require(COMPONENT, needle, message)

assert "property bool starHandle" not in COMPONENT, "legacy starHandle boolean must be removed"

star_users = []
legacy_users = []

for path in ROOT.rglob("*.qml"):
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)

    if re.search(r"\bstarHandle\s*:", text):
        legacy_users.append(str(rel))

    if 'handleStyle: "star"' in text:
        star_users.append(str(rel))

assert not legacy_users, "legacy starHandle usage remains: " + ", ".join(legacy_users)
assert len(star_users) == 4, f"expected four star-handle consumer files, found {len(star_users)}: {star_users}"

print("Neon scrollbar contracts: PASS")
print("star-handle consumers:", ", ".join(star_users))


# Migrated legacy/custom scrollbar contracts. These values are intentionally
# surface-specific; centralization must not flatten their established look.
MIGRATED = {
    "widgets/CpuPlusW.qml": (
        "NeonScrollBar {",
        "id: targetScrollTrack",
        "barAreaWidth: 10",
        "railWidth: 10",
        "barHandleWidth: 6",
        "minimumHandleHeight: 30",
        "railOpacity: 0.90",
        "railGlowOpacity: 0.24",
        "handleOpacity: 0.90",
        "barGlowIdleOpacity: 0.28",
        "preserveDragOffset: true",
    ),
    "widgets/notifications/NotificationsHubW.qml": (
        "NeonScrollBar {",
        "id: scrollBarArea",
        "barAreaWidth: root.scrollBarAreaWidth",
        "railWidth: root.scrollTrackWidth",
        "barHandleWidth: root.scrollThumbWidth",
        "minimumHandleHeight: root.scrollThumbMinHeight",
        "railOpacity: 0.52",
        'handleGlowStyle: "drop"',
        "handleDropGlowRadius: 10",
        "handleDropGlowSamples: 13",
        "handleDropGlowIdleOpacity: 0.60",
    ),
    "widgets/WorkflowLibraryView.qml": (
        "NeonScrollBar {",
        "id: workflowScrollTrack",
        "barAreaWidth: 9",
        "railWidth: 9",
        "barHandleWidth: 5",
        "minimumHandleHeight: 26",
        "railBorderColor: Colors.orange",
        "handleOpacity: scrollable ? 0.92 : 0.0672",
        "preserveDragOffset: true",
    ),
    "widgets/appcontrol/TaskManagerView.qml": (
        "NeonScrollBar {",
        "id: taskProcessScopeScrollTrack",
        "barAreaWidth: 8",
        "railWidth: 8",
        "barHandleWidth: 5",
        "minimumHandleHeight: 18",
        "railOpacity: 0.90",
        "handleOpacity: 0.90",
        "barGlowIdleOpacity: 0.22",
    ),
    "widgets/appcontrol/DestructiveConfirmOverlay.qml": (
        "NeonScrollBar {",
        "id: destructiveConfirmMessageScrollTrack",
        "barAreaWidth: 9",
        "railWidth: 9",
        "barHandleWidth: 6",
        "minimumHandleHeight: 24",
        "railColor: Colors.red",
        "railOpacity: 0.92",
        "handleOpacity: 0.92",
        "barGlowIdleOpacity: 0.28",
    ),
    "widgets/GitHubWorkItemsView.qml": (
        "NeonScrollBar {",
        "id: scrollTrack",
        "barAreaWidth: 4",
        "railWidth: 4",
        "barHandleWidth: 4",
        "minimumHandleHeight: 18",
        "railColor: Colors.dark",
        "interactive: false",
    ),
    "widgets/RepositoryProfileView.qml": (
        "NeonScrollBar {",
        "id: catalogScrollTrack",
        "barAreaWidth: 5",
        "railWidth: 5",
        "barHandleWidth: 5",
        "minimumHandleHeight: 18",
        "railBorderColor: Colors.dark",
        "handleOpacity: scrollable ? 0.82 : 0.30",
        "interactive: false",
    ),
}

for path, needles in MIGRATED.items():
    source = (ROOT / path).read_text(encoding="utf-8")
    for needle in needles:
        require(source, needle, f"preserve migrated scrollbar values in {path}")
