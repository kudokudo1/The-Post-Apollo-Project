import QtQuick
import Quickshell
import Quickshell.Wayland
import "./services/hub"

// M13i standalone source-only review panel, NEVER imported by shell.qml.
// Uses the same read-only provider bridge that the TASKS singleton exposes.
// Click only probes whether org.freedesktop.secrets has an existing owner.
// It cannot store a recovery draft, unlock the keyring or mutate tasks.
Scope {
    id: harness

    TaskEncryptedRecoveryBridgeM13i {
        id: bridge
    }

    PanelWindow {
        exclusiveZone: 0
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        focusable: true
        visible: true
        implicitWidth: 490
        implicitHeight: 244
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
                    text: "TASKS // ENCRYPTED RECOVERY M13i"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }

                Text {
                    width: parent.width
                    text: "READ-ONLY PROVIDER CHECK // NO DRAFTS OR KEYS"
                    color: "#F2BE4E"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Text {
                    text: "RECOVERY // DISABLED   WRITES // DISABLED"
                    color: "#DCF3FA"
                    font.pixelSize: 12
                }

                Text {
                    width: parent.width
                    text: "PROVIDER // " + bridge.providerStatus
                    color: "#55CFCA"
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Rectangle {
                    width: 186
                    height: 34
                    radius: 2
                    color: action.pressed ? "#C74EC7" : "#1B0623"
                    border.color: "#55CFCA"
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: bridge.checking ? "CHECKING..." : "CHECK PROVIDER"
                        font.pixelSize: 12
                        color: action.pressed ? "#1B0623" : "#DCF3FA"
                    }
                    MouseArea {
                        id: action
                        anchors.fill: parent
                        enabled: !bridge.checking
                        onClicked: bridge.inspectProvider()
                    }
                }

                Text {
                    width: parent.width
                    text: "UNLOCK: UNVERIFIED // PERSIST: OFF // TASKS: UNCHANGED"
                    color: "#F2BE4E"
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
