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
    property var deviceObservation: ({})
    property string deviceObservationCheck: "NOT CHECKED"
    property var phoneAudioStatus: ({})
    property string phoneAudioCheck: "NOT CHECKED"
    property string phoneAudioResult: "IDLE"
    property var callPrerequisiteReport: ({})
    property string callPrerequisiteCheck: "NOT CHECKED"
    property string callSetupStatus: "IDLE"
    // Strict, public tool identifiers only; never paths or process output.
    property var callSetupMissingTools: ([])

    function callingMissingToolText() {
        var labels = ({
            "FOOT": "foot terminal",
            "PYTHON3": "Python 3",
            "INSTALLER_HELPER": "PHONE installer script",
            "PKCON": "PackageKit (pkcon)",
            "PKEXEC": "Polkit (pkexec)",
            "DNF5": "DNF5"
        });
        var found = [];
        for (var i = 0; i < callSetupMissingTools.length; ++i) {
            var tool = callSetupMissingTools[i];
            if (typeof labels[tool] === "string")
                found.push(labels[tool]);
        }
        return found.length > 0 ? " Not available to PHONE: " + found.join(", ") + "." : "";
    }

    function callingSupportSetup() {
        if (!visible || selectedSection !== "DEVICE" || setupState !== "CHECKED"
                || stageWanted || callSetupProcess.running
                || callPrerequisiteProcess.running || audioActionProcess.running)
            return;
        if (callSetupStatus === "GUI_OPEN_REQUESTED"
                || callSetupStatus === "FOLLOWUP_REQUIRED") {
            callSetupStatus = "RECHECKING";
            diagnoseCallPrerequisites();
            refreshPhoneAudioControls();
            return;
        }
        if (callPrerequisiteCheck !== "CHECKED"
                || callPrerequisiteReport.state !== "PACKAGE_NOT_INSTALLED"
                || callPrerequisiteReport.package !== "NOT_INSTALLED"
                || callPrerequisiteReport.serviceLoad !== "not-found")
            return;
        if (!stageHoleValid) {
            // Never launch a terminal behind an unusably small Social panel.
            callSetupStatus = "STAGE_BAY_TOO_SMALL";
            return;
        }
        callSetupMissingTools = ([]);
        callSetupStatus = "OPENING";
        callSetupProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneCallingSetupHandoff.py"),
            "--open-ofono"
        ];
        callSetupProcess.running = true;
    }

    function callingSupportSetupText() {
        if (callSetupStatus === "OPENING")
            return "Opening the oFono installer in PHONE...";
        if (callSetupStatus === "STAGED_TERMINAL_REQUESTED"
                || callSetupStatus === "STAGED_TERMINAL_EXISTING")
            return "Fedora's interactive installer runs in the PHONE terminal below. Review its transaction and confirm or decline; Social has not assumed installation succeeded.";
        if (callSetupStatus === "GUI_OPEN_REQUESTED")
            return "A native PackageKit installer was requested. Review and approve it there, then choose CHECK AGAIN. No installation was confirmed by Social.";
        if (callSetupStatus === "RECHECKING")
            return "Checking oFono, the system service and BlueFerry call status...";
        if (callSetupStatus === "INSTALL_NOT_CONFIRMED")
            return "oFono is still reported missing. Complete the installation in the software manager, or retry setup. No audio changes were made by Social.";
        if (callSetupStatus === "FOLLOWUP_REQUIRED")
            return "Package check completed. The next step is shown below. CHECK AGAIN updates the existing service and call statuses without changing audio.";
        if (callSetupStatus === "STAGE_BAY_TOO_SMALL")
            return "PHONE is too small for an interactive installer. Enlarge the Social panel and try SET UP CALLING again. No external window was opened.";
        if (callSetupStatus === "TERMINAL_UNAVAILABLE")
            return "The embedded installer cannot start." + callingMissingToolText()
                + " No external window was opened and no package was installed.";
        if (callSetupStatus === "PACKAGE_MANAGER_UNAVAILABLE")
            return "No supported Fedora package installer is available to PHONE."
                + callingMissingToolText()
                + " Either PackageKit or BOTH Polkit and DNF5 are required. No installation was attempted.";
        if (callSetupStatus === "GUI_UNAVAILABLE")
            return "The embedded package installer is unavailable. No external window was opened or package installed.";
        if (callSetupStatus === "GUI_LAUNCH_FAILED")
            return "PHONE could not start the embedded PackageKit terminal. No external window was opened or installation confirmed.";
        if (callSetupStatus === "UNSUPPORTED_HOST")
            return "Automatic package selection is currently supported on Fedora only. No changes were made.";
        if (callSetupStatus === "DIAGNOSIS_UNAVAILABLE"
                || callSetupStatus === "NOT_APPLICABLE")
            return "Calling setup could not be started from the current system diagnosis. Check the call prerequisite status again.";
        return "";
    }

    // Explain the existing sanitized statuses without claiming verified audio.
    function callProgressText() {
        if (callSetupStatus !== "FOLLOWUP_REQUIRED"
                || callPrerequisiteCheck !== "CHECKED")
            return "";
        var stage = callPrerequisiteReport.state;
        if (stage === "SERVICE_STOPPED")
            return "oFono is installed, but its system service is stopped. It needs separately approved system-audio setup; PHONE will not start it automatically.";
        if (stage === "SERVICE_FAILED" || stage === "SERVICE_MASKED")
            return "oFono's service needs system-audio repair before calling. Your existing phone pairing and media settings remain untouched.";
        if (stage === "SERVICE_UNIT_MISSING" || stage === "INSPECTION_UNAVAILABLE")
            return "The oFono service could not be verified. Check the system installation before enabling PC calls.";
        if (stage === "SERVICE_STARTING")
            return "The oFono service is changing state. Check again when it settles.";
        if (stage === "DBUS_NAME_MISSING")
            return "oFono is running without its expected system D-Bus owner. Hands-free call control cannot be verified.";
        if (stage !== "AUDIO_PATH_UNVERIFIED")
            return "Calling prerequisites remain unverified.";
        if (phoneAudioCheck !== "CHECKED"
                || phoneAudioStatus.result !== "OBSERVED")
            return "oFono is running, but BlueFerry's call status is unavailable. This is not proof of a connected phone.";
        if (phoneAudioStatus.callsEnabled !== true)
            return "oFono is running. Calls on PC is still OFF. Enable it separately when your system's hands-free routing is configured.";
        var calls = phoneAudioStatus.callsState;
        if (calls === "READY")
            return "BlueFerry reports hands-free call control READY. Microphone and speaker routing still need a real non-emergency test call.";
        if (calls === "BLUEZ_CONFLICT")
            return "BlueFerry reports a BlueZ HFP conflict. The system-audio owner must check which Bluetooth service owns hands-free calls.";
        if (calls === "SEARCHING")
            return "BlueFerry is searching for the iPhone's hands-free link. Check the phone connection and WirePlumber's oFono backend; no reset was attempted.";
        if (calls === "CONNECTING")
            return "BlueFerry is negotiating the hands-free link. Check again; call audio is not verified yet.";
        return "BlueFerry cannot confirm hands-free call readiness. oFono D-Bus access, WirePlumber and BlueZ still require verification.";
    }

    function diagnoseCallPrerequisites() {
        if (!visible || stageWanted || callPrerequisiteProcess.running)
            return;
        callPrerequisiteReport = ({});
        callPrerequisiteCheck = "CHECKING";
        phoneAudioResult = "CALLS_DIAGNOSING";
        callPrerequisiteProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneCallPrerequisites.py"),
            "--check"
        ];
        callPrerequisiteProcess.running = true;
    }

    function callPrerequisiteText() {
        if (callPrerequisiteCheck === "CHECKING")
            return "Checking the local hands-free calling prerequisites...";
        if (callPrerequisiteCheck !== "CHECKED")
            return "oFono hands-free support could not be checked. No audio changes were made.";
        var state = callPrerequisiteReport.state;
        if (state === "PACKAGE_NOT_INSTALLED")
            return "oFono is not installed on this Fedora system. Calling needs a separately approved system setup. No audio changes were made.";
        if (state === "SERVICE_UNIT_MISSING")
            return "Fedora cannot find the oFono service unit. Its installation or service registration needs checking. No changes were made.";
        if (state === "SERVICE_MASKED")
            return "The oFono service is masked by the system. A separate approved system setup is needed. No changes were made.";
        if (state === "SERVICE_FAILED")
            return "The oFono service exists but failed to start. The system audio setup needs repair. No changes were made.";
        if (state === "SERVICE_STOPPED")
            return "oFono is installed as a service but is stopped. It must be started through an approved system setup before calls can use this computer.";
        if (state === "SERVICE_STARTING")
            return "oFono is changing state. Wait until it is stable and check again. No audio changes were made.";
        if (state === "DBUS_NAME_MISSING")
            return "oFono is active, but its system D-Bus connection is not responding. Calls are not verified. No changes were made.";
        if (state === "AUDIO_PATH_UNVERIFIED")
            return "oFono appears active. Hands-free routing through WirePlumber and Bluetooth is not yet verified. Use CONNECT PHONE to refresh the call setting.";
        return "The oFono service state could not be determined. No changes were made.";
    }

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
                || callPrerequisiteProcess.running)
            return;
        if (family === "media" && ["phone", "pc", "auto"].indexOf(selection) < 0)
            return;
        if (family === "calls" && ["enable", "disable"].indexOf(selection) < 0)
            return;
        if (family !== "media" && family !== "calls")
            return;

        // The CALLS button remains clickable even if the HFP backend is not
        // available. Only an actual supported action reaches the host helper.
        if (family === "calls") {
            if (phoneAudioCheck !== "CHECKED"
                    || phoneAudioStatus.canAdjust !== true) {
                phoneAudioResult = "CALLS_STATUS_UNAVAILABLE";
                return;
            }
            if (typeof phoneAudioStatus.callsEnabled !== "boolean") {
                phoneAudioResult = "CALLS_UNSUPPORTED";
                return;
            }
            if (selection === "enable" && phoneAudioStatus.ofonoActive !== true) {
                phoneAudioResult = "CALLS_PREREQUISITES_MISSING";
                diagnoseCallPrerequisites();
                return;
            }
        } else if (phoneAudioCheck !== "CHECKED"
                   || phoneAudioStatus.canAdjust !== true) {
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
        if (phoneAudioResult === "CALLS_DIAGNOSING")
            return callPrerequisiteText();
        if (phoneAudioResult === "PREFERENCE_SAVED")
            return "Preference saved by BlueFerry. Actual playback and call availability depend on the iPhone and audio services.";
        if (phoneAudioResult === "CALLS_PREREQUISITES_MISSING")
            return callPrerequisiteText();
        if (phoneAudioResult === "CALLS_UNSUPPORTED")
            return "The running BlueFerry backend does not report a supported Calls on PC setting. No change made; this requires a compatible phone-call provider.";
        if (phoneAudioResult === "CALLS_STATUS_UNAVAILABLE")
            return "Call settings cannot be read from BlueFerry yet. Check the phone connection with CONNECT PHONE. No change made.";
        if (phoneAudioResult === "NOT_CONFIRMED")
            return "Requested, but BlueFerry did not confirm the saved preference.";
        if (phoneAudioResult === "CHANGE_FAILED"
                || phoneAudioResult === "CLIENT_UNAVAILABLE"
                || phoneAudioResult === "BRIDGE_UNAVAILABLE")
            return "Could not change phone audio. Existing routing was not intentionally reset.";
        return "";
    }

    // Physical BlueZ name and Bluetooth link only. The opaque BlueFerry ID
    // distinguishes the active profile; neither this nor a name is a grant.
    function refreshDeviceObservation() {
        if (!visible || deviceObservationProcess.running)
            return;
        deviceObservationCheck = "CHECKING";
        deviceObservation = ({});
        deviceObservationProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneDeviceObservation.py"),
            "--inspect"
        ];
        deviceObservationProcess.running = true;
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
    property string stagePurpose: "PHONE"
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
    // Reserve a real lower terminal bay independently of the scrollable
    // setup column. Before this, implicitHeight grew with every new control
    // and pushed the "hole" below the panel, leaving the terminal behind
    // an opaque Social window with no reachable keyboard or mouse input.
    readonly property int stageBayTop: Math.max(
        setupHeader.height + 112, Math.round(phoneChatFeed.height * 0.43))
    readonly property int stageHoleX: Math.round(phoneChatFeed.x + 10)
    readonly property int stageHoleY: Math.round(phoneChatFeed.y + stageBayTop)
    readonly property int stageHoleWidth: Math.round(phoneChatFeed.width - 20)
    readonly property int stageHoleHeight: Math.round(
        phoneChatFeed.height - stageBayTop - 12)
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
        var installer = stagePurpose === "OFONO";
        stageWanted = false;
        stageState = "IDLE";
        stagePollCount = 0;
        stagePurpose = "PHONE";
        if (installer) {
            // A running package transaction must never be killed by a
            // navigation event or by returning from the PHONE panel.
            if (visible && selectedSection === "DEVICE") {
                callSetupStatus = "RECHECKING";
                diagnoseCallPrerequisites();
                refreshPhoneAudioControls();
            }
            return;
        }
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
                || stageProcess.running)
            return;
        if (!stageHoleValid) {
            // Too small to stage: do not promise a transparent/input hole.
            // The explicitly launched native window remains external.
            stageWanted = false;
            stageState = "UNAVAILABLE";
            return;
        }
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
            stagePurpose === "OFONO" ? "--sync-installer" : "--sync",
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
        refreshDeviceObservation();
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
            deviceObservationCheck = "NOT CHECKED";
            deviceObservation = ({});
            phoneAudioStatus = ({});
            phoneAudioCheck = "NOT CHECKED";
            phoneAudioResult = "IDLE";
            callSetupStatus = "IDLE";
            callSetupMissingTools = ([]);
            callPrerequisiteReport = ({});
            callPrerequisiteCheck = "NOT CHECKED";
            stageWanted = false;
            stagePurpose = "PHONE";
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
        id: deviceObservationProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.deviceObservationCheck !== "CHECKING")
                    return;
                try {
                    var observed = JSON.parse(String(text || ""));
                    var states = [
                        "UNAVAILABLE", "PROFILE_ONLY", "PAIRED_OFFLINE",
                        "BLUETOOTH_CONNECTED"
                    ];
                    var links = ["UNVERIFIED", "PAIRED_OFFLINE", "CONNECTED"];
                    var profile = String(observed.profileId || "");
                    var validProfile = profile === ""
                        || /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(profile);
                    if (observed.schema !== "post-apollo.phone.device-observation.v0"
                            || observed.execution !== "READ_ONLY_DEVICE_OBSERVATION"
                            || states.indexOf(observed.state) < 0
                            || links.indexOf(observed.bluetoothLink) < 0
                            || observed.trustedPhoneLink !== "UNVERIFIED"
                            || observed.contentAccessEnabled !== false
                            || typeof observed.profileId !== "string"
                            || !validProfile
                            || typeof observed.displayName !== "string"
                            || observed.displayName.length > 56
                            || (observed.state === "UNAVAILABLE"
                                && (profile !== "" || observed.displayName !== ""
                                    || observed.bluetoothLink !== "UNVERIFIED"))
                            || (observed.state !== "UNAVAILABLE"
                                && (profile === "" || observed.displayName.length === 0))
                            || (observed.state === "BLUETOOTH_CONNECTED"
                                && observed.bluetoothLink !== "CONNECTED")
                            || (observed.state === "PAIRED_OFFLINE"
                                && observed.bluetoothLink !== "PAIRED_OFFLINE")
                            || (observed.state === "PROFILE_ONLY"
                                && observed.bluetoothLink !== "UNVERIFIED"))
                        throw new Error("Unexpected device observation");
                    phonePane.deviceObservation = observed;
                    phonePane.deviceObservationCheck = "CHECKED";
                } catch (error) {
                    phonePane.deviceObservation = ({});
                    phonePane.deviceObservationCheck = "UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.deviceObservationCheck === "CHECKING"
                    && code !== 0)
                phonePane.deviceObservationCheck = "UNAVAILABLE";
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
        id: callPrerequisiteProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.callPrerequisiteCheck !== "CHECKING")
                    return;
                try {
                    var r = JSON.parse(String(text || ""));
                    var states = [
                        "PACKAGE_NOT_INSTALLED", "SERVICE_UNIT_MISSING", "SERVICE_MASKED",
                        "SERVICE_FAILED", "SERVICE_STOPPED", "SERVICE_STARTING",
                        "DBUS_NAME_MISSING", "AUDIO_PATH_UNVERIFIED",
                        "INSPECTION_UNAVAILABLE"
                    ];
                    if (r.schema !== "post-apollo.phone.calls-prerequisites.v0"
                            || r.execution !== "READ_ONLY_CALL_DIAGNOSIS"
                            || states.indexOf(r.state) < 0
                            || ["INSTALLED", "NOT_INSTALLED", "UNKNOWN"].indexOf(r.package) < 0
                            || ["loaded", "not-found", "masked", "error", "stub", "unknown"].indexOf(r.serviceLoad) < 0
                            || ["active", "inactive", "failed", "activating",
                                "deactivating", "reloading", "unknown"].indexOf(r.serviceActive) < 0
                            || ["OWNER_PRESENT", "NO_OWNER", "UNKNOWN"].indexOf(r.systemBus) < 0
                            || r.hfpVerified !== false
                            || r.trustedPhoneLink !== "UNVERIFIED"
                            || r.contentAccessEnabled !== false)
                        throw new Error("Invalid hands-free diagnostic report");
                    phonePane.callPrerequisiteReport = r;
                    phonePane.callPrerequisiteCheck = "CHECKED";
                    phonePane.phoneAudioResult = "CALLS_PREREQUISITES_MISSING";
                    if (phonePane.callSetupStatus === "RECHECKING") {
                        phonePane.callSetupStatus = r.state === "PACKAGE_NOT_INSTALLED"
                                                    ? "INSTALL_NOT_CONFIRMED"
                                                    : "FOLLOWUP_REQUIRED";
                    }
                } catch (error) {
                    phonePane.callPrerequisiteReport = ({});
                    phonePane.callPrerequisiteCheck = "UNAVAILABLE";
                    phonePane.phoneAudioResult = "CALLS_PREREQUISITES_MISSING";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.callPrerequisiteCheck === "CHECKING" && code !== 0) {
                phonePane.callPrerequisiteReport = ({});
                phonePane.callPrerequisiteCheck = "UNAVAILABLE";
                phonePane.phoneAudioResult = "CALLS_PREREQUISITES_MISSING";
            }
        }
    }

    Process {
        id: callSetupProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.callSetupStatus !== "OPENING")
                    return;
                try {
                    var r = JSON.parse(String(text || ""));
                    if (r.schema !== "post-apollo.phone.calling-setup-handoff.v0"
                            || r.execution !== "USER_INITIATED_INSTALLER_HANDOFF"
                            || r.package !== "ofono"
                            || !Array.isArray(r.missingTools)
                            || r.missingTools.length > 6
                            || r.missingTools.some(function(v, i) {
                                return typeof v !== "string"
                                    || ["FOOT", "PYTHON3", "INSTALLER_HELPER",
                                        "PKCON", "PKEXEC", "DNF5"].indexOf(v) < 0
                                    || r.missingTools.indexOf(v) !== i;
                            })
                            || (r.status !== "TERMINAL_UNAVAILABLE"
                                && r.status !== "PACKAGE_MANAGER_UNAVAILABLE"
                                && r.missingTools.length !== 0)
                            || ["STAGED_TERMINAL_REQUESTED", "STAGED_TERMINAL_EXISTING",
                                "GUI_OPEN_REQUESTED", "GUI_UNAVAILABLE",
                                "TERMINAL_UNAVAILABLE", "PACKAGE_MANAGER_UNAVAILABLE",
                                "GUI_LAUNCH_FAILED", "UNSUPPORTED_HOST",
                                "NOT_APPLICABLE", "DIAGNOSIS_UNAVAILABLE",
                                "STAGE_UNAVAILABLE"].indexOf(r.status) < 0
                            || r.installerOpened !== (r.status === "GUI_OPEN_REQUESTED")
                            || r.stageCandidate !== (
                                r.status === "STAGED_TERMINAL_REQUESTED"
                                || r.status === "STAGED_TERMINAL_EXISTING")
                            || r.packageInstalled !== false
                            || r.hfpVerified !== false
                            || r.trustedPhoneLink !== "UNVERIFIED"
                            || r.contentAccessEnabled !== false)
                        throw new Error("Invalid installer handoff");
                    phonePane.callSetupMissingTools = r.missingTools;
                    phonePane.callSetupStatus = r.status;
                    if (r.stageCandidate === true) {
                        phonePane.stagePurpose = "OFONO";
                        phonePane.stageState = "WAITING";
                        phonePane.stageWanted = true;
                        phonePane.stagePollCount = 0;
                    }
                } catch (error) {
                    phonePane.callSetupMissingTools = ([]);
                    phonePane.callSetupStatus = "GUI_LAUNCH_FAILED";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.callSetupStatus === "OPENING" && code !== 0)
                phonePane.callSetupStatus = "GUI_LAUNCH_FAILED";
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
                        phonePane.stagePurpose = "PHONE";
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
                        var installer = phonePane.stagePurpose === "OFONO";
                        phonePane.stageWanted = false;
                        phonePane.stagePurpose = "PHONE";
                        phonePane.stageState = "FINISHED";
                        if (installer) {
                            phonePane.callSetupStatus = "RECHECKING";
                            phonePane.diagnoseCallPrerequisites();
                            phonePane.refreshPhoneAudioControls();
                        } else {
                            phonePane.refreshSavedBridgeState();
                            phonePane.refreshDeviceObservation();
                        }
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

            // Always reachable even when the compact upper setup controls
            // need scrolling. Installer detach never kills PackageKit.
            ActionButton {
                id: stagedExitAction
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(160, Math.max(100, parent.width * 0.36))
                height: 32
                visible: phonePane.stageWanted
                label: phonePane.stagePurpose === "OFONO"
                       ? "RETURN TO PHONE" : "CLOSE SETUP"
                labelPixelSize: 9
                accentColor: phonePane.stagePurpose === "OFONO"
                             ? Colors.magenta : Colors.red
                destructive: phonePane.stagePurpose !== "OFONO"
                onTriggered: phonePane.closeStagedSetup()
            }
        }

        Flickable {
            id: setupScroll
            anchors.top: setupHeader.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            // Limit the scrolling controls to the space ABOVE the staged
            // terminal. Without this, their contents still paint over the
            // compositor cutout even if the stage geometry is valid.
            anchors.bottomMargin: phonePane.stageWanted && phonePane.stageHoleValid
                                  ? Math.max(0, setupOverlay.height -
                                             phonePane.stageBayTop + 8) : 0
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

                // BlueZ's name is scoped to the exact opaque BlueFerry profile
                // and paired device, not to a Social user or an audio stream.
                Text {
                    width: parent.width
                    visible: phonePane.deviceObservationCheck === "CHECKED"
                    textFormat: Text.PlainText
                    text: phonePane.deviceObservation.state === "BLUETOOTH_CONNECTED"
                          ? "IPHONE // " + phonePane.deviceObservation.displayName
                            + "\nBluetooth device: CONNECTED. Social messages and contacts: NOT LINKED."
                          : phonePane.deviceObservation.state === "PAIRED_OFFLINE"
                          ? "IPHONE // " + phonePane.deviceObservation.displayName
                            + "\nBluetooth device: PAIRED, NOT CONNECTED. Social data: NOT LINKED."
                          : phonePane.deviceObservation.state === "PROFILE_ONLY"
                          ? "IPHONE PROFILE // Name and Bluetooth link not verified. Social data: NOT LINKED."
                          : "No configured iPhone identity could be verified. Existing audio settings were not changed."
                    color: Colors.cyan
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

                Column {
                    id: phoneAudioSettings
                    width: setupColumn.width
                    spacing: 9
                    visible: phonePane.setupState === "CHECKED" && !phonePane.stageWanted

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
                        // Always allow a diagnostic click. The handler blocks
                        // unsupported changes and explains them in this pane.
                        interactive: !audioActionProcess.running
                                     && !audioStatusProcess.running
                                     && !callPrerequisiteProcess.running
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
                              : "For calls only, choose IPHONE above and select CALLS ON PC." +
                                (phonePane.phoneAudioCheck === "CHECKED"
                                 && phonePane.phoneAudioStatus.ofonoActive !== true
                                 ? " Tap the call control for the missing hands-free requirement." : "")
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    ActionButton {
                        id: installCallingSupport
                        width: Math.min(220, phoneAudioSettings.width)
                        height: 36
                        visible: phonePane.callPrerequisiteCheck === "CHECKED"
                                 && (phonePane.callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED"
                                     || phonePane.callSetupStatus === "FOLLOWUP_REQUIRED")
                        label: phonePane.callSetupStatus === "GUI_OPEN_REQUESTED"
                               || phonePane.callSetupStatus === "FOLLOWUP_REQUIRED"
                               ? "CHECK AGAIN"
                               : phonePane.callSetupStatus === "INSTALL_NOT_CONFIRMED"
                                 ? "RETRY SETUP" : "SET UP CALLING"
                        labelPixelSize: 10
                        accentColor: Colors.magenta
                        interactive: !callSetupProcess.running
                                     && !callPrerequisiteProcess.running
                                     && !audioActionProcess.running
                                     && !phonePane.stageWanted
                        onTriggered: phonePane.callingSupportSetup()
                    }

                    Text {
                        width: parent.width
                        visible: installCallingSupport.visible
                                 && phonePane.callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED"
                        text: "Only oFono. Review and confirm the Fedora package transaction inside PHONE. Social never approves it automatically."
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        visible: phonePane.callingSupportSetupText().length > 0
                        text: phonePane.callingSupportSetupText()
                        color: Colors.orange
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        visible: phonePane.callProgressText().length > 0
                        text: phonePane.callProgressText()
                        color: Colors.cyan
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
                          ? (phonePane.stagePurpose === "OFONO"
                             ? "OFONO INSTALL // TERMINAL BELOW"
                             : "BLUEFERRY SETUP // TERMINAL BELOW")
                          : phonePane.stageState === "FINISHED"
                          ? "Terminal closed. Checking the latest provider and package status..."
                          : phonePane.stageState === "UNAVAILABLE"
                          ? "Stage placement could not be verified. The terminal may remain external; no phone or audio change was made by Social."
                          : phonePane.stagePurpose === "OFONO"
                          ? "Placing Fedora's interactive installer inside PHONE. Review its transaction and confirmation."
                          : "Placing BlueFerry's terminal inside the PHONE workspace..."
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
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
