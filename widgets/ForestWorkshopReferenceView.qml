import QtQuick
import Quickshell
import Quickshell.Io
import "../components"
import "../services/forest/ForestWorkshopReferencePolicy.js" as Policy

// Historical Bristlecone reference only; not a live task or activation.
Item {
    id: pane
    property bool profileSupported: false
    property var receipt: null
    property var submitted: null
    property bool busy: false
    property bool discard: false
    property bool stdoutSeen: false
    property bool stderrSeen: false
    property bool exitSeen: false
    property bool refused: false
    property string output: ""
    property string status: "LOAD REFERENCE"

    function reset() {
        receipt = null;
        status = "LOAD REFERENCE";
        if (busy) discard = true;
    }
    onVisibleChanged: {
        if (!visible) reset();
    }
    onProfileSupportedChanged: reset()

    function requestPlan(workshop, general, ready) {
        if (!visible || !profileSupported || busy || worker.running) return;
        submitted = [workshop, general.join(","), ready.join(",")];
        receipt = null;
        discard = false;
        stdoutSeen = false;
        stderrSeen = false;
        exitSeen = false;
        refused = false;
        output = "";
        status = "READING REFERENCE";
        busy = true;
        worker.exec(["/usr/bin/python3", "-B",
            Quickshell.shellPath("scripts/forest/ui_workshop_reference.py")].concat(submitted));
    }
    function selectWorkshop(key) {
        if (!receipt) return;
        requestPlan(key, [], []);
    }
    function toggleOptional(key, category) {
        if (!receipt || busy) return;
        const g = receipt.inputs[1] ? receipt.inputs[1].split(",") : [];
        const r = receipt.inputs[2] ? receipt.inputs[2].split(",") : [];
        if (category === "general" && receipt.general_ready.indexOf(key) >= 0)
            requestPlan(receipt.plan.workshop, Policy.toggle(g,key), r);
        else if (category === "ready" && chosenWorkshop && chosenWorkshop.ready.indexOf(key) >= 0)
            requestPlan(receipt.plan.workshop, g, Policy.toggle(r,key));
    }
    readonly property var chosenWorkshop: receipt ? receipt.workshops.find(function(w) {
        return w.key === receipt.plan.workshop;
    }) : null
    function finish() {
        if (!busy || !stdoutSeen || !stderrSeen || !exitSeen) return;
        if (!discard && visible && profileSupported) {
            receipt = refused ? null : Policy.parse(output,submitted);
            status = receipt ? "REFERENCE // UNKNOWN_HOLD" : "REFERENCE REFUSED // LOAD AGAIN";
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
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentHeight: body.implicitHeight
        Column {
            id: body
            width: scroll.width
            spacing: 5
            GohuText {
                width: parent.width
                text: pane.profileSupported ? "BRISTLECONE // HISTORICAL PROFILE"
                    : "NO RECOVERED WORKSHOP PROFILE FOR THIS TREE"
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "REFERENCE ONLY // NO TOOL EXECUTION OR PERMISSION"
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: body.width
                height: 27
                visible: pane.profileSupported && !pane.receipt
                available: !pane.busy
                label: pane.busy ? "READING..." : "LOAD REFERENCE"
                onLeftClicked: pane.requestPlan("research", [], [])
            }
            GohuText {
                width: parent.width
                visible: pane.profileSupported
                text: pane.status
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Column {
                width: body.width
                visible: !!pane.receipt
                spacing: 5
                GohuText {
                    text: "WORKSHOPS"
                    color: Colors.magenta
                    font.pixelSize: 10
                }
                Flow {
                    width: parent.width
                    spacing: 3
                    Repeater {
                        model: pane.receipt ? pane.receipt.workshops : []
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.max(0,(body.width-3)/2)
                            height: 28
                            label: modelData.key.toUpperCase()
                            selected: !!pane.receipt && pane.receipt.plan.workshop === modelData.key
                            available: !pane.busy
                            onLeftClicked: pane.selectWorkshop(modelData.key)
                        }
                    }
                }
                Repeater {
                    model: [
                        {title:"WORKSHOP CORE", category:"core",
                         entries:pane.receipt ? pane.receipt.plan.core : []},
                        {title:"GENERAL / READY", category:"general",
                         entries:pane.receipt ? pane.receipt.general_ready : []},
                        {title:"WORKSHOP READY", category:"ready",
                         entries:pane.chosenWorkshop ? pane.chosenWorkshop.ready : []}
                    ]
                    delegate: Column {
                        id: section
                        required property var modelData
                        width: body.width
                        spacing: 3
                        GohuText {
                            text: section.modelData.title
                            color: Colors.magenta
                            font.pixelSize: 10
                        }
                        Repeater {
                            model: section.modelData.entries
                            delegate: ActionButton {
                                required property string modelData
                                width: body.width
                                height: 25
                                readonly property bool isCore: !!pane.receipt && pane.receipt.plan.core.indexOf(modelData)>=0
                                selected: !!pane.receipt && pane.receipt.plan.selected.indexOf(modelData)>=0
                                available: !pane.busy && !isCore && section.modelData.category !== "core"
                                label: modelData.toUpperCase() + (isCore ? " // CORE" : selected ? " // SELECTED" : " // OPTIONAL")
                                onLeftClicked: pane.toggleOptional(modelData,section.modelData.category)
                            }
                        }
                    }
                }
                GohuText {
                    width: parent.width
                    text: pane.receipt ? "SELECTED " + pane.receipt.plan.selected.length
                        + " / DORMANT " + pane.receipt.plan.dormant.length
                        + " / NO HISTORICAL TARGET " + pane.receipt.plan.unresolved.length : ""
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                GohuText {
                    width: parent.width
                    text: "CAPABILITY REGISTRY // " + (pane.receipt ? pane.receipt.definitions.length : 0)
                    color: Colors.magenta
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: pane.receipt ? pane.receipt.definitions : []
                    delegate: GohuText {
                        required property var modelData
                        width: body.width
                        text: modelData.key.toUpperCase() + " // " + modelData.kind.toUpperCase()
                            + (pane.receipt && pane.receipt.plan.selected.indexOf(modelData.key)>=0 ? " / SELECTED" : " / DORMANT")
                            + "\nHIST TARGET " + (modelData.historical_target || "UNRESOLVED")
                        textFormat: Text.PlainText
                        color: Colors.cyan
                        font.pixelSize: 9
                        wrapMode: Text.WrapAnywhere
                    }
                }
            }
        }
    }
}
