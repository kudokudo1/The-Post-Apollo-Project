import QtQuick
import Quickshell
import Quickshell.Wayland
import "TasksChassisPolicy.js" as TasksChassisPolicy
import "../services/prism/PrismIndex.js" as PrismIndex
import "../components"

// PRISM // One reusable widget chassis, no separate dictionary data yet.
// Geometry follows TASKS' three portrait levels. Its height cannot exceed
// the exact full-height reserve currently owned by Trash.
PanelWindow {
    id: root
    objectName: "prismWindow"
    property bool menuOpen: false
    property string chassisLevel: "compact"
    // The owning shell binds this to the actual Prism dock border color.
    property color prismBorderColor: Colors.white
    property bool indexOpen: false
    // Source-backed registered placements. Not a service scan or heartbeat.
    readonly property var registeredLocations: PrismIndex.registered()
    onMenuOpenChanged: if (!menuOpen) indexOpen = false
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
        borderColor: root.prismBorderColor
        borderWidth: 1
        radius: 0
        glowVisible: root.menuOpen
        glowColor: root.prismBorderColor

        Rectangle {
            id: prismHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            // Two rows preserve legibility at TASKS' narrow portrait sizes.
            // The upper row is the title and close; the lower row is the
            // ordinary controls family and a source label, NOT a live poll.
            height: 84
            color: "transparent"

            GohuText {
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.right: closePrismButton.left
                anchors.rightMargin: 8
                anchors.verticalCenter: closePrismButton.verticalCenter
                text: "PRISM // POST APOLLO"
                font.pixelSize: 17
                font.bold: true
                color: root.prismBorderColor
                elide: Text.ElideRight
            }

            CloseButton {
                id: closePrismButton
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.top: parent.top
                anchors.topMargin: 5
                Accessible.name: "Close Prism widget"
                onCloseRequested: root.menuOpen = false
            }

            Row {
                id: prismToolbar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                anchors.top: parent.top
                anchors.topMargin: 45
                height: 28
                spacing: 5

                ResizeButton {
                    id: collapsePrismButton
                    width: 28
                    direction: "down"
                    available: root.chassisLevel !== "compact"
                    onResizeRequested: function(delta) {
                        if (delta === -1) root.collapseChassis();
                    }
                }
                ResizeButton {
                    id: expandPrismButton
                    width: 28
                    direction: "up"
                    available: root.chassisLevel !== "large"
                    onResizeRequested: function(delta) {
                        if (delta === 1) root.expandChassis();
                    }
                }

                Item {
                    width: Math.max(0, prismToolbar.width
                        - collapsePrismButton.width - expandPrismButton.width
                        - prismSourceIndicator.width - prismReloadButton.width
                        - prismIndexButton.width - prismToolbar.spacing * 5)
                    height: 1
                }

                // "Live indicator" location, but no fabricated liveness:
                // this is only a static semantic-source identification badge.
                Rectangle {
                    id: prismSourceIndicator
                    objectName: "prismSourceIndicator"
                    width: Math.max(0, Math.min(126, prismToolbar.width
                        - 28 - 28 - 30 - 38 - prismToolbar.spacing * 4))
                    height: 27
                    radius: 0
                    color: Colors.dark
                    border.width: 1
                    border.color: root.prismBorderColor

                    GohuText {
                        anchors.fill: parent
                        anchors.leftMargin: 3
                        anchors.rightMargin: 3
                        text: "COLOR // SYNTAGMA"
                        color: root.prismBorderColor
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }

                // The standard ReloadButton stays visible but unavailable.
                // No reload action or fabricated service is wired yet.
                ReloadButton {
                    id: prismReloadButton
                    objectName: "prismReloadButton"
                    width: 30
                    height: 28
                    available: false
                    unavailableOpacity: 0.80
                    semanticColor: Colors.yellow
                    hoverSurfaceColor: Colors.orange
                    Accessible.name: "Reload Prism index not yet available"
                }

                // The diagnostic control opens the real placement index.
                // Selection follows the displayed index, not a fake scan.
                DiagnosticsDockButton {
                    id: prismIndexButton
                    objectName: "prismIndexButton"
                    width: 38
                    height: 28
                    diagnosticsOpen: root.indexOpen
                    Accessible.description: "Registered Prism locations index"
                    onToggleRequested: root.indexOpen = !root.indexOpen
                }
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
            color: root.prismBorderColor
        }

        Item {
            id: prismBody
            anchors.top: prismDivider.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            Column {
                visible: !root.indexOpen
                anchors.centerIn: parent
                width: Math.max(0, parent.width - 28)
                spacing: 12

                GohuText {
                    width: parent.width
                    text: "VISUAL LANGUAGE // DICTIONARY"
                    font.pixelSize: 13
                    color: root.prismBorderColor
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
                    color: root.prismBorderColor
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }

            // First dossier/index: exactly those Prism placements registered
            // in source, with no invented readiness or definitions. Future
            // modules append a verified entry in the common registry.
            Flickable {
                id: prismIndex
                objectName: "prismPlacementIndex"
                visible: root.indexOpen
                anchors.fill: parent
                anchors.margins: 14
                clip: true
                contentWidth: width
                contentHeight: indexColumn.implicitHeight
                flickableDirection: Flickable.VerticalFlick

                Column {
                    id: indexColumn
                    width: prismIndex.width
                    spacing: 12

                    GohuText {
                        width: parent.width
                        text: "PRISM // PLACEMENT INDEX"
                        color: root.prismBorderColor
                        font.pixelSize: 15
                        font.bold: true
                        elide: Text.ElideRight
                    }
                    GohuText {
                        width: parent.width
                        text: root.registeredLocations.length + " REGISTERED LOCATIONS"
                        color: Colors.orange
                        font.pixelSize: 11
                    }
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: root.prismBorderColor
                    }

                    Repeater {
                        model: root.registeredLocations
                        delegate: Rectangle {
                            width: indexColumn.width
                            height: 88
                            radius: 0
                            color: Colors.dark
                            border.width: 1
                            border.color: root.prismBorderColor

                            Column {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 6
                                GohuText {
                                    width: parent.width
                                    text: modelData.name
                                    color: root.prismBorderColor
                                    font.pixelSize: 14
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: modelData.location
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: modelData.definitions + " DEFINITIONS // " + modelData.source
                                    color: Colors.orange
                                    font.pixelSize: 10
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                    GohuText {
                        width: parent.width
                        text: "INDEX OF INSTALLED PRISM ENTRY POINTS // NOT A SERVICE CHECK"
                        wrapMode: Text.WordWrap
                        color: root.prismBorderColor
                        font.pixelSize: 10
                        opacity: 0.7
                    }
                }
            }

        }
    }
}
