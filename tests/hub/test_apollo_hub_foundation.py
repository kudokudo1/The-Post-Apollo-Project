#!/usr/bin/env python3
"""Source contracts for the standalone ApolloHubW foundation (no live shell change)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
dock = (ROOT / "modules/ApolloHub.qml").read_text(encoding="utf-8")
window = (ROOT / "widgets/ApolloHubW.qml").read_text(encoding="utf-8")
tile = (ROOT / "widgets/hub/ApolloHubTile.qml").read_text(encoding="utf-8")
media_mini = (ROOT / "widgets/hub/ApolloHubMediaMini.qml").read_text(encoding="utf-8")
system_mini = (ROOT / "widgets/hub/ApolloHubSystemMini.qml").read_text(encoding="utf-8")
uptime_mini = (ROOT / "widgets/hub/ApolloHubUptimeMini.qml").read_text(encoding="utf-8")
apps_mini = (ROOT / "widgets/hub/ApolloHubAppsMini.qml").read_text(encoding="utf-8")
todo_mini = (ROOT / "widgets/hub/ApolloHubTodoMini.qml").read_text(encoding="utf-8")
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
    ("widgets/ApolloHubW.qml", window, 6),
    ("widgets/hub/ApolloHubTile.qml", tile, 3),
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
):
    assert action in window, f"Hub button behavior changed: {action}"
for action in ('label: "←"', 'label: "→"', 'label: "SWAP"'):
    assert action in tile, f"Hub edit-tile action changed: {action}"

shared_action = (ROOT / "components/ActionButton.qml").read_text(encoding="utf-8")
assert "property bool trackLabelGlowLocally: true" in shared_action
assert "contentHost.x + labelText.x" in shared_action
assert "contentHost.y + labelText.y" in shared_action

# Configure modes/sub-modes and exchange module positions independently.
for name in ("defaultLayout", "normalize", "parse", "swapTiles",
             "renameMode", "addMode", "addSubMode", "addTile", "cycleTile"):
    assert "function " + name + "(" in layout
assert 'version: 1' in layout
assert 'Math.min(6, data.modes.length)' in layout
assert 'Math.min(6, inputMode.subModes.length)' in layout
assert 'Math.min(8, inputSub.tiles.length)' in layout
assert "onMoveLeft: hub.shiftTile(" in window
assert "onMoveRight: hub.shiftTile(" in window
assert "Layout.cycleTile(" in window
assert 'TimePolicy.snapshot(tile.now.getTime(), tile.use24Hour)' in tile
assert "Qt.formatDate(tile.now" not in tile

# Standard window-local key grammar, without inventing a bottom rail.
for key in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right",
            "Left", "Right", "Up", "Down", "Enter", "Return", "Esc"):
    assert 'sequence: "' + key + '"' in window, key
assert 'sequence: "Ctrl+Left"' not in window
assert 'sequence: "Ctrl+Right"' not in window
assert "function cycleMainMode(direction)" in window
assert "function cycleTopSubMode(direction)" in window
assert "function moveNavigationCursor(delta)" in window
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
assert "columns: 2" in system_mini
assert "rowSpacing: 9" in system_mini
assert "columnSpacing: 12" in system_mini
assert "height: 19" in system_mini
assert "height: 5" in system_mini
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

# Launchers and widget backends are unchanged in this first stage.
print("ApolloHubW foundation source contracts passed")
