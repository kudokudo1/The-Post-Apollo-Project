import QtQuick
import "../../components"

// Git-specific diagnostic presentation; same dock/close/rail controls as
// other diagnostics. No process, timer, or service ownership.
Rectangle {
    id: root
    required property var service
    signal closeRequested()
    property bool rawMode: false
    property bool failureMode: !!service.refreshDiagLastFailure
    readonly property var failure: service.refreshDiagLastFailure
    readonly property bool showingFailure: failureMode && !!failure
    readonly property var marks: showingFailure ? (failure.marks || []) : service.refreshDiagMarks
    readonly property real doneMs: showingFailure ? failure.doneMs : service.refreshDiagDoneMs
    readonly property var timingRows: makeRows(marks)
    readonly property var slowest: timingRows.reduce((best,row)=>row.ms>=0 && (!best || row.ms>best.ms) ? row : best,null)
    readonly property var finalMark: marks.find(m=>m.stage==="finished")
    readonly property real shellMs: finalMark ? finalMark.shellMs : -1
    readonly property real budget: Math.max(1,service.refreshDiagDeadlineMs)
    readonly property real scale: Math.max(budget,shellMs,doneMs)
    function makeRows(input) {
        const stages=["repo_check","metadata","status","upstream","merged_refs","cherry","local_branches","remote_branches","history","finished"];
        return input.filter(m=>m.stage!=="finished").map(m=>{
            const n=input[input.indexOf(m)+1];
            return {stage:m.stage,label:service.diagnosticStageLabel(m.stage),
                ms:n && stages.indexOf(n.stage)===stages.indexOf(m.stage)+1 ? n.shellMs-m.shellMs : -1,
                arrival:m.arrivalMs};
        });
    }
    function formatMs(value) { return Number.isFinite(value) && value>=0 ? value+" ms" : "N/A"; }
    color: "#110319"
    border.width: 1
    border.color: Colors.magenta
    radius: 0
    clip: true

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        onPressed: function(mouse) { mouse.accepted=true; }
        onWheel: function(wheel) { wheel.accepted=true; }
    }
    Column {
        id: header
        x: 12; y: 8
        width: Math.max(0,parent.width-24)
        spacing: 6
        Row {
            width: parent.width; height: 34; spacing: 8
            GohuText {
                width: Math.max(0,parent.width-closeButton.width-parent.spacing)
                anchors.verticalCenter: parent.verticalCenter
                text: "GIT HEALTH // DIAGNOSTICS"
                color: Colors.magenta; font.pixelSize: 15
                elide: Text.ElideRight
            }
            CloseButton { id: closeButton; width: 34; onCloseRequested: root.closeRequested() }
        }
        Rectangle { width: parent.width; height: 2; color: Colors.cyan }
        Row {
            width: parent.width; height: 30; spacing: 5
            ActionButton {
                width: (parent.width-15)/4; height: parent.height
                label: "OVERVIEW"; selected: !root.rawMode; onLeftClicked: root.rawMode=false
            }
            ActionButton {
                width: (parent.width-15)/4; height: parent.height
                label: "RAW"; selected: root.rawMode; onLeftClicked: root.rawMode=true
            }
            ActionButton {
                width: (parent.width-15)/4; height: parent.height
                label: "CURRENT"; selected: !root.showingFailure
                available: !root.rawMode; onLeftClicked: root.failureMode=false
            }
            ActionButton {
                width: (parent.width-15)/4; height: parent.height
                label: "LAST FAILURE"; selected: root.showingFailure
                available: !!root.failure && !root.rawMode; onLeftClicked: root.failureMode=true
            }
        }
    }
    Flickable {
        id: scroll
        anchors.top: header.bottom
        anchors.topMargin: 8
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 12
        anchors.rightMargin: 32
        contentWidth: width
        contentHeight: body.height
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        Column {
            id: body
            width: scroll.width
            height: implicitHeight
            spacing: 9
            Column {
                width: parent.width
                visible: !root.rawMode
                spacing: 8
                GohuText {
                    width: parent.width
                    text: (root.service.refreshing?"READING":root.service.available?"LOCAL LIVE":"OFFLINE")
                        +" // "+(root.showingFailure?"FAILED ATTEMPT "+root.failure.attempt:"CURRENT ATTEMPT "+root.service.refreshDiagAttempt)
                    font.pixelSize: 14
                    color: root.service.refreshing?Colors.orange:root.service.available?Colors.cyan:Colors.red
                    wrapMode: Text.Wrap
                }
                Text {
                    width: parent.width
                    text: root.showingFailure && root.failure.code==="GIT READ TIMEOUT"
                        ? "Local read exceeded the deadline. "+(root.doneMs>=0?"Completion marker arrived later.":"Completion not yet recorded.")
                        : root.showingFailure ? root.failure.code : root.service.refreshDiagOutcome
                    color: Colors.white; font.pixelSize: 14; wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
                Row {
                    width: parent.width; height: 58; spacing: 6
                    Repeater {
                        model: [{label:"DEADLINE",value:root.budget,ink:Colors.orange},
                            {label:"SHELL TOTAL",value:root.shellMs,ink:Colors.cyan},
                            {label:"DONE RECEIVED",value:root.doneMs,ink:root.doneMs>root.budget?Colors.red:Colors.cyan}]
                        delegate: Rectangle {
                            required property var modelData
                            width: Math.max(0,(body.width-12)/3); height: 58
                            color: Colors.dark; border.color: modelData.ink; border.width: 1
                            Column {
                                anchors.fill: parent; anchors.margins: 6; spacing: 5
                                GohuText { width: parent.width; text: modelData.label; color: Colors.white; font.pixelSize: 10; elide: Text.ElideRight }
                                GohuText { width: parent.width; text: root.formatMs(modelData.value); color: modelData.ink; font.pixelSize: 17; fontSizeMode: Text.HorizontalFit; minimumPixelSize: 10 }
                            }
                        }
                    }
                }
                // Deadline tick marks the scale, not a second progress estimate.
                Rectangle {
                    width: parent.width; height: 13; color: Colors.dark; border.color: Colors.cyan
                    Rectangle { height: parent.height-2; x: 1; y: 1; width: Math.max(0,(parent.width-2)*Math.max(0,root.doneMs)/root.scale); color: root.doneMs>root.budget?Colors.red:Colors.cyan; opacity: 0.65 }
                    Rectangle { x: Math.min(parent.width-2,(parent.width-2)*root.budget/root.scale); width: 2; height: parent.height; color: Colors.yellow }
                }
                GohuText {
                    width: parent.width; color: Colors.orange; font.pixelSize: 12; wrapMode: Text.Wrap
                    text: root.slowest ? "SLOWEST COMPLETED // "+root.slowest.label+" · "+root.formatMs(root.slowest.ms) : "SLOWEST COMPLETED // NOT AVAILABLE"
                }
                GohuText {
                    width: parent.width; color: Colors.magenta; font.pixelSize: 12
                    text: "EXECUTION STAGES // SHELL / RECEIPT"
                }
                Repeater {
                    model: root.timingRows
                    delegate: Item {
                        required property var modelData
                        width: body.width; height: 34
                        readonly property color ink: root.slowest && root.slowest.stage===modelData.stage ? Colors.orange : Colors.cyan
                        Row {
                            width: parent.width; height: 20; spacing: 4
                            Text { width: Math.max(0,parent.width-154); text: modelData.label; font.pixelSize: 13; color: Colors.white; elide: Text.ElideRight }
                            GohuText { width: 75; horizontalAlignment: Text.AlignRight; text: root.formatMs(modelData.ms); color: ink; font.pixelSize: 12 }
                            GohuText { width: 71; horizontalAlignment: Text.AlignRight; text: "+"+root.formatMs(modelData.arrival); color: Colors.white; font.pixelSize: 10 }
                        }
                        Rectangle {
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 3
                            width: parent.width; height: 7; color: Colors.dark
                            Rectangle { height: parent.height; width: Math.min(parent.width,parent.width*Math.max(0,modelData.ms)/root.scale); color: ink }
                        }
                    }
                }
                Text {
                    width: parent.width; font.pixelSize: 12; color: Colors.white; wrapMode: Text.Wrap
                    text: "Child at timeout: "+(root.showingFailure?(root.failure.childRunning?"RUNNING":"IDLE"):"N/A")
                        +" | STDERR: "+(root.showingFailure?root.failure.stderrCount:root.service.refreshDiagStderr)
                        +" | Late DONE: "+root.service.refreshDiagLateDone
                        +"\nUnattributed wall time: "+(root.shellMs>=0 && root.doneMs>=0 ? (root.doneMs-root.shellMs)+" ms" : "N/A")
                        +" (launch, delivery, scheduling and clock differences)."
                }
            }
            Text {
                width: parent.width; visible: root.rawMode
                text: root.rawMode ? root.service.refreshDiagnosticText() : ""
                textFormat: Text.PlainText; wrapMode: Text.Wrap; font.pixelSize: 13; color: Colors.white
            }
            Text {
                width: parent.width; font.pixelSize: 11; color: Colors.white; opacity: 0.85; wrapMode: Text.Wrap
                text: "READ ONLY // Local Git is not internet connectivity. Timing is session-only; overlap and clock changes can affect attribution."
            }
        }
    }
    NeonScrollBar {
        flickable: scroll
        geometryHost: root
        handleStyle: "star"
        visible: scrollable
    }
}
