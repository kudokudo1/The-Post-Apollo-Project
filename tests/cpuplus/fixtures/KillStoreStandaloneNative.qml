import QtQuick
import Quickshell
import "services/kill" as KillBackend

// No widget, real process probe or process mutation. Fixture timer only.
ShellRoot {
    id: root
    QtObject {
        id: first
        readonly property var store: KillBackend.KillStore
        readonly property var rows: store.rows
        readonly property var graphState: store.graphState
    }
    QtObject {
        id: second
        readonly property var store: KillBackend.KillStore
        readonly property var rows: store.rows
        readonly property var graphState: store.graphState
    }
    // Independent synthetic graph controller: never launches a real probe.
    property var witnessRows: [
        {_taskRecord:true,pid:4321,startTicks:10,comm:"first"},
        {_taskRecord:true,pid:4322,startTicks:20,comm:"second"}
    ]
    QtObject {
        id: witnessState
        property int taskHistoryPid: 0
    }
    QtObject {
        id: witnessGraph
        property int clears: 0
        property int accepted: 0
        function clearDetailHistory() { clears++; witnessState.taskHistoryPid=0; }
        function miniCpuHistory(entry) { return []; }
        function resetForSelection(entry, preload, forceReset) { witnessState.taskHistoryPid=entry.pid; }
        function refreshDetailProbe(entry) {}
        function applyDetailProbe(sample, entry) { accepted++; }
    }
    KillBackend.KillDetailSession {
        id: witness
        graph: witnessGraph
        state: witnessState
        rows: root.witnessRows
    }
    function verifySession() {
        const a=witnessRows[0], b=witnessRows[1];
        witness.selectDonor(a);
        witness.donorActive=true;
        if (!witness.matches(a) || witness.matches(b)) return false;
        witness.setCpuActive(true);
        witness.selectCpu(a);
        if (!witness.matches(a)) return false;
        const same=witnessGraph.clears;
        witness.selectCpu(a);
        if (witnessGraph.clears!==same) return false;
        witness.selectCpu(b);
        if (!witness.matches(b) || witness.matches(a)) return false;
        if (witness.accept({pid:a.pid,startTicks:a.startTicks})) return false;
        if (witness.accept({pid:b.pid,startTicks:b.startTicks+1})) return false;
        if (!witness.accept({pid:b.pid,startTicks:b.startTicks}) || witnessGraph.accepted!==1) return false;
        const reused={_taskRecord:true,pid:b.pid,startTicks:21,comm:b.comm};
        witnessRows=[a,reused];
        if (witness.activeKey || witness.accept({pid:b.pid,startTicks:b.startTicks})) return false;
        witness.selectCpu(reused);
        if (!witness.matches(reused) || witness.matches(b)) return false;
        if (witness.accept({pid:b.pid,startTicks:b.startTicks})) return false;
        witness.setCpuActive(false);
        return witness.matches(a) && !witness.matches(reused)
            && witnessState.taskHistoryPid===a.pid && witnessGraph.accepted===1;
    }
    // Run after the shell event loop starts, not during component loading.
    Timer {
        interval: 100
        running: true
        repeat: false
        onTriggered: root.verifyStore()
    }
    function verifyStore() {
        const sample = [{_taskRecord: true, pid: 4321, startTicks: 98765,
            comm: "synthetic", cpuInstant: 31, rss: 2048, mem: 3, elapsed: "00:05"}];
        first.store.graphVisible = true;
        first.store.publishSnapshot(sample);
        first.store.graphController.updateMiniCpuHistories(sample);
        first.store.graphController.updateMiniHunterMetricHistories(sample);
        first.graphState.taskMiniDisplayRevision += 1;
        const next = [{_taskRecord: true, pid: 4321, startTicks: 98765,
            comm: "synthetic", cpuInstant: 52, rss: 3072, mem: 4, elapsed: "00:06"}];
        const previous = second.graphState.taskMiniCpuHistories["pid:4321"];
        first.store.graphController.updateMiniCpuHistories(next);
        first.store.graphController.updateMiniHunterMetricHistories(next);
        first.graphState.taskMiniDisplayRevision += 1;
        if (!verifySession()
                || first.store !== second.store
                || first.store.telemetry !== second.store.telemetry
                || first.graphState !== second.graphState
                || first.store.graphController !== second.store.graphController
                || previous.length !== 1 || previous[0] !== 31
                || second.graphState.taskMiniCpuHistories["pid:4321"].length !== 2
                || second.graphState.taskMiniCpuHistories["pid:4321"][1] !== 52
                || second.graphState.taskMiniHunterMetricHistories["mem:pid:4321"][1] !== 3
                || second.graphState.taskMiniDisplayRevision !== 2
                || first.rows.length !== 1 || second.rows.length !== 1
                || first.rows[0].startTicks !== second.rows[0].startTicks
                || first.store.telemetry.snapshotLoading
                || first.store.telemetry.miniProbeLoading
                || first.store.telemetry.detailProbeLoading) {
            console.error("KILL_STORE_NATIVE_FAIL");
        } else {
            console.log("KILL_STORE_NATIVE_PASS");
        }
        Qt.quit();
    }
}
