import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "ForestChassisPolicy.js" as ForestSizing

// FOREST V0: self-contained visual workspace. No model, PX or Hospital calls.
PanelWindow {
    id: root

    property bool menuOpen: false
    property real dockCenterX: 0
    property int chassisLevel: 0
    property int selectedTreeIndex: 0
    readonly property var treeSlots: [
        { name: "CHERRY", role: "GENERAL COORDINATOR", mark: "✿" },
        { name: "MAPLE", role: "FILES & ORGANIZATION", mark: "🍁" }
    ]
    readonly property var activeTree: treeSlots[selectedTreeIndex]
    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 8
    readonly property var chassisFrame: ForestSizing.frame(
        chassisLevel, root.screen ? root.screen.width : 1366,
        root.screen ? root.screen.height : 768,
        glowGutter, frameTopInset, bottomScreenGap)
    readonly property int frameWidth: chassisFrame.width
    readonly property int frameHeight: chassisFrame.height
    readonly property int sideWidth:
        Math.min(204, Math.max(144, Math.round(frameWidth * 0.31)))

    function toggle() { menuOpen = !menuOpen; }
    function expandChassis() { chassisLevel = ForestSizing.step(chassisLevel, 1); }
    function collapseChassis() { chassisLevel = ForestSizing.step(chassisLevel, -1); }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap
    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: ForestSizing.topMargin(
            root.screen ? root.screen.height : 768, root.implicitHeight)
        left: ForestSizing.leftMargin(
            root.screen ? root.screen.width : 1366,
            root.implicitWidth, root.dockCenterX)
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        root.menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: root.menuOpen
    color: "transparent"
    surfaceFormat.opaque: false
    // Remain mapped: a zero-size input mask makes the closed panel inert.
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.frameTopInset
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: forestFrame
        anchors.fill: parent
        anchors.leftMargin: root.glowGutter
        anchors.rightMargin: root.glowGutter
        anchors.topMargin: root.frameTopInset
        anchors.bottomMargin: root.bottomScreenGap
        visible: root.menuOpen
        focus: root.menuOpen
        fillColor: Colors.black
        fillOpacity: 0.97
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 0
        glowColor: Colors.magenta
        glowVisible: root.menuOpen
        Keys.onEscapePressed: function(event) {
            root.menuOpen = false;
            event.accepted = true;
        }

        Rectangle {
            id: header
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 56
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: collapseButton.left
                anchors.rightMargin: 8
                text: "FOREST // AI WORKSPACE"
                font.pixelSize: 16
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }
            ResizeButton {
                id: collapseButton
                anchors.right: expandButton.left
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                direction: "down"
                available: root.chassisLevel > 0
                onResizeRequested: function(delta) {
                    if (delta === -1) root.collapseChassis();
                }
            }
            ResizeButton {
                id: expandButton
                anchors.right: closeButton.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                direction: "up"
                available: root.chassisLevel < 3
                onResizeRequested: function(delta) {
                    if (delta === 1) root.expandChassis();
                }
            }
            CloseButton {
                id: closeButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                Accessible.name: "Close Forest workspace"
                onCloseRequested: root.menuOpen = false
            }
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
            }
        }

        Rectangle {
            id: treePane
            anchors.top: header.bottom
            anchors.bottom: footer.top
            anchors.left: parent.left
            width: root.sideWidth
            color: "transparent"

            GohuText {
                id: treeHeading
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.margins: 13
                text: "TREES // 02"
                font.pixelSize: 12
                color: Colors.cyan
            }
            Column {
                id: treeColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: treeHeading.bottom
                anchors.topMargin: 14
                anchors.leftMargin: 9
                anchors.rightMargin: 9
                spacing: 7
                Repeater {
                    model: root.treeSlots
                    Rectangle {
                        id: treeRow
                        width: treeColumn.width
                        height: 59
                        color: index === root.selectedTreeIndex ? Colors.dark : Colors.black
                        border.width: 1
                        border.color: index === root.selectedTreeIndex ? Colors.magenta : Colors.cyan
                        GohuText {
                            anchors.left: parent.left
                            anchors.leftMargin: 9
                            anchors.top: parent.top
                            anchors.topMargin: 9
                            text: modelData.mark + "  " + modelData.name
                            font.pixelSize: 12
                            font.bold: true
                            color: index === root.selectedTreeIndex ? Colors.magenta : Colors.white
                        }
                        GohuText {
                            anchors.left: parent.left
                            anchors.leftMargin: 9
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 9
                            width: parent.width - 18
                            elide: Text.ElideRight
                            text: modelData.role
                            font.pixelSize: 9
                            color: Colors.cyan
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedTreeIndex = index
                        }
                    }
                }
            }
            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 13
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 13
                text: "LEAVES // NOT CONNECTED"
                font.pixelSize: 9
                color: Colors.orange
                width: parent.width - 20
                wrapMode: Text.WordWrap
            }
            Rectangle {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 1
                color: Colors.cyan
            }
        }

        Item {
            id: chatPane
            anchors.left: treePane.right
            anchors.right: parent.right
            anchors.top: header.bottom
            anchors.bottom: footer.top

            GohuText {
                id: chatHeading
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.topMargin: 14
                text: root.activeTree.name + " // CHAT"
                color: Colors.magenta
                font.pixelSize: 15
            }
            GohuText {
                anchors.right: parent.right
                anchors.rightMargin: 13
                anchors.top: parent.top
                anchors.topMargin: 18
                text: "PREVIEW"
                color: Colors.orange
                font.pixelSize: 10
            }
            Rectangle {
                anchors.top: chatHeading.bottom
                anchors.topMargin: 12
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
            }
            Column {
                anchors.centerIn: parent
                width: Math.max(120, parent.width - 30)
                spacing: 13
                GohuText {
                    width: parent.width
                    text: "NO ACTIVE SESSION"
                    color: Colors.white
                    font.pixelSize: 15
                    horizontalAlignment: Text.AlignHCenter
                }
                GohuText {
                    width: parent.width
                    text: "OLLAMA / HERMES ADAPTER NOT CONNECTED"
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
                GohuText {
                    width: parent.width
                    text: "Forest V0 launcher preview. No model is running from this widget."
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }
            Rectangle {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 13
                height: 40
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                opacity: 0.65
                GohuText {
                    anchors.centerIn: parent
                    text: "MESSAGE // AVAILABLE AFTER LOCAL ADAPTER"
                    color: Colors.white
                    font.pixelSize: 9
                }
            }
        }

        Rectangle {
            id: footer
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 30
            color: Colors.black
            Rectangle {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                height: 1
                color: Colors.cyan
            }
            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "LOCAL FIRST // NO NETWORK REQUESTS"
                color: Colors.cyan
                font.pixelSize: 10
            }
            GohuText {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "TOOLS OFF"
                color: Colors.orange
                font.pixelSize: 10
            }
        }
    }
}
