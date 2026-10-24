#!/usr/bin/env python3
"""Verify the five requested control surfaces share FinanceW's visible top."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def source(path):
    return (root / path).read_text(encoding="utf-8")

hospital = source("widgets/HospitalW.qml")
git = source("widgets/GitW.qml")
tasks = source("widgets/TasksW.qml")
time = source("widgets/TimeW.qml")
deck = source("widgets/MediaDeckW.qml")
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
assert "frameHeight: 768" in tasks

assert "readonly property int glowGutter: 12" in time
assert "readonly property int frameTopInset: 9" in time
assert "    margins {\n        top: 0\n        right: 13\n    }" in time
assert "y: timew.frameTopInset" in time
assert "anchors.topMargin: timew.frameTopInset" in time
assert "implicitHeight: frameHeight + frameTopInset + glowGutter" in time
assert "frameHeight: 768" in time

assert "property int panelTopMargin: 9" in deck
assert "        top: panelTopMargin" in deck
assert "    SurfaceFrame {\n        anchors.fill: parent" in deck
assert "property int panelHeight: 850" in deck

# Finance is the accepted experiment's reference: compact inset = 12 - 3.
assert "readonly property int compactTopLift: 3" in finance
assert 'chassisLevel === "compact" ? glowGutter - compactTopLift : glowGutter' in finance
assert "anchors.topMargin: root.frameTopInset" in finance
assert "panelTopMargin: 0" in hospital
assert "chassisTopY: hospitalWindow.panelTopMargin" in shell
assert "+ hospitalWindow.topGlowGutter" in shell

# Other widget panel dimensions and established visibility lifetimes remain.
assert "property int panelHeight: 1320" in hospital
assert "property int panelHeight: 790" in git
assert "visible: true" in hospital and "visible: true" in git
assert "visible: true" in tasks and "visible: true" in time
assert "visible: menuOpen" in deck
assert "WlrLayershell.layer: WlrLayer.Overlay" in deck

print("Five-widget visible top-edge alignment // 9px: PASS")
