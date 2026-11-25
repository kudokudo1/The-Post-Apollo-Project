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
    property string section: "PROCESSES"
    readonly property bool groupIdentityAvailable: false
    function selectSection(name) {
        if (visible && ["PROCESSES","GROUPS"].includes(name)) section=name;
    }
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
            text: root.section==="GROUPS" ? "PROC // GROUP CONTROLS" : "PROC // PROCESS OBSERVATION"
            color: Colors.magenta
            font.pixelSize: 12
        }
        Row {
            id: procNavigation
            width: parent.width
            spacing: 4
            Repeater {
                model: ["PROCESSES","GROUPS"]
                delegate: ActionButton {
                    required property string modelData
                    objectName: modelData==="GROUPS" ? "cpuplusProcGroups" : "cpuplusProcProcesses"
                    width: Math.max(0,(procNavigation.width-procNavigation.spacing)/2)
                    height: 26
                    label: modelData
                    contentPadding: 2
                    selected: root.section===modelData
                    acceptedButtons: Qt.LeftButton
                    keyboardActivationSignal: "leftClicked"
                    onLeftClicked: root.selectSection(modelData)
                }
            }
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
                available: root.section==="PROCESSES" && !CpuPlusDiagnostics.busy && !CpuPlusDiagnostics.archiveBusy && !CpuPlusDiagnostics.faulted
                acceptedButtons: Qt.LeftButton
                keyboardActivationSignal: "leftClicked"
                onLeftClicked: { if(root.section==="PROCESSES" && visible && available) CpuPlusDiagnostics.request("census") }
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
        visible: root.section==="PROCESSES"
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
        visible: root.section==="PROCESSES"
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
        model: root.section==="PROCESSES" ? root.ranked : []
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
        visible: root.section==="PROCESSES"
        text: "Same-user selected rows only. RSS includes shared pages. Change compares first/final returned rows with matching PID and start ticks, not continuous growth. Names are not application identities. No PSS, swap, group totals or process limits available here."
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    GohuText {
        width: parent.width
        visible: root.section==="PROCESSES"
        text: "PROCESS CONTROLS // HOLD: VERIFIED GROUP IDENTITY & PERMISSIONS REQUIRED"
        color: Colors.orange
        font.pixelSize: 10
        wrapMode: Text.Wrap
    }
    Column {
        objectName: "cpuplusProcGroupWorkspace"
        visible: root.section==="GROUPS"
        width: root.width
        spacing: 5
        GohuText {
            width: parent.width
            text: "GROUP IDENTITY // UNAVAILABLE"
            color: Colors.orange
            font.pixelSize: 12
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "No verified process-group provider connected. A process name or historical PID cannot identify a controllable application group."
            color: Colors.white
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        GohuText {
            width: parent.width
            text: "MEMBERSHIP / MEMORY TOTAL / LIMIT / PROTECTION // NOT OBSERVED"
            color: Colors.cyan
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
        ActionButton {
            objectName: "cpuplusProcGroupProtectionLocked"
            width: parent.width
            height: 28
            label: "PROTECTION // LOCKED"
            available: false
        }
        ActionButton {
            objectName: "cpuplusProcGroupLimitLocked"
            width: parent.width
            height: 28
            label: "RESOURCE LIMIT // LOCKED"
            available: false
        }
        GohuText {
            width: parent.width
            text: "Requires verified group identity, current membership, fresh resource observations and separately authorized control. No group inferred from census; no change or background scan initiated."
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.Wrap
        }
    }
}
