import QtQuick
import Quickshell
import Quickshell.Wayland
import "../../../services/projects"

// M12e STANDALONE MANUAL NATIVE OBSERVATION ONLY.
// Uses the existing M11g isolated host+FileView, without creating a second
// writer. NOT loaded by shell.qml, not connected to production TASKS.
// The M11g bridge restricts the user-entered path to a private disposable
// m11e-fileview-test/fixture-only.json fixture. Native testing is a separate
// operator-approved action, never launched by CI.
Scope {
    id: lab
    property string fixturePath: ""
    property string writerId: ""
    property bool bootstrapTestAuthority: false
    property var observations: []
    readonly property bool liveWriterAuthorized: false
    readonly property bool productionActivation: false
    readonly property bool sqliteTaskMigrationAuthorized: false
    readonly property bool nativeStageAttributionProven: false

    function capture() {
        // Deliberately record counters/tags only: no file contents, keys,
        // task text, source path, writer ID or native host payload.
        var summary = bridge.nativeSummary;
        observations = observations.concat([{
            sequence: observations.length + 1,
            state: bridge.fileState,
            phase: bridge.phase,
            saveChains: summary.saveChains,
            evidenceLabel: summary.label
        }]).slice(-24);
    }

    function dispatch(action) {
        if (action === "NEW TEST") {
            fixturePath = inputPath.text.trim();
            writerId = inputWriter.text.trim();
            bootstrapTestAuthority = true;
            return bridge.startTestSession();
        }
        if (action === "EXISTING") {
            fixturePath = inputPath.text.trim();
            writerId = inputWriter.text.trim();
            bootstrapTestAuthority = false;
            return bridge.startTestSession();
        }
        if (action === "INCREMENT") return bridge.incrementSynthetic();
        if (action === "FREEZE") return bridge.freezeTest();
        if (action === "STOP") { bridge.stopTest(); return true; }
        return false;
    }

    TaskFileViewHostBridgeM11g {
        id: bridge
        fixturePath: lab.fixturePath
        writerId: lab.writerId
        bootstrapTestAuthority: lab.bootstrapTestAuthority
        onObserved: lab.capture()
    }

    PanelWindow {
        id: panel
        visible: true
        implicitWidth: 580
        implicitHeight: 430
        exclusiveZone: 0
        focusable: true
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
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
                spacing: 8
                Text {
                    text: "M12e // NATIVE CALLBACK ATTRIBUTION LAB"
                    font.pixelSize: 14
                    font.bold: true
                    color: "#C74EC7"
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "DISPOSABLE M11g FILEVIEW ONLY // CALLBACK TAGS ARE NOT DURABLE STAGE IDS"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
                Text {
                    text: "PRIVATE SYNTHETIC FILE // m11e-fileview-test/fixture-only.json"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: inputPath
                        anchors.fill: parent
                        anchors.margins: 6
                        focus: true
                        color: "#DCF3FA"
                        selectByMouse: true
                        font.pixelSize: 11
                        text: ""
                    }
                }
                Text {
                    text: "TEST WRITER ID // 8-96 ASCII CHARACTERS"
                    color: "#55CFCA"
                    font.pixelSize: 10
                }
                Rectangle {
                    width: parent.width
                    height: 30
                    color: "#1B0623"
                    border.color: "#55CFCA"
                    TextInput {
                        id: inputWriter
                        anchors.fill: parent
                        anchors.margins: 6
                        color: "#DCF3FA"
                        selectByMouse: true
                        font.pixelSize: 11
                        text: ""
                    }
                }
                Flow {
                    width: parent.width
                    spacing: 5
                    Repeater {
                        model: ["NEW TEST", "EXISTING", "INCREMENT", "FREEZE", "STOP"]
                        Rectangle {
                            id: action
                            required property string modelData
                            width: 104
                            height: 28
                            color: area.pressed ? "#C74EC7" : "#1B0623"
                            border.color: "#55CFCA"
                            Text {
                                anchors.centerIn: parent
                                text: action.modelData
                                color: area.pressed ? "#1B0623" : "#DCF3FA"
                                font.pixelSize: 10
                            }
                            MouseArea {
                                id: area
                                anchors.fill: parent
                                onClicked: lab.dispatch(action.modelData)
                            }
                        }
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: "#DCF3FA"
                    font.pixelSize: 11
                    text: "PHASE: " + bridge.phase + "  // FILE: " + bridge.fileState
                          + "  // COUNTER: " + bridge.confirmedCounter
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: "#DCF3FA"
                    font.pixelSize: 11
                    text: "SAVED CHAINS: " + bridge.nativeSummary.saveChains
                          + " // " + bridge.nativeSummary.label
                }
                Text {
                    width: parent.width
                    wrapMode: Text.Wrap
                    color: "#55CFCA"
                    font.pixelSize: 11
                    text: bridge.nativeRecent
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: "#F2BE4E"
                    font.pixelSize: 11
                    text: "NATIVE STAGE ATTRIBUTION: NOT PROVEN // PRODUCTION AUTHORITY: FALSE"
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    color: "#DCF3FA"
                    font.pixelSize: 10
                    text: "Independent journal settlement and fresh owner identity are necessary. " +
                          "No native event label alone can certify the matching stage."
                }
            }
        }
    }
}
