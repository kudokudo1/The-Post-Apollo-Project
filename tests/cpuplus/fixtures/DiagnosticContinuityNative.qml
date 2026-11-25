import QtQuick
import QtQuick.Window
import Quickshell
import qs.services.diagnostics
import "widgets/cpuplus"

ShellRoot {
    id: root
    // Reference remains alive while the memory pane is unloaded.
    readonly property var diagnosticSessionOwner: CpuPlusDiagnostics
    property int phase: 0
    property int ticks: 0
    property bool done: false
    property bool paneActive: true
    property int completions: 0
    property string completedId: ""
    Connections {
        target: CpuPlusDiagnostics
        function onCaptureFinished(job, reportId) {
            if (job === "inventory") {
                root.completions += 1;
                root.completedId = reportId;
            }
        }
    }

    function findItem(item, name) {
        if (!item) return null;
        if (item.objectName === name) return item;
        for (const child of item.children || []) {
            const found = findItem(child,name);
            if (found) return found;
        }
        return null;
    }
    function check(ok, message) {
        if (!ok) {
            console.error("CPU_DIAG_NATIVE_FAIL // " + message);
            done = true;
            Qt.quit();
        }
        return ok;
    }
    Window {
        width: 320
        height: 620
        visible: true
        Loader {
            id: pane
            anchors.fill: parent
            active: root.paneActive
            sourceComponent: CpuPlusMemoryActuatorPane {}
        }
    }
    Timer {
        interval: 100
        repeat: true
        running: !root.done
        onTriggered: {
            if (++root.ticks > 150) {
                root.check(false, "timeout // " + CpuPlusDiagnostics.feedback);
                return;
            }
            if (root.phase === 0 && pane.item) {
                pane.item.selectMenu(4);
                if (!root.check(pane.item.page === "DIAG", "select DIAG")) return;
                if (!root.check(CpuPlusDiagnostics.request("inventory"), "start fixture scan")) return;
                if (!root.check(CpuPlusDiagnostics.busy, "capture did not enter busy")) return;
                root.paneActive = false;
                root.phase = 1;
                return;
            }
            if (root.phase === 1) {
                if (!root.check(!pane.item, "pane was not destroyed")) return;
                if (!root.check(CpuPlusDiagnostics.busy, "capture lost when pane unloaded")) return;
                root.paneActive = true;
                root.phase = 2;
                return;
            }
            if (root.phase === 2 && pane.item) {
                if (!root.check(pane.item.page === "DIAG", "reopened on wrong page")) return;
                if (!root.check(CpuPlusDiagnostics.selectedReport === "inventory", "report selection lost")) return;
                pane.item.selectMenu(1);
                if (!root.check(pane.item.page === "POL", "switch to POL")) return;
                root.paneActive = false;
                root.phase = 3;
                return;
            }
            if (root.phase === 3) {
                if (CpuPlusDiagnostics.busy || CpuPlusDiagnostics.archiveBusy) return;
                const report = CpuPlusDiagnostics.reports.inventory;
                if (!root.check(report && report.status === "COMPLETE",
                                "scan failed // " + CpuPlusDiagnostics.feedback)) return;
                if (!root.check(report.summary.indexOf("826 files") >= 0, "wrong report")) return;
                if (!root.check(root.completions === 1 && root.completedId === report.id,
                                "terminal signal or capture identity mismatch")) return;
                if (!root.check(CpuPlusDiagnostics.reportFor("inventory", report.id) === report
                                && CpuPlusDiagnostics.reportFor("inventory", "stale") === null,
                                "exact report resolution")) return;
                if (!root.check(CpuPlusDiagnostics.archiveStatus === "READY"
                        && CpuPlusDiagnostics.archiveRows.length === 1
                        && CpuPlusDiagnostics.archiveRows[0].id === report.id,
                        "archive save receipt")) return;
                if (!root.check(CpuPlusDiagnostics.loadHistory(), "archive reload request")) return;
                root.phase = 5;
                return;
            }
            if (root.phase === 5) {
                if (CpuPlusDiagnostics.archiveBusy) return;
                if (!root.check(CpuPlusDiagnostics.archiveStatus === "READY"
                        && CpuPlusDiagnostics.archiveRows[0].id === root.completedId,
                        "archive reload receipt")) return;
                root.paneActive = true;
                root.phase = 4;
                return;
            }
            if (root.phase === 4 && pane.item) {
                if (!root.check(pane.item.page === "POL", "non-DIAG page continuity")) return;
                pane.item.selectMenu(4);
                if (!root.check(CpuPlusDiagnostics.reports.inventory.status === "COMPLETE",
                                "completed report lost")) return;
                if (!root.check(CpuPlusDiagnostics.selectedReport === "inventory", "wrong report after reopen")) return;
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                if (!ui) return;
                const one = {event:"memory",pid:12,startTicks:99,tsMs:1000,cpuTicks:100,cpuPct:null,sampleIntervalMs:null,
                    memoryKiB:{Rss:2097152,Pss:1048576,Pss_Anon:524288,Pss_File:262144,Pss_Shmem:262144,
                        Private_Dirty:524288,Swap:131072,SwapPss:65536},pssPlusSwapPssKiB:1114112};
                const two = Object.assign({},one,{tsMs:11000,cpuTicks:110,cpuPct:1,sampleIntervalMs:10000,
                    memoryKiB:Object.assign({},one.memoryKiB,{Rss:3145728,Pss:1572864,Private_Dirty:1048576}),
                    pssPlusSwapPssKiB:1638400});
                const terminal = {event:"complete",pid:12,startTicks:99};
                // Isolated presentation fixture only; do not request another observer or archive a fabricated report.
                const report = {id:"synthetic-memory",status:"COMPLETE",summary:"TEST ONLY",
                    text:[one,two,terminal].map(row=>JSON.stringify(row)).join("\n"),finishedAt:"2026-11-24T12:00:00.000Z"};
                CpuPlusDiagnostics.reports = Object.assign({},CpuPlusDiagnostics.reports,{memory:report});
                CpuPlusDiagnostics.selectLatest("memory");
                root.phase = 6;
                return;
            }
            if (root.phase === 6 && pane.item) {
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                const breakdown = root.findItem(pane.item,"cpuplusMemoryBreakdown");
                if (!ui || !breakdown) return;
                if (!root.check(breakdown.visible && ui.memoryDetails
                    && ui.memoryDetails.rows.length === 5 && ui.memoryDetails.rows[1].change === 524288
                    && !CpuPlusDiagnostics.busy && root.completions === 1,
                    "historical memory presentation without new capture")) return;
                CpuPlusDiagnostics.selectLatest("inventory");
                root.phase = 7;
                return;
            }
            if (root.phase === 7 && pane.item) {
                const ui = root.findItem(pane.item,"cpuplusDiagnosticControls");
                const breakdown = root.findItem(pane.item,"cpuplusMemoryBreakdown");
                if (!root.check(ui && breakdown && !breakdown.visible && ui.memoryDetails === null,
                    "no stale memory presentation after report change")) return;
                console.log("CPU_DIAG_NATIVE_PASS");
                root.done = true;
                Qt.quit();
            }
        }
    }
}
