import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/DiagnosticComparison.js" as Compare
import "../../services/diagnostics/CpuPlusDiagnosticsPolicy.js" as Policy
import "../../components"

// UI only. Session owner survives CPU++ closing or changing pages.
Column {
    id: root
    objectName: "cpuplusDiagnosticControls"
    spacing: 6
    readonly property string selectedReport: CpuPlusDiagnostics.selectedReport
    property bool showReport: false
    readonly property var report: CpuPlusDiagnostics.selectedArchiveId
        ? CpuPlusDiagnostics.reportFor(selectedReport, CpuPlusDiagnostics.selectedArchiveId)
        : CpuPlusDiagnostics.reports[selectedReport] || null
    property bool showHistory: false
    property bool showComparison: false
    readonly property var archiveRows: CpuPlusDiagnostics.archiveStatus === "READY" && !CpuPlusDiagnostics.archiveBusy
        ? CpuPlusDiagnostics.archiveRows : []
    readonly property var beforeRecord: archiveRows.find(row => row.id === CpuPlusDiagnostics.compareBeforeId) || null
    readonly property var afterRecord: archiveRows.find(row => row.id === CpuPlusDiagnostics.compareAfterId) || null
    readonly property bool canChooseComparison: report !== null && archiveRows.some(row => row.id === report.id && row.status === "COMPLETE")
    readonly property var comparison: showComparison ? Compare.compare(beforeRecord, afterRecord, Policy.summarize) : null
    function comparisonLabel(row) {
        return row ? row.kind.toUpperCase() + " // " + row.finishedAt.slice(0, 19).replace("T", " ") + " UTC" : "NOT SELECTED / NO LONGER RETAINED";
    }
    function valueLabel(value, digits, unit, delta) {
        if (value === null) return "N/A";
        return (delta && value > 0 ? "+" : "") + value.toFixed(digits)
            + (unit ? " " + (delta && unit === "%" ? "pp" : unit) : "");
    }

    GohuText {
        width: parent.width
        text: "TROUBLESHOOT // ON DEMAND"
        color: Colors.magenta
        font.pixelSize: 12
    }
    GohuText {
        width: parent.width
        text: CpuPlusDiagnostics.feedback
        color: CpuPlusDiagnostics.busy || CpuPlusDiagnostics.faulted ? Colors.orange : Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Repeater {
        model: [
            {kind: "memory", label: "MEMORY OBSERVE // 120s"},
            {kind: "inventory", label: "SOURCE WORKLOAD SCAN"},
            {kind: "threads", label: "THREAD SAMPLE // 30s"},
            {kind: "census", label: "PROCESS CENSUS // 30s"}
        ]
        delegate: ActionButton {
            required property var modelData
            width: root.width
            height: 30
            label: modelData.label
            labelPixelSize: 10
            available: !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.faulted && !CpuPlusDiagnostics.archiveBusy
            onLeftClicked: {
                if (CpuPlusDiagnostics.request(modelData.kind)) {
                    root.showReport = false;
                }
            }
        }
    }
    ActionButton {
        width: parent.width
        height: 30
        visible: CpuPlusDiagnostics.busy
        available: CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.cancelled
        label: "STOP CAPTURE"
        onLeftClicked: CpuPlusDiagnostics.cancel()
    }
    GohuText {
        width: parent.width
        text: "Captures run outside Quickshell. Close this menu and reproduce the issue, then return here. Memory/thread targets are the newest same-user Quickshell; verify the reported PID. Source scan is not a live census. Process census reads same-user CPU, RSS and storage I/O; GPU and database-specific activity are not measured."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Row {
        width: parent.width
        spacing: 3
        Repeater {
            model: ["memory", "inventory", "threads", "census"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(0, Math.floor((root.width - 9) / 4))
                height: 27
                label: modelData === "inventory" ? "SCAN" : modelData === "memory" ? "MEM" : modelData === "threads" ? "THREAD" : "CENSUS"
                labelPixelSize: 9
                selected: root.selectedReport === modelData
                onLeftClicked: {
                    CpuPlusDiagnostics.selectLatest(modelData);
                    root.showReport = false;
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: root.report ? root.report.status + " // " + root.report.finishedAt
            + "\n" + root.report.summary : "NO CAPTURE SELECTED"
        color: root.report && root.report.status === "COMPLETE" ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
    }
    ActionButton {
        width: parent.width
        height: 28
        visible: root.report !== null && root.report.text.length > 0
        label: root.showReport ? "HIDE REPORT" : "VIEW REPORT"
        onLeftClicked: root.showReport = !root.showReport
    }
    ActionButton {
        width: parent.width
        height: 28
        visible: root.showReport && root.report !== null && root.report.text.length > 0
        label: "COPY REPORT"
        onLeftClicked: {
            reportText.selectAll();
            reportText.copy();
            reportText.deselect();
        }
    }
    TextEdit {
        id: reportText
        width: parent.width
        visible: root.showReport && root.report !== null
        height: visible ? implicitHeight : 0
        text: visible && root.report ? root.report.text : ""
        readOnly: true
        selectByMouse: true
        textFormat: TextEdit.PlainText
        wrapMode: TextEdit.Wrap
        color: Colors.white
        font.pixelSize: 10
        font.family: "monospace"
    }
    GohuText {
        width: parent.width
        text: "LOCAL ARCHIVE // " + CpuPlusDiagnostics.archiveStatus
        color: CpuPlusDiagnostics.archiveStatus === "READY" ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    ActionButton {
        width: parent.width
        height: 28
        label: root.showHistory ? "HIDE HISTORY" : "LOAD HISTORY"
        available: root.showHistory || (!CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.archiveBusy)
        onLeftClicked: {
            if (root.showHistory) root.showHistory = false;
            else if (CpuPlusDiagnostics.loadHistory()) root.showHistory = true;
        }
    }
    Repeater {
        model: root.showHistory ? CpuPlusDiagnostics.archiveRows : []
        delegate: ActionButton {
            required property var modelData
            width: root.width
            height: 30
            label: modelData.kind.toUpperCase() + " // " + modelData.finishedAt.slice(5, 16)
            labelPixelSize: 9
            selected: root.report !== null && root.report.id === modelData.id
            onLeftClicked: {
                if (CpuPlusDiagnostics.selectExactReport(modelData.kind, modelData.id)) {
                    root.showReport = false;
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: "COMPARE // SELECT A COMPLETED ARCHIVE REPORT"
        color: Colors.magenta
        font.pixelSize: 11
        wrapMode: Text.Wrap
    }
    Row {
        width: parent.width
        spacing: 4
        ActionButton {
            width: Math.max(0, (root.width - 4) / 2)
            height: 30
            label: "SET BEFORE"
            available: root.canChooseComparison
            onLeftClicked: CpuPlusDiagnostics.selectComparison("before", root.report.id)
        }
        ActionButton {
            width: Math.max(0, (root.width - 4) / 2)
            height: 30
            label: "SET AFTER"
            available: root.canChooseComparison
            onLeftClicked: CpuPlusDiagnostics.selectComparison("after", root.report.id)
        }
    }
    GohuText {
        width: parent.width
        text: "BEFORE // " + root.comparisonLabel(root.beforeRecord)
            + "\nAFTER // " + root.comparisonLabel(root.afterRecord)
        color: Colors.cyan
        font.pixelSize: 10
        wrapMode: Text.Wrap
        textFormat: Text.PlainText
    }
    ActionButton {
        width: parent.width
        height: 30
        label: root.showComparison ? "HIDE COMPARISON" : "COMPARE CAPTURES"
        available: root.showComparison || (root.beforeRecord !== null && root.afterRecord !== null)
        onLeftClicked: root.showComparison = !root.showComparison
    }
    GohuText {
        width: parent.width
        visible: root.showComparison && root.comparison !== null && root.comparison.error !== ""
        text: visible ? root.comparison.error : ""
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Repeater {
        model: root.comparison ? root.comparison.rows : []
        delegate: Column {
            required property var modelData
            width: root.width
            spacing: 2
            GohuText {
                width: parent.width
                text: modelData.label
                color: Colors.magenta
                font.pixelSize: 10
            }
            GohuText {
                width: parent.width
                text: "B " + root.valueLabel(modelData.before, modelData.digits, modelData.unit, false)
                    + "  /  A " + root.valueLabel(modelData.after, modelData.digits, modelData.unit, false)
                    + "\nCHANGE // " + root.valueLabel(modelData.delta, modelData.digits, modelData.unit, true)
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.Wrap
            }
        }
    }
    GohuText {
        width: parent.width
        visible: root.comparison !== null && root.comparison.note !== ""
        text: visible ? root.comparison.note : ""
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "Last 8 terminal captures saved locally; oldest replaced on the next save. Session captures remain available if archive write fails. No automatic uploads or privileged actions."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
