import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"

// TASKS M1: a presentation-only menu with no task data or sync service.
// Stay mapped across opens; closed state uses an empty pointer input mask.
PanelWindow {
    id: root

    property bool menuOpen: false
    property real dockCenterX: 0
    property real chassisTopY: 0

    // Reuse the FinanceW/TimeW 9:16 pilot geometry until live review.
    readonly property int frameWidth: 432
    readonly property int frameHeight: 768
    readonly property int glowGutter: 12

    function toggle() {
        menuOpen = !menuOpen;
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    // Align with the Git/Hospital panel top, and clamp to the screen.
    margins {
        top: Math.max(0, Math.round(root.chassisTopY - root.glowGutter))
        left: Math.max(0, Math.min(
            Math.max(0, root.screen ? root.screen.width - root.implicitWidth : 0),
            Math.round(root.dockCenterX - root.implicitWidth / 2)
        ))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    focusable: false

    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.glowGutter
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: tasksFrame
        anchors.fill: parent
        anchors.margins: root.glowGutter
        visible: root.menuOpen

        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 0

        glowVisible: root.menuOpen
        glowColor: Colors.cyan

        Rectangle {
            id: tasksHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 56
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.right: feedBadge.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: "TASKS // HOME"
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            // A truthful state indicator, not a fake local task feed.
            Rectangle {
                id: feedBadge
                width: 68
                height: 26
                anchors.right: closeButton.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                color: Colors.dark
                border.width: 1
                border.color: Colors.orange

                GohuText {
                    anchors.centerIn: parent
                    text: "NO FEED"
                    font.pixelSize: 9
                    color: Colors.orange
                }
            }

            ActionButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 34
                height: 32
                label: "×"
                labelPixelSize: 22
                contentPadding: 4
                accentColor: Colors.red
                destructive: true
                onLeftClicked: root.menuOpen = false
            }
        }

        Rectangle {
            id: tasksDivider
            anchors.top: tasksHeader.bottom
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
            height: 2
            color: Colors.cyan
        }

        Column {
            anchors.centerIn: parent
            spacing: 12
            width: parent.width - 40

            GohuText {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "NO TASKS LOADED"
                font.pixelSize: 18
                font.bold: true
                color: Colors.white
            }

            GohuText {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: "TASK EDITOR // NOT CONNECTED"
                font.pixelSize: 12
                color: Colors.cyan
            }
        }
    }
}
