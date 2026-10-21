import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "hub"
import "../services/hub/ApolloHubLayout.js" as Layout
import qs.services.hub

// ApolloHubW foundation, intentionally NOT wired into shell.qml yet.
// This is a configurable in-Hub workspace, not a replacement for the domain
// owners (Calendar, CPU++, Media, Network, etc.).
PanelWindow {
    id: hub

    property bool menuOpen: false
    property bool editMode: false
    property bool writingLayout: false
    property var layout: Layout.defaultLayout()
    property int selectedModeIndex: 0
    property int selectedSubModeIndex: 0

    readonly property var activeMode:
        layout.modes.length > selectedModeIndex ? layout.modes[selectedModeIndex] : null
    readonly property var activeSubMode:
        activeMode && activeMode.subModes.length > selectedSubModeIndex
        ? activeMode.subModes[selectedSubModeIndex] : null
    readonly property var activeTiles: activeSubMode ? activeSubMode.tiles : []

    readonly property int frameWidth: 700
    readonly property int frameHeight: 670
    readonly property int glowGutter: 12

    function toggle() {
        menuOpen = !menuOpen;
    }

    function restore() {
        if (writingLayout)
            return;
        layout = Layout.parse(ApolloHubStore.layoutJson);
        selectedModeIndex = Math.min(selectedModeIndex, layout.modes.length - 1);
        selectedSubModeIndex = 0;
    }

    function save(next) {
        writingLayout = true;
        layout = Layout.normalize(next);
        ApolloHubStore.layoutJson = JSON.stringify(layout);
        writingLayout = false;
    }

    function chooseMode(index) {
        selectedModeIndex = index;
        selectedSubModeIndex = 0;
    }

    function shiftTile(fromIndex, toIndex) {
        save(Layout.swapTiles(layout, selectedModeIndex, selectedSubModeIndex,
                              fromIndex, toIndex));
    }

    Component.onCompleted: restore()

    Connections {
        target: ApolloHubStore
        function onLayoutJsonChanged() { hub.restore(); }
    }

    screen: Quickshell.screens.find(s => s.name === "DP-5")
    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: 70
        left: Math.max(0, Math.round(
            ((hub.screen ? hub.screen.width : 2560) - hub.implicitWidth) / 2))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        hub.menuOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: hub.menuOpen
    color: "transparent"
    surfaceFormat.opaque: false

    // Keep the layer surface mapped like the established FinanceW window.
    // The closed input mask is zero-sized, avoiding an invisible click blocker.
    visible: true
    mask: Region {
        x: hub.glowGutter
        y: hub.glowGutter
        width: hub.menuOpen ? hub.frameWidth : 0
        height: hub.menuOpen ? hub.frameHeight : 0
    }

    Shortcut {
        sequence: "Esc"
        context: Qt.WindowShortcut
        enabled: hub.menuOpen
        onActivated: hub.menuOpen = false
    }

    WindowPanelFrame {
        anchors.fill: parent
        anchors.margins: hub.glowGutter
        visible: hub.menuOpen
        glowVisible: hub.menuOpen
        glowColor: Colors.cyan
        fillColor: Colors.black
        fillOpacity: 0.96
        borderColor: Colors.cyan
        borderWidth: 1
        radius: 5

        Column {
            id: hubColumn
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            Row {
                id: header
                width: parent.width
                height: 42
                spacing: 8

                GohuText {
                    width: parent.width - editButton.width - closeButton.width - 20
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 18
                    font.weight: 700
                    color: Colors.cyan
                    text: "APOLLO // HUB"
                }
                ActionButton {
                    id: editButton
                    width: 85
                    height: 32
                    label: hub.editMode ? "VIEW" : "EDIT"
                    selected: hub.editMode
                    onLeftClicked: hub.editMode = !hub.editMode
                }
                ActionButton {
                    id: closeButton
                    width: 35
                    height: 32
                    label: "×"
                    destructive: true
                    onLeftClicked: hub.menuOpen = false
                }
            }

            Row {
                id: modeStrip
                width: parent.width
                height: 55
                spacing: 6

                Repeater {
                    model: hub.layout.modes.length
                    ModeButton {
                        width: (modeStrip.width - (hub.layout.modes.length - 1) * modeStrip.spacing)
                               / hub.layout.modes.length
                        height: modeStrip.height
                        selected: hub.selectedModeIndex === index
                        iconText: hub.layout.modes[index].icon
                        labelText: hub.layout.modes[index].name
                        iconFontSize: 18
                        labelFontSize: 11
                        onTriggered: hub.chooseMode(index)
                    }
                }
            }

            Row {
                id: subStrip
                width: parent.width
                height: 33
                spacing: 6

                Repeater {
                    model: hub.activeMode ? hub.activeMode.subModes.length : 0
                    ActionButton {
                        width: Math.min(160, Math.max(76, subStrip.width / Math.max(1, hub.activeMode.subModes.length) - 6))
                        height: subStrip.height
                        label: hub.activeMode.subModes[index].name
                        selected: hub.selectedSubModeIndex === index
                        onLeftClicked: hub.selectedSubModeIndex = index
                    }
                }
            }

            Row {
                id: editRow
                width: parent.width
                height: hub.editMode ? 40 : 0
                visible: hub.editMode
                spacing: 6

                ActionButton {
                    width: 88
                    height: 32
                    label: "+ MODE"
                    available: hub.layout.modes.length < 6
                    onLeftClicked: {
                        hub.save(Layout.addMode(hub.layout));
                        hub.chooseMode(hub.layout.modes.length - 1);
                    }
                }
                ActionButton {
                    width: 92
                    height: 32
                    label: "+ GROUP"
                    available: hub.activeMode && hub.activeMode.subModes.length < 6
                    onLeftClicked: {
                        hub.save(Layout.addSubMode(hub.layout, hub.selectedModeIndex));
                        hub.selectedSubModeIndex = hub.activeMode.subModes.length - 1;
                    }
                }
                ActionButton {
                    width: 85
                    height: 32
                    label: "+ TILE"
                    available: hub.activeTiles.length < 8
                    onLeftClicked: hub.save(Layout.addTile(
                        hub.layout, hub.selectedModeIndex, hub.selectedSubModeIndex))
                }
                GohuText {
                    height: 32
                    verticalAlignment: Text.AlignVCenter
                    color: Colors.cyan
                    text: "MODE:"
                }
                SectionFrame {
                    width: 190
                    height: 32
                    fillColor: Colors.black
                    borderColor: Colors.magenta
                    borderWidth: 1
                    inset: 5

                    TextInput {
                        anchors.fill: parent
                        color: Colors.white
                        font.pixelSize: 14
                        selectByMouse: true
                        text: hub.activeMode ? hub.activeMode.name : ""
                        onEditingFinished: hub.save(
                            Layout.renameMode(hub.layout, hub.selectedModeIndex, text))
                    }
                }
            }

            Flickable {
                id: tileScroll
                width: parent.width
                height: Math.max(100, hubColumn.height - header.height - modeStrip.height
                                 - subStrip.height - editRow.height - 5 * hubColumn.spacing)
                contentWidth: width
                contentHeight: tileFlow.height
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                Flow {
                    id: tileFlow
                    width: tileScroll.width
                    height: childrenRect.height
                    spacing: 8

                    Repeater {
                        model: hub.activeTiles.length

                        ApolloHubTile {
                            readonly property var tileConfig: hub.activeTiles[index]
                            moduleId: tileConfig.module
                            tileIndex: index
                            tileCount: hub.activeTiles.length
                            editing: hub.editMode
                            width: tileConfig.size === "wide"
                                   ? tileFlow.width
                                   : (tileFlow.width - tileFlow.spacing) / 2
                            height: 140
                            onMoveLeft: hub.shiftTile(index, index - 1)
                            onMoveRight: hub.shiftTile(index, index + 1)
                            onChangeModule: hub.save(Layout.cycleTile(
                                hub.layout, hub.selectedModeIndex,
                                hub.selectedSubModeIndex, index))
                        }
                    }
                }
            }

            GohuText {
                width: parent.width
                height: 22
                color: Colors.cyan
                opacity: 0.8
                font.pixelSize: 11
                text: hub.editMode
                      ? "← → MOVE TILE    SWAP CHANGE MODULE    MAX 6 MODES / 6 GROUPS / 8 TILES"
                      : "FOUNDATION PREVIEW  //  LIVE TIME + DATE; OTHER DATA ADAPTERS PENDING"
            }
        }
    }
}
