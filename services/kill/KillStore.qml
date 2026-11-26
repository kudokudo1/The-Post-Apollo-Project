pragma Singleton

import QtQuick
import Quickshell
import "../system"

// Authoritative runtime acquisition store. No widget dependency, persistence,
// process mutation, or extra polling loop. Shell owns service admission;
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

    function publishSnapshot(rows) {
        sampler.rows = Array.isArray(rows) ? rows : [];
    }

    ProcessTelemetry {
        id: sampler
        onDetailProbeReady: function(sample) { selectedDetail.accept(sample); }
    }
}
