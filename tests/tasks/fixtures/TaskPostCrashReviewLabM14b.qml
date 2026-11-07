import QtQuick
import Quickshell
import Quickshell.Io
import "../../../widgets/tasks/TaskRecoveryReviewPolicyM13z.js" as ReviewPolicy

// TASKS M14b // Manually launched, isolated, disposable source review.
// NOT imported by production shell.qml, TASKS, or Connections.
// Runs existing M13y Python in one short-lived subprocess ONLY after
// explicit operator click, with an absolute fixture-only SQLite path.
// The subprocess does not write task data or repair any journal.
Scope {
    id: lab

    property string fixtureDbPath: ""
    property string status: "NOT_STARTED"
    property bool inFlight: false
    property bool frameSeen: false
    property var pendingProjection: null
    property var resultProjection: ReviewPolicy.syntheticResult(null)

    readonly property bool productionEnabled: false
    readonly property bool realTaskDataAccessAuthorized: false
    readonly property bool nativeSourceOwnerAuthenticated: false
    readonly property bool durableUserSaveAcknowledged: false
    readonly property bool automaticReplayAuthorized: false
    readonly property bool draftDeletionAuthorized: false
    readonly property bool keyReleaseAuthorized: false

    // Preliminary UI guard, not a filesystem authority. M13y revalidates
    // private directory, symlinks, SQLite journal and the synthetic source.
    function fixtureOnlyPath(path) {
        return typeof path === "string" &&
            /^\/.+\/m11e-fileview-test\/handoff-test\.db$/.test(path) &&
            path.indexOf("/../") < 0 && path.indexOf("/./") < 0 &&
            path.indexOf("//") < 0 &&
            path.indexOf("apollo-hub-todo-v1.json") < 0;
    }

    function inspectOnce() {
        if (inFlight || inspector.running)
            return false;
        resultProjection = ReviewPolicy.syntheticResult(null);
        pendingProjection = null;
        frameSeen = false;
        if (!fixtureOnlyPath(fixtureDbPath)) {
            status = "REFUSED // PRIVATE M11E FIXTURE ONLY";
            return false;
        }
        status = "READING SYNTHETIC FIXTURE // NO SOURCE WRITES";
        inFlight = true;
        inspector.exec([
            "python3", "-I", "-B",
            Quickshell.shellPath(
                "tests/tasks/fixtures/TaskPostCrashSourceReviewM13y.py"),
            "--db", fixtureDbPath
        ]);
        return true;
    }

    function acceptFrame(line) {
        if (!inFlight || frameSeen || typeof line !== "string" ||
                line.length > 4096) {
            pendingProjection = null;
            frameSeen = true;
            status = "REFUSED // INVALID INSPECTOR OUTPUT";
            return;
        }
        frameSeen = true;
        try {
            // The strict M13z projection does NOT echo raw source bytes,
            // hashes, stage IDs, journal paths or user-supplied text.
            var value = JSON.parse(line);
            pendingProjection = ReviewPolicy.syntheticResult(value);
        } catch (error) {
            pendingProjection = null;
            status = "REFUSED // INVALID INSPECTOR OUTPUT";
        }
    }

    function completeInspection(code) {
        inFlight = false;
        if (code !== 0 || !frameSeen || pendingProjection === null) {
            resultProjection = ReviewPolicy.syntheticResult(null);
            status = "REFUSED // SOURCE EVIDENCE UNVERIFIED";
        } else {
            resultProjection = pendingProjection;
            status = resultProjection.origin ===
                "SYNTHETIC FIXTURE ONLY // NOT LIVE"
                ? "SYNTHETIC SOURCE OBSERVATION // REVIEW ONLY"
                : "REFUSED // SOURCE EVIDENCE UNVERIFIED";
        }
        pendingProjection = null;
        frameSeen = false;
    }

    Process {
        id: inspector
        stdinEnabled: false
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) { lab.acceptFrame(line); }
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            lab.completeInspection(code);
        }
    }

    PanelWindow {
        visible: true
        implicitWidth: 600
        implicitHeight: 410
        focusable: true
        exclusiveZone: 0
        anchors { left: true; top: true }
        color: "#1B0623"

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10

                Text {
                    width: parent.width
                    text: "M14b // POST-CRASH SOURCE REVIEW LAB"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }

                Text {
                    width: parent.width
                    text: "DISPOSABLE M11E SOURCE ONLY // NOT REAL TASKS"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: "Enter a private absolute /m11e-fileview-test/handoff-test.db path."
                    color: "#55CFCA"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    width: parent.width
                    height: 33
                    color: "#16041D"
                    border.color: "#55CFCA"
                    clip: true

                    TextInput {
                        id: sourceInput
                        anchors.fill: parent
                        anchors.margins: 8
                        text: ""
                        selectByMouse: true
                        clip: true
                        color: "#DCF3FA"
                        font.pixelSize: 11
                        onTextChanged: lab.fixtureDbPath = text.trim()
                    }
                }

                Rectangle {
                    width: 162
                    height: 32
                    color: inspectMouse.pressed ? "#C74EC7" : "#1B0623"
                    border.color: "#55CFCA"
                    border.width: 1
                    opacity: lab.inFlight ? 0.5 : 1

                    Text {
                        anchors.centerIn: parent
                        text: lab.inFlight ? "INSPECTING" : "INSPECT TEST"
                        color: "#DCF3FA"
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        id: inspectMouse
                        anchors.fill: parent
                        enabled: !lab.inFlight
                        onClicked: lab.inspectOnce()
                    }
                }

                Text {
                    width: parent.width
                    text: lab.status
                    color: "#F2BE4E"
                    font.pixelSize: 11
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    width: parent.width
                    height: reviewBody.implicitHeight + 18
                    color: "#16041D"
                    border.width: 1
                    border.color: "#5B5FD4"

                    Column {
                        id: reviewBody
                        x: 9
                        y: 9
                        width: parent.width - 18
                        spacing: 8

                        Text {
                            width: parent.width
                            text: lab.resultProjection.origin
                            color: "#55CFCA"
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: lab.resultProjection.title
                            color: "#F2BE4E"
                            font.pixelSize: 11
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: lab.resultProjection.explanation
                            color: "#DCF3FA"
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            width: parent.width
                            text: "KEEP DRAFT // NO REPLAY // NO RESTORE // NO DELETE"
                            color: "#ED981A"
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                Text {
                    width: parent.width
                    text: "SOURCE MATCH IS NOT APPLICATION IDENTITY OR DURABLE ACK."
                    color: "#55CFCA"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
