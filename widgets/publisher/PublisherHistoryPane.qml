import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import "../../components"

// P1.6 // Local queue event history only, NEVER provider receipts.
// Audit is read-only; reconciliation requires an explicit second action
// and only BLOCKS jobs whose saved draft changed or disappeared.
Rectangle {
    id: historyPane
    color: Colors.black
    clip: true

    property var events: []
    property var auditResult: null
    property string feedback: "LOCAL QUEUE HISTORY // NO EXTERNAL POSTS"
    property string runningAction: ""
    property string responseText: ""
    property bool reconcileArmed: false
    readonly property bool busy: historyProcess.running

    function command(action) {
        if (busy) {
            feedback = "QUEUE BUSY // NO SECOND REQUEST";
            return false;
        }
        runningAction = action;
        responseText = "";
        historyProcess.exec(["python3","-I","-B",
            Quickshell.shellPath("services/publisher/PublisherQueueCli.py"),
            action,"--db",Quickshell.dataDir + "/publisher-queue-v1.sqlite3",
            "--drafts",Quickshell.dataDir + "/publisher-drafts-v1.json"]);
        feedback = action.toUpperCase() + " // WAIT FOR LOCAL RESULT";
        return true;
    }
    function confirmReconcile() {
        if (!auditResult || auditResult.ledgerConsistent !== true
                || !Array.isArray(auditResult.sourceProblems)) {
            feedback = "AUDIT REQUIRED // HISTORY MUST BE CONSISTENT";
            return;
        }
        if (auditResult.sourceProblems.length === 0) {
            feedback = "NO STALE SOURCE LINKS TO BLOCK";
            return;
        }
        if (!reconcileArmed) {
            reconcileArmed = true;
            feedback = "CONFIRM BLOCK " + auditResult.sourceProblems.length
                       + " STALE LOCAL JOBS? NO FILES WILL BE DELETED";
            return;
        }
        reconcileArmed = false;
        command("reconcile");
    }
    function accept(action,exitCode,raw) {
        if (exitCode !== 0 || !raw) {
            feedback = "LOCAL HISTORY ENGINE UNAVAILABLE";
            return;
        }
        var result;
        try { result = JSON.parse(raw); }
        catch (e) {
            feedback = "INVALID HISTORY RESPONSE // NO CHANGE CONFIRMED";
            return;
        }
        if (!result || result.ok !== true || result.canPublish !== false
                || result.posted !== 0) {
            feedback = "HISTORY REFUSED // "
                + String(result && result.reason || "INVALID_RECEIPT");
            return;
        }
        if (action === "history") {
            if (!Array.isArray(result.events)
                    || result.source !== "LOCAL_QUEUE_ONLY") {
                feedback = "UNTRUSTED HISTORY RESPONSE";
                return;
            }
            events = result.events;
            feedback = "LOCAL EVENTS LOADED // " + events.length
                       + " // NOT PUBLISHED";
        } else if (action === "audit") {
            if (typeof result.ledgerConsistent !== "boolean"
                    || !Array.isArray(result.ledgerProblems)
                    || !Array.isArray(result.sourceProblems)
                    || result.repairPerformed !== false) {
                feedback = "UNTRUSTED AUDIT RESPONSE";
                return;
            }
            auditResult = result;
            reconcileArmed = false;
            feedback = (result.ledgerConsistent ? "LEDGER CONSISTENT" :
                        "LEDGER DIVERGENCE")
                       + " // STALE SOURCES " + result.sourceProblems.length
                       + " // NO REPAIR PERFORMED";
        } else if (action === "reconcile") {
            auditResult = null;
            feedback = "STALE JOBS BLOCKED // " + result.blocked
                       + " // NOTHING SENT";
            Qt.callLater(function() {
                if (historyPane.visible && !historyPane.busy)
                    historyPane.command("audit");
            });
        }
    }

    Process {
        id: historyProcess
        stdout: StdioCollector {
            onStreamFinished: historyPane.responseText=String(text || "").trim()
        }
        onExited: function(exitCode, exitStatus) {
            var action=historyPane.runningAction;
            Qt.callLater(function() {
                historyPane.accept(action,exitCode,historyPane.responseText);
            });
        }
    }
    onVisibleChanged: {
        reconcileArmed = false;
        if (visible && !busy) Qt.callLater(function() {
            if (historyPane.visible && !historyPane.busy)
                historyPane.command("history");
        });
    }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: content.implicitHeight + 15
        boundsBehavior: Flickable.StopAtBounds
        Column {
            id: content
            width: scroll.width
            spacing: 9
            Text {
                width: parent.width
                font.pixelSize: 14
                font.bold: true
                color: Colors.white
                text: "HISTORY // LOCAL EVENTS & RECOVERY"
            }
            Text {
                width: parent.width
                font.pixelSize: 11
                color: Colors.orange
                wrapMode: Text.WordWrap
                text: "NO SOCIAL POSTS, PROVIDER CONFIRMATIONS OR DELIVERY "
                      + "RECEIPTS ARE RECORDED. HISTORY IS LOCAL QUEUE ACTIVITY."
            }
            Row {
                width: parent.width
                height: 34
                spacing: 6
                ActionButton {
                    width: (parent.width - parent.spacing)/2
                    height: 33
                    label: "RELOAD HISTORY"
                    accentColor: Colors.cyan
                    available: !historyPane.busy
                    onTriggered: historyPane.command("history")
                }
                ActionButton {
                    width: (parent.width - parent.spacing)/2
                    height: 33
                    label: "AUDIT STORAGE & SOURCES"
                    labelPixelSize: 10
                    accentColor: Colors.cyan
                    available: !historyPane.busy
                    onTriggered: historyPane.command("audit")
                }
            }
            Text {
                width: parent.width
                font.pixelSize: 10
                color: historyPane.auditResult
                       && historyPane.auditResult.ledgerConsistent === false
                       ? Colors.orange : Colors.cyan
                text: historyPane.auditResult
                      ? (historyPane.auditResult.ledgerConsistent
                          ? "LEDGER // CONSISTENT" : "LEDGER // INCONSISTENT")
                        + " // SOURCE ISSUES " + historyPane.auditResult.sourceProblems.length
                      : "AUDIT // NOT YET RUN"
            }
            ActionButton {
                width: parent.width
                height: 34
                label: historyPane.reconcileArmed
                       ? "CONFIRM BLOCK STALE JOBS" : "BLOCK STALE // EXPLICIT ONLY"
                labelPixelSize: 11
                accentColor: Colors.orange
                available: !historyPane.busy && historyPane.auditResult
                           && historyPane.auditResult.ledgerConsistent === true
                           && historyPane.auditResult.sourceProblems.length > 0
                onTriggered: historyPane.confirmReconcile()
            }
            Text {
                width: parent.width
                font.pixelSize: 11
                color: Colors.cyan
                text: "EVENTS // LATEST " + historyPane.events.length
            }
            Repeater {
                model: historyPane.events
                Rectangle {
                    required property var modelData
                    width: content.width
                    height: 64
                    color: Colors.black
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 3
                        Text {
                            width: parent.width
                            color: Colors.white
                            font.pixelSize: 10
                            elide: Text.ElideRight
                            text: "#" + modelData.id + " // JOB "
                                  + modelData.job_id + " // "
                                  + modelData.action.toUpperCase()
                        }
                        Text {
                            width: parent.width
                            color: Colors.cyan
                            font.pixelSize: 10
                            elide: Text.ElideRight
                            text: modelData.from_state.toUpperCase()
                                  + " → " + modelData.to_state.toUpperCase()
                                  + " // OCCURRENCE " + modelData.occurrence
                        }
                        Text {
                            width: parent.width
                            color: Colors.orange
                            font.pixelSize: 9
                            elide: Text.ElideRight
                            text: modelData.detail + " // LOCAL ONLY"
                        }
                    }
                }
            }
            Text {
                width: parent.width
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                text: historyPane.feedback
            }
        }
    }
}
