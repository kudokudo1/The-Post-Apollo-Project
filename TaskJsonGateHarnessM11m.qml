import QtQuick
import Quickshell
import Quickshell.Wayland
import "./services/projects"

// M11m explicit standalone test only. NEVER imported by production shell.
// Requires a pre-existing, private m11l-tasks-copy/todo-copy.json test fixture.
Scope {
    id: harness
    property int observations: 0

    TaskJsonGateHostBridgeM11m {
        id: bridge
        onObserved: harness.observations++
    }

    PanelWindow {
        exclusiveZone: 0
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        focusable: true
        visible: true
        implicitWidth: 610
        implicitHeight: 438
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
                    text: "M11m // JSON FileView HOST TEST"
                    color: "#C74EC7"
                    font.pixelSize: 16
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "DISPOSABLE TASK COPY ONLY // PRODUCTION TASKS LOCKED OFF"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    text: "Pre-existing private .../m11l-tasks-copy/todo-copy.json"
                    color: "#55CFCA"
                    font.pixelSize: 11
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
                        focus: true
                        selectByMouse: true
                        clip: true
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 6
                    Repeater {
                        model: ["NEW TEST", "EXISTING", "INCREMENT", "FREEZE", "STOP"]
                        Rectangle {
                            id: button
                            required property string modelData
                            width: 108
                            height: 30
                            color: action.pressed ? "#C74EC7" : "#1B0623"
                            border.color: "#55CFCA"
                            border.width: 1
                            Text {
                                anchors.centerIn: parent
                                text: button.modelData
                                font.pixelSize: 11
                                color: action.pressed ? "#1B0623" : "#DCF3FA"
                            }
                            MouseArea {
                                id: action
                                anchors.fill: parent
                                onClicked: {
                                    if (button.modelData === "NEW TEST"
                                            || button.modelData === "EXISTING") {
                                        bridge.fixturePath = pathInput.text.trim();
                                        bridge.writerId = "m11m-quickshell-test-001";
                                        bridge.bootstrapTestAuthority =
                                            button.modelData === "NEW TEST";
                                        bridge.beginTest();
                                    } else if (button.modelData === "INCREMENT") {
                                        bridge.incrementTestTitle();
                                    } else if (button.modelData === "FREEZE") {
                                        bridge.freezeTest();
                                    } else if (button.modelData === "STOP") {
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
                    text: "FILE // " + bridge.fileState + " // EPOCH " + bridge.epoch
                    color: "#55CFCA"
                    font.pixelSize: 11
                }
                Text {
                    text: "CONFIRMED TEST TITLE COUNTER // " + bridge.confirmedCounter
                    color: "#DCF3FA"
                    font.pixelSize: 12
                }
                Text {
                    text: "TEST STAGE ELIGIBLE // " + bridge.testStageEligible
                        + " // OBSERVATIONS " + harness.observations
                    color: "#55CFCA"
                    font.pixelSize: 11
                }
                Text {
                    width: parent.width
                    text: "ERROR // " + (bridge.errorCode || "NONE")
                    color: "#F2BE4E"
                    font.pixelSize: 11
                    wrapMode: Text.WrapAnywhere
                }
                Text {
                    width: parent.width
                    text: "EVENTS // " + bridge.recentEvents.join(" / ")
                    color: "#DCF3FA"
                    font.pixelSize: 11
                    wrapMode: Text.WrapAnywhere
                    maximumLineCount: 4
                }
                Text {
                    text: "LIVE WRITER: FALSE // SQLITE: FALSE // MIGRATION: FALSE"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                }
            }
        }
    }
}
