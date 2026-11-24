import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../services/forest/ForestAutoPolicyPreview.js" as AutoPreview
import "../services/forest/ForestModelFormPolicy.js" as ModelFormPolicy

// Explicit example inputs only. Never reads the composer or sets equipment.
Item {
    id: pane
    property var equipment: null
    property string inventoryStatus: "NOT_CHECKED"
    property var inventoryModels: []
    property string complexity: "unset"
    property string failure: "unset"
    property string suitability: "unset"
    property string requestedForm: "auto"
    property string effort: "normal"
    property string bindingScenario: "missing"
    property var result: null
    property var submitted: null
    property bool busy: false
    property bool discard: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property bool refused: false
    property string output: ""
    property string status: "NOT EVALUATED"
    function resetExample() {
        complexity = "unset";
        failure = "unset";
        suitability = "unset";
        requestedForm = "auto";
        effort = "normal";
        bindingScenario = "missing";
        result = null;
        status = "NOT EVALUATED";
        if (busy) discard = true;
    }
    onVisibleChanged: if (!visible) resetExample()
    function editExample(key,value) {
        if (busy) return;
        if (key === "complexity") complexity = value;
        else if (key === "failure") failure = value;
        else if (key === "suitability") suitability = value;
        else if (key === "requestedForm") requestedForm = value;
        else if (key === "effort") effort = value;
        else if (key === "bindingScenario") bindingScenario = value;
        result = null;
        status = "NOT EVALUATED";
    }
    function evaluateExample() {
        if (!visible || busy || worker.running) return;
        submitted = [requestedForm,effort,complexity,failure,suitability,bindingScenario];
        result = null;
        discard = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        refused = false;
        output = "";
        busy = true;
        status = "EVALUATING";
        worker.exec(["/usr/bin/python3","-B",
            Quickshell.shellPath("scripts/forest/ui_binding_example.py")].concat(submitted));
    }
    function finish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen) return;
        if (!discard && visible) {
            result = refused ? null : AutoPreview.parseBinding(output,submitted);
            status = result ? "I1 / I2 REFERENCE // UNKNOWN_HOLD" : "REFERENCE REFUSED";
        }
        submitted = null;
        output = "";
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
                if (pane.stderrSeen || String(this.text || "").trim().length) pane.refused = true;
                pane.stderrSeen = true;
                pane.finish();
            }
        }
        onExited: function(code,exitStatus) {
            if (!pane.busy) return;
            if (pane.exitSeen || code !== 0 || exitStatus !== 0) pane.refused = true;
            pane.exitSeen = true;
            pane.finish();
        }
    }

    Flickable {
        anchors.fill: parent
        clip: true
        contentHeight: body.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: body
            width: parent.width
            spacing: 5
            GohuText {
                width: parent.width
                text: "AUTO // OFFLINE POLICY PREVIEW"
                color: Colors.magenta
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "Choose example evidence. No real task assessed, no model started."
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: [
                    { key:"requestedForm", title:"EXAMPLE REQUESTED FORM", values:["auto","small","big"] },
                    { key:"effort", title:"EXAMPLE RESOLVED REASONING", values:["light","normal","deep"] },
                    { key:"complexity", title:"TASK COMPLEXITY", values:["unset","low","normal","high"] },
                    { key:"failure", title:"KNOWN SMALL FAILURE", values:["unset","absent","present"] },
                    { key:"suitability", title:"SMALL CAPABILITY", values:["unset","sufficient","insufficient","unknown"] }
                ]
                delegate: Column {
                    id: group
                    required property var modelData
                    width: body.width
                    spacing: 2
                    GohuText {
                        text: group.modelData.title
                        color: Colors.cyan
                        font.pixelSize: 9
                    }
                    Flow {
                        width: parent.width
                        spacing: 3
                        Repeater {
                            model: group.modelData.values
                            delegate: Rectangle {
                                required property string modelData
                                readonly property bool chosen: pane[group.modelData.key] === modelData
                                width: Math.max(48, optionText.implicitWidth + 12)
                                height: 23
                                color: chosen ? Colors.yellow : Colors.dark
                                border.width: 1
                                border.color: chosen ? Colors.magenta : Colors.cyan
                                Accessible.name: group.modelData.title + ": " + modelData
                                GohuText {
                                    id: optionText
                                    anchors.centerIn: parent
                                    text: parent.modelData.toUpperCase()
                                    font.pixelSize: 9
                                    color: parent.chosen ? Colors.magenta : Colors.cyan
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    enabled: !pane.busy
                                    onClicked: pane.editExample(group.modelData.key,parent.modelData)
                                }
                            }
                        }
                    }
                }
            }
            Rectangle {
                width: parent.width
                height: bindingChoices.implicitHeight + 12
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                Column {
                    id: bindingChoices
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 6
                    spacing: 3
                    GohuText {
                        width: parent.width
                        text: "I2 // FICTIONAL BINDING EVIDENCE"
                        color: Colors.magenta
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }
                    GohuText {
                        width: parent.width
                        text: "Example needs CHAT + REASONING / CTX 4096. Not the equipped model."
                        color: Colors.orange
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Flow {
                        width: parent.width
                        spacing: 3
                        Repeater {
                            model: [
                                {key:"unbound",label:"UNBOUND"},
                                {key:"missing",label:"NO EVIDENCE"},
                                {key:"mismatch",label:"DIGEST MISMATCH"},
                                {key:"not-installed",label:"NOT INSTALLED"},
                                {key:"install-unknown",label:"INSTALL ?"},
                                {key:"capability-unknown",label:"CAPABILITY ?"},
                                {key:"feature-unsupported",label:"FEATURE MISSING"},
                                {key:"context-insufficient",label:"CTX TOO LOW"},
                                {key:"match",label:"REFERENCE MATCH"}
                            ]
                            delegate: Rectangle {
                                required property var modelData
                                readonly property bool chosen: pane.bindingScenario === modelData.key
                                width: Math.min(bindingChoices.width, Math.max(48, bindingLabel.implicitWidth + 12))
                                height: 23
                                color: chosen ? Colors.yellow : Colors.black
                                border.width: 1
                                border.color: chosen ? Colors.magenta : Colors.cyan
                                GohuText {
                                    id: bindingLabel
                                    anchors.centerIn: parent
                                    text: parent.modelData.label
                                    color: parent.chosen ? Colors.magenta : Colors.cyan
                                    font.pixelSize: 9
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: !pane.busy
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: pane.editExample("bindingScenario",parent.modelData.key)
                                }
                            }
                        }
                    }
                }
            }
            ActionButton {
                width: parent.width
                height: 27
                label: pane.busy ? "EVALUATING..." : "EVALUATE"
                available: !pane.busy
                onLeftClicked: pane.evaluateExample()
            }
            GohuText {
                width: parent.width
                text: pane.status
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 1
                color: Colors.cyan
            }
            GohuText {
                width: parent.width
                text: "EXAMPLE RECOMMENDATION // " + (pane.result ? pane.result.form : "UNKNOWN")
                font.pixelSize: 11
                color: Colors.yellow
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: pane.result ? pane.result.reasons.join(" / ") : "EVALUATE EXAMPLE INPUTS"
                font.pixelSize: 9
                color: Colors.cyan
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: !pane.result ? "SLOT // UNRESOLVED"
                    : "EQUIPPED SLOT // " + ModelFormPolicy.slotLabel(pane.equipment,
                        pane.result.form.toLowerCase(), pane.inventoryStatus, pane.inventoryModels)
                font.pixelSize: 9
                color: Colors.cyan
                textFormat: Text.PlainText
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "I2 REFERENCE // " + (pane.result ? pane.result.bindingReason : "NOT EVALUATED")
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "LIVE BINDING // UNRESOLVED"
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "I1 / I2 EXAMPLE ONLY // NO RESOLVED BINDING // REASONING INDEPENDENT"
                font.pixelSize: 9
                color: Colors.orange
                wrapMode: Text.WordWrap
            }
        }
    }
}
