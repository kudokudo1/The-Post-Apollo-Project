import QtQuick
import Quickshell
import "services/kill" as KillBackend
import qs.services.favorites

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
    // Only in-memory lock operations on synthetic identities; never call
    // ProcessControl or ProcessLimits mutation methods.
    function verifyControlCustody() {
        const old={pid:4321,startTicks:98765,comm:"sway",user:"synthetic"};
        const same={pid:4321,startTicks:98765,comm:"sway",user:"synthetic"};
        const reused={pid:4321,startTicks:98766,comm:"sway",user:"synthetic"};
        const unknown={pid:4321,startTicks:0,comm:"sway",user:"synthetic"};
        const safety=first.store.safety;
        // Collection is disabled in the standalone scene. A synthetic
        // capture must not arm the executor even with the canonical policy.
        first.store.hunterOperation.start("kill-all", [{
            pid:4321,startTicks:98765,name:"sway",identity:"synthetic"}],true);
        if (safety !== second.store.safety
                || first.store.control !== second.store.control
                || first.store.limits !== second.store.limits
                || first.store.hunterExecutor !== second.store.hunterExecutor
                || first.store.hunterExecutor.running
                || first.store.hunterExecutor.expectedTarget !== null
                || first.store.hunterExecutor.completionVerified
                || first.store.hunterOperation !== second.store.hunterOperation
                || first.store.hunterOperation.phase !== "idle"
                || first.store.hunterOperation.host !== null
                || first.store.hunterOperation.policyOwner !== first.store
                || first.store.hunterOperation.policyReady
                || first.store.windowInventory !== second.store.windowInventory
                || first.store.windowInventory.loading || first.store.windowInventory.settled
                || first.store.hunterVisibleWindows !== null
                || first.store.hunterOperation.favoriteStoreObject !== FavoritesStore
                || first.store.favoriteStore !== second.store.favoriteStore
                || !safety.requiresDangerUnlock(old)
                || first.store.limits.applyLoading
                || first.store.limits.activeRequest !== null
                || first.store.limits.queuedRequest !== null) return false;
        safety.toggleDangerStickyUnlock(old);
        if (second.store.safety.dangerUnlockMode(same)!=="sticky"
                || safety.dangerUnlockMode(reused)!==""
                || safety.dangerUnlockMode(unknown)!=="") return false;
        safety.toggleDangerUnlock(old);
        safety.toggleDangerActionUnlock(old,"freeze");
        if (second.store.safety.dangerActionUnlockMode(same,"freeze")!=="once"
                || safety.dangerActionUnlockMode(reused,"freeze")!=="") return false;
        safety.relockDangerAction(same,"freeze");
        return safety.dangerActionUnlockMode(same,"freeze")==="";
    }

    // No confirm() or probe execution: only prepare/cancel and refusal
    // on synthetic process identities inside the isolated singleton.
    function verifyActionGateway() {
        const gate=first.store.actionGate;
        const other=second.store.actionGate;
        if (gate !== other || gate.presentationOwner !== first.store.presentation
                || gate.pending || gate.busy || !first.rows.length) return false;
        const row=first.rows[0], pid=row.pid, birth=row.startTicks, name=row.comm;
        if (gate.prepare(pid,birth+1,name,"end",0)) return false;
        first.store.donorActionBlocked=true;
        const refused=!gate.prepare(pid,birth,name,"end",0);
        first.store.donorActionBlocked=false;
        if (!refused || !gate.prepare(pid,birth,name,"end",0)) return false;
        const pending=gate.pending;
        if (!pending || other.pending !== pending || other.busy
                || other.prepare(pid,birth,name,"restart",0)) return false;
        return other.cancel() && !gate.pending && !gate.busy
            && gate.feedback==="CANCELLED // NO ACTION";
    }

    function verifyStore() {
        const sample = [{_taskRecord: true, pid: 4321, startTicks: 98765,
            comm: "synthetic", cpuInstant: 31, rss: 2048, mem: 3, elapsed: "00:05"}];
        first.store.cpuVisible = true;
        const cpuGraphDemand = first.store.graphVisible
            && first.graphState.taskMiniHistoryKeepImmutable
            && !first.store.donorGraphVisible;
        // Exercise the real signal route with no donor attached, no probe.
        first.store.telemetry.snapshotReady(sample);
        const next = [{_taskRecord: true, pid: 4321, startTicks: 98765,
            comm: "synthetic", cpuInstant: 52, rss: 3072, mem: 4, elapsed: "00:06"}];
        const previous = second.graphState.taskMiniCpuHistories["pid:4321"];
        first.store.telemetry.miniProbeReady(next);
        // Real singleton remains disarmed throughout this synthetic test.
        first.store.cpuVisible=true;
        const cpuCadence=first.store.snapshotInterval===600 && first.store.miniProbeNeeded;
        first.store.cpuVisible=false;
        const idleGraphDemand = !first.store.graphVisible
            && !first.graphState.taskMiniHistoryKeepImmutable;
        first.store.donorGraphVisible=true;
        const donorGraphDemand = first.store.graphVisible
            && first.graphState.taskMiniHistoryKeepImmutable;
        first.store.donorGraphVisible=false;
        first.store.donorResourceVisible=true;
        const resourceCadence=first.store.snapshotInterval===900 && !first.store.miniProbeNeeded;
        first.store.donorResourceVisible=false;
        first.store.donorFavoritesVisible=true;
        first.store.donorCombiVisible=true;
        const combiCadence=first.store.snapshotInterval===1800 && first.store.miniProbeNeeded;
        first.store.donorFavoritesVisible=false;
        first.store.donorCombiVisible=false;
        if (!verifyActionGateway() || !verifyControlCustody() || !verifySession() || !cpuCadence || !resourceCadence || !combiCadence
                || !cpuGraphDemand || !idleGraphDemand || !donorGraphDemand
                || first.store.collectionEnabled || first.store !== second.store
                || first.store.telemetry !== second.store.telemetry
                || first.graphState !== second.graphState
                || first.store.graphController !== second.store.graphController
                || previous.length !== 1 || previous[0] !== 31
                || second.graphState.taskMiniCpuHistories["pid:4321"].length !== 2
                || second.graphState.taskMiniCpuHistories["pid:4321"][1] !== 52
                || second.graphState.taskMiniHunterMetricHistories["mem:pid:4321"][1] !== 3
                || second.graphState.taskMiniDisplayRevision !== 2
                || second.graphState.taskMiniHistoryRevision !== 2
                || second.graphState.taskMiniPreloadSnapshots !== 1
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
