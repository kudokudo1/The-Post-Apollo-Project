import QtQuick
import Quickshell
import "../../../services/projects"

// M10r: DISPOSABLE Quickshell manual acceptance surface.
// Loaded only by an explicit test runner, NEVER by shell.qml.
// The underlying M10q bridge speaks exclusively to handoff-test.db.
// It has no capability to open live TASKS files or enable SQLite writes.
Scope {
    id: harness
    property string fixturePath: ""
    property string writerId: ""
    property string observation: "NOT STARTED // TEST ONLY"
    property int observationCount: 0
    readonly property bool liveStorageAuthorized: false
    readonly property bool migrationAuthorized: false
    readonly property bool remoteSyncAuthorized: false

    function dispatch(action) {
        if (action === "START") {
            fixturePath = fixtureInput.text.trim();
            writerId = writerInput.text.trim();
            return rehearsal.beginRehearsal();
        }
        if (action === "STATUS") return rehearsal.inspectFixture();
        if (action === "STAGE") return rehearsal.simulateStage("synthetic-stage-m10r-001");
        if (action === "FREEZE") return rehearsal.simulateFreeze();
        if (action === "SAVE OK")
            return rehearsal.simulateSaveCallback("synthetic-stage-m10r-001",true);
        if (action === "SAVE FAIL")
            return rehearsal.simulateSaveCallback("synthetic-stage-m10r-001",false);
        if (action === "STOP") {
            rehearsal.stopRehearsal();
            return true;
        }
        return false;
    }

    TaskSqliteAdmissionRehearsal {
        id: rehearsal
        fixturePath: harness.fixturePath
        writerId: harness.writerId
        onObserved: {
            harness.observationCount++;
            harness.observation = rehearsal.status + " // " + rehearsal.phase
                + (rehearsal.pendingStage ? " // PENDING" : "")
                + (rehearsal.errorCode ? " // " + rehearsal.errorCode : "");
        }
    }

    PanelWindow {
        id: testPanel
        visible: true
        implicitWidth: 500
        implicitHeight: 350
        anchors { top: true; left: true }
        color: "#1B0623"

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            border.width: 1

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 9

                Text {
                    text: "M10r // SQLITE ADMISSION REHEARSAL"
                    color: "#C74EC7"
                    font.pixelSize: 14
                    font.bold: true
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "DISPOSABLE TEST ONLY // NO LIVE TASKS / NO MIGRATION"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
                Text {
                    text: "EXPLICIT PRIVATE PATH // handoff-test.db"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: fixtureInput
                        anchors.fill: parent
                        anchors.margins: 6
                        text: ""
                        color: "#DCF3FA"
                        font.pixelSize: 11
                        selectByMouse: true
                        onEditingFinished: harness.fixturePath = text.trim()
                    }
                }
                Text {
                    text: "TEST WRITER ID // 8-96 permitted characters"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: writerInput
                        anchors.fill: parent
                        anchors.margins: 6
                        text: ""
                        color: "#DCF3FA"
                        font.pixelSize: 11
                        selectByMouse: true
                        onEditingFinished: harness.writerId = text.trim()
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 5
                    Repeater {
                        model: ["START","STATUS","STAGE","FREEZE","SAVE OK","SAVE FAIL","STOP"]
                        Rectangle {
                            id: action
                            required property string modelData
                            width: 65
                            height: 27
                            color: area.pressed ? "#C74EC7" : "#1B0623"
                            border.color: "#55CFCA"
                            Text {
                                anchors.centerIn: parent
                                text: action.modelData
                                color: area.pressed ? "#1B0623" : "#DCF3FA"
                                font.pixelSize: 9
                            }
                            MouseArea {
                                id: area
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                onClicked: harness.dispatch(action.modelData)
                            }
                        }
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: harness.observation
                    color: "#DCF3FA"
                    font.pixelSize: 11
                }
                Text {
                    width: parent.width
                    text: "SQLite authorized: NO // Live changes: NO // Remote: NO"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                }
            }
        }
    }
}
