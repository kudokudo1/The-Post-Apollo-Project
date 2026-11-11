import QtQuick
import Quickshell

// Windows-style middle-click anchor indicator.
// NOT connected to live input; requires compositor-trusted output and
// pointer coordinates. This window neither accepts clicks nor takes focus.
PanelWindow {
    id: overlay
    property bool authorized: false
    property bool coordinateVerified: false
    property bool runtimeVerified: false
    property real anchorX: -1
    property real anchorY: -1
    property real displacementX: 0
    property real displacementY: 0
    property string anchorOutput: ""
    property string verifiedOutput: ""
    property string safeState: "not-armed"

    readonly property bool safeToShow:
        authorized && coordinateVerified && runtimeVerified
        && anchorOutput.length > 0 && anchorOutput === verifiedOutput
        && Number.isFinite(anchorX) && Number.isFinite(anchorY)
        && anchorX >= 24 && anchorY >= 24
        && anchorX <= width - 24 && anchorY <= height - 24
        && Number.isFinite(displacementX) && Number.isFinite(displacementY)

    visible: safeToShow
    focusable: false
    color: "transparent"
    aboveWindows: true
    exclusionMode: ExclusionMode.Ignore
    anchors { left: true; right: true; top: true; bottom: true }

    // Critical: a transparent fullscreen layer still intercepts pointer
    // events unless its input region is explicitly EMPTY.
    mask: Region {}

    Rectangle {
        id: anchorMarker
        width: 42
        height: 42
        x: overlay.anchorX - width / 2
        y: overlay.anchorY - height / 2
        radius: 21
        color: "#221224"
        border.width: 2
        border.color: "#22d3ee"
        visible: overlay.safeToShow

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 1
            text: "▲"
            color: "#22d3ee"
            font.pixelSize: 14
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 1
            text: "▼"
            color: "#22d3ee"
            font.pixelSize: 14
        }
        Rectangle {
            anchors.centerIn: parent
            height: 2
            width: 13
            radius: 1
            color: "#f0c64b"
        }
    }
    Rectangle {
        // Non-interactive direction/speed feedback, local to the anchor.
        width: 56
        height: 19
        radius: 3
        x: overlay.anchorX - width / 2
        y: overlay.anchorY + 28
        color: "#221224"
        border.color: "#f0c64b"
        border.width: 1
        visible: overlay.safeToShow
        Text {
            anchors.centerIn: parent
            font.pixelSize: 9
            color: "#f0c64b"
            text: Math.abs(overlay.displacementY) <= 15
                ? "STOP" : overlay.displacementY > 0 ? "DOWN" : "UP"
        }
    }
}
