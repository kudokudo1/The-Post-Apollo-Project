import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false

    property int panelWidth: 540
    property int panelHeight: 470
    property int panelTopMargin: 0
    property int panelLeftMargin: 600
    property int frameInset: 8

    implicitWidth: panelWidth
    implicitHeight: panelHeight

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin
        right: 0
        bottom: 0
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay

    color: "transparent"
    surfaceFormat.opaque: false
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
        color: Colors.orange
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan
    }

    component MetaValue: GohuText {
        font.pixelSize: 11
        color: Colors.white
        elide: Text.ElideRight
    }

    component ActionButton: Rectangle {
        id: actionButton

        property string label: ""
        property bool enabledAction: false

        width: 112
        height: 36

        color: Colors.dark
        border.width: 1
        border.color: enabledAction ? Colors.orange : Colors.cyan
        opacity: enabledAction ? 1.0 : 0.45

        GohuText {
            anchors.centerIn: parent
            text: actionButton.label
            font.pixelSize: 10
            color: actionButton.enabledAction ? Colors.orange : Colors.cyan
        }
    }

    // Active outer frame glow. Kept inside the surface bounds so the
    // menu can remain flush with the top edge.
    Rectangle {
        id: frameGlowSource

        anchors.fill: parent

        color: "transparent"
        border.width: 2
        border.color: Colors.orange

        opacity: root.menuOpen ? 1.0 : 0.0

        z: 2
    }

    DropShadow {
        anchors.fill: frameGlowSource
        source: frameGlowSource

        horizontalOffset: 0
        verticalOffset: 0

        radius: 18
        samples: 23

        color: Colors.orange
        opacity: root.menuOpen ? 0.76 : 0.0

        z: 3

        transparentBorder: true
    }

    Rectangle {
        id: frame
        anchors.fill: parent

        color: Colors.black
        opacity: root.menuOpen ? 0.97 : 0.0

        border.width: 2
        border.color: Colors.orange

        Rectangle {
            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        Column {
            anchors {
                fill: parent
                margins: 18
            }

            spacing: 12

            Item {
                width: parent.width
                height: 56

                GohuText {
                    anchors {
                        left: parent.left
                        top: parent.top
                    }

                    text: "GIT // LOCAL REPOSITORY"
                    font.pixelSize: 20
                    color: Colors.orange
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

                    width: 94
                    height: 26

                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange

                    GohuText {
                        anchors.centerIn: parent
                        text: "NOT CONNECTED"
                        font.pixelSize: 8
                        color: Colors.orange
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 2
                color: Colors.orange
            }

            Rectangle {
                width: parent.width
                height: 154

                color: Colors.dark
                border.width: 1
                border.color: Colors.orange

                Column {
                    anchors {
                        fill: parent
                        margins: 12
                    }

                    spacing: 8

                    SectionLabel {
                        text: "LOCAL TRUTH"
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "REPOSITORY"
                        }

                        MetaValue {
                            width: 365
                            text: "NOT CONNECTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "BRANCH"
                        }

                        MetaValue {
                            width: 365
                            text: "NOT CONNECTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "HEAD"
                        }

                        MetaValue {
                            width: 365
                            text: "NOT CONNECTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "WORKTREE"
                        }

                        MetaValue {
                            width: 365
                            text: "NOT CONNECTED"
                        }
                    }
                }
            }

            SectionLabel {
                text: "LOCAL ACTIONS"
            }

            Row {
                width: parent.width
                spacing: 10

                ActionButton { label: "STATUS" }
                ActionButton { label: "DIFF" }
                ActionButton { label: "LOG" }
                ActionButton { label: "LAZYGIT" }
            }

            Rectangle {
                width: parent.width
                height: 88

                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors {
                        fill: parent
                        margins: 12
                    }

                    spacing: 8

                    SectionLabel {
                        text: "REMOTE"
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "ORIGIN"
                        }

                        MetaValue {
                            width: 365
                            text: "NOT CONNECTED"
                        }
                    }

                    Row {
                        spacing: 10

                        MetaLabel {
                            width: 100
                            text: "NETWORK"
                        }

                        MetaValue {
                            width: 365
                            text: "NOT REQUESTED"
                        }
                    }
                }
            }

            Row {
                width: parent.width
                spacing: 10

                ActionButton { label: "FETCH" }
                ActionButton { label: "PULL" }
                ActionButton { label: "PUSH" }
            }

            GohuText {
                width: parent.width
                text: "READERS OFFLINE // NO GIT COMMANDS EXECUTED"
                horizontalAlignment: Text.AlignRight
                font.pixelSize: 8
                color: Colors.orange
            }
        }

    }
}
