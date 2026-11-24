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
                if (CpuPlusDiagnostics.busy) return;
                const report = CpuPlusDiagnostics.reports.inventory;
                if (!root.check(report && report.status === "COMPLETE",
                                "scan failed // " + CpuPlusDiagnostics.feedback)) return;
                if (!root.check(report.summary.indexOf("826 files") >= 0, "wrong report")) return;
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
                console.log("CPU_DIAG_NATIVE_PASS");
                root.done = true;
                Qt.quit();
            }
        }
    }
}
