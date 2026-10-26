import QtQuick
import Quickshell
import "./services/projects"

// Explicit use only: qs -p /absolute/repo/TaskFileViewHostHarnessM11g.qml
// Never mounted in production shell.qml. Only synthetic fixture increments.
Scope {
    id: harness
    property int observations: 0

    TaskFileViewHostBridgeM11g {
        id: bridge
        onObserved: harness.observations += 1
    }

    PanelWindow {
        visible: true
        implicitWidth: 580
        implicitHeight: 352
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
                    text: "M11g // OWNED FileView TEST"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "DISPOSABLE FIXTURE ONLY // NO LIVE TASKS // NO SQLITE CUTOVER"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    text: "Absolute private m11e-fileview-test/fixture-only.json path"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Rectangle {
                    width: parent.width
                    height: 32
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: pathInput
                        anchors.fill: parent
                        anchors.margins: 5
                        text: ""
                        font.pixelSize: 11
                        color: "#DCF3FA"
                        selectByMouse: true
                        clip: true
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: ["NEW TEST","EXISTING","INCREMENT","FREEZE","STOP"]
                        Rectangle {
                            id: control
                            required property string modelData
                            width: 101
                            height: 30
                            color: area.pressed ? "#C74EC7" : "#1B0623"
                            border.color: "#55CFCA"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: control.modelData
                                font.pixelSize: 11
                                color: area.pressed ? "#1B0623" : "#DCF3FA"
                            }
                            MouseArea {
                                id: area
                                anchors.fill: parent
                                onClicked: {
                                    if (control.modelData === "NEW TEST"
                                            || control.modelData === "EXISTING") {
                                        bridge.fixturePath = pathInput.text.trim();
                                        bridge.writerId = "m11g-quickshell-test-owner-001";
                                        bridge.bootstrapTestAuthority =
                                            control.modelData === "NEW TEST";
                                        bridge.startTestSession();
                                    } else if (control.modelData === "INCREMENT") {
                                        bridge.incrementSynthetic();
                                    } else if (control.modelData === "FREEZE") {
                                        bridge.freezeTest();
                                    } else if (control.modelData === "STOP") {
                                        bridge.stopTest();
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    text: "HOST // " + bridge.status + " // " + bridge.phase
                    color: "#DCF3FA"
                    font.pixelSize: 12
                }
                Text {
                    text: "FILE // " + bridge.fileState
                        + " // EPOCH " + bridge.epoch
                    color: "#55CFCA"
                    font.pixelSize: 11
                }
                Text {
                    text: "CONFIRMED SYNTHETIC COUNTER // " + bridge.confirmedCounter
                    color: "#DCF3FA"
                    font.pixelSize: 11
                }
                Text {
                    text: "STAGE ELIGIBLE IN TEST // " + bridge.testStageEligible
                          + " // INSPECTIONS " + harness.observations
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Text {
                    text: "ERROR // " + (bridge.errorCode || "NONE")
                    color: "#F2BE4E"
                    font.pixelSize: 10
                }
                Text {
                    text: "PRODUCTION AUTHORITY // FALSE // NO MIGRATION"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                }
            }
        }
    }
}
