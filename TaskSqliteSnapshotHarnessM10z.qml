import QtQuick
import Quickshell
import "./services/projects"

// M10z explicit-use ROOT config, e.g. qs -p /path/to/repo/TaskSqliteSnapshotHarnessM10z.qml
// Do NOT import into shell.qml. Separate instance, read-only TEST DB only.
Scope {
    id: harness

    TaskSqliteSnapshotBridgeM10y {
        id: snapshotProbe
        onInspected: {
            // Do not log task text or filesystem paths.
            harness.observations += 1;
        }
    }
    property int observations: 0

    PanelWindow {
        visible: true
        implicitWidth: 540
        implicitHeight: 320
        anchors { top: true; left: true }
        color: "#1B0623"

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            border.width: 2

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 10
                Text {
                    text: "M10z // SQLITE SNAPSHOT RUNTIME TEST"
                    color: "#C74EC7"
                    font.pixelSize: 14
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "ISOLATED CONFIG // READ ONLY // NEVER LIVE TASKS"
                    font.pixelSize: 11
                    color: "#F2BE4E"
                    wrapMode: Text.WordWrap
                }
                Text {
                    text: "Enter an existing private m10y-snapshot-test/tasks.db path"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: pathInput
                        anchors.fill: parent
                        anchors.margins: 6
                        text: ""
                        font.pixelSize: 11
                        color: "#DCF3FA"
                        selectByMouse: true
                        clip: true
                    }
                }
                Row {
                    height: 29
                    spacing: 6
                    Repeater {
                        model: ["READ","CANCEL","CLEAR"]
                        Rectangle {
                            required property string modelData
                            width: 90
                            height: 29
                            color: hit.pressed ? "#C74EC7" : "#1B0623"
                            border.width: 1
                            border.color: "#55CFCA"
                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                color: hit.pressed ? "#1B0623" : "#DCF3FA"
                                font.pixelSize: 11
                            }
                            MouseArea {
                                id: hit
                                anchors.fill: parent
                                onClicked: {
                                    if (modelData === "READ") {
                                        snapshotProbe.candidatePath = pathInput.text.trim();
                                        snapshotProbe.requestSnapshot();
                                    } else if (modelData === "CANCEL") {
                                        snapshotProbe.cancelSnapshot();
                                    } else {
                                        snapshotProbe.clearSnapshot();
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    text: "PROCESS // " + snapshotProbe.status
                          + (snapshotProbe.busy ? " // BUSY" : "")
                    color: snapshotProbe.status === "ERROR" ? "#ED981A" : "#DCF3FA"
                    font.pixelSize: 11
                }
                Text {
                    text: "ERROR // " + (snapshotProbe.errorCode || "NONE")
                    color: "#F2BE4E"
                    font.pixelSize: 10
                }
                Text {
                    text: "SNAPSHOT // " + snapshotProbe.snapshot.total
                          + " TASKS // " + snapshotProbe.snapshot.remaining
                          + " REMAINING // " + snapshotProbe.snapshot.completed + " DONE"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Text {
                    text: "INSPECTIONS // " + harness.observations
                          + " // WRITABLE: " + snapshotProbe.snapshot.writable
                    color: "#DCF3FA"
                    font.pixelSize: 10
                }
                Text {
                    text: "SQLITE WRITE: NO // GITHUB: NO // MIGRATION: NO"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                }
            }
        }
    }
}
