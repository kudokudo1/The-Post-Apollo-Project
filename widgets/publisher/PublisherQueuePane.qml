import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.services.publisher
import "../../components"

// P1.4 queue is DENY-ONLY. Every due item becomes NEEDS_REVIEW, NOT SENT.
// No web login, media upload or provider adapter runs from this component.
// A separately launched CLI watch process can tick while SocialW is closed;
// this UI does not install or start a background daemon automatically.
Rectangle {
    id: queuePane
    color: Colors.black
    clip: true

    property bool calendarMode: false
    property string activeDraftId: ""
    property var jobs: []
    property int selectedJobId: 0
    property int cancelArmedJobId: 0
    property string feedback: "SCHEDULER LOCAL // OUTBOUND PUBLISHING DISABLED"
    property string runningAction: ""
    property string sourceResponse: ""
    readonly property bool busy: queueProcess.running
    readonly property var currentDraft: {
        var drafts = PublisherDraftStore.snapshot.drafts;
        for (var i = 0; i < drafts.length; i++)
            if (drafts[i].id === activeDraftId) return drafts[i];
        return null;
    }
    readonly property var selectedJob: {
        for (var i = 0; i < jobs.length; i++)
            if (jobs[i].id === selectedJobId) return jobs[i];
        return null;
    }

    function issue(action, extra) {
        if (busy) {
            feedback = "QUEUE BUSY // REQUEST NOT SENT";
            return false;
        }
        runningAction = action;
        sourceResponse = "";
        var argv = ["python3", "-I", "-B",
            Quickshell.shellPath("services/publisher/PublisherQueueCli.py"),
            action,
            "--db", Quickshell.dataDir + "/publisher-queue-v1.sqlite3",
            "--drafts", Quickshell.dataDir + "/publisher-drafts-v1.json"];
        if (extra) argv = argv.concat(extra);
        queueProcess.exec(argv);
        feedback = action.toUpperCase() + " // LOCAL REQUEST IN PROGRESS";
        return true;
    }
    function refresh() { return issue("status", []); }
    function scheduleCurrent() {
        if (!currentDraft) {
            feedback = "SAVE OR OPEN A DRAFT BEFORE SCHEDULING";
            return;
        }
        issue("schedule", [
            "--draft", currentDraft.id,
            "--local-time", localTime.text.trim(),
            "--timezone", timezoneText.text.trim(),
            "--recurrence", recurrenceCombo.currentText
        ]);
    }
    function act(operation) {
        if (!selectedJob || busy) return;
        if (operation === "cancel" && cancelArmedJobId !== selectedJob.id) {
            cancelArmedJobId = selectedJob.id;
            feedback = "PRESS CANCEL AGAIN // KEEP HISTORY, STOP THIS JOB";
            return;
        }
        cancelArmedJobId = 0;
        issue(operation, ["--id", String(selectedJob.id)]);
    }
    function acceptResult(action, code, raw) {
        if (code !== 0 || !raw) {
            feedback = "QUEUE ENGINE UNAVAILABLE // NO ACTION CONFIRMED";
            return;
        }
        var result;
        try { result = JSON.parse(raw); }
        catch (e) {
            feedback = "INVALID QUEUE RESPONSE // NO ACTION CONFIRMED";
            return;
        }
        if (!result || result.ok !== true) {
            feedback = "QUEUE REFUSED // " + String(result && result.reason || "UNKNOWN");
            return;
        }
        if (action === "status") {
            if (!Array.isArray(result.jobs)) {
                feedback = "QUEUE RESPONSE INVALID";
                return;
            }
            jobs = result.jobs;
            feedback = "QUEUE LOADED // " + jobs.length
                + " RECORDS // NO PROVIDER DISPATCH";
        } else {
            feedback = action.toUpperCase() + " CONFIRMED LOCALLY // NOT POSTED";
            // The next command waits until the previous process exits.
            Qt.callLater(function() {
                if (!queuePane.busy && queuePane.visible)
                    queuePane.refresh();
            });
        }
    }

    Process {
        id: queueProcess
        stdout: StdioCollector {
            onStreamFinished: queuePane.sourceResponse = String(text || "").trim()
        }
        onExited: function(exitCode, exitStatus) {
            var op = queuePane.runningAction;
            Qt.callLater(function() {
                queuePane.acceptResult(op, exitCode, queuePane.sourceResponse);
            });
        }
    }
    Timer {
        interval: 60000
        repeat: true
        running: queuePane.visible
        onTriggered: if (!queuePane.busy) queuePane.refresh()
    }
    onVisibleChanged: {
        cancelArmedJobId = 0;
        if (visible && !busy) Qt.callLater(function() {
            if (queuePane.visible && !queuePane.busy) queuePane.refresh();
        });
    }

    Flickable {
        id: scroll
        anchors.fill: parent
        contentWidth: width
        contentHeight: content.implicitHeight + 15
        clip: true
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
                text: queuePane.calendarMode ? "CALENDAR // DUE SCHEDULE"
                                             : "QUEUE // LOCAL REVIEW LEDGER"
            }
            Text {
                width: parent.width
                font.pixelSize: 10
                color: Colors.orange
                wrapMode: Text.WordWrap
                text: "DENY-ONLY // DUE = NEEDS REVIEW. NEVER POSTED. "
                      + "Background tick is NOT installed by this screen."
            }
            Text {
                width: parent.width
                font.pixelSize: 11
                color: Colors.cyan
                text: queuePane.currentDraft
                      ? "SOURCE DRAFT // " + queuePane.currentDraft.id
                        + " // " + queuePane.currentDraft.title
                      : "SOURCE DRAFT // SAVE OR SELECT IN COMPOSE"
                elide: Text.ElideRight
            }
            Row {
                width: parent.width
                spacing: 6
                height: 34
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "REFRESH"
                    accentColor: Colors.cyan
                    available: !queuePane.busy
                    onTriggered: queuePane.refresh()
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "CHECK DUE // NO SEND"
                    accentColor: Colors.orange
                    available: !queuePane.busy
                    onTriggered: queuePane.issue("tick", [])
                }
            }
            Text {
                width: parent.width
                color: Colors.cyan
                font.pixelSize: 11
                text: "NEW SCHEDULE // FUTURE DATE AND IANA TIME ZONE"
            }
            TextField {
                id: localTime
                width: parent.width
                height: 35
                placeholderText: "2026-11-20T14:30 (LOCAL DATE/TIME)"
                placeholderTextColor: Colors.cyan
                color: Colors.white
                selectByMouse: true
                background: Rectangle {
                    color: Colors.black
                    border.width: 1
                    border.color: localTime.activeFocus ? Colors.magenta : Colors.cyan
                }
            }
            Row {
                width: parent.width
                spacing: 6
                height: 36
                TextField {
                    id: timezoneText
                    width: (parent.width - parent.spacing) * 0.62
                    height: 34
                    text: "UTC"
                    placeholderText: "IANA TIME ZONE (E.G. America/New_York)"
                    placeholderTextColor: Colors.cyan
                    color: Colors.white
                    selectByMouse: true
                    background: Rectangle {
                        color: Colors.black
                        border.width: 1
                        border.color: timezoneText.activeFocus
                                      ? Colors.magenta : Colors.cyan
                    }
                }
                ComboBox {
                    id: recurrenceCombo
                    width: (parent.width - parent.spacing) * 0.38
                    height: 34
                    model: ["once","daily","weekly"]
                }
            }
            ActionButton {
                width: parent.width
                height: 35
                label: "ADD SCHEDULE // DENY-ONLY"
                accentColor: Colors.magenta
                available: queuePane.currentDraft !== null && !queuePane.busy
                onTriggered: queuePane.scheduleCurrent()
            }
            Text {
                width: parent.width
                color: Colors.cyan
                font.pixelSize: 11
                text: "SAVED JOBS // " + queuePane.jobs.length
            }
            Flickable {
                id: listScroll
                width: parent.width
                height: Math.max(120, queuePane.height * 0.31)
                clip: true
                contentWidth: width
                contentHeight: jobRows.implicitHeight
                boundsBehavior: Flickable.StopAtBounds
                Column {
                    id: jobRows
                    width: listScroll.width
                    spacing: 5
                    Repeater {
                        model: queuePane.jobs
                        ActionButton {
                            required property var modelData
                            width: jobRows.width
                            height: 44
                            label: "#" + modelData.id + " // "
                                   + modelData.status.toUpperCase()
                                   + (modelData.due ? " // DUE" : "")
                                   + "\n" + modelData.local_time + " "
                                   + modelData.timezone + " // "
                                   + modelData.title
                            labelPixelSize: 10
                            accentColor: modelData.status === "blocked"
                                         ? Colors.orange : Colors.cyan
                            selected: queuePane.selectedJobId === modelData.id
                            onTriggered: {
                                queuePane.selectedJobId = modelData.id;
                                queuePane.cancelArmedJobId = 0;
                            }
                        }
                    }
                }
            }
            Text {
                width: parent.width
                color: Colors.white
                font.pixelSize: 11
                elide: Text.ElideRight
                text: queuePane.selectedJob
                      ? "SELECTED #" + queuePane.selectedJob.id
                        + " // " + queuePane.selectedJob.status.toUpperCase()
                        + " // " + queuePane.selectedJob.recurrence
                      : "SELECT A JOB FOR LOCAL CONTROLS"
            }
            Row {
                width: parent.width
                spacing: 5
                height: 34
                ActionButton {
                    width: (parent.width - 2 * parent.spacing) / 3
                    height: 33
                    label: "PAUSE"
                    accentColor: Colors.cyan
                    available: queuePane.selectedJob
                               && queuePane.selectedJob.status === "scheduled"
                               && !queuePane.busy
                    onTriggered: queuePane.act("pause")
                }
                ActionButton {
                    width: (parent.width - 2 * parent.spacing) / 3
                    height: 33
                    label: "RESUME"
                    accentColor: Colors.cyan
                    available: queuePane.selectedJob
                               && queuePane.selectedJob.status === "paused"
                               && !queuePane.busy
                    onTriggered: queuePane.act("resume")
                }
                ActionButton {
                    width: (parent.width - 2 * parent.spacing) / 3
                    height: 33
                    label: queuePane.cancelArmedJobId === queuePane.selectedJobId
                           && queuePane.selectedJobId !== 0
                           ? "CONFIRM CANCEL" : "CANCEL"
                    accentColor: Colors.orange
                    available: queuePane.selectedJob
                               && ["scheduled","paused","needs_review","blocked"]
                                      .indexOf(queuePane.selectedJob.status) >= 0
                               && !queuePane.busy
                    onTriggered: queuePane.act("cancel")
                }
            }
            Row {
                width: parent.width
                spacing: 5
                height: 34
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "MARK REVIEWED // NOT SENT"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    available: queuePane.selectedJob
                               && queuePane.selectedJob.status === "needs_review"
                               && !queuePane.busy
                    onTriggered: queuePane.act("acknowledge")
                }
                ActionButton {
                    width: (parent.width - parent.spacing) / 2
                    height: 33
                    label: "REARM RECURRENCE"
                    accentColor: Colors.cyan
                    available: queuePane.selectedJob
                               && queuePane.selectedJob.status === "reviewed"
                               && queuePane.selectedJob.recurrence !== "once"
                               && !queuePane.busy
                    onTriggered: queuePane.act("rearm")
                }
            }
            Text {
                width: parent.width
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
                text: queuePane.feedback
            }
        }
    }
}
