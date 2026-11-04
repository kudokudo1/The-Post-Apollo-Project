import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "../weather" as WeatherStage

// PHONE stays in Social. CONNECT PHONE performs an explicit read-only check
// of existing provider observations; no pairing, permission or link is granted.
Rectangle {
    id: phonePane
    color: stageHoleActive ? "transparent" : Colors.black
    border.width: 1
    border.color: Colors.green
    clip: true

    property string selectedSection: "MESSAGES"
    property string probeStatus: "NOT CHECKED"
    property var readiness: ({})
    property string setupState: "NOT STARTED"
    property var setupReport: ({})
    property bool detailsOpen: false
    property string nativeSetupTarget: ""
    property string nativeSetupStatus: "IDLE"
    property var savedBridgeState: ({})
    property string savedBridgeCheck: "NOT CHECKED"
    property var phoneAudioStatus: ({})
    property string phoneAudioCheck: "NOT CHECKED"
    property string phoneAudioResult: "IDLE"

    function refreshPhoneAudioControls() {
        if (!visible || audioStatusProcess.running || audioActionProcess.running)
            return;
        phoneAudioCheck = "CHECKING";
        phoneAudioStatus = ({});
        audioStatusProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneAudioControls.py"),
            "--status"
        ];
        audioStatusProcess.running = true;
    }

    function changePhoneAudio(family, selection) {
        if (!visible || selectedSection !== "DEVICE"
                || setupState !== "CHECKED" || stageWanted
                || audioActionProcess.running || audioStatusProcess.running
                || phoneAudioCheck !== "CHECKED"
                || phoneAudioStatus.canAdjust !== true)
            return;
        if (family === "media" && ["phone", "pc", "auto"].indexOf(selection) < 0)
            return;
        if (family === "calls" && ["enable", "disable"].indexOf(selection) < 0)
            return;
        if (family !== "media" && family !== "calls")
            return;
        if (family === "calls" && selection === "enable"
                && phoneAudioStatus.ofonoActive !== true) {
            phoneAudioResult = "CALLS_PREREQUISITES_MISSING";
            return;
        }
        phoneAudioResult = "UPDATING";
        audioActionProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneAudioControls.py"),
            "--set", family, selection
        ];
        audioActionProcess.running = true;
    }

    function phoneAudioResultText() {
        if (phoneAudioResult === "UPDATING")
            return "Applying your phone audio preference...";
        if (phoneAudioResult === "PREFERENCE_SAVED")
            return "Preference saved by BlueFerry. Actual playback and call availability depend on the iPhone and audio services.";
        if (phoneAudioResult === "CALLS_PREREQUISITES_MISSING")
            return "Calls on this computer need oFono/HFP support. No change made. Phone media routing works separately.";
        if (phoneAudioResult === "NOT_CONFIRMED")
            return "Requested, but BlueFerry did not confirm the saved preference.";
        if (phoneAudioResult === "CHANGE_FAILED"
                || phoneAudioResult === "CLIENT_UNAVAILABLE"
                || phoneAudioResult === "BRIDGE_UNAVAILABLE")
            return "Could not change phone audio. Existing routing was not intentionally reset.";
        return "";
    }

    function refreshSavedBridgeState() {
        if (!visible || savedBridgeProcess.running)
            return;
        savedBridgeCheck = "CHECKING";
        savedBridgeState = ({});
        savedBridgeProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneSavedBridgeState.py"),
            "--inspect"
        ];
        savedBridgeProcess.running = true;
    }
    property bool stageWanted: false
    property string stageState: "IDLE"
    property int stagePollCount: 0
    property int stageHostX: 0
    property int stageHostY: 0
    property int stageHostWidth: 0
    property int stageHostHeight: 0
    onStageHostXChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    onStageHostYChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    onStageHostWidthChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    onStageHostHeightChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    readonly property int stageHoleX: Math.round(phoneChatFeed.x + 10)
    readonly property int stageHoleY: Math.round(
        phoneChatFeed.y + setupHeader.height + setupColumn.implicitHeight + 24)
    readonly property int stageHoleWidth: Math.round(phoneChatFeed.width - 20)
    readonly property int stageHoleHeight: Math.round(height - stageHoleY - 12)
    readonly property bool stageHoleValid:
        stageHoleX >= 0 && stageHoleY >= 0
        && stageHoleWidth >= 200 && stageHoleHeight >= 120
        && stageHoleX + stageHoleWidth <= width
        && stageHoleY + stageHoleHeight <= height
    readonly property bool stageHoleActive:
        visible && selectedSection === "DEVICE" && stageWanted
        && stageState === "ALIGNED" && stageHoleValid

    function closeStagedSetup() {
        if (!stageWanted) return;
        stageWanted = false;
        stageState = "IDLE";
        stagePollCount = 0;
        if (visible && selectedSection === "DEVICE")
            refreshSavedBridgeState();
        if (!stageCloseProcess.running) {
            stageCloseProcess.command = [
                "python3",
                Quickshell.shellPath("services/phone/PhoneStageDirector.py"),
                "--close"
            ];
            stageCloseProcess.running = true;
        }
    }

    function syncStagedSetup() {
        if (!stageWanted || !visible || selectedSection !== "DEVICE"
                || !stageHoleValid || stageProcess.running)
            return;
        if (stageState === "ALIGNED") stagePollCount = 0;
        else stagePollCount += 1;
        if (stagePollCount > 40) {
            stageWanted = false;
            stageState = "UNAVAILABLE";
            return;
        }
        stageProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneStageDirector.py"),
            "--sync",
            String(Math.round(x + stageHoleX)),
            String(Math.round(y + stageHoleY)),
            String(stageHoleWidth),
            String(stageHoleHeight)
        ];
        stageProcess.running = true;
    }

    onSelectedSectionChanged: {
        if (selectedSection !== "DEVICE") closeStagedSetup();
    }
    onStageHoleXChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    onStageHoleYChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    onStageHoleWidthChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }
    onStageHoleHeightChanged: {
        if (stageWanted) stageState = "POSITIONING";
    }

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
        if (!visible || setupProcess.running || stageWanted)
            return;
        selectedSection = "DEVICE";
        setupState = "CHECKING";
        setupReport = ({});
        nativeSetupStatus = "IDLE";
        nativeSetupTarget = "";
        refreshSavedBridgeState();
        refreshPhoneAudioControls();
        setupProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneSetupReadiness.py"),
            "--check"
        ];
        setupProcess.running = true;
    }

    function openNativeSetup(target) {
        if (!visible || setupState !== "CHECKED" || nativeSetupProcess.running
                || stageWanted
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
        if (!visible) closeStagedSetup();
        if (visible) {
            selectedSection = "MESSAGES";
            setupState = "NOT STARTED";
            setupReport = ({});
            detailsOpen = false;
            nativeSetupStatus = "IDLE";
            nativeSetupTarget = "";
            savedBridgeCheck = "NOT CHECKED";
            savedBridgeState = ({});
            phoneAudioStatus = ({});
            phoneAudioCheck = "NOT CHECKED";
            phoneAudioResult = "IDLE";
            stageWanted = false;
            stageState = "IDLE";
            stagePollCount = 0;
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
        id: savedBridgeProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.savedBridgeCheck !== "CHECKING")
                    return;
                try {
                    var next = JSON.parse(String(text || ""));
                    var states = [
                        "NO_LOCAL_CONFIGURATION", "CONFIGURATION_PRESENT_BACKEND_INACTIVE",
                        "CONFIGURATION_PRESENT_BACKEND_UNVERIFIED", "BACKEND_REPORTED",
                        "UNAVAILABLE"
                    ];
                    var backendStates = [
                        "active", "inactive", "failed", "activating",
                        "deactivating", "unknown"
                    ];
                    var startupStates = [
                        "enabled", "enabled-runtime", "disabled", "static",
                        "indirect", "masked", "masked-runtime", "generated",
                        "linked", "linked-runtime", "transient", "alias", "unknown"
                    ];
                    if (next.schema !== "post-apollo.phone.saved-bridge-state.v0"
                            || next.execution !== "READ_ONLY_LOCAL_LIFECYCLE"
                            || states.indexOf(next.state) < 0
                            || next.trustedPhoneLink !== "UNVERIFIED"
                            || next.contentAccessEnabled !== false
                            || (next.configurationPresent !== null
                                && typeof next.configurationPresent !== "boolean")
                            || backendStates.indexOf(next.backendService) < 0
                            || startupStates.indexOf(next.startup) < 0
                            || ["ACTIVE_BACKEND_REPORT", "INACTIVE_BACKEND_REPORT",
                                "UNVERIFIED"].indexOf(next.messageProfile) < 0
                            || ["ACTIVE_BACKEND_REPORT", "INACTIVE_BACKEND_REPORT",
                                "UNVERIFIED"].indexOf(next.contactsProfile) < 0)
                        throw new Error("Unexpected local lifecycle result");
                    phonePane.savedBridgeState = next;
                    phonePane.savedBridgeCheck = "CHECKED";
                } catch (error) {
                    phonePane.savedBridgeState = ({});
                    phonePane.savedBridgeCheck = "UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode) {
            if (phonePane.visible && phonePane.savedBridgeCheck === "CHECKING"
                    && exitCode !== 0)
                phonePane.savedBridgeCheck = "UNAVAILABLE";
        }
    }

    Process {
        id: audioStatusProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.phoneAudioCheck !== "CHECKING")
                    return;
                try {
                    var r = JSON.parse(String(text || ""));
                    if (r.schema !== "post-apollo.phone.audio-controls.v0"
                            || r.execution !== "READ_ONLY"
                            || ["OBSERVED", "BRIDGE_UNAVAILABLE"].indexOf(r.result) < 0
                            || r.trustedPhoneLink !== "UNVERIFIED"
                            || r.contentAccessEnabled !== false
                            || ["PHONE", "PC", "AUTO", "UNKNOWN"].indexOf(r.mediaPreference) < 0
                            || ["PHONE", "PC", "UNKNOWN"].indexOf(r.mediaRoute) < 0
                            || (r.callsEnabled !== null && typeof r.callsEnabled !== "boolean")
                            || ["DISABLED", "UNAVAILABLE", "SEARCHING", "CONNECTING",
                                "READY", "BLUEZ_CONFLICT", "UNKNOWN"].indexOf(r.callsState) < 0
                            || typeof r.canAdjust !== "boolean"
                            || typeof r.ofonoActive !== "boolean"
                            || (r.result === "BRIDGE_UNAVAILABLE" && r.canAdjust !== false))
                        throw new Error("Invalid audio status");
                    phonePane.phoneAudioStatus = r;
                    phonePane.phoneAudioCheck = "CHECKED";
                } catch (error) {
                    phonePane.phoneAudioStatus = ({});
                    phonePane.phoneAudioCheck = "UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.phoneAudioCheck === "CHECKING" && code !== 0) {
                phonePane.phoneAudioStatus = ({});
                phonePane.phoneAudioCheck = "UNAVAILABLE";
            }
        }
    }

    Process {
        id: audioActionProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.phoneAudioResult !== "UPDATING")
                    return;
                try {
                    var r = JSON.parse(String(text || ""));
                    if (r.schema !== "post-apollo.phone.audio-controls.v0"
                            || r.execution !== "USER_ACTION"
                            || ["PREFERENCE_SAVED", "BRIDGE_UNAVAILABLE", "CLIENT_UNAVAILABLE",
                                "CALLS_PREREQUISITES_MISSING", "CHANGE_FAILED",
                                "NOT_CONFIRMED", "REFUSED"].indexOf(r.result) < 0
                            || r.trustedPhoneLink !== "UNVERIFIED"
                            || r.contentAccessEnabled !== false)
                        throw new Error("Invalid audio action");
                    phonePane.phoneAudioResult = r.result;
                } catch (error) {
                    phonePane.phoneAudioResult = "CHANGE_FAILED";
                }
            }
        }
        onExited: function(code) {
            if (!phonePane.visible)
                return;
            if (phonePane.phoneAudioResult === "UPDATING")
                phonePane.phoneAudioResult = "CHANGE_FAILED";
            phonePane.refreshPhoneAudioControls();
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
                            || typeof result.stageCandidate !== "boolean"
                            || result.trustedPhoneLink !== "UNVERIFIED"
                            || result.routeEligible !== false
                            || result.contentAccessEnabled !== false)
                        throw new Error("Invalid native setup handoff");
                    phonePane.nativeSetupStatus = result.status;
                    if (result.status === "OPEN_REQUESTED"
                            && result.stageCandidate && result.target === "iphone") {
                        phonePane.stageState = "WAITING";
                        phonePane.stageWanted = true;
                        phonePane.stagePollCount = 0;
                    }
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

    // PHONE is a normal Social conversation workspace: the same contact-list
    // and chat-feed components used by Sessions/Telegram, with zero trusted
    // phone content until the Phone Bridge explicitly authorizes it.
    Process {
        id: stageProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.stageWanted || !phonePane.visible)
                    return;
                try {
                    const result = JSON.parse(String(text || ""));
                    if (result.schema !== "post-apollo.phone.stage-director.v0"
                            || result.execution !== "STAGE_ONLY"
                            || result.trustedPhoneLink !== "UNVERIFIED"
                            || result.contentAccessEnabled !== false
                            || typeof result.verifiedHole !== "boolean")
                        throw new Error("Invalid Stage Director result");
                    if (result.state === "ALIGNED" && result.verifiedHole === true)
                        phonePane.stageState = "ALIGNED";
                    else if (result.state === "ACTOR_NOT_FOUND"
                             && phonePane.stageState === "ALIGNED") {
                        // The staged terminal exited. That is not evidence of
                        // phone disconnection. Refresh the local service state.
                        phonePane.stageWanted = false;
                        phonePane.stageState = "FINISHED";
                        phonePane.refreshSavedBridgeState();
                    } else if (result.state === "POSITION_REQUESTED"
                             || result.state === "ACTOR_NOT_FOUND"
                             || result.state === "HOST_NOT_FOUND")
                        phonePane.stageState = "POSITIONING";
                    else
                        throw new Error("Stage unavailable");
                } catch (error) {
                    phonePane.stageWanted = false;
                    phonePane.stageState = "UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode) {
            if (phonePane.stageWanted && exitCode !== 0) {
                phonePane.stageWanted = false;
                phonePane.stageState = "UNAVAILABLE";
            }
        }
    }

    Process {
        id: stageCloseProcess
    }

    Timer {
        interval: 700
        repeat: true
        running: phonePane.stageWanted && phonePane.visible
                 && phonePane.selectedSection === "DEVICE"
        onTriggered: phonePane.syncStagedSetup()
    }

    WeatherStage.StationChassisCutout {
        anchors.fill: parent
        visible: phonePane.stageHoleActive
        holeX: phonePane.stageHoleX
        holeY: phonePane.stageHoleY
        holeWidth: phonePane.stageHoleWidth
        holeHeight: phonePane.stageHoleHeight
        panelColor: Colors.black
        panelOpacity: 1
        z: -1
    }

    Rectangle {
        id: header
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 46
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan

        Text {
            anchors.left: parent.left
            anchors.leftMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            text: "PHONE // CONNECT"
            color: Colors.cyan
            font.family: "GohuFont 11 Nerd Font Mono"
            font.pixelSize: 16
            font.bold: true
        }

        ActionButton {
            id: connectPhoneAction
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(158, Math.max(110, header.width * 0.25))
            height: 32
            label: setupProcess.running ? "CHECKING..." : "CONNECT PHONE"
            labelPixelSize: 9
            accentColor: Colors.magenta
            interactive: !setupProcess.running
            onTriggered: phonePane.startSetup()
        }
    }

    Rectangle {
        id: sectionToolbar
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 46
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan

        Row {
            id: sectionTabs
            anchors.fill: parent
            anchors.margins: 5
            spacing: 6

            Repeater {
                model: ["DEVICE", "CALLS", "MESSAGES", "CONTACTS"]
                delegate: ActionButton {
                    required property string modelData
                    width: Math.max(62, (sectionTabs.width - 18) / 4)
                    height: sectionTabs.height
                    label: modelData
                    labelPixelSize: 10
                    labelMinimumPixelSize: 8
                    accentColor: Colors.cyan
                    selected: phonePane.selectedSection === modelData
                    onTriggered: phonePane.selectedSection = modelData
                }
            }
        }
    }

    ContactList {
        id: phoneContactList
        anchors.top: sectionToolbar.bottom
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: Math.min(200, Math.max(135, phonePane.width * 0.30))
        conversations: []
        keyboardFocused: false
    }

    // No invented people or unapproved phone numbers. The real ContactList
    // remains empty until a different, trusted owner provides scoped data.
    Text {
        id: emptyPhoneContacts
        anchors.top: phoneContactList.top
        anchors.topMargin: 108
        anchors.left: phoneContactList.left
        anchors.right: phoneContactList.right
        anchors.margins: 10
        z: 4
        text: phonePane.selectedSection === "CONTACTS"
              ? "NO PHONE CONTACTS\nSYNC NOT AUTHORIZED"
              : "NO PHONE CHATS YET"
        color: Colors.white
        opacity: 0.8
        font.family: "GohuFont 11 Nerd Font Mono"
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }

    ChatFeed {
        id: phoneChatFeed
        anchors.top: sectionToolbar.bottom
        anchors.left: phoneContactList.right
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: phonePane.selectedSection !== "DEVICE"
        conversation: null
        messages: []
        sendEnabled: false
        emptyConversationLabel: phonePane.selectedSection === "CALLS"
                                ? "PHONE CALLS NOT LINKED"
                                : phonePane.selectedSection === "CONTACTS"
                                ? "PHONE CONTACTS NOT LINKED"
                                : "PHONE NOT LINKED"
    }

    // DEVICE is a contextual overlay in the existing chat-feed column,
    // NOT a separate screen or permanent vertical security/menu rail.
    Rectangle {
        id: setupOverlay
        anchors.fill: phoneChatFeed
        visible: phonePane.selectedSection === "DEVICE"
        color: phonePane.stageHoleActive ? "transparent" : Colors.black
        border.width: 1
        border.color: Colors.cyan
        z: 5

        Rectangle {
            id: setupHeader
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 60
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Text {
                anchors.left: parent.left
                anchors.leftMargin: 18
                anchors.verticalCenter: parent.verticalCenter
                text: "PHONE SETUP"
                color: Colors.cyan
                font.family: "GohuFont 11 Nerd Font Mono"
                font.pixelSize: 18
                font.bold: true
            }
        }

        Flickable {
            id: setupScroll
            anchors.top: setupHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            contentWidth: width
            contentHeight: setupColumn.implicitHeight + 24
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick
            clip: true

            Column {
                id: setupColumn
                x: 16
                y: 14
                width: Math.max(1, setupScroll.width - 32)
                spacing: 13

                Text {
                    width: parent.width
                    text: "DEVICE // " + phonePane.setupState
                    color: Colors.cyan
                    font.pixelSize: 12
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: phonePane.setupState === "CHECKING"
                          ? "Checking existing phone bridges..."
                          : phonePane.setupState === "CHECKED"
                            && phonePane.setupReport.status === "BRIDGE_REPORTED"
                          ? "A phone bridge responded. Social has NOT linked a phone or enabled private content."
                          : phonePane.setupState === "CHECKED"
                          ? "No active phone bridge was reported. An existing Bluetooth pairing does not need to be repeated automatically."
                          : phonePane.setupState === "UNAVAILABLE"
                          ? "Could not check existing phone bridges. Try CONNECT PHONE again."
                          : "Check your existing phone connection first. You do not need to leave Bluetooth settings open for ordinary reconnection."
                    color: Colors.white
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
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
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    lineHeight: 1.35
                }

                Text {
                    width: parent.width
                    visible: phonePane.savedBridgeCheck === "CHECKED"
                    text: phonePane.savedBridgeState.state === "BACKEND_REPORTED"
                          ? "BlueFerry configuration exists and its background service responds. Message/contacts sessions are reported separately; Social access is not yet linked."
                          : phonePane.savedBridgeState.state === "CONFIGURATION_PRESENT_BACKEND_INACTIVE"
                          ? "BlueFerry configuration exists, but its background service is not active. Re-pairing will not fix a stopped service."
                          : phonePane.savedBridgeState.state === "CONFIGURATION_PRESENT_BACKEND_UNVERIFIED"
                          ? "BlueFerry has local configuration and a running service, but its active phone sessions could not be verified."
                          : phonePane.savedBridgeState.state === "NO_LOCAL_CONFIGURATION"
                          ? "BlueFerry has no local configuration file. Initial setup may be incomplete."
                          : "BlueFerry's saved setup status could not be verified."
                    color: Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: phonePane.savedBridgeCheck === "CHECKED"
                    text: "Saved BlueFerry config file: " +
                          (phonePane.savedBridgeState.configurationPresent === true ? "PRESENT" :
                           phonePane.savedBridgeState.configurationPresent === false ? "NOT FOUND" : "UNKNOWN") +
                          "\nBackground service: " + String(phonePane.savedBridgeState.backendService || "unknown").toUpperCase() +
                          "\nStarts with session: " + String(phonePane.savedBridgeState.startup || "unknown").toUpperCase() +
                          "\nMessages: " + String(phonePane.savedBridgeState.messageProfile || "UNVERIFIED") +
                          "\nContacts: " + String(phonePane.savedBridgeState.contactsProfile || "UNVERIFIED")
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    lineHeight: 1.35
                }

                // Only the currently selected BlueFerry iPhone is affected.
                // These are its two existing provider preferences, not a
                // universal Post-Apollo or OS-wide audio default.
                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                    text: "IPHONE AUDIO"
                    color: Colors.cyan
                    font.pixelSize: 12
                    font.bold: true
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                    text: phonePane.phoneAudioCheck === "CHECKING"
                          ? "Reading iPhone audio preferences..."
                          : phonePane.phoneAudioCheck !== "CHECKED"
                            || phonePane.phoneAudioStatus.result !== "OBSERVED"
                          ? "Audio settings unavailable until BlueFerry's configured background service responds."
                          : "Media preference: " + phonePane.phoneAudioStatus.mediaPreference +
                            "  |  Current route: " + phonePane.phoneAudioStatus.mediaRoute
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                Row {
                    id: mediaRouteChoices
                    width: setupColumn.width
                    spacing: 6
                    visible: phonePane.setupState === "CHECKED"

                    Repeater {
                        model: [
                            { title: "IPHONE", route: "phone" },
                            { title: "COMPUTER", route: "pc" },
                            { title: "AUTO", route: "auto" }
                        ]
                        delegate: ActionButton {
                            required property var modelData
                            width: Math.max(66, (mediaRouteChoices.width - 12) / 3)
                            height: 34
                            label: modelData.title
                            labelPixelSize: 9
                            accentColor: Colors.magenta
                            selected: phonePane.phoneAudioStatus.mediaPreference
                                      === modelData.route.toUpperCase()
                            interactive: phonePane.phoneAudioCheck === "CHECKED"
                                         && phonePane.phoneAudioStatus.canAdjust === true
                                         && !audioActionProcess.running
                                         && !audioStatusProcess.running
                                         && !phonePane.stageWanted
                            onTriggered: phonePane.changePhoneAudio("media", modelData.route)
                        }
                    }
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                    text: "Media = music, video and other iPhone playback. This does not switch phone-call audio."
                    color: Colors.white
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                ActionButton {
                    width: Math.min(210, setupColumn.width)
                    height: 36
                    visible: phonePane.setupState === "CHECKED"
                    label: phonePane.phoneAudioStatus.callsEnabled === true
                           ? "CALLS ON PC: ON" : "CALLS ON PC: OFF"
                    labelPixelSize: 10
                    accentColor: Colors.magenta
                    selected: phonePane.phoneAudioStatus.callsEnabled === true
                    interactive: phonePane.phoneAudioCheck === "CHECKED"
                                 && phonePane.phoneAudioStatus.canAdjust === true
                                 && phonePane.phoneAudioStatus.callsEnabled !== null
                                 && (phonePane.phoneAudioStatus.callsEnabled === true
                                     || phonePane.phoneAudioStatus.ofonoActive === true)
                                 && !audioActionProcess.running
                                 && !audioStatusProcess.running
                                 && !phonePane.stageWanted
                    onTriggered: phonePane.changePhoneAudio(
                        "calls", phonePane.phoneAudioStatus.callsEnabled === true
                                 ? "disable" : "enable")
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                    text: phonePane.phoneAudioStatus.callsEnabled === true
                          ? "Call preference on. HFP status: " + String(phonePane.phoneAudioStatus.callsState || "UNKNOWN") +
                            ". Actual call audio depends on oFono and the system's hands-free routing."
                          : "For calls only, choose IPHONE above and enable CALLS ON PC when supported." +
                            (phonePane.phoneAudioCheck === "CHECKED"
                             && phonePane.phoneAudioStatus.ofonoActive !== true
                             ? " Calls require an oFono hands-free backend; not ready on this desktop." : "")
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                             && phonePane.phoneAudioResultText().length > 0
                    text: phonePane.phoneAudioResultText()
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                    text: "First media change may briefly interrupt other Bluetooth sound while WirePlumber applies BlueFerry's per-phone rule."
                    color: Colors.white
                    opacity: 0.75
                    font.pixelSize: 9
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: phonePane.setupState === "CHECKED"
                    text: "If setup is needed, choose your phone below. This opens the provider's own setup. BlueFerry may require the iPhone Bluetooth screen during initial pairing only, not permanently."
                    color: Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Row {
                    id: nativeSetupChoices
                    width: setupColumn.width
                    spacing: 8
                    visible: phonePane.selectedSection === "DEVICE"
                             && phonePane.setupState === "CHECKED"

                    ActionButton {
                        width: Math.max(75, (nativeSetupChoices.width - 8) / 2)
                        height: 38
                        label: phonePane.savedBridgeState.configurationPresent === true
                               ? "OPEN IPHONE" : "SET UP IPHONE"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        interactive: !nativeSetupProcess.running && !phonePane.stageWanted
                        onTriggered: phonePane.openNativeSetup("iphone")
                    }

                    ActionButton {
                        width: Math.max(75, (nativeSetupChoices.width - 8) / 2)
                        height: 38
                        label: "SET UP ANDROID"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        interactive: !nativeSetupProcess.running && !phonePane.stageWanted
                        onTriggered: phonePane.openNativeSetup("android")
                    }
                }

                Text {
                    width: parent.width
                    visible: phonePane.nativeSetupStatus !== "IDLE"
                    text: phonePane.nativeSetupStatus === "OPENING"
                          ? "Opening your phone setup..."
                          : phonePane.nativeSetupStatus === "OPEN_REQUESTED"
                          ? "BlueFerry client requested. Saved configurations open the existing phone session, not the re-pairing wizard. Use CONNECT PHONE to recheck. Social messages remain locked."
                          : phonePane.nativeSetupStatus === "CLIENT_UNAVAILABLE"
                          ? "No supported BlueFerry or KDE Connect setup client could be found on this desktop. The Bluetooth bridge may still be installed or paired. No pairing changes made."
                          : "Could not start the provider setup client. Your phone's pairing has not been changed by Social."
                    color: Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    height: 45 // Stable bay position across stage state changes.
                    visible: phonePane.stageWanted || phonePane.stageState === "UNAVAILABLE" || phonePane.stageState === "FINISHED"
                    text: phonePane.stageState === "ALIGNED"
                          ? "BLUEFERRY SETUP // TERMINAL BELOW"
                          : phonePane.stageState === "FINISHED"
                          ? "BlueFerry client closed. Checking saved configuration and background service..."
                          : phonePane.stageState === "UNAVAILABLE"
                          ? "Stage placement could not be verified. Terminal window remains external; no Social phone connection was granted."
                          : "Placing BlueFerry's terminal inside the PHONE workspace..."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }

                ActionButton {
                    width: Math.min(190, setupColumn.width)
                    height: 32
                    visible: phonePane.stageWanted
                    label: "CLOSE SETUP"
                    labelPixelSize: 9
                    accentColor: Colors.red
                    destructive: true
                    onTriggered: phonePane.closeStagedSetup()
                }

                ActionButton {
                    width: Math.min(190, setupColumn.width)
                    height: 38
                    label: phonePane.detailsOpen ? "HIDE DETAILS" : "DETAILS"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    interactive: !phonePane.stageWanted
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

                ActionButton {
                    width: Math.min(190, setupColumn.width)
                    height: 38
                    visible: phonePane.selectedSection === "DEVICE" && phonePane.detailsOpen
                    label: "REFRESH READINESS"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
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
}
