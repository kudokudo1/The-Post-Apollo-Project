import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"
import "hub"
import "../services/hub/ApolloHubLayout.js" as Layout
import qs.services.hub

// Configurable in-Hub workspace. The shared shell owns live service instances;
// this UI only consumes snapshots supplied through its liveBridge property.
PanelWindow {
    id: hub

    property bool menuOpen: false
    property bool editMode: false
    // Injected read-only ApolloHubLiveBridge; do not construct a second provider.
    property var liveBridge: null
    // Only the currently keyboard-owned window may consume navigation keys.
    // The standalone preview uses keyboardActive=true; the main bar supplies
    // relationship-focus guards when it mounts this window.
    property bool keyboardActive: true
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false
    signal keyboardOwnershipRequested()
    property int selectedTileIndex: 0
    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)
        && !modeNameInput.activeFocus
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

    readonly property int frameWidth: 1000
    readonly property int frameHeight: 700
    readonly property int glowGutter: 12
    readonly property int frameInset: 8

    function toggle() {
        menuOpen = !menuOpen;
    }

    function restore() {
        if (writingLayout)
            return;
        layout = Layout.parse(ApolloHubStore.layoutJson);
        selectedModeIndex = Math.min(selectedModeIndex, layout.modes.length - 1);
        selectedSubModeIndex = 0;
        selectedTileIndex = 0;
    }

    function save(next) {
        writingLayout = true;
        layout = Layout.normalize(next);
        ApolloHubStore.layoutJson = JSON.stringify(layout);
        writingLayout = false;
    }

    function chooseMode(index) {
        if (index < 0 || index >= layout.modes.length)
            return;
        selectedModeIndex = index;
        selectedSubModeIndex = 0;
        selectedTileIndex = 0;
    }

    function cycleMainMode(direction) {
        const count = layout.modes.length;
        if (count < 2)
            return;
        const step = Number(direction) < 0 ? -1 : 1;
        chooseMode((selectedModeIndex + step + count) % count);
    }

    function selectSubMode(index) {
        if (!activeMode || index < 0 || index >= activeMode.subModes.length)
            return;
        selectedSubModeIndex = index;
        selectedTileIndex = 0;
    }

    function cycleTopSubMode(direction) {
        if (!activeMode || activeMode.subModes.length < 2)
            return;
        const count = activeMode.subModes.length;
        const step = Number(direction) < 0 ? -1 : 1;
        selectSubMode((selectedSubModeIndex + step + count) % count);
    }

    // The initial tile grid is two columns wide. Keep navigation bounded;
    // selection previews a card, it does not activate its action.
    function moveNavigationCursor(delta) {
        if (activeTiles.length < 1)
            return;
        selectedTileIndex = Math.max(0, Math.min(
            activeTiles.length - 1, selectedTileIndex + delta));
    }

    function activateNavigationCursor() {
        // View-mode modules without real action adapters are deliberately inert.
        // EDIT + Enter performs only the same safe module-cycle as SWAP.
        if (!editMode || selectedTileIndex < 0
                || selectedTileIndex >= activeTiles.length)
            return;
        save(Layout.cycleTile(layout, selectedModeIndex,
                              selectedSubModeIndex, selectedTileIndex));
    }

    function shiftTile(fromIndex, toIndex) {
        save(Layout.swapTiles(layout, selectedModeIndex, selectedSubModeIndex,
                              fromIndex, toIndex));
    }

    Component.onCompleted: restore()
    onMenuOpenChanged: {
        if (menuOpen && keyboardActive)
            Qt.callLater(function() {
                if (hub.standardKeysAvailable)
                    hubKeyboardAnchor.forceActiveFocus();
            });
    }
    onKeyboardActiveChanged: {
        if (menuOpen && keyboardActive)
            Qt.callLater(function() {
                if (hub.standardKeysAvailable)
                    hubKeyboardAnchor.forceActiveFocus();
            });
    }

    Connections {
        target: ApolloHubStore
        function onLayoutJsonChanged() { hub.restore(); }
    }

    screen: Quickshell.screens.find(s => s.name === "DP-5")
    implicitWidth: frameWidth + glowGutter * 2
    // Leave glow room on the sides and bottom, but let the visible chassis
    // touch the top edge of the display without an empty strip.
    implicitHeight: frameHeight + glowGutter

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }
    margins {
        top: 0
        left: Math.max(0, Math.round(
            ((hub.screen ? hub.screen.width : 2560) - hub.implicitWidth) / 2))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        hub.menuOpen && hub.keyboardActive
        ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: hub.menuOpen && hub.keyboardActive
    color: "transparent"
    surfaceFormat.opaque: false

    // Keep the layer surface mapped like the established FinanceW window.
    // The closed input mask is zero-sized, avoiding an invisible click blocker.
    visible: true
    mask: Region {
        x: hub.glowGutter
        y: 0
        width: hub.menuOpen ? hub.frameWidth : 0
        height: hub.menuOpen ? hub.frameHeight : 0
    }

    // Qt may consume Tab before a WindowShortcut; intercept locally when
    // the navigation anchor owns Qt focus, and keep matching guarded shortcuts
    // for all the other keyboard focus paths. Never intercept text editing.
    Item {
        id: hubKeyboardAnchor
        anchors.fill: parent
        z: -1000
        focus: hub.standardKeysAvailable
        enabled: hub.standardKeysAvailable

        Keys.priority: Keys.BeforeItem
        Keys.onShortcutOverride: function(event) {
            if (!hub.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab
                    || event.key === Qt.Key_Escape) {
                event.accepted = true;
            }
        }
        Keys.onPressed: function(event) {
            if (!hub.standardKeysAvailable)
                return;
            if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) {
                const reverse = event.key === Qt.Key_Backtab
                                || (event.modifiers & Qt.ShiftModifier) !== 0;
                hub.cycleMainMode(reverse ? -1 : 1);
            } else if ((event.modifiers & Qt.ShiftModifier) !== 0
                       && (event.key === Qt.Key_Left || event.key === Qt.Key_Right)) {
                hub.cycleTopSubMode(event.key === Qt.Key_Left ? -1 : 1);
            } else if (event.key === Qt.Key_Left) {
                hub.moveNavigationCursor(-1);
            } else if (event.key === Qt.Key_Right) {
                hub.moveNavigationCursor(1);
            } else if (event.key === Qt.Key_Up) {
                hub.moveNavigationCursor(-2);
            } else if (event.key === Qt.Key_Down) {
                hub.moveNavigationCursor(2);
            } else if (event.key === Qt.Key_Enter || event.key === Qt.Key_Return) {
                hub.activateNavigationCursor();
            } else if (event.key === Qt.Key_Escape) {
                hub.menuOpen = false;
            } else {
                return;
            }
            event.accepted = true;
        }
    }

    Shortcut {
        sequence: "Tab"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.cycleMainMode(1)
    }
    Shortcut {
        sequence: "Shift+Tab"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.cycleMainMode(-1)
    }
    Shortcut {
        sequence: "Shift+Left"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.cycleTopSubMode(-1)
    }
    Shortcut {
        sequence: "Shift+Right"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.cycleTopSubMode(1)
    }
    Shortcut {
        sequence: "Left"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor(-1)
    }
    Shortcut {
        sequence: "Right"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor(1)
    }
    Shortcut {
        sequence: "Up"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor(-2)
    }
    Shortcut {
        sequence: "Down"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor(2)
    }
    Shortcut {
        sequence: "Enter"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.activateNavigationCursor()
    }
    Shortcut {
        sequence: "Return"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.activateNavigationCursor()
    }
    Shortcut {
        sequence: "Esc"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.menuOpen = false
    }

    WindowPanelFrame {
        anchors.fill: parent
        anchors.margins: hub.glowGutter
        anchors.topMargin: 0
        visible: hub.menuOpen
        glowVisible: hub.menuOpen
        glowColor: Colors.magenta
        fillColor: Colors.black
        fillOpacity: 0.96
        borderColor: Colors.magenta
        borderWidth: 1
        radius: 0

        HoverHandler {
            enabled: hub.menuOpen
            onHoveredChanged: {
                if (hovered)
                    hub.keyboardOwnershipRequested();
            }
        }

        // Hospital/Git chassis variant: square, cyan inner outline separated
        // from the magenta outer frame by an eight-pixel inset.
        Rectangle {
            id: hubInnerFrame
            anchors.fill: parent
            anchors.margins: hub.frameInset
            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

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
                    color: Colors.magenta
                    text: "APOLLO // HUB"
                }
                ActionButton {
                    // Keep text and its sampled glow aligned during layout/state changes.
                    trackLabelGlowLocally: true
                    id: editButton
                    width: 85
                    height: 32
                    label: hub.editMode ? "VIEW" : "EDIT"
                    selected: hub.editMode
                    onLeftClicked: hub.editMode = !hub.editMode
                }
                ActionButton {
                    trackLabelGlowLocally: true
                    // Standard Close × (U+00D7), not the letter X.
                    // Red is the permanent close identity; the shared
                    // destructive pressed state remains black-on-red.
                    id: closeButton
                    width: 35
                    height: 32
                    label: "×"
                    labelPixelSize: 22
                    contentPadding: 4
                    accentColor: Colors.red
                    destructive: true
                    idleForegroundColor: Colors.red
                    hoverForegroundColor: Colors.red
                    selectedForegroundColor: Colors.red
                    keyboardSelectedForegroundColor: Colors.red
                    hoverBorderColor: Colors.red
                    selectedBorderColor: Colors.red
                    keyboardSelectedBorderColor: Colors.red
                    idleContentGlowColor: Colors.red
                    hoverContentGlowColor: Colors.red
                    selectedContentGlowColor: Colors.red
                    keyboardSelectedContentGlowColor: Colors.red
                    softGlowEnabled: true
                    idleSoftGlowColor: Colors.red
                    hoverSoftGlowColor: Colors.red
                    pressedSoftGlowColor: Colors.red
                    softGlowIdleOpacity: 0.48
                    softGlowHoverOpacity: 0.70
                    wideGlowEnabled: true
                    idleWideGlowColor: Colors.red
                    hoverWideGlowColor: Colors.red
                    pressedWideGlowColor: Colors.red
                    wideGlowIdleOpacity: 0.22
                    wideGlowHoverOpacity: 0.32
                    onLeftClicked: hub.menuOpen = false
                }
            }

            Rectangle {
                id: headerDivider
                width: parent.width
                height: 2
                color: Colors.cyan
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
                        // Default Grid glyphs and sampled glows track the same
                        // reactive coordinates without becoming Grid children.
                        trackDefaultGlowsLocally: true
                        selected: hub.selectedModeIndex === index
                        keyboardActive: hub.standardKeysAvailable
                        keyboardSelected: hub.selectedModeIndex === index
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
                        // Keep text and its sampled glow aligned during layout/state changes.
                        trackLabelGlowLocally: true
                        width: Math.min(160, Math.max(76, subStrip.width / Math.max(1, hub.activeMode.subModes.length) - 6))
                        height: subStrip.height
                        label: hub.activeMode.subModes[index].name
                        selected: hub.selectedSubModeIndex === index
                        keyboardSelected: hub.standardKeysAvailable
                                          && hub.selectedSubModeIndex === index
                        onLeftClicked: hub.selectSubMode(index)
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
                    // Keep text and its sampled glow aligned during layout/state changes.
                    trackLabelGlowLocally: true
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
                    // Keep text and its sampled glow aligned during layout/state changes.
                    trackLabelGlowLocally: true
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
                    // Keep text and its sampled glow aligned during layout/state changes.
                    trackLabelGlowLocally: true
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
                        id: modeNameInput
                        anchors.fill: parent
                        color: Colors.white
                        font.pixelSize: 14
                        selectByMouse: true
                        text: hub.activeMode ? hub.activeMode.name : ""
                        onEditingFinished: {
                            hub.save(Layout.renameMode(
                                hub.layout, hub.selectedModeIndex, text));
                            if (hub.menuOpen && hub.keyboardActive)
                                Qt.callLater(function() {
                                    hubKeyboardAnchor.forceActiveFocus();
                                });
                        }
                    }
                }
            }

            Flickable {
                id: tileScroll
                width: parent.width
                // Reserve the footer and divider *inside* the fixed panel.
                // Edit mode has seven visible Column children; view has six.
                height: Math.max(100, hubColumn.height - header.height
                                 - headerDivider.height - modeStrip.height
                                 - subStrip.height - editRow.height
                                 - statusFooter.height
                                 - (hub.editMode ? 6 : 5) * hubColumn.spacing)
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
                            // Live QML binding; changes to the shared bridge's
                            // weatherSnapshot update the tile without copying data.
                            weatherSnapshot: hub.liveBridge
                                             ? hub.liveBridge.weatherSnapshot : null
                            tileIndex: index
                            tileCount: hub.activeTiles.length
                            editing: hub.editMode
                            keyboardSelected: hub.standardKeysAvailable
                                              && hub.selectedTileIndex === index
                            onPointerEntered: hub.selectedTileIndex = index
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
                id: statusFooter
                width: parent.width
                height: 26
                verticalAlignment: Text.AlignVCenter
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
