import Quickshell
import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../components"

PanelWindow {
    id: cpuPlusWindow

    property bool menuOpen: false

    function open() {
        menuOpen = true;
    }

    function close() {
        menuOpen = false;
    }

    function toggle() {
        menuOpen = !menuOpen;
    }

    // Same outer footprint as AppControlW.
    implicitWidth: 834
    implicitHeight: 674

    // Mirrored placement for the right-side CPU module.
    anchors {
        top: true
        right: true
    }

    margins {
        top: -3
        right: 2
    }

    color: "transparent"
    surfaceFormat.opaque: false
    focusable: true
    visible: menuOpen

    RectangularShadow {
        anchors.fill: background
        spread: 6
        z: -20
        opacity: 0.38
        color: Colors.cyan
    }

    RectangularShadow {
        anchors.fill: background
        spread: 12
        z: -21
        opacity: 0.12
        color: Colors.cyan
    }

    Rectangle {
        id: background
        anchors.fill: parent
        anchors.margins: 12
        color: "transparent"
    }

    // ============================================================
    // REVERSED THREE-PART LAYOUT
    //
    // AppControl: 110 | 310 | 390
    // CPU++:      390 | 310 | 110
    //
    // The split remains horizontal and the interior stays 810 px.
    // ============================================================

    Rectangle {
        id: controlPane

        width: 390

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        anchors.leftMargin: 12
        anchors.topMargin: 12
        anchors.bottomMargin: 12

        color: Qt.rgba(
            Colors.black.r,
            Colors.black.g,
            Colors.black.b,
            0.95
        )

        border.width: 1
        border.color: Colors.cyan

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 5
            anchors.rightMargin: 5
            anchors.topMargin: 8
            height: 2
            color: Colors.cyan
        }

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.leftMargin: 16
            anchors.topMargin: 20

            text: "CPU++ // CONTROL"
            font.pixelSize: 14
            color: Colors.cyan
        }
    }

    Rectangle {
        id: monitorPane

        width: 310

        anchors.left: controlPane.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        anchors.topMargin: 12
        anchors.bottomMargin: 12

        color: Colors.dark

        GohuText {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 20

            text: "MONITOR"
            font.pixelSize: 14
            color: Colors.orange
        }
    }

    Rectangle {
        id: modeRail

        width: 110

        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        anchors.rightMargin: 12
        anchors.topMargin: 12
        anchors.bottomMargin: 12

        color: Colors.black

        GohuText {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 20

            text: "CPU++"
            font.pixelSize: 16
            color: Colors.cyan
        }

        Column {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.topMargin: 58
            spacing: 8

            Repeater {
                model: [
                    "PROCESS",
                    "THERMAL",
                    "SYSTEM"
                ]

                Rectangle {
                    required property string modelData

                    width: parent.width
                    height: 55

                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        text: modelData
                        font.pixelSize: 11
                        color: Colors.white
                    }
                }
            }
        }
    }
}
