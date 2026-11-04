import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"

// PHONE stays in Social. CONNECT PHONE performs an explicit read-only check
// of existing provider observations; no pairing, permission or link is granted.
Rectangle {
    id: phonePane
    color: Colors.black
    border.width: 1
    border.color: Colors.green
    clip: true

    property string selectedSection: "DEVICE"
    property string probeStatus: "NOT CHECKED"
    property var readiness: ({})
    property string setupState: "NOT STARTED"
    property var setupReport: ({})
    property bool detailsOpen: false
    property string nativeSetupTarget: ""
    property string nativeSetupStatus: "IDLE"

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

    function startSetup() {
        if (!visible || setupProcess.running)
            return;
        setupState = "CHECKING";
        setupReport = ({});
        nativeSetupStatus = "IDLE";
        nativeSetupTarget = "";
        setupProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneSetupReadiness.py"),
            "--check"
        ];
        setupProcess.running = true;
    }

    function openNativeSetup(target) {
        if (!visible || setupState !== "CHECKED" || nativeSetupProcess.running
                || (target !== "iphone" && target !== "android"))
            return;
        nativeSetupTarget = target;
        nativeSetupStatus = "OPENING";
        nativeSetupProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneNativeSetupLaunch.py"),
            "--open", target
        ];
        nativeSetupProcess.running = true;
    }

    onVisibleChanged: {
        if (visible) {
            selectedSection = "DEVICE";
            setupState = "NOT STARTED";
            setupReport = ({});
            detailsOpen = false;
            nativeSetupStatus = "IDLE";
            nativeSetupTarget = "";
            // No pairing or inventory action runs automatically on menu open.
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

    Process {
        id: setupProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.setupState !== "CHECKING")
                    return;
                try {
                    var report = JSON.parse(String(text || ""));
                    if (report.schema !== "post-apollo.phone.setup-check.v0"
                            || report.execution !== "READ_ONLY_CHECK"
                            || report.trustedPhoneLink !== "UNVERIFIED"
                            || report.routeEligible !== false
                            || report.contentAccessEnabled !== false
                            || ["BRIDGE_REPORTED", "NO_BRIDGE_REPORTED"].indexOf(report.status) < 0
                            || !report.providers
                            || !report.providers.BLUEFERRY
                            || !report.providers.KDECONNECT)
                        throw new Error("Unexpected phone setup report");
                    phonePane.setupReport = report;
                    phonePane.setupState = "CHECKED";
                } catch (error) {
                    phonePane.setupReport = ({});
                    phonePane.setupState = "UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode) {
            if (phonePane.visible && phonePane.setupState === "CHECKING" && exitCode !== 0) {
                phonePane.setupReport = ({});
                phonePane.setupState = "UNAVAILABLE";
            }
        }
    }

    Process {
        id: nativeSetupProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.nativeSetupStatus !== "OPENING")
                    return;
                try {
                    var result = JSON.parse(String(text || ""));
                    if (result.schema !== "post-apollo.phone.native-setup-launch.v0"
                            || result.execution !== "USER_INITIATED_NATIVE_SETUP"
                            || result.target !== phonePane.nativeSetupTarget
                            || ["OPEN_REQUESTED", "CLIENT_UNAVAILABLE", "LAUNCH_FAILED"].indexOf(result.status) < 0
                            || result.trustedPhoneLink !== "UNVERIFIED"
                            || result.routeEligible !== false
                            || result.contentAccessEnabled !== false)
                        throw new Error("Invalid native setup handoff");
                    phonePane.nativeSetupStatus = result.status;
                } catch (error) {
                    phonePane.nativeSetupStatus = "LAUNCH_FAILED";
                }
            }
        }
        onExited: function(exitCode) {
            if (phonePane.visible && phonePane.nativeSetupStatus === "OPENING"
                    && exitCode !== 0)
                phonePane.nativeSetupStatus = "LAUNCH_FAILED";
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
            text: "PHONE // CONNECT"
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
                model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]
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
                text: phonePane.selectedSection + " // " +
                      (phonePane.selectedSection === "DEVICE"
                       ? phonePane.setupState : "NOT CONNECTED")
                color: Colors.green
                font.pixelSize: 11
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection === "DEVICE"
                text: phonePane.setupState === "CHECKING"
                      ? "Checking existing phone bridges..."
                      : phonePane.setupState === "CHECKED"
                        && phonePane.setupReport.status === "BRIDGE_REPORTED"
                      ? "A phone bridge responded. Social has NOT linked a phone or enabled private content."
                      : phonePane.setupState === "CHECKED"
                      ? "No active phone bridge was reported. Pair through your phone and desktop settings if needed."
                      : phonePane.setupState === "UNAVAILABLE"
                      ? "Could not check existing phone bridges. Try again."
                      : "One setup action. Use your existing phone pairing and normal phone permissions."
                color: Colors.white
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }

            ActionButton {
                id: connectPhoneAction
                width: Math.min(190, sectionContent.width)
                height: 38
                visible: phonePane.selectedSection === "DEVICE"
                label: setupProcess.running ? "CHECKING..." : "CONNECT PHONE"
                labelPixelSize: 10
                accentColor: Colors.magenta
                interactive: !setupProcess.running
                onTriggered: phonePane.startSetup()
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection === "DEVICE"
                text: "Choose iPhone or Android below to open its existing setup app. Phone-side pairing stays under your control; Social message access is not enabled yet."
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection === "DEVICE"
                         && phonePane.setupState === "CHECKED"
                text: "Bluetooth bridge: " +
                      String((phonePane.setupReport.providers || {}).BLUEFERRY
                             ? phonePane.setupReport.providers.BLUEFERRY.state
                             : "UNAVAILABLE") +
                      "\nNetwork bridge: " +
                      String((phonePane.setupReport.providers || {}).KDECONNECT
                             ? phonePane.setupReport.providers.KDECONNECT.state
                             : "UNAVAILABLE") +
                      "\nSocial phone link: NOT VERIFIED"
                color: Colors.white
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            Row {
                width: sectionContent.width
                spacing: 8
                visible: phonePane.selectedSection === "DEVICE"
                         && phonePane.setupState === "CHECKED"

                ActionButton {
                    width: Math.max(72, (sectionContent.width - 8) / 2)
                    height: 38
                    label: "SET UP IPHONE"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    interactive: !nativeSetupProcess.running
                    onTriggered: phonePane.openNativeSetup("iphone")
                }

                ActionButton {
                    width: Math.max(72, (sectionContent.width - 8) / 2)
                    height: 38
                    label: "SET UP ANDROID"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    interactive: !nativeSetupProcess.running
                    onTriggered: phonePane.openNativeSetup("android")
                }
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection === "DEVICE"
                         && phonePane.nativeSetupStatus !== "IDLE"
                text: phonePane.nativeSetupStatus === "OPENING"
                      ? "Opening your phone setup app..."
                      : phonePane.nativeSetupStatus === "OPEN_REQUESTED"
                      ? "Native phone setup requested. Approve pairing in that app and on your phone, then use CONNECT PHONE to recheck. Social messages remain locked."
                      : phonePane.nativeSetupStatus === "CLIENT_UNAVAILABLE"
                      ? "The native setup app for that phone is not installed. No pairing changes made."
                      : "Could not launch the native phone setup app. No pairing changes made."
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }

            ActionButton {
                width: Math.min(190, sectionContent.width)
                height: 38
                visible: phonePane.selectedSection === "DEVICE"
                label: phonePane.detailsOpen ? "HIDE DETAILS" : "DETAILS"
                labelPixelSize: 9
                accentColor: Colors.green
                onTriggered: {
                    phonePane.detailsOpen = !phonePane.detailsOpen;
                    if (phonePane.detailsOpen)
                        phonePane.refreshReadiness();
                }
            }

            Text {
                width: parent.width
                visible: phonePane.selectedSection === "DEVICE" && phonePane.detailsOpen
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
                visible: phonePane.selectedSection === "DEVICE" && phonePane.detailsOpen
                label: "REFRESH READINESS"
                labelPixelSize: 9
                accentColor: Colors.green
                interactive: !readinessProcess.running
                onTriggered: phonePane.refreshReadiness()
            }

            Text {
                width: parent.width
                text: "READ-ONLY SETUP PREVIEW // NO PAIRING, MESSAGES, CONTACTS OR CALL CHANGES"
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
}
