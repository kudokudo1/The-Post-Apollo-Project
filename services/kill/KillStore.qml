pragma Singleton

import QtQuick
import Quickshell
import "../system"

// Authoritative runtime acquisition store. No widget dependency, persistence,
// process mutation, or extra polling loop. The original detail cadence is
// now here; the temporary donor adapter still drives snapshot/mini cadence.
Scope {
    id: root

    readonly property var telemetry: sampler
    readonly property var rows: sampler.rows

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
