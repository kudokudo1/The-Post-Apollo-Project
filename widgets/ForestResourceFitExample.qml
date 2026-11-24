import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../services/forest/ForestResourceFitExamplePolicy.js" as Example

// Explicit hypothetical calculator. No host observation, model binding,
// persistence, permission or admission. Uses Core P1, not a second policy.
Column {
    id: pane
    spacing: 4
    property bool expanded: false
    property var values: ["","","","","","","","",""]
    property bool mayDefer: true
    property bool busy: false
    property var submitted: null
    property var result: null
    property string status: "NOT_EVALUATED"
    property string output: ""
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property bool refused: false

    function editValue(index, value) {
        if (busy || index < 0 || index >= 9) return;
        const next = values.slice();
        next[index] = value;
        values = next;
        result = null;
        status = "NOT_EVALUATED";
    }
    function evaluateNow() {
        if (!visible || !expanded || busy || worker.running) return;
        const args = Example.commandInputs(values, mayDefer);
        result = null;
        if (!args) { status = "INVALID INPUT"; return; }
        submitted = args;
        output = "";
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        refused = false;
        status = "EVALUATING";
        busy = true;
        worker.exec(["/usr/bin/python3", "-B",
            Quickshell.shellPath("scripts/forest/ui_resource_fit_example.py")].concat(args));
    }
    function finish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen) return;
        result = refused ? null : Example.parseReceipt(output, submitted);
        status = result ? "EXAMPLE ONLY" : "EVALUATION REFUSED";
        output = "";
        submitted = null;
        busy = false;
    }

    Process {
        id: worker
        running: false
        stdout: StdioCollector {
            onStreamFinished: {
                if (!pane.busy) return;
                if (pane.stdoutSeen) pane.refused = true;
                pane.stdoutSeen = true;
                pane.output = String(this.text || "");
                pane.finish();
            }
        }
        stderr: StdioCollector {
            onStreamFinished: {
                if (!pane.busy) return;
                if (pane.stderrSeen || String(this.text || "").trim().length)
                    pane.refused = true;
                pane.stderrSeen = true;
                pane.finish();
            }
        }
        onExited: function(code, exitStatus) {
            if (!pane.busy) return;
            if (pane.exitSeen || code !== 0 || exitStatus !== 0) pane.refused = true;
            pane.exitSeen = true;
            pane.finish();
        }
    }

    Rectangle {
        width: pane.width
        height: 26
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan
        GohuText {
            anchors.centerIn: parent
            text: pane.expanded ? "− RESOURCE FIT // P1 EXAMPLE" : "+ RESOURCE FIT // P1 EXAMPLE"
            color: Colors.cyan
            font.pixelSize: 9
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: pane.expanded = !pane.expanded
        }
    }
    Column {
        id: inputsPanel
        visible: pane.expanded
        width: pane.width
        spacing: 4
        GohuText {
            width: parent.width
            text: "HYPOTHETICAL VALUES ONLY // NO LIVE CAPACITY OR REQUIREMENT"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "Blank: unknown requirement/availability, no explicit budget. Zero is a real value."
            color: Colors.cyan
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: ["HOST RAM (MiB)", "ACCELERATOR (MiB)", "CPU THREADS"]
            delegate: Column {
                id: dimension
                required property string modelData
                required property int index
                width: inputsPanel.width
                spacing: 2
                GohuText {
                    text: dimension.modelData
                    color: Colors.magenta
                    font.pixelSize: 9
                }
                Row {
                    width: dimension.width
                    spacing: 3
                    Repeater {
                        model: ["NEED","BUDGET","AVAIL"]
                        delegate: Column {
                            id: field
                            required property string modelData
                            required property int index
                            readonly property int slot: dimension.index * 3 + index
                            width: (dimension.width - 6) / 3
                            spacing: 2
                            GohuText {
                                text: field.modelData
                                color: Colors.cyan
                                font.pixelSize: 9
                            }
                            Rectangle {
                                width: field.width
                                height: 23
                                color: Colors.black
                                border.width: 1
                                border.color: Colors.cyan
                                clip: true
                                TextInput {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    text: pane.values[field.slot]
                                    color: Colors.cyan
                                    font.pixelSize: 10
                                    maximumLength: 10
                                    readOnly: pane.busy
                                    selectByMouse: true
                                    validator: RegularExpressionValidator { regularExpression: /[0-9]{0,10}/ }
                                    Accessible.name: dimension.modelData + " " + field.modelData + ", hypothetical"
                                    onTextEdited: pane.editValue(field.slot, text)
                                }
                            }
                        }
                    }
                }
            }
        }
        Row {
            width: parent.width
            spacing: 3
            Rectangle {
                width: (inputsPanel.width - 3) / 2
                height: 25
                color: Colors.dark
                border.width: 1
                border.color: Colors.magenta
                GohuText {
                    anchors.centerIn: parent
                    text: pane.mayDefer ? "DEFER ALLOWED" : "NO DEFERRAL"
                    color: Colors.magenta
                    font.pixelSize: 9
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: !pane.busy
                    onClicked: {
                        pane.mayDefer = !pane.mayDefer;
                        pane.result = null;
                        pane.status = "NOT_EVALUATED";
                    }
                }
            }
            Rectangle {
                width: (inputsPanel.width - 3) / 2
                height: 25
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                GohuText {
                    anchors.centerIn: parent
                    text: pane.busy ? "..." : "EVALUATE"
                    color: Colors.cyan
                    font.pixelSize: 9
                }
                MouseArea {
                    anchors.fill: parent
                    enabled: !pane.busy
                    onClicked: pane.evaluateNow()
                }
            }
        }
        GohuText {
            width: parent.width
            text: pane.result ? "P1 EXAMPLE // " + (pane.result.outcome === "approve"
                ? "MODELED FIT" : pane.result.outcome.toUpperCase()) : pane.status
            color: Colors.orange
            font.pixelSize: 10
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            visible: !!pane.result
            text: pane.result ? pane.result.reasons.join(" / ") : ""
            textFormat: Text.PlainText
            color: Colors.cyan
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
        GohuText {
            width: parent.width
            text: "NO LEASE / NO PERMISSION / NO MODEL EXECUTION"
            color: Colors.orange
            font.pixelSize: 9
            wrapMode: Text.WordWrap
        }
    }
}
