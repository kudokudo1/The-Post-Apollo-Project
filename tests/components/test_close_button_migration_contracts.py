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
    assert source.count(component) == 1, (path, "exactly one shared CloseButton")
    assert handler in source, (path, "original close behavior")
    assert "×" not in source if path in ("widgets/CameraW.qml",) else True
    assert 'label: "X"' not in source if path in ("widgets/CameraW.qml",) else True

# Preserve distinct semantics and sizing of special-case close surfaces.
company_editor = (ROOT / "widgets/CompanyHubEditor.qml").read_text(encoding="utf-8")
assert "available: !editor.saving" in company_editor
popup = (ROOT / "widgets/TimeResyncPopup.qml").read_text(encoding="utf-8")
assert 'width: 25' in popup
trash = (ROOT / "modules/Trash.qml").read_text(encoding="utf-8")
assert "id: closeTrashButton" in trash and "width: 30" in trash
assert "width: parent.width - 180" in trash
camera = (ROOT / "widgets/CameraW.qml").read_text(encoding="utf-8")
assert "cameraCloseButton.width" in camera
assert 'label: "X"' not in camera
cpu = (ROOT / "widgets/CpuPlusW.qml").read_text(encoding="utf-8")
assert "id: cpuPlusCloseMouse" not in cpu

# Notification × is one-item dismiss. CLEAR ALL remains separate.
notifications = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text(encoding="utf-8")
assert 'label: "CLEAR ALL"' in notifications
assert "root.requestClearAllForApp(notificationEntry.appKey, notificationEntry.source)" in notifications
assert "onCloseRequested:" in notifications
assert "root.dismissNotification(notificationEntry.notificationId)" in notifications

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

print("CloseButton cross-widget migration contracts: PASS")
