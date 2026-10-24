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

    // Owner-owned windows are represented by bounded availability/state
    // and explicit signals, never passed into tile delegates as handles.
    property bool appControlAvailable: false
    property var processSnapshot: null
    property var socialSnapshot: null
    property bool socialActionsAvailable: false
    signal openAppControlRequested()
    signal openSocialRequested()
    signal socialPlatformRequested(int index)

    function requestAppControl() {
        if (!appControlAvailable || !menuOpen)
            return;
        openAppControlRequested();
        menuOpen = false;
    }
    function requestSocialOpen() {
        if (!socialActionsAvailable || !menuOpen)
            return;
        openSocialRequested();
        menuOpen = false;
    }
    function requestSocialPlatform(index) {
        if (!socialActionsAvailable || !menuOpen
                || !Number.isInteger(index) || index < 0 || index > 3)
            return;
        socialPlatformRequested(index);
        menuOpen = false;
    }
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
    property real modulePickerAnchorX: 12
    property real modulePickerAnchorY: 12
    readonly property var modulePickerChoices: Layout.moduleChoices(
        layout, selectedModeIndex, selectedSubModeIndex,
        modulePickerTileIndex, modulePickerQuery)
    property bool transferPickerOpen: false
    property int transferTileIndex: -1
    property string transferTileId: ""
    property string transferModeId: ""
    property string transferGroupId: ""
    readonly property var transferTargets: Layout.moveTargets(
        layout, selectedModeIndex, selectedSubModeIndex, transferTileIndex)
    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)
        && !modeNameInput.activeFocus
        && !modulePickerOpen
        && !transferPickerOpen
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
    // Derived presentation only. Packing never changes the stored tile order.
    readonly property var tileGrid: Layout.packTiles(activeTiles)

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
        closeTransferPicker();
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
        closeTransferPicker();
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
        closeTransferPicker();
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
        closeTransferPicker();
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
        modulePickerInput.text = "";
        if (menuOpen && keyboardActive)
            Qt.callLater(function() {
                if (hub.standardKeysAvailable)
                    hubKeyboardAnchor.forceActiveFocus();
            });
    }

    function openModulePicker(index, sourceItem) {
        if (!menuOpen || !editMode || layoutStorageIssue.length > 0
                || pendingRemoval !== null || !activeMode || !activeSubMode
                || index < 0 || index >= activeTiles.length || !sourceItem)
            return;
        closeTransferPicker();
        // Anchor to the actual SWAP button, not a guessed tile width/height.
        // Keep the popup within the Hub chassis on either side of the button.
        const below = sourceItem.mapToItem(
            modulePickerOverlay, 0, sourceItem.height + 3);
        const above = sourceItem.mapToItem(modulePickerOverlay, 0, 0);
        modulePickerAnchorX = Math.max(10, Math.min(
            modulePickerOverlay.width - modulePickerPopup.width - 10, below.x));
        modulePickerAnchorY = below.y + modulePickerPopup.height
                              <= modulePickerOverlay.height - 10
                              ? below.y
                              : Math.max(10, above.y - modulePickerPopup.height - 3);
        modulePickerTileIndex = index;
        modulePickerTileId = activeTiles[index].id;
        modulePickerModeId = activeMode.id;
        modulePickerGroupId = activeSubMode.id;
        modulePickerQuery = "";
        modulePickerInput.text = "";
        modulePickerOpen = true;
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

    function closeTransferPicker() {
        const wasOpen = transferPickerOpen;
        transferPickerOpen = false;
        transferTileIndex = -1;
        transferTileId = "";
        transferModeId = "";
        transferGroupId = "";
        if (wasOpen && menuOpen && keyboardActive)
            Qt.callLater(function() {
                if (hub.standardKeysAvailable)
                    hubKeyboardAnchor.forceActiveFocus();
            });
    }

    function openTransferPicker(index, sourceItem) {
        if (!menuOpen || !editMode || layoutStorageIssue.length > 0
                || pendingRemoval !== null || !activeMode || !activeSubMode
                || index < 0 || index >= activeTiles.length || !sourceItem)
            return;
        closeModulePicker();
        // Same floating overlay as SWAP, positioned from the actual MOVE
        // button. Vertical flipping and horizontal clamping are shared.
        const below = sourceItem.mapToItem(
            modulePickerOverlay, 0, sourceItem.height + 3);
        const above = sourceItem.mapToItem(modulePickerOverlay, 0, 0);
        modulePickerAnchorX = Math.max(10, Math.min(
            modulePickerOverlay.width - modulePickerPopup.width - 10, below.x));
        modulePickerAnchorY = below.y + modulePickerPopup.height
                              <= modulePickerOverlay.height - 10
                              ? below.y
                              : Math.max(10, above.y - modulePickerPopup.height - 3);
        transferTileIndex = index;
        transferTileId = activeTiles[index].id;
        transferModeId = activeMode.id;
        transferGroupId = activeSubMode.id;
        transferPickerOpen = true;
        Qt.callLater(function() {
            if (hub.transferPickerOpen)
                transferFocusAnchor.forceActiveFocus();
        });
    }

    function chooseTransferDestination(modeId, groupId) {
        if (!transferPickerOpen || !menuOpen || !editMode
                || layoutStorageIssue.length > 0 || pendingRemoval !== null
                || !activeMode || !activeSubMode
                || activeMode.id !== transferModeId
                || activeSubMode.id !== transferGroupId
                || transferTileIndex < 0 || transferTileIndex >= activeTiles.length
                || activeTiles[transferTileIndex].id !== transferTileId)
            return;
        const target = transferTargets.items.find(function(row) {
            return row.modeId === modeId && row.groupId === groupId;
        });
        if (!target || !target.available)
            return;
        const moved = Layout.transferTile(
            layout, selectedModeIndex, selectedSubModeIndex, transferTileIndex,
            transferTileId, transferModeId, transferGroupId,
            target.modeIndex, target.groupIndex, target.modeId, target.groupId);
        if (JSON.stringify(moved) === JSON.stringify(layout))
            return;
        save(moved);
        // Show the destination and selected tile immediately after transfer;
        // the same UNDO action restores the original layout document.
        selectedModeIndex = target.modeIndex;
        selectedSubModeIndex = target.groupIndex;
        selectedTileIndex = Math.max(0, activeTiles.length - 1);
        closeTransferPicker();
    }

    function chooseMode(index) {
        if (index < 0 || index >= layout.modes.length)
            return;
        cancelPendingRemoval();
        closeModulePicker();
        closeTransferPicker();
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
        closeTransferPicker();
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

    // Stage 7: follow the packed tiles' actual rectangles, never saved-index
    // +/-1 or +/-2. Selection previews a card; it never activates its action.
    function moveNavigationCursor(direction) {
        if (activeTiles.length < 1 || tileGrid.state !== "ready")
            return;
        const next = Layout.navigationTarget(tileGrid, selectedTileIndex,
                                             direction);
        if (next === selectedTileIndex)
            return;
        selectedTileIndex = next;
        // Keep the selected card visible within the existing Flickable.
        // This does not change tile positions or saved layout JSON.
        const card = tileRepeater.itemAt(next);
        if (!card)
            return;
        const margin = tileFlow.spacing;
        const maxScroll = Math.max(0, tileScroll.contentHeight - tileScroll.height);
        // A H:3 card may be taller than this viewport. Favor its header
        // rather than scrolling directly to the bottom of the card.
        if (card.height + 2 * margin > tileScroll.height
                || card.y < tileScroll.contentY + margin)
            tileScroll.contentY = Math.min(maxScroll, Math.max(0, card.y - margin));
        else if (card.y + card.height > tileScroll.contentY + tileScroll.height - margin)
            tileScroll.contentY = Math.min(maxScroll,
                card.y + card.height - tileScroll.height + margin);
    }

    function activateNavigationCursor() {
        // View-mode modules without real action adapters are deliberately inert.
        // EDIT + Enter opens the same safe selector as SWAP.
        if (!editMode || selectedTileIndex < 0
                || selectedTileIndex >= activeTiles.length)
            return;
        const selected = tileRepeater.itemAt(selectedTileIndex);
        openModulePicker(selectedTileIndex, selected ? selected.swapAnchor : null);
    }

    function shiftTile(fromIndex, toIndex) {
        save(Layout.swapTiles(layout, selectedModeIndex, selectedSubModeIndex,
                              fromIndex, toIndex));
    }

    Component.onCompleted: restore()
    onEditModeChanged: if (!editMode) {
        cancelPendingRemoval();
        closeModulePicker();
        closeTransferPicker();
    }
    onMenuOpenChanged: {
        if (!menuOpen) {
            cancelPendingRemoval();
            closeModulePicker();
            closeTransferPicker();
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
                hub.moveNavigationCursor("left");
            } else if (event.key === Qt.Key_Right) {
                hub.moveNavigationCursor("right");
            } else if (event.key === Qt.Key_Up) {
                hub.moveNavigationCursor("up");
            } else if (event.key === Qt.Key_Down) {
                hub.moveNavigationCursor("down");
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
        onActivated: hub.moveNavigationCursor("left")
    }
    Shortcut {
        sequence: "Right"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor("right")
    }
    Shortcut {
        sequence: "Up"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor("up")
    }
    Shortcut {
        sequence: "Down"
        context: Qt.WindowShortcut
        enabled: hub.standardKeysAvailable
        onActivated: hub.moveNavigationCursor("down")
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
    Shortcut {
        // Cancel the picker even if focus moves off the search/list.
        sequence: "Esc"
        context: Qt.WindowShortcut
        enabled: hub.menuOpen && (hub.modulePickerOpen || hub.transferPickerOpen)
        onActivated: {
            hub.closeModulePicker();
            hub.closeTransferPicker();
        }
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

                Item {
                    id: tileFlow
                    width: tileScroll.width
                    property int spacing: 8
                    // Same 140px base and 8px gap used by the original Flow,
                    // but computed grid cells can be filled beside tall tiles.
                    height: hub.tileGrid.rows > 0
                            ? hub.tileGrid.rows * 140
                              + (hub.tileGrid.rows - 1) * spacing
                            : 0

                    Repeater {
                        id: tileRepeater
                        model: hub.activeTiles.length

                        ApolloHubTile {
                            readonly property var tileConfig: hub.activeTiles[index]
                            readonly property var gridCell: hub.tileGrid.items[index]
                            // Pure first-fit coordinates in the existing two
                            // columns. Width, row span and identity are saved
                            // exactly as before; only x/y are derived.
                            x: gridCell ? gridCell.column
                               * ((tileFlow.width - tileFlow.spacing) / 2
                                  + tileFlow.spacing) : 0
                            y: gridCell ? gridCell.row * (140 + tileFlow.spacing) : 0
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
                            appControlAvailable: hub.appControlAvailable
                            processSnapshot: hub.processSnapshot
                            socialSnapshot: hub.socialSnapshot
                            socialActionsAvailable: hub.socialActionsAvailable
                            onOpenAppControlRequested: hub.requestAppControl()
                            onOpenSocialRequested: hub.requestSocialOpen()
                            onSocialPlatformRequested: function(index) {
                                hub.requestSocialPlatform(index);
                            }
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
                            onChangeModule: hub.openModulePicker(index, sourceItem)
                            onTransferTile: hub.openTransferPicker(index, sourceItem)
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
                      : hub.modulePickerOpen
                      ? "MODULE PICKER // CLICK TO SELECT // ESC OR CLOSE TO CANCEL"
                      : hub.transferPickerOpen
                      ? "MOVE TILE // CHOOSE DESTINATION // ESC OR CLOSE TO CANCEL"
                      : hub.editMode
                      ? "← → REORDER    SWAP MODULE    MOVE GROUP    W/H SIZE    × REMOVE    UNDO"
                      : "APOLLO HUB  //  LIVE MODULES CONNECTED"
            }
        }

        // The selector floats above the scrollable grid. Unlike the old
        // full-page picker, neither the grid nor its scroll position changes.
        Item {
            id: modulePickerOverlay
            anchors.fill: parent
            z: 200
            visible: hub.modulePickerOpen || hub.transferPickerOpen

            // A transparent input surface blocks underlying tile actions
            // while the dropdown is open. Consistent with TimeW's TapHandler.
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                TapHandler {
                    onTapped: {
                        hub.closeModulePicker();
                        hub.closeTransferPicker();
                    }
                }
            }

            Rectangle {
                id: modulePickerPopup
                x: hub.modulePickerAnchorX
                y: hub.modulePickerAnchorY
                width: 368
                height: 342
                color: Colors.black
                border.width: 1
                border.color: Colors.magenta
                z: 1

                // Empty-space taps inside the popup never dismiss it.
                TapHandler {
                    onTapped: {}
                }

                Column {
                    id: modulePickerDropdownContent
                    visible: hub.modulePickerOpen
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 7

                    Row {
                        width: parent.width
                        height: 27
                        spacing: 6
                        GohuText {
                            width: parent.width - 78
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            color: Colors.magenta
                            font.pixelSize: 12
                            text: "SWAP // "
                                + (hub.modulePickerTileIndex >= 0
                                   && hub.modulePickerTileIndex < hub.activeTiles.length
                                   ? Layout.tileTitle(
                                       hub.activeTiles[hub.modulePickerTileIndex].module)
                                   : "UNAVAILABLE")
                        }
                        ActionButton {
                            trackLabelGlowLocally: true
                            width: 72
                            height: 26
                            label: "CLOSE"
                            onLeftClicked: hub.closeModulePicker()
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.7
                    }

                    SectionFrame {
                        width: parent.width
                        height: 34
                        fillColor: Colors.black
                        borderColor: Colors.cyan
                        borderWidth: 1
                        inset: 6

                        TextInput {
                            id: modulePickerInput
                            anchors.fill: parent
                            color: Colors.white
                            font.pixelSize: 13
                            selectByMouse: true
                            text: ""
                            onTextChanged: hub.modulePickerQuery = text
                            Keys.onPressed: function(event) {
                                if (event.key === Qt.Key_Escape) {
                                    hub.closeModulePicker();
                                    event.accepted = true;
                                } else if (event.key === Qt.Key_Enter
                                           || event.key === Qt.Key_Return) {
                                    // Only a single unambiguous, nonblank
                                    // result may be selected using Enter.
                                    if (hub.modulePickerQuery.trim().length > 0
                                            && hub.modulePickerChoices.availableCount === 1) {
                                        const match = hub.modulePickerChoices.items.find(
                                            function(item) { return item.available; });
                                        if (match)
                                            hub.chooseModuleFromPicker(match.id);
                                    }
                                    event.accepted = true;
                                }
                            }
                        }
                        GohuText {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 11
                            color: Colors.cyan
                            opacity: 0.6
                            enabled: false
                            visible: modulePickerInput.text.length === 0
                            text: "SEARCH MODULE / ID"
                        }
                    }

                    GohuText {
                        width: parent.width
                        height: 19
                        verticalAlignment: Text.AlignVCenter
                        font.pixelSize: 11
                        color: Colors.cyan
                        text: hub.modulePickerChoices.state !== "ready"
                              ? "MODULE LIST UNAVAILABLE"
                              : hub.modulePickerChoices.matchCount + " / "
                                + hub.modulePickerChoices.total
                                + " MATCHES  //  "
                                + hub.modulePickerChoices.availableCount
                                + " SELECTABLE"
                    }

                    ListView {
                        id: modulePickerResults
                        width: parent.width - modulePickerRail.crossExtent - 4
                        height: 212
                        clip: true
                        spacing: 2
                        model: hub.modulePickerChoices.items
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height

                        delegate: ActionButton {
                            trackLabelGlowLocally: true
                            width: modulePickerResults.width
                            height: 30
                            contentPadding: 7
                            labelPixelSize: 11
                            labelHorizontalAlignment: Text.AlignLeft
                            available: modelData.available
                            selected: modelData.selected
                            label: modelData.title + "  //  " + modelData.id
                                   + (modelData.selected ? "  [CURRENT]"
                                      : modelData.inUse ? "  [IN USE]" : "")
                            onLeftClicked: hub.chooseModuleFromPicker(modelData.id)
                        }
                    }
                }

                Column {
                    id: transferPickerDropdownContent
                    visible: hub.transferPickerOpen
                    anchors.fill: parent
                    anchors.margins: 9
                    spacing: 7

                    Row {
                        width: parent.width
                        height: 27
                        spacing: 6
                        GohuText {
                            width: parent.width - 78
                            height: parent.height
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                            color: Colors.magenta
                            font.pixelSize: 12
                            text: "MOVE // "
                                  + (hub.transferTileIndex >= 0
                                     && hub.transferTileIndex < hub.activeTiles.length
                                     ? Layout.tileTitle(
                                         hub.activeTiles[hub.transferTileIndex].module)
                                     : "UNAVAILABLE")
                        }
                        ActionButton {
                            trackLabelGlowLocally: true
                            width: 72
                            height: 26
                            label: "CLOSE"
                            onLeftClicked: hub.closeTransferPicker()
                        }
                    }
                    Rectangle {
                        width: parent.width
                        height: 1
                        color: Colors.cyan
                        opacity: 0.7
                    }
                    GohuText {
                        width: parent.width
                        height: 37
                        verticalAlignment: Text.AlignVCenter
                        color: Colors.cyan
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                        text: hub.transferTargets.state !== "ready"
                              ? "DESTINATIONS UNAVAILABLE"
                              : "CHOOSE A MODE / GROUP  //  "
                                + hub.transferTargets.availableCount
                                + " / " + hub.transferTargets.total
                                + " AVAILABLE"
                    }
                    ListView {
                        id: transferPickerResults
                        width: parent.width - transferPickerRail.crossExtent - 4
                        height: 235
                        clip: true
                        spacing: 3
                        model: hub.transferTargets.items
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height

                        delegate: ActionButton {
                            trackLabelGlowLocally: true
                            width: transferPickerResults.width
                            height: 33
                            contentPadding: 7
                            labelPixelSize: 11
                            labelHorizontalAlignment: Text.AlignLeft
                            available: modelData.available
                            label: modelData.label
                                   + "  [" + modelData.count + "/8]"
                                   + (modelData.reason.length > 0
                                      ? "  " + modelData.reason : "")
                            onLeftClicked: hub.chooseTransferDestination(
                                modelData.modeId, modelData.groupId)
                        }
                    }
                }
                Item {
                    id: transferFocusAnchor
                    width: 0
                    height: 0
                    focus: hub.transferPickerOpen
                    visible: false
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Escape) {
                            hub.closeTransferPicker();
                            event.accepted = true;
                        }
                    }
                }

                NeonScrollBar {
                    id: transferPickerRail
                    flickable: transferPickerResults
                    accountForContentOrigin: true
                    geometryMode: "viewport"
                    x: modulePickerPopup.width - width - 4
                    y: transferPickerResults.mapToItem(modulePickerPopup, 0, 0).y
                    height: transferPickerResults.height
                    handleStyle: "star"
                    railColor: Colors.cyan
                    handleColor: Colors.magenta
                    handleBorderColor: Colors.magenta
                    railGlowColor: Colors.white
                    visible: hub.transferPickerOpen
                             && transferPickerResults.contentHeight > transferPickerResults.height
                }

                NeonScrollBar {
                    id: modulePickerRail
                    flickable: modulePickerResults
                    accountForContentOrigin: true
                    geometryMode: "viewport"
                    x: modulePickerPopup.width - width - 4
                    y: modulePickerResults.mapToItem(modulePickerPopup, 0, 0).y
                    height: modulePickerResults.height
                    handleStyle: "star"
                    railColor: Colors.cyan
                    handleColor: Colors.magenta
                    handleBorderColor: Colors.magenta
                    railGlowColor: Colors.white
                    visible: hub.modulePickerOpen
                             && modulePickerResults.contentHeight > modulePickerResults.height
                }
            }
        }
    }
}
