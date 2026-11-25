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
    readonly property var memoryDetails: memoryBreakdown(selectedReport, report)
    function memoryBreakdown(selected, report) {
        // Presentation only: reuse the existing completed JSONL capture.
        if (selected !== "memory" || !report || report.status !== "COMPLETE"
                || typeof report.text !== "string" || report.text.length > 65536) return null;
        try {
            const records = report.text.trim().split("\n").map(line => JSON.parse(line));
            const final = records.pop();
            const keys = ["Rss","Pss","Pss_Anon","Pss_File","Pss_Shmem","Private_Dirty","Swap","SwapPss"];
            const count = value => Number.isSafeInteger(value) && value >= 0;
            if (!final || final.event !== "complete" || !count(final.pid) || final.pid === 0
                    || !count(final.startTicks) || records.length < 1 || records.length > 361)
                return null;
            let duration = 0;
            for (let i=0; i<records.length; ++i) {
                const row = records[i];
                if (!row || row.event !== "memory" || row.pid !== final.pid
                        || row.startTicks !== final.startTicks || !row.memoryKiB
                        || !keys.every(key => count(row.memoryKiB[key]))
                        || !count(row.tsMs) || !count(row.cpuTicks)
                        || !count(row.pssPlusSwapPssKiB)
                        || row.pssPlusSwapPssKiB !== row.memoryKiB.Pss + row.memoryKiB.SwapPss
                        || row.memoryKiB.Pss > row.memoryKiB.Rss
                        || row.memoryKiB.Private_Dirty > row.memoryKiB.Rss
                        || row.memoryKiB.SwapPss > row.memoryKiB.Swap)
                    return null;
                if (i === 0) {
                    if (row.sampleIntervalMs !== null || row.cpuPct !== null) return null;
                } else {
                    if (!count(row.sampleIntervalMs) || row.sampleIntervalMs === 0
                            || typeof row.cpuPct !== "number" || !Number.isFinite(row.cpuPct) || row.cpuPct < 0
                            || row.cpuTicks < records[i-1].cpuTicks) return null;
                    duration += row.sampleIntervalMs;
                    if (!count(duration)) return null;
                }
            }
            const first = records[0].memoryKiB, last = records[records.length-1].memoryKiB;
            const labels = [
                ["RSS","Rss"], ["PSS","Pss"], ["PRIVATE DIRTY","Private_Dirty"],
                ["SWAP","Swap"], ["SWAP PSS","SwapPss"]
            ];
            return {pid:final.pid, startTicks:final.startTicks, samples:records.length,
                durationMs:duration, rows:labels.map(pair => ({label:pair[0],
                    first:first[pair[1]], peak:Math.max(...records.map(row=>row.memoryKiB[pair[1]])),
                    last:last[pair[1]], change:records.length > 1 ? last[pair[1]]-first[pair[1]] : null})),
                anon:last.Pss_Anon, file:last.Pss_File, shmem:last.Pss_Shmem};
        } catch (_) { return null; }
    }

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
            {kind: "census", label: "PROCESS CENSUS // 30s"},
            {kind: "storage", label: "STORAGE OBSERVE // 30s"}
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
        text: "Captures run outside Quickshell. Close this menu and reproduce the issue, then return here. Memory/thread targets are the newest same-user Quickshell; verify the reported PID. Source scan is not a live census. Process census reads same-user CPU, RSS and storage I/O; Storage observe checks fixed file metadata only; not writer identity, SQL activity or bytes written. GPU is not measured."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Row {
        width: parent.width
        spacing: 3
        Repeater {
            model: ["memory", "inventory", "threads", "census", "storage"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(0, Math.floor((root.width - 12) / 5))
                height: 27
                label: modelData === "inventory" ? "SCAN" : modelData === "memory" ? "MEM" : modelData === "threads" ? "THREAD" : modelData === "census" ? "CENSUS" : "STORE"
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
    Column {
        id: memoryInstrument
        objectName: "cpuplusMemoryBreakdown"
        width: parent.width
        spacing: 4
        visible: root.selectedReport === "memory" && root.report !== null
        GohuText {
            width: parent.width
            text: "QUICKSHELL // CAPTURE BREAKDOWN"
            color: Colors.magenta
            font.pixelSize: 11
        }
        GohuText {
            width: parent.width
            text: root.memoryDetails
                ? "PID " + root.memoryDetails.pid + " // " + root.memoryDetails.samples
                    + " SAMPLES // " + (root.memoryDetails.durationMs / 1000).toFixed(1) + " s"
                : "COMPLETE MEMORY BREAKDOWN UNAVAILABLE"
            color: root.memoryDetails ? Colors.cyan : Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: root.memoryDetails ? root.memoryDetails.rows : []
            delegate: Rectangle {
                required property var modelData
                width: memoryInstrument.width
                height: detailBody.implicitHeight + 8
                color: Colors.black
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: detailBody
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 4
                    spacing: 2
                    GohuText {
                        width: parent.width
                        text: modelData.label + " // " + (modelData.last / 1048576).toFixed(3) + " GiB"
                        color: Colors.cyan
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "START " + (modelData.first / 1048576).toFixed(3)
                            + " / PEAK " + (modelData.peak / 1048576).toFixed(3) + " GiB"
                            + "\nCHANGE // " + (modelData.change === null ? "N/A"
                                : (modelData.change > 0 ? "+" : "") + (modelData.change / 1024).toFixed(1) + " MiB")
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
        GohuText {
            width: parent.width
            visible: root.memoryDetails !== null
            text: root.memoryDetails ? "FINAL PSS // ANON " + (root.memoryDetails.anon / 1048576).toFixed(3)
                + " / FILE " + (root.memoryDetails.file / 1048576).toFixed(3)
                + " / SHMEM " + (root.memoryDetails.shmem / 1048576).toFixed(3) + " GiB" : ""
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "HISTORICAL CAPTURE // NOT LIVE\nRSS includes shared pages; PSS apportions shared pages. Private dirty is not total private memory. GPU memory and component attribution are unavailable. Growth alone does not prove a leak."
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
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
