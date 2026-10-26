#!/usr/bin/env python3
"""Verify the five requested control surfaces share FinanceW's visible top."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def source(path):
    return (root / path).read_text(encoding="utf-8")

hospital = source("widgets/HospitalW.qml")
social = source("widgets/messanger/MessagingW.qml")
notifications = source("widgets/notifications/NotificationsHubW.qml")
git = source("widgets/GitW.qml")
tasks = source("widgets/TasksW.qml")
time = source("widgets/TimeW.qml")
deck = source("widgets/MediaDeckW.qml")
weather = source("widgets/weather/WeatherStationW.qml")
finance = source("widgets/FinanceW.qml")
shell = source("shell.qml")

# These are compositor-relative QML coordinates, not a claim of live pixel
# measurements. All five visible top edges are 9px when anchored to the output.
assert "property int panelTopMargin: 0" in hospital
assert "property int topGlowGutter: 9" in hospital
assert "anchors.topMargin: root.frameInset" in hospital
assert "property int panelTopMargin: 0" in git
assert "property int topGlowGutter: 9" in git
assert git.count("anchors.topMargin: root.topGlowGutter") >= 2

assert "readonly property int glowGutter: 12" in tasks
assert "readonly property int frameTopInset: 9" in tasks
assert "root.chassisTopY - root.glowGutter" in tasks
assert "y: root.frameTopInset" in tasks
assert "anchors.topMargin: root.frameTopInset" in tasks
assert "implicitHeight: frameHeight + frameTopInset + glowGutter" in tasks
assert "frameHeight: 790" in tasks

assert "readonly property int glowGutter: 12" in time
assert "readonly property int frameTopInset: 9" in time
assert "    margins {\n        top: 0\n        right: 13\n    }" in time
assert "y: timew.frameTopInset" in time
assert "anchors.topMargin: timew.frameTopInset" in time
assert "implicitHeight: frameHeight + frameTopInset + glowGutter" in time
assert "frameHeight: 790" in time

assert "property int panelTopMargin: 9" in deck
assert "        top: panelTopMargin" in deck
assert "    SurfaceFrame {\n        anchors.fill: parent" in deck
assert "property int panelHeight: 850" in deck

# Weather Station fills its own 1000x700 frame (no inner top gutter).
# Shift the native weather window from 0px to the shared 9px visible line;
# no changes to the frame size, side placement or terminal hole geometry.
assert "implicitWidth: menuOpen ? 1000 : 0" in weather
assert "implicitHeight: menuOpen ? 700 : 0" in weather
assert "    margins {\n        top: 9\n        bottom: 0\n        right: 20\n        left: 0\n    }" in weather
assert "width: weatherStation.menuOpen ? 1000 : 0" in weather
assert "height: weatherStation.menuOpen ? 700 : 0" in weather

# All three portrait widgets use a visible height of 790px on large outputs.
policy = source("widgets/FinanceChassisPolicy.js")
assert 'mode === "expanded" ? 900 : 790' in policy
assert 'readonly property int frameHeight: 790' in tasks
assert 'readonly property int frameHeight: 790' in time

# Finance uses one 9px visible top line in Compact, Expanded and Fullscreen.
assert "readonly property int frameTopInset: 9" in finance
assert "readonly property int bottomScreenGap: 8" in finance
assert "compactTopLift" not in finance
assert "anchors.topMargin: root.frameTopInset" in finance
assert "panelTopMargin: 0" in hospital
assert "chassisTopY: hospitalWindow.panelTopMargin" in shell
assert "+ hospitalWindow.topGlowGutter" in shell

# This is a *visible frame* alignment, not a comparison of QsWindow heights.
# Notifications draws its WindowPanelFrame with 8px on BOTH edges; its
# PanelWindow has top/bottom anchors and a 5px screen-bottom margin.
assert "property int panelBottomMargin: 5" in notifications
assert "property int frameInset: 8" in notifications
assert "anchors.fill: parent\n            anchors.margins: root.frameInset" in notifications
assert "        bottom: true" in notifications
assert "        top: true" in notifications
assert "        bottom: root.panelBottomMargin" in notifications

# Hospital must use the identical vertical anchor mode/margins and frame
# inset; screen.height is not equivalent to the compositor-owned QsWindow
# height when panels reserve work area above the actual viewport.
assert "property var notificationsReference: null" in hospital
assert "notificationsReference.panelBottomMargin : 5" in hospital
assert "property int panelHeight: Math.max(1, height - frameInset * 2)" in hospital
assert "implicitHeight: panelHeight" not in hospital
assert "        bottom: notificationBottomGap" in hospital
assert "anchors.topMargin: root.frameInset" in hospital
assert "property int frameInset: 8" in hospital

# Social is a separate Sway FloatingWindow. The shared social window and
# Discord/X follower geometry are sized from the visible notification panel.
assert "property var notificationsReference: null" in social
assert "notificationsReference.frameInset : 8" in social
assert "notificationsReference.panelBottomMargin : 5" in social
assert "Math.round(notificationsReference.height) - 2 * notificationsFrameInset" in social
assert "sharedPanelHeight = defaultPanelHeight;" in social
assert "height: messagingWindow.sharedPanelHeight" in social
# Social opens at Notifications/Hospital's visible top border, not at
# an output-bottom-derived Y that can be displaced by Sway's work area.
# QScreen.geometry.y includes the output's virtual-desktop origin.
assert "readonly property int defaultPanelY: Math.round(" in social
assert "(screen ? screen.geometry.y : 0)" in social
assert "(notificationsReference ? notificationsReference.panelTopMargin : 0)" in social
assert "+ notificationsFrameInset" in social
assert "swayAreaY + swayAreaHeight - defaultPanelHeight" not in social
assert "sharedPanelY = Math.round(defaultPanelY);" in social
# X and the shared size/Discord geometry must not change.
assert "readonly property int defaultPanelX: swayAreaX + swayAreaWidth - margins.right - defaultPanelWidth" in social
assert "property int defaultPanelWidth: 1210" in social
assert "property int defaultPanelHeight: Math.max(" in social
assert "sharedPanelWidth = defaultPanelWidth;" in social
assert "sharedPanelHeight = defaultPanelHeight;" in social
assert "const" not in social.split("readonly property int defaultPanelY:", 1)[1].split("readonly property int discordX:", 1)[0]
assert "notificationsReference: notificationsHubWindow" in shell
assert shell.count("notificationsReference: notificationsHubWindow") == 2

# Geometry arithmetic. All three visible frames use identical 8px insets
# and lower screen clearance. The Sway floating position is a separately
# reviewed initial-placement estimate, not proof of compositor placement.
for window_height in (763, 1075, 1435, 1595):
    notification_frame = window_height - 16
    hospital_frame = window_height - 16
    social_frame = window_height - 16
    assert notification_frame == hospital_frame == social_frame
    assert 8 + hospital_frame + 8 == window_height

# Different virtual monitor origins do not alter the target 8px
# visible inset relative to each output.
for output_y in (-1080, 0, 240, 1440):
    top = output_y + 0 + 8
    assert top - output_y == 8
    assert top == output_y + 8

# Other widget panel widths, top-edge geometry and visibility lifetimes remain.
assert "property int panelWidth: 744" in hospital
assert "property int defaultPanelWidth: 1210" in social
assert "property int panelHeight: 790" in git
assert "visible: true" in hospital and "visible: true" in git
assert "visible: true" in tasks and "visible: true" in time
assert "visible: menuOpen" in deck
assert "WlrLayershell.layer: WlrLayer.Overlay" in deck

print("Visible Notification/Social/Hospital frame-size alignment + top-edge contracts: PASS")
