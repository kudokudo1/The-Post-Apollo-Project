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
assert "anchors.topMargin: root.topGlowGutter" in hospital
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

# Notifications is the live reference: anchored top/bottom with an exact 5px
# output-bottom margin. Social and Hospital must track screen height, rather
# than freezing at their old 1355px / 1320px constants.
assert "property int panelBottomMargin: 5" in notifications
assert "        bottom: true" in notifications
assert "        top: true" in notifications
assert "        bottom: root.panelBottomMargin" in notifications
assert "property int defaultPanelHeight: Math.max(" in social
assert "(screen ? Math.round(screen.height) : 1360) - 5" in social
assert "sharedPanelHeight = defaultPanelHeight;" in social
assert "height: messagingWindow.sharedPanelHeight" in social
# Sway workspaces start below the bar: the taller Social FloatingWindow
# must start above the workspace top rather than spill off the output.
assert "swayAreaY + swayAreaHeight - defaultPanelHeight - 5" in social
assert "sharedPanelY = Math.round(defaultPanelY);" in social
assert "readonly property int notificationBottomGap: 5" in hospital
assert "property int panelHeight: Math.max(" in hospital
assert "- topGlowGutter - notificationBottomGap" in hospital
assert "implicitHeight: panelHeight + topGlowGutter + notificationBottomGap" in hospital
# The Notification and Social panels have the same span on the selected
# output; Hospital retains its 9px top reveal and shares their bottom edge.
for screen_height in (768, 1080, 1440, 1600):
    notification_height = screen_height - 5
    social_height = max(260, notification_height)
    hospital_frame = max(260, screen_height - 9 - 5)
    assert social_height == notification_height
    assert hospital_frame + 9 == notification_height
    assert hospital_frame + 9 + 5 == screen_height

# Other widget panel widths, top-edge geometry and visibility lifetimes remain.
assert "property int panelWidth: 744" in hospital
assert "property int defaultPanelWidth: 1210" in social
assert "property int panelHeight: 790" in git
assert "visible: true" in hospital and "visible: true" in git
assert "visible: true" in tasks and "visible: true" in time
assert "visible: menuOpen" in deck
assert "WlrLayershell.layer: WlrLayer.Overlay" in deck

print("Portrait 790px / Hospital+Social notification bottom line / top-edge alignment: PASS")
