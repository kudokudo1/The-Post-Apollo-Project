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
    // Do not let Hub mode shortcuts consume typing in the B7 editor.
    property bool todoInputFocused: false
    property bool notesInputFocused: false
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
    // The Hub picker is transient; it never changes the app catalog or file.
    property bool modulePickerOpen: false
    property int modulePickerTileIndex: -1
    property string modulePickerTileId: ""
    property string modulePickerModeId: ""
    property string modulePickerGroupId: ""
    property string modulePickerQuery: ""
    readonly property var modulePickerChoices: Layout.moduleChoices(
        layout, selectedModeIndex, selectedSubModeIndex,
        modulePickerTileIndex, modulePickerQuery)
    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)
        && !modeNameInput.activeFocus
        && !modulePickerOpen
        && !todoInputFocused
        && !notesInputFocused
    property bool writingLayout: false
    // In-session undo makes accidental tile deletion reversible.
    property var layoutUndoStack: []
    // Pending destructive layout action. Never touch a service or data store.
    property var pendingRemoval: null
    readonly property string layoutStorageIssue:
        Layout.storageIssue(ApolloHubStore.layoutJson)
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
        cancelPendingRemoval();
        closeModulePicker();
        layout = Layout.parse(ApolloHubStore.layoutJson);
        selectedModeIndex = Math.min(selectedModeIndex, layout.modes.length - 1);
        selectedSubModeIndex = 0;
        selectedTileIndex = 0;
    }

    function save(next) {
        // A newer/corrupt saved schema must not be overwritten by fallback UI.
        if (layoutStorageIssue.length > 0)
            return;
        const normalized = Layout.normalize(next);
        const previous = JSON.stringify(layout);
        if (JSON.stringify(normalized) === previous)
            return;
        cancelPendingRemoval();
        closeModulePicker();
        const history = layoutUndoStack.slice();
        history.push(previous);
        if (history.length > 10)
            history.shift();
        layoutUndoStack = history;
        writingLayout = true;
        layout = normalized;
        ApolloHubStore.layoutJson = JSON.stringify(layout);
        writingLayout = false;
    }

    function undoLastLayoutEdit() {
        if (layoutStorageIssue.length > 0 || layoutUndoStack.length < 1)
            return;
        cancelPendingRemoval();
        closeModulePicker();
        const history = layoutUndoStack.slice();
        const previous = history.pop();
        layoutUndoStack = history;
        writingLayout = true;
        layout = Layout.parse(previous);
        ApolloHubStore.layoutJson = JSON.stringify(layout);
        writingLayout = false;
        selectedModeIndex = Math.max(0, Math.min(
            selectedModeIndex, layout.modes.length - 1));
        selectedSubModeIndex = Math.max(0, Math.min(
            selectedSubModeIndex, activeMode.subModes.length - 1));
        selectedTileIndex = Math.max(0, Math.min(
            selectedTileIndex, activeTiles.length - 1));
    }

    function removeEditedTile(index) {
        if (!editMode || layoutStorageIssue.length > 0
                || index < 0 || index >= activeTiles.length)
            return;
        save(Layout.removeTile(layout, selectedModeIndex,
                               selectedSubModeIndex, index));
        selectedTileIndex = Math.max(0, Math.min(
            selectedTileIndex, activeTiles.length - 1));
    }

    function toggleEditedTileWidth(index) {
        if (!editMode || layoutStorageIssue.length > 0
                || index < 0 || index >= activeTiles.length)
            return;
        const tile = activeTiles[index];
        const nextSize = tile.size === "wide" ? "half" : "wide";
        save(Layout.resizeTile(layout, selectedModeIndex,
                               selectedSubModeIndex, index,
                               nextSize, tile.rowSpan));
    }

    function cycleEditedTileHeight(index) {
        if (!editMode || layoutStorageIssue.length > 0
                || index < 0 || index >= activeTiles.length)
            return;
        const tile = activeTiles[index];
        const nextSpan = tile.rowSpan >= Layout.MAX_ROW_SPAN
                         ? 1 : tile.rowSpan + 1;
        save(Layout.resizeTile(layout, selectedModeIndex,
                               selectedSubModeIndex, index,
                               tile.size, nextSpan));
    }

    function cancelPendingRemoval() {
        pendingRemoval = null;
    }

    function requestLayoutRemoval(kind) {
        if (!menuOpen || !editMode || layoutStorageIssue.length > 0
                || !activeMode)
            return;
        closeModulePicker();
        if (kind === "mode") {
            if (layout.modes.length <= 1)
                return;
            pendingRemoval = {
                kind: "mode",
                modeId: activeMode.id,
                label: activeMode.name,
                count: activeMode.subModes.length
            };
        } else if (kind === "group") {
            if (!activeSubMode || activeMode.subModes.length <= 1)
                return;
            pendingRemoval = {
                kind: "group",
                modeId: activeMode.id,
                groupId: activeSubMode.id,
                label: activeSubMode.name,
                count: activeSubMode.tiles.length
            };
        }
    }

    function confirmLayoutRemoval() {
        const pending = pendingRemoval;
        if (!pending)
            return;
        // Re-check both the expected stable IDs and the live selection.
        // A stale confirmation cannot delete whichever row moved into place.
        if (!menuOpen || !editMode || layoutStorageIssue.length > 0
                || !activeMode || activeMode.id !== pending.modeId) {
            cancelPendingRemoval();
            return;
        }
        if (pending.kind === "mode") {
            if (layout.modes.length <= 1) {
                cancelPendingRemoval();
                return;
            }
            save(Layout.removeMode(layout, selectedModeIndex,
                                   pending.modeId, true));
            selectedModeIndex = Math.max(0, Math.min(
                selectedModeIndex, layout.modes.length - 1));
            selectedSubModeIndex = 0;
            selectedTileIndex = 0;
        } else if (pending.kind === "group") {
            if (!activeSubMode || activeSubMode.id !== pending.groupId
                    || activeMode.subModes.length <= 1) {
                cancelPendingRemoval();
                return;
            }
            save(Layout.removeSubMode(layout, selectedModeIndex,
                                      selectedSubModeIndex, pending.groupId, true));
            selectedSubModeIndex = Math.max(0, Math.min(
                selectedSubModeIndex, activeMode.subModes.length - 1));
            selectedTileIndex = 0;
        }
        cancelPendingRemoval();
    }

    function closeModulePicker() {
        modulePickerOpen = false;
        modulePickerTileIndex = -1;
        modulePickerTileId = "";
        modulePickerModeId = "";
        modulePickerGroupId = "";
        modulePickerQuery = "";
        if (menuOpen && keyboardActive)
            Qt.callLater(function() {
                if (hub.standardKeysAvailable)
                    hubKeyboardAnchor.forceActiveFocus();
            });
    }

    function openModulePicker(index) {
        if (!menuOpen || !editMode || layoutStorageIssue.length > 0
                || pendingRemoval !== null || !activeMode || !activeSubMode
                || index < 0 || index >= activeTiles.length)
            return;
        modulePickerTileIndex = index;
        modulePickerTileId = activeTiles[index].id;
        modulePickerModeId = activeMode.id;
        modulePickerGroupId = activeSubMode.id;
        modulePickerQuery = "";
        modulePickerOpen = true;
        tileScroll.contentY = 0;
        Qt.callLater(function() {
            if (hub.modulePickerOpen)
                modulePickerInput.forceActiveFocus();
        });
    }

    function chooseModuleFromPicker(moduleId) {
        if (!modulePickerOpen || !menuOpen || !editMode
                || layoutStorageIssue.length > 0
                || pendingRemoval !== null || !activeMode || !activeSubMode
                || activeMode.id !== modulePickerModeId
                || activeSubMode.id !== modulePickerGroupId
                || modulePickerTileIndex < 0
                || modulePickerTileIndex >= activeTiles.length
                || activeTiles[modulePickerTileIndex].id !== modulePickerTileId)
            return;
        const choice = modulePickerChoices.items.find(function(item) {
            return item.id === moduleId;
        });
        if (!choice || !choice.available)
            return;
        const index = modulePickerTileIndex;
        save(Layout.setTileModule(layout, selectedModeIndex,
                                  selectedSubModeIndex, index,
                                  modulePickerTileId, moduleId));
        selectedTileIndex = index;
        closeModulePicker();
    }

    function chooseMode(index) {
        if (index < 0 || index >= layout.modes.length)
            return;
        cancelPendingRemoval();
        closeModulePicker();
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
        cancelPendingRemoval();
        closeModulePicker();
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
        // EDIT + Enter opens the same safe selector as SWAP.
        if (!editMode || selectedTileIndex < 0
                || selectedTileIndex >= activeTiles.length)
            return;
        openModulePicker(selectedTileIndex);
    }

    function shiftTile(fromIndex, toIndex) {
        save(Layout.swapTiles(layout, selectedModeIndex, selectedSubModeIndex,
                              fromIndex, toIndex));
    }

    Component.onCompleted: restore()
    onEditModeChanged: if (!editMode) {
        cancelPendingRemoval();
        closeModulePicker();
    }
    onMenuOpenChanged: {
        if (!menuOpen) {
            cancelPendingRemoval();
            closeModulePicker();
            todoInputFocused = false;
            notesInputFocused = false;
        }
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
                    visible: hub.pendingRemoval === null
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
                    visible: hub.pendingRemoval === null
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
                    visible: hub.pendingRemoval === null
                    available: hub.activeTiles.length < 8
                    onLeftClicked: hub.save(Layout.addTile(
                        hub.layout, hub.selectedModeIndex, hub.selectedSubModeIndex))
                }
                ActionButton {
                    trackLabelGlowLocally: true
                    width: 65
                    height: 32
                    label: "UNDO"
                    visible: hub.pendingRemoval === null
                    available: hub.layoutStorageIssue.length === 0
                               && hub.layoutUndoStack.length > 0
                    onLeftClicked: hub.undoLastLayoutEdit()
                }
                ActionButton {
                    // One click requests removal; separate CONFIRM persists it.
                    trackLabelGlowLocally: true
                    width: 84
                    height: 32
                    visible: hub.pendingRemoval === null
                    label: "− MODE"
                    accentColor: Colors.red
                    destructive: true
                    hoverFillColor: Colors.red
                    hoverForegroundColor: Colors.black
                    hoverBorderColor: Colors.red
                    available: hub.layoutStorageIssue.length === 0
                               && hub.layout.modes.length > 1
                    onLeftClicked: hub.requestLayoutRemoval("mode")
                }
                ActionButton {
                    trackLabelGlowLocally: true
                    width: 90
                    height: 32
                    visible: hub.pendingRemoval === null
                    label: "− GROUP"
                    accentColor: Colors.red
                    destructive: true
                    hoverFillColor: Colors.red
                    hoverForegroundColor: Colors.black
                    hoverBorderColor: Colors.red
                    available: hub.layoutStorageIssue.length === 0
                               && hub.activeMode !== null
                               && hub.activeMode.subModes.length > 1
                    onLeftClicked: hub.requestLayoutRemoval("group")
                }
                GohuText {
                    width: 320
                    height: 32
                    visible: hub.pendingRemoval !== null
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    color: Colors.orange
                    text: hub.pendingRemoval
                          ? "REMOVE " + hub.pendingRemoval.kind.toUpperCase()
                            + ": " + hub.pendingRemoval.label
                            + " (" + hub.pendingRemoval.count
                            + (hub.pendingRemoval.kind === "mode" ? " GROUPS)" : " TILES)")
                          : ""
                }
                ActionButton {
                    trackLabelGlowLocally: true
                    width: 96
                    height: 32
                    visible: hub.pendingRemoval !== null
                    label: "CONFIRM"
                    accentColor: Colors.red
                    destructive: true
                    hoverFillColor: Colors.red
                    hoverForegroundColor: Colors.black
                    hoverBorderColor: Colors.red
                    onLeftClicked: hub.confirmLayoutRemoval()
                }
                ActionButton {
                    trackLabelGlowLocally: true
                    width: 74
                    height: 32
                    visible: hub.pendingRemoval !== null
                    label: "CANCEL"
                    onLeftClicked: hub.cancelPendingRemoval()
                }
                GohuText {
                    height: 32
                    verticalAlignment: Text.AlignVCenter
                    color: Colors.cyan
                    text: "MODE:"
                    visible: hub.pendingRemoval === null
                }
                SectionFrame {
                    visible: hub.pendingRemoval === null
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
                            // B3 passive Network state is provided by the
                            // SAME read-only bridge. No new polling or
                            // NetworkManager control lives in the tile.
                            networkSnapshot: hub.liveBridge
                                             ? hub.liveBridge.networkSnapshot : null
                            // B4 read-only Media observation, retaining distinct
                            // MPD and explicitly selected MPRIS snapshots.
                            mediaSnapshot: hub.liveBridge
                                           ? hub.liveBridge.mediaSnapshot : null
                            // B2 CPU++ reuses the shared telemetry snapshot.
                            // A reactive QML binding, not a second collector.
                            systemSnapshot: hub.liveBridge
                                            ? hub.liveBridge.systemSnapshot : null
                            // B5 OS uptime is already read by the shared
                            // bridge. This binding adds no timer or procfs IO.
                            uptimeSnapshot: hub.liveBridge
                                            ? hub.liveBridge.uptimeSnapshot : null
                            // B6 passive desktop app catalog, without access
                            // to launch methods, command lines, or executables.
                            appsSnapshot: hub.liveBridge
                                          ? hub.liveBridge.appsSnapshot : null
                            // B7 task data belongs to a separate guarded
                            // singleton; never mix it with hub layout JSON.
                            todoStore: ApolloHubTodoStore
                            todoSnapshot: ApolloHubTodoStore.snapshot
                            onTodoTextFocusChanged: function(focused) {
                                hub.todoInputFocused = focused;
                            }
                            // B8 Notes is a separate singleton and never
                            // shares B7 To-do or the Hub layout JSON store.
                            notesStore: ApolloHubNotesStore
                            notesSnapshot: ApolloHubNotesStore.snapshot
                            onNotesTextFocusChanged: function(focused) {
                                hub.notesInputFocused = focused;
                            }
                            // B9 reuses the shared bridge's local civil
                            // calendar. Only explicit view button clicks
                            // update month offset or week-start preference.
                            calendarSnapshot: hub.liveBridge
                                              ? hub.liveBridge.calendarSnapshot : null
                            calendarBridge: hub.liveBridge
                            tileIndex: index
                            tileCount: hub.activeTiles.length
                            tileColumnSpan: tileConfig.size === "wide" ? 2 : 1
                            tileRowSpan: tileConfig.rowSpan || 1
                            editing: hub.editMode
                            keyboardSelected: hub.standardKeysAvailable
                                              && hub.selectedTileIndex === index
                            onPointerEntered: hub.selectedTileIndex = index
                            width: tileConfig.size === "wide"
                                   ? tileFlow.width
                                   : (tileFlow.width - tileFlow.spacing) / 2
                            // v2 rowSpan=1 preserves the original 140px tile.
                            height: 140 * (tileConfig.rowSpan || 1)
                                    + tileFlow.spacing * ((tileConfig.rowSpan || 1) - 1)
                            onMoveLeft: hub.shiftTile(index, index - 1)
                            onMoveRight: hub.shiftTile(index, index + 1)
                            onChangeModule: hub.openModulePicker(index)
                            onRemoveTile: hub.removeEditedTile(index)
                            onToggleTileWidth: hub.toggleEditedTileWidth(index)
                            onCycleTileHeight: hub.cycleEditedTileHeight(index)
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
                text: hub.layoutStorageIssue.length > 0
                      ? "LAYOUT READ ONLY // " + hub.layoutStorageIssue
                      : hub.pendingRemoval !== null
                      ? "CONFIRM REMOVE " + hub.pendingRemoval.kind.toUpperCase()
                        + " // " + hub.pendingRemoval.label + " // UNDO AVAILABLE"
                      : hub.editMode
                      ? "← → MOVE    SWAP MODULE    W:1/2 WIDTH    H:1/2/3 HEIGHT    × REMOVE    UNDO"
                      : "APOLLO HUB  //  LIVE MODULES CONNECTED"
            }
        }
    }
}
