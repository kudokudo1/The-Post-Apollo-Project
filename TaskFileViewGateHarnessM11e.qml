import QtQuick
import Quickshell
import "./services/projects"

// Explicit standalone Quickshell test configuration, NEVER shell.qml.
// M11e has one real FileView for a disposable SYNTHETIC TEST file only.
Scope {
    id: harness
    property int observations: 0

    TaskFileViewGateM11e {
        id: gate
        onObserved: harness.observations += 1
    }

    PanelWindow {
        visible: true
        implicitWidth: 550
        implicitHeight: 340
        anchors { top: true; left: true }
        color: "#1B0623"
        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            border.width: 2
            Column {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 11
                Text {
                    text: "M11e // DISPOSABLE FileView GATE"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "STANDALONE ONLY // NEVER LIVE TASKS // NO SQLITE"
                    wrapMode: Text.WordWrap
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
                Text {
                    text: "Existing m11e-fileview-test/fixture-only.json"
                    color: "#55CFCA"
                    font.pixelSize: 11
                }
                Rectangle {
                    width: parent.width
                    height: 32
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: fixtureInput
                        anchors.fill: parent
                        anchors.margins: 6
                        text: ""
                        font.pixelSize: 11
                        color: "#DCF3FA"
                        selectByMouse: true
                        clip: true
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 7
                    Repeater {
                        model: ["ATTACH","INCREMENT","FREEZE","RELOAD"]
                        Rectangle {
                            id: control
                            required property string modelData
                            width: 109
                            height: 30
                            border.width: 1
                            border.color: "#55CFCA"
                            color: hit.pressed ? "#C74EC7" : "#1B0623"
                            Text {
                                anchors.centerIn: parent
                                text: control.modelData
                                color: hit.pressed ? "#1B0623" : "#DCF3FA"
                                font.pixelSize: 11
                            }
                            MouseArea {
                                id: hit
                                anchors.fill: parent
                                onClicked: {
                                    if (control.modelData === "ATTACH") {
                                        gate.fixturePath = fixtureInput.text.trim();
                                        gate.attachTestFile();
                                    } else if (control.modelData === "INCREMENT") {
                                        gate.stageSyntheticIncrement();
                                    } else if (control.modelData === "FREEZE") {
                                        gate.freezeTestAdmission();
                                    } else if (control.modelData === "RELOAD") {
                                        gate.reloadTestFile();
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    text: "PHASE // " + gate.phase
                    color: gate.phase === "RECOVERY_REVIEW" ? "#ED981A" : "#DCF3FA"
                    font.pixelSize: 12
                }
                Text {
                    text: "REASON // " + (gate.reason || "NONE")
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
                Text {
                    text: "CONFIRMED COUNTER // " + gate.confirmedCounter
                          + "  // SAVES // " + gate.completedWrites
                    color: "#55CFCA"
                    font.pixelSize: 11
                }
                Text {
                    text: "TEST STAGE AVAILABLE // " + gate.testStageAvailable
                          + "  // OBSERVATIONS // " + harness.observations
                    color: "#DCF3FA"
                    font.pixelSize: 10
                }
                Text {
                    text: "LIVE WRITER: NO // SQLITE: NO // GITHUB: NO"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
            }
        }
    }
}
