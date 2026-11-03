import QtQuick
import Quickshell
import Quickshell.Wayland
import "./services/hub"

// M13k // Never imported by normal shell.qml.
// The button ONLY works in a separate private disposable D-Bus/HOME runner;
// on normal Fedora it is disabled and cannot reach the host.
Scope {
    id: harness
    TaskEncryptedDraftHostBridgeM13k {
        id: bridge
    }
    PanelWindow {
        exclusiveZone: 0
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        focusable: true
        visible: true
        implicitWidth: 490
        implicitHeight: 240
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
                spacing: 12
                Text {
                    text: "TASKS // ENCRYPTED DRAFT HOST M13k"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: "PRIVATE SYNTHETIC ONLY // NO REAL TASKS"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "RECOVERY // DISABLED   SOURCE WRITES // OFF"
                    color: "#DCF3FA"
                    font.pixelSize: 11
                }
                Text {
                    width: parent.width
                    text: "HOST // " + bridge.status
                    color: "#55CFCA"
                    font.pixelSize: 11
                    wrapMode: Text.WrapAnywhere
                }
                Rectangle {
                    width: 218
                    height: 34
                    color: action.pressed ? "#C74EC7" : "#1B0623"
                    border.color: "#55CFCA"
                    Text {
                        anchors.centerIn: parent
                        text: "RUN PRIVATE SYNTHETIC"
                        color: action.pressed ? "#1B0623" : "#DCF3FA"
                        font.pixelSize: 11
                    }
                    MouseArea {
                        id: action
                        anchors.fill: parent
                        enabled: bridge.syntheticCIEligible && !bridge.busy
                        onClicked: bridge.startSynthetic()
                    }
                }
                Text {
                    width: parent.width
                    text: bridge.syntheticCIEligible
                          ? "PRIVATE TEST BUS // VERIFIED BY HOST"
                          : "NO PRIVATE TEST SESSION // BUTTON LOCKED"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
