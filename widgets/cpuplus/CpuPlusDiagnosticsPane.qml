import QtQuick
import qs.services.diagnostics
import "../../components"

// UI only. Session owner survives CPU++ closing or changing pages.
Column {
    id: root
    objectName: "cpuplusDiagnosticControls"
    spacing: 6
    readonly property string selectedReport: CpuPlusDiagnostics.selectedReport
    property bool showReport: false
    readonly property var report: CpuPlusDiagnostics.reports[selectedReport] || null

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
            {kind: "threads", label: "THREAD SAMPLE // 30s"}
        ]
        delegate: ActionButton {
            required property var modelData
            width: root.width
            height: 30
            label: modelData.label
            labelPixelSize: 10
            available: !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.faulted
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
        text: "Captures run outside Quickshell. Close this menu and reproduce the issue, then return here. Memory/thread targets are the newest same-user Quickshell; verify the reported PID. Source scan is not a live census."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
    Row {
        width: parent.width
        spacing: 3
        Repeater {
            model: ["memory", "inventory", "threads"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(0, Math.floor((root.width - 6) / 3))
                height: 27
                label: modelData === "inventory" ? "SCAN" : modelData === "memory" ? "MEM" : "THREAD"
                labelPixelSize: 9
                selected: root.selectedReport === modelData
                onLeftClicked: {
                    CpuPlusDiagnostics.selectedReport = modelData;
                    root.showReport = false;
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: root.report ? root.report.status + " // " + root.report.finishedAt
            + "\n" + root.report.summary : "NO CAPTURE // THIS SESSION"
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
        text: "Latest result per tool retained until shell exit. Copy before restarting. No automatic uploads, storage changes or privileged actions."
        color: Colors.white
        font.pixelSize: 10
        wrapMode: Text.WordWrap
    }
}
