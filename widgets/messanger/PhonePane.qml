import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

// PHONE shares the existing Social workspace. This is a read-only readiness
// view, not a BlueFerry session owner or permission/identity authority.
Rectangle {
    id: phonePane
    color: Colors.black
    border.width: 1
    border.color: Colors.green
    clip: true

    property string selectedSection: "DEVICE"
    property string probeStatus: "NOT CHECKED"
    property var readiness: ({})

    // BlueFerry's GetStatus is a self-report from an already-running daemon.
    // Active MAP/PBAP sessions do not prove content authorization or ownership.
    function profileText(key) {
        if (probeStatus !== "READINESS CHECKED"
                || readiness.backendObservation !== "REPORTED")
            return "NOT VERIFIED";
        return readiness[key] === true ? "ACTIVE (BACKEND REPORT)" :
               readiness[key] === false ? "INACTIVE (BACKEND REPORT)" :
               "NOT VERIFIED";
    }

    function refreshReadiness() {
        if (!visible || readinessProcess.running)
            return;
        probeStatus = "CHECKING";
        readiness = ({});
        readinessProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/BlueFerryReadiness.py")
        ];
        readinessProcess.running = true;
    }

    onVisibleChanged: {
        if (visible) {
            selectedSection = "DEVICE";
            refreshReadiness();
        }
    }

    Process {
        id: readinessProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible)
                    return;
                try {
                    var next = JSON.parse(String(text || ""));
                    if (next.schema !== "post-apollo.social.phone-readiness.v0"
                            || next.execution !== "READ_ONLY"
                            || next.contentAuthorized !== false
                            || next.phoneLink !== "UNVERIFIED")
                        throw new Error("Unexpected readiness schema");
                    var states = [
                        "NOT_RUNNING", "NO_OWNER", "UNAVAILABLE", "REPORTED"
                    ];
                    if (states.indexOf(next.backendObservation) < 0)
                        throw new Error("Unknown backend status");
                    if (next.backendObservation === "REPORTED") {
                        if (typeof next.mapSessionActive !== "boolean"
                                || typeof next.pbapSessionActive !== "boolean")
                            throw new Error("Invalid profile status");
                    } else if (next.mapSessionActive !== null
                               || next.pbapSessionActive !== null) {
                        throw new Error("Unexpected profile status");
                    }
                    phonePane.readiness = next;
                    phonePane.probeStatus = "READINESS CHECKED";
                } catch (error) {
                    phonePane.readiness = ({});
                    phonePane.probeStatus = "READINESS UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode) {
            if (phonePane.visible && exitCode !== 0)
                phonePane.probeStatus = "READINESS UNAVAILABLE";
        }
    }

    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 38
        color: Colors.dark
        border.width: 1
        border.color: Colors.green

        Text {
            anchors.centerIn: parent
            text: "PHONE // READINESS"
            color: Colors.green
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 12
            font.bold: true
        }
    }

    Row {
        id: workspace
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 10
        spacing: 10

        Column {
            id: sectionRail
            width: Math.min(140, Math.max(96, Math.floor(workspace.width * 0.27)))
            spacing: 8

            Repeater {
                model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS", "PERMISSIONS"]
                delegate: ActionButton {
                    required property string modelData
                    width: sectionRail.width
                    height: 38
                    label: modelData
                    labelPixelSize: 10
                    labelMinimumPixelSize: 8
                    accentColor: Colors.green
                    selected: phonePane.selectedSection === modelData
                    onTriggered: phonePane.selectedSection = modelData
                }
            }
        }

        Column {
            id: sectionContent
            width: Math.max(1, workspace.width - sectionRail.width - workspace.spacing)
            spacing: 13

            Text {
                width: parent.width
                text: phonePane.selectedSection + " // " + phonePane.probeStatus
                color: Colors.green
                font.pixelSize: 11
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection === "DEVICE"
                text: "BlueFerry package: " +
                      (phonePane.probeStatus !== "READINESS CHECKED" ? "NOT CHECKED" :
                       phonePane.readiness.blueferryInstalled ? "INSTALLED" : "NOT FOUND") +
                      "\nBluetooth service: " +
                      String(phonePane.readiness.bluetoothService || "UNKNOWN").toUpperCase() +
                      "\nBluetooth controller: " +
                      (phonePane.readiness.controllerPowered === true ? "POWERED" :
                       phonePane.readiness.controllerPowered === false ? "OFF" : "UNKNOWN") +
                      "\nBlueFerry setup file: " +
                      (phonePane.probeStatus !== "READINESS CHECKED" ? "NOT CHECKED" :
                       phonePane.readiness.configurationPresent ? "PRESENT" : "MISSING") +
                      "\nBackend service: " +
                      String(phonePane.readiness.backendService || "UNKNOWN").toUpperCase() +
                      "\nBlueFerry D-Bus: " +
                      String(phonePane.readiness.backendObservation || "UNAVAILABLE") +
                      "\nMAP session: " + phonePane.profileText("mapSessionActive") +
                      "\nPBAP session: " + phonePane.profileText("pbapSessionActive") +
                      "\nTrusted phone link: UNVERIFIED"
                color: Colors.white
                font.pixelSize: 11
                wrapMode: Text.WrapAnywhere
                lineHeight: 1.4
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection !== "DEVICE"
                text: phonePane.selectedSection === "CALLS"
                      ? "No call controls are connected to Post-Apollo. Audio heard through Fedora does not authorize dialing, answering, or hangup from Social."
                      : phonePane.selectedSection === "MESSAGES"
                      ? "MESSAGES LOCKED. No inbox access, message import, receiving, or sending is enabled in Social."
                      : phonePane.selectedSection === "CONTACTS"
                      ? "CONTACTS LOCKED. No address-book reading, syncing, or importing is enabled in Social."
                      : "Bluetooth pairing is not a Social permission grant. Verified person, organization, phone device, and phone line authorization must be established before protected actions can be enabled."
                color: Colors.white
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                lineHeight: 1.3
            }

            ActionButton {
                width: Math.min(190, sectionContent.width)
                height: 38
                visible: phonePane.selectedSection === "DEVICE"
                label: "REFRESH READINESS"
                labelPixelSize: 9
                accentColor: Colors.green
                interactive: !readinessProcess.running
                onTriggered: phonePane.refreshReadiness()
            }

            Text {
                width: parent.width
                text: "READ-ONLY // NO PAIRING, MESSAGE, CONTACT, CALL OR ACCOUNT CHANGES"
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
}
