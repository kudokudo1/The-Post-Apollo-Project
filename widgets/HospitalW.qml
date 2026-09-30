import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false

    property int panelWidth: 520
    property int panelHeight: 650
    property int panelTopMargin: 0
    property int panelLeftMargin: 50
    property int frameInset: 8
    property int glowGutter: 14

    // The visible menu keeps its original size/position. The transparent
    // surface is larger only so the chassis shadow has pixels to render into.
    implicitWidth: panelWidth + glowGutter * 2
    implicitHeight: panelHeight + glowGutter

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin - glowGutter
        right: 0
        bottom: 0
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay

    color: "transparent"
    surfaceFormat.opaque: false

    // Keep the real surface mapped. Closed state is invisible + click-through.
    visible: true

    mask: Region {
        x: 0
        y: 0
        width: root.menuOpen ? root.width : 0
        height: root.menuOpen ? root.height : 0
    }

    function open() {
        root.menuOpen = true;
    }

    function close() {
        root.menuOpen = false;
    }

    function toggle() {
        root.menuOpen = !root.menuOpen;
    }

    component SectionLabel: GohuText {
        font.pixelSize: 12
        color: Colors.magenta

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 6
            samples: 7
            opacity: 0.46
            color: Colors.magenta
            transparentBorder: true
        }
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 4
            samples: 5
            opacity: 0.28
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component MetaValue: GohuText {
        font.pixelSize: 11
        color: Colors.white
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 5
            opacity: 0.38
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component RoomRow: Rectangle {
        id: roomRow

        property string team: ""
        property string responsibility: ""
        property string stateText: "UNVERIFIED"

        width: roomsColumn.width
        height: 42

        color: Colors.dark
        border.width: 1
        border.color: Colors.magenta

        RectangularShadow {
            anchors.fill: parent
            spread: 4
            z: -1
            opacity: 0.38
            color: Colors.magenta
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 10
            }

            text: roomRow.team
            font.pixelSize: 12
            color: Colors.magenta
        }

        GohuText {
            anchors {
                left: parent.left
                verticalCenter: parent.verticalCenter
                leftMargin: 62
            }

            width: 285
            text: roomRow.responsibility
            font.pixelSize: 11
            color: Colors.white
            elide: Text.ElideRight

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 5
                samples: 5
                opacity: 0.38
                color: Colors.cyan
                transparentBorder: true
            }
        }

        GohuText {
            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                rightMargin: 10
            }

            text: roomRow.stateText
            font.pixelSize: 9
            color: Colors.cyan
        }
    }

    // Background halo. Inset slightly so the drop shadow has room to
    // render inside the always-mapped PanelWindow surface.
    Rectangle {
        id: backgroundGlowSource

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter

        color: Colors.black
        opacity: root.menuOpen ? 0.92 : 0.0

        z: -4
    }

    DropShadow {
        anchors.fill: backgroundGlowSource
        source: backgroundGlowSource

        horizontalOffset: 0
        verticalOffset: 3

        radius: 30
        samples: 31

        color: Colors.magenta
        opacity: root.menuOpen ? 0.42 : 0.0

        z: -5

        transparentBorder: true
    }

    // Active outer frame glow. Kept inside the surface bounds so the
    // menu can remain flush with the top edge.
    Rectangle {
        id: frameGlowSource

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter

        color: "transparent"
        border.width: 2
        border.color: Colors.magenta

        opacity: root.menuOpen ? 1.0 : 0.0

        z: 2
    }

    DropShadow {
        anchors.fill: frameGlowSource
        source: frameGlowSource

        horizontalOffset: 0
        verticalOffset: 0

        radius: 14
        samples: 17

        color: Colors.magenta
        opacity: root.menuOpen ? 0.96 : 0.0

        z: 3

        transparentBorder: true
    }

    RectangularShadow {
        anchors.fill: frameGlowSource
        spread: 8
        z: -2
        opacity: root.menuOpen ? 0.62 : 0.0
        color: Colors.magenta
    }

    RectangularShadow {
        anchors.fill: frameGlowSource
        spread: 18
        z: -3
        opacity: root.menuOpen ? 0.22 : 0.0
        color: Colors.magenta
    }

    Rectangle {
        id: frame

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter

        color: Colors.black
        opacity: root.menuOpen ? 0.97 : 0.0

        border.width: 2
        border.color: Colors.magenta

        Rectangle {
            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        Column {
            id: content

            anchors {
                fill: parent
                margins: 18
            }

            spacing: 12

            // ===== HEADER =======================================

            Item {
                width: parent.width
                height: 56

                GohuText {
                    anchors {
                        left: parent.left
                        top: parent.top
                    }

                    text: "HOSPITAL // SURGERY ROOM"
                    font.pixelSize: 20
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 8
                        samples: 9
                        opacity: 0.52
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }

                GohuText {
                    anchors {
                        left: parent.left
                        bottom: parent.bottom
                    }

                    text: "CONTROL SURFACE // STATIC SHELL"
                    font.pixelSize: 10
                    color: Colors.cyan
                }

                Rectangle {
                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                    }

                    width: 86
                    height: 26

                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.magenta

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 3
                        z: -1
                        opacity: 0.58
                        color: Colors.magenta
                    }

                    GohuText {
                        anchors.centerIn: parent
                        text: "UNVERIFIED"
                        font.pixelSize: 9
                        color: Colors.magenta
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.34
                    color: Colors.cyan
                }
            }

            // ===== PATIENT ======================================

            Rectangle {
                width: parent.width
                height: 118

                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta

                RectangularShadow {
                    anchors.fill: parent
                    spread: 5
                    z: -1
                    opacity: 0.44
                    color: Colors.magenta
                }

                Column {
                    anchors {
                        fill: parent
                        margins: 12
                    }

                    spacing: 7

                    SectionLabel {
                        text: "PATIENT"
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 110
                            text: "REPOSITORY"
                        }

                        MetaValue {
                            width: 330
                            text: "taskbars-post-apollo"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 110
                            text: "CERTIFIED HEAD"
                        }

                        MetaValue {
                            width: 330
                            text: "NOT CONNECTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 110
                            text: "HOST SLOT"
                        }

                        MetaValue {
                            width: 330
                            text: "NOT CONNECTED"
                        }
                    }
                }
            }

            // ===== OPERATING ROOMS ==============================

            SectionLabel {
                text: "OPERATING ROOMS"
            }

            Column {
                id: roomsColumn

                width: parent.width
                spacing: 5

                RoomRow { team: "T1"; responsibility: "SYSTEM / HUNTER" }
                RoomRow { team: "T2"; responsibility: "FAVORITES" }
                RoomRow { team: "T3-F"; responsibility: "FILES" }
                RoomRow { team: "T3-R"; responsibility: "REMOTE" }
                RoomRow { team: "T4"; responsibility: "CPU++" }
                RoomRow { team: "T5"; responsibility: "TABS / SURFACE" }
                RoomRow { team: "T6"; responsibility: "APPLICATION AUDIO" }
                RoomRow { team: "T7"; responsibility: "DESKTOP IDENTITY" }
                RoomRow { team: "T8"; responsibility: "APPS" }
            }

            // ===== ACTION BAY ===================================

            Rectangle {
                width: parent.width
                height: 54

                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 5
                    z: -1
                    opacity: 0.42
                    color: Colors.cyan
                }

                Row {
                    anchors.centerIn: parent
                    spacing: 22

                    GohuText {
                        text: "REFRESH"
                        font.pixelSize: 10
                        color: Colors.cyan
                        opacity: 0.45
                    }

                    GohuText {
                        text: "AUDIT"
                        font.pixelSize: 10
                        color: Colors.cyan
                        opacity: 0.45
                    }

                    GohuText {
                        text: "GITHUB"
                        font.pixelSize: 10
                        color: Colors.cyan
                        opacity: 0.45
                    }
                }

                GohuText {
                    anchors {
                        right: parent.right
                        bottom: parent.bottom
                        rightMargin: 8
                        bottomMargin: 5
                    }

                    text: "ACTUATORS OFFLINE"
                    font.pixelSize: 8
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 6
                        samples: 7
                        opacity: 0.62
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }
            }
        }

    }
}
