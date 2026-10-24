import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import "../components"
import "../services/hub/ApolloHubTimePolicy.js" as LocalTimePolicy
import "../services/time/WorldClockPolicy.js" as WorldClockPolicy
import "../services/time/WorldZoneSearch.js" as WorldZoneSearch
import "../services/time/TimeConverterFormat.js" as ConverterFormat
import "../services/time/StopwatchPolicy.js" as StopwatchPolicy
import "../services/time/CountdownPolicy.js" as CountdownPolicy
import "../services/time/MachineTimelinePolicy.js" as MachineTimelinePolicy
import "../services/time/MachineSelectionPolicy.js" as MachineSelectionPolicy
import "../services/time/MachineLayoutDiffPolicy.js" as MachineLayoutDiffPolicy
import "../services/time/MachineRestorePreviewPolicy.js" as MachineRestorePreviewPolicy

// TimeW: standalone temporal window. Manual MACHINE timeline markers are
// session-local; no screenshots or desktop restoration are implemented.
// The clock dock and shell wiring are intentionally separate integration steps.
PanelWindow {
    id: timew

    property bool menuOpen: false
    property bool keyboardActive: true
    property bool relationshipFocusModeActive: false
    property bool relationshipFocused: false

    readonly property bool standardKeysAvailable:
        menuOpen && keyboardActive
        && (!relationshipFocusModeActive || relationshipFocused)

    // Reuse FinanceW's tested chassis geometry until the operator has a live
    // TimeW preview to measure. This remains a design choice, not a new rule.
    readonly property int frameWidth: 432
    readonly property int frameHeight: 768
    readonly property int glowGutter: 12
    // TimeW identity is white. Universal magenta header, cyan dividers and
    // destructive red Close keep their independent semantic roles.
    readonly property color semanticColor: Colors.white

    // Presentation choice is local to TimeW; it does not change the Clock
    // dock or Hub preference. The Hub helper is pure and owns no clock tick.
    property bool use24Hour: true
    readonly property var localTimeSnapshot:
        LocalTimePolicy.snapshot(localClock.date.getTime(), use24Hour)
    // Local clock display identity follows the dock's 24H/12H colors.
    // The window chassis remains white. Meridiem is intentionally visible
    // in both modes as //AM or //PM, even when the hour is in 24H format.
    readonly property color clockReadoutColor:
        use24Hour ? Colors.orange : Colors.cyan
    readonly property string clockReadoutText:
        localTimeSnapshot.state === "ready"
        ? (use24Hour ? localTimeSnapshot.time24
                     : localTimeSnapshot.time12.slice(0, 8))
          + "//" + localTimeSnapshot.meridiem
        : "--:--:--//--"

    // Two CALC views, with MATH split into duration shift vs. interval.
    property string calcView: "convert"
    property string mathView: "elapsed"
    property string differenceEndZone: "UTC"
    property string differenceEndDate: new Date().toISOString().slice(0, 10)
    property string differenceEndTime: new Date().toISOString().slice(11, 16)
    property bool differenceEnd24Hour: true
    readonly property var differenceEndParsedTime:
        ConverterFormat.parseInput(differenceEndTime, differenceEnd24Hour)
    property var differenceResult: null
    property bool differenceBusy: false
    property string differenceSubmittedKey: ""
    readonly property string differenceInputsKey:
        [converterDate,
         converterParsedTime.valid ? converterParsedTime.canonical
                                   : "INVALID:" + converterTime,
         converterSourceZone, differenceEndDate,
         differenceEndParsedTime.valid ? differenceEndParsedTime.canonical
                                       : "INVALID:" + differenceEndTime,
         differenceEndZone].join("|")
    onDifferenceInputsKeyChanged: differenceResult = null

    function setMathView(which) {
        if (which !== "elapsed" && which !== "between")
            return;
        closeConverterDropdowns();
        mathView = which;
    }

    function cycleDifferenceEndZone() {
        const choices = converterZones;
        if (choices.length === 0) return;
        const idx = choices.findIndex(function(zone) {
            return zone.id === differenceEndZone;
        });
        differenceEndZone = choices[(idx + 1) % choices.length].id;
        closeConverterDropdowns();
    }

    function toggleDifferenceEndFormat() {
        const next24 = !differenceEnd24Hour;
        const formatted = ConverterFormat.convertInput(
                              differenceEndTime, differenceEnd24Hour, next24);
        if (!formatted.valid) {
            differenceResult = {status: formatted.error, options: []};
            return;
        }
        differenceEnd24Hour = next24;
        differenceEndTime = formatted.text;
    }

    function runTimeDifference() {
        if (differenceBusy || !menuOpen || selectedMode !== "calc"
                || calcView !== "math" || mathView !== "between")
            return;
        if (!converterZoneAllowed(converterSourceZone)
                || !converterZoneAllowed(differenceEndZone)) {
            differenceResult = {status: "ZONE_UNAVAILABLE", options: []};
            return;
        }
        if (!converterParsedTime.valid || !differenceEndParsedTime.valid) {
            differenceResult = {
                status: "INVALID_INPUT_TIME", options: []
            };
            return;
        }
        differenceResult = null;
        differenceSubmittedKey = differenceInputsKey;
        differenceBusy = true;
        differenceProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeDifference.py"),
            converterSourceZone, converterDate, converterParsedTime.canonical,
            differenceEndZone, differenceEndDate,
            differenceEndParsedTime.canonical
        ]);
    }
    property string mathOperation: "add"
    property string mathDays: "0"
    property string mathHours: "1"
    property string mathMinutes: "0"
    property var mathResult: null
    property bool mathBusy: false
    property string mathSubmittedKey: ""
    readonly property string mathInputsKey:
        [converterDate,
         converterParsedTime.valid ? converterParsedTime.canonical
                                   : "INVALID:" + converterTime,
         converterSourceZone, mathOperation, mathDays,
         mathHours, mathMinutes].join("|")

    onMathInputsKeyChanged: mathResult = null

    function setCalcView(which) {
        if (which !== "convert" && which !== "math")
            return;
        closeConverterDropdowns();
        calcView = which;
    }

    function toggleMathOperation() {
        mathOperation = mathOperation === "add" ? "subtract" : "add";
    }

    function runTimeArithmetic() {
        if (mathBusy || !menuOpen || selectedMode !== "calc"
                || calcView !== "math")
            return;
        if (!converterZoneAllowed(converterSourceZone)) {
            mathResult = {status: "ZONE_UNAVAILABLE", options: []};
            return;
        }
        if (!converterParsedTime.valid) {
            mathResult = {status: converterParsedTime.error, options: []};
            return;
        }
        mathResult = null;
        mathSubmittedKey = mathInputsKey;
        mathBusy = true;
        arithmeticProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeArithmetic.py"),
            converterSourceZone, converterDate,
            converterParsedTime.canonical, mathOperation,
            mathDays, mathHours, mathMinutes
        ]);
    }

    // CALC // Time-zone conversion is deliberately request-driven, not a
    // new background clock. UTC initial values avoid ambiguous local defaults.
    property string converterDate: new Date().toISOString().slice(0, 10)
    property string converterTime: new Date().toISOString().slice(11, 16)
    // Independent format preferences: input controls how a civil time is
    // entered; output only changes presentation of a completed conversion.
    property bool converterInput24Hour: true
    property bool converterOutput24Hour: true
    readonly property color converterInputFormatColor:
        converterInput24Hour ? Colors.orange : Colors.cyan
    readonly property color converterOutputFormatColor:
        converterOutput24Hour ? Colors.orange : Colors.cyan
    readonly property var converterParsedTime:
        ConverterFormat.parseInput(converterTime, converterInput24Hour)

    function toggleConverterInputFormat() {
        const target24 = !converterInput24Hour;
        const converted = ConverterFormat.convertInput(
                              converterTime, converterInput24Hour, target24);
        if (!converted.valid) {
            // Avoid rewriting an invalid, partially typed value, or silently
            // assuming PM for an ambiguous 12H entry.
            converterResult = {status: converted.error, options: []};
            return;
        }
        converterInput24Hour = target24;
        converterTime = converted.text;
        // Same canonical civil instant: retain an existing result.
    }

    function toggleConverterOutputFormat() {
        converterOutput24Hour = !converterOutput24Hour;
        // Repaint existing results; neither input nor backend is touched.
    }
    property string converterSourceZone: "UTC"
    property string converterTargetZone: "America/New_York"
    property bool converterBusy: false
    property var converterResult: null
    // Only one of the independent FROM/TO selector popups may be open.
    property string activeConverterDropdown: ""

    function closeConverterDropdowns() {
        activeConverterDropdown = "";
        converterSourcePicker.dropFocus();
        converterTargetPicker.dropFocus();
        mathZonePicker.dropFocus();
        differenceEndPicker.dropFocus();
        Qt.callLater(restoreKeyboardFocus);
    }

    function openConverterDropdown(which) {
        if (!menuOpen || selectedMode !== "calc")
            return;
        if (which !== "source" && which !== "target"
                && which !== "math" && which !== "difference")
            return;
        // CONVERT has independent FROM/TO selectors; MATH shares FROM's
        // selected zone but has its own popup and keyboard focus.
        if (which === "math" && calcView !== "math")
            return;
        if (which === "difference"
                && (calcView !== "math" || mathView !== "between"))
            return;
        if (which === "source" || which === "target") {
            if (calcView !== "convert") return;
        }
        activeConverterDropdown = which;
        loadWorldZoneCatalog();
    }

    function toggleConverterDropdown(which) {
        if (activeConverterDropdown === which)
            closeConverterDropdowns();
        else
            openConverterDropdown(which);
    }

    function chooseConverterSearchZone(which, zoneId) {
        // Search text is never passed to subprocesses. Selected IDs must
        // belong to the trusted catalog from timedatectl.
        if (!WorldZoneSearch.contains(worldZoneCatalog, zoneId))
            return;
        if (which === "source" || which === "math")
            converterSourceZone = zoneId;
        else if (which === "target")
            converterTargetZone = zoneId;
        else if (which === "difference")
            differenceEndZone = zoneId;
        else
            return;
        converterResult = null;
        closeConverterDropdowns();
    }
    property string converterSubmittedKey: ""
    readonly property string converterInputsKey:
        [converterDate, converterParsedTime.valid
                        ? converterParsedTime.canonical : "INVALID:" + converterTime,
         converterSourceZone, converterTargetZone].join("|")
    // Keep the four clock shortcuts; add a selected WORLD result, if one exists.
    readonly property var converterZones: worldZones.concat(
        selectedSearchedZone !== ""
        && !worldZones.some(function(z) { return z.id === selectedSearchedZone; })
        ? [{ id: selectedSearchedZone, label: "WORLD" }] : [])

    function cycleConverterZone(which) {
        const choices = converterZones;
        if (choices.length === 0)
            return;
        const current = which === "source"
                        ? converterSourceZone : converterTargetZone;
        let idx = choices.findIndex(function(z) { return z.id === current; });
        idx = (idx + 1) % choices.length;
        if (which === "source")
            converterSourceZone = choices[idx].id;
        else
            converterTargetZone = choices[idx].id;
        converterResult = null;
        closeConverterDropdowns();
    }

    function converterZoneAllowed(zoneId) {
        return converterZones.some(function(z) { return z.id === zoneId; })
               || WorldZoneSearch.contains(worldZoneCatalog, zoneId);
    }

    function runTimeConverter() {
        if (converterBusy || !menuOpen || selectedMode !== "calc")
            return;
        const src = converterSourceZone;
        const dst = converterTargetZone;
        if (!converterZoneAllowed(src) || !converterZoneAllowed(dst)) {
            converterResult = { status: "ZONE_UNAVAILABLE", options: [] };
            return;
        }
        if (!converterParsedTime.valid) {
            converterResult = {status: converterParsedTime.error, options: []};
            return;
        }
        converterResult = null;
        converterSubmittedKey = converterInputsKey;
        converterBusy = true;
        // Fixed executable, fixed repo-owned script path, separate argv.
        // No string shell, arbitrary script path, or clock mutation.
        converterProcess.exec([
            "python3", "-B", "-I",
            Quickshell.shellPath("services/time/TimeZoneConverter.py"),
            src, dst, converterDate, converterParsedTime.canonical
        ]);
    }

    // First world-clock slice. Zone IDs are allowlisted and passed only as
    // child-process environment values, never interpolated into a shell.
    readonly property var worldZones: [
        { id: "UTC", label: "UTC" },
        { id: "America/New_York", label: "NYC" },
        { id: "Europe/London", label: "LON" },
        { id: "Asia/Tokyo", label: "TYO" }
    ]
    // Presets remain available whenever WORLD is off. Selecting WORLD enters
    // directory-search mode and disables the four preset buttons, without
    // deleting their selections. Returning restores the last quick zone.
    property bool worldModeActive: false
    property string selectedQuickZone: "UTC"
    property string selectedSearchedZone: ""
    property string selectedWorldZone: "UTC"
    property string worldSearchQuery: ""
    property bool worldSearchPopupOpen: false
    property var worldZoneCatalog: []
    // Metadata is read once from the host's tzdata; unavailable files leave
    // the original city/zone search intact.
    property var worldCountryNames: ({})
    property string worldCountryZoneTable: ""
    property bool worldCountryLookupStarted: false
    readonly property var worldCountryIndex:
        WorldZoneSearch.parseCountryZones(worldCountryZoneTable, worldCountryNames)
    property bool worldCatalogLoaded: false
    property bool worldCatalogLoading: false
    property bool worldCatalogFailed: false
    readonly property var worldSearchMatches:
        WorldZoneSearch.search(worldZoneCatalog, worldSearchQuery,
                               WorldZoneSearch.MAX_ZONES, worldCountryIndex)
    readonly property bool navigationKeysAvailable:
        standardKeysAvailable && !worldSearchInput.activeFocus
        && !converterSourcePicker.searchFocused
        && !converterTargetPicker.searchFocused
        && !mathZonePicker.searchFocused
        && !differenceEndPicker.searchFocused
        && !differenceEndDateInput.activeFocus
        && !differenceEndTimeInput.activeFocus
        && !countdownNameField.activeFocus
        && !countdownHoursField.activeFocus
        && !countdownMinutesField.activeFocus
        && !countdownSecondsField.activeFocus
        && !machineMarkerInput.activeFocus
        && !converterDateInput.activeFocus && !converterTimeInput.activeFocus
    property string worldLookupZone: ""
    property string worldValidZone: ""
    property string worldRawOffset: ""
    readonly property bool worldClockReady:
        worldValidZone === selectedWorldZone && worldRawOffset !== ""
    readonly property var worldTimeSnapshot:
        WorldClockPolicy.snapshot(localClock.date.getTime(),
                                  worldClockReady ? worldRawOffset : "",
                                  use24Hour)

    function chooseWorldZone(zoneId) {
        if (!worldZones.some(function(zone) { return zone.id === zoneId; }))
            return;
        // Presets are always usable, including when WORLD was selected.
        worldModeActive = false;
        selectedQuickZone = zoneId;
        dismissWorldSearchPopup();
        selectActiveZone(zoneId);
    }

    function selectActiveZone(zoneId) {
        if (selectedWorldZone !== zoneId) {
            selectedWorldZone = zoneId;
            worldValidZone = "";
            worldRawOffset = "";
        }
        if (zoneId !== "")
            refreshWorldClock();
    }

    function loadWorldZoneCatalog() {
        if (!menuOpen || (selectedMode !== "clock" && selectedMode !== "calc")
                || worldCatalogLoaded || worldCatalogLoading)
            return;
        worldCatalogLoading = true;
        worldCatalogFailed = false;
        zoneCatalogLookup.exec(["timedatectl", "list-timezones", "--no-pager"]);
        loadWorldCountryMetadata();
    }

    function loadWorldCountryMetadata() {
        if (worldCountryLookupStarted || !menuOpen
                || (selectedMode !== "clock" && selectedMode !== "calc"))
            return;
        worldCountryLookupStarted = true;
        // Fixed, read-only system files; neither command takes user input.
        isoCountryLookup.exec(["cat", "/usr/share/zoneinfo/iso3166.tab"]);
        zoneCountryLookup.exec(["cat", "/usr/share/zoneinfo/zone.tab"]);
    }

    function dismissWorldSearchPopup() {
        worldSearchPopupOpen = false;
        worldSearchInput.focus = false;
        Qt.callLater(restoreKeyboardFocus);
    }

    function openWorldSearchPopup() {
        if (!worldModeActive) {
            worldModeActive = true;
            selectActiveZone(selectedSearchedZone);
        }
        worldSearchPopupOpen = true;
        loadWorldZoneCatalog();
        Qt.callLater(function() {
            if (timew.menuOpen && timew.selectedMode === "clock")
                worldSearchInput.forceActiveFocus();
        });
    }

    function toggleWorldDropdown() {
        if (worldSearchPopupOpen)
            dismissWorldSearchPopup();
        else
            openWorldSearchPopup();
    }

    function toggleWorldMode() {
        if (worldModeActive) {
            worldModeActive = false;
            dismissWorldSearchPopup();
            selectActiveZone(selectedQuickZone);
        } else {
            openWorldSearchPopup();
        }
    }

    function worldSearchEdited(query) {
        worldSearchQuery = query;
        worldSearchPopupOpen = true;
        if (!worldModeActive) {
            worldModeActive = true;
            selectActiveZone(selectedSearchedZone);
        }
        loadWorldZoneCatalog();
    }

    function selectWorldSearchResult(zoneId) {
        // Never forward an arbitrary typed string to the TZ process.
        if (!WorldZoneSearch.contains(worldZoneCatalog, zoneId))
            return;
        worldModeActive = true;
        selectedSearchedZone = zoneId;
        worldSearchQuery = WorldZoneSearch.label(zoneId);
        dismissWorldSearchPopup();
        selectActiveZone(zoneId);
    }

    function refreshWorldClock() {
        if (!menuOpen || selectedMode !== "clock" || worldLookup.running)
            return;
        worldLookupZone = selectedWorldZone;
        worldLookup.exec({
            command: ["date", "+%z"],
            environment: { TZ: worldLookupZone, LC_ALL: "C" }
        });
    }

    // TOOLS subview selection is local and does not affect the other modes.
    property string toolsView: "stopwatch"

    // COUNTDOWN // up to eight independent, named session-local timers.
    // One monotonic ElapsedTimer supplies timestamps for all records.
    // Their immutable collection survives closing the TimeW surface, but
    // intentionally does not survive restarting Quickshell.
    property var countdownTimers: [CountdownPolicy.createTimer(1)]
    property int countdownNextId: 2
    property int selectedCountdownId: 1
    readonly property var selectedCountdown:
        CountdownPolicy.byId(countdownTimers, selectedCountdownId)
    readonly property int countdownRunningCount:
        CountdownPolicy.runningCount(countdownTimers)

    function countdownNowMs() {
        return countdownAnchor.elapsed() * 1000;
    }

    function refreshCountdowns() {
        countdownTimers = CountdownPolicy.tick(countdownTimers, countdownNowMs());
    }

    function selectCountdown(id) {
        if (!CountdownPolicy.byId(countdownTimers, id))
            return;
        selectedCountdownId = id;
    }

    function createCountdown() {
        if (countdownTimers.length >= CountdownPolicy.MAX_TIMERS)
            return;
        const newTimer = CountdownPolicy.createTimer(countdownNextId);
        if (!newTimer) return;
        countdownTimers = countdownTimers.concat([newTimer]);
        selectedCountdownId = countdownNextId;
        countdownNextId += 1;
    }

    function editCountdown(field, value) {
        const timer = selectedCountdown;
        if (!timer) return;
        if (field === "name") {
            if (typeof value !== "string" || value.length > CountdownPolicy.MAX_NAME_LENGTH)
                return;
        } else {
            if ((field !== "hours" && field !== "minutes" && field !== "seconds")
                    || timer.status !== "ready")
                return;
        }
        const patch = {};
        patch[field] = value;
        patch.error = "";
        countdownTimers = CountdownPolicy.update(countdownTimers, timer.id, patch);
    }

    function startCountdown() {
        const timer = selectedCountdown;
        if (!timer) return;
        countdownTimers = CountdownPolicy.act(
                              countdownTimers, timer.id, "start", countdownNowMs());
    }

    function pauseCountdown() {
        const timer = selectedCountdown;
        if (!timer) return;
        countdownTimers = CountdownPolicy.act(
                              countdownTimers, timer.id, "pause", countdownNowMs());
    }

    function resetCountdown() {
        const timer = selectedCountdown;
        if (!timer) return;
        countdownTimers = CountdownPolicy.act(
                              countdownTimers, timer.id, "reset", countdownNowMs());
    }

    function removeCountdown() {
        if (countdownTimers.length <= 1) return;
        const timer = selectedCountdown;
        if (!timer) return;
        countdownTimers = countdownTimers.filter(function(entry) {
            return entry.id !== timer.id;
        });
        selectedCountdownId = countdownTimers[0].id;
    }

    // TOOLS / STOPWATCH. Monotonic measurement continues while the window
    // is closed; only the visible readout refresh pauses to conserve CPU.
    property bool stopwatchRunning: false
    property bool stopwatchStarted: false
    property real stopwatchAccumulatedMs: 0
    property real stopwatchDisplayMs: 0
    property real stopwatchLastLapMs: 0
    property int stopwatchLapSequence: 0
    property var stopwatchLaps: []
    readonly property int stopwatchMaxLaps: StopwatchPolicy.MAX_LAPS

    function refreshStopwatch() {
        stopwatchDisplayMs = stopwatchRunning
                             ? StopwatchPolicy.sample(
                                   stopwatchAccumulatedMs,
                                   stopwatchAnchor.elapsed() * 1000)
                             : stopwatchAccumulatedMs;
    }

    function startStopwatch() {
        if (stopwatchRunning)
            return;
        stopwatchAnchor.restart();
        stopwatchRunning = true;
        stopwatchStarted = true;
        refreshStopwatch();
    }

    function pauseStopwatch() {
        if (!stopwatchRunning)
            return;
        refreshStopwatch();
        stopwatchAccumulatedMs = stopwatchDisplayMs;
        stopwatchRunning = false;
    }

    function lapStopwatch() {
        if (!stopwatchRunning)
            return;
        refreshStopwatch();
        const newLap = StopwatchPolicy.appendLap(
                           stopwatchLaps, stopwatchDisplayMs,
                           stopwatchLastLapMs, stopwatchLapSequence + 1);
        if (newLap === null)
            return;
        stopwatchLaps = newLap;
        stopwatchLastLapMs = stopwatchDisplayMs;
        stopwatchLapSequence += 1;
    }

    function resetStopwatch() {
        if (stopwatchRunning)
            return;
        stopwatchAccumulatedMs = 0;
        stopwatchDisplayMs = 0;
        stopwatchLastLapMs = 0;
        stopwatchLapSequence = 0;
        stopwatchLaps = [];
        stopwatchStarted = false;
    }

    // MACHINE / TEMPORAL MARKERS. Manual in-memory timestamps only;
    // not a screenshot, session save, Hospital checkpoint or restore point.
    property string machineMarkerDraft: ""
    property var machineMarkers: []
    property int machineMarkerNextId: 1
    readonly property string machineInstanceAge: {
        const refresh = localClock.date;
        return MachineTimelinePolicy.ageLabel(machineLifetimeAnchor.elapsed() * 1000);
    }
    readonly property string machineUtcNow:
        MachineTimelinePolicy.utcStamp(localClock.date.getTime())

    // Capture requires a deliberate click, never menu-open or background polling.
    property bool machineCaptureBusy: false
    property var machineCapturePreview: null
    property string machineCaptureStatus: "NOT CAPTURED"
    property string machineInspectKind: "outputs"
    property int machineInspectIndex: 0
    readonly property var machineInspectItems: machineCapturePreview
        ? (machineCapturePreview[machineInspectKind] || []) : []
    readonly property var machineInspectItem:
        machineInspectIndex >= 0 && machineInspectIndex < machineInspectItems.length
        ? machineInspectItems[machineInspectIndex] : null

    // Exclusion keys are preview-local indexes scoped to each fresh capture.
    // Duplicate app IDs remain individually selectable, without PID/title keys.
    property var machineExcludedItems: ({})
    function machineSelectionKey(kind, index) {
        return kind + ":" + index;
    }
    function machineItemIncluded(kind, index) {
        return machineExcludedItems[machineSelectionKey(kind, index)] !== true;
    }
    function toggleMachineItemSelection() {
        if (!machineCapturePreview || !machineInspectItem)
            return;
        const key = machineSelectionKey(machineInspectKind, machineInspectIndex);
        const next = Object.assign({}, machineExcludedItems);
        if (next[key] === true)
            delete next[key];
        else
            next[key] = true;
        machineExcludedItems = next;
        machineStoreStatus = "SELECTION CHANGED // NOT SAVED";
    }
    function machineIncludedCount(kind) {
        const items = machineCapturePreview ? (machineCapturePreview[kind] || []) : [];
        let count = 0;
        for (let i = 0; i < items.length; i++)
            if (machineItemIncluded(kind, i))
                count++;
        return count;
    }
    function machineSelectionPreview() {
        if (!machineCapturePreview
                || machineSelectionValidation.status !== "ready")
            return null;
        const source = machineCapturePreview;
        return {
            preview_only: true,
            kind: "sway-layout-selection-preview",
            outputs: source.outputs.filter(function(_, i) {
                return timew.machineItemIncluded("outputs", i);
            }),
            workspaces: source.workspaces.filter(function(_, i) {
                return timew.machineItemIncluded("workspaces", i);
            }),
            windows: source.windows.filter(function(_, i) {
                return timew.machineItemIncluded("windows", i);
            })
        };
    }

    // Fail-closed selection review. No dependencies are automatically excluded:
    // the operator decides whether to include a parent or omit its children.
    readonly property var machineSelectionValidation:
        MachineSelectionPolicy.validate(machineCapturePreview, machineExcludedItems)

    function machineLocateSelectionIssue() {
        const issues = machineSelectionValidation.issues;
        if (!issues || issues.length === 0)
            return;
        const first = issues[0];
        if (first.kind !== "outputs"
                && first.kind !== "workspaces" && first.kind !== "windows")
            return;
        machineInspectKind = first.kind;
        machineInspectIndex = first.index;
    }

    function selectMachineInspectKind(kind) {
        if (kind !== "outputs" && kind !== "workspaces" && kind !== "windows")
            return;
        machineInspectKind = kind;
        machineInspectIndex = 0;
    }
    function stepMachineInspect(delta) {
        const count = machineInspectItems.length;
        if (count === 0)
            return;
        machineInspectIndex = (machineInspectIndex + delta + count) % count;
    }

    function requestMachineCapturePreview() {
        if (!menuOpen || selectedMode !== "machine" || machineCaptureBusy)
            return;
        machineCapturePreview = null;
        machineLayoutComparison = null;
        machineRestorePlan = null;
        machineInvalidateResolver();
        machineStoreStatus = "NEW CAPTURE // NOT SAVED";
        machineExcludedItems = ({});
        machineInspectIndex = 0;
        machineCaptureStatus = "READING SWAY";
        machineCaptureBusy = true;
        machineCaptureProcess.exec(["python3", "-B", "-I",
            Quickshell.shellPath("services/time/MachineSwayRead.py")]);
    }

    // The saved database is separate from Hospital and the current desktop.
    // Only SAVE writes; list/load are explicitly requested and read-only.
    property bool machineStoredViewOpen: false
    property bool machineStoreBusy: false
    property string machineStoreAction: ""
    property string machineStorePayload: ""
    property var machineStoreResponse: null
    property string machineStoreStatus: "NOT LOADED"
    property var machineSavedCheckpoints: []
    property int machineSavedIndex: 0
    property var machineOpenedCheckpoint: null
    readonly property var machineSavedItem:
        machineSavedIndex >= 0 && machineSavedIndex < machineSavedCheckpoints.length
        ? machineSavedCheckpoints[machineSavedIndex] : null

    // An explicit, bounded comparison of a saved metadata snapshot against
    // an explicit current capture. No Sway reads, writes, or restore operations.
    property var machineLayoutComparison: null
    property int machineLayoutDifferenceIndex: 0
    readonly property var machineLayoutDifference:
        machineLayoutComparison && machineLayoutDifferenceIndex >= 0
        && machineLayoutDifferenceIndex < machineLayoutComparison.differences.length
        ? machineLayoutComparison.differences[machineLayoutDifferenceIndex] : null
    function machineCompareSavedToCapture() {
        if (machineStoreBusy || machineCaptureBusy || !machineCapturePreview
                || !machineOpenedCheckpoint || !machineSavedItem
                || machineOpenedCheckpoint.checkpoint.id !== machineSavedItem.id)
            return;
        machineRestorePlan = null;
        machineLayoutComparison = MachineLayoutDiffPolicy.compare(
            machineOpenedCheckpoint.document, machineCapturePreview);
        machineLayoutDifferenceIndex = 0;
    }
    function machineStepLayoutDifference(delta) {
        const n = machineLayoutComparison
                  ? machineLayoutComparison.differences.length : 0;
        if (n)
            machineLayoutDifferenceIndex =
                (machineLayoutDifferenceIndex + delta + n) % n;
    }

    // Read-only planning: never infer process identity, never run an action.
    property var machineRestorePlan: null
    property int machineRestorePlanIndex: 0
    readonly property var machineRestorePlanItem:
        machineRestorePlan && machineRestorePlanIndex >= 0
        && machineRestorePlanIndex < machineRestorePlan.items.length
        ? machineRestorePlan.items[machineRestorePlanIndex] : null
    function machinePreviewRestorePlan() {
        if (machineStoreBusy || machineCaptureBusy || !machineCapturePreview
                || !machineOpenedCheckpoint || !machineSavedItem
                || machineOpenedCheckpoint.checkpoint.id !== machineSavedItem.id)
            return;
        machineLayoutComparison = null;
        machineRestorePlan = MachineRestorePreviewPolicy.plan(
            machineOpenedCheckpoint.document, machineCapturePreview);
        machineRestorePlanIndex = 0;
    }
    function machineStepRestorePlanItem(delta) {
        const n = machineRestorePlan ? machineRestorePlan.items.length : 0;
        if (n > 0)
            machineRestorePlanIndex = (machineRestorePlanIndex + delta + n) % n;
    }

    // A fresh, one-shot Sway read resolves possible live window targets.
    // IDs here are ephemeral and never an authorization to perform movement.
    property bool machineResolverBusy: false
    property string machineResolverStatus: "NOT RESOLVED"
    property string machineResolverPayload: ""
    property string machineResolverCheckpointId: ""
    property var machineWindowResolution: null
    property int machineResolverIndex: 0
    readonly property var machineResolverItem:
        machineWindowResolution && machineResolverIndex >= 0
        && machineResolverIndex < machineWindowResolution.candidates.length
        ? machineWindowResolution.candidates[machineResolverIndex] : null
    function machineInvalidateResolver() {
        machineResolverCheckpointId = "";
        machineWindowResolution = null;
        machineResolverIndex = 0;
        machineResolverStatus = "NOT RESOLVED";
    }
    function machineResolveLiveWindows() {
        if (!menuOpen || selectedMode !== "machine"
                || machineResolverBusy || machineStoreBusy || machineCaptureBusy
                || !machineOpenedCheckpoint || !machineSavedItem
                || machineOpenedCheckpoint.checkpoint.id !== machineSavedItem.id)
            return;
        machineResolverCheckpointId = machineSavedItem.id;
        machineResolverPayload = JSON.stringify(machineOpenedCheckpoint.document);
        machineWindowResolution = null;
        machineResolverIndex = 0;
        machineResolverStatus = "RESOLVING LIVE WINDOWS";
        machineResolverBusy = true;
        machineResolverProcess.exec(["python3", "-B", "-I",
            Quickshell.shellPath("services/time/MachineWindowResolver.py")]);
    }
    function machineStepResolverItem(delta) {
        const n = machineWindowResolution ? machineWindowResolution.candidates.length : 0;
        if (n)
            machineResolverIndex = (machineResolverIndex + delta + n) % n;
    }

    function machineStoreRequest(action, data, id) {
        if (!menuOpen || selectedMode !== "machine" || machineStoreBusy)
            return;
        if (action !== "save" && action !== "list" && action !== "load")
            return;
        machineStoreAction = action;
        machineStorePayload = action === "save" ? JSON.stringify(data) : "";
        machineStoreResponse = null;
        machineStoreBusy = true;
        machineStoreStatus = action === "save" ? "SAVING CHECKPOINT"
                           : action === "list" ? "READING STORED"
                           : "OPENING METADATA";
        const argv = ["python3", "-B", "-I",
            Quickshell.shellPath("services/time/MachineCheckpointStore.py"), action];
        if (action === "load")
            argv.push(id);
        machineStoreProcess.exec(argv);
    }

    function machineSaveCheckpoint() {
        if (machineCaptureBusy || machineSelectionValidation.status !== "ready")
            return;
        const chosen = machineSelectionPreview();
        if (!chosen)
            return;
        chosen.schema_version = 1;
        chosen.captured_at_utc = machineCapturePreview.captured_at_utc;
        chosen.label = "MACHINE // " + machineCapturePreview.captured_at_utc.slice(0, 19);
        machineStoreRequest("save", chosen, "");
    }

    function machineShowSavedCheckpoints() {
        machineStoredViewOpen = true;
        machineListCheckpoints();
    }
    function machineListCheckpoints() {
        machineStoreRequest("list", null, "");
    }
    function machineOpenSavedCheckpoint() {
        if (!machineSavedItem)
            return;
        machineOpenedCheckpoint = null;
        machineLayoutComparison = null;
        machineRestorePlan = null;
        machineInvalidateResolver();
        machineStoreRequest("load", null, machineSavedItem.id);
    }
    function machineStepSavedCheckpoint(delta) {
        const n = machineSavedCheckpoints.length;
        if (n > 0)
            machineSavedIndex = (machineSavedIndex + delta + n) % n;
        machineOpenedCheckpoint = null;
        machineLayoutComparison = null;
        machineRestorePlan = null;
        machineInvalidateResolver();
    }
    function machineAcceptStoreResponse(data) {
        if (!data || typeof data.status !== "string") {
            machineStoreStatus = "INVALID STORE RESPONSE";
            return;
        }
        if (data.status === "error") {
            machineStoreStatus = "STORAGE ERROR // " + String(data.reason || "UNKNOWN");
            return;
        }
        if (machineStoreAction === "save" && data.status === "saved"
                && data.checkpoint && typeof data.checkpoint.id === "string") {
            machineSavedCheckpoints = [data.checkpoint].concat(
                machineSavedCheckpoints.filter(function(x) {
                    return x.id !== data.checkpoint.id;
                })).slice(0, 30);
            machineSavedIndex = 0;
            machineOpenedCheckpoint = null;
            machineLayoutComparison = null;
            machineRestorePlan = null;
            machineInvalidateResolver();
            machineStoreStatus = "SAVED // LOCAL SQLITE";
            return;
        }
        if (machineStoreAction === "list" && data.status === "listed"
                && Array.isArray(data.checkpoints)) {
            machineSavedCheckpoints = data.checkpoints.slice(0, 30);
            machineSavedIndex = 0;
            machineOpenedCheckpoint = null;
            machineLayoutComparison = null;
            machineRestorePlan = null;
            machineInvalidateResolver();
            machineStoreStatus = "STORED // " + machineSavedCheckpoints.length;
            return;
        }
        if (machineStoreAction === "load" && data.status === "loaded"
                && data.read_only === true && data.document
                && data.document.preview_only === true) {
            machineOpenedCheckpoint = data;
            machineLayoutComparison = null;
            machineRestorePlan = null;
            machineInvalidateResolver();
            machineStoreStatus = "OPENED // METADATA ONLY";
            return;
        }
        machineStoreStatus = "UNEXPECTED STORE RESPONSE";
    }

    function addMachineMarker() {
        if (!menuOpen || selectedMode !== "machine")
            return;
        const marker = MachineTimelinePolicy.createMarker(
            machineMarkerNextId, machineMarkerDraft,
            localClock.date.getTime(), machineLifetimeAnchor.elapsed() * 1000);
        if (!marker)
            return;
        const next = MachineTimelinePolicy.appendMarker(machineMarkers, marker);
        if (next === null)
            return;
        machineMarkers = next;
        machineMarkerNextId += 1;
        machineMarkerDraft = "";
        machineMarkerInput.focus = false;
        Qt.callLater(restoreKeyboardFocus);
    }

    function removeMachineMarker(id) {
        if (!Number.isInteger(id))
            return;
        machineMarkers = MachineTimelinePolicy.removeMarker(machineMarkers, id);
    }

    readonly property var modes: [
        { id: "clock", name: "CLOCK" },
        { id: "calc", name: "CALC" },
        { id: "tools", name: "TOOLS" },
        { id: "machine", name: "MACHINE" }
    ]
    property int selectedModeIndex: 0
    readonly property string selectedMode: modes[selectedModeIndex].id
    readonly property string selectedName: modes[selectedModeIndex].name

    function toggle() {
        menuOpen = !menuOpen;
    }

    function chooseMode(index) {
        if (index >= 0 && index < modes.length)
            selectedModeIndex = index;
    }

    function cycleMainMode(direction) {
        const length = modes.length;
        const next = (selectedModeIndex + (direction < 0 ? -1 : 1)
                      + length) % length;
        chooseMode(next);
    }

    function restoreKeyboardFocus() {
        if (standardKeysAvailable)
            keyboardAnchor.forceActiveFocus();
    }

    onMenuOpenChanged: {
        if (!menuOpen) {
            dismissWorldSearchPopup();
            closeConverterDropdowns();
        }
        if (menuOpen) {
            Qt.callLater(restoreKeyboardFocus);
            if (selectedMode === "tools") {
                refreshStopwatch();
                refreshCountdowns();
            }
            if (selectedMode === "clock")
                Qt.callLater(refreshWorldClock);
            if (selectedMode === "clock" || selectedMode === "calc")
                Qt.callLater(loadWorldZoneCatalog);
        }
    }
    onSelectedModeChanged: {
        if (selectedMode !== "clock")
            dismissWorldSearchPopup();
        if (selectedMode !== "calc")
            closeConverterDropdowns();
        if (menuOpen && selectedMode === "tools") {
            refreshStopwatch();
            refreshCountdowns();
        }
        if (menuOpen && selectedMode === "clock")
            Qt.callLater(refreshWorldClock);
        if (menuOpen && (selectedMode === "clock" || selectedMode === "calc"))
            Qt.callLater(loadWorldZoneCatalog);
    }
    onStandardKeysAvailableChanged: {
        if (standardKeysAvailable)
            Qt.callLater(restoreKeyboardFocus);
    }

    // The window stays mapped to avoid the existing layer-shell remap crash.
    // A zero-sized closed mask prevents invisible pointer interception.
    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2
    color: "transparent"
    surfaceFormat.opaque: false
    visible: true
    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        standardKeysAvailable ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None
    focusable: standardKeysAvailable

    // Match the right dock's 8px top inset. The earlier formula adding the
    // dock's 50px height placed the window too low in the live screenshot.
    // Keep the existing frame glow gutter and compensate only by moving the
    // owning PanelWindow up; visual acceptance remains a separate check.
    anchors {
        top: true
        bottom: false
        left: false
        right: true
    }
    margins {
        top: 8
        right: 13
    }
    mask: Region {
        x: timew.glowGutter
        y: timew.glowGutter
        width: timew.menuOpen ? timew.frameWidth : 0
        height: timew.menuOpen ? timew.frameHeight : 0
    }

    SystemClock {
        id: localClock
        precision: SystemClock.Seconds
    }

    // Quickshell v0.2.1's native monotonic elapsed timer; no wall-clock
    // wall-clock queries, network or subprocesses for stopwatch measurement.
    ElapsedTimer {
        id: stopwatchAnchor
    }

    ElapsedTimer {
        id: countdownAnchor
        Component.onCompleted: restart()
    }

    ElapsedTimer {
        id: machineLifetimeAnchor
        Component.onCompleted: restart()
    }

    // Explicit, read-only IPC capture; its JSON is already allowlisted by the
    // Python adapter. No checkpoint saving, restoration or persistent storage.
    Process {
        id: machineCaptureProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(this.text);
                    if (data && data.preview_only === true
                            && data.kind === "sway-layout-metadata-preview"
                            && Array.isArray(data.outputs)
                            && Array.isArray(data.workspaces)
                            && Array.isArray(data.windows)) {
                        timew.machineCapturePreview = data;
                        timew.machineCaptureStatus = "PREVIEW READY // MEMORY ONLY";
                    } else {
                        timew.machineCapturePreview = null;
                        timew.machineCaptureStatus = "CAPTURE UNAVAILABLE";
                    }
                } catch (error) {
                    timew.machineCapturePreview = null;
                    timew.machineCaptureStatus = "INVALID PREVIEW";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.machineCaptureBusy = false;
            if (exitCode !== 0) {
                timew.machineCapturePreview = null;
                timew.machineCaptureStatus = "CAPTURE UNAVAILABLE";
            }
        }
    }

    // CLI save uses stdin; checkpoint contents never appear in argv.
    Process {
        id: machineStoreProcess
        running: false
        stdinEnabled: true
        onStarted: {
            if (timew.machineStoreAction === "save" && timew.machineStorePayload)
                machineStoreProcess.write(timew.machineStorePayload + String.fromCharCode(10));
            timew.machineStorePayload = "";
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(this.text);
                    timew.machineStoreResponse = data;
                    timew.machineAcceptStoreResponse(data);
                } catch (error) {
                    timew.machineStoreStatus = "INVALID STORE RESPONSE";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.machineStoreBusy = false;
            timew.machineStorePayload = "";
            if (exitCode !== 0)
                timew.machineStoreStatus = timew.machineStoreResponse
                    && timew.machineStoreResponse.status === "error"
                    ? "STORAGE ERROR // "
                      + String(timew.machineStoreResponse.reason || "UNKNOWN")
                    : "STORAGE UNAVAILABLE";
        }
    }

    Process {
        id: machineResolverProcess
        running: false
        stdinEnabled: true
        onStarted: {
            if (timew.machineResolverPayload)
                machineResolverProcess.write(
                    timew.machineResolverPayload + String.fromCharCode(10));
            timew.machineResolverPayload = "";
        }
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const data = JSON.parse(this.text);
                    if (timew.machineResolverCheckpointId !== ""
                            && timew.machineSavedItem
                            && timew.machineResolverCheckpointId === timew.machineSavedItem.id
                            && data.kind === "machine-live-window-resolution"
                            && data.read_only === true && data.executable === false
                            && Array.isArray(data.candidates) && data.counts) {
                        timew.machineWindowResolution = data;
                        timew.machineResolverStatus = "LIVE RESOLUTION // REVIEW ONLY";
                    } else {
                        timew.machineWindowResolution = null;
                        timew.machineResolverStatus = "RESOLUTION UNAVAILABLE";
                    }
                } catch (error) {
                    timew.machineWindowResolution = null;
                    timew.machineResolverStatus = "INVALID RESOLUTION";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.machineResolverBusy = false;
            timew.machineResolverPayload = "";
            if (exitCode !== 0) {
                timew.machineWindowResolution = null;
                timew.machineResolverStatus = "LIVE RESOLUTION UNAVAILABLE";
            }
        }
    }

    // Difference comparisons are also one-shot. Existing inputs are kept
    // private, argv is fixed, and stale results are discarded on every edit.
    Process {
        id: differenceProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                if (timew.differenceSubmittedKey !== timew.differenceInputsKey)
                    return;
                try {
                    const data = JSON.parse(this.text);
                    timew.differenceResult =
                        data && typeof data.status === "string"
                        && Array.isArray(data.options)
                        ? data : {status: "INVALID_RESULT", options: []};
                } catch (e) {
                    timew.differenceResult =
                        {status: "INVALID_RESULT", options: []};
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.differenceBusy = false;
            if (exitCode !== 0
                    && timew.differenceSubmittedKey === timew.differenceInputsKey)
                timew.differenceResult =
                    {status: "DIFFERENCE_UNAVAILABLE", options: []};
        }
    }

    // Request-driven elapsed arithmetic. Keep it separate from the zone
    // converter so neither process nor result interferes with the other.
    Process {
        id: arithmeticProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                if (timew.mathSubmittedKey !== timew.mathInputsKey)
                    return;
                try {
                    const result = JSON.parse(this.text);
                    timew.mathResult =
                        result && typeof result.status === "string"
                        && Array.isArray(result.options)
                        ? result : {status: "INVALID_RESULT", options: []};
                } catch (e) {
                    timew.mathResult = {status: "INVALID_RESULT", options: []};
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.mathBusy = false;
            if (exitCode !== 0
                    && timew.mathSubmittedKey === timew.mathInputsKey)
                timew.mathResult = {status: "MATH_UNAVAILABLE", options: []};
        }
    }

    // Manual conversion only. Output is structured JSON from our Python
    // stdlib zoneinfo helper; stale results are ignored after input changes.
    Process {
        id: converterProcess
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                if (timew.converterSubmittedKey !== timew.converterInputsKey)
                    return;
                try {
                    const result = JSON.parse(this.text);
                    if (result && typeof result.status === "string"
                            && Array.isArray(result.options))
                        timew.converterResult = result;
                    else
                        timew.converterResult = {status: "INVALID_RESULT",
                                                 options: []};
                } catch (e) {
                    timew.converterResult = {status: "INVALID_RESULT",
                                             options: []};
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.converterBusy = false;
            if (exitCode !== 0
                    && timew.converterSubmittedKey === timew.converterInputsKey)
                timew.converterResult = {status: "CONVERTER_UNAVAILABLE",
                                         options: []};
        }
    }

    // Load the host's actual IANA zone list once per TimeW window lifetime.
    // No shell, network or filesystem writes. Missing timedatectl is shown
    // explicitly; the four built-in shortcuts still work.
    Process {
        id: zoneCatalogLookup
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                const zones = WorldZoneSearch.parseCatalog(this.text);
                if (zones.length > 0) {
                    timew.worldZoneCatalog = zones;
                    timew.worldCatalogLoaded = true;
                    timew.worldCatalogFailed = false;
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            timew.worldCatalogLoading = false;
            if (exitCode !== 0 || !timew.worldCatalogLoaded)
                timew.worldCatalogFailed = true;
        }
    }

    Process {
        id: isoCountryLookup
        running: false
        stdout: StdioCollector {
            onStreamFinished:
                timew.worldCountryNames =
                    WorldZoneSearch.parseCountryNames(this.text)
        }
    }

    Process {
        id: zoneCountryLookup
        running: false
        stdout: StdioCollector {
            onStreamFinished: timew.worldCountryZoneTable = this.text
        }
    }

    // A short-lived read-only lookup into the host IANA zone database.
    // Existing SystemClock renders seconds; refresh the zone offset at most
    // twice a minute, while Clock mode is open. No continuous subprocess.
    Process {
        id: worldLookup
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                const offset = this.text.trim();
                if (worldLookupZone === timew.selectedWorldZone
                        && WorldClockPolicy.parseOffset(offset) !== null) {
                    timew.worldRawOffset = offset;
                    timew.worldValidZone = worldLookupZone;
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0 && worldLookupZone === timew.selectedWorldZone) {
                timew.worldRawOffset = "";
                timew.worldValidZone = "";
            }
            if (timew.menuOpen && timew.selectedMode === "clock"
                    && worldLookupZone !== timew.selectedWorldZone)
                Qt.callLater(timew.refreshWorldClock);
        }
    }

    Timer {
        interval: 30000
        repeat: true
        running: timew.menuOpen && timew.selectedMode === "clock"
        onTriggered: timew.refreshWorldClock()
    }

    Timer {
        id: stopwatchDisplayTimer
        // 10Hz presentation only; measurement is the ElapsedTimer.
        interval: 100
        repeat: true
        running: timew.stopwatchRunning
                 && timew.menuOpen && timew.selectedMode === "tools"
                 && timew.toolsView === "stopwatch"
        onTriggered: timew.refreshStopwatch()
    }

    Timer {
        id: countdownHeartbeat
        // Always monitor a running timer, even with TOOLS closed.
        // Refresh at 10Hz only while visible; once per second otherwise.
        interval: timew.menuOpen && timew.selectedMode === "tools"
                  && timew.toolsView === "countdown" ? 100 : 1000
        repeat: true
        running: timew.countdownRunningCount > 0
        onTriggered: timew.refreshCountdowns()
    }

    Item {
        id: keyboardAnchor
        anchors.fill: parent
        z: -1000
        enabled: timew.navigationKeysAvailable
        focus: timew.navigationKeysAvailable

        Keys.priority: Keys.BeforeItem
        Keys.onShortcutOverride: function(event) {
            if (!timew.navigationKeysAvailable)
                return;
            if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab
                    || event.key === Qt.Key_Escape)
                event.accepted = true;
        }
        Keys.onPressed: function(event) {
            if (!timew.navigationKeysAvailable)
                return;
            if (event.key === Qt.Key_Escape) {
                timew.menuOpen = false;
            } else if (event.key === Qt.Key_Tab
                       || event.key === Qt.Key_Backtab) {
                const reverse = event.key === Qt.Key_Backtab
                    || (event.modifiers & Qt.ShiftModifier) !== 0;
                timew.cycleMainMode(reverse ? -1 : 1);
            } else {
                return;
            }
            event.accepted = true;
        }
    }

    Shortcut {
        sequence: "Tab"
        context: Qt.WindowShortcut
        enabled: timew.navigationKeysAvailable
        onActivated: timew.cycleMainMode(1)
    }
    Shortcut {
        sequence: "Shift+Tab"
        context: Qt.WindowShortcut
        enabled: timew.navigationKeysAvailable
        onActivated: timew.cycleMainMode(-1)
    }
    Shortcut {
        sequence: "Esc"
        context: Qt.WindowShortcut
        enabled: timew.navigationKeysAvailable
        onActivated: timew.menuOpen = false
    }

    WindowPanelFrame {
        id: timewFrame
        anchors.fill: parent
        anchors.margins: timew.glowGutter
        visible: timew.menuOpen
        glowVisible: timew.menuOpen
        glowColor: timew.semanticColor
        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: timew.semanticColor
        borderWidth: 1
        radius: 0

        // Passive grab observes taps anywhere inside TimeW, including on
        // buttons, without consuming their own clicks. Search/popup taps stay
        // open; other taps close suggestions and restore window navigation.
        TapHandler {
            enabled: timew.worldSearchPopupOpen
                     || worldSearchInput.activeFocus
                     || timew.activeConverterDropdown !== ""
                     || converterSourcePicker.searchFocused
                     || converterTargetPicker.searchFocused
                     || mathZonePicker.searchFocused
                     || differenceEndPicker.searchFocused
            gesturePolicy: TapHandler.DragThreshold
            onTapped: function(point, button) {
                if (button !== Qt.LeftButton)
                    return;
                const px = point.position.x;
                const py = point.position.y;
                if (timew.selectedMode === "clock") {
                    const search = worldSearchArea.mapToItem(timewFrame, 0, 0);
                    const withinSearch = px >= search.x
                                         && px <= search.x + worldSearchArea.width
                                         && py >= search.y
                                         && py <= search.y + worldSearchArea.height;
                    const popup = worldSearchPopup.mapToItem(timewFrame, 0, 0);
                    const withinPopup = worldSearchPopup.visible
                                        && px >= popup.x
                                        && px <= popup.x + worldSearchPopup.width
                                        && py >= popup.y
                                        && py <= popup.y + worldSearchPopup.height;
                    if (!withinSearch && !withinPopup)
                        timew.dismissWorldSearchPopup();
                } else if (timew.selectedMode === "calc") {
                    // Only inspect the active CALC subview; the two CONVERT
                    // pickers remain instantiated while MATH is visible.
                    // Testing hidden pickers would incorrectly keep menus open.
                    if (timew.calcView === "math") {
                        const onMathZone = mathZonePicker.containsFramePoint(
                                               timewFrame, px, py);
                        const onEndZone = timew.mathView === "between"
                                          && differenceEndPicker.containsFramePoint(
                                                 timewFrame, px, py);
                        if (!onMathZone && !onEndZone)
                            timew.closeConverterDropdowns();
                    } else {
                        const inSource = converterSourcePicker.containsFramePoint(
                                             timewFrame, px, py);
                        const inTarget = converterTargetPicker.containsFramePoint(
                                             timewFrame, px, py);
                        if (!inSource && !inTarget)
                            timew.closeConverterDropdowns();
                    }
                }
            }
        }

        Column {
            id: chassis
            anchors.fill: parent
            anchors.margins: 14
            spacing: 8

            Row {
                id: header
                width: parent.width
                height: 42
                spacing: 8

                GohuText {
                    width: parent.width - stateIndicator.width
                           - closeButton.width - header.spacing * 2
                    height: parent.height
                    verticalAlignment: Text.AlignVCenter
                    font.pixelSize: 18
                    font.weight: 700
                    color: Colors.magenta
                    text: "TIME // W"
                }

                Rectangle {
                    id: stateIndicator
                    width: 85
                    height: 32
                    color: "transparent"
                    border.width: 1
                    border.color: Colors.cyan

                    GohuText {
                        anchors.centerIn: parent
                        font.pixelSize: 11
                        color: timew.semanticColor
                        text: timew.selectedMode === "clock"
                              ? "LOCAL" : "PLANNED"
                    }
                }

                ActionButton {
                    id: closeButton
                    width: 35
                    height: 32
                    label: "×"
                    labelPixelSize: 22
                    contentPadding: 4
                    trackLabelGlowLocally: true
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
                    onLeftClicked: timew.menuOpen = false
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
                    model: timew.modes.length

                    ModeButton {
                        width: (modeStrip.width
                                - (timew.modes.length - 1) * modeStrip.spacing)
                               / timew.modes.length
                        height: modeStrip.height
                        bordered: false
                        textOnly: true
                        labelFontSize: 11
                        trackDefaultGlowsLocally: true
                        idlePrimaryColor: timew.semanticColor
                        selected: timew.selectedModeIndex === index
                        keyboardActive: timew.standardKeysAvailable
                        keyboardSelected: timew.selectedModeIndex === index
                        labelText: timew.modes[index].name
                        onTriggered: timew.chooseMode(index)
                    }
                }
            }

            Rectangle {
                id: page
                width: parent.width
                height: Math.max(0, chassis.height - header.height
                                 - headerDivider.height - modeStrip.height
                                 - chassis.spacing * 3)
                color: "transparent"
                border.width: 1
                border.color: Colors.cyan

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    GohuText {
                        text: timew.selectedName + " // TIMEW"
                        color: timew.semanticColor
                        font.pixelSize: 18
                    }

                    Rectangle {
                        width: parent.width
                        height: 2
                        color: Colors.cyan
                        opacity: 0.5
                    }

                    Column {
                        id: localClockPane
                        visible: timew.selectedMode === "clock"
                        // The CLOCK pane owns popup stacking above later
                        // sibling text, including the status footer.
                        z: timew.worldSearchPopupOpen ? 20 : 0
                        width: parent.width
                        spacing: 10

                        Row {
                            width: parent.width
                            height: 34
                            spacing: 8

                            GohuText {
                                width: Math.max(0, parent.width
                                                - hourFormatButton.width
                                                - parent.spacing)
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: timew.clockReadoutText
                                color: timew.clockReadoutColor
                                font.pixelSize: 22
                                elide: Text.ElideRight
                            }

                            ActionButton {
                                id: hourFormatButton
                                width: 60
                                height: 30
                                label: timew.use24Hour ? "24H" : "12H"
                                labelPixelSize: 11
                                trackLabelGlowLocally: true
                                accentColor: timew.clockReadoutColor
                                onLeftClicked: timew.use24Hour = !timew.use24Hour
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: timew.localTimeSnapshot.dateLabel
                            color: Colors.white
                            font.pixelSize: 18
                        }

                        GohuText {
                            width: parent.width
                            text: timew.localTimeSnapshot.utcOffsetLabel
                            color: Colors.orange
                            font.pixelSize: 11
                        }

                        GohuText {
                            text: timew.localTimeSnapshot.state === "ready"
                                  ? "LOCAL CLOCK // SYSTEM TIME"
                                  : "LOCAL CLOCK // UNAVAILABLE"
                            color: Colors.orange
                            font.pixelSize: 11
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.5
                        }

                        GohuText {
                            text: "WORLD // CURRENT TIME"
                            color: timew.semanticColor
                            font.pixelSize: 14
                        }

                        // Search stays above WORLD and the four quick
                        // selectors. Its dropdown opens BELOW their row so
                        // every preset remains clickable while searching.
                        Item {
                            id: worldSearchArea
                            width: parent.width
                            height: 34
                            z: 30

                            Row {
                                id: worldSearchRow
                                anchors.fill: parent
                                spacing: 6

                                ActionButton {
                                    id: worldDropdownArrow
                                    width: 34
                                    height: 34
                                    label: "▾"
                                    labelPixelSize: 18
                                    trackLabelGlowLocally: true
                                    accentColor: Colors.white
                                    selected: timew.worldSearchPopupOpen
                                    onLeftClicked: timew.toggleWorldDropdown()
                                }

                                TextField {
                                    id: worldSearchInput
                                    width: Math.max(0, worldSearchRow.width
                                                    - worldDropdownArrow.width
                                                    - worldSearchRow.spacing)
                                    height: worldSearchRow.height
                                    placeholderText: "SEARCH CITY / TIME ZONE"
                                    placeholderTextColor: Colors.cyan
                                    text: timew.worldSearchQuery
                                    // Typed text and insertion cursor have
                                    // their own semantic colors.
                                    color: Colors.magenta
                                    selectionColor: Colors.magenta
                                    selectedTextColor: Colors.black
                                    cursorDelegate: Rectangle {
                                        width: 2
                                        color: Colors.orange
                                    }
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 12
                                    leftPadding: 9
                                    rightPadding: 9
                                    selectByMouse: true
                                    background: Rectangle {
                                        color: Colors.black
                                        border.color: worldSearchInput.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                        border.width: 1
                                    }
                                    onPressed: timew.openWorldSearchPopup()
                                    onTextEdited: timew.worldSearchEdited(text)
                                    onAccepted: {
                                        if (timew.worldSearchMatches.length > 0)
                                            timew.selectWorldSearchResult(
                                                timew.worldSearchMatches[0].id);
                                    }
                                    Keys.onPressed: function(event) {
                                        if (event.key === Qt.Key_Escape) {
                                            timew.dismissWorldSearchPopup();
                                            event.accepted = true;
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                id: worldSearchPopup
                                // worldZoneStrip is a sibling of
                                // worldSearchArea. Position the popup beneath
                                // the shortcuts without making the Column
                                // reserve extra space for the floating list.
                                y: worldZoneStrip.y + worldZoneStrip.height
                                   + 3 - worldSearchArea.y
                                width: parent.width
                                // A compact count header sits above the
                                // results without changing the window size.
                                height: timew.worldSearchMatches.length > 0
                                        ? Math.min(212, 34
                                                   + timew.worldSearchMatches.length * 30)
                                        : 54
                                z: 60
                                visible: timew.menuOpen
                                         && timew.selectedMode === "clock"
                                         && timew.worldModeActive
                                         && timew.worldSearchPopupOpen
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.white

                                GohuText {
                                    id: worldSearchCount
                                    x: 8
                                    y: 4
                                    width: parent.width - 16
                                    height: 18
                                    verticalAlignment: Text.AlignVCenter
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                    text: (timew.worldSearchQuery.trim() === ""
                                           ? "ITEMS // " : "MATCHES // ")
                                          + timew.worldSearchMatches.length
                                }

                                // Virtualize the full catalog, scrolling only
                                // the rows below the fixed count header.
                                ListView {
                                    id: worldSearchResults
                                    anchors {
                                        top: worldSearchCount.bottom
                                        bottom: parent.bottom
                                        left: parent.left
                                        right: parent.right
                                        margins: 4
                                        topMargin: 4
                                        // Reserve a dedicated gutter for the
                                        // scrollbar's 16px star track plus a
                                        // 5px separation/outer clearance.
                                        rightMargin: worldSearchRail.crossExtent + 5
                                    }
                                    clip: true
                                    spacing: 2
                                    model: timew.worldSearchMatches
                                    boundsBehavior: Flickable.StopAtBounds
                                    interactive: contentHeight > height

                                    delegate: ActionButton {
                                        width: worldSearchResults.width
                                        height: 28
                                        label: modelData.country
                                               ? modelData.country + " // "
                                                 + modelData.label
                                               : modelData.label
                                        labelPixelSize: 11
                                        labelHorizontalAlignment: Text.AlignLeft
                                        trackLabelGlowLocally: true
                                        accentColor: Colors.white
                                        softGlowEnabled: false
                                        onLeftClicked:
                                            timew.selectWorldSearchResult(modelData.id)
                                    }
                                }

                                NeonScrollBar {
                                    id: worldSearchRail
                                    flickable: worldSearchResults
                                    accountForContentOrigin: true
                                    geometryMode: "viewport"
                                    // Default viewport geometry positions the
                                    // rail INSIDE the ListView. Place it in
                                    // the reserved popup gutter instead and
                                    // align its track with the row viewport.
                                    x: worldSearchPopup.width - width - 3
                                    y: worldSearchResults.y
                                    height: worldSearchResults.height
                                    handleStyle: "star"
                                    railColor: Colors.cyan
                                    handleColor: Colors.magenta
                                    handleBorderColor: Colors.magenta
                                    railGlowColor: Colors.white
                                    containGlow: true
                                    visible: timew.worldSearchPopupOpen
                                             && scrollable
                                }

                                GohuText {
                                    visible: timew.worldSearchMatches.length === 0
                                    anchors.centerIn: parent
                                    width: parent.width - 12
                                    height: 24
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 11
                                    color: Colors.orange
                                    text: timew.worldCatalogLoading
                                          ? "LOADING SYSTEM ZONES..."
                                          : timew.worldCatalogFailed
                                          ? "ZONE DIRECTORY UNAVAILABLE"
                                          : timew.worldSearchQuery.trim() === ""
                                          ? "TYPE CITY OR COUNTRY"
                                          : "NO MATCHES"
                                }
                            }
                        }

                        Row {
                            id: worldZoneStrip
                            width: parent.width
                            height: 32
                            spacing: 6

                            ActionButton {
                                id: worldModeButton
                                width: (worldZoneStrip.width
                                        - worldZoneStrip.spacing * 4) / 5
                                height: 30
                                label: "WORLD"
                                labelPixelSize: 11
                                trackLabelGlowLocally: true
                                accentColor: Colors.white
                                selected: timew.worldModeActive
                                selectedFillColor: Colors.magenta
                                selectedForegroundColor: Colors.black
                                onLeftClicked: timew.toggleWorldMode()
                            }

                            Repeater {
                                model: timew.worldZones

                                ActionButton {
                                    width: (worldZoneStrip.width
                                            - worldZoneStrip.spacing * 4) / 5
                                    height: 30
                                    label: modelData.label
                                    labelPixelSize: 11
                                    trackLabelGlowLocally: true
                                    accentColor: timew.semanticColor
                                    selected: !timew.worldModeActive
                                              && modelData.id
                                                 === timew.selectedQuickZone
                                    onLeftClicked:
                                        timew.chooseWorldZone(modelData.id)
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: timew.worldTimeSnapshot.readout
                            color: timew.clockReadoutColor
                            font.pixelSize: 22
                        }

                        GohuText {
                            width: parent.width
                            text: timew.worldModeActive
                                  && timew.selectedWorldZone === ""
                                  ? "WORLD // SELECT A SEARCH RESULT"
                                  : timew.worldClockReady
                                  ? timew.selectedWorldZone + " // "
                                    + timew.worldTimeSnapshot.utcOffsetLabel
                                  : "ZONE LOOKUP // UNAVAILABLE OR UPDATING"
                            color: Colors.orange
                            font.pixelSize: 11
                        }

                        GohuText {
                            width: parent.width
                            text: timew.worldClockReady
                                  ? "DATE // " + timew.worldTimeSnapshot.localDate
                                  : "DATE // --"
                            color: Colors.white
                            font.pixelSize: 11
                        }
                    }

                    Row {
                        id: calcSubModeStrip
                        visible: timew.selectedMode === "calc"
                        width: parent.width
                        height: 34
                        spacing: 6

                        ModeButton {
                            width: (calcSubModeStrip.width - calcSubModeStrip.spacing) / 2
                            height: parent.height
                            bordered: false
                            textOnly: true
                            labelText: "CONVERT"
                            labelFontSize: 11
                            idlePrimaryColor: timew.semanticColor
                            selected: timew.calcView === "convert"
                            onTriggered: timew.setCalcView("convert")
                        }

                        ModeButton {
                            width: (calcSubModeStrip.width - calcSubModeStrip.spacing) / 2
                            height: parent.height
                            bordered: false
                            textOnly: true
                            labelText: "MATH"
                            labelFontSize: 11
                            idlePrimaryColor: timew.semanticColor
                            selected: timew.calcView === "math"
                            onTriggered: timew.setCalcView("math")
                        }
                    }

                    Column {
                        id: converterPane
                        visible: timew.selectedMode === "calc" && timew.calcView === "convert"
                        // Overlay either dropdown above following inputs,
                        // results, and the footer, without shifting the page.
                        z: timew.activeConverterDropdown !== "" ? 20 : 0
                        width: parent.width
                        spacing: 12

                        GohuText {
                            width: parent.width
                            text: "TIME ZONE // DATE + TIME CONVERTER"
                            color: Colors.white
                            font.pixelSize: 13
                        }

                        Row {
                            id: converterSourceRow
                            width: parent.width
                            height: 34
                            spacing: 6
                            z: 40

                            GohuText {
                                width: 45
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: "FROM"
                                color: Colors.cyan
                                font.pixelSize: 11
                            }

                            ActionButton {
                                width: 67
                                height: 30
                                label: "CHANGE"
                                labelPixelSize: 9
                                accentColor: Colors.white
                                onLeftClicked: timew.cycleConverterZone("source")
                            }

                            TimeZonePicker {
                                id: converterSourcePicker
                                width: Math.max(0, converterSourceRow.width
                                                - 45 - 67
                                                - converterSourceRow.spacing * 2)
                                height: converterSourceRow.height
                                selectedZone: timew.converterSourceZone
                                catalog: timew.worldZoneCatalog
                                countryIndex: timew.worldCountryIndex
                                catalogLoading: timew.worldCatalogLoading
                                catalogFailed: timew.worldCatalogFailed
                                expanded: timew.activeConverterDropdown === "source"
                                onOpenRequested: timew.openConverterDropdown("source")
                                onToggleRequested: timew.toggleConverterDropdown("source")
                                onZoneChosen: function(zoneId) {
                                    timew.chooseConverterSearchZone("source", zoneId);
                                }
                            }
                        }

                        Row {
                            id: converterTargetRow
                            width: parent.width
                            height: 34
                            spacing: 6
                            z: 30

                            GohuText {
                                width: 45
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: "TO"
                                color: Colors.cyan
                                font.pixelSize: 11
                            }

                            ActionButton {
                                width: 67
                                height: 30
                                label: "CHANGE"
                                labelPixelSize: 9
                                accentColor: Colors.white
                                onLeftClicked: timew.cycleConverterZone("target")
                            }

                            TimeZonePicker {
                                id: converterTargetPicker
                                width: Math.max(0, converterTargetRow.width
                                                - 45 - 67
                                                - converterTargetRow.spacing * 2)
                                height: converterTargetRow.height
                                selectedZone: timew.converterTargetZone
                                catalog: timew.worldZoneCatalog
                                countryIndex: timew.worldCountryIndex
                                catalogLoading: timew.worldCatalogLoading
                                catalogFailed: timew.worldCatalogFailed
                                expanded: timew.activeConverterDropdown === "target"
                                onOpenRequested: timew.openConverterDropdown("target")
                                onToggleRequested: timew.toggleConverterDropdown("target")
                                onZoneChosen: function(zoneId) {
                                    timew.chooseConverterSearchZone("target", zoneId);
                                }
                            }
                        }

                        Row {
                            id: converterInputs
                            width: parent.width
                            height: 34
                            spacing: 4

                            TextField {
                                id: converterDateInput
                                // A compact three-column row preserves enough
                                // width for date, time/AM-PM, and format button.
                                width: Math.max(0, (converterInputs.width
                                        - converterInputFormatButton.width
                                        - converterInputs.spacing * 2) / 2)
                                height: parent.height
                                text: timew.converterDate
                                placeholderText: "YYYY-MM-DD"
                                color: Colors.magenta
                                placeholderTextColor: Colors.cyan
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 10
                                leftPadding: 3
                                rightPadding: 3
                                cursorDelegate: Rectangle {
                                    width: 2
                                    color: Colors.orange
                                }
                                background: Rectangle {
                                    color: Colors.black
                                    border.width: 1
                                    border.color: converterDateInput.activeFocus
                                                  ? Colors.magenta : Colors.cyan
                                }
                                onTextEdited: {
                                    timew.converterDate = text;
                                    timew.converterResult = null;
                                }
                            }

                            TextField {
                                id: converterTimeInput
                                width: Math.max(0, converterInputs.width
                                        - converterDateInput.width
                                        - converterInputFormatButton.width
                                        - converterInputs.spacing * 2)
                                height: parent.height
                                text: timew.converterTime
                                placeholderText: timew.converterInput24Hour
                                                 ? "HH:MM" : "HH:MM//PM"
                                color: Colors.magenta
                                placeholderTextColor: Colors.cyan
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 10
                                leftPadding: 3
                                rightPadding: 3
                                cursorDelegate: Rectangle {
                                    width: 2
                                    color: Colors.orange
                                }
                                background: Rectangle {
                                    color: Colors.black
                                    border.width: 1
                                    border.color: converterTimeInput.activeFocus
                                                  ? Colors.magenta : Colors.cyan
                                }
                                onTextEdited: {
                                    timew.converterTime = text;
                                    timew.converterResult = null;
                                }
                            }

                            ActionButton {
                                id: converterInputFormatButton
                                width: 44
                                height: converterInputs.height
                                label: timew.converterInput24Hour ? "24H" : "12H"
                                labelPixelSize: 11
                                accentColor: timew.converterInputFormatColor
                                trackLabelGlowLocally: true
                                onLeftClicked: timew.toggleConverterInputFormat()
                            }
                        }

                        ActionButton {
                            id: converterRunButton
                            width: parent.width
                            height: 34
                            label: timew.converterBusy ? "CONVERTING..." : "CONVERT // DATE + TIME"
                            accentColor: Colors.white
                            available: !timew.converterBusy
                            onLeftClicked: timew.runTimeConverter()
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.5
                        }

                        Row {
                            id: converterResultHeader
                            width: parent.width
                            height: 44
                            spacing: 5

                            GohuText {
                                id: converterStatusLabel
                                width: Math.max(0, parent.width
                                                - converterOutputFormatButton.width
                                                - converterResultHeader.spacing)
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                wrapMode: Text.Wrap
                                color: timew.converterResult
                                       && timew.converterResult.status === "READY"
                                       ? Colors.cyan : Colors.orange
                                font.pixelSize: 11
                                text: timew.converterBusy
                                      ? "CONVERSION // WORKING"
                                      : !timew.converterResult
                                      ? "CONVERSION // ENTER DATE AND TIME"
                                      : timew.converterResult.status === "READY"
                                      ? "CONVERSION // 1 VALID INSTANT"
                                      : timew.converterResult.status === "AMBIGUOUS_LOCAL_TIME"
                                      ? "REPEATED HOUR // TWO POSSIBLE INSTANTS"
                                      : timew.converterResult.status === "NONEXISTENT_LOCAL_TIME"
                                      ? "TIME DOES NOT EXIST // DST CLOCK JUMP"
                                      : "CONVERSION // " + timew.converterResult.status
                            }

                            // Output format is independent of how the user
                            // typed the source time. Switching never reruns
                            // the converter or changes its DST-fold choices.
                            ActionButton {
                                id: converterOutputFormatButton
                                width: 44
                                height: 30
                                label: timew.converterOutput24Hour ? "24H" : "12H"
                                labelPixelSize: 11
                                accentColor: timew.converterOutputFormatColor
                                trackLabelGlowLocally: true
                                onLeftClicked: timew.toggleConverterOutputFormat()
                            }
                        }

                        Repeater {
                            model: timew.converterResult
                                   && timew.converterResult.options
                                   ? timew.converterResult.options : []
                            Column {
                                width: converterPane.width
                                spacing: 4
                                GohuText {
                                    width: parent.width
                                    font.pixelSize: 11
                                    color: Colors.white
                                    text: "RESULT " + (index + 1)
                                          + " // " + (index === 0 ? "EARLIER" : "LATER")
                                }
                                GohuText {
                                    width: parent.width
                                    text: ConverterFormat.formatResult(
                                              modelData.destination,
                                              timew.converterOutput24Hour)
                                    color: timew.converterOutputFormatColor
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: "SOURCE // "
                                          + ConverterFormat.formatResult(
                                                modelData.source,
                                                timew.converterOutput24Hour)
                                    color: Colors.orange
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            wrapMode: Text.Wrap
                            text: "FROM and TO support independent country/zone search. "
                                  + "CHANGE cycles quick presets; system time stays unchanged."
                            color: Colors.white
                            opacity: 0.72
                            font.pixelSize: 11
                        }
                    }

                    Column {
                        id: mathPane
                        visible: timew.selectedMode === "calc" && timew.calcView === "math"
                        // Keep the list above date/duration controls and footer.
                        z: (timew.activeConverterDropdown === "math"
                            || timew.activeConverterDropdown === "difference")
                           ? 20 : 0
                        width: parent.width
                        spacing: 10

                        GohuText {
                            text: timew.mathView === "elapsed"
                                  ? "ELAPSED TIME // ADD OR SUBTRACT"
                                  : "ELAPSED TIME // BETWEEN MOMENTS"
                            color: Colors.white
                            font.pixelSize: 13
                        }

                        Row {
                            id: mathZoneRow
                            width: parent.width
                            height: 34
                            spacing: 6
                            z: 40
                            GohuText {
                                width: 50
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: "ZONE"
                                color: Colors.cyan
                                font.pixelSize: 11
                            }
                            ActionButton {
                                width: 67
                                height: 30
                                label: "CHANGE"
                                labelPixelSize: 9
                                accentColor: Colors.white
                                onLeftClicked: timew.cycleConverterZone("source")
                            }
                            TimeZonePicker {
                                id: mathZonePicker
                                width: Math.max(0, mathZoneRow.width
                                                - 50 - 67
                                                - mathZoneRow.spacing * 2)
                                height: mathZoneRow.height
                                selectedZone: timew.converterSourceZone
                                catalog: timew.worldZoneCatalog
                                countryIndex: timew.worldCountryIndex
                                catalogLoading: timew.worldCatalogLoading
                                catalogFailed: timew.worldCatalogFailed
                                expanded: timew.activeConverterDropdown === "math"
                                onOpenRequested: timew.openConverterDropdown("math")
                                onToggleRequested: timew.toggleConverterDropdown("math")
                                onZoneChosen: function(zoneId) {
                                    timew.chooseConverterSearchZone("math", zoneId);
                                }
                            }
                        }

                        Row {
                            id: mathDateTimeRow
                            width: parent.width
                            height: 34
                            spacing: 4
                            TextField {
                                id: mathDateInput
                                width: Math.max(0, (mathDateTimeRow.width
                                        - mathTimeFormatButton.width
                                        - mathDateTimeRow.spacing * 2) / 2)
                                height: parent.height
                                text: timew.converterDate
                                placeholderText: "YYYY-MM-DD"
                                color: Colors.magenta
                                placeholderTextColor: Colors.cyan
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 10
                                leftPadding: 3
                                rightPadding: 3
                                cursorDelegate: Rectangle {
                                    width: 2
                                    color: Colors.orange
                                }
                                background: Rectangle {
                                    color: Colors.black
                                    border.color: mathDateInput.activeFocus
                                                  ? Colors.magenta : Colors.cyan
                                    border.width: 1
                                }
                                onTextEdited: timew.converterDate = text
                            }
                            TextField {
                                id: mathTimeInput
                                width: Math.max(0, mathDateTimeRow.width
                                       - mathDateInput.width
                                       - mathTimeFormatButton.width
                                       - mathDateTimeRow.spacing * 2)
                                height: parent.height
                                text: timew.converterTime
                                placeholderText: timew.converterInput24Hour
                                                 ? "HH:MM" : "HH:MM//PM"
                                color: Colors.magenta
                                placeholderTextColor: Colors.cyan
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 10
                                leftPadding: 3
                                rightPadding: 3
                                cursorDelegate: Rectangle {
                                    width: 2
                                    color: Colors.orange
                                }
                                background: Rectangle {
                                    color: Colors.black
                                    border.color: mathTimeInput.activeFocus
                                                  ? Colors.magenta : Colors.cyan
                                    border.width: 1
                                }
                                onTextEdited: timew.converterTime = text
                            }
                            ActionButton {
                                id: mathTimeFormatButton
                                width: 44
                                height: parent.height
                                label: timew.converterInput24Hour ? "24H" : "12H"
                                labelPixelSize: 11
                                accentColor: timew.converterInputFormatColor
                                onLeftClicked: timew.toggleConverterInputFormat()
                            }
                        }

                        Row {
                            id: mathTypeStrip
                            width: parent.width
                            height: 32
                            spacing: 6
                            ModeButton {
                                width: (mathTypeStrip.width - mathTypeStrip.spacing) / 2
                                height: parent.height
                                bordered: false
                                textOnly: true
                                labelText: "ADD / SUB"
                                labelFontSize: 11
                                idlePrimaryColor: timew.semanticColor
                                selected: timew.mathView === "elapsed"
                                onTriggered: timew.setMathView("elapsed")
                            }
                            ModeButton {
                                width: (mathTypeStrip.width - mathTypeStrip.spacing) / 2
                                height: parent.height
                                bordered: false
                                textOnly: true
                                labelText: "BETWEEN"
                                labelFontSize: 11
                                idlePrimaryColor: timew.semanticColor
                                selected: timew.mathView === "between"
                                onTriggered: timew.setMathView("between")
                            }
                        }

                        Column {
                            id: mathDifferencePane
                            visible: timew.mathView === "between"
                            width: parent.width
                            spacing: 9
                            z: timew.activeConverterDropdown === "difference" ? 30 : 0

                            GohuText {
                                text: "END // DATE + TIME"
                                color: Colors.white
                                font.pixelSize: 12
                            }

                            Row {
                                id: differenceEndZoneRow
                                width: parent.width
                                height: 34
                                spacing: 6
                                z: 30

                                GohuText {
                                    width: 50
                                    height: parent.height
                                    verticalAlignment: Text.AlignVCenter
                                    text: "ZONE"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                ActionButton {
                                    width: 67
                                    height: 30
                                    label: "CHANGE"
                                    labelPixelSize: 9
                                    accentColor: Colors.white
                                    onLeftClicked: timew.cycleDifferenceEndZone()
                                }
                                TimeZonePicker {
                                    id: differenceEndPicker
                                    width: Math.max(0, differenceEndZoneRow.width
                                                    - 50 - 67
                                                    - differenceEndZoneRow.spacing * 2)
                                    height: differenceEndZoneRow.height
                                    selectedZone: timew.differenceEndZone
                                    catalog: timew.worldZoneCatalog
                                    countryIndex: timew.worldCountryIndex
                                    catalogLoading: timew.worldCatalogLoading
                                    catalogFailed: timew.worldCatalogFailed
                                    expanded: timew.activeConverterDropdown === "difference"
                                    onOpenRequested:
                                        timew.openConverterDropdown("difference")
                                    onToggleRequested:
                                        timew.toggleConverterDropdown("difference")
                                    onZoneChosen: function(zoneId) {
                                        timew.chooseConverterSearchZone("difference", zoneId);
                                    }
                                }
                            }

                            Row {
                                id: differenceEndInputs
                                width: parent.width
                                height: 34
                                spacing: 4
                                TextField {
                                    id: differenceEndDateInput
                                    width: Math.max(0, (differenceEndInputs.width
                                            - differenceEndFormatButton.width
                                            - differenceEndInputs.spacing * 2) / 2)
                                    height: parent.height
                                    text: timew.differenceEndDate
                                    placeholderText: "YYYY-MM-DD"
                                    color: Colors.magenta
                                    placeholderTextColor: Colors.cyan
                                    selectionColor: Colors.magenta
                                    selectedTextColor: Colors.black
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 10
                                    leftPadding: 3
                                    rightPadding: 3
                                    cursorDelegate: Rectangle {
                                        width: 2
                                        color: Colors.orange
                                    }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.width: 1
                                        border.color: differenceEndDateInput.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                    }
                                    onTextEdited: timew.differenceEndDate = text
                                }
                                TextField {
                                    id: differenceEndTimeInput
                                    width: Math.max(0, differenceEndInputs.width
                                            - differenceEndDateInput.width
                                            - differenceEndFormatButton.width
                                            - differenceEndInputs.spacing * 2)
                                    height: parent.height
                                    text: timew.differenceEndTime
                                    placeholderText: timew.differenceEnd24Hour
                                                     ? "HH:MM" : "HH:MM//PM"
                                    color: Colors.magenta
                                    placeholderTextColor: Colors.cyan
                                    selectionColor: Colors.magenta
                                    selectedTextColor: Colors.black
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 10
                                    leftPadding: 3
                                    rightPadding: 3
                                    cursorDelegate: Rectangle {
                                        width: 2
                                        color: Colors.orange
                                    }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.width: 1
                                        border.color: differenceEndTimeInput.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                    }
                                    onTextEdited: timew.differenceEndTime = text
                                }
                                ActionButton {
                                    id: differenceEndFormatButton
                                    width: 44
                                    height: parent.height
                                    label: timew.differenceEnd24Hour ? "24H" : "12H"
                                    labelPixelSize: 11
                                    accentColor: timew.differenceEnd24Hour
                                                 ? Colors.orange : Colors.cyan
                                    onLeftClicked: timew.toggleDifferenceEndFormat()
                                }
                            }

                            ActionButton {
                                id: differenceRunButton
                                width: parent.width
                                height: 34
                                label: timew.differenceBusy
                                       ? "CALCULATING..." : "FIND ELAPSED DURATION"
                                labelPixelSize: 11
                                accentColor: Colors.white
                                available: !timew.differenceBusy
                                onLeftClicked: timew.runTimeDifference()
                            }

                            Rectangle {
                                width: parent.width
                                height: 2
                                color: Colors.cyan
                                opacity: 0.5
                            }

                            Row {
                                id: differenceResultHeader
                                width: parent.width
                                height: 40
                                spacing: 6
                                GohuText {
                                    width: parent.width - differenceOutputFormatButton.width
                                           - differenceResultHeader.spacing
                                    height: parent.height
                                    verticalAlignment: Text.AlignVCenter
                                    wrapMode: Text.Wrap
                                    color: timew.differenceResult
                                           && timew.differenceResult.status === "READY"
                                           ? Colors.cyan : Colors.orange
                                    font.pixelSize: 11
                                    text: timew.differenceBusy ? "BETWEEN // WORKING"
                                          : !timew.differenceResult
                                          ? "BETWEEN // ENTER TWO MOMENTS"
                                          : timew.differenceResult.status === "READY"
                                          ? "BETWEEN // 1 DURATION"
                                          : timew.differenceResult.status === "AMBIGUOUS_LOCAL_TIME"
                                          ? "DST OVERLAP // MULTIPLE DURATIONS"
                                          : timew.differenceResult.status.indexOf(
                                                "NONEXISTENT_LOCAL_TIME") >= 0
                                          ? "TIME DOES NOT EXIST // DST CLOCK JUMP"
                                          : "BETWEEN // " + timew.differenceResult.status
                                }
                                ActionButton {
                                    id: differenceOutputFormatButton
                                    width: 44
                                    height: 30
                                    label: timew.converterOutput24Hour ? "24H" : "12H"
                                    labelPixelSize: 11
                                    accentColor: timew.converterOutputFormatColor
                                    onLeftClicked: timew.toggleConverterOutputFormat()
                                }
                            }

                            Item {
                                id: differenceResultsArea
                                width: parent.width
                                height: timew.differenceResult
                                        && timew.differenceResult.options
                                        && timew.differenceResult.options.length > 0
                                        ? Math.min(176,
                                            timew.differenceResult.options.length * 90)
                                        : 0

                            Flickable {
                                id: differenceResults
                                width: Math.max(0, differenceResultsArea.width - 21)
                                height: differenceResultsArea.height
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                contentHeight: differenceResultsColumn.height
                                interactive: contentHeight > height

                                Column {
                                    id: differenceResultsColumn
                                    width: differenceResults.width - 18
                                    spacing: 7
                                    Repeater {
                                        model: timew.differenceResult
                                               && timew.differenceResult.options
                                               ? timew.differenceResult.options : []
                                        Column {
                                            width: differenceResultsColumn.width
                                            spacing: 3
                                            GohuText {
                                                width: parent.width
                                                text: "PAIR " + (index + 1) + " // "
                                                      + modelData.sign
                                                      + modelData.days + "D "
                                                      + modelData.hours + "H "
                                                      + modelData.minutes + "M"
                                                color: timew.converterOutputFormatColor
                                                font.pixelSize: 13
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: "START // " + ConverterFormat.formatResult(
                                                          modelData.start,
                                                          timew.converterOutput24Hour)
                                                elide: Text.ElideRight
                                                color: Colors.orange
                                                font.pixelSize: 11
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: "END // " + ConverterFormat.formatResult(
                                                          modelData.end,
                                                          timew.converterOutput24Hour)
                                                elide: Text.ElideRight
                                                color: Colors.white
                                                font.pixelSize: 11
                                            }
                                        }
                                    }
                                }
                            }
                            NeonScrollBar {
                                id: differenceResultsRail
                                flickable: differenceResults
                                geometryMode: "viewport"
                                x: differenceResultsArea.width - width - 3
                                y: 0
                                height: differenceResults.height
                                handleStyle: "star"
                                railColor: Colors.cyan
                                handleColor: Colors.magenta
                                handleBorderColor: Colors.magenta
                                containGlow: true
                                visible: timew.mathView === "between" && scrollable
                            }
                            }

                            GohuText {
                                width: parent.width
                                text: "ELAPSED DURATION // ZONES AND DST AWARE"
                                color: Colors.white
                                font.pixelSize: 11
                                opacity: 0.72
                            }
                        }

                        Row {
                            id: mathDurationRow
                            visible: timew.mathView === "elapsed"
                            width: parent.width
                            height: 60
                            spacing: 6
                            Column {
                                width: (mathDurationRow.width - mathDurationRow.spacing * 2) / 3
                                spacing: 4
                                GohuText {
                                    text: "DAYS"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: mathDaysInput
                                    width: parent.width
                                    height: 34
                                    text: timew.mathDays
                                    color: Colors.magenta
                                    placeholderText: "0"
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 12
                                    cursorDelegate: Rectangle { width: 2; color: Colors.orange }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.color: mathDaysInput.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                        border.width: 1
                                    }
                                    onTextEdited: timew.mathDays = text
                                }
                            }
                            Column {
                                width: (mathDurationRow.width - mathDurationRow.spacing * 2) / 3
                                spacing: 4
                                GohuText {
                                    text: "HOURS"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: mathHoursInput
                                    width: parent.width
                                    height: 34
                                    text: timew.mathHours
                                    color: Colors.magenta
                                    placeholderText: "1"
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 12
                                    cursorDelegate: Rectangle { width: 2; color: Colors.orange }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.color: mathHoursInput.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                        border.width: 1
                                    }
                                    onTextEdited: timew.mathHours = text
                                }
                            }
                            Column {
                                width: (mathDurationRow.width - mathDurationRow.spacing * 2) / 3
                                spacing: 4
                                GohuText {
                                    text: "MINUTES"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: mathMinutesInput
                                    width: parent.width
                                    height: 34
                                    text: timew.mathMinutes
                                    color: Colors.magenta
                                    placeholderText: "0"
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 12
                                    cursorDelegate: Rectangle { width: 2; color: Colors.orange }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.color: mathMinutesInput.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                        border.width: 1
                                    }
                                    onTextEdited: timew.mathMinutes = text
                                }
                            }
                        }

                        Row {
                            id: mathActionRow
                            visible: timew.mathView === "elapsed"
                            width: parent.width
                            height: 34
                            spacing: 6
                            ActionButton {
                                width: 90
                                height: parent.height
                                label: timew.mathOperation === "add" ? "+ ADD" : "- SUB"
                                labelPixelSize: 11
                                accentColor: timew.mathOperation === "add"
                                             ? Colors.orange : Colors.cyan
                                onLeftClicked: timew.toggleMathOperation()
                            }
                            ActionButton {
                                width: parent.width - 96
                                height: parent.height
                                label: timew.mathBusy ? "CALCULATING..." : "CALCULATE"
                                labelPixelSize: 11
                                available: !timew.mathBusy
                                accentColor: Colors.white
                                onLeftClicked: timew.runTimeArithmetic()
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.5
                        }

                        Row {
                            id: mathResultHeader
                            visible: timew.mathView === "elapsed"
                            width: parent.width
                            height: 42
                            spacing: 6
                            GohuText {
                                width: parent.width - mathResultFormatButton.width
                                       - mathResultHeader.spacing
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                wrapMode: Text.Wrap
                                color: timew.mathResult
                                       && timew.mathResult.status === "READY"
                                       ? Colors.cyan : Colors.orange
                                font.pixelSize: 11
                                text: timew.mathBusy
                                      ? "MATH // WORKING"
                                      : !timew.mathResult ? "MATH // ENTER DURATION"
                                      : timew.mathResult.status === "READY"
                                      ? "MATH // 1 RESULT"
                                      : timew.mathResult.status === "AMBIGUOUS_LOCAL_TIME"
                                      ? "REPEATED HOUR // 2 RESULTS"
                                      : timew.mathResult.status === "NONEXISTENT_LOCAL_TIME"
                                      ? "TIME DOES NOT EXIST // DST CLOCK JUMP"
                                      : "MATH // " + timew.mathResult.status
                            }
                            ActionButton {
                                id: mathResultFormatButton
                                width: 44
                                height: 30
                                label: timew.converterOutput24Hour ? "24H" : "12H"
                                labelPixelSize: 11
                                accentColor: timew.converterOutputFormatColor
                                onLeftClicked: timew.toggleConverterOutputFormat()
                            }
                        }

                        Repeater {
                            model: timew.mathView === "elapsed" && timew.mathResult
                                   && timew.mathResult.options
                                   ? timew.mathResult.options : []
                            Column {
                                width: mathPane.width
                                spacing: 4
                                GohuText {
                                    text: "RESULT " + (index + 1)
                                          + (index === 0 ? " // EARLIER" : " // LATER")
                                    color: Colors.white
                                    font.pixelSize: 11
                                }
                                GohuText {
                                    width: parent.width
                                    text: ConverterFormat.formatResult(
                                              modelData.result,
                                              timew.converterOutput24Hour)
                                    color: timew.converterOutputFormatColor
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: parent.width
                                    text: "SOURCE // " + ConverterFormat.formatResult(
                                              modelData.source,
                                              timew.converterOutput24Hour)
                                    color: Colors.orange
                                    font.pixelSize: 11
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            visible: timew.mathView === "elapsed"
                            text: "ELAPSED // 1 DAY = 24 HOURS. "
                                  + "FROM zone comes from CONVERT."
                            color: Colors.white
                            opacity: 0.72
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                    }

                    Row {
                        id: toolsSubModeStrip
                        visible: timew.selectedMode === "tools"
                        width: parent.width
                        height: 34
                        spacing: 6

                        ModeButton {
                            width: (toolsSubModeStrip.width
                                    - toolsSubModeStrip.spacing) / 2
                            height: parent.height
                            bordered: false
                            textOnly: true
                            labelText: "STOPWATCH"
                            labelFontSize: 11
                            idlePrimaryColor: timew.semanticColor
                            selected: timew.toolsView === "stopwatch"
                            onTriggered: {
                                timew.toolsView = "stopwatch";
                                timew.refreshStopwatch();
                            }
                        }

                        ModeButton {
                            width: (toolsSubModeStrip.width
                                    - toolsSubModeStrip.spacing) / 2
                            height: parent.height
                            bordered: false
                            textOnly: true
                            labelText: "COUNTDOWN"
                            labelFontSize: 11
                            idlePrimaryColor: timew.semanticColor
                            selected: timew.toolsView === "countdown"
                            onTriggered: {
                                timew.toolsView = "countdown";
                                timew.refreshCountdowns();
                            }
                        }
                    }

                    Column {
                        id: stopwatchPane
                        visible: timew.selectedMode === "tools"
                                 && timew.toolsView === "stopwatch"
                        width: parent.width
                        spacing: 12

                        GohuText {
                            text: "STOPWATCH // ELAPSED TIME"
                            color: timew.semanticColor
                            font.pixelSize: 14
                        }

                        GohuText {
                            width: parent.width
                            text: StopwatchPolicy.format(timew.stopwatchDisplayMs)
                            color: timew.stopwatchRunning ? Colors.orange
                                   : timew.stopwatchStarted ? Colors.cyan
                                   : timew.semanticColor
                            font.pixelSize: 28
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Row {
                            width: parent.width
                            height: 22
                            GohuText {
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: timew.stopwatchRunning ? "STATUS // RUNNING"
                                      : timew.stopwatchStarted ? "STATUS // PAUSED"
                                      : "STATUS // READY"
                                color: timew.stopwatchRunning
                                       ? Colors.orange : Colors.cyan
                                font.pixelSize: 11
                            }
                        }

                        Row {
                            id: stopwatchActions
                            width: parent.width
                            height: 38
                            spacing: 8

                            ActionButton {
                                id: stopwatchRunButton
                                width: (stopwatchActions.width
                                        - stopwatchActions.spacing) / 2
                                height: parent.height
                                label: timew.stopwatchRunning ? "PAUSE"
                                       : timew.stopwatchStarted ? "RESUME" : "START"
                                labelPixelSize: 12
                                accentColor: timew.stopwatchRunning
                                             ? Colors.cyan : Colors.orange
                                trackLabelGlowLocally: true
                                onLeftClicked: {
                                    if (timew.stopwatchRunning)
                                        timew.pauseStopwatch();
                                    else
                                        timew.startStopwatch();
                                }
                            }

                            ActionButton {
                                id: stopwatchSecondaryButton
                                width: (stopwatchActions.width
                                        - stopwatchActions.spacing) / 2
                                height: parent.height
                                label: timew.stopwatchRunning ? "LAP" : "RESET"
                                labelPixelSize: 12
                                accentColor: timew.semanticColor
                                trackLabelGlowLocally: true
                                available: timew.stopwatchStarted
                                onLeftClicked: {
                                    if (timew.stopwatchRunning)
                                        timew.lapStopwatch();
                                    else
                                        timew.resetStopwatch();
                                }
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.55
                        }

                        Row {
                            width: parent.width
                            height: 25
                            GohuText {
                                width: parent.width * 0.55
                                text: "LAPS // " + timew.stopwatchLapSequence
                                color: Colors.white
                                font.pixelSize: 12
                            }
                            GohuText {
                                width: parent.width * 0.45
                                horizontalAlignment: Text.AlignRight
                                text: "SHOWN // " + timew.stopwatchLaps.length
                                color: Colors.cyan
                                font.pixelSize: 11
                            }
                        }

                        Item {
                            id: stopwatchLapArea
                            width: parent.width
                            height: 315

                            ListView {
                                id: stopwatchLapList
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                    margins: 3
                                    rightMargin: stopwatchLapRail.crossExtent + 6
                                }
                                model: timew.stopwatchLaps
                                spacing: 4
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                interactive: contentHeight > height

                                delegate: Rectangle {
                                    width: stopwatchLapList.width
                                    height: 39
                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.cyan

                                    Row {
                                        anchors.fill: parent
                                        anchors.margins: 5
                                        spacing: 5
                                        GohuText {
                                            width: 60
                                            height: parent.height
                                            verticalAlignment: Text.AlignVCenter
                                            text: "#" + modelData.index
                                            color: Colors.white
                                            font.pixelSize: 11
                                        }
                                        GohuText {
                                            width: (parent.width - 70) * 0.48
                                            height: parent.height
                                            verticalAlignment: Text.AlignVCenter
                                            text: StopwatchPolicy.format(modelData.splitMs)
                                            color: Colors.cyan
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                        GohuText {
                                            width: (parent.width - 70) * 0.52
                                            height: parent.height
                                            verticalAlignment: Text.AlignVCenter
                                            horizontalAlignment: Text.AlignRight
                                            text: StopwatchPolicy.format(modelData.totalMs)
                                            color: Colors.orange
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                id: stopwatchLapRail
                                flickable: stopwatchLapList
                                accountForContentOrigin: true
                                geometryMode: "viewport"
                                x: stopwatchLapArea.width - width - 3
                                y: stopwatchLapList.y
                                height: stopwatchLapList.height
                                handleStyle: "star"
                                railColor: Colors.cyan
                                handleColor: Colors.magenta
                                handleBorderColor: Colors.magenta
                                railGlowColor: Colors.white
                                containGlow: true
                                visible: scrollable
                            }

                            GohuText {
                                visible: timew.stopwatchLaps.length === 0
                                anchors.centerIn: parent
                                width: parent.width
                                horizontalAlignment: Text.AlignHCenter
                                text: "NO LAPS // START + LAP"
                                color: Colors.white
                                font.pixelSize: 11
                                opacity: 0.7
                            }
                        }

                        GohuText {
                            width: parent.width
                            wrapMode: Text.Wrap
                            text: "MONOTONIC // CONTINUES WHILE WINDOW IS CLOSED"
                            color: Colors.white
                            font.pixelSize: 10
                            opacity: 0.72
                        }

                    }

                    Column {
                        id: countdownPane
                        visible: timew.selectedMode === "tools"
                                 && timew.toolsView === "countdown"
                        width: parent.width
                        spacing: 9

                        GohuText {
                            text: "COUNTDOWN // NAMED TIMERS"
                            color: timew.semanticColor
                            font.pixelSize: 14
                        }

                        Row {
                            id: countdownListHeader
                            width: parent.width
                            height: 30
                            spacing: 8
                            GohuText {
                                width: parent.width - newCountdownButton.width
                                       - countdownListHeader.spacing
                                height: parent.height
                                verticalAlignment: Text.AlignVCenter
                                text: "TIMERS // " + timew.countdownTimers.length
                                      + "    ACTIVE // " + timew.countdownRunningCount
                                color: Colors.cyan
                                font.pixelSize: 11
                            }
                            ActionButton {
                                id: newCountdownButton
                                width: 72
                                height: parent.height
                                label: "+ NEW"
                                labelPixelSize: 11
                                accentColor: timew.semanticColor
                                available: timew.countdownTimers.length
                                           < CountdownPolicy.MAX_TIMERS
                                onLeftClicked: timew.createCountdown()
                            }
                        }

                        Item {
                            id: countdownListArea
                            width: parent.width
                            height: 126

                            ListView {
                                id: countdownTimerList
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                    margins: 3
                                    rightMargin: countdownListRail.crossExtent + 6
                                }
                                clip: true
                                spacing: 3
                                boundsBehavior: Flickable.StopAtBounds
                                interactive: contentHeight > height
                                model: timew.countdownTimers

                                delegate: ActionButton {
                                    width: countdownTimerList.width
                                    height: 35
                                    label: (modelData.name.trim() !== ""
                                            ? modelData.name : "TIMER " + modelData.id)
                                           + " // "
                                           + CountdownPolicy.format(
                                               CountdownPolicy.displayMs(modelData))
                                    labelPixelSize: 10
                                    labelHorizontalAlignment: Text.AlignLeft
                                    trackLabelGlowLocally: true
                                    selected: timew.selectedCountdownId === modelData.id
                                    accentColor: modelData.status === "finished"
                                                 ? Colors.magenta
                                                 : modelData.status === "running"
                                                 ? Colors.orange
                                                 : Colors.white
                                    onLeftClicked: timew.selectCountdown(modelData.id)
                                }
                            }

                            NeonScrollBar {
                                id: countdownListRail
                                flickable: countdownTimerList
                                accountForContentOrigin: true
                                geometryMode: "viewport"
                                x: countdownListArea.width - width - 3
                                y: countdownTimerList.y
                                height: countdownTimerList.height
                                handleStyle: "star"
                                railColor: Colors.cyan
                                handleColor: Colors.magenta
                                handleBorderColor: Colors.magenta
                                railGlowColor: Colors.white
                                containGlow: true
                                visible: scrollable
                            }
                        }

                        TextField {
                            id: countdownNameField
                            width: parent.width
                            height: 32
                            text: timew.selectedCountdown.name
                            placeholderText: "TIMER NAME"
                            maximumLength: CountdownPolicy.MAX_NAME_LENGTH
                            color: Colors.magenta
                            placeholderTextColor: Colors.cyan
                            selectionColor: Colors.magenta
                            selectedTextColor: Colors.black
                            font.family: "GohuFont 11 Nerd Font Mono"
                            font.pixelSize: 12
                            cursorDelegate: Rectangle {
                                width: 2
                                color: Colors.orange
                            }
                            background: Rectangle {
                                color: Colors.black
                                border.width: 1
                                border.color: countdownNameField.activeFocus
                                              ? Colors.magenta : Colors.cyan
                            }
                            onTextEdited: timew.editCountdown("name", text)
                        }

                        GohuText {
                            width: parent.width
                            height: 38
                            verticalAlignment: Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                            text: CountdownPolicy.format(
                                      CountdownPolicy.displayMs(
                                          timew.selectedCountdown))
                            color: timew.selectedCountdown.status === "finished"
                                   ? Colors.magenta
                                   : timew.selectedCountdown.status === "running"
                                   ? Colors.orange
                                   : timew.selectedCountdown.status === "paused"
                                   ? Colors.cyan : timew.semanticColor
                            font.pixelSize: 26
                        }

                        GohuText {
                            width: parent.width
                            text: timew.selectedCountdown.error !== ""
                                  ? "TIMER // " + timew.selectedCountdown.error
                                  : "STATUS // " + timew.selectedCountdown.status.toUpperCase()
                            horizontalAlignment: Text.AlignHCenter
                            color: timew.selectedCountdown.status === "finished"
                                   ? Colors.magenta
                                   : timew.selectedCountdown.status === "running"
                                   ? Colors.orange : Colors.cyan
                            font.pixelSize: 11
                        }

                        Row {
                            id: countdownInputRow
                            width: parent.width
                            height: 61
                            spacing: 8

                            Column {
                                width: (countdownInputRow.width
                                        - countdownInputRow.spacing * 2) / 3
                                spacing: 4
                                GohuText {
                                    text: "HOURS"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: countdownHoursField
                                    width: parent.width
                                    height: 35
                                    text: timew.selectedCountdown.hours
                                    placeholderText: "00"
                                    color: Colors.magenta
                                    placeholderTextColor: Colors.cyan
                                    selectionColor: Colors.magenta
                                    selectedTextColor: Colors.black
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 15
                                    horizontalAlignment: Text.AlignHCenter
                                    readOnly: timew.selectedCountdown.status !== "ready"
                                    cursorDelegate: Rectangle {
                                        width: 2
                                        color: Colors.orange
                                    }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.width: 1
                                        border.color: countdownHoursField.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                    }
                                    onTextEdited: timew.editCountdown("hours", text)
                                }
                            }

                            Column {
                                width: (countdownInputRow.width
                                        - countdownInputRow.spacing * 2) / 3
                                spacing: 4
                                GohuText {
                                    text: "MINUTES"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: countdownMinutesField
                                    width: parent.width
                                    height: 35
                                    text: timew.selectedCountdown.minutes
                                    placeholderText: "00"
                                    color: Colors.magenta
                                    placeholderTextColor: Colors.cyan
                                    selectionColor: Colors.magenta
                                    selectedTextColor: Colors.black
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 15
                                    horizontalAlignment: Text.AlignHCenter
                                    readOnly: timew.selectedCountdown.status !== "ready"
                                    cursorDelegate: Rectangle {
                                        width: 2
                                        color: Colors.orange
                                    }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.width: 1
                                        border.color: countdownMinutesField.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                    }
                                    onTextEdited: timew.editCountdown("minutes", text)
                                }
                            }

                            Column {
                                width: (countdownInputRow.width
                                        - countdownInputRow.spacing * 2) / 3
                                spacing: 4
                                GohuText {
                                    text: "SECONDS"
                                    color: Colors.cyan
                                    font.pixelSize: 11
                                }
                                TextField {
                                    id: countdownSecondsField
                                    width: parent.width
                                    height: 35
                                    text: timew.selectedCountdown.seconds
                                    placeholderText: "00"
                                    color: Colors.magenta
                                    placeholderTextColor: Colors.cyan
                                    selectionColor: Colors.magenta
                                    selectedTextColor: Colors.black
                                    font.family: "GohuFont 11 Nerd Font Mono"
                                    font.pixelSize: 15
                                    horizontalAlignment: Text.AlignHCenter
                                    readOnly: timew.selectedCountdown.status !== "ready"
                                    cursorDelegate: Rectangle {
                                        width: 2
                                        color: Colors.orange
                                    }
                                    background: Rectangle {
                                        color: Colors.black
                                        border.width: 1
                                        border.color: countdownSecondsField.activeFocus
                                                      ? Colors.magenta : Colors.cyan
                                    }
                                    onTextEdited: timew.editCountdown("seconds", text)
                                }
                            }
                        }

                        Row {
                            id: countdownActions
                            width: parent.width
                            height: 36
                            spacing: 6
                            ActionButton {
                                id: countdownRunButton
                                width: (countdownActions.width - countdownActions.spacing * 2) * 0.4
                                height: parent.height
                                label: timew.selectedCountdown.status === "running" ? "PAUSE"
                                       : timew.selectedCountdown.status === "paused" ? "RESUME"
                                       : timew.selectedCountdown.status === "finished"
                                         ? "RESTART" : "START"
                                labelPixelSize: 11
                                accentColor: timew.selectedCountdown.status === "running"
                                             ? Colors.cyan : Colors.orange
                                trackLabelGlowLocally: true
                                onLeftClicked: {
                                    if (timew.selectedCountdown.status === "running")
                                        timew.pauseCountdown();
                                    else
                                        timew.startCountdown();
                                }
                            }
                            ActionButton {
                                id: countdownResetButton
                                width: (countdownActions.width - countdownActions.spacing * 2) * 0.3
                                height: parent.height
                                label: "RESET"
                                labelPixelSize: 11
                                accentColor: timew.semanticColor
                                trackLabelGlowLocally: true
                                available: timew.selectedCountdown.status !== "ready"
                                           || timew.selectedCountdown.error !== ""
                                onLeftClicked: timew.resetCountdown()
                            }
                            ActionButton {
                                id: countdownRemoveButton
                                width: (countdownActions.width - countdownActions.spacing * 2) * 0.3
                                height: parent.height
                                label: "REMOVE"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: timew.countdownTimers.length > 1
                                onLeftClicked: timew.removeCountdown()
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.55
                        }

                        GohuText {
                            width: parent.width
                            text: "MAX 8 TIMERS // MONOTONIC // SESSION ONLY"
                            color: Colors.white
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }

                        GohuText {
                            width: parent.width
                            text: "NO AUDIO OR DESKTOP NOTIFICATION // INITIAL SLICE"
                            color: Colors.orange
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                    }

                    Column {
                        id: machinePane
                        visible: timew.selectedMode === "machine" && !timew.machineStoredViewOpen
                        width: parent.width
                        spacing: 9

                        GohuText {
                            width: parent.width
                            text: "MACHINE // SESSION TIMELINE"
                            color: timew.semanticColor
                            font.pixelSize: 14
                        }

                        GohuText {
                            width: parent.width
                            text: "WINDOW INSTANCE // ELAPSED"
                            color: Colors.cyan
                            font.pixelSize: 11
                        }

                        GohuText {
                            width: parent.width
                            text: timew.machineInstanceAge
                            color: Colors.orange
                            font.pixelSize: 24
                            horizontalAlignment: Text.AlignHCenter
                        }

                        GohuText {
                            width: parent.width
                            text: "UTC // " + timew.machineUtcNow
                            color: Colors.white
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.55
                        }

                        Row {
                            id: machineActivityRow
                            width: parent.width
                            height: 24
                            spacing: 8
                            GohuText {
                                width: (parent.width - machineActivityRow.spacing) / 2
                                text: "STOPWATCH // "
                                      + (timew.stopwatchRunning ? "RUNNING"
                                         : timew.stopwatchStarted ? "PAUSED" : "READY")
                                color: timew.stopwatchRunning ? Colors.orange : Colors.cyan
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                            GohuText {
                                width: (parent.width - machineActivityRow.spacing) / 2
                                text: "TIMERS // " + timew.countdownRunningCount
                                      + " ACTIVE"
                                color: timew.countdownRunningCount > 0
                                       ? Colors.orange : Colors.cyan
                                font.pixelSize: 11
                                elide: Text.ElideRight
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.55
                        }

                        Row {
                            id: machineCaptureRow
                            width: parent.width
                            height: 34
                            spacing: 8
                            ActionButton {
                                width: 150
                                height: parent.height
                                label: "CAPTURE PREVIEW"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: !timew.machineCaptureBusy
                                onLeftClicked: timew.requestMachineCapturePreview()
                            }
                            GohuText {
                                width: parent.width - 158
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineCaptureStatus
                                color: timew.machineCaptureBusy ? Colors.orange : Colors.cyan
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: timew.machineCapturePreview
                                  ? ("OUTPUTS // " + timew.machineCapturePreview.outputs.length
                                     + "     WORKSPACES // " + timew.machineCapturePreview.workspaces.length
                                     + "     WINDOWS // " + timew.machineCapturePreview.windows.length)
                                  : "CLICK TO READ LAYOUT // NO SAVE OR RESTORE"
                            color: Colors.white
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                        }

                        Row {
                            width: parent.width
                            height: 27
                            spacing: 4
                            visible: timew.machineCapturePreview !== null
                            Repeater {
                                model: [
                                    {name: "MONITORS", kind: "outputs"},
                                    {name: "WORKSPACES", kind: "workspaces"},
                                    {name: "WINDOWS", kind: "windows"}
                                ]
                                delegate: ActionButton {
                                    width: (machinePane.width - 8) / 3
                                    height: 27
                                    label: modelData.name
                                    labelPixelSize: 9
                                    accentColor: timew.machineInspectKind === modelData.kind
                                                 ? Colors.magenta : timew.semanticColor
                                    onLeftClicked: timew.selectMachineInspectKind(modelData.kind)
                                }
                            }
                        }
                        Row {
                            width: parent.width
                            height: 29
                            spacing: 5
                            visible: timew.machineCapturePreview !== null
                            ActionButton {
                                width: 43
                                height: parent.height
                                label: "<"
                                labelPixelSize: 12
                                accentColor: timew.semanticColor
                                available: timew.machineInspectItems.length > 1
                                onLeftClicked: timew.stepMachineInspect(-1)
                            }
                            GohuText {
                                width: Math.max(0, parent.width - 96)
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineInspectItems.length
                                      ? (timew.machineInspectIndex + 1) + " / "
                                        + timew.machineInspectItems.length
                                      : "0 / 0"
                                horizontalAlignment: Text.AlignHCenter
                                color: Colors.cyan
                                font.pixelSize: 12
                            }
                            ActionButton {
                                width: 43
                                height: parent.height
                                label: ">"
                                labelPixelSize: 12
                                accentColor: timew.semanticColor
                                available: timew.machineInspectItems.length > 1
                                onLeftClicked: timew.stepMachineInspect(1)
                            }
                        }
                        GohuText {
                            width: parent.width
                            visible: timew.machineCapturePreview !== null
                            text: !timew.machineInspectItem
                                  ? "NO ITEMS IN THIS CATEGORY"
                                  : timew.machineInspectKind === "outputs"
                                  ? timew.machineInspectItem.connector + " // "
                                    + timew.machineInspectItem.rect.width + "x"
                                    + timew.machineInspectItem.rect.height
                                  : timew.machineInspectKind === "workspaces"
                                  ? timew.machineInspectItem.name + " // "
                                    + timew.machineInspectItem.output
                                  : timew.machineInspectItem.app_id + " // "
                                    + timew.machineInspectItem.workspace
                                    + (timew.machineInspectItem.floating
                                       ? " // FLOATING" : " // TILED")
                            color: Colors.white
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }

                        Row {
                            width: parent.width
                            height: 29
                            spacing: 7
                            visible: timew.machineCapturePreview !== null
                            ActionButton {
                                width: 142
                                height: parent.height
                                label: timew.machineItemIncluded(timew.machineInspectKind,
                                                                timew.machineInspectIndex)
                                       ? "EXCLUDE ITEM" : "INCLUDE ITEM"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: timew.machineInspectItem !== null
                                onLeftClicked: timew.toggleMachineItemSelection()
                            }
                            GohuText {
                                width: parent.width - 149
                                anchors.verticalCenter: parent.verticalCenter
                                text: "INCLUDED // "
                                      + timew.machineIncludedCount(timew.machineInspectKind)
                                      + " / " + timew.machineInspectItems.length
                                color: Colors.cyan
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                        }
                        Row {
                            width: parent.width
                            height: 27
                            spacing: 6
                            visible: timew.machineCapturePreview !== null
                            GohuText {
                                width: Math.max(0, parent.width - 96)
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineSelectionValidation.status === "ready"
                                      ? "SELECTION CONSISTENT // READY TO SAVE"
                                      : timew.machineSelectionValidation.issues.length > 0
                                      ? "BLOCKED " + timew.machineSelectionValidation.issueCount
                                        + " // " + timew.machineSelectionValidation.issues[0].label
                                      : "BLOCKED // INVALID PREVIEW"
                                color: timew.machineSelectionValidation.status === "ready"
                                       ? Colors.cyan : Colors.orange
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 90
                                height: parent.height
                                label: "LOCATE"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: timew.machineSelectionValidation.issues.length > 0
                                onLeftClicked: timew.machineLocateSelectionIssue()
                            }
                        }
                        Row {
                            width: parent.width
                            height: 34
                            spacing: 6
                            ActionButton {
                                width: (parent.width - 12) / 2
                                height: parent.height
                                label: "SAVE CHECKPOINT"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: !timew.machineStoreBusy && !timew.machineCaptureBusy
                                           && timew.machineSelectionValidation.status === "ready"
                                onLeftClicked: timew.machineSaveCheckpoint()
                            }
                            ActionButton {
                                width: (parent.width - 12) / 2
                                height: parent.height
                                label: "STORED"
                                labelPixelSize: 11
                                accentColor: timew.semanticColor
                                available: !timew.machineStoreBusy
                                onLeftClicked: timew.machineShowSavedCheckpoints()
                            }
                        }
                        GohuText {
                            width: parent.width
                            text: timew.machineStoreStatus
                            color: Colors.orange
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            text: "MANUAL TIME MARKERS // MEMORY ONLY"
                            color: Colors.white
                            font.pixelSize: 12
                        }

                        Row {
                            id: machineMarkerRow
                            width: parent.width
                            height: 35
                            spacing: 7

                            TextField {
                                id: machineMarkerInput
                                width: Math.max(0, parent.width
                                        - machineMarkButton.width
                                        - machineMarkerRow.spacing)
                                height: parent.height
                                text: timew.machineMarkerDraft
                                maximumLength: MachineTimelinePolicy.MAX_NAME_LENGTH
                                placeholderText: "NAME THIS MOMENT"
                                color: Colors.magenta
                                placeholderTextColor: Colors.cyan
                                selectionColor: Colors.magenta
                                selectedTextColor: Colors.black
                                font.family: "GohuFont 11 Nerd Font Mono"
                                font.pixelSize: 12
                                leftPadding: 8
                                rightPadding: 8
                                cursorDelegate: Rectangle {
                                    width: 2
                                    color: Colors.orange
                                }
                                background: Rectangle {
                                    color: Colors.black
                                    border.width: 1
                                    border.color: machineMarkerInput.activeFocus
                                                  ? Colors.magenta : Colors.cyan
                                }
                                onTextEdited: timew.machineMarkerDraft = text
                                onAccepted: timew.addMachineMarker()
                            }

                            ActionButton {
                                id: machineMarkButton
                                width: 75
                                height: parent.height
                                label: "MARK"
                                labelPixelSize: 11
                                accentColor: timew.semanticColor
                                available: timew.machineMarkers.length
                                           < MachineTimelinePolicy.MAX_MARKERS
                                onLeftClicked: timew.addMachineMarker()
                            }
                        }

                        Row {
                            width: parent.width
                            height: 22
                            GohuText {
                                width: parent.width
                                text: "MARKERS // " + timew.machineMarkers.length
                                      + " / " + MachineTimelinePolicy.MAX_MARKERS
                                color: Colors.cyan
                                font.pixelSize: 11
                            }
                        }

                        Item {
                            id: machineMarkerArea
                            width: parent.width
                            height: 67

                            ListView {
                                id: machineMarkerList
                                anchors {
                                    top: parent.top
                                    bottom: parent.bottom
                                    left: parent.left
                                    right: parent.right
                                    margins: 3
                                    rightMargin: machineMarkerRail.crossExtent + 6
                                }
                                model: timew.machineMarkers
                                spacing: 4
                                clip: true
                                interactive: contentHeight > height
                                boundsBehavior: Flickable.StopAtBounds

                                delegate: Rectangle {
                                    width: machineMarkerList.width
                                    height: 52
                                    color: Colors.black
                                    border.width: 1
                                    border.color: Colors.cyan

                                    Row {
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        spacing: 5
                                        Column {
                                            width: Math.max(0, parent.width
                                                    - removeMachineMarkerButton.width
                                                    - parent.spacing)
                                            spacing: 4
                                            GohuText {
                                                width: parent.width
                                                text: "#" + modelData.id + " // " + modelData.label
                                                color: Colors.white
                                                font.pixelSize: 11
                                                elide: Text.ElideRight
                                            }
                                            GohuText {
                                                width: parent.width
                                                text: modelData.utc
                                                color: Colors.orange
                                                font.pixelSize: 10
                                                elide: Text.ElideRight
                                            }
                                        }
                                        ActionButton {
                                            id: removeMachineMarkerButton
                                            width: 65
                                            height: parent.height
                                            label: "REMOVE"
                                            labelPixelSize: 10
                                            accentColor: timew.semanticColor
                                            onLeftClicked:
                                                timew.removeMachineMarker(modelData.id)
                                        }
                                    }
                                }
                            }

                            NeonScrollBar {
                                id: machineMarkerRail
                                flickable: machineMarkerList
                                accountForContentOrigin: true
                                geometryMode: "viewport"
                                x: machineMarkerArea.width - width - 3
                                y: machineMarkerList.y
                                height: machineMarkerList.height
                                handleStyle: "star"
                                railColor: Colors.cyan
                                handleColor: Colors.magenta
                                handleBorderColor: Colors.magenta
                                railGlowColor: Colors.white
                                containGlow: true
                                visible: scrollable
                            }

                            GohuText {
                                visible: timew.machineMarkers.length === 0
                                anchors.centerIn: parent
                                text: "NO MARKERS // NAME A MOMENT"
                                color: Colors.white
                                opacity: 0.72
                                font.pixelSize: 11
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 2
                            color: Colors.cyan
                            opacity: 0.55
                        }

                        GohuText {
                            width: parent.width
                            text: "NO SCREENSHOTS OR RESTORATION ACTIVE"
                            color: Colors.orange
                            font.pixelSize: 11
                        }
                        GohuText {
                            width: parent.width
                            text: "MARKERS ARE TIMESTAMPS ONLY // LOST ON RESTART"
                            color: Colors.white
                            opacity: 0.74
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                        }
                    }

                    Column {
                        id: machineStoredPane
                        visible: timew.selectedMode === "machine" && timew.machineStoredViewOpen
                        width: parent.width
                        spacing: 14

                        GohuText {
                            width: parent.width
                            text: "MACHINE // STORED CHECKPOINTS"
                            color: timew.semanticColor
                            font.pixelSize: 14
                        }
                        Row {
                            width: parent.width
                            height: 35
                            spacing: 8
                            ActionButton {
                                width: (parent.width - 8) / 2
                                height: parent.height
                                label: "BACK TO CAPTURE"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                onLeftClicked: timew.machineStoredViewOpen = false
                            }
                            ActionButton {
                                width: (parent.width - 8) / 2
                                height: parent.height
                                label: "REFRESH STORED"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: !timew.machineStoreBusy
                                onLeftClicked: timew.machineListCheckpoints()
                            }
                        }
                        Row {
                            width: parent.width
                            height: 32
                            spacing: 5
                            ActionButton {
                                width: 48
                                height: parent.height
                                label: "<"
                                accentColor: timew.semanticColor
                                available: timew.machineSavedCheckpoints.length > 1
                                onLeftClicked: timew.machineStepSavedCheckpoint(-1)
                            }
                            GohuText {
                                width: Math.max(0, parent.width - 106)
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineSavedCheckpoints.length
                                      ? (timew.machineSavedIndex + 1) + " / "
                                        + timew.machineSavedCheckpoints.length
                                      : "NO SAVED CHECKPOINTS"
                                color: Colors.cyan
                                horizontalAlignment: Text.AlignHCenter
                                font.pixelSize: 12
                            }
                            ActionButton {
                                width: 48
                                height: parent.height
                                label: ">"
                                accentColor: timew.semanticColor
                                available: timew.machineSavedCheckpoints.length > 1
                                onLeftClicked: timew.machineStepSavedCheckpoint(1)
                            }
                        }
                        GohuText {
                            width: parent.width
                            text: timew.machineSavedItem ? timew.machineSavedItem.label
                                                          : "NO SAVED RECORD SELECTED"
                            color: Colors.orange
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: timew.machineSavedItem
                                  ? "SAVED // " + timew.machineSavedItem.saved_at_utc
                                  : "RECORDS SURVIVE RESTARTS IF LOCAL STORAGE REMAINS"
                            color: Colors.white
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: timew.machineSavedItem
                                  ? "OUTPUTS " + timew.machineSavedItem.counts.outputs
                                    + " // WORKSPACES " + timew.machineSavedItem.counts.workspaces
                                    + " // WINDOWS " + timew.machineSavedItem.counts.windows
                                  : "READ ONLY UNTIL SAVE CHECKPOINT IS PRESSED"
                            color: Colors.cyan
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                        Row {
                            width: parent.width
                            height: 35
                            spacing: 7
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: parent.height
                                label: "OPEN SAVED METADATA"
                                labelPixelSize: 9
                                accentColor: timew.semanticColor
                                available: !!timew.machineSavedItem && !timew.machineStoreBusy
                                           && !timew.machineResolverBusy
                                onLeftClicked: timew.machineOpenSavedCheckpoint()
                            }
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: parent.height
                                label: "RESOLVE LIVE"
                                labelPixelSize: 10
                                accentColor: timew.semanticColor
                                available: !!timew.machineOpenedCheckpoint
                                           && !!timew.machineSavedItem
                                           && timew.machineOpenedCheckpoint.checkpoint.id
                                              === timew.machineSavedItem.id
                                           && !timew.machineResolverBusy
                                           && !timew.machineStoreBusy
                                           && !timew.machineCaptureBusy
                                onLeftClicked: timew.machineResolveLiveWindows()
                            }
                        }
                        GohuText {
                            width: parent.width
                            text: timew.machineStoreStatus
                            color: Colors.orange
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                        GohuText {
                            width: parent.width
                            text: timew.machineOpenedCheckpoint
                                  ? "OPENED // "
                                    + timew.machineOpenedCheckpoint.document.outputs.length
                                    + " MONITORS, "
                                    + timew.machineOpenedCheckpoint.document.workspaces.length
                                    + " WORKSPACES, "
                                    + timew.machineOpenedCheckpoint.document.windows.length
                                    + " WINDOWS"
                                  : "OPEN READS ONLY // DOES NOT CHANGE DESKTOP"
                            color: Colors.white
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                        }
                        GohuText {
                            width: parent.width
                            visible: timew.machineWindowResolution !== null
                            text: timew.machineWindowResolution
                                  ? "LIVE // CANDIDATES "
                                    + timew.machineWindowResolution.counts.candidate
                                    + " / MANUAL " + timew.machineWindowResolution.counts.manual
                                    + " / BLOCKED " + timew.machineWindowResolution.counts.blocked
                                  : ""
                            color: Colors.cyan
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        Row {
                            width: parent.width
                            height: 26
                            spacing: 5
                            visible: !!timew.machineWindowResolution
                                     && timew.machineWindowResolution.candidates.length > 0
                            ActionButton {
                                width: 37
                                height: parent.height
                                label: "<"
                                accentColor: timew.semanticColor
                                available: !!timew.machineWindowResolution
                                           && timew.machineWindowResolution.candidates.length > 1
                                onLeftClicked: timew.machineStepResolverItem(-1)
                            }
                            GohuText {
                                width: Math.max(0, parent.width - 84)
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineResolverItem
                                      ? timew.machineResolverItem.status.toUpperCase()
                                        + " // " + timew.machineResolverItem.app_id
                                        + " // " + timew.machineResolverItem.reason
                                      : ""
                                color: Colors.white
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 37
                                height: parent.height
                                label: ">"
                                accentColor: timew.semanticColor
                                available: !!timew.machineWindowResolution
                                           && timew.machineWindowResolution.candidates.length > 1
                                onLeftClicked: timew.machineStepResolverItem(1)
                            }
                        }
                        Row {
                            width: parent.width
                            height: 35
                            spacing: 8
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: parent.height
                                label: "COMPARE TO CAPTURE"
                                labelPixelSize: 9
                                accentColor: timew.semanticColor
                                available: !!timew.machineOpenedCheckpoint
                                           && !!timew.machineCapturePreview
                                           && !!timew.machineSavedItem
                                           && timew.machineOpenedCheckpoint.checkpoint.id
                                              === timew.machineSavedItem.id
                                           && !timew.machineCaptureBusy
                                           && !timew.machineStoreBusy
                                onLeftClicked: timew.machineCompareSavedToCapture()
                            }
                            ActionButton {
                                width: (parent.width - parent.spacing) / 2
                                height: parent.height
                                label: "RESTORE PREVIEW"
                                labelPixelSize: 9
                                accentColor: timew.semanticColor
                                available: !!timew.machineOpenedCheckpoint
                                           && !!timew.machineCapturePreview
                                           && !!timew.machineSavedItem
                                           && timew.machineOpenedCheckpoint.checkpoint.id
                                              === timew.machineSavedItem.id
                                           && !timew.machineCaptureBusy
                                           && !timew.machineStoreBusy
                                onLeftClicked: timew.machinePreviewRestorePlan()
                            }
                        }
                        GohuText {
                            width: parent.width
                            visible: timew.machineLayoutComparison !== null
                            text: !timew.machineLayoutComparison
                                  ? ""
                                  : timew.machineLayoutComparison.status === "unavailable"
                                  ? "COMPARE UNAVAILABLE // INVALID METADATA"
                                  : timew.machineLayoutComparison.status === "match"
                                  ? "MATCHES CURRENT CAPTURE // NO CHANGES"
                                  : "DIFFERENCES // "
                                    + timew.machineLayoutComparison.differenceCount
                                    + " (MON "
                                    + timew.machineLayoutComparison.counts.monitors
                                    + " / WS "
                                    + timew.machineLayoutComparison.counts.workspaces
                                    + " / WIN "
                                    + timew.machineLayoutComparison.counts.windows + ")"
                            color: timew.machineLayoutComparison
                                   && timew.machineLayoutComparison.status === "match"
                                   ? Colors.cyan : Colors.orange
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        Row {
                            width: parent.width
                            height: 29
                            spacing: 6
                            visible: !!timew.machineLayoutComparison
                                     && timew.machineLayoutComparison.differences.length > 0
                            ActionButton {
                                width: 43
                                height: parent.height
                                label: "<"
                                accentColor: timew.semanticColor
                                available: timew.machineLayoutComparison
                                           && timew.machineLayoutComparison.differences.length > 1
                                onLeftClicked: timew.machineStepLayoutDifference(-1)
                            }
                            GohuText {
                                width: Math.max(0, parent.width - 98)
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineLayoutDifference
                                      ? (timew.machineLayoutDifferenceIndex + 1) + " / "
                                        + timew.machineLayoutComparison.differences.length
                                        + " // " + timew.machineLayoutDifference.label
                                      : ""
                                color: Colors.white
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 43
                                height: parent.height
                                label: ">"
                                accentColor: timew.semanticColor
                                available: timew.machineLayoutComparison
                                           && timew.machineLayoutComparison.differences.length > 1
                                onLeftClicked: timew.machineStepLayoutDifference(1)
                            }
                        }
                        GohuText {
                            width: parent.width
                            visible: !!timew.machineLayoutComparison
                                     && timew.machineLayoutComparison.truncated === true
                            text: "SHOWING FIRST 40 DIFFERENCES"
                            color: Colors.orange
                            font.pixelSize: 10
                        }
                        GohuText {
                            width: parent.width
                            visible: !!timew.machineRestorePlan
                            text: !timew.machineRestorePlan ? ""
                                  : timew.machineRestorePlan.status === "unavailable"
                                  ? "RESTORE PLAN UNAVAILABLE // INVALID DATA"
                                  : "RESTORE PLAN // " + timew.machineRestorePlan.status.toUpperCase()
                                    + " // REVIEW " + timew.machineRestorePlan.counts.manual
                                    + " / AMBIG " + timew.machineRestorePlan.counts.ambiguous
                                    + " / BLOCK " + timew.machineRestorePlan.counts.blocked
                            color: timew.machineRestorePlan
                                   && timew.machineRestorePlan.status === "aligned"
                                   ? Colors.cyan : Colors.orange
                            font.pixelSize: 10
                            elide: Text.ElideRight
                        }
                        Row {
                            width: parent.width
                            height: 29
                            spacing: 6
                            visible: !!timew.machineRestorePlan
                                     && timew.machineRestorePlan.items.length > 0
                            ActionButton {
                                width: 43
                                height: parent.height
                                label: "<"
                                accentColor: timew.semanticColor
                                available: timew.machineRestorePlan
                                           && timew.machineRestorePlan.items.length > 1
                                onLeftClicked: timew.machineStepRestorePlanItem(-1)
                            }
                            GohuText {
                                width: Math.max(0, parent.width - 98)
                                anchors.verticalCenter: parent.verticalCenter
                                text: timew.machineRestorePlanItem
                                      ? (timew.machineRestorePlanIndex + 1) + " / "
                                        + timew.machineRestorePlan.items.length
                                        + " // " + timew.machineRestorePlanItem.label
                                      : ""
                                color: Colors.white
                                font.pixelSize: 10
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 43
                                height: parent.height
                                label: ">"
                                accentColor: timew.semanticColor
                                available: timew.machineRestorePlan
                                           && timew.machineRestorePlan.items.length > 1
                                onLeftClicked: timew.machineStepRestorePlanItem(1)
                            }
                        }
                        GohuText {
                            width: parent.width
                            visible: !!timew.machineRestorePlanItem
                            text: timew.machineRestorePlanItem
                                  ? timew.machineRestorePlanItem.note : ""
                            color: Colors.cyan
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                        }
                        GohuText {
                            width: parent.width
                            visible: !!timew.machineRestorePlan
                                     && timew.machineRestorePlan.truncated === true
                            text: "SHOWING FIRST 40 RESTORE REVIEW ITEMS"
                            color: Colors.orange
                            font.pixelSize: 10
                        }
                        GohuText {
                            width: parent.width
                            visible: !!timew.machineRestorePlan
                            text: "PLAN ONLY // NO ACTIONS OR RESTARTS"
                            color: Colors.orange
                            font.pixelSize: 10
                        }
                        GohuText {
                            width: parent.width
                            text: "NO SCREENSHOTS OR RESTORATION ACTIVE"
                            color: Colors.orange
                            font.pixelSize: 11
                        }
                    }

                    GohuText {
                        // The floating result sheet owns this space while it
                        // is open; the footer must not overlap its entries.
                        visible: !(timew.selectedMode === "clock"
                                   && timew.worldSearchPopupOpen)
                                 && !(timew.selectedMode === "calc"
                                      && timew.activeConverterDropdown !== "")
                        text: timew.selectedMode === "clock"
                              ? "LOCAL + WORLD // LIVE // CALC HAS CONVERTER"
                              : timew.selectedMode === "calc"
                              ? "TIME ZONE CONVERTER // READ ONLY"
                              : timew.selectedMode === "machine"
                              ? "MACHINE // LOCAL CHECKPOINTS"
                              : "FOUNDATION PREVIEW // UI ONLY"
                        color: Colors.white
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
