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

    // ============================================================
    // WINDOW
    //
    // AppControlW: 834 wide x 674 tall
    // CPU++:       674 wide x 834 tall
    //
    // The entire footprint is transposed so CPU++ is taller than wide.
    // ============================================================

    implicitWidth: 674
    implicitHeight: 834

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

    // ============================================================
    // OUTER CHASSIS GLOW
    // Orange is the CPU++ structural accent.
    // ============================================================

    RectangularShadow {
        anchors.fill: background
        spread: 6
        z: -20
        opacity: 0.38
        color: Colors.orange
    }

    RectangularShadow {
        anchors.fill: background
        spread: 12
        z: -21
        opacity: 0.12
        color: Colors.orange
    }

    Rectangle {
        id: background

        anchors.fill: parent
        anchors.margins: 12

        color: "transparent"
    }

    // ============================================================
    // TOP MODE SELECTOR
    //
    // AppControl's 110 px vertical mode rail is transposed into a
    // 110 px horizontal rail that spans the full CPU++ interior.
    // ============================================================

    Rectangle {
        id: modeRail

        height: 110

        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        anchors.leftMargin: 12
        anchors.rightMargin: 12
        anchors.topMargin: 12

        color: Colors.black

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity: 0.22
            color: Colors.orange
        }

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 14
            anchors.topMargin: 10

            text: "CPU++"

            font.pixelSize: 15
            color: Colors.orange
        }

        Row {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            anchors.leftMargin: 8
            anchors.rightMargin: 8
            anchors.bottomMargin: 10

            height: 55
            spacing: 8

            Repeater {
                model: [
                    "PROCESS",
                    "THERMAL",
                    "SYSTEM"
                ]

                Rectangle {
                    required property string modelData

                    width:
                        (parent.width - parent.spacing * 2) / 3
                    height: parent.height

                    color: Colors.black

                    border.width: 1
                    border.color: Colors.orange

                    GohuText {
                        anchors.centerIn: parent

                        text: modelData

                        font.pixelSize: 12
                        color: Colors.white
                    }

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: 0.12
                        color: Colors.orange
                    }
                }
            }
        }
    }

    // ============================================================
    // LOWER WORK AREA
    //
    // Left:
    //   Shared AppControl instrument bay.
    //   390 px keeps the stolen Task/Thermal/System views at their
    //   familiar detail-pane width.
    //
    // Right:
    //   CPU++ native expansion controls.
    //
    // Interior width = 650 px
    // Shared bay     = 390 px
    // Native bay     = 260 px
    // ============================================================

    Rectangle {
        id: sharedInstrumentPane

        width: 390

        anchors.left: parent.left
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.leftMargin: 12
        anchors.bottomMargin: 12

        color: Qt.rgba(
            Colors.black.r,
            Colors.black.g,
            Colors.black.b,
            0.95
        )

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            anchors.left: parent.left
            anchors.top: parent.top

            anchors.leftMargin: 16
            anchors.topMargin: 18

            text: "SHARED INSTRUMENT"

            font.pixelSize: 13
            color: Colors.orange
        }
    }

    Rectangle {
        id: nativeControlPane

        anchors.left: sharedInstrumentPane.right
        anchors.right: parent.right
        anchors.top: modeRail.bottom
        anchors.bottom: parent.bottom

        anchors.rightMargin: 12
        anchors.bottomMargin: 12

        color: Colors.dark

        border.width: 1
        border.color: Colors.orange

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity: 0.18
            color: Colors.orange
        }

        GohuText {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top

            anchors.topMargin: 18

            text: "CPU++ CONTROL"

            font.pixelSize: 13
            color: Colors.orange
        }
    }
}
