pragma Singleton

import QtQuick
import Quickshell
import "../system"

// Authoritative runtime KILL store. No widget dependency, persistence,
// or extra polling loop. Mutation primitives retain existing guarded callers.
// Shell owns service admission;
// the original snapshot, mini and detail cadences live in this module.
Scope {
    id: root

    readonly property var telemetry: sampler
    readonly property var rows: sampler.rows

    // Shell enables collection only after both consumers are constructed.
    // Demand flags are presentation inputs, never a second collector.
    property bool collectionEnabled: false
    property bool cpuVisible: false
    property bool donorResourceVisible: false
    property bool donorKillVisible: false
    property bool donorFavoritesVisible: false
    property bool donorFavoriteTasksVisible: false
    property bool donorCombiVisible: false
    property bool hasTaskFavorites: false

    readonly property bool miniProbeNeeded:
        cpuVisible || donorKillVisible || donorFavoritesVisible
    readonly property int snapshotInterval: snapshotCadence(cpuVisible,
        donorResourceVisible, donorKillVisible, donorFavoriteTasksVisible,
        donorCombiVisible, histories.taskMiniPreloadSnapshots,
        histories.taskMiniPreloadTarget, hasTaskFavorites)
    readonly property var refreshAfterActionTimer: afterAction

    // Single custody for existing runtime locks, process mutation primitives
    // and the serialized limit queue. No policy or execution changes in K3a.
    readonly property var safety: safetyState
    readonly property var control: controlBackend
    readonly property var limits: limitBackend
    // One long-lived execution lifecycle. Transitional donor supplies
    // candidate policy and legacy confirmation presentation, not execution state.
    property var donorHunterHost: null
    property var donorHunterFavorites: null
    readonly property var hunterExecutor: hunterExecution
    readonly property var hunterOperation: hunterController
    HunterOperationController {
        id: hunterController
        host: root.donorHunterHost
        favoriteStoreObject: root.donorHunterFavorites
        executor: hunterExecution
        refreshTimer: afterAction
    }
    HunterExecutor {
        id: hunterExecution
        onResultReady: function(result) { hunterController.applyResult(result); }
        onFinished: hunterController.finish()
        onErrorRaised: function(message) {
            console.log("AppControl: HUNTER", String(message || ""));
        }
    }

    // Shared individual action authority. Only the transitional legacy
    // confirmation UI selects donorTask and contributes its bulk exclusion.
    property var donorTask: null
    property bool donorActionBlocked: false
    readonly property var presentation: actionPresentation
    readonly property var actionGate: guardedActions
    ProcessPresentationController {
        id: actionPresentation
        safetyService: root.safety
        limitsService: root.limits
        controlService: root.control
        currentTask: root.donorTask
        taskRows: root.rows
        onRefreshRequested: afterAction.restart()
    }
    AppControlHubActionGate {
        id: guardedActions
        ownerRows: root.rows
        safetyOwner: root.safety
        presentationOwner: root.presentation
        controlOwner: root.control
        limitsOwner: root.limits
        refreshOwner: root.refreshAfterActionTimer
        bulkBlocked: root.donorActionBlocked
    }

    TaskSafety { id: safetyState }
    ProcessControl { id: controlBackend }
    ProcessLimits {
        id: limitBackend
        onRefreshRequested: afterAction.restart()
    }

    // CPU++ lock projection and toggles share the same in-memory TaskSafety.
    // Keep sticky/per-action methods off the Hub-facing gateway interface.
    function lockModeForIdentity(pid, birth, name, action, localOnly) {
        const row = actionGate.exactRow(pid, birth, name);
        if (!row) return "";
        if (!action) return localOnly ? "" : safety.dangerUnlockMode(row);
        return localOnly ? safety.dangerActionLocalUnlockMode(row, action)
                         : safety.dangerActionUnlockMode(row, action);
    }

    function toggleLockForIdentity(pid, birth, name, action, sticky) {
        if (actionGate.pending || actionGate.busy || actionGate.bulkBlocked)
            return false;
        const row = actionGate.exactRow(pid, birth, name);
        if (!row || !safety.requiresDangerUnlock(row) || typeof sticky !== "boolean")
            return false;
        if (action !== "" && ["kill", "restart", "freeze", "limit"].indexOf(action) === -1)
            return false;
        if (!action && !sticky) return actionGate.toggleOneShotUnlock(pid, birth, name);
        if (!action) safety.toggleDangerStickyUnlock(row);
        else if (sticky) safety.toggleDangerActionStickyUnlock(row, action);
        else safety.toggleDangerActionUnlock(row, action);
        return true;
    }

    // One immutable recipient review. Candidate selection and final execution
    // admission remain with the existing donor until Hunter custody moves.
    property var cpuBulkReview: null

    function captureCpuBulkReview(kind, metric, visibility, captures) {
        if (cpuBulkReview || actionGate.pending || actionGate.busy || actionGate.bulkBlocked)
            return null;
        if (!Array.isArray(captures) || !captures.length
                || new Set(captures.map(t => t.pid)).size !== captures.length)
            return null;
        const targets = Object.freeze(captures.map(t => Object.freeze(t)));
        const label = kind === "kill-all" ? "ALL ELIGIBLE PROCESSES"
            : kind === "kill-mice" ? "DETACHED IDLE LEAVES"
            : ["COMBI","CPU","MEMORY","I/O","AGE"][metric] + " HOGS";
        cpuBulkReview = Object.freeze({kind:kind, metric:metric, visibility:visibility,
            label:label, targets:targets});
        return cpuBulkReview;
    }

    function releaseCpuBulkReview(review) {
        if (!review || cpuBulkReview !== review) return false;
        cpuBulkReview = null;
        return true;
    }

    function snapshotCadence(cpu, resource, kill, taskFavorites, combi,
                             preload, target, favorites) {
        if (cpu) return 600;
        if (resource) return 900;
        if (kill || taskFavorites) return 600;
        if (combi) return 1800;
        if (preload < target) return 700;
        return favorites ? 1400 : 3200;
    }

    function refreshSnapshot() {
        if (collectionEnabled) sampler.refreshSnapshot();
    }

    function miniRequestForRows(sourceRows) {
        const request = [];
        for (let i = 0; i < sourceRows.length; i++) {
            const entry = sourceRows[i];
            const pid = Number(entry && entry.pid || 0);
            if (pid <= 1) continue;
            request.push({
                pid: pid,
                comm: String(entry.comm || entry.name || entry.label || "PROCESS"),
                fallbackCpu: Number(entry.cpuInstant !== undefined
                    ? entry.cpuInstant : entry.cpu || 0)
            });
        }
        return request;
    }

    function refreshMiniProbe() {
        if (!collectionEnabled || !miniProbeNeeded || sampler.miniProbeLoading)
            return;
        sampler.refreshMiniProbe(miniRequestForRows(rows));
    }

    Timer {
        id: taskManagerRefreshTimer
        interval: root.snapshotInterval
        repeat: true
        running: root.collectionEnabled
        triggeredOnStart: true
        onTriggered: root.refreshSnapshot()
    }

    Timer {
        id: taskMiniDisplayTimer
        interval: 1200
        repeat: true
        running: root.collectionEnabled && root.miniProbeNeeded
        triggeredOnStart: true
        onTriggered: root.refreshMiniProbe()
    }

    Timer {
        id: afterAction
        interval: 320
        repeat: false
        onTriggered: root.refreshSnapshot()
    }

    // Both consumers read the authoritative graph-history state.
    // Transitional donor bindings select visibility and its legacy detail mode.
    property bool graphVisible: false
    property int graphMetricMode: 0
    readonly property var graphState: histories
    readonly property var graphController: graph
    readonly property var hunterPresentation: hunter
    readonly property var detailSession: selectedDetail

    ProcessPresentationState {
        id: histories
        taskMiniHistoryKeepImmutable: root.graphVisible
    }

    HunterPresentation {
        id: hunter
        presentationState: histories
        metricMode: root.graphMetricMode
    }

    TaskGraphController {
        id: graph
        presentationState: histories
        telemetry: sampler
        hunterPresentation: hunter
        taskRows: root.rows
    }

    KillDetailSession {
        id: selectedDetail
        graph: root.graphController
        state: histories
        rows: root.rows
    }

    // Publication never requires a widget. Transitional observers preserve
    // the donor's ordering, selection and opt-in diagnostic stage markers.
    property bool snapshotTraceEnabled: false
    property bool miniTraceEnabled: false
    property int snapshotTraceSequence: 0
    signal snapshotStarted(var rows)
    signal snapshotOrdering(var rows)
    signal snapshotStage(string stage, int sequence, double startMs, int rowCount)
    signal snapshotPublished(var rows, int sequence)
    signal miniStage(string stage, double startMs)

    function publishSnapshot(input) {
        const snapshotRows = Array.isArray(input) ? input : [];
        const sequence = snapshotTraceEnabled ? ++snapshotTraceSequence : 0;
        const count = snapshotRows.length;
        snapshotStarted(snapshotRows);

        if (!miniProbeNeeded) {
            let started = sequence ? Date.now() : 0;
            graph.updateMiniCpuHistories(snapshotRows);
            if (sequence) snapshotStage("cpu-history", sequence, started, count);
            started = sequence ? Date.now() : 0;
            graph.updateMiniHunterMetricHistories(snapshotRows);
            if (sequence) snapshotStage("hunter-history", sequence, started, count);
            started = sequence ? Date.now() : 0;
            histories.taskMiniHistoryRevision += 1;
            histories.taskMiniDisplayRevision += 1;
            if (sequence) snapshotStage("history-revisions", sequence, started, count);
        }

        let started = sequence ? Date.now() : 0;
        snapshotOrdering(snapshotRows);
        if (sequence) snapshotStage("task-order", sequence, started, count);
        started = sequence ? Date.now() : 0;
        sampler.rows = snapshotRows;
        if (sequence) snapshotStage("task-rows", sequence, started, count);
        histories.taskMiniPreloadSnapshots = Math.min(
            histories.taskMiniPreloadTarget, histories.taskMiniPreloadSnapshots + 1);
        snapshotPublished(snapshotRows, sequence);
    }

    function publishMiniSamples(input) {
        const samples = Array.isArray(input) ? input : [];
        if (!samples.length) return;
        const timed = miniTraceEnabled;
        let started = timed ? Date.now() : 0;
        graph.updateMiniCpuHistories(samples);
        if (timed) miniStage("mini-cpu-history", started);
        started = timed ? Date.now() : 0;
        graph.updateMiniHunterMetricHistories(samples);
        if (timed) miniStage("mini-hunter-history", started);
        started = timed ? Date.now() : 0;
        histories.taskMiniHistoryRevision += 1;
        histories.taskMiniDisplayRevision += 1;
        if (timed) miniStage("mini-history-revisions", started);
    }

    ProcessTelemetry {
        id: sampler
        onSnapshotReady: function(rows) { root.publishSnapshot(rows); }
        onMiniProbeReady: function(rows) { root.publishMiniSamples(rows); }
        onDetailProbeReady: function(sample) { selectedDetail.accept(sample); }
    }
}
