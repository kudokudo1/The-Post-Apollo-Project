#!/usr/bin/env python3
"""Cross-widget close × migration: visual reuse without changing close authority."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CLOSE = (ROOT / "components/CloseButton.qml").read_text(encoding="utf-8")
cases = {
    "widgets/FinanceW.qml": ("CloseButton {", "onCloseRequested: root.menuOpen = false"),
    "widgets/CameraW.qml": ("CloseButton {", "onCloseRequested: camera.menuOpen = false"),
    "widgets/CompanyNetworkW.qml": ("CloseButton {", "onCloseRequested: root.menuOpen = false"),
    "widgets/TasksW.qml": ("CloseButton {", "onCloseRequested: root.menuOpen = false"),
    "widgets/CpuPlusW.qml": ("CloseButton {", "onCloseRequested: cpuPlusWindow.close()"),
    "widgets/weather/WeatherStationW.qml": ("CloseButton {", "onCloseRequested: weatherStation.close()"),
    "widgets/TimeW.qml": ("CloseButton {", "onCloseRequested: timew.menuOpen = false"),
    "widgets/ApolloHubW.qml": ("CloseButton {", "onCloseRequested: hub.menuOpen = false"),
    "widgets/GitW.qml": ("SharedComponents.CloseButton {", "onCloseRequested: root.close()"),
    "widgets/HospitalW.qml": ("CloseButton {", "onCloseRequested: root.close()"),
    "modules/Trash.qml": ("CloseButton {", "onCloseRequested: trashLauncher.toggle()"),
    "widgets/CompanyHubEditor.qml": ("CloseButton {", "onCloseRequested: editor.cancelRequested()"),
    "widgets/TimeResyncPopup.qml": ("CloseButton {", "onCloseRequested: popup.closeRequested()"),
    "widgets/notifications/NotificationsHubW.qml": (
        "CloseButton {", "root.dismissNotification(notificationEntry.notificationId)"),
    "widgets/GitHubProjectsFieldEditor.qml": ("Components.CloseButton {", "onCloseRequested: root.closeEditor()"),
}
for path, (component, handler) in cases.items():
    source = (ROOT / path).read_text(encoding="utf-8")
    expected = 2 if path == "widgets/notifications/NotificationsHubW.qml" else 1
    assert source.count(component) == expected, (path, "reviewed CloseButton count")
    assert handler in source, (path, "original close behavior")
    if path == "widgets/CameraW.qml":
        assert 'label: "X"' not in source

# Preserve distinct semantics and sizing of special-case close surfaces.
company_editor = (ROOT / "widgets/CompanyHubEditor.qml").read_text(encoding="utf-8")
assert "available: !editor.saving" in company_editor
popup = (ROOT / "widgets/TimeResyncPopup.qml").read_text(encoding="utf-8")
assert 'width: 25' in popup
trash = (ROOT / "modules/Trash.qml").read_text(encoding="utf-8")
assert "id: closeTrashButton" in trash and "width: 30" in trash
# ReloadButton joins the same header row without displacing the Close ×.
# The title width follows actual siblings instead of a stale fixed deduction.
assert "id: trashHeaderRow" in trash
assert "collapseTrashButton.width - expandTrashButton.width" in trash
assert "trashLiveIndicator.width - trashHeaderReloadButton.width" in trash
assert "closeTrashButton.width - trashHeaderRow.spacing * 5" in trash
camera = (ROOT / "widgets/CameraW.qml").read_text(encoding="utf-8")
assert "cameraCloseButton.width" in camera
assert 'label: "X"' not in camera
cpu = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
assert "id: cpuPlusCloseMouse" not in cpu

# Notification card × is one-item dismiss, while the new header × only
# closes the history window. CLEAR ALL remains a separate destructive action.
notifications = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text(encoding="utf-8")
assert 'label: "CLEAR ALL"' in notifications
assert "root.requestClearAllForApp(notificationEntry.appKey, notificationEntry.source)" in notifications
assert "onCloseRequested:" in notifications
assert "root.dismissNotification(notificationEntry.notificationId)" in notifications
assert "id: closeNotificationsHubButton" in notifications
assert "onCloseRequested: root.close()" in notifications

# An Identity Center X intentionally removes a specific identity: not a Close.
identity = (ROOT / "widgets/cpuplus/CpuPlusIdManagementPane.qml").read_text(encoding="utf-8")
assert "id: removeButton" in identity and 'label: "X"' in identity

# Visual identity is defined ONCE by the shared control.
for key in (
    'label: "×"', "height: width * 16 / 17",
    "hoverFillColor: Colors.yellow", "hoverForegroundColor: Colors.red",
    "pressedFillColor: Colors.red", "pressedForegroundColor: Colors.black",
    "contentGlowPressedOpacity: 1.0",
    "softGlowPressedOpacity: 1.0",
    "wideGlowPressedOpacity: 1.0",
    "trackLabelGlowLocally: true",
    "onLeftClicked: closeButton.closeRequested()",
):
    assert key in CLOSE, key

# A repository-wide inventory catches other literal X/× glyph users without
# reclassifying destructive Remove actions as ordinary Close automatically.
# A nonempty inventory is a review queue, not permission for mass conversion.
remaining = []
for scope in ("widgets", "modules"):
    for path in sorted((ROOT / scope).rglob("*.qml")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r'\b(?:label|text):\s*["\'](?:X|×)["\']', line):
                remaining.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
print("Residual literal X/× control inventory:")
for record in remaining:
    print("  " + record)

print("CloseButton cross-widget migration contracts: PASS")
