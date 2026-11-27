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
    property string helpPage: "syntagma"
    readonly property var helpModes: [
        { id: "syntagma", label: "SYNTAGMA" },
        { id: "atlas", label: "ATLAS" }
    ]
    function selectHelpPage(page) {
        if (page !== "syntagma" && page !== "atlas") return;
        helpPage = page;
        indexOpen = false;
    }
    // Source-backed registered placements. Not a service scan or heartbeat.
    readonly property var registeredLocations: PrismIndex.registered()
    onMenuOpenChanged: if (!menuOpen) indexOpen = false
    // The shell binds this to trashWindow.fullHeightReserve. This fallback
    // keeps standalone previews safe before the parent supplies a Trash owner.
    property int fullHeightReserve: 165
    property real dockCenterX: 108
    property real chassisTopY: 80
    // Trash panel's bottom is 90 + 10 - 15 = 85px above the screen.
    // Anchor Prism to that same baseline, growing upward at every size.
    readonly property int frameBottomClearance: Math.max(0, fullHeightReserve - chassisTopY)

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
        top: false
        bottom: true
        left: true
        right: false
    }
    margins {
        bottom: Math.max(0, root.frameBottomClearance - root.bottomScreenGap)
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
        x: root.glowGutter
        y: root.frameTopInset
        width: root.frameWidth
        height: root.frameHeight
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
        borderVisible: false
        radius: 0
        glowVisible: false

        // SurfaceFrame's default border is above its content. Place one
        // fixed white edge INSIDE that content instead, beneath the spectrum.
        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 1
            border.color: root.prismBorderColor
            z: -1
        }
        PrismBorderGlow {
            anchors.fill: parent
            z: 3
        }

        Rectangle {
            id: prismHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 40
            color: "transparent"

            PrismTextGlow { labelItem: prismTitleText }
            GohuText {
                id: prismTitleText
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.right: prismToolbar.left
                anchors.rightMargin: 5
                anchors.verticalCenter: parent.verticalCenter
                text: width >= 145 ? "PRISM // POST APOLLO" : "PRISM"
                font.pixelSize: width >= 145 ? 14 : 12
                font.bold: true
                color: root.prismBorderColor
                elide: Text.ElideRight
            }

            // Exact operator order, starting at the right edge.
            Row {
                id: prismToolbar
                anchors.right: parent.right
                anchors.rightMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                layoutDirection: Qt.RightToLeft
                spacing: 3
                readonly property int controlWidth:
                    Math.max(16, Math.min(28, Math.floor((prismHeader.width - 100) / 6)))

                CloseButton {
                    id: closePrismButton
                    width: prismToolbar.controlWidth
                    height: width
                    Accessible.name: "Close Prism widget"
                    onCloseRequested: root.menuOpen = false
                }
                ReloadButton {
                    id: prismReloadButton
                    objectName: "prismReloadButton"
                    width: prismToolbar.controlWidth
                    height: width
                    available: false
                    unavailableOpacity: 0.80
                    semanticColor: Colors.yellow
                    hoverSurfaceColor: Colors.orange
                    Accessible.name: "Reload Prism index not yet available"
                }
                Rectangle {
                    id: prismSourceIndicator
                    objectName: "prismSourceIndicator"
                    width: Math.max(0, Math.min(94, prismHeader.width
                        - 5 * prismToolbar.controlWidth - prismToolbar.spacing * 5 - 45))
                    height: prismToolbar.controlWidth
                    radius: 0
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.white
                    PrismBorderGlow { anchors.fill: parent }
                    PrismTextGlow { labelItem: prismSourceText; strength: 0.85 }
                    GohuText {
                        id: prismSourceText
                        anchors.fill: parent
                        anchors.leftMargin: 2
                        anchors.rightMargin: 2
                        text: "COLOR // SYNTAGMA"
                        color: root.prismBorderColor
                        font.pixelSize: 9
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                    }
                }
                DiagnosticsDockButton {
                    id: prismIndexButton
                    objectName: "prismIndexButton"
                    width: prismToolbar.controlWidth
                    height: width
                    diagnosticsOpen: root.indexOpen
                    Accessible.description: "Registered Prism locations index"
                    onToggleRequested: root.indexOpen = !root.indexOpen
                }
                ResizeButton {
                    id: expandPrismButton
                    width: prismToolbar.controlWidth
                    direction: "up"
                    available: root.chassisLevel !== "large"
                    onResizeRequested: function(delta) {
                        if (delta === 1) root.expandChassis();
                    }
                }
                ResizeButton {
                    id: collapsePrismButton
                    width: prismToolbar.controlWidth
                    direction: "down"
                    available: root.chassisLevel !== "compact"
                    onResizeRequested: function(delta) {
                        if (delta === -1) root.collapseChassis();
                    }
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
            height: 1
            color: root.prismBorderColor
            PrismBorderGlow { anchors.fill: parent; divider: true }
        }

        // Ordinary main-mode buttons; no Prism overrides on controls.
        Row {
            id: prismMainModes
            anchors.top: prismDivider.bottom
            anchors.topMargin: 8
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            height: 38
            spacing: 6

            Repeater {
                model: root.helpModes
                ModeButton {
                    required property var modelData
                    width: Math.max(0, (prismMainModes.width - prismMainModes.spacing)
                                           / root.helpModes.length)
                    height: prismMainModes.height
                    textOnly: true
                    labelText: modelData.label
                    labelFontSize: 12
                    bordered: false
                    selected: !root.indexOpen && root.helpPage === modelData.id
                    onTriggered: root.selectHelpPage(modelData.id)
                }
            }
        }

        Item {
            id: prismBody
            anchors.top: prismMainModes.bottom
            anchors.topMargin: 8
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom

            PrismHelpContent {
                anchors.fill: parent
                visible: !root.indexOpen
                page: root.helpPage
                structuralColor: root.prismBorderColor
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
                        PrismBorderGlow { anchors.fill: parent; divider: true }
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
                            PrismBorderGlow { anchors.fill: parent }

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
