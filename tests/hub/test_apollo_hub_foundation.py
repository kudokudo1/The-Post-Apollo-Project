#!/usr/bin/env python3
"""Source contracts for the standalone ApolloHubW foundation (no live shell change)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
dock = (ROOT / "modules/ApolloHub.qml").read_text(encoding="utf-8")
window = (ROOT / "widgets/ApolloHubW.qml").read_text(encoding="utf-8")
tile = (ROOT / "widgets/hub/ApolloHubTile.qml").read_text(encoding="utf-8")
network_explore = (ROOT / "widgets/hub/ApolloHubNetworkExplore.qml").read_text(encoding="utf-8")
weather_explore = (ROOT / "widgets/hub/ApolloHubWeatherExplore.qml").read_text(encoding="utf-8")
media_mini = (ROOT / "widgets/hub/ApolloHubMediaMini.qml").read_text(encoding="utf-8")
media_explore = (ROOT / "widgets/hub/ApolloHubMediaExplore.qml").read_text(encoding="utf-8")
system_mini = (ROOT / "widgets/hub/ApolloHubSystemMini.qml").read_text(encoding="utf-8")
uptime_mini = (ROOT / "widgets/hub/ApolloHubUptimeMini.qml").read_text(encoding="utf-8")
apps_mini = (ROOT / "widgets/hub/ApolloHubAppsMini.qml").read_text(encoding="utf-8")
apps_explore = (ROOT / "widgets/hub/ApolloHubAppsExplore.qml").read_text(encoding="utf-8")
process_explore = (ROOT / "widgets/hub/ApolloHubProcessesExplore.qml").read_text(encoding="utf-8")
process_policy = (ROOT / "services/hub/ApolloHubProcessesPolicy.js").read_text(encoding="utf-8")
social_mini = (ROOT / "widgets/hub/ApolloHubSocialMini.qml").read_text(encoding="utf-8")
todo_mini = (ROOT / "widgets/hub/ApolloHubTodoMini.qml").read_text(encoding="utf-8")
todo_explore = (ROOT / "widgets/hub/ApolloHubTodoExplore.qml").read_text(encoding="utf-8")
todo_store = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")
notes_mini = (ROOT / "widgets/hub/ApolloHubNotesMini.qml").read_text(encoding="utf-8")
notes_store = (ROOT / "services/hub/ApolloHubNotesStore.qml").read_text(encoding="utf-8")
calendar_mini = (ROOT / "widgets/hub/ApolloHubCalendarMini.qml").read_text(encoding="utf-8")
calendar_policy = (ROOT / "services/hub/ApolloHubCalendarPolicy.js").read_text(encoding="utf-8")
time_mini = (ROOT / "widgets/hub/ApolloHubTimeMini.qml").read_text(encoding="utf-8")
time_policy = (ROOT / "services/hub/ApolloHubTimePolicy.js").read_text(encoding="utf-8")
layout = (ROOT / "services/hub/ApolloHubLayout.js").read_text(encoding="utf-8")
store = (ROOT / "services/hub/ApolloHubStore.qml").read_text(encoding="utf-8")
module = (ROOT / "services/hub/qmldir").read_text(encoding="utf-8")

# Center dock integration is a separate shared-shell branch, allowing the
# user to accept the root-safe click preview before live activation.
assert "Calendar {" not in shell
assert "ApolloHub {" in shell
assert "ApolloHubW {" in shell
assert "onToggleRequested: apolloHubWindow.toggle()" in shell
assert "menuOpen: apolloHubWindow.menuOpen" in shell
assert "keyboardActive: !relationshipFocus.active" in shell
assert "WlrKeyboardFocus.Exclusive" not in window

# Use approved shared controls / frames rather than duplicating menus.
assert "DockButton {" in dock
assert 'NotoText {' in dock
assert 'textFormat: Text.StyledText' in dock
assert '⌯⌲ <font color=' in dock
assert '>🗓</font> ⋆˙⟡' in dock
assert """text: " ⌯⌲ <font color='" + (dock.open ? Colors.magenta : Colors.orange) + "'>🗓</font> ⋆˙⟡ " """ .strip() in dock
assert "color: dock.foregroundColor" in dock
assert "normalForegroundColor: Colors.white" in dock
assert "openForegroundColor: Colors.magenta" in dock
assert "contentGlowSource: hubMark" in dock
# Keep every chassis/artwork halo magenta, with reactive glow tracking.
# Ornaments and Calendar switch to magenta on open; Calendar is orange idle.
assert "normalDockGlowColor: Colors.magenta" in dock
assert "trackArtworkGlowLocally: true" in dock
for glow in ("hoverDockGlowColor", "pressedDockGlowColor", "openGlowColor",
             "normalContentGlowColor", "hoverContentGlowColor",
             "pressedContentGlowColor"):
    assert glow + ": Colors.magenta" in dock, glow
assert "PanelWindow {" in window
assert "WindowPanelFrame {" in window
assert "ModeButton {" in window

# ApolloHub chassis: 1000x700 visible body flush with top of screen,
# centered horizontally, square frame, magenta title and cyan inner outline.
assert "readonly property int frameWidth: 1000" in window
assert "readonly property int frameHeight: 700" in window
assert "readonly property int frameInset: 8" in window
assert "implicitHeight: frameHeight + glowGutter" in window
assert "        top: 0" in window
assert "anchors.topMargin: 0" in window
assert "((hub.screen ? hub.screen.width : 2560) - hub.implicitWidth) / 2" in window
assert "id: hubInnerFrame" in window
assert "anchors.margins: hub.frameInset" in window
assert "border.color: Colors.cyan" in window
assert "glowColor: Colors.magenta" in window
assert "borderColor: Colors.magenta" in window
assert "radius: 0" in window
assert 'color: Colors.magenta\n                    text: "APOLLO // HUB"' in window
assert "id: headerDivider" in window
assert "height: 2\n                color: Colors.cyan" in window

# Scroll content subtracts both header divider and fixed footer, including
# view/edit visibility-dependent Column spacings; the footer cannot be pushed
# below the bottom border by a full-height Flickable.
assert "id: statusFooter" in window
assert "- statusFooter.height" in window
assert "- headerDivider.height" in window
assert "(hub.editMode ? 6 : 5) * hubColumn.spacing" in window
assert "verticalAlignment: Text.AlignVCenter" in window
assert "    radius: 0\n    inset: 10" in tile
assert window.count("ActionButton {") >= 5
assert "SectionFrame {" in tile
assert "MouseArea {" not in window + tile + dock

# The header Close action uses the canonical U+00D7 multiplication sign.
# Red stays its identity for normal/hover/keyboard states, without changing
# ActionButton's destructive black-on-red pressed state. Size follows the
# accepted FinanceW Close precedent, not a generic 10px label.
close_start = window.index("id: closeButton")
close_end = window.index("onLeftClicked: hub.menuOpen = false", close_start)
close_button = window[close_start:close_end]
for needle in (
    'label: "×"',
    "labelPixelSize: 22",
    "contentPadding: 4",
    "accentColor: Colors.red",
    "destructive: true",
    "trackLabelGlowLocally: true",
    "hoverForegroundColor: Colors.red",
    "hoverBorderColor: Colors.red",
    "hoverContentGlowColor: Colors.red",
    "softGlowEnabled: true",
    "wideGlowEnabled: true",
    "softGlowIdleOpacity: 0.48",
    "wideGlowIdleOpacity: 0.22",
):
    # trackLabelGlowLocally appears before the id, unlike state/size options.
    if needle == "trackLabelGlowLocally: true":
        assert needle in window[window.rindex("ActionButton {", 0, close_start):close_start]
    else:
        assert needle in close_button, f"Hub Close missing {needle}"
assert 'label: "X"' not in close_button
assert 'label: "✕"' not in close_button
assert 'label: "✖"' not in close_button
assert "onLeftClicked: hub.menuOpen = false" in window[close_start:close_end + 42]

# Hub editor/selector buttons use ActionButton's existing reactive label
# tracking (proven on Projects ARCHIVE). Keep the icon and caption alignment
# independent from button backgrounds, halos and click actions.
import re

for path, source, count in (
    ("widgets/ApolloHubW.qml", window, 15),
    ("widgets/hub/ApolloHubTile.qml", tile, 7),
):
    actions = len(re.findall(r"\bActionButton\s*\{", source))
    tracked = len(re.findall(
        r"\bActionButton\s*\{\s*(?://[^\n]*\n\s*)?trackLabelGlowLocally:\s*true",
        source,
    ))
    assert actions == count, f"{path}: action count changed ({actions})"
    assert tracked == actions, f"{path}: {actions - tracked} untracked glow(s)"

for action in (
    'label: hub.editMode ? "VIEW" : "EDIT"',
    'label: hub.activeMode.subModes[index].name',
    'label: "+ MODE"',
    'label: "+ GROUP"',
    'label: "+ TILE"',
    'label: "UNDO"',
    'label: "− MODE"',
    'label: "− GROUP"',
    'label: "CONFIRM"',
    'label: "CANCEL"',
):
    assert action in window, f"Hub button behavior changed: {action}"
for action in ('label: "←"', 'label: "→"', 'label: "SWAP"', 'label: "MOVE"', 'label: "×"'):
    assert action in tile, f"Hub edit-tile action changed: {action}"

shared_action = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
assert "property bool trackLabelGlowLocally: true" in shared_action
assert "contentHost.x + labelText.x" in shared_action
assert "contentHost.y + labelText.y" in shared_action

# Configure modes/sub-modes and exchange module positions independently.
for name in ("defaultLayout", "normalize", "parse", "swapTiles",
             "renameMode", "addMode", "addSubMode", "addTile", "cycleTile",
             "removeTile", "resizeTile", "storageIssue",
             "removeMode", "removeSubMode", "moveTargets", "transferTile"):
    assert "function " + name + "(" in layout
assert 'var LAYOUT_VERSION = 2' in layout
assert 'version: LAYOUT_VERSION' in layout
assert 'Math.min(MAX_MODES, data.modes.length)' in layout
assert 'Math.min(MAX_SUBMODES, inputMode.subModes.length)' in layout
assert 'Math.min(MAX_TILES, inputSub.tiles.length)' in layout
assert 'rowSpan:' in layout
assert 'nextTileId' in layout
assert 'function assignId(input)' in layout
assert "onMoveLeft: hub.shiftTile(" in window
assert "onMoveRight: hub.shiftTile(" in window
assert "Layout.setTileModule(" in window
assert "Layout.cycleTile(" not in window
assert "signal removeTile(int index)" in tile
assert 'label: "×"' in tile
assert 'accentColor: Colors.red' in tile
assert 'onLeftClicked: tile.removeTile(tile.tileIndex)' in tile
assert 'onRemoveTile: hub.removeEditedTile(index)' in window
# P1 stage 2: no new service or layout schema; in-place edit-only resize
# controls preserve the normal tile size and share the Undo path.
for token in (
    'property int tileColumnSpan: 1',
    'property int tileRowSpan: 1',
    'label: "W:" + tile.tileColumnSpan',
    'label: "H:" + tile.tileRowSpan',
    'signal toggleTileWidth(int index)',
    'signal cycleTileHeight(int index)',
    'onLeftClicked: tile.toggleTileWidth(tile.tileIndex)',
    'onLeftClicked: tile.cycleTileHeight(tile.tileIndex)',
):
    assert token in tile, f"Tile resizing seam missing: {token}"
assert tile.index('label: "SWAP"') < tile.index('label: "W:"') \
       < tile.index('label: "H:"') < tile.index('label: "×"')
for token in (
    'function toggleEditedTileWidth(index)',
    'function cycleEditedTileHeight(index)',
    'nextSize = tile.size === "wide" ? "half" : "wide"',
    'tile.rowSpan >= Layout.MAX_ROW_SPAN',
    'Layout.resizeTile(layout, selectedModeIndex,',
    'tileColumnSpan: tileConfig.size === "wide" ? 2 : 1',
    'tileRowSpan: tileConfig.rowSpan || 1',
    'onToggleTileWidth: hub.toggleEditedTileWidth(index)',
    'onCycleTileHeight: hub.cycleEditedTileHeight(index)',
    'if (!editMode || layoutStorageIssue.length > 0',
):
    assert token in window, f"Hub resize wiring missing: {token}"
assert 'property var layoutUndoStack: []' in window
assert 'height: 140 * (tileConfig.rowSpan || 1)' in window
# Stage 3: deletion is staged and identity-bound; the last mode/group
# cannot be removed, and all successful mutations go through existing Undo.
for token in (
    'property var pendingRemoval: null',
    'function requestLayoutRemoval(kind)',
    'function confirmLayoutRemoval()',
    'function cancelPendingRemoval()',
    'Layout.removeMode(layout, selectedModeIndex,',
    'Layout.removeSubMode(layout, selectedModeIndex,',
    'layout.modes.length <= 1',
    'activeMode.subModes.length <= 1',
    'activeMode.id !== pending.modeId',
    'activeSubMode.id !== pending.groupId',
    'onLeftClicked: hub.requestLayoutRemoval("mode")',
    'onLeftClicked: hub.requestLayoutRemoval("group")',
    'onLeftClicked: hub.confirmLayoutRemoval()',
    'onLeftClicked: hub.cancelPendingRemoval()',
    'visible: hub.pendingRemoval !== null',
    'visible: hub.pendingRemoval === null',
    'destructive: true',
    'onEditModeChanged: if (!editMode) {',
    'cancelPendingRemoval();',
    'closeModulePicker();',
):
    assert token in window, f"Hub staged deletion contract missing: {token}"
assert 'confirmed !== true || next.modes.length <= 1' in layout
assert 'groups.length <= 1 || !validIndex(subIndex, groups.length)' in layout
assert 'next.modes[modeIndex].id !== expectedModeId' in layout
assert 'groups[subIndex].id !== expectedGroupId' in layout
assert window.count('label: "CONFIRM"') == 1
assert window.count('label: "CANCEL"') == 1
assert window.count('onLeftClicked: hub.confirmLayoutRemoval()') == 1
assert window.count('onLeftClicked: hub.cancelPendingRemoval()') == 1

assert 'Layout.removeTile(layout, selectedModeIndex,' in window
assert 'function undoLastLayoutEdit()' in window
assert 'onLeftClicked: hub.undoLastLayoutEdit()' in window
assert 'property var layoutUndoStack: []' in window
assert 'layoutStorageIssue.length > 0' in window
assert 'Layout.storageIssue(ApolloHubStore.layoutJson)' in window
assert 'height: 140 * (tileConfig.rowSpan || 1)' in window
assert 'APOLLO HUB  //  LIVE MODULES CONNECTED' in window
# Stage 4 picker must search the ten HUB module IDs (not desktop apps),
# show all on empty search, keep keyboard typing isolated and require explicit
# nonduplicate targeted selection. SWAP must not cycle behind the user's back.
for token in (
    'function moduleChoices(layout, modeIndex, subIndex, tileIndex, rawQuery)',
    'function setTileModule(layout, modeIndex, subIndex, tileIndex,',
    'matchCount: items.length',
    'availableCount: availableCount',
    'selected: selected',
    'inUse: !selected && !available',
    'tiles[tileIndex].id !== expectedTileId',
    'tile.module === moduleId',
):
    assert token in layout, f"Missing module-picker policy contract: {token}"
for token in (
    'property bool modulePickerOpen: false',
    'property string modulePickerQuery: ""',
    'property real modulePickerAnchorX: 12',
    'property real modulePickerAnchorY: 12',
    'readonly property var modulePickerChoices: Layout.moduleChoices(',
    'function openModulePicker(index, sourceItem)',
    'function closeModulePicker()',
    'function chooseModuleFromPicker(moduleId)',
    'sourceItem.mapToItem(',
    'modulePickerOverlay, 0, sourceItem.height + 3',
    'modulePickerAnchorX = Math.max(10, Math.min(',
    'modulePickerAnchorY = below.y + modulePickerPopup.height',
    'modulePickerInput.forceActiveFocus()',
    'modulePickerInput.text = ""',
    'id: modulePickerOverlay',
    'anchors.fill: parent',
    'z: 200',
    'id: modulePickerPopup',
    'x: hub.modulePickerAnchorX',
    'y: hub.modulePickerAnchorY',
    'id: modulePickerInput',
    'onTextChanged: hub.modulePickerQuery = text',
    'SEARCH MODULE / ID',
    'hub.modulePickerChoices.matchCount + " / "',
    'id: modulePickerResults',
    'model: hub.modulePickerChoices.items',
    'onLeftClicked: hub.chooseModuleFromPicker(modelData.id)',
    'onChangeModule: hub.openModulePicker(index, sourceItem)',
    'onLeftClicked: hub.closeModulePicker()',
    'available: modelData.available',
    'selected: modelData.selected',
    '&& !modulePickerOpen',
    'contentHeight: tileFlow.height',
    'clip: true',
    'event.key === Qt.Key_Escape',
    'enabled: hub.menuOpen && (hub.modulePickerOpen || hub.transferPickerOpen)',
    'hub.closeModulePicker();',
    'hub.closeTransferPicker();',
    'hub.modulePickerChoices.availableCount === 1',
    'activeTiles[modulePickerTileIndex].id !== modulePickerTileId',
    'activeMode.id !== modulePickerModeId',
    'activeSubMode.id !== modulePickerGroupId',
    'id: tileRepeater',
    'tileRepeater.itemAt(selectedTileIndex)',
    'visible: hub.modulePickerOpen',
    'onTapped: {',
    'hub.closeModulePicker();',
    'hub.closeTransferPicker();',
    'TapHandler {',
    'id: modulePickerRail',
    'accountForContentOrigin: true',
    'handleStyle: "star"',
):
    assert token in window, f"Missing Hub dropdown contract: {token}"
assert 'modulePickerOpen = true' in window
assert 'modulePickerOpen = false' in window
assert window.count('onChangeModule: hub.openModulePicker(index, sourceItem)') == 1
assert 'signal changeModule(int index, var sourceItem)' in tile
assert 'readonly property Item swapAnchor: swapAction' in tile
assert 'onLeftClicked: tile.changeModule(tile.tileIndex, swapAction)' in tile
assert 'visible: !hub.modulePickerOpen' not in window
assert 'id: modulePicker\\n' not in window
assert 'tileScroll.contentY = 0' not in window
# The dropdown must mount after the grid's clipped Flickable, not inside it.
assert window.index('id: tileScroll') < window.index('id: modulePickerOverlay')
assert window.index('id: modulePickerPopup') > window.index('id: modulePickerOverlay')
assert 'width: 368' in window
assert 'height: 342' in window
assert 'interactive: contentHeight > height' in window

assert 'TimePolicy.snapshot(tile.now.getTime(), tile.use24Hour)' in tile
assert "Qt.formatDate(tile.now" not in tile

# Stage 5: MOVE is a separate destination dropdown, not SWAP or a
# destructive delete. Both policy and UI preserve identities and bounds.
for token in (
    'function moveTargets(layout, fromMode, fromGroup, fromIndex)',
    'function transferTile(layout, fromMode, fromGroup, fromIndex, expectedTileId,',
    'validIndex(fromIndex,source.tiles.length)',
    'source.tiles[fromIndex].id !== expectedTileId',
    'sourceMode.id !== expectedModeId',
    'destinationMode.id !== expectedDestinationModeId',
    'destination.id !== expectedDestinationGroupId',
    'destination.tiles.length >= MAX_TILES',
    'tile.module === source.tiles[fromIndex].module',
    'source.tiles.splice(fromIndex,1)[0]',
    'destination.tiles.push(moved)',
    'reason:full ? "FULL" : duplicate ? "IN USE" : ""',
):
    assert token in layout, f"Missing cross-group MOVE policy: {token}"
for token in (
    'property bool transferPickerOpen: false',
    'readonly property var transferTargets: Layout.moveTargets(',
    'function openTransferPicker(index, sourceItem)',
    'function closeTransferPicker()',
    'function chooseTransferDestination(modeId, groupId)',
    'activeTiles[transferTileIndex].id !== transferTileId',
    'activeMode.id !== transferModeId',
    'activeSubMode.id !== transferGroupId',
    'Layout.transferTile(',
    'save(moved);',
    'selectedModeIndex = target.modeIndex;',
    'selectedSubModeIndex = target.groupIndex;',
    'selectedTileIndex = Math.max(0, activeTiles.length - 1);',
    'onTransferTile: hub.openTransferPicker(index, sourceItem)',
    'id: transferPickerDropdownContent',
    'id: transferPickerResults',
    'model: hub.transferTargets.items',
    'modelData.label',
    'modelData.reason.length > 0',
    'onLeftClicked: hub.chooseTransferDestination(',
    'id: transferPickerRail',
    'visible: hub.modulePickerOpen || hub.transferPickerOpen',
    'hub.transferTargets.availableCount',
    'z: 200',
):
    assert token in window, f"Missing MOVE dropdown/interaction: {token}"
assert 'signal transferTile(int index, var sourceItem)' in tile
assert 'onLeftClicked: tile.transferTile(tile.tileIndex, moveAction)' in tile
assert tile.index('label: "SWAP"') < tile.index('label: "MOVE"') < tile.index('label: "W:"') < tile.index('label: "H:"') < tile.index('label: "×"')
assert window.count('onTransferTile: hub.openTransferPicker(index, sourceItem)') == 1
assert 'modulePickerOverlay.width - modulePickerPopup.width - 10' in window
assert window.count('closeTransferPicker();') >= 5

# P1 Stage 6: only view coordinates change, not saved tile sequence.
# The original Flow made every short neighbor inherit its tallest row's height.
for token in (
    'function packTiles(tiles)',
    'MAX_TILES*MAX_ROW_SPAN',
    'for (var row=0;row<MAX_TILES*MAX_ROW_SPAN && !placed;row++)',
    'columnSpan:width',
    'rowSpan:tile.rowSpan',
    'state:"ready", columns:2, rows:highestRow',
):
    assert token in layout, f"Gap-filling grid policy missing: {token}"
for token in (
    'readonly property var tileGrid: Layout.packTiles(activeTiles)',
    'Item {\n                    id: tileFlow',
    'property int spacing: 8',
    'height: hub.tileGrid.rows > 0',
    'hub.tileGrid.rows * 140',
    '(hub.tileGrid.rows - 1) * spacing',
    'readonly property var gridCell: hub.tileGrid.items[index]',
    'x: gridCell ? gridCell.column',
    'y: gridCell ? gridCell.row * (140 + tileFlow.spacing) : 0',
    'height: 140 * (tileConfig.rowSpan || 1)',
    'contentHeight: tileFlow.height',
    'onTransferTile: hub.openTransferPicker(index, sourceItem)',
):
    assert token in window, f"Gap-filling QML geometry missing: {token}"
assert 'Flow {\n                    id: tileFlow' not in window
# Grid output must remain derived data: never serialize positions into layout.
assert 'gridCell.column' not in layout
assert 'tileGrid' not in (ROOT / "services/hub/ApolloHubStore.qml").read_text(encoding="utf-8")

# Standard window-local key grammar, without inventing a bottom rail.
for key in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right",
            "Left", "Right", "Up", "Down", "Enter", "Return", "Esc"):
    assert 'sequence: "' + key + '"' in window, key
assert 'sequence: "Ctrl+Left"' not in window
assert 'sequence: "Ctrl+Right"' not in window
assert "function cycleMainMode(direction)" in window
assert "function cycleTopSubMode(direction)" in window
assert "function moveNavigationCursor(direction)" in window
assert "Layout.navigationTarget(tileGrid, selectedTileIndex," in window
assert "const card = tileRepeater.itemAt(next);" in window
assert "tileScroll.contentHeight - tileScroll.height" in window
assert "tileScroll.contentY = Math.min(maxScroll, Math.max(0, card.y - margin));" in window
assert "tileScroll.contentY = Math.min(maxScroll," in window
assert "card.height + 2 * margin > tileScroll.height" in window
assert "Math.min(maxScroll, Math.max(0, card.y - margin))" in window
assert "selectedTileIndex + delta" not in window
for direction in ("left", "right", "up", "down"):
    assert window.count('hub.moveNavigationCursor("' + direction + '")') == 2
for token in (
    'function navigationTarget(grid, selectedIndex, direction)',
    'source.column+source.columnSpan',
    'source.row+source.rowSpan',
    'cx0+candidate.columnSpan',
    'cy0+candidate.rowSpan',
    'if (primary<0)',
):
    assert token in layout, f"Missing pure spatial navigation helper: {token}"
assert "function activateNavigationCursor()" in window
assert "Keys.onShortcutOverride" in window
assert "Keys.onPressed" in window
assert "modeNameInput.activeFocus" in window
assert "context: Qt.WindowShortcut" in window
assert "WlrKeyboardFocus.OnDemand" in window
assert "WlrKeyboardFocus.Exclusive" not in window
assert "property bool keyboardSelected" in tile
assert "onPointerEntered: hub.selectedTileIndex = index" in window
assert "if (!editMode || selectedTileIndex < 0" in window


# Only save configuration, not user secrets or duplicated system services.
assert '"/apollo-hub-layout.json"' in store
assert "JsonAdapter {" in store
assert "onAdapterUpdated: writeAdapter()" in store
assert "singleton ApolloHubStore" in module
assert "ApolloHubStore.layoutJson = JSON.stringify(layout);" in window
assert "DATA ADAPTER NOT CONNECTED" in tile

# W1 UI: consume the shared shell's existing bridge through reactive QML
# bindings, never a copied snapshot or another WeatherService. Independent
# weather/AQI states must be visible even without a shell attachment.
assert "property var liveBridge: null" in window
assert "weatherSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.weatherSnapshot : null" in window
assert "property var weatherSnapshot: null" in tile
assert 'weatherState === "ready"' in tile
assert "weatherSnapshot.fresh === true" in tile
assert 'weatherState === "ready" && !weatherReady' in tile
assert "tile.weatherStatus" in tile
assert 'tile.moduleId === "weather"' in tile
assert "tile.weatherSnapshot.temperatureF" in tile
assert "tile.weatherSnapshot.condition" in tile
assert "tile.weatherSnapshot.humidity" in tile
assert "tile.weatherSnapshot.windMph" in tile
assert "tile.airQualityText" in tile
assert "airQuality.fresh === true" in tile
assert "airQuality.index" in tile
assert 'return "DISCONNECTED";' in tile
assert 'String(airQuality.state || "unavailable").toUpperCase()' in tile
assert 'tile.weatherSnapshot.ageMinutes' in tile
for forbidden in ("WeatherService {", "ApolloHubLiveBridge {", "SystemTelemetry {"):
    assert forbidden not in window + tile, forbidden
assert "SystemTelemetry {" not in window
assert "HeadlessMediaController {" not in window

# W3 Network UI: use the existing B3 passive bridge, not an additional
# NetworkManager/polling instance. The visible status must say LOCAL LINK
# and explicitly UNVERIFIED INTERNET; unknown signal/speed stays "--".
assert "networkSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.networkSnapshot : null" in window
assert "property var networkSnapshot: null" in tile
for needle in (
    'networkState === "connected"',
    "networkSnapshot.connected === true",
    'networkTransport === "ethernet"',
    'networkTransport === "wifi"',
    'networkState === "disconnected"',
    'networkState === "unavailable"',
    "networkWifi.networkName",
    "networkWifi.interfaceName",
    "networkEthernet.interfaceName",
    "networkWifi.signalPercent",
    "value >= 0 && value <= 100",
    'return "--";',
    "networkSnapshot.linkSpeedMbps",
    '"WI-FI LINK  " + tile.wifiLinkText',
    '"ETHERNET   " + tile.ethernetLinkText',
    '"INTERNET   UNVERIFIED"',
    '"LOCAL LINK CONNECTED"',
    '" // INTERNET UNVERIFIED"',
):
    assert needle in tile, f"B3 Network mini-tile missing {needle}"
assert 'visible: tile.moduleId === "network"' in tile
assert 'tile.moduleId !== "weather" && tile.moduleId !== "network"' in tile
for forbidden in ("Network {", "Networking {", "Process {", "nmcli", "iw dev",
                  "ethtool", "checkConnectivity(", "Networking.devices"):
    assert forbidden not in window + tile, f"UI must not collect/control network: {forbidden}"

# B4 UI projects the existing mediaSnapshot without creating controllers,
# choosing a MPRIS player, polling MPD, or claiming audio output.
assert "mediaSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.mediaSnapshot : null" in window
assert "property var mediaSnapshot: null" in tile
assert "ApolloHubMediaMini {" in tile
assert "mediaSnapshot: tile.mediaSnapshot" in tile
assert 'visible: tile.moduleId === "media"' in tile
assert 'tile.moduleId !== "media"' in tile
assert "MEDIA // READ ONLY // AUDIO OUTPUT NOT VERIFIED" in tile
for phrase in (
    "mediaSnapshot.mpd", "mediaSnapshot.mpris",
    'mpdState === "playing"', 'mpdState === "paused"',
    'mpdState === "stopped"', 'mpdState === "unloaded"',
    "mpd.fresh === true", "mpd.lastKnownLoadedTitle",
    'mprisState === "selection-required"',
    'mprisState === "player-missing"',
    'mprisState === "playing"', 'mprisState === "paused"',
    'mprisState === "stopped"',
    "mpris.selected === true", "mpris.title", "mpris.artist",
    "NO TRACK LOADED", "LAST LOADED", "SELECT PLAYER IN HI-FI",
    "NO SELECTED PLAYER",
):
    assert phrase in media_mini, f"Missing B4 MPD/MPRIS UI distinction: {phrase}"
for forbidden in (
    "HeadlessMediaController {", "MprisPlaybackAdapter {",
    "Mpris {", "Process {", "playerctld",
    "playPause(", "play(", "pause(", "next(", "previous(",
    "selectedMprisBusName =", "startPolling(", "polling:",
):
    assert forbidden not in media_mini + tile + window, (
        f"Hub UI must not own/poll/control players: {forbidden}")

# The existing Time/Calendar tile has a clock Timer; only the Media view
# must remain free of observers/timers.
assert "Timer {" not in media_mini

# B2 CPU++ UI is a passive consumer of the existing normalized snapshot.
# The shared shell controls on-demand refresh; no new collection loop or
# device action is permitted in this presentation.
assert "systemSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.systemSnapshot : null" in window
assert "property var systemSnapshot: null" in tile
assert "ApolloHubSystemMini {" in tile
assert 'visible: tile.moduleId === "cpu"' in tile
assert "systemSnapshot: tile.systemSnapshot" in tile
assert 'tile.moduleId !== "cpu"' in tile
assert "systemMini.statusLine" in tile
for needle in (
    "property var systemSnapshot: null",
    'systemState === "ready"',
    "systemSnapshot.fresh === true",
    "typeof value !== \"number\"",
    "!isFinite(value)",
    "value < 0 || value > 100",
    "return -1;",
    "sample.cpuPercent",
    "sample.memoryPercent",
    "sample.swapPercent",
    "sample.rootFilesystemPercent",
    "displaySample.cpuPercent",
    "displaySample.memoryPercent",
    "displaySample.swapPercent",
    "displaySample.rootFilesystemPercent",
    'labelText: "CPU"',
    'labelText: "RAM"',
    'labelText: "SWAP"',
    'labelText: "ROOT FS"',
    "percentValue >= 0",
    'String(gauge.percentValue) + "%"',
    '"--"',
    'statusLine:',
    'systemState.toUpperCase().replace(/-/g, " ")',
    "systemSnapshot.ageMinutes",
):
    assert needle in system_mini, f"B2 CPU++ mini missing {needle}"
# W2 follow-up: one shared grid, common gauge baselines, no flashing to
# empty during short telemetry refreshes. A cached observation is eligible
# only while LOADING and only within the existing five-minute freshness limit.
assert "Grid {" in system_mini
assert "columns: systemMini.densityLevel === 3 && width < 500 ? 1 : 2" in system_mini
assert "rowSpacing: 9" in system_mini
assert "columnSpacing: 12" in system_mini
assert ": systemMini.densityLevel === 2 ? 29 : 19" in system_mini
assert ": systemMini.densityLevel === 2 ? 9 : 5" in system_mini
assert "height: gauge.prominent ? 19 : 18" not in system_mini
assert "height: gauge.prominent ? 5 : 4" not in system_mini
assert 'property var lastReadySample: null' in system_mini
assert "onSystemSnapshotChanged:" in system_mini
assert 'sample.state === "ready" && sample.fresh === true' in system_mini
assert "lastReadySample.observedAtMs === stamp" in system_mini
assert 'sample.state !== "loading"' in system_mini
assert 'systemState === "loading" && lastReadySample !== null' in system_mini
assert "Date.now() - lastReadySample.observedAtMs <= 300000" in system_mini
assert 'systemReady ? systemSnapshot' in system_mini
assert 'holdingPrevious ? lastReadySample : null' in system_mini
assert '"CPU++ // REFRESHING // LAST OBSERVATION"' in system_mini

for forbidden in (
    "SystemTelemetry {", "HeadlessMediaController {",
    "Process {", "Timer {", "refresh(", "systemRows",
    "FanControl {", "IpcHandler {",
):
    assert forbidden not in system_mini, f"CPU++ UI collecting/controlling: {forbidden}"
assert "SystemTelemetry {" not in window + tile

# B5 Linux uptime: the mini tile consumes one pre-normalized snapshot.
# Never instantiate another procfs reader or claim zero uptime when source is
# unobserved, unavailable, stale, malformed, or in error.
assert "uptimeSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.uptimeSnapshot : null" in window
assert "property var uptimeSnapshot: null" in tile
assert "ApolloHubUptimeMini {" in tile
assert 'visible: tile.moduleId === "uptime"' in tile
assert "uptimeSnapshot: tile.uptimeSnapshot" in tile
assert 'tile.moduleId !== "uptime"' in tile
assert "uptimeMini.statusLine" in tile
for needle in (
    "property var uptimeSnapshot: null",
    'uptimeState === "ready"',
    "uptimeSnapshot.ready === true",
    "validPart(uptimeSnapshot.days)",
    "validPart(uptimeSnapshot.hours)",
    "validPart(uptimeSnapshot.minutes)",
    'typeof value === "number"',
    "isFinite(value)",
    "value >= 0",
    'return uptimeReady ? String(value) : "--";',
    "uptimeMini.uptimeSnapshot.days",
    "uptimeMini.uptimeSnapshot.hours",
    "uptimeMini.uptimeSnapshot.minutes",
    'unitText: "DAYS"',
    'unitText: "HOURS"',
    'unitText: "MIN"',
    '"LINUX // SINCE BOOT"',
    '"UPTIME // READY // APPROX"',
    'uptimeState === "ready" ? "UPTIME // UNAVAILABLE"',
    'uptimeState.toUpperCase().replace(/-/g, " ")',
    "Grid {",
    "columns: 3",
):
    assert needle in uptime_mini, f"B5 uptime mini missing {needle}"
# The existing Time/Calendar tile legitimately owns a one-second clock.
# Only the new Uptime mini-component must have no timer or file reader.
for forbidden in (
    "FileView {", "Process {", "Timer {", "SystemTelemetry {",
    "/proc/uptime", "uptimeFile", "reload(", "exec(", "readFile(",
):
    assert forbidden not in uptime_mini, (
        f"Uptime mini must not read, poll, or collect: {forbidden}")
for forbidden in ("FileView {", "Process {", "/proc/uptime"):
    assert forbidden not in window + tile, (
        f"Uptime Hub UI must not add a procfs reader: {forbidden}")

# B6 Apps UI: the native index remains read-only. A direct left tap
# launches one exact-ID installed DesktopEntry. Opening/scrolling the Hub
# never starts applications or creates a second launcher/catalog process.
assert "appsSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.appsSnapshot : null" in window
assert "property var appsSnapshot: null" in tile
assert "ApolloHubAppsMini {" in tile
assert 'visible: tile.moduleId === "apps"' in tile
assert "appsSnapshot: tile.appsSnapshot" in tile
assert 'tile.moduleId !== "apps"' in tile
assert "appsMini.statusLine" in tile
for phrase in (
    "property var appsSnapshot: null",
    'catalogState === "ready"',
    'catalogState === "empty"',
    'catalogState === "unavailable"',
    "appsSnapshot.installedCount",
    "appsSnapshot.matchCount",
    "appsSnapshot.truncated",
    "appsSnapshot.items",
    "entries.length",
    "GridView {",
    "model: appsMini.entries",
    "appEntry.modelData.name",
    "appEntry.modelData.icon",
    "Quickshell.iconPath(",
    "GridView.FlowLeftToRight",
    'boundsBehavior: Flickable.StopAtBounds',
    'text: appsMini.catalogReady ? "NO MATCHES"',
    '"NO APPLICATIONS"',
    '"CATALOG UNAVAILABLE"',
    "CLICK TO LAUNCH",
    "TapHandler {",
    "acceptedButtons: Qt.LeftButton",
    "onTapped: appsMini.launchApp(appEntry.modelData)",
    "function launchApp(item)",
    "DesktopEntries.byId(id)",
    'target.id !== id',
    'target.noDisplay === true',
    'typeof target.execute !== "function"',
    "target.execute();",
    'launchFeedback = "LAUNCH REQUESTED"',
    'launchFeedback = "LAUNCH FAILED"',
    "entries.some(function(candidate)",
):
    assert phrase in apps_mini, f"B6 explicit app-launch UI missing {phrase}"
# Only the Apps row's direct left tap may trigger the existing desktop-entry
# launch method. No launch from render, model updates, search, or Hub opens.
assert apps_mini.count("target.execute();") == 1
assert apps_mini.count("DesktopEntries.byId(") == 1
assert apps_mini.count("onTapped:") == 1
for forbidden in (
    "DesktopEntries {", "DesktopEntries.applications",
    "DesktopEntries.heuristicLookup(", "execDetached(", "Process {",
    "Timer {", "FileView {", "scanDesktopFiles(", "app.launch(",
    "onCompleted:", "onVisibleChanged:", "onAppsSnapshotChanged:",
    "onDoubleClicked:", "MouseArea {",
):
    assert forbidden not in apps_mini, (
        f"Apps mini may only launch on user tap, never poll/auto-start: {forbidden}")
for forbidden in ("DesktopEntries.byId(", "execDetached(", "app.launch("):
    assert forbidden not in window + tile, (
        f"Hub window/tile must not own app launch: {forbidden}")

# To-do compact header: RELOAD directly above ADD/SAVE, exactly the
# same width and right edge; the task input remains level with ADD.
assert 'id: controlStack' in todo_mini
assert 'id: editorArea' in todo_mini
assert todo_mini.index('id: reloadButton') < todo_mini.index('id: submitButton')
assert todo_mini.count('width: parent.width') >= 2
assert todo_mini.count('anchors.right: controlStack.left') == 2
assert 'id: countRow' in todo_mini
assert 'top: editorArea.bottom' in todo_mini
assert 'top: countRow.bottom' not in todo_mini

# B7 To-do: one existing singleton and explicit operator-initiated
# mutations, never a second store, separate process, or file write in UI.
assert "import qs.services.hub" in window
assert "todoStore: ApolloHubTodoStore" in window
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in window
assert "property bool todoInputFocused: false" in window
assert "&& !todoInputFocused" in window
assert "onTodoTextFocusChanged: function(focused)" in window
assert "property var todoStore: null" in tile
assert "property var todoSnapshot: null" in tile
assert "signal todoTextFocusChanged(bool focused)" in tile
assert "ApolloHubTodoMini {" in tile
assert 'visible: tile.moduleId === "todo"' in tile
assert "todoStore: tile.todoStore" in tile
assert "todoSnapshot: tile.todoSnapshot" in tile
assert 'tile.moduleId !== "todo"' in tile
assert "todoMini.statusLine" in tile

for phrase in (
    "property var todoStore: null",
    "property var todoSnapshot: null",
    "signal textFocusChanged(bool focused)",
    'storeState === "ready" || storeState === "empty"',
    "todoSnapshot.writable === true",
    "storeState === \"saving\"",
    '"TO-DO // SAVING // NOT YET CONFIRMED"',
    "WRITES LOCKED",
    "onTodoSnapshotChanged:",
    'pendingWriteKind === "add"',
    'pendingWriteKind === "rename"',
    'pendingWriteKind === "remove"',
    "if (storeState === \"ready\" || storeState === \"empty\")",
    'storeState === "error" || storeState === "unsupported"',
    "todoStore.addTask(value)",
    "todoStore.renameTask(target, value)",
    "todoStore.setTaskDone(task.id, task.done !== true)",
    "todoStore.removeTask(task.id, true)",
    "confirmDeleteId !== task.id",
    "confirmDeleteId = String(task.id)",
    "todoStore.reloadFromDisk()",
    'todoMini.storeState !== "saving"',
    "MAXIMUM_LENGTH_PLACEHOLDER",
    "onActiveFocusChanged: todoMini.textFocusChanged(activeFocus)",
    "onTextFocusChanged: function(focused)",
    'label: todoEntry.awaitingDelete ? "YES" : "DEL"',
    'label: todoEntry.awaitingDelete ? "NO" : "EDIT"',
):
    if phrase == "MAXIMUM_LENGTH_PLACEHOLDER":
        phrase = "maximumLength: 160"
    assert phrase in (todo_mini + tile), f"B7 To-do UI missing {phrase}"
for forbidden in (
    "ApolloHubTodoStore {", "FileView {", "Process {", "Timer {",
    "JsonAdapter {", "Quickshell.dataDir", "atomicWrites:",
    "Qt.openUrlExternally(", "execDetached(", "setTimeout(",
):
    assert forbidden not in todo_mini, f"To-do UI must not own storage/processes: {forbidden}"
# No direct arbitrary writes or automatic save from lifecycle handlers.
assert "removeTask(task.id, true)" in todo_mini
assert "removeTask(task.id, false)" not in todo_mini
assert "function confirmDelete(task)" in todo_mini
assert "function requestDelete(task)" in todo_mini
assert "onCompleted: todoStore" not in todo_mini
assert "onVisibleChanged:" in todo_mini
assert "onSaved:" in todo_store and "atomicWrites: true" in todo_store

# B8 Notes mini: separate user-private singleton, revision-safe detached
# editor, explicit Save, and two-step revision-guarded delete. No autosave,
# second FileView, filesystem writes, or background processing in the UI.
assert "notesStore: ApolloHubNotesStore" in window
assert "notesSnapshot: ApolloHubNotesStore.snapshot" in window
assert "property bool notesInputFocused: false" in window
assert "&& !notesInputFocused" in window
assert "onNotesTextFocusChanged: function(focused)" in window
assert "property var notesStore: null" in tile
assert "property var notesSnapshot: null" in tile
assert "signal notesTextFocusChanged(bool focused)" in tile
assert "ApolloHubNotesMini {" in tile
assert 'visible: tile.moduleId === "notes"' in tile
assert "notesStore: tile.notesStore" in tile
assert "notesSnapshot: tile.notesSnapshot" in tile
assert 'tile.moduleId !== "notes"' in tile
assert "notesMini.statusLine" in tile
for phrase in (
    "property var notesStore: null", "property var notesSnapshot: null",
    "signal textFocusChanged(bool focused)",
    "onTypingChanged: textFocusChanged(typing)",
    "notesSnapshot.writable === true",
    '"loading"', '"saving"', '"error"', '"unsupported"',
    "NOT YET CONFIRMED", "WRITES LOCKED", "DRAFT RETAINED",
    "property int openedRevision: 0",
    "property string openedTitle:", "property string openedBody:",
    "notesStore.getNote(item.id)", "openedRevision = detail.revision",
    "openedTitle = detail.title", "openedBody = detail.body",
    "titleInput.text = detail.title", "bodyInput.text = detail.body",
    "notesStore.createNote(title, body)",
    "notesStore.saveNote(openedId, openedRevision, title, body)",
    "notesStore.deleteNote(openedId, openedRevision, true)",
    "notesStore.reloadFromDisk()",
    "if (!deleteArmed)", "deleteArmed = true",
    'label: notesMini.deleteArmed ? "YES" : "DEL"',
    "label: \"NO\"", "saveDraft()", "deleteNote()",
    "if (storeState === \"ready\" || storeState === \"empty\")",
    "onNotesSnapshotChanged:", 'pendingAction = "";',
    "if (!started)", "feedback = \"SAVE REJECTED // CHECK REVISION\"",
    "if (draftDirty && !discardArmed)", "discardArmed = true",
    'label: notesMini.discardArmed ? "DISCARD" : "BACK"',
    "maximumLength: 120", "bodyInput.text.length <= 8192",
    "textFormat: TextEdit.PlainText", "textFormat: Text.PlainText",
    "notesMini.entries", "model: notesMini.entries",
    "noteRow.modelData.preview", "noteRow.modelData.title",
    'id: titleInput', 'id: bodyInput', 'id: noteList',
):
    assert phrase in notes_mini, f"B8 Notes UI missing {phrase}"
for forbidden in (
    "ApolloHubNotesStore {", "FileView {", "Process {",
    "Timer {", "JsonAdapter {", "Quickshell.dataDir",
    "atomicWrites:", "setText(", "execDetached(",
    "onTextChanged:", "onTitleChanged:", "onBodyChanged:",
    "Component.onCompleted:", "onSaved:", "createNote()",
):
    assert forbidden not in notes_mini, (
        f"Notes UI must not own persistence or autosave: {forbidden}")
assert "singleton ApolloHubNotesStore 1.0 ApolloHubNotesStore.qml" in module
assert "atomicWrites: true" in notes_store
assert "watchChanges: false" in notes_store
assert 'storageState="saving"' in notes_store
assert "onSaved:" in notes_store and "onSaveFailed:" in notes_store

# B9 Calendar mini: month geometry is owned by the pure policy and
# refreshed through the existing shared bridge clock, never a second timer.
assert "calendarSnapshot: hub.liveBridge" in window
assert "hub.liveBridge.calendarSnapshot : null" in window
assert "calendarBridge: hub.liveBridge" in window
assert "property var calendarSnapshot: null" in tile
assert "property var calendarBridge: null" in tile
assert "ApolloHubCalendarMini {" in tile
assert 'visible: tile.moduleId === "calendar"' in tile
assert "calendarSnapshot: tile.calendarSnapshot" in tile
assert "calendarBridge: tile.calendarBridge" in tile
assert "todoSnapshot: tile.todoSnapshot" in tile
assert 'tile.moduleId !== "calendar"' in tile
assert "calendarMini.statusLine" in tile

for needle in (
    "property var calendarSnapshot: null",
    "property var calendarBridge: null",
    'calendarState === "ready"',
    "Array.isArray(calendarSnapshot.weekdayLabels)",
    "Array.isArray(calendarSnapshot.cells)",
    "calendarSnapshot.weeks >= 4",
    "calendarSnapshot.weeks <= 6",
    "calendarSnapshot.cells.length === calendarSnapshot.weeks * 7",
    "calendarSnapshot.weekdayLabels",
    "calendarSnapshot.cells",
    "calendarSnapshot.monthLabel",
    "Grid {",
    "columns: 7",
    "model: calendarMini.weekdayLabels",
    "model: calendarMini.monthCells",
    "modelData.isToday === true",
    "modelData.inMonth === true",
    "calendarSnapshot.weeks - 1",
    'label: "TODAY"',
    'label: calendarMini.weekStart === 0 ? "SUN" : "MON"',
    "function moveMonth(direction)",
    "function showToday()",
    "function toggleWeekStart()",
    "calendarBridge.calendarMonthOffset = next",
    "calendarBridge.calendarMonthOffset = 0",
    "calendarBridge.calendarWeekStartsOn = weekStart === 0 ? 1 : 0",
    "if (next < -120 || next > 120)",
    'onLeftClicked: calendarMini.moveMonth(-1)',
    'onLeftClicked: calendarMini.moveMonth(1)',
    'onLeftClicked: calendarMini.showToday()',
    'onLeftClicked: calendarMini.toggleWeekStart()',
    "EVENTS NOT CONNECTED",
    '"CALENDAR UNAVAILABLE"',
):
    assert needle in calendar_mini, f"B9 UI missing {needle}"

for forbidden in (
    "Timer {", "SystemClock {", "Process {", "FileView {",
    "Qt.formatDate(", "new Date(", "Date.now(", "CalendarPolicy.snapshot(",
    "Qt.openUrlExternally(", "eventCount === 0", "NO EVENTS",
    "NO APPOINTMENTS", "EventService {", "onCalendarSnapshotChanged:",
):
    assert forbidden not in calendar_mini, (
        f"B9 UI must not duplicate calendar state or invent events: {forbidden}")
assert "function snapshot(" in calendar_policy
assert 'eventsState:"not-connected"' in calendar_policy
assert "eventCount:-1" in calendar_policy

# B10 Time UI uses the original, single 1000ms tile.now timer.
# Formatting is pure; 12/24 changes are presentation-only and in-memory.
assert 'import "../../services/hub/ApolloHubTimePolicy.js" as TimePolicy' in tile
assert "property date now: new Date()" in tile
assert tile.count("Timer {") == 1
assert 'interval: 1000' in tile
assert 'onTriggered: tile.now = new Date()' in tile
assert 'running: tile.visible && (tile.moduleId === "time" || tile.moduleId === "calendar")' in tile
assert 'property bool use24Hour: true' in tile
assert 'TimePolicy.snapshot(tile.now.getTime(), tile.use24Hour)' in tile
assert "ApolloHubTimeMini {" in tile
assert 'visible: tile.moduleId === "time"' in tile
assert "timeSnapshot: tile.timeSnapshot" in tile
assert "use24Hour: tile.use24Hour" in tile
assert "onToggleHourFormat: tile.use24Hour = !tile.use24Hour" in tile
assert 'tile.moduleId !== "time"' in tile
assert "timeMini.statusLine" in tile
assert "Qt.formatTime(" not in tile

for needle in (
    "property var timeSnapshot: null",
    "property bool use24Hour: true",
    "signal toggleHourFormat()",
    'timeSnapshot.state === "ready"',
    "timeSnapshot.displayTime",
    "timeSnapshot.dateLabel",
    "timeSnapshot.utcOffsetLabel",
    'label: timeMini.use24Hour ? "24H" : "12H"',
    "onLeftClicked: timeMini.toggleHourFormat()",
    '"--:--:--"', '"LOCAL DATE UNAVAILABLE"',
    '"UTC OFFSET UNKNOWN"', '"TIME // UNAVAILABLE"',
    '"TIME // LOCAL CLOCK // "',
):
    assert needle in time_mini, f"B10 Time mini missing {needle}"

for forbidden in (
    "Timer {", "SystemClock {", "Process {", "FileView {",
    "Date.now(", "new Date(", "setTime(", "Qt.formatTime(",
    "ApolloHubStore", "TimeW", "Qt.openUrlExternally(",
):
    assert forbidden not in time_mini, (
        f"B10 mini must not create clock, mutate time, or persist preferences: {forbidden}")
assert "function snapshot(epochMs, use24Hour)" in time_policy
assert 'utcOffsetLabel: offsetLabel' in time_policy
assert 'displayTime: use24Hour ? time24 : time12' in time_policy

# P1 Stage 7B: Time expands presentation ONLY when the allocated tile
# chassis is taller. H:1 retains original compact type/spacing and position.
# Layout sizing is owned by the tile; the mini cannot start another clock.
for token in (
    'readonly property int densityLevel: height >= 300 ? 3',
    ': height >= 180 ? 2 : 1',
    'id: timeContent',
    'height: childrenRect.height',
    'y: timeMini.densityLevel > 1',
    '(timeMini.height - height) / 2',
    'height: timeMini.densityLevel === 3 ? 58',
    'font.pixelSize: timeMini.densityLevel === 3',
    '(timeMini.use24Hour ? 42 : 34)',
    '(timeMini.use24Hour ? 32 : 28)',
    '(timeMini.use24Hour ? 23 : 20)',
    'horizontalAlignment: timeMini.densityLevel > 1',
    'width: timeMini.densityLevel > 1 ? 54 : 44',
    'label: timeMini.use24Hour ? "24H" : "12H"',
    'onLeftClicked: timeMini.toggleHourFormat()',
    'timeMini.timeSnapshot.displayTime',
    'timeMini.timeSnapshot.dateLabel',
    'timeMini.timeSnapshot.utcOffsetLabel',
):
    assert token in time_mini, f"Stage 7B Time presentation missing {token}"
assert "anchors.fill: parent" not in time_mini
assert "Timer {" not in time_mini
assert tile.count("Timer {") == 1
assert "ApolloHubTimeMini {" in tile

# Stage 7C: Calendar gains responsive typography only. The existing
# bridge, event-not-connected state and explicit month/week actions remain.
for token in (
    'readonly property int densityLevel: height >= 300 ? 3',
    ': height >= 180 ? 2 : 1',
    'spacing: calendarMini.densityLevel === 3 ? 7',
    'height: calendarMini.densityLevel === 3 ? 32',
    'font.pixelSize: calendarMini.densityLevel === 3 ? 17',
    'height: calendarMini.densityLevel === 3 ? 21',
    'font.pixelSize: calendarMini.densityLevel === 3 ? 14',
    ': calendarMini.densityLevel === 2 ? 12 : 9',
    ': calendarMini.densityLevel === 2 ? 13',
    'calendarMini.calendarSnapshot.weeks === 6 ? 9 : 10',
    'calendarBridge.calendarMonthOffset = next;',
    'calendarBridge.calendarWeekStartsOn = weekStart === 0 ? 1 : 0;',
):
    assert token in calendar_mini, f"Calendar H:2/H:3 contract missing: {token}"
assert 'Timer {' not in calendar_mini
assert 'FileView {' not in calendar_mini
assert 'ApolloHubCalendarMini {' in tile


# Stage 7D: CPU++ and Uptime grow into allocated H:2/H:3 space while
# H:1 stays compact. No new data source, writer, service or timer.
for mini in (system_mini, uptime_mini):
    assert 'readonly property int densityLevel: height >= 300 ? 3' in mini
    assert ': height >= 180 ? 2 : 1' in mini
    assert 'height: childrenRect.height' in mini
    for forbidden in ('Timer {', 'Process {', 'FileView {',
                      'SystemTelemetry {', 'Qt.openUrlExternally('):
        assert forbidden not in mini, f"Stage 7D unsafe mini source: {forbidden}"
for token in (
    'height: labelHeight + spacing + trackHeight',
    'height: gauge.labelHeight',
    'height: gauge.trackHeight',
    'systemMini.densityLevel === 3 ? 40',
    'systemMini.densityLevel === 3 ? 13',
    '(gauge.prominent ? 14 : 12)',
    'y: systemMini.densityLevel > 1',
    'width < 500 ? 1 : 2',
    'metrics.columnSpacing * (metrics.columns - 1)',
):
    assert token in system_mini, f"Stage 7D CPU++ layout missing {token}"
for token in (
    'id: uptimeContent',
    'y: uptimeMini.densityLevel > 1',
    'height: digitHeight + spacing + unitHeight',
    'height: part.digitHeight',
    'height: part.unitHeight',
    ': uptimeMini.densityLevel === 2 ? 54 : 31',
    ': uptimeMini.densityLevel === 2 ? 18 : 13',
    ': uptimeMini.densityLevel === 2 ? 39 : 23',
    ': uptimeMini.densityLevel === 2 ? 13 : 10',
    'columns: 3',
):
    assert token in uptime_mini, f"Stage 7D Uptime layout missing {token}"


# Level 2 Hub Calendar agenda reuses TASKS policy and the single
# TodoStore snapshot. It is not an event feed or another task writer.
for needle in (
    'import "../tasks/TaskPlannerPolicy.js" as Planner',
    'property var todoSnapshot: null',
    'property string selectedView: "month"',
    'property string selectedTaskDate: ""',
    'Planner.view(',
    'todoSnapshot, taskMonthKey, taskFocusDateKey, taskTodayKey',
    'densityLevel >= 2 && (selectedView === "agenda"',
    'id: viewSelector',
    'visible: calendarMini.densityLevel >= 2',
    'model: ["MONTH", "WEEK", "DAY", "AGENDA"]',
    'label: modelData',
    'modelData === "MONTH"',
    'calendarMini.calendarReady && calendarMini.taskView.available',
    'function selectTaskDate(dateKey)',
    'selectedTaskDate = dateKey;',
    'TapHandler {',
    'onTapped: calendarMini.selectTaskDate(dayCell.modelData.date)',
    'calendarMini.remainingTasksOn(',
    'id: agendaPane',
    'model: calendarMini.agendaEntries',
    '"TASKS // LOCAL DUE DATES // READ ONLY"',
    '"NO TASKS DUE ON SELECTED DATE"',
    'parent.modelData.done',
):
    assert needle in calendar_mini, f"Level 2 agenda missing {needle}"
for forbidden in (
    'ApolloHubTodoStore {', 'FileView {', 'Process {',
    'Timer {', 'Date.now(', 'new Date(', 'Qt.openUrlExternally(',
    'addTask(', 'removeTask(', 'updateTask(', 'setDone(',
):
    assert forbidden not in calendar_mini, (
        f"Level 2 agenda cannot collect or write: {forbidden}")

# Stage 8B: WEEK/DAY are view-only extensions to the existing TASKS
# source projection, using its pure day/week arithmetic and existing data.
for needle in (
    'Planner.weekDays(todoSnapshot, taskFocusDateKey, taskTodayKey)',
    'model: ["MONTH", "WEEK", "DAY", "AGENDA"]',
    'function stepTaskDate(direction)',
    'Planner.moveDay(taskFocusDateKey, step)',
    'selectedView === "week" ? direction * 7 : direction',
    'const delta = (to.year - from.year) * 12',
    'newOffset < -120 || newOffset > 120',
    'calendarBridge.calendarMonthOffset = newOffset;',
    'id: dateNavigation',
    'id: weekStrip',
    'model: calendarMini.weekEntries',
    'weekDay.modelData.remaining',
    'onTapped: calendarMini.selectedTaskDate = weekDay.modelData.date',
    'calendarMini.selectedView === "day" ? 47 : 29',
    'parent.modelData.priority',
    'parent.modelData.projectId',
    'dateNavigation.visible',
    '? dateNavigation.height + 6 : 0',
    'weekStrip.visible ? weekStrip.height + 6 : 0',
):
    assert needle in calendar_mini, f"Stage 8B navigation missing {needle}"
for forbidden in ('Timer {', 'FileView {', 'Process {', 'new Date(',
                  'Date.now(', 'addTask(', 'reschedule(', 'setDone('):
    assert forbidden not in calendar_mini, f"Stage 8B unowned action: {forbidden}"


# Stage 8C: H:1 is the original weather card; H:2/H:3 expose
# four truthful read-only domains through the one injected bridge.
for needle in (
    'visible: tile.moduleId === "weather" && tile.tileRowSpan === 1',
    'ApolloHubWeatherExplore {',
    'visible: tile.moduleId === "weather" && tile.tileRowSpan > 1',
    'weatherSnapshot: tile.weatherSnapshot',
    'weatherExplore.statusLine',
):
    assert needle in tile, f"Stage 8C mount missing {needle}"
for needle in (
    'property var weatherSnapshot: null',
    'property string selectedDomain: "weather"',
    'model: ["WEATHER", "GROUND", "SKY", "SPACE"]',
    'onLeftClicked: weatherExplore.selectedDomain = modelData.toLowerCase()',
    'weatherSnapshot.fresh === true',
    'airQuality.fresh === true',
    'typeof airQuality.index === "number"',
    'weatherSnapshot.uvIndex >= 0',
    'weatherSnapshot.temperatureF',
    'weatherSnapshot.feelsLikeF',
    'weatherSnapshot.windMph',
    'weatherSnapshot.windDirection',
    'weatherSnapshot.humidity',
    'SPACE // PROVIDER NOT CONNECTED',
    'POLLEN / SEISMIC // NOT CONNECTED',
    'NOAA SOLAR // NOT CONNECTED',
    'AURORA / FLARES // NOT CONNECTED',
):
    assert needle in weather_explore, f"Stage 8C data missing {needle}"
for forbidden in (
    'WeatherService {', 'SpaceService {', 'SeismicService {',
    'AuroraService {', 'SolarFlareService {', 'XrayFluxService {',
    'SwpcAlertService {', 'FileView {', 'Process {', 'Timer {',
    'SystemTelemetry {', 'Qt.openUrlExternally(',
    'request(', 'fetch(', 'refresh(', 'startPolling(',
):
    assert forbidden not in weather_explore, (
        f"Stage 8C cannot collect or control: {forbidden}")


# Stage 8D: read-only Network explorer, existing one bridge snapshot.
for token in (
    'visible: tile.moduleId === "network" && tile.tileRowSpan === 1',
    'ApolloHubNetworkExplore {',
    'visible: tile.moduleId === "network" && tile.tileRowSpan > 1',
    'networkSnapshot: tile.networkSnapshot',
    'networkExplore.statusLine',
):
    assert token in tile, f"Stage 8D mount missing {token}"
for token in (
    'property var networkSnapshot: null',
    'property string selectedView: "status"',
    'model: ["STATUS", "WI-FI", "ETHERNET"]',
    'onLeftClicked: networkExplore.selectedView =',
    'networkSnapshot.connected === true',
    'networkState === "connected"',
    'wifi.present === true',
    'ethernet.present === true',
    'wifi.signalPercent',
    'typeof value === "number"',
    'isFinite(value)',
    'value >= 0 && value <= 100',
    'networkSnapshot.linkSpeedApproximate !== true',
    'networkSnapshot.linkSpeedMbps',
    'transport !== "wifi"',
    '"WIRED SPEED // NOT OBSERVED"',
    'INTERNET // UNVERIFIED',
    'LOCAL LINK CONNECTED',
    'NOT PRESENT',
    'UNAVAILABLE',
):
    assert token in network_explore, f"Stage 8D data missing {token}"
for forbidden in (
    'NetworkManager {', 'Networking.devices', 'Process {',
    'FileView {', 'Timer {', 'nmcli', 'ethtool', 'iw dev',
    'checkConnectivity(', 'activateConnection(', 'setNetworkingEnabled(',
    'Qt.openUrlExternally(', 'request(', 'fetch(', 'refresh(', 'startPolling(',
):
    assert forbidden not in network_explore, (
        f"Stage 8D network view must not probe/control: {forbidden}")


# Stage 8E: taller Media views share the same MPD/MPRIS snapshots and
# reuse the existing mini for BOTH. UI cannot create/own media services.
for needle in (
    'visible: tile.moduleId === "media" && tile.tileRowSpan === 1',
    'ApolloHubMediaExplore {',
    'visible: tile.moduleId === "media" && tile.tileRowSpan > 1',
    'mediaSnapshot: tile.mediaSnapshot',
    'mediaExplore.statusLine',
):
    assert needle in tile, f"Stage 8E tile seam missing {needle}"
for needle in (
    'property var mediaSnapshot: null',
    'property string selectedView: "both"',
    'model: ["BOTH", "MPD", "MPRIS"]',
    'onLeftClicked: mediaExplore.selectedView = modelData.toLowerCase()',
    'ApolloHubMediaMini {',
    'mediaSnapshot: mediaExplore.mediaSnapshot',
    'mediaExplore.selectedView === "both"',
    'mpd.fresh === true',
    'mpdState === "playing"',
    'mpdState === "unloaded"',
    'mpd.observationSource',
    'mpd.ageSeconds',
    'LAST KNOWN LOADED',
    'mpris.selected === true',
    'mprisState === "selection-required"',
    'mprisState === "player-missing"',
    'mpris.album',
    'MPRIS PLAYERS',
    'NO AUTOMATIC SELECTION',
    'AUDIO OUTPUT NOT VERIFIED',
):
    assert needle in media_explore, f"Stage 8E Media missing {needle}"
for forbidden in (
    'HeadlessMediaController {', 'MprisPlaybackAdapter {',
    'Mpris {', 'Process {', 'FileView {', 'Timer {',
    'playPause(', 'play(', 'pause(', 'next(', 'previous(',
    'selectedMprisBusName =', 'startPolling(', 'polling:',
    'Qt.openUrlExternally(', 'execute(', 'run(',
):
    assert forbidden not in media_explore, (
        f"Stage 8E Hub Media must not control playback: {forbidden}")


# Stage 8F: app taps in taller tiles inspect metadata, never launch.
for token in (
    'visible: tile.moduleId === "apps" && tile.tileRowSpan === 1',
    'ApolloHubAppsExplore {',
    'visible: tile.moduleId === "apps" && tile.tileRowSpan > 1',
    'appsSnapshot: tile.appsSnapshot',
    'appsExplore.statusLine',
):
    assert token in tile, f"Stage 8F tile mounting missing {token}"
for token in (
    'property var appsSnapshot: null',
    'property string selectedView: "catalog"',
    'property string selectedId: ""',
    'model: appsExplore.entries',
    'appsSnapshot.truncated === true',
    'appsSnapshot.matchCount',
    'Array.isArray(appsSnapshot.items)',
    'function inspectEntry(item)',
    'entries.some(function(entry)',
    'entry.id === id',
    'selectedId = id;',
    'selectedView = "details";',
    'onTapped: appsExplore.inspectEntry(appRow.modelData)',
    'readonly property var selectedEntry:',
    'entry.id === selectedId',
    'label: "CATALOG"',
    'label: "DETAILS"',
    'available: appsExplore.detailReady',
    'label: "BACK TO CATALOG"',
    'String(appsExplore.selectedEntry.name)',
    'String(appsExplore.selectedEntry.genericName',
    'String(appsExplore.selectedEntry.id)',
    'READ ONLY // NO APP LAUNCHED',
    'FIRST ',
    'Quickshell.iconPath(',
):
    assert token in apps_explore, f"Stage 8F inspector missing {token}"
for forbidden in (
    'DesktopEntries.byId(', 'target.execute(', 'launchApp(',
    'DesktopEntries.applications', 'DesktopEntries {', 'Process {',
    'FileView {', 'Timer {', 'scanDesktopFiles(', 'execDetached(',
    'Qt.openUrlExternally(', 'onCompleted:', 'onVisibleChanged:',
    'onAppsSnapshotChanged:', 'onDoubleClicked:',
):
    assert forbidden not in apps_explore, f"Stage 8F must not activate apps: {forbidden}"
assert apps_explore.count('onTapped:') == 1
assert apps_mini.count('target.execute();') == 1


# Stage 8G uses exactly the same TASKS pane for the real task details.
for token in (
    'visible: tile.moduleId === "todo" && tile.tileRowSpan === 1',
    'ApolloHubTodoExplore {',
    'visible: tile.moduleId === "todo" && tile.tileRowSpan > 1',
    'todoStore: tile.todoStore',
    'todoSnapshot: tile.todoSnapshot',
    'todoExplore.statusLine',
):
    assert token in tile, f"Stage 8G To-do mount missing {token}"
for token in (
    'import "../tasks"',
    'ApolloHubTodoMini {',
    'TaskDetailsPane {',
    'todoStore: todoExplore.todoStore',
    'todoSnapshot: todoExplore.todoSnapshot',
    'signal textFocusChanged(bool focused)',
    'onTextFocusChanged: function(focused)',
    'onTaskSelected: function(taskId)',
    'taskDetails.chooseTask(taskId)',
    'taskDetails.pendingWrite',
    'taskDetails.dirty',
    'onDetailModeChanged: textFocusChanged(detailMode)',
    'label: "LIST"',
    'label: "DETAILS"',
):
    assert token in todo_explore, f"Stage 8G TASKS reuse missing {token}"
for forbidden in ('ApolloHubTodoStore {', 'FileView {', 'Process {',
                  'Timer {', 'JsonAdapter {', 'updateTaskDetails(',
                  'setTaskDone(', 'createProject(', 'saveDetails(',
                  'Qt.openUrlExternally('):
    assert forbidden not in todo_explore, f"Stage 8G double write forbidden: {forbidden}"
for token in (
    'readonly property int densityLevel: height >= 300 ? 3',
    ': height >= 180 ? 2 : 1',
    'height: notesMini.densityLevel === 3 ? 45',
    'height: notesMini.densityLevel === 3 ? 30',
    'height: notesMini.densityLevel === 3 ? 28',
    'font.pixelSize: notesMini.densityLevel === 3 ? 15',
    'notesStore.createNote(title, body)',
    'notesStore.saveNote(openedId, openedRevision, title, body)',
    'notesStore.deleteNote(openedId, openedRevision, true)',
    'if (draftDirty && !discardArmed)',
    'pendingAction = "delete"',
):
    assert token in notes_mini, f"Stage 8G Notes real editor missing {token}"


# Phase 2A: opt-in Social, AppControl owner-opening and no Hi-Fi changes.
for token in ('"media", "apps", "cpu", "network", "social"',
              'network: "NETWORK", social: "SOCIAL"'):
    assert token in layout, f"Social module registration missing {token}"
for token in (
    'appControlAvailable: appControlWindow !== null',
    'socialActionsAvailable: messagingWindow !== null',
    'activeAppIndex: messagingWindow.activeAppIndex',
    'onOpenAppControlRequested:',
    'appControlWindow.menuOpen = true;',
    'onOpenSocialRequested:',
    'messagingWindow.menuOpen = true;',
    'onSocialPlatformRequested: function(index)',
    'messagingWindow.activateApp(index, false);',
):
    assert token in shell, f"Owner action seam missing {token}"
for token in (
    'signal openAppControlRequested()',
    'signal openSocialRequested()',
    'signal socialPlatformRequested(int index)',
    'function requestAppControl()',
    'function requestSocialOpen()',
    'function requestSocialPlatform(index)',
    'Number.isInteger(index)',
    'onOpenAppControlRequested: hub.requestAppControl()',
    'onOpenSocialRequested: hub.requestSocialOpen()',
    'hub.requestSocialPlatform(index);',
):
    assert token in window, f"Hub action boundary missing {token}"
for token in (
    'property var socialSnapshot: null',
    'property bool socialActionsAvailable: false',
    'signal openSocialRequested()',
    'signal socialPlatformRequested(int index)',
    'ApolloHubSocialMini {',
    'socialSnapshot: tile.socialSnapshot',
    'actionsAvailable: tile.socialActionsAvailable',
    'socialMini.statusLine',
    'tile.moduleId !== "social"',
):
    assert token in tile, f"Social tile seam missing {token}"
for token in (
    'model: socialMini.platforms',
    '["SESSIONS", "DISCORD", "TELEGRAM", "X"]',
    'signal openRequested()',
    'signal platformRequested(int index)',
    'available: socialMini.actionsAvailable',
    'onLeftClicked: socialMini.openRequested()',
    'onLeftClicked: socialMini.platformRequested(index)',
    'MODE SELECTION // NOT CONNECTION PROOF',
):
    assert token in social_mini, f"Social controls missing: {token}"
for token in (
    'signal openAppControlRequested()',
    'property bool appControlAvailable: false',
    'label: "RUNNING CONTROLS"',
    'onLeftClicked: appsExplore.selectedView = "running"',
    'label: "BACK TO CATALOG"',
):
    assert token in apps_explore, f"AppControl entry missing {token}"
for forbidden in (
    'SessionAdapter {', 'Process {', 'FileView {', 'Timer {',
    'DesktopEntries.byId(', 'Quickshell.execDetached(',
    'sendMessage(', 'stopProcess(', 'terminate(', 'kill(',
    'transport(', 'HeadlessMediaController {',
):
    assert forbidden not in social_mini + apps_explore, (
        f"Owner backend leak: {forbidden}")
assert 'ApolloHubMediaExplore {' in tile
assert 'mediaSnapshot: tile.mediaSnapshot' in tile


# Phase 2B1: running processes are a bounded, read-only projection of the
# EXISTING AppControl sampler. No second process sampler or direct signals.
for token in (
    'import "services/hub/ApolloHubProcessesPolicy.js" as HubProcessesPolicy',
    'HubProcessesPolicy.snapshot(',
    'appControlWindow.taskRows,',
    'appControlWindow.taskSnapshotLoading,',
    'appControlWindow.taskSnapshotError)',
):
    assert token in shell, f"Owner process snapshot missing {token}"
for token in (
    'property var processSnapshot: null',
    'processSnapshot: hub.processSnapshot',
):
    assert token in window, f"Hub process binding missing {token}"
for token in (
    'property var processSnapshot: null',
    'processSnapshot: tile.processSnapshot',
):
    assert token in tile, f"Process tile binding missing {token}"
for token in (
    'property var processSnapshot: null',
    'readonly property bool runningMode: selectedView === "running"',
    'runningMode ? processExplore.statusLine',
    'label: "RUNNING"',
    'ApolloHubProcessesExplore {',
    'processSnapshot: appsExplore.processSnapshot',
    'visible: !appsExplore.detailMode && !appsExplore.runningMode',
):
    assert token in apps_explore, f"Apps RUNNING view missing {token}"
for token in (
    'property int selectedPid: -1',
    'property string selectedName: ""',
    'readonly property var selectedEntry:',
    'item.pid === selectedPid',
    'item.startTicks === selectedStartTicks',
    'function inspect(item)',
    'model: processExplore.entries',
    'onLeftClicked: processExplore.inspect(runningRow.modelData)',
    'label: "FREEZE"',
    'label: "RESUME"',
    'label: "END"',
    'label: "RESTART"',
    'label: "APPLY MEMORY LIMIT"',
    'processActionGate.prepare(',
    'processActionGate.confirm()',
    'processActionGate.cancel()',
    'NOT GUARANTEED CURRENT',
):
    assert token in process_explore, f"Process UI missing {token}"
for token in (
    'var MAX_ROWS = 24',
    'function snapshot(rows, loading, error)',
    'function processId(value)',
    'function cleanName(value)',
    'total > items.length',
    'state:loading === true ? "refreshing"',
    'source:"appcontrol-process-telemetry"',
):
    assert token in process_policy, f"Process policy missing {token}"
for forbidden in (
    'ProcessTelemetry {', 'ProcessControl {', 'Process {', 'FileView {',
    'Timer {', 'sendSignal(', 'toggleFreeze(', 'requestTerminate(',
    'requestRestart(', 'Quickshell.execDetached(', 'onCompleted:',
):
    assert forbidden not in process_explore + process_policy, (
        f"Hub cannot independently sample/control processes: {forbidden}")
for sensitive in ('args:', 'user:', 'cmdline:', 'environment:', 'commandLine:'):
    assert sensitive not in process_policy, f"Process secret projected: {sensitive}"
assert 'ApolloHubMediaExplore {' in tile


# Phase 2C: all inline process mutations are issued by the AppControl-owner
# gateway only after a fresh process birth check and local Hub confirmation.
owner_blob = (ROOT / "widgets/AppControlW.qml").read_text(encoding="utf-8")
owner_gate = (ROOT / "widgets/appcontrol/AppControlHubActionGate.qml").read_text(encoding="utf-8")
telemetry = (ROOT / "services/system/ProcessTelemetry.qml").read_text(encoding="utf-8")
for token in (
    'AppControlHubActionGate {',
    'property alias hubProcessActionGate: appControlHubGate',
    'ownerRows: appControlWindow.taskRows',
    'safetyOwner: taskSafety',
    'presentationOwner: processPresentationController',
    'controlOwner: processControl',
    'limitsOwner: processLimits',
):
    assert token in owner_blob, f"AppControl owner API missing {token}"
for token in (
    'function exactRow(pid, startTicks, name)',
    'function toggleOneShotUnlock(pid, startTicks, name)',
    'function prepare(pid, startTicks, name, action, percent)',
    'function confirm()',
    'function cancel()',
    'function finishProbe(exitCode)',
    'actual==comm and int(fields[19])==born',
    'safetyOwner.dangerActionUnlocked(row,kind)',
    'controlOwner.sendSignal(req.pid,"-STOP")',
    'controlOwner.sendSignal(req.pid,"-CONT")',
    'controlOwner.sendSignal(req.pid,"-TERM")',
    'controlOwner.restart(req.pid)',
    'presentationOwner.setLimitPercent(req.percent,row)',
    'REQUEST ISSUED // VERIFY OWNER STATE',
):
    assert token in owner_gate, f"Guarded AppControl gateway missing {token}"
for token in (
    'pidToken.indexOf(":")',
    'startTicks: Number.isSafeInteger(startTicks)',
    'stat_pair=$(sed',
):
    assert token in telemetry, f"AppControl birth token missing {token}"
for token in (
    'property var processActionGate: null',
    'processActionGate: hub.processActionGate',
    'processInputFocused = focused',
    '&& !processInputFocused',
):
    assert token in window, f"Hub action/focus link missing {token}"
assert 'processActionGate: appControlWindow' in shell
assert 'appControlWindow.hubProcessActionGate : null' in shell
assert 'processActionGate: tile.processActionGate' in tile
assert 'processActionGate: appsExplore.processActionGate' in apps_explore
assert 'signal inputFocusChanged(bool focused)' in process_explore
assert 'Slider {' in process_explore
assert 'onMoved: processExplore.limitDraft = Math.round(value)' in process_explore
assert 'label: "CONFIRM ACTION"' in process_explore
assert 'label: "CANCEL"' in process_explore
assert '"UNLOCK ONCE // PROTECTED"' in process_explore
assert 'startTicks:Number.isSafeInteger(row.startTicks)' in process_policy
for forbidden in ('controlOwner.sendSignal(', 'ProcessControl {', 'Process {',
                  'Quickshell.execDetached(', 'toggleFreeze('):
    assert forbidden not in process_explore + apps_explore, (
        f"Process mutation must stay in owner gateway: {forbidden}")
assert 'ApolloHubMediaExplore {' in tile

# P2-C startup regression: RUNNING now operates inline and the child
# ApolloHubProcessesExplore intentionally declares NO AppControl-open signal.
# Binding its nonexistent onOpenAppControlRequested aborts the entire QS shell.
assert "onOpenAppControlRequested:" not in apps_explore, (
    "AppsExplore binds an obsolete signal on ApolloHubProcessesExplore; "
    "Qt cannot instantiate the Hub and refuses to load shell.qml")
assert "signal openAppControlRequested()" not in process_explore
assert "onInputFocusChanged: function(focused)" in apps_explore
assert "signal inputFocusChanged(bool focused)" in process_explore

# Launchers and widget backends are unchanged in this first stage.
print("ApolloHubW foundation source contracts passed")
