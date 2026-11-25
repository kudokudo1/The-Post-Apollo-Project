import QtQuick
import qs.services.diagnostics
import "../../services/diagnostics/CpuPlusDiagnosticsPolicy.js" as Policy
import "../../components"
import "CpuPlusProcessPresentation.js" as Census

// Demand-loaded view of the existing shared diagnostic owner. No new poller.
Column {
    id: root
    objectName: "cpuplusProcessPane"
    property Item headerTarget: null
    property Item footerTarget: null
    property string order: "RSS"
    readonly property bool censusRunning: CpuPlusDiagnostics.busy && CpuPlusDiagnostics.kind === "census"
    function cancelCensus() {
        if (censusRunning && !CpuPlusDiagnostics.cancelled) CpuPlusDiagnostics.cancel();
    }
    readonly property var report: CpuPlusDiagnostics.reports.census || null
    // The session owner stores kind by map key; only archived records carry kind.
    readonly property var view: Census.project(report ? Object.assign({kind:"census"},report) : null,Policy.summarize)
    readonly property var ranked: Census.rank(view,order)
    spacing: 5
    Column {
        parent: root.headerTarget || root
        objectName: "cpuplusProcTopControls"
        width: parent.width
        spacing: 3
        GohuText {
            width: parent.width
            text: "PROC // PROCESS OBSERVATION"
            color: Colors.magenta
            font.pixelSize: 12
        }
        Row {
            width: parent.width
            spacing: 4
            ActionButton {
                objectName: "cpuplusProcStart"
                width: Math.max(0,parent.width-72-parent.spacing)
                height: 28
                label: "PROCESS CENSUS // 30s"
                labelFontSizeMode: Text.HorizontalFit
                labelMinimumPixelSize: 8
                contentPadding: 2
                available: !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.archiveBusy && !CpuPlusDiagnostics.faulted
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: CpuPlusDiagnostics.request("census")
            }
            ActionButton {
                objectName: "cpuplusProcCancel"
                width: 72
                height: 28
                label: root.censusRunning && CpuPlusDiagnostics.cancelled ? "STOPPING" : "CANCEL"
                contentPadding: 2
                accentColor: Colors.red
                available: root.censusRunning && !CpuPlusDiagnostics.cancelled
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.cancelCensus()
            }
        }
        GohuText {
            width: parent.width
            text: CpuPlusDiagnostics.feedback
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
    }
    GohuText {
        width: parent.width
        text: root.view ? "HISTORICAL CAPTURE // "+root.report.finishedAt
            + "\nRETURNED "+root.view.rows.length+" / OBSERVED "+root.view.observed
            + "\nCPU / I-O COVERAGE "+root.view.cpuMeasured+" / "+root.view.ioMeasured
            + "\n"+root.view.samples+" SAMPLES // "+root.view.skipped+" UNREADABLE OR EXITED PID ENTRIES AT FINAL SCAN"
            + (root.view.limited?"\nSCAN LIMIT REACHED":"") : "NO COMPLETE PROCESS CENSUS AVAILABLE"
        color: root.view ? Colors.cyan : Colors.orange
        font.pixelSize: 10
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
    }
    Row {
        id: sortRail
        parent: root.footerTarget || root
        objectName: "cpuplusProcBottomControls"
        width: parent.width
        spacing: 4
        Repeater {
            model: ["RSS","CPU","WRITE"]
            delegate: ActionButton {
                required property string modelData
                width: Math.max(0,(sortRail.width-8)/3)
                height: 28
                contentPadding: 2
                label: modelData
                available: root.view !== null
                selected: root.order===modelData
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: root.order=modelData
            }
        }
    }
    Repeater {
        model: root.ranked
        delegate: Rectangle {
            required property var modelData
            width: root.width
            height: body.implicitHeight+8
            color: Colors.black
            border.color: Colors.cyan
            border.width: 1
            Column {
                id: body
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 4
                spacing: 2
                GohuText {
                    width: parent.width
                    text: modelData.name+" // PID "+modelData.pid
                    color: Colors.magenta
                    font.pixelSize: 11
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: "RSS "+Census.gib(modelData.rssKiB)+" // CHANGE "+Census.change(modelData.change)
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
                GohuText {
                    width: parent.width
                    text: "CPU "+(modelData.cpuPct===null?"N/A":modelData.cpuPct.toFixed(1)+"%")
                        +" // THREADS "+modelData.threads
                        +"\nREAD "+Census.rate(modelData.readBps)+" / WRITE "+Census.rate(modelData.writeBps)
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.Wrap
                }
            }
        }
    }
    GohuText {
        width: parent.width
        text: "Same-user selected rows only. RSS includes shared pages. Change compares first/final returned rows with matching PID and start ticks, not continuous growth. Names are not application identities. No PSS, swap, group totals or process limits available here."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        text: "PROCESS CONTROLS // HOLD: VERIFIED GROUP IDENTITY & PERMISSIONS REQUIRED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
}
