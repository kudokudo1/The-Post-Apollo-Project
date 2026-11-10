"""Read-only source contracts for the first bottom-left Trash launcher.

These tests never invoke Quickshell, GIO or filesystem deletion. Real visual
geometry, glyph rendering, focus and compositor behavior require operator review.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
POWER = (ROOT / "modules" / "Power.qml").read_text(encoding="utf-8")
TRASH = (ROOT / "modules" / "Trash.qml").read_text(encoding="utf-8")
SHELL = (ROOT / "shell.qml").read_text(encoding="utf-8")
DOCK = (ROOT / "components" / "DockButton.qml").read_text(encoding="utf-8")


def number(source, name):
    match = re.search(r"\b" + re.escape(name) + r"\s*:\s*(\d+)", source)
    if match is None:
        raise AssertionError(f"Missing numeric QML property {name}")
    return int(match.group(1))


def section(source, before, after):
    return source.split(before, 1)[1].split(after, 1)[0]


class TrashBottomLeftLauncherTests(unittest.TestCase):
    def test_shell_mounts_one_bottom_left_trash_and_preserves_power(self):
        self.assertEqual(SHELL.count("    Trash {"), 1)
        self.assertEqual(SHELL.count("    Power {}"), 1)
        self.assertLess(SHELL.index("    Trash {"), SHELL.index("    Power {}"))
        self.assertIn("id: trashWindow", SHELL)
        self.assertIn("cameraCleanupQueueCount: cameraWindow.batchPaths.length", SHELL)
        self.assertIn("cameraCleanupBusy: cameraWindow.busy", SHELL)
        self.assertIn("cameraCleanupController: cameraWindow", SHELL)
        self.assertNotIn("onCleanupRequested: function(technique)", SHELL)
        self.assertIn("Tray {}", SHELL)
        self.assertIn("id: leftModules", SHELL)

    def test_mirror_power_real_geometry_not_window_size_guess(self):
        trash_anchor = section(TRASH, "    anchors {", "    margins {")
        power_anchor = section(POWER, "    anchors {", "    margins {")
        self.assertIn("bottom: true", trash_anchor)
        self.assertIn("left: true", trash_anchor)
        self.assertIn("right: false", trash_anchor)
        self.assertIn("bottom: true", power_anchor)
        self.assertIn("right: true", power_anchor)

        trash_margins = section(TRASH, "    margins {", "    implicitWidth:")
        power_margins = section(POWER, "    margins {", "    implicitWidth:")
        trash_button = section(TRASH, "        DockButton {", "            onLeftClicked:")
        power_button = section(POWER, "        DockButton {", "            onHoverEntered:")
        # The panel's geometry changes with its size mode, but the
        # Power-mirrored dock button never changes width, height or gaps.
        self.assertIn("implicitWidth: frameWidth + 30", TRASH)
        self.assertIn("implicitHeight: frameHeight + 90", TRASH)
        self.assertIn("width: trashLauncher.implicitWidth", TRASH)
        self.assertIn("height: trashLauncher.implicitHeight", TRASH)
        for key in ("width", "height"):
            self.assertEqual(number(trash_button, key), number(power_button, key))
        self.assertEqual(number(trash_button, "width"), 50)
        self.assertEqual(number(trash_button, "height"), 50)
        self.assertIn("y: trashArea.height - 60", trash_button)
        self.assertIn("height: trashLauncher.frameHeight", TRASH)
        left_gap = number(trash_margins, "left") + number(trash_button, "x")
        right_gap = (number(power_margins, "right")
                     + number(POWER, "implicitWidth")
                     - number(power_button, "x")
                     - number(power_button, "width"))
        self.assertEqual(left_gap, right_gap)
        self.assertEqual(left_gap, 25)

        # Bottom position follows the larger panel height; never shift dock.
        trash_bottom = number(trash_margins, "bottom") + 60 - 50
        power_bottom = (number(power_margins, "bottom")
                        + number(POWER, "implicitHeight")
                        - number(power_button, "y")
                        - number(power_button, "height"))
        self.assertEqual(trash_bottom, power_bottom)
        self.assertEqual(trash_bottom, 20)

    def test_top_row_glow_strengths_and_independent_color_planes(self):
        self.assertIn("DockButton {", TRASH)
        self.assertIn("readonly property bool hovered:", DOCK)
        self.assertIn("readonly property bool pressed:", DOCK)
        self.assertIn("readonly property bool energized:", DOCK)
        self.assertIn("open: trashLauncher.menuOpen", TRASH)

        # The white glyph stays white while closed/hovered/pressed, then
        # follows the canonical yellow/magenta selected state.
        for field in (
            "normalForegroundColor", "hoverForegroundColor",
            "pressedForegroundColor"
        ):
            self.assertIn(field + ": Colors.white", TRASH)
        self.assertIn("openForegroundColor: Colors.magenta", TRASH)
        self.assertIn("openFillColor: Colors.yellow", TRASH)

        # The sampled glyph glow is a distinct Omnitrix-green layer.
        # The chassis is ordinary green; open overrides both to magenta.
        for field in (
            "normalContentGlowColor", "hoverContentGlowColor",
            "pressedContentGlowColor"
        ):
            self.assertIn(field + ": Colors.omnitrix", TRASH)
        for field in (
            "normalDockGlowColor", "hoverDockGlowColor",
            "pressedDockGlowColor"
        ):
            self.assertIn(field + ": Colors.green", TRASH)
        self.assertIn("openGlowColor: Colors.magenta", TRASH)
        self.assertIn('text: "♻︎"', TRASH)
        self.assertIn("contentGlowSource: trashGlyph", TRASH)
        self.assertIn("color: trashButton.foregroundColor", TRASH)

        # Inherit every numerical glow setting from the same DockButton
        # component used by the top-row AppLauncher/Camera modules.
        trash_button = section(TRASH, "        DockButton {", "            onLeftClicked:")
        for field in (
            "contentGlowIdleOpacity", "contentGlowHoverOpacity",
            "contentGlowPressedOpacity", "contentGlowOpenOpacity",
            "contentGlowIdleRadius", "contentGlowActiveRadius",
            "contentGlowHoverRadius", "contentGlowPressedRadius",
            "contentGlowOpenRadius", "contentGlowIdleSamples",
            "contentGlowActiveSamples", "contentGlowHoverSamples",
            "contentGlowPressedSamples", "contentGlowOpenSamples",
            "softGlowSpread", "softGlowIdleOpacity",
            "softGlowHoverOpacity", "softGlowPressedOpacity",
            "softGlowOpenOpacity", "wideGlowSpread",
            "wideGlowIdleOpacity", "wideGlowHoverOpacity",
            "wideGlowPressedOpacity", "wideGlowOpenOpacity"
        ):
            self.assertRegex(DOCK, r"\b" + field + r"\s*:")
            self.assertNotRegex(trash_button, r"\b" + field + r"\s*:")

    def test_four_size_steps_and_appcontrol_family_glow(self):
        self.assertIn('property string chassisSize: "compact"', TRASH)
        self.assertIn('readonly property var chassisSizes: ["compact", "medium", "large", "full"]', TRASH)
        self.assertIn("function stepChassis(direction)", TRASH)
        self.assertIn('chassisSize === "medium" ? 620', TRASH)
        self.assertIn('chassisSize === "large" ? 900', TRASH)
        self.assertIn('chassisSize === "medium" ? 570', TRASH)
        self.assertIn('chassisSize === "large" ? 730', TRASH)
        self.assertIn("usableWidth - 55", TRASH)
        self.assertIn("usableHeight - 120", TRASH)
        self.assertIn('label: "↓"', TRASH)
        self.assertIn('label: "↑"', TRASH)
        self.assertIn("onLeftClicked: trashLauncher.stepChassis(-1)", TRASH)
        self.assertIn("onLeftClicked: trashLauncher.stepChassis(1)", TRASH)
        self.assertIn("WindowPanelFrame {", TRASH)
        self.assertIn("readonly property bool burnWarning:", TRASH)
        self.assertIn('confirmMode !== "" || pendingAction === "burn"', TRASH)
        self.assertIn('|| pendingAction === "burn-all"', TRASH)
        self.assertIn("borderColor: trashLauncher.burnWarning ? Colors.orange : Colors.green", TRASH)
        self.assertIn("glowColor: trashLauncher.burnWarning ? Colors.red : Colors.green", TRASH)
        self.assertIn("glowVisible: trashLauncher.menuOpen", TRASH)

    def test_square_frame_and_live_indicator_by_size_arrows(self):
        frame = section(TRASH, "    WindowPanelFrame {", "        Keys.onPressed:")
        self.assertIn("radius: 0", frame)
        self.assertIn('id: trashLiveIndicator', TRASH)
        self.assertIn('text: "● " + trashLauncher.liveLabel', TRASH)
        self.assertIn('readonly property string liveLabel:', TRASH)
        self.assertIn('readonly property color liveColor:', TRASH)
        self.assertIn('liveLabel === "LIVE" ? Colors.omnitrix', TRASH)
        self.assertIn('liveLabel === "STALE" ? Colors.red', TRASH)
        self.assertLess(TRASH.index('id: collapseTrashButton'),
                        TRASH.index('id: expandTrashButton'))
        self.assertLess(TRASH.index('id: expandTrashButton'),
                        TRASH.index('id: trashLiveIndicator'))
        self.assertLess(TRASH.index('id: trashLiveIndicator'),
                        TRASH.index('id: closeTrashButton'))
        self.assertIn("border.color: trashLauncher.liveColor", TRASH)

    def test_auto_refresh_on_open_and_bounded_safe_live_poll(self):
        toggle = section(TRASH, "    function toggle() {", "    function run(")
        self.assertIn("if (menuOpen)", toggle)
        self.assertIn("refresh(true);", toggle)
        self.assertIn("function refresh(clearReceipt, passive)", TRASH)
        self.assertIn('passive === true ? "index-live" : "index"', TRASH)
        timer = section(TRASH, "    Timer {", "    Process {")
        self.assertIn("interval: 15000", timer)
        self.assertIn("repeat: true", timer)
        self.assertIn("triggeredOnStart: false", timer)
        self.assertIn("running: trashLauncher.menuOpen", timer)
        self.assertIn("!trashLauncher.busy", timer)
        self.assertIn('trashLauncher.confirmMode === ""', timer)
        # A focused search field must NOT block live updates indefinitely.
        self.assertNotIn("trashSearch.activeFocus", timer)
        self.assertIn("trashLauncher.refresh(false, true)", timer)
        self.assertNotIn('run("burn"', timer)
        self.assertNotIn('run("burn-all"', timer)
        self.assertIn('action === "index" || action === "index-live"', TRASH)
        self.assertIn("const changed = !indexReady || nextRevision !== revision;", TRASH)
        self.assertIn('if (action === "index" || changed)', TRASH)
        self.assertIn("items = Array.isArray(payload.items) ? payload.items : [];", TRASH)
        self.assertIn("indexReady = true;", TRASH)
        self.assertIn('lastError ? "STALE"', TRASH)

    def test_gio_trash_change_events_trigger_read_only_debounced_refresh(self):
        monitor = section(TRASH, "        id: trashChangeMonitor",
                          "    Process {\n        id: trashProcess")
        self.assertIn('command: ["gio", "monitor", "--dir=trash:///"]', monitor)
        self.assertIn("running: trashLauncher.menuOpen", monitor)
        self.assertIn("stdout: SplitParser {", monitor)
        self.assertIn("trashEventDebounce.restart()", monitor)
        debounce = section(TRASH, "        id: trashEventDebounce",
                           "    Process {\n        id: trashChangeMonitor")
        self.assertIn("interval: 450", debounce)
        self.assertIn("repeat: false", debounce)
        self.assertIn('trashLauncher.confirmMode === ""', debounce)
        self.assertIn("!trashLauncher.busy", debounce)
        self.assertIn("trashLauncher.refresh(false, true)", debounce)
        self.assertNotIn('trashLauncher.run("burn"', debounce)
        self.assertNotIn('trashLauncher.run("burn-all"', debounce)
        # Polling still runs if the optional event watcher is unavailable.
        timer = section(TRASH, "        id: trashLiveTimer",
                        "    Timer {\n        id: trashEventDebounce")
        self.assertIn("interval: 15000", timer)
        self.assertIn("running: trashLauncher.menuOpen", timer)
        self.assertNotIn("trashSearch.activeFocus", timer)

    def test_lifecycle_scaffold_shows_boundaries_without_granting_record_deletion(self):
        self.assertIn('property string activeMode: "trash"', TRASH)
        self.assertIn('readonly property var lifecycleModes: ["cleanup", "archive", "trash", "burn"]', TRASH)
        self.assertIn('function setMode(nextMode)', TRASH)
        self.assertIn('lifecycleModes.indexOf(requested) < 0', TRASH)
        self.assertIn('id: trashLifecycleModes', TRASH)
        for label in ("CLEANUP", "ARCHIVE", "TRASH", "BURN"):
            self.assertIn('"' + label + '"', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.setMode(', TRASH)
        self.assertIn('id: lifecyclePreparation', TRASH)
        self.assertIn('visible: trashLauncher.activeMode !== "trash"', TRASH)
        self.assertIn("CameraCleanupView {", TRASH)
        self.assertIn('import "../widgets"', TRASH)
        self.assertIn("id: archiveRecordsView", TRASH)
        self.assertIn("id: archiveEntriesList", TRASH)
        self.assertIn("id: archiveFilterRow", TRASH)
        self.assertIn("Original Weather archives, Hospital and Finance records remain protected.", TRASH)
        self.assertIn('onLeftClicked: trashLauncher.setMode("trash")', TRASH)
        self.assertIn('visible: trashLauncher.activeMode === "trash"', TRASH)
        self.assertIn('activeMode === "trash"', TRASH)
        # New tabs are navigation, not authorization to alter Hospital,
        # Finance, or arbitrary path records.
        self.assertNotIn("hospital-room-report-delete", TRASH)
        self.assertNotIn("remove-worktree", TRASH)
        self.assertNotIn("finance-write-transaction", TRASH)

    def test_archive_is_real_source_owned_read_only_inventory(self):
        self.assertIn('property var archiveRows: []', TRASH)
        self.assertIn('property var archiveSources: []', TRASH)
        self.assertIn('function refreshArchive()', TRASH)
        self.assertIn('function consumeArchive(raw)', TRASH)
        self.assertIn('id: archiveProcess', TRASH)
        self.assertIn('Quickshell.shellPath("scripts/trash/record_index.py")', TRASH)
        self.assertIn('"index", Quickshell.dataDir', TRASH)
        self.assertIn('onStreamFinished: trashLauncher.consumeArchive(this.text)', TRASH)
        self.assertIn('if (trashLauncher.activeMode === "archive")', TRASH)
        self.assertIn('if (activeMode === "archive")', TRASH)
        self.assertIn('id: archiveRecordsView', TRASH)
        self.assertIn('id: archiveSearch', TRASH)
        self.assertIn('id: archiveEntriesList', TRASH)
        self.assertIn('model: trashLauncher.archiveFilteredRows', TRASH)
        for label in ('"EVENTS"', '"DOSSIERS"', '"SCRAPES"'):
            self.assertIn(label, TRASH)
        self.assertIn('SAVE COPY // WEATHER EVENTS OR DEMO SCRAPES.', TRASH)
        self.assertIn('visible: trashLauncher.activeMode === "burn"', TRASH)
        self.assertIn('Original Weather archives, Hospital and Finance records remain protected.', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.burnRecord(', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.trashRecord(', TRASH)

    def test_research_copies_have_distinct_store_and_deletion_scope(self):
        self.assertIn('property var researchRows: []', TRASH)
        self.assertIn('property int researchRevision: 0', TRASH)
        self.assertIn('property bool researchBusy: false', TRASH)
        self.assertIn('id: researchProcess', TRASH)
        self.assertIn('function runResearch(action, args)', TRASH)
        self.assertIn('function refreshResearch()', TRASH)
        self.assertIn('function consumeResearch(raw)', TRASH)
        self.assertIn('function saveDemoCopy(row)', TRASH)
        self.assertIn('function trashResearchCopy(row)', TRASH)
        self.assertIn('function restoreResearchCopy(row)', TRASH)
        self.assertIn('Quickshell.shellPath("scripts/trash/research_records.py")', TRASH)
        self.assertIn('action, Quickshell.dataDir', TRASH)
        self.assertIn('if (trashLauncher.activeMode === "archive")', TRASH)
        self.assertIn('trashLauncher.refreshResearch();', TRASH)
        self.assertIn('onStreamFinished: trashLauncher.consumeResearch(this.text)', TRASH)
        self.assertIn('archiveRows.concat(researchRows)', TRASH)
        self.assertIn('sourceObservedAt', TRASH)
        self.assertIn('label: "BURN COPY"', TRASH)
        self.assertIn('label: "TRASH COPY"', TRASH) if 'label: "TRASH COPY"' in TRASH else self.assertIn('? "RESTORE" : "TRASH COPY"', TRASH)
        self.assertIn('label: "RECORD BIN " + trashLauncher.researchBinRows.length', TRASH)
        self.assertIn('trashLauncher.archiveFilter = "bin";', TRASH)
        self.assertIn('id: researchBurnReview', TRASH)
        self.assertIn('id: researchBurnList', TRASH)
        self.assertIn('model: trashLauncher.researchBinRows', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.runResearch("burn"', TRASH)

    def test_record_copy_burn_keeps_remote_confirmation_and_revision(self):
        self.assertIn('function armResearchBurn(row)', TRASH)
        self.assertIn('function confirmResearchBurn()', TRASH)
        self.assertIn('function clearResearchBurn()', TRASH)
        self.assertIn('researchBurnRevision !== researchRevision', TRASH)
        self.assertIn('!researchBurnPointerRelocated', TRASH)
        self.assertIn('"BURN_SAVED_COPY_CONFIRMED"', TRASH)
        self.assertIn('id: managedResearchBurnConfirm', TRASH)
        self.assertIn('visible: trashLauncher.researchBurnId !== ""', TRASH)
        self.assertIn('id: managedResearchRemoteTarget', TRASH)
        self.assertIn('id: managedResearchArrival', TRASH)
        self.assertIn('trashLauncher.researchBurnPointerRelocated = true;', TRASH)
        self.assertIn('id: confirmManagedResearchBurn', TRASH)
        self.assertIn('id: cancelManagedResearchBurn', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.clearResearchBurn()', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.advanceResearchBurn()', TRASH)
        self.assertIn('SCOPE // ONE TRASH++ MANAGED COPY', TRASH)
        self.assertIn('Original', TRASH) if 'Original' in TRASH else self.assertIn('original demo scrape', TRASH)
        self.assertIn('researchBurnId !== ""', TRASH)
        self.assertIn('clearResearchBurn();', TRASH)

    def test_weather_event_copy_and_red_remove_button(self):
        self.assertIn('function saveWeatherEventCopy(row)', TRASH)
        self.assertIn('runResearch("archive-event"', TRASH)
        self.assertIn('row.sourceEventKey', TRASH)
        self.assertIn('row.sourceLastCapturedAtMs', TRASH)
        self.assertIn('modelData.kind === "EVENT HISTORY"', TRASH)
        self.assertIn('modelData.kind === "SAVED EVENT"', TRASH)
        self.assertIn('trashLauncher.saveWeatherEventCopy(modelData)', TRASH)
        self.assertIn('? Colors.red : Colors.cyan', TRASH)
        self.assertIn('Original Weather events, demo scrape exports', TRASH)

    def test_copy_burn_requires_two_clicks_and_visible_loading(self):
        self.assertIn('function advanceResearchBurn()', TRASH)
        self.assertIn('researchBurnClickArmed = true;', TRASH)
        self.assertIn('!researchBurnClickArmed || !researchBurnLoadComplete', TRASH)
        self.assertIn('researchBurnArmAnimation.restart();', TRASH)
        self.assertIn('id: researchBurnArmAnimation', TRASH)
        self.assertIn('duration: 850', TRASH)
        self.assertIn('id: researchBurnLoadFill', TRASH)
        self.assertIn('height: Math.max(0, parent.height - 4)', TRASH)
        self.assertIn('idleBorderWidth: 2', TRASH)
        self.assertIn('idleBorderColor: Colors.red', TRASH)
        self.assertIn('"CLICK AGAIN // BURN"', TRASH)
        self.assertIn('"CLICK TO ARM"', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.advanceResearchBurn()', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.confirmResearchBurn()', TRASH)

    def test_trash_filters_show_files_and_trashed_managed_copies(self):
        self.assertIn('property string trashViewFilter: "all"', TRASH)
        self.assertIn('readonly property var trashDisplayRows:', TRASH)
        self.assertIn('fileRows.concat(copyRows)', TRASH)
        self.assertIn('model: trashLauncher.trashDisplayRows', TRASH)
        self.assertIn('id: trashSourceFilters', TRASH)
        for key in ('all','files','records','events','research'):
            self.assertIn('{id:"' + key + '", label:', TRASH)
        self.assertIn('trashLauncher.trashViewFilter = "records"', TRASH)
        self.assertIn('modelData.entryType === "record"', TRASH)
        self.assertIn('trashLauncher.restoreResearchCopy(', TRASH)
        self.assertIn('trashLauncher.armResearchBurn(', TRASH)
        self.assertIn('trashLauncher.restoreItem(', TRASH)
        self.assertIn('trashLauncher.armBurn(', TRASH)
        self.assertIn('trashLauncher.trashShowsFiles', TRASH)
        self.assertIn('"BURN COPY" : "BURN"', TRASH)

    def test_managed_burn_all_is_separate_from_system_gio_burn_all(self):
        self.assertIn('function armResearchBurnAll()', TRASH)
        self.assertIn('researchBurnCount !== researchBinCount', TRASH)
        self.assertIn('researchBurnDigest !== researchBinDigest', TRASH)
        self.assertIn('"BURN_ALL_MANAGED_COPIES_CONFIRMED"', TRASH)
        self.assertIn('id: burnAllManagedCopiesButton', TRASH)
        self.assertIn('label: "BURN ALL COPIES"', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.armResearchBurnAll()', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.armBurnAll()', TRASH)
        self.assertIn('researchBurnScope === "all"', TRASH)
        self.assertIn('MANAGED BIN ONLY', TRASH)
        self.assertIn('GIO system Trash', TRASH)
        self.assertIn('researchBurnPointerRelocated', TRASH)
        self.assertIn('researchBurnClickArmed', TRASH)
        self.assertIn('researchBurnLoadComplete', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.runResearch("burn-all"', TRASH)

    def test_burn_all_requires_spatially_separate_modal_and_pointer_relocation(self):
        self.assertIn('property bool burnAllPointerRelocated: false', TRASH)
        self.assertIn('burnAllPointerRelocated = false;', TRASH)
        arm = section(TRASH, '    function armBurnAll() {', '    IpcHandler {')
        self.assertIn('confirmMode = "all";', arm)
        self.assertIn('burnAllPointerRelocated = false;', arm)
        self.assertIn('&& burnAllPointerRelocated', arm)
        self.assertIn('&& activeMode === "trash"', arm)
        self.assertIn('&& confirmRevision === revision', arm)
        self.assertIn('&& confirmCount === total', arm)
        self.assertIn('"BURN_ALL_CONFIRMED"', arm)

        # The list footer can ONLY arm, never submit Burn All.
        self.assertIn('onLeftClicked: trashLauncher.armBurnAll()', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.run("burn-all"', TRASH)
        self.assertIn('id: burnAllConfirmMenu', TRASH)
        self.assertIn('visible: trashLauncher.confirmMode === "all"', TRASH)
        self.assertIn('id: burnAllRemoteTarget', TRASH)
        self.assertIn('id: confirmAllRemoteButton', TRASH)
        self.assertIn('id: cancelAllBurnButton', TRASH)
        self.assertIn('HoverHandler {', TRASH)
        self.assertIn('onHoveredChanged:', TRASH)
        self.assertIn('trashLauncher.burnAllPointerRelocated = true;', TRASH)
        self.assertIn('&& trashLauncher.burnAllPointerRelocated', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.confirmBurn()', TRASH)
        self.assertIn('onLeftClicked: trashLauncher.clearConfirmation()', TRASH)

        # Modal is separate from the inline per-item BURN row and traps
        # clicks that repeat the old lower-right BURN ALL coordinate.
        self.assertIn('visible: trashLauncher.confirmMode === "item"', TRASH)
        self.assertIn('height: trashLauncher.confirmMode === "item" ? 40 : 0', TRASH)
        self.assertIn('anchors.fill: parent', TRASH)
        self.assertIn('acceptedButtons: Qt.LeftButton | Qt.RightButton', TRASH)
        self.assertIn('onClicked: function(mouse) { mouse.accepted = true; }', TRASH)
        self.assertIn('SCOPE // SYSTEM TRASH (INCLUDING OTHER MOUNTS)', TRASH)
        self.assertIn('ITEMS TO DESTROY // ', TRASH)
        self.assertIn('This permanently empties the existing Linux Trash.', TRASH)
        self.assertIn('MOVE YOUR POINTER TO THE SEPARATE CONFIRM BUTTON.', TRASH)

    def test_finance_red_close_button_family_and_no_destructive_shortcut(self):
        self.assertIn('id: closeTrashButton', TRASH)
        self.assertIn('label: "×"', TRASH)
        self.assertIn("accentColor: Colors.red", TRASH)
        self.assertIn("destructive: true", TRASH)
        self.assertIn("idleSoftGlowColor: Colors.red", TRASH)
        self.assertIn("hoverSoftGlowColor: Colors.red", TRASH)
        self.assertIn("idleWideGlowColor: Colors.red", TRASH)
        self.assertIn("hoverWideGlowColor: Colors.red", TRASH)
        self.assertIn("onLeftClicked: trashLauncher.toggle()", TRASH)
        self.assertIn('label: "CONFIRM BURN"', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.run("burn"', TRASH)

    def test_ipc_handler_type_is_imported_before_use(self):
        # IpcHandler is exported by Quickshell.Io, not base Quickshell.
        # Missing this import prevents the entire shell from starting.
        self.assertIn("import Quickshell.Io", TRASH.split("PanelWindow {", 1)[0])
        self.assertIn("IpcHandler {", TRASH)
        self.assertIn("import Quickshell.Io", POWER.split("PanelWindow {", 1)[0])

    def test_open_close_mask_keyboard_and_placeholder_are_safe(self):
        self.assertIn("function toggle()", TRASH)
        self.assertIn("onLeftClicked: trashLauncher.toggle()", TRASH)
        self.assertIn('target: "trash"', TRASH)
        self.assertNotIn("WlrKeyboardFocus.Exclusive", TRASH)
        self.assertIn("WlrKeyboardFocus.OnDemand", TRASH)
        self.assertIn("WlrKeyboardFocus.None", TRASH)
        self.assertIn("focusable: menuOpen", TRASH)
        self.assertNotIn("trashMenu.forceActiveFocus()", TRASH)
        self.assertIn("mask: Region {", TRASH)
        self.assertIn("item: trashButton", TRASH)
        self.assertIn("width: trashMenu.visible ? trashMenu.width : 0", TRASH)
        self.assertIn("height: trashMenu.visible ? trashMenu.height : 0", TRASH)
        self.assertIn("event.key === Qt.Key_Escape", TRASH)
        self.assertIn("trashLauncher.menuOpen = false", TRASH)
        self.assertIn('label: "×"', TRASH)
        self.assertIn('text: "TRASH++ // " + trashLauncher.activeMode.toUpperCase()', TRASH)
        self.assertIn('Quickshell.shellPath("scripts/trash/trash_cli.py")', TRASH)
        self.assertIn('stdout: StdioCollector {', TRASH)
        self.assertIn("function consume(raw)", TRASH)
        self.assertIn("function refresh(clearReceipt, passive)", TRASH)
        self.assertIn("function restoreItem(item)", TRASH)
        self.assertIn("function armBurn(item)", TRASH)
        self.assertIn("function armBurnAll()", TRASH)
        self.assertIn("function confirmBurn()", TRASH)
        self.assertIn('label: "BURN ALL"', TRASH)
        self.assertIn('label: "CONFIRM BURN"', TRASH)
        self.assertIn("run(\"burn\", [\"burn\", confirmUri, confirmOriginal,", TRASH)
        self.assertIn('run("burn-all", ["burn-all", confirmRevision,', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.run("burn"', TRASH)
        self.assertNotIn('onLeftClicked: trashLauncher.run("burn-all"', TRASH)


if __name__ == "__main__":
    unittest.main()
