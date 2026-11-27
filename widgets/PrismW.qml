import QtQuick
import Quickshell
import Quickshell.Wayland
import "TasksChassisPolicy.js" as TasksChassisPolicy
import "../components"

// PRISM // One reusable widget chassis, no separate dictionary data yet.
// Geometry follows TASKS' three portrait levels. Its height cannot exceed
// the exact full-height reserve currently owned by Trash.
PanelWindow {
    id: root
    objectName: "prismWindow"
    property bool menuOpen: false
    property string chassisLevel: "compact"
    // The shell binds this to trashWindow.fullHeightReserve. This fallback
    // keeps standalone previews safe before the parent supplies a Trash owner.
    property int fullHeightReserve: 165
    property real dockCenterX: 108
    property real chassisTopY: 80

    readonly property int glowGutter: 12
    readonly property int frameTopInset: 9
    readonly property int bottomScreenGap: 12
    readonly property int usableScreenHeight:
        root.screen ? root.screen.height : 1440
    readonly property int maximumFrameHeight:
        Math.max(1, usableScreenHeight - fullHeightReserve)
    readonly property var tasksChassisFrame: TasksChassisPolicy.frame(
        chassisLevel,
        root.screen ? root.screen.width : 456,
        usableScreenHeight, glowGutter, frameTopInset, bottomScreenGap)
    readonly property int frameHeight:
        Math.min(tasksChassisFrame.height, maximumFrameHeight)
    // TASKS portrait rule: narrow as the usable height becomes shorter.
    readonly property int frameWidth:
        Math.max(1, Math.min(tasksChassisFrame.width,
                             Math.floor(frameHeight * 0.58)))

    function toggle() { menuOpen = !menuOpen; }
    function expandChassis() {
        chassisLevel = TasksChassisPolicy.step(chassisLevel, 1);
    }
    function collapseChassis() {
        chassisLevel = TasksChassisPolicy.step(chassisLevel, -1);
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + frameTopInset + bottomScreenGap

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: TasksChassisPolicy.topMargin(
            root.chassisTopY, root.usableScreenHeight,
            root.implicitHeight, root.frameTopInset)
        left: TasksChassisPolicy.leftMargin(
            root.dockCenterX,
            root.screen ? root.screen.width : root.implicitWidth,
            root.implicitWidth)
    }
    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: menuOpen
    color: "transparent"
    surfaceFormat.opaque: false
    visible: true

    // Keep one mapped PanelWindow while closed. The menu has NO pointer
    // region until explicitly opened, and closing doesn't destroy the frame.
    mask: Region {
        x: root.glowGutter
        y: root.frameTopInset
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        id: prismFrame
        objectName: "prismWidgetFrame"
        anchors.fill: parent
        anchors.margins: root.glowGutter
        anchors.topMargin: root.frameTopInset
        visible: root.menuOpen
        focus: root.menuOpen
        Keys.onEscapePressed: function(event) {
            if (!root.menuOpen) return;
            root.menuOpen = false;
            event.accepted = true;
        }

        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 0
        glowVisible: root.menuOpen
        glowColor: Colors.cyan

        Rectangle {
            id: prismHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 56
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.right: collapsePrismButton.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                text: "PRISM // POST APOLLO"
                font.pixelSize: 17
                font.bold: true
                color: Colors.magenta
                elide: Text.ElideRight
            }

            ResizeButton {
                id: collapsePrismButton
                anchors.right: expandPrismButton.left
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                direction: "down"
                available: root.chassisLevel !== "compact"
                onResizeRequested: function(delta) {
                    if (delta === -1) root.collapseChassis();
                }
            }
            ResizeButton {
                id: expandPrismButton
                anchors.right: closePrismButton.left
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                direction: "up"
                available: root.chassisLevel !== "large"
                onResizeRequested: function(delta) {
                    if (delta === 1) root.expandChassis();
                }
            }
            CloseButton {
                id: closePrismButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                Accessible.name: "Close Prism widget"
                onCloseRequested: root.menuOpen = false
            }
        }

        Rectangle {
            id: prismDivider
            anchors.top: prismHeader.bottom
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.right: parent.right
            anchors.rightMargin: 12
            height: 2
            color: Colors.cyan
        }

        Item {
            id: prismBody
            anchors.top: prismDivider.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            Column {
                anchors.centerIn: parent
                width: Math.max(0, parent.width - 28)
                spacing: 12

                GohuText {
                    width: parent.width
                    text: "VISUAL LANGUAGE // DICTIONARY"
                    font.pixelSize: 13
                    color: Colors.white
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    text: "NO DEFINITIONS YET"
                    font.pixelSize: 12
                    color: Colors.orange
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
                GohuText {
                    width: parent.width
                    text: "POST APOLLO // CONTEXTUAL HELP"
                    font.pixelSize: 11
                    color: Colors.cyan
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
        }
    }
}
