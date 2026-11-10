import QtQuick
import Quickshell
import Quickshell.Io
import "../../components"
import "../weather" as WeatherStage
import "../../services/messaging/adapters" as PhoneAdapters

// PHONE stays in Social. CONNECT PHONE performs an explicit read-only check
// of existing provider observations; no pairing, permission or link is granted.
Rectangle {
    id: phonePane
    color: stageHoleActive ? "transparent" : Colors.black
    border.width: 1
    border.color: Colors.green
    clip: true

    property string selectedSection: "MESSAGES"
    // Remembered Personal preference, not Identity Center authorization.
    property string personalReadStatus: "NOT_STARTED"
    property string personalReadOperation: ""
    property int personalReadGeneration: 0
    property string personalConsentStatus: "IDLE"
    property bool personalApproved: false
    property bool personalPermissionOpen: false
    // BlueFerry's encrypted history key is separate from Social consent.
    // Never prompt the desktop wallet without an explicit user click.
    property string phoneStorageState: "UNKNOWN"
    property string phoneStoragePolicy: "unknown"
    property int phoneStorageGeneration: 0
    // A local Social identity change must not auto-display Personal content.
    property bool personalNeedsExplicitReload: false
    // The QML tree must exist before lifecycle handlers reference children.
    property bool personalReadUiReady: false
    Component.onCompleted: personalReadUiReady = true
    // A local Social identity is a display selector, never an auth grant.
    property string activeSocialIdentityId: ""
    onActiveSocialIdentityIdChanged: {
        if (!personalReadUiReady) return;
        personalReadGeneration += 1;
        if (personalReadProcess.running)
            personalReadProcess.running = false;
        phoneReadAdapter.forgetHostView();
        personalApproved = false;
        personalPermissionOpen = false;
        personalNeedsExplicitReload = true;
        personalReadStatus = "IDENTITY_CHANGED";
        callsWorkspaceGeneration += 1;
        callsRequireExplicitRefresh = true;
        callsConfirmDial = false;
        callsPendingDial = "";
        liveCalls = ([]);
        callsWorkspaceState = "IDENTITY_CHANGED";
        if (phoneCallsStatusProcess.running)
            phoneCallsStatusProcess.running = false;
        if (personalStatusProcess.running)
            personalStatusProcess.running = false;
        if (visible)
            checkPersonalApproval(false, false);
    }
    property string probeStatus: "NOT CHECKED"
    property var readiness: ({})
    property string setupState: "NOT STARTED"
    property var setupReport: ({})
    property bool detailsOpen: false
    property string nativeSetupTarget: ""
    property string nativeSetupStatus: "IDLE"
    property var savedBridgeState: ({})
    property string savedBridgeCheck: "NOT CHECKED"
    property var contentDiagnostic: ({})
    property string contentDiagnosticCheck: "NOT CHECKED"
    property var deviceObservation: ({})
    property string deviceObservationCheck: "NOT CHECKED"
    property var phoneNickname: ({})
    property string phoneNicknameCheck: "NOT CHECKED"
    property bool nicknameEditorOpen: false
    property string nicknameActionStatus: "IDLE"
    property string nicknameWriteProfile: ""
    property string nicknameWriteIntent: ""
    property var phoneAudioStatus: ({})
    property string phoneAudioCheck: "NOT CHECKED"
    property string phoneAudioResult: "IDLE"
    property var callPrerequisiteReport: ({})
    property string callPrerequisiteCheck: "NOT CHECKED"
    property string callSetupStatus: "IDLE"
    // Only inspect active calls while CALLS is visible. Provider-owned HFP
    // call control is separate from Messages/Contacts Personal read consent.
    property var liveCalls: ([])
    property string callsWorkspaceState: "NOT_CHECKED"
    property string callsWorkspaceResult: "IDLE"
    property int callsWorkspaceGeneration: 0
    property bool callsRequireExplicitRefresh: false
    property bool callsConfirmDial: false
    property string callsPendingDial: ""
    // Strict, public tool identifiers only; never paths or process output.
    property var callSetupMissingTools: ([])

    function callingMissingToolText() {
        var labels = ({
            "FOOT": "foot terminal",
            "PYTHON3": "Python 3",
            "INSTALLER_HELPER": "PHONE installer script",
            "PKCON": "PackageKit (pkcon)",
            "PKEXEC": "Polkit (pkexec)",
            "DNF5": "DNF5",
            "RPM_OSTREE": "Silverblue host rpm-ostree"
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
        if (callPrerequisiteCheck !== "CHECKED")
            return;
        if (callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED") {
            if (callPrerequisiteReport.package !== "NOT_INSTALLED"
                    || callPrerequisiteReport.serviceLoad !== "not-found")
                return;
        } else if (callPrerequisiteReport.state !== "SERVICE_STOPPED"
                   && callPrerequisiteReport.state !== "AUDIO_PATH_UNVERIFIED") {
            return;
        } else if (callPrerequisiteReport.serviceLoad !== "loaded"
                   || (callPrerequisiteReport.serviceActive !== "active"
                       && callPrerequisiteReport.serviceActive !== "inactive")
                   || callPrerequisiteReport.package === "NOT_INSTALLED") {
            return;
        }
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
            return "Fedora's interactive installer runs in the PHONE terminal for missing oFono. Once installed, guided systemd and WirePlumber HFP setup uses the same PHONE terminal. Use FOCUS TERMINAL if typing fails; after the command finishes, the terminal closes automatically. An active transaction is never killed by closing PHONE. Social has not assumed installation succeeded or calling is ready.";
        if (callSetupStatus === "GUI_OPEN_REQUESTED")
            return "A native PackageKit installer was requested. Review and approve it there, then choose CHECK AGAIN. No installation was confirmed by Social.";
        if (callSetupStatus === "RECHECKING")
            return "Checking oFono, the system service and BlueFerry call status...";
        if (callSetupStatus === "INSTALL_NOT_CONFIRMED")
            return "oFono is still reported missing. On Silverblue, an rpm-ostree install is not active until a separately approved reboot. Check rpm-ostree status before retrying setup. No audio changes were made by Social.";
        if (callSetupStatus === "FOLLOWUP_REQUIRED")
            return "Setup session ended. CHECK AGAIN refreshes prerequisites. Silverblue requires a separate reboot after package installation; service and HFP changes require separate confirmations.";
        if (callSetupStatus === "READY_TO_CONTINUE")
            return "oFono is installed. FINISH CALLING SETUP reviews service, user D-Bus access and the WirePlumber HFP backend. Each change needs a separate confirmation; CALLS ON PC remains a separate opt-in.";
        if (callSetupStatus === "STAGE_BAY_TOO_SMALL")
            return "PHONE is too small for an interactive installer. Enlarge the Social panel and try SET UP CALLING again. No external window was opened.";
        if (callSetupStatus === "TERMINAL_UNAVAILABLE")
            return "The embedded installer cannot start." + callingMissingToolText()
                + " No external window was opened and no package was installed.";
        if (callSetupStatus === "PACKAGE_MANAGER_UNAVAILABLE")
            return "No supported Fedora package installer is available to PHONE."
                + callingMissingToolText()
                + (callSetupMissingTools.indexOf("RPM_OSTREE") >= 0
                   ? " Silverblue requires trusted host rpm-ostree. No installation was attempted."
                   : " Either PackageKit or BOTH Polkit and DNF5 are required. No installation was attempted.");
        if (callSetupStatus === "GUI_UNAVAILABLE")
            return "The embedded package installer is unavailable. No external window was opened or package installed.";
        if (callSetupStatus === "GUI_LAUNCH_FAILED")
            return "PHONE could not start the embedded installer terminal. No external window was opened or installation confirmed.";
        if (callSetupStatus === "UNSUPPORTED_HOST")
            return "Automatic package selection is currently supported on Fedora only. No changes were made.";
        if (callSetupStatus === "DIAGNOSIS_UNAVAILABLE"
                || callSetupStatus === "NOT_APPLICABLE")
            return "Calling setup could not be started from the current system diagnosis. Check the call prerequisite status again.";
        return "";
    }

    // Explain the existing sanitized statuses without claiming verified audio.
    function callProgressText() {
        if ((callSetupStatus !== "FOLLOWUP_REQUIRED"
                && callSetupStatus !== "READY_TO_CONTINUE")
                || callPrerequisiteCheck !== "CHECKED")
            return "";
        var stage = callPrerequisiteReport.state;
        if (stage === "SERVICE_STOPPED")
            return "oFono is installed but stopped. FINISH CALLING SETUP can request a one-time, separately approved service start; nothing starts automatically.";
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
            return "oFono is installed as a service but is stopped. FINISH CALLING SETUP offers a reviewed, one-time system service start.";
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
        nicknameEditorOpen = false;
        phoneNicknameCheck = "NOT CHECKED";
        phoneNickname = ({});
        nicknameActionStatus = "IDLE";
        deviceObservationProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneDeviceObservation.py"),
            "--inspect"
        ];
        deviceObservationProcess.running = true;
    }

    // MAP/PBAP availability observations contain no message or contact content.
    // CONNECT PHONE requests this once. Even a reported active provider
    // profile is not authorization for Social to read or send anything.
    function refreshContentDiagnostic() {
        if (!visible || contentDiagnosticProcess.running)
            return;
        contentDiagnosticCheck = "CHECKING";
        contentDiagnostic = ({});
        contentDiagnosticProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneContentDiagnostic.py"),
            "--inspect"
        ];
        contentDiagnosticProcess.running = true;
    }

    function contentDiagnosticText(section) {
        if (contentDiagnosticCheck === "CHECKING")
            return "Checking the iPhone's message and contact channels. No private data is read.";
        if (contentDiagnosticCheck !== "CHECKED")
            return "PHONE DATA NOT CHECKED // Use CONNECT PHONE to inspect available channels. Your desktop audio connection is separate.";
        if (contentDiagnostic.state === "DEVICE_OFFLINE")
            return "The configured iPhone is paired but not currently connected over Bluetooth. Messages and contacts are not verified.";
        if (contentDiagnostic.state !== "BACKEND_REPORTED")
            return "The matching iPhone data channels could not be verified. This does not affect existing audio routing.";
        if (section === "CONTACTS") {
            var contacts = contentDiagnostic.contacts || {};
            if (contacts.state !== "PBAP_ACTIVE_BACKEND_REPORT")
                return "CONTACTS // PBAP is not reported active. Check iPhone Bluetooth contact-sync permission and BlueFerry. Social is not authorized to read contacts yet.";
            var amount = contacts.cachedCount;
            var extra = typeof amount === "number"
                        ? " BlueFerry reports " + amount + " cached contact cards."
                        : " Contact cache size is not reported.";
            return "CONTACTS // PBAP session reported active." + extra
                   + " Social contact access is still NOT LINKED.";
        }
        var messages = contentDiagnostic.messages || {};
        if (messages.state !== "MAP_ACTIVE_BACKEND_REPORT")
            return "MESSAGES // Bluetooth MAP is not reported active. Check BlueFerry's message access on the iPhone. Audio working does not mean messages are available.";
        return "MESSAGES // Bluetooth MAP session reported active. Message history and Social permission are NOT VERIFIED. The trusted data bridge is still required.";
    }

    // A nickname is a local display preference for the physically verified
    // BlueFerry profile. It never names an authorized Social identity or line.
    function refreshPhoneNickname() {
        if (!visible || nicknameReadProcess.running || nicknameWriteProcess.running
                || deviceObservationCheck !== "CHECKED"
                || (deviceObservation.state !== "BLUETOOTH_CONNECTED"
                    && deviceObservation.state !== "PAIRED_OFFLINE"))
            return;
        phoneNicknameCheck = "CHECKING";
        phoneNickname = ({});
        nicknameReadProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneNickname.py"),
            "--read", deviceObservation.profileId
        ];
        nicknameReadProcess.running = true;
    }

    function changePhoneNickname(action) {
        if (!visible || !nicknameEditorOpen || stageWanted
                || nicknameWriteProcess.running || nicknameReadProcess.running
                || deviceObservationCheck !== "CHECKED"
                || (deviceObservation.state !== "BLUETOOTH_CONNECTED"
                    && deviceObservation.state !== "PAIRED_OFFLINE")
                || (action !== "save" && action !== "clear"))
            return;
        var name = phoneNicknameInput.text.trim();
        if (action === "save" && (name.length < 1 || name.length > 40)) {
            nicknameActionStatus = "INVALID_NICKNAME";
            return;
        }
        nicknameWriteProfile = deviceObservation.profileId;
        nicknameWriteIntent = action;
        nicknameActionStatus = "WORKING";
        nicknameWriteProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneNickname.py"),
            action === "save" ? "--save" : "--clear",
            nicknameWriteProfile
        ];
        if (action === "save")
            nicknameWriteProcess.command =
                nicknameWriteProcess.command.concat([name]);
        nicknameWriteProcess.running = true;
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

    function focusStagedInstaller() {
        if (!visible || selectedSection !== "DEVICE" || !stageWanted
                || stagePurpose !== "OFONO" || stageState !== "ALIGNED"
                || stageFocusProcess.running)
            return;
        // User click only. Restores keyboard input to exactly the installed
        // foot actor, without sending Enter or stopping a package transaction.
        stageFocusProcess.command = [
            "python3",
            Quickshell.shellPath("services/phone/PhoneStageDirector.py"),
            "--focus-installer"
        ];
        stageFocusProcess.running = true;
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
        if (!personalReadUiReady) return;
        if (selectedSection !== "DEVICE") closeStagedSetup();
        if (selectedSection !== "CALLS") {
            callsWorkspaceGeneration += 1;
            callsConfirmDial = false;
            callsPendingDial = "";
            liveCalls = ([]);
            if (phoneCallsStatusProcess.running)
                phoneCallsStatusProcess.running = false;
        }
        if (visible && selectedSection === "CALLS" && !callsRequireExplicitRefresh)
            refreshCallsWorkspace();
        if (visible && phoneStorageState === "UNKNOWN")
            checkBlueFerryStorage();
        personalReadGeneration += 1;
        if (personalReadProcess.running)
            personalReadProcess.running = false;
        if (personalStatusProcess.running)
            personalStatusProcess.running = false;
        if (visible && (selectedSection === "MESSAGES"
                        || selectedSection === "CONTACTS")) {
            if (personalApproved && !personalNeedsExplicitReload)
                loadPersonalSnapshot();
            else
                checkPersonalApproval(false, false);
        }
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
        refreshContentDiagnostic();
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
        // Preserve the independent native setup/installer exit behavior.
        if (!visible) closeStagedSetup();
        if (!personalReadUiReady) return;
        if (!visible) {
            personalReadGeneration += 1;
            phoneStorageGeneration += 1;
            callsWorkspaceGeneration += 1;
            callsConfirmDial = false;
            callsPendingDial = "";
            liveCalls = ([]);
            if (phoneCallsStatusProcess.running)
                phoneCallsStatusProcess.running = false;
            if (personalReadProcess.running)
                personalReadProcess.running = false;
            if (personalStatusProcess.running)
                personalStatusProcess.running = false;
            if (phoneStorageStatusProcess.running)
                phoneStorageStatusProcess.running = false;
            if (phoneStorageUnlockProcess.running)
                phoneStorageUnlockProcess.running = false;
            phoneReadAdapter.forgetHostView();
            personalPermissionOpen = false;
            personalApproved = false;
        }
        if (visible) {
            callsWorkspaceGeneration += 1;
            liveCalls = ([]);
            callsWorkspaceState = "NOT_CHECKED";
            callsWorkspaceResult = "IDLE";
            callsConfirmDial = false;
            callsPendingDial = "";
            phoneStorageGeneration += 1;
            phoneStorageState = "UNKNOWN";
            phoneStoragePolicy = "unknown";
            personalReadStatus = "CHECKING_PERMISSION";
            personalReadOperation = "";
            personalConsentStatus = "IDLE";
            personalPermissionOpen = false;
            personalApproved = false;
            phoneReadAdapter.forgetHostView();
            selectedSection = "MESSAGES";
            setupState = "NOT STARTED";
            setupReport = ({});
            detailsOpen = false;
            nativeSetupStatus = "IDLE";
            nativeSetupTarget = "";
            savedBridgeCheck = "NOT CHECKED";
            savedBridgeState = ({});
            contentDiagnosticCheck = "NOT CHECKED";
            contentDiagnostic = ({});
            deviceObservationCheck = "NOT CHECKED";
            deviceObservation = ({});
            phoneNicknameCheck = "NOT CHECKED";
            phoneNickname = ({});
            nicknameEditorOpen = false;
            nicknameActionStatus = "IDLE";
            nicknameWriteProfile = "";
            nicknameWriteIntent = "";
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
            // Only a previously remembered Personal consent may auto-read.
            // No pairing, new approval or device configuration on menu open.
            Qt.callLater(function() {
                if (phonePane.visible) {
                    phonePane.checkBlueFerryStorage();
                    phonePane.checkPersonalApproval(!phonePane.personalNeedsExplicitReload, false);
                }
            });
        }
    }

    function callsWorkspaceMessage() {
        switch (callsWorkspaceState) {
        case "CHECKING": return "CHECKING IPHONE HANDS-FREE CALLS...";
        case "READY": return liveCalls.length > 0
                       ? "LIVE CALLS // " + liveCalls.length + " reported by BlueFerry."
                       : "CALLS READY // No current calls. A real test call must still verify mic and speaker.";
        case "DISABLED": return "CALLS DISABLED // Open DEVICE and enable CALLS ON PC after oFono setup.";
        case "UNAVAILABLE": return "OFONO OR HFP UNAVAILABLE // Check oFono permissions and WirePlumber HFP backend.";
        case "SEARCHING": return "HFP SEARCHING // BlueFerry has not found the iPhone hands-free modem.";
        case "CONNECTING": return "HFP CONNECTING // Waiting for the phone modem to come online.";
        case "BLUEZ_CONFLICT": return "HFP CONFLICT // BlueZ and oFono are competing for the hands-free profile.";
        case "DEVICE_UNAVAILABLE": return "PHONE NOT READY // No matching connected Personal iPhone.";
        case "UNSUPPORTED": return "CALLS1 NOT SUPPORTED // Check installed BlueFerry version.";
        case "BACKEND_UNAVAILABLE": return "BLUEFERRY CALLS SERVICE UNAVAILABLE // No live call control.";
        case "IDENTITY_CHANGED": return "SOCIAL IDENTITY CHANGED // Select REFRESH CALLS to view Personal calls.";
        default: return "CALLS NOT CHECKED // Select REFRESH CALLS.";
        }
    }

    function callsActionMessage() {
        switch (callsWorkspaceResult) {
        case "SUBMITTING": return "REQUESTING PHONE ACTION...";
        case "ACTION_SUBMITTED": return "REQUEST ACCEPTED BY BLUEFERRY // Actual call state will update separately.";
        case "ACTION_REFUSED": return "ACTION NOT VALID FOR THE CURRENT CALL. Refresh and try again.";
        case "ACTION_FAILED": return "CALL ACTION FAILED // BlueFerry did not confirm the request.";
        case "ACTION_NOT_CONFIRMED": return "CALL ACTION SENT, BUT HFP STATE CHANGED. Verify on your iPhone.";
        case "DEVICE_UNAVAILABLE": return "PHONE DISCONNECTED OR CHANGED DURING THE REQUEST.";
        case "INVALID_NUMBER": return "ENTER A PLAIN PHONE NUMBER WITH COUNTRY CODE IF NEEDED.";
        case "CONFIRM_DIAL": return "CONFIRM THIS NUMBER. Emergencies must be called directly on the iPhone.";
        default: return "";
        }
    }

    function activeCallId() {
        for (var i = 0; i < liveCalls.length; ++i) {
            if (liveCalls[i].state === "active")
                return String(liveCalls[i].id);
        }
        return "";
    }

    function canSwapCalls() {
        var active = false, held = false;
        for (var i = 0; i < liveCalls.length; ++i) {
            active = active || liveCalls[i].state === "active";
            held = held || liveCalls[i].state === "held";
        }
        return active && held;
    }

    function canHoldAnswer() {
        var active = false, waiting = false;
        for (var i = 0; i < liveCalls.length; ++i) {
            active = active || liveCalls[i].state === "active";
            waiting = waiting || liveCalls[i].state === "waiting";
        }
        return active && waiting;
    }

    function refreshCallsWorkspace() {
        if (!visible || selectedSection !== "CALLS" || stageWanted
                || phoneCallsStatusProcess.running || phoneCallsActionProcess.running)
            return;
        callsRequireExplicitRefresh = false;
        // Keep ready actions visible while a normal live refresh is pending.
        if (callsWorkspaceState !== "READY")
            callsWorkspaceState = "CHECKING";
        phoneCallsStatusProcess.generation = callsWorkspaceGeneration;
        phoneCallsStatusProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneCallWorkspace.py"),
            "--status"
        ];
        phoneCallsStatusProcess.running = true;
    }

    function preparePhoneDial() {
        if (!visible || selectedSection !== "CALLS"
                || callsWorkspaceState !== "READY"
                || phoneCallsActionProcess.running)
            return;
        var entered = phoneDialInput.text.trim();
        if (!/^\+?[0-9]{3,18}$/.test(entered)) {
            callsWorkspaceResult = "INVALID_NUMBER";
            return;
        }
        callsPendingDial = entered;
        callsConfirmDial = true;
        callsWorkspaceResult = "CONFIRM_DIAL";
    }

    function requestCallAction(action, argument) {
        if (!visible || selectedSection !== "CALLS"
                || callsWorkspaceState !== "READY"
                || phoneCallsActionProcess.running
                || phoneCallsStatusProcess.running)
            return;
        var named = ["dial", "answer", "decline", "hangup", "tones"];
        var plain = ["swap", "hold-answer"];
        if (named.indexOf(action) < 0 && plain.indexOf(action) < 0)
            return;
        if (action === "dial" && (!callsConfirmDial || argument !== callsPendingDial))
            return;
        if (action === "dial") {
            callsConfirmDial = false;
            callsPendingDial = "";
            phoneDialInput.text = "";
        }
        callsWorkspaceResult = "SUBMITTING";
        phoneCallsActionProcess.generation = callsWorkspaceGeneration;
        phoneCallsActionProcess.requestAction = action;
        phoneCallsActionProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneCallWorkspace.py"),
            "--action", action
        ];
        if (named.indexOf(action) >= 0)
            phoneCallsActionProcess.command =
                phoneCallsActionProcess.command.concat([argument]);
        phoneCallsActionProcess.running = true;
    }

    Process {
        id: phoneCallsStatusProcess
        property int generation: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.selectedSection !== "CALLS"
                        || phoneCallsStatusProcess.generation
                           !== phonePane.callsWorkspaceGeneration
                        || phonePane.callsRequireExplicitRefresh)
                    return;
                try {
                    var response = JSON.parse(String(text || ""));
                    if (response.schema !== "post-apollo.phone.calls-workspace.v0"
                            || response.execution !== "PERSONAL_SESSION_BLUEFERRY_CALLS1"
                            || response.scope !== "PERSONAL_LOCAL_USER_ONLY"
                            || response.organizationGrant !== false
                            || response.faceTimeEnabled !== false
                            || response.smsReplyEnabled !== false
                            || response.autoCallingEnabled !== false
                            || typeof response.state !== "string"
                            || ["READY", "DISABLED", "UNAVAILABLE", "SEARCHING",
                                "CONNECTING", "BLUEZ_CONFLICT", "DEVICE_UNAVAILABLE",
                                "UNSUPPORTED", "BACKEND_UNAVAILABLE"].indexOf(response.state) < 0)
                        throw new Error("invalid CALLS status");
                    var calls = response.state === "READY" ? response.calls : [];
                    if (!Array.isArray(calls) || calls.length > 8)
                        throw new Error("invalid call list");
                    for (var i = 0; i < calls.length; ++i) {
                        var c = calls[i];
                        if (!c || typeof c.id !== "string" || c.id.length > 128
                                || typeof c.peer !== "string" || c.peer.length > 96
                                || ["incoming", "waiting", "dialing", "alerting",
                                    "active", "held", "disconnecting"].indexOf(c.state) < 0
                                || typeof c.multiparty !== "boolean"
                                || typeof c.emergency !== "boolean")
                            throw new Error("invalid call");
                    }
                    phonePane.liveCalls = calls;
                    phonePane.callsWorkspaceState = response.state;
                } catch (error) {
                    phonePane.liveCalls = ([]);
                    phonePane.callsWorkspaceState = "BACKEND_UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.selectedSection === "CALLS"
                    && code !== 0 && generation === phonePane.callsWorkspaceGeneration) {
                phonePane.liveCalls = ([]);
                phonePane.callsWorkspaceState = "BACKEND_UNAVAILABLE";
            }
        }
    }

    Process {
        id: phoneCallsActionProcess
        property int generation: 0
        property string requestAction: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.selectedSection !== "CALLS"
                        || generation !== phonePane.callsWorkspaceGeneration)
                    return;
                try {
                    var result = JSON.parse(String(text || ""));
                    if (result.schema !== "post-apollo.phone.calls-workspace.v0"
                            || result.execution !== "PERSONAL_SESSION_BLUEFERRY_CALLS1"
                            || result.scope !== "PERSONAL_LOCAL_USER_ONLY"
                            || result.organizationGrant !== false
                            || result.faceTimeEnabled !== false
                            || result.smsReplyEnabled !== false
                            || result.autoCallingEnabled !== false
                            || ["ACTION_SUBMITTED", "ACTION_REFUSED", "ACTION_FAILED",
                                "ACTION_NOT_CONFIRMED", "DEVICE_UNAVAILABLE",
                                "DISABLED", "UNAVAILABLE", "SEARCHING",
                                "CONNECTING", "BLUEZ_CONFLICT",
                                "BACKEND_UNAVAILABLE"].indexOf(result.state) < 0)
                        throw new Error("invalid call action");
                    phonePane.callsWorkspaceResult = result.state;
                } catch (error) {
                    phonePane.callsWorkspaceResult = "ACTION_FAILED";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.selectedSection === "CALLS"
                    && generation === phonePane.callsWorkspaceGeneration) {
                if (code !== 0)
                    phonePane.callsWorkspaceResult = "ACTION_FAILED";
                Qt.callLater(function() {
                    if (phonePane.visible && phonePane.selectedSection === "CALLS")
                        phonePane.refreshCallsWorkspace();
                });
            }
        }
    }

    Timer {
        interval: 2500
        repeat: true
        running: phonePane.visible && phonePane.selectedSection === "CALLS"
                 && !phonePane.callsRequireExplicitRefresh
                 && !phoneCallsActionProcess.running
        onTriggered: phonePane.refreshCallsWorkspace()
    }

    // The service adapter only displays already-released projections.
    // A user-private saved preference, not app/process authentication, allows
    // Personal one-shot reads without opening a terminal or persistent socket.
    PhoneAdapters.BlueFerryAdapter {
        id: phoneReadAdapter
        active: phonePane.visible
    }

    function personalReadMessage() {
        if (phoneStorageState === "LOCKED" || phoneStorageState === "UNLOCKING")
            return phoneStorageMessage();
        if (phoneStorageState === "UNLOCK_FAILED")
            return phoneStorageMessage();
        if (phoneStorageState === "NO_RETENTION")
            return "BLUEFERRY DATA NOT RETAINED // History and contacts are not cached. Changing retention can erase existing cache.";
        switch (personalReadStatus) {
        case "READING": return "READING IPHONE // Checking the selected device and BlueFerry...";
        case "CHECKING_PERMISSION": return "CHECKING SAVED PERSONAL APPROVAL...";
        case "SAVING_APPROVAL": return "SAVING PERSONAL READ PREFERENCE...";
        case "LOCAL_SNAPSHOT":
            return selectedSection === "CONTACTS"
                ? "PERSONAL CONTACTS // " + phoneReadAdapter.contactCards.length
                  + " cards received. READ ONLY."
                : "PERSONAL MESSAGES // " + phoneReadAdapter.conversations.length
                  + " threads received. READ ONLY.";
        case "APPROVAL_REQUIRED": return "PERMISSION REQUIRED // Select APPROVE READ once.";
        case "APPROVED": return "PERSONAL READ APPROVED // Loading or select REFRESH.";
        case "NOT_CONSENTED": return "THIS TAB IS NOT APPROVED // Select APPROVE READ to change access.";
        case "DEVICE_UNAVAILABLE": return "IPHONE OFFLINE OR DIFFERENT DEVICE // Reconnect the saved phone.";
        case "PROVIDER_UNAVAILABLE": return "BLUEFERRY READ SERVICE UNAVAILABLE // Check DEVICE status.";
        case "READ_UNAVAILABLE": return "READ FAILED // BlueFerry did not return a usable snapshot.";
        case "STORAGE_UNAVAILABLE": return "SAVED PERMISSION UNAVAILABLE // Check local state permissions.";
        case "REVOKED": return "PERSONAL READ APPROVAL REVOKED // No private data displayed.";
        case "REVOKE_FAILED": return "WARNING // View cleared, saved approval could NOT be revoked.";
        case "IDENTITY_CHANGED": return "SOCIAL IDENTITY CHANGED // Personal data hidden.";
        case "VIEW_CLEARED": return "LOCAL PHONE VIEW CLEARED.";
        case "STATUS_UNAVAILABLE": return "PHONE STATUS CHECK FAILED // Local data hidden.";
        case "BRIDGE_UNAVAILABLE": return "PHONE READ COMMAND FAILED // The bridge did not start.";
        case "APPROVAL_FAILED": return "COULD NOT SAVE APPROVAL // Check phone connection and storage.";
        default: return "PERSONAL READ ONLY // Approval is remembered until revoked.";
        }
    }

    function openPersonalConsent() {
        if (!visible || stageWanted || personalConsentProcess.running)
            return;
        personalPermissionOpen = true;
        personalReadStatus = "APPROVAL_REQUIRED";
    }

    function savePersonalApproval(choice) {
        if (!visible || !personalPermissionOpen || personalConsentProcess.running
                || ["m", "c", "b"].indexOf(choice) < 0)
            return;
        personalConsentStatus = "SAVING";
        personalReadStatus = "SAVING_APPROVAL";
        personalConsentProcess.requestGeneration = personalReadGeneration;
        personalConsentProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneRememberedRead.py"),
            "--approve", choice
        ];
        personalConsentProcess.running = true;
    }

    function checkPersonalApproval(autoRead, promptIfMissing) {
        if (!visible || !personalReadUiReady)
            return;
        if (personalStatusProcess.running) {
            personalStatusProcess.wantsAutoRead = personalStatusProcess.wantsAutoRead
                                                  || autoRead;
            personalStatusProcess.promptIfMissing = personalStatusProcess.promptIfMissing
                                                     || promptIfMissing;
            return;
        }
        personalStatusProcess.requestGeneration = personalReadGeneration;
        personalStatusProcess.requestedContext = phoneReadAdapter._contextKey;
        personalStatusProcess.requestedEpoch = phoneReadAdapter._contextEpoch;
        personalStatusProcess.wantsAutoRead = autoRead;
        personalStatusProcess.promptIfMissing = promptIfMissing;
        personalStatusProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneRememberedRead.py"),
            "--status"
        ];
        personalStatusProcess.running = true;
    }

    function loadPersonalSnapshot() {
        if (!visible || personalPermissionOpen || personalReadProcess.running
                || (selectedSection !== "MESSAGES" && selectedSection !== "CONTACTS"))
            return;
        if (phoneStorageState === "LOCKED" || phoneStorageState === "UNLOCKING"
                || phoneStorageState === "UNLOCK_FAILED"
                || phoneStorageState === "NO_RETENTION") {
            personalReadStatus = "LOCAL_STORAGE_LOCKED";
            return;
        }
        personalNeedsExplicitReload = false; // User explicitly requested Personal.
        if (!personalApproved) {
            // A click must never appear to do nothing. Restore an existing
            // saved approval or show the in-PHONE permission prompt.
            personalReadStatus = "CHECKING_PERMISSION";
            checkPersonalApproval(true, true);
            return;
        }
        personalReadGeneration += 1;
        personalReadOperation = selectedSection === "MESSAGES"
                                ? "messages.read" : "contacts.read";
        personalReadStatus = "READING";
        personalReadProcess.requestGeneration = personalReadGeneration;
        personalReadProcess.requestOperation = personalReadOperation;
        personalReadProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneRememberedRead.py"),
            "--read", personalReadOperation
        ];
        personalReadProcess.running = true;
    }

    function revokePersonalAccess() {
        if (!visible || personalRevokeProcess.running)
            return;
        personalReadGeneration += 1;
        if (personalReadProcess.running)
            personalReadProcess.running = false;
        phoneReadAdapter.forgetHostView();
        personalApproved = false;
        personalPermissionOpen = false;
        personalReadStatus = "VIEW_CLEARED";
        personalRevokeProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneRememberedRead.py"),
            "--revoke"
        ];
        personalRevokeProcess.running = true;
    }

    function clearPersonalView() {
        phoneReadAdapter.forgetHostView();
        personalReadStatus = "VIEW_CLEARED";
    }

    function phoneStorageMessage() {
        switch (phoneStorageState) {
        case "READY":
            return phoneStoragePolicy === "plaintext"
                ? "BLUEFERRY LOCAL DATA // READY (NOT ENCRYPTED)."
                : "BLUEFERRY ENCRYPTED LOCAL DATA // READY.";
        case "LOCKED":
            return "BLUEFERRY STORAGE LOCKED // Select UNLOCK DATA. Incoming notifications can still arrive.";
        case "UNLOCKING":
            return "UNLOCKING BLUEFERRY DATA // Use the desktop wallet prompt if shown...";
        case "UNLOCK_FAILED":
            return "BLUEFERRY UNLOCK FAILED // Retry UNLOCK DATA or check your desktop wallet.";
        case "NO_RETENTION":
            return "BLUEFERRY DOES NOT RETAIN LOCAL DATA // No saved history or contacts cache.";
        case "UNAVAILABLE":
            return "BLUEFERRY STORAGE STATE UNAVAILABLE // Check the running BlueFerry service.";
        case "PROVIDER_UNAVAILABLE":
            return "BLUEFERRY STORAGE SERVICE NOT AVAILABLE // Check the iPhone data service.";
        default:
            return "BLUEFERRY STORAGE // Checking local data availability...";
        }
    }

    function checkBlueFerryStorage() {
        if (!visible || !personalReadUiReady || phoneStorageStatusProcess.running
                || phoneStorageUnlockProcess.running)
            return;
        phoneStorageStatusProcess.requestGeneration = phoneStorageGeneration;
        phoneStorageStatusProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneBlueFerryStorageUi.py"),
            "--status"
        ];
        phoneStorageStatusProcess.running = true;
    }

    function unlockBlueFerryStorage() {
        if (!visible || phoneStorageUnlockProcess.running
                || (phoneStorageState !== "LOCKED"
                    && phoneStorageState !== "UNLOCK_FAILED"))
            return;
        phoneStorageGeneration += 1;
        if (phoneStorageStatusProcess.running)
            phoneStorageStatusProcess.running = false;
        phoneStorageState = "UNLOCKING";
        phoneStorageUnlockProcess.requestGeneration = phoneStorageGeneration;
        phoneStorageUnlockProcess.command = [
            "python3", Quickshell.shellPath("services/phone/PhoneBlueFerryStorageUi.py"),
            "--unlock"
        ];
        phoneStorageUnlockProcess.running = true;
    }

    Process {
        id: phoneStorageStatusProcess
        property int requestGeneration: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phoneStorageUnlockProcess.running
                        || phoneStorageStatusProcess.requestGeneration
                           !== phonePane.phoneStorageGeneration)
                    return;
                try {
                    var reply = JSON.parse(String(text || ""));
                    if (reply.schema !== "post-apollo.phone.blueferry-storage-ui.v0"
                            || reply.execution !== "EXPLICIT_BLUEFERRY_STORAGE_UNLOCK"
                            || reply.contentsIncluded !== false
                            || reply.credentialsIncluded !== false
                            || ["READY", "LOCKED", "NO_RETENTION", "UNAVAILABLE",
                                "PROVIDER_UNAVAILABLE"].indexOf(reply.state) < 0
                            || ["encrypted", "plaintext", "none", "unknown"].indexOf(reply.storagePolicy) < 0)
                        throw new Error("invalid storage state");
                    var old = phonePane.phoneStorageState;
                    phonePane.phoneStorageState = reply.state;
                    phonePane.phoneStoragePolicy = reply.storagePolicy;
                    if (reply.state !== "READY") {
                        // A stale read must not repopulate the view after
                        // locking the keyring or losing the provider.
                        phonePane.personalReadGeneration += 1;
                        if (personalReadProcess.running)
                            personalReadProcess.running = false;
                        phoneReadAdapter.forgetHostView();
                    } else if (reply.state === "READY" && old === "LOCKED"
                               && phonePane.personalApproved
                               && !phonePane.personalNeedsExplicitReload)
                        Qt.callLater(function() {
                            if (phonePane.visible
                                    && (phonePane.selectedSection === "MESSAGES"
                                        || phonePane.selectedSection === "CONTACTS"))
                                phonePane.loadPersonalSnapshot();
                        });
                } catch (error) {
                    phonePane.phoneStorageState = "UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && code !== 0
                    && requestGeneration === phonePane.phoneStorageGeneration)
                phonePane.phoneStorageState = "UNAVAILABLE";
        }
    }

    Process {
        id: phoneStorageUnlockProcess
        property int requestGeneration: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phoneStorageUnlockProcess.requestGeneration
                                            !== phonePane.phoneStorageGeneration)
                    return;
                try {
                    var reply = JSON.parse(String(text || ""));
                    if (reply.schema !== "post-apollo.phone.blueferry-storage-ui.v0"
                            || reply.execution !== "EXPLICIT_BLUEFERRY_STORAGE_UNLOCK"
                            || reply.contentsIncluded !== false
                            || reply.credentialsIncluded !== false
                            || ["READY", "UNLOCK_FAILED", "UNLOCK_UNAVAILABLE",
                                "NO_RETENTION"].indexOf(reply.state) < 0)
                        throw new Error("invalid unlock result");
                    phonePane.phoneStorageState = reply.state === "READY"
                                                 ? "READY" : "UNLOCK_FAILED";
                    phonePane.phoneStoragePolicy = reply.storagePolicy;
                    if (reply.state === "READY" && phonePane.personalApproved
                            && !phonePane.personalNeedsExplicitReload)
                        Qt.callLater(function() {
                            if (phonePane.visible
                                    && (phonePane.selectedSection === "MESSAGES"
                                        || phonePane.selectedSection === "CONTACTS"))
                                phonePane.loadPersonalSnapshot();
                        });
                } catch (error) {
                    phonePane.phoneStorageState = "UNLOCK_FAILED";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && code !== 0
                    && requestGeneration === phonePane.phoneStorageGeneration)
                phonePane.phoneStorageState = "UNLOCK_FAILED";
        }
    }

    // Only metadata is polled. This never unlocks the wallet on its own.
    Timer {
        interval: 12500
        repeat: true
        running: phonePane.visible && !phoneStorageUnlockProcess.running
        onTriggered: phonePane.checkBlueFerryStorage()
    }

    Process {
        id: personalConsentProcess
        property int requestGeneration: 0
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible
                        || personalConsentProcess.requestGeneration
                           !== phonePane.personalReadGeneration)
                    return;
                try {
                    var result = JSON.parse(String(text || ""));
                    if (result.schema !== "post-apollo.phone.personal-remembered-read.v0"
                            || result.execution !== "LOCAL_USER_PREFERENCE_NOT_AUTHORITY"
                            || result.ownerKind !== "PERSONAL"
                            || result.organizationAccess !== false
                            || result.sendingEnabled !== false)
                        throw new Error("invalid Personal preference response");
                    if (result.state !== "APPROVED") {
                        phonePane.personalReadStatus =
                            result.state === "STORAGE_UNAVAILABLE" ? result.state
                            : result.state === "DEVICE_UNAVAILABLE" ? result.state
                            : result.state === "PROVIDER_UNAVAILABLE" ? result.state
                            : "APPROVAL_FAILED";
                        return;
                    }
                    phonePane.personalApproved = true;
                    phonePane.personalPermissionOpen = false;
                    phonePane.personalConsentStatus = "SAVED";
                    phonePane.personalReadStatus = "APPROVED";
                    Qt.callLater(function() {
                        if (phonePane.visible)
                            phonePane.loadPersonalSnapshot();
                    });
                } catch (error) {
                    phonePane.personalReadStatus = "APPROVAL_FAILED";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && code !== 0
                    && requestGeneration === phonePane.personalReadGeneration
                    && phonePane.personalReadStatus === "SAVING_APPROVAL")
                phonePane.personalReadStatus = "APPROVAL_FAILED";
        }
    }

    Process {
        id: personalReadProcess
        property int requestGeneration: 0
        property string requestOperation: ""
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible
                        || personalReadProcess.requestGeneration
                           !== phonePane.personalReadGeneration
                        || phonePane.personalReadStatus !== "READING"
                        || ((phonePane.selectedSection === "MESSAGES"
                             ? "messages.read" : phonePane.selectedSection === "CONTACTS"
                             ? "contacts.read" : "") !== personalReadProcess.requestOperation))
                    return;
                try {
                    var value = JSON.parse(String(text || ""));
                    if (value.schema !== "post-apollo.phone.personal-remembered-read.v0"
                            || value.execution !== "LOCAL_USER_PREFERENCE_NOT_AUTHORITY"
                            || value.ownerKind !== "PERSONAL"
                            || value.organizationAccess !== false
                            || value.sendingEnabled !== false)
                        throw new Error("unexpected read response");
                    if (value.state !== "SNAPSHOT") {
                        phoneReadAdapter.forgetHostView();
                        phonePane.personalReadStatus =
                            ["APPROVAL_REQUIRED", "NOT_CONSENTED",
                             "DEVICE_UNAVAILABLE", "PROVIDER_UNAVAILABLE",
                             "READ_UNAVAILABLE", "STORAGE_UNAVAILABLE"].indexOf(value.state) >= 0
                            ? value.state : "BRIDGE_UNAVAILABLE";
                        if (value.state === "APPROVAL_REQUIRED") {
                            phonePane.personalApproved = false;
                            phonePane.openPersonalConsent();
                        }
                        return;
                    }
                    if (value.operation !== personalReadProcess.requestOperation
                            || typeof value.contextKey !== "string"
                            || typeof value.profileId !== "string"
                            || typeof value.epoch !== "number"
                            || typeof value.sequence !== "number"
                            || !value.projection)
                        throw new Error("invalid projection envelope");
                    if (phoneReadAdapter._contextKey !== value.contextKey
                            || phoneReadAdapter._contextEpoch !== value.epoch
                            || phoneReadAdapter._profileId !== value.profileId) {
                        phoneReadAdapter.forgetHostView();
                        if (!phoneReadAdapter.beginHostView(
                                value.contextKey, value.profileId, value.epoch))
                            throw new Error("stale or invalid context");
                    }
                    if (!phoneReadAdapter.applyHostProjection(
                                value.contextKey, value.epoch, value.sequence,
                                value.operation, value.projection))
                        throw new Error("rejected projection");
                    phonePane.personalReadStatus = "LOCAL_SNAPSHOT";
                } catch (error) {
                    phoneReadAdapter.forgetHostView();
                    phonePane.personalReadStatus = "READ_UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && code !== 0
                    && requestGeneration === phonePane.personalReadGeneration
                    && phonePane.personalReadStatus === "READING")
                phonePane.personalReadStatus = "BRIDGE_UNAVAILABLE";
        }
    }

    Process {
        id: personalRevokeProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible) return;
                try {
                    var result = JSON.parse(String(text || ""));
                    phonePane.personalReadStatus =
                        result.schema === "post-apollo.phone.personal-remembered-read.v0"
                        && result.execution === "LOCAL_USER_PREFERENCE_NOT_AUTHORITY"
                        && result.ownerKind === "PERSONAL"
                        && result.organizationAccess === false
                        && result.sendingEnabled === false
                        && result.state === "REVOKED"
                        ? "REVOKED" : "REVOKE_FAILED";
                } catch (error) {
                    phonePane.personalReadStatus = "REVOKE_FAILED";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && code !== 0
                    && phonePane.personalReadStatus === "VIEW_CLEARED")
                phonePane.personalReadStatus = "REVOKE_FAILED";
        }
    }

    Process {
        id: personalStatusProcess
        property int requestGeneration: 0
        property string requestedContext: ""
        property int requestedEpoch: 0
        property bool wantsAutoRead: false
        property bool promptIfMissing: false
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible
                        || personalStatusProcess.requestGeneration
                           !== phonePane.personalReadGeneration
                        || (personalStatusProcess.requestedContext !== ""
                            && personalStatusProcess.requestedContext
                               !== phoneReadAdapter._contextKey))
                    return;
                try {
                    var value = JSON.parse(String(text || ""));
                    if (value.schema !== "post-apollo.phone.personal-remembered-read.v0"
                            || value.execution !== "LOCAL_USER_PREFERENCE_NOT_AUTHORITY"
                            || value.ownerKind !== "PERSONAL"
                            || value.organizationAccess !== false
                            || value.sendingEnabled !== false)
                        throw new Error("invalid permission status");
                    if (value.state === "APPROVED") {
                        if (phoneReadAdapter._contextKey !== ""
                                && (value.contextKey !== phoneReadAdapter._contextKey
                                    || value.epoch !== phoneReadAdapter._contextEpoch)) {
                            phonePane.clearPersonalView();
                        }
                        phonePane.personalApproved = true;
                        if (phonePane.personalReadStatus !== "READING"
                                && phonePane.personalReadStatus !== "LOCAL_SNAPSHOT")
                            phonePane.personalReadStatus =
                                phonePane.personalNeedsExplicitReload
                                ? "IDENTITY_CHANGED" : "APPROVED";
                        if (personalStatusProcess.wantsAutoRead
                                && !phonePane.personalNeedsExplicitReload
                                && (phonePane.selectedSection === "MESSAGES"
                                    || phonePane.selectedSection === "CONTACTS"))
                            Qt.callLater(function() {
                                if (phonePane.visible)
                                    phonePane.loadPersonalSnapshot();
                            });
                    } else {
                        phonePane.personalApproved = false;
                        if (phoneReadAdapter._contextKey !== "")
                            phonePane.clearPersonalView();
                        phonePane.personalReadStatus =
                            ["APPROVAL_REQUIRED", "DEVICE_UNAVAILABLE",
                             "STORAGE_UNAVAILABLE"].indexOf(value.state) >= 0
                            ? value.state : "STATUS_UNAVAILABLE";
                        if (value.state === "APPROVAL_REQUIRED"
                                && personalStatusProcess.promptIfMissing)
                            phonePane.openPersonalConsent();
                    }
                } catch (error) {
                    phonePane.personalApproved = false;
                    phonePane.clearPersonalView();
                    phonePane.personalReadStatus = "STATUS_UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (code !== 0 && phonePane.visible
                    && requestGeneration === phonePane.personalReadGeneration) {
                phonePane.personalApproved = false;
                phonePane.clearPersonalView();
                phonePane.personalReadStatus = "STATUS_UNAVAILABLE";
            }
        }
    }

    Timer {
        interval: 8000
        repeat: true
        running: phonePane.visible && phonePane.personalApproved
                 && (phonePane.selectedSection === "MESSAGES"
                     || phonePane.selectedSection === "CONTACTS")
        onTriggered: phonePane.checkPersonalApproval(false, false)
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
        id: contentDiagnosticProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible
                        || phonePane.contentDiagnosticCheck !== "CHECKING")
                    return;
                try {
                    var result = JSON.parse(String(text || ""));
                    var states = ["BACKEND_REPORTED", "DEVICE_OFFLINE", "UNAVAILABLE"];
                    var devices = ["BLUETOOTH_CONNECTED", "PAIRED_OFFLINE", "UNVERIFIED"];
                    var messageStates = [
                        "MAP_ACTIVE_BACKEND_REPORT", "MAP_INACTIVE_BACKEND_REPORT",
                        "UNVERIFIED"
                    ];
                    var contactsStates = [
                        "PBAP_ACTIVE_BACKEND_REPORT", "PBAP_INACTIVE_BACKEND_REPORT",
                        "UNVERIFIED"
                    ];
                    var count = (result.contacts || {}).cachedCount;
                    var validCount = count === null
                        || (typeof count === "number" && Number.isInteger(count)
                            && count >= 0 && count <= 100000);
                    if (result.schema !== "post-apollo.phone.content-diagnostic.v0"
                            || result.execution !== "READ_ONLY_PROVIDER_METADATA"
                            || states.indexOf(result.state) < 0
                            || devices.indexOf(result.deviceState) < 0
                            || !result.messages || !result.contacts
                            || messageStates.indexOf(result.messages.state) < 0
                            || contactsStates.indexOf(result.contacts.state) < 0
                            || !validCount
                            || result.socialLink !== "NOT_AUTHORIZED"
                            || result.trustedPhoneLink !== "UNVERIFIED"
                            || result.routeEligible !== false
                            || result.contentAccessEnabled !== false
                            || (result.state === "BACKEND_REPORTED"
                                && (result.deviceState !== "BLUETOOTH_CONNECTED"
                                    || result.messages.state === "UNVERIFIED"
                                    || result.contacts.state === "UNVERIFIED"))
                            || (result.state === "DEVICE_OFFLINE"
                                && result.deviceState !== "PAIRED_OFFLINE")
                            || (result.state === "UNAVAILABLE"
                                && result.deviceState !== "UNVERIFIED")
                            || (result.state !== "BACKEND_REPORTED"
                                && (result.messages.state !== "UNVERIFIED"
                                    || result.contacts.state !== "UNVERIFIED"
                                    || count !== null)))
                        throw new Error("Unexpected phone data diagnostic");
                    phonePane.contentDiagnostic = result;
                    phonePane.contentDiagnosticCheck = "CHECKED";
                } catch (error) {
                    phonePane.contentDiagnostic = ({});
                    phonePane.contentDiagnosticCheck = "UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode) {
            if (phonePane.visible
                    && phonePane.contentDiagnosticCheck === "CHECKING"
                    && exitCode !== 0)
                phonePane.contentDiagnosticCheck = "UNAVAILABLE";
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
                    phonePane.refreshPhoneNickname();
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
        id: nicknameReadProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.phoneNicknameCheck !== "CHECKING")
                    return;
                try {
                    var result = JSON.parse(String(text || ""));
                    if (result.schema !== "post-apollo.phone.nickname-action.v0"
                            || result.execution !== "LOCAL_DISPLAY_METADATA"
                            || result.profileId !== phonePane.deviceObservation.profileId
                            || result.trustedPhoneLink !== "UNVERIFIED"
                            || result.contentAccessEnabled !== false
                            || ["PRESENT", "EMPTY"].indexOf(result.state) < 0
                            || typeof result.nickname !== "string"
                            || result.nickname.length > 40
                            || (result.state === "EMPTY" && result.nickname !== "")
                            || (result.state === "PRESENT"
                                && (!result.nickname
                                    || result.nickname !== result.nickname.trim()
                                    || /[\x00-\x1f\x7f]/.test(result.nickname))))
                        throw new Error("Invalid nickname result");
                    phonePane.phoneNickname = result;
                    phonePane.phoneNicknameCheck = "CHECKED";
                } catch (error) {
                    phonePane.phoneNickname = ({});
                    phonePane.phoneNicknameCheck = "UNAVAILABLE";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.phoneNicknameCheck === "CHECKING"
                    && code !== 0)
                phonePane.phoneNicknameCheck = "UNAVAILABLE";
        }
    }

    Process {
        id: nicknameWriteProcess
        stdout: StdioCollector {
            onStreamFinished: {
                if (!phonePane.visible || phonePane.nicknameActionStatus !== "WORKING")
                    return;
                try {
                    var next = JSON.parse(String(text || ""));
                    var expected = phonePane.nicknameWriteIntent === "save"
                                   ? "SAVED" : "CLEARED";
                    if (next.schema !== "post-apollo.phone.nickname-action.v0"
                            || next.execution !== "LOCAL_DISPLAY_METADATA"
                            || next.profileId !== phonePane.nicknameWriteProfile
                            || next.profileId !== phonePane.deviceObservation.profileId
                            || next.trustedPhoneLink !== "UNVERIFIED"
                            || next.contentAccessEnabled !== false
                            || next.state !== expected
                            || typeof next.nickname !== "string"
                            || next.nickname.length > 40
                            || (expected === "CLEARED" && next.nickname !== "")
                            || (expected === "SAVED"
                                && (!next.nickname
                                    || next.nickname !== next.nickname.trim()
                                    || /[\x00-\x1f\x7f]/.test(next.nickname))))
                        throw new Error("Invalid nickname write response");
                    phonePane.phoneNickname = ({
                        "state": expected === "SAVED" ? "PRESENT" : "EMPTY",
                        "nickname": next.nickname
                    });
                    phonePane.phoneNicknameCheck = "CHECKED";
                    phonePane.nicknameActionStatus = expected;
                } catch (error) {
                    phonePane.nicknameActionStatus = "NOT_CONFIRMED";
                }
            }
        }
        onExited: function(code) {
            if (phonePane.visible && phonePane.nicknameActionStatus === "WORKING")
                phonePane.nicknameActionStatus = "NOT_CONFIRMED";
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
                                                    : ["SERVICE_STOPPED", "AUDIO_PATH_UNVERIFIED"].indexOf(r.state) >= 0
                                                      ? "READY_TO_CONTINUE" : "FOLLOWUP_REQUIRED";
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
                            || r.missingTools.length > 7
                            || r.missingTools.some(function(v, i) {
                                return typeof v !== "string"
                                    || ["FOOT", "PYTHON3", "INSTALLER_HELPER",
                                        "PKCON", "PKEXEC", "DNF5", "RPM_OSTREE"].indexOf(v) < 0
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
                            phonePane.refreshContentDiagnostic();
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

    Process {
        id: stageFocusProcess
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

    Rectangle {
        id: personalReadBar
        anchors.top: sectionToolbar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: visible ? 44 : 0
        visible: phonePane.selectedSection === "MESSAGES"
                 || phonePane.selectedSection === "CONTACTS"
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan
        z: 6

        Row {
            anchors.centerIn: parent
            spacing: 7
            ActionButton {
                width: Math.max(96, Math.min(150,
                           (personalReadBar.width - 30) / 3))
                height: 31
                label: phonePane.personalApproved ? "PERMISSION ON" : "APPROVE READ"
                labelPixelSize: 9
                accentColor: Colors.magenta
                onTriggered: phonePane.openPersonalConsent()
            }
            ActionButton {
                width: Math.max(96, Math.min(150,
                           (personalReadBar.width - 30) / 3))
                height: 31
                label: phonePane.phoneStorageState === "UNLOCKING"
                       ? "UNLOCKING..."
                       : (phonePane.phoneStorageState === "LOCKED"
                          || phonePane.phoneStorageState === "UNLOCK_FAILED")
                         ? "UNLOCK DATA"
                         : phonePane.personalReadStatus === "READING"
                           ? "LOADING..." : phonePane.personalApproved
                             ? "REFRESH" : "LOAD PERSONAL"
                labelPixelSize: 9
                accentColor: phonePane.phoneStorageState === "LOCKED"
                             ? Colors.magenta : Colors.cyan
                interactive: !personalReadProcess.running
                             && !personalConsentProcess.running
                             && !phoneStorageUnlockProcess.running
                onTriggered: {
                    if (phonePane.phoneStorageState === "LOCKED"
                            || phonePane.phoneStorageState === "UNLOCK_FAILED")
                        phonePane.unlockBlueFerryStorage();
                    else
                        phonePane.loadPersonalSnapshot();
                }
            }
            ActionButton {
                width: Math.max(96, Math.min(150,
                           (personalReadBar.width - 30) / 3))
                height: 31
                label: "STOP ACCESS"
                labelPixelSize: 9
                accentColor: Colors.red
                destructive: true
                onTriggered: phonePane.revokePersonalAccess()
            }
        }
    }

    // This always-visible strip explains *why* a read has not completed.
    // No exception text, SMS content, profile UUIDs or tokens shown here.
    Rectangle {
        id: personalReadFeedback
        anchors.top: personalReadBar.bottom
        anchors.left: phoneContactList.right
        anchors.right: parent.right
        height: visible ? 29 : 0
        visible: phonePane.selectedSection === "MESSAGES"
                 || phonePane.selectedSection === "CONTACTS"
        color: Colors.dark
        border.width: 1
        border.color: phonePane.personalReadStatus === "LOCAL_SNAPSHOT"
                      ? Colors.green : Colors.orange
        z: 7
        Text {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            text: phonePane.personalReadMessage()
            textFormat: Text.PlainText
            color: phonePane.personalReadStatus === "LOCAL_SNAPSHOT"
                   ? Colors.green : Colors.orange
            font.pixelSize: 10
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
    }

    // A genuine on-screen, explicit one-time preference choice.
    // This is NOT an OS camera-style per-app sandbox authorization.
    Rectangle {
        id: personalPermissionOverlay
        anchors.fill: parent
        z: 100
        visible: phonePane.personalPermissionOpen
        color: "#ef090315"
        border.color: Colors.magenta
        border.width: 2
        MouseArea {
            anchors.fill: parent
            onClicked: {} // Block clicks into PHONE while the choice is shown.
        }
        Column {
            anchors.centerIn: parent
            width: Math.max(240, Math.min(420, parent.width - 40))
            spacing: 12

            Text {
                width: parent.width
                text: "PERSONAL IPHONE // READ PERMISSION"
                textFormat: Text.PlainText
                color: Colors.magenta
                font.bold: true
                font.pixelSize: 15
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "Allow Social PHONE to read the selected iPhone's messages and/or contact cards? Your choice is remembered until you select STOP ACCESS. You do not need to approve again each time you open PHONE."
                textFormat: Text.PlainText
                color: Colors.white
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            Text {
                width: parent.width
                text: "PERSONAL LINUX-USER PREFERENCE ONLY. Other apps running as your Linux user may access BlueFerry independently. This does not authenticate an LLC/nonprofit or permit sending messages."
                textFormat: Text.PlainText
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
            ActionButton {
                width: parent.width
                height: 38
                label: "ALLOW BOTH // REMEMBER"
                labelPixelSize: 10
                accentColor: Colors.magenta
                interactive: !personalConsentProcess.running
                onTriggered: phonePane.savePersonalApproval("b")
            }
            ActionButton {
                width: parent.width
                height: 34
                label: "MESSAGES ONLY // REMEMBER"
                labelPixelSize: 9
                accentColor: Colors.cyan
                interactive: !personalConsentProcess.running
                onTriggered: phonePane.savePersonalApproval("m")
            }
            ActionButton {
                width: parent.width
                height: 34
                label: "CONTACTS ONLY // REMEMBER"
                labelPixelSize: 9
                accentColor: Colors.cyan
                interactive: !personalConsentProcess.running
                onTriggered: phonePane.savePersonalApproval("c")
            }
            ActionButton {
                width: parent.width
                height: 34
                label: "NOT NOW"
                labelPixelSize: 10
                accentColor: Colors.orange
                interactive: !personalConsentProcess.running
                onTriggered: phonePane.personalPermissionOpen = false
            }
            Text {
                width: parent.width
                visible: phonePane.personalReadStatus === "STORAGE_UNAVAILABLE"
                         || phonePane.personalReadStatus === "PROVIDER_UNAVAILABLE"
                         || phonePane.personalReadStatus === "DEVICE_UNAVAILABLE"
                         || phonePane.personalReadStatus === "APPROVAL_FAILED"
                text: phonePane.personalReadMessage()
                textFormat: Text.PlainText
                color: Colors.orange
                font.pixelSize: 10
                wrapMode: Text.WordWrap
            }
        }
    }

    ContactList {
        id: phoneContactList
        anchors.top: personalReadBar.bottom
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        width: Math.min(200, Math.max(135, phonePane.width * 0.30))
        visible: phonePane.selectedSection === "MESSAGES"
        conversations: phonePane.selectedSection === "MESSAGES"
                       ? phoneReadAdapter.conversations : []
        keyboardFocused: false
        onContactClicked: {
            if (selectedConversation && phonePane.selectedSection === "MESSAGES")
                phoneReadAdapter.loadMessages(String(selectedConversation.id));
        }
    }

    // Contact cards are address book rows, not fake conversation threads.
    ListView {
        id: phoneAddressBook
        anchors.fill: phoneContactList
        visible: phonePane.selectedSection === "CONTACTS"
        clip: true
        model: phoneReadAdapter.contactCards
        delegate: Rectangle {
            required property var modelData
            width: phoneAddressBook.width
            height: 58
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            Column {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 5
                Text {
                    width: parent.width
                    text: modelData.displayNameInProfile || "Unnamed contact"
                    textFormat: Text.PlainText
                    color: Colors.white
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
                Text {
                    width: parent.width
                    text: modelData.primary || ""
                    textFormat: Text.PlainText
                    color: Colors.cyan
                    font.pixelSize: 9
                    elide: Text.ElideRight
                }
            }
        }
    }

    // No invented people or unapproved phone numbers. The real ContactList
    // remains empty until a different, trusted owner provides scoped data.
    Text {
        id: emptyPhoneContacts
        visible: phonePane.selectedSection === "CONTACTS"
                 ? phoneReadAdapter.contactCards.length === 0
                 : phonePane.selectedSection === "MESSAGES"
                   && phoneReadAdapter.conversations.length === 0
        anchors.top: phoneContactList.top
        anchors.topMargin: 108
        anchors.left: phoneContactList.left
        anchors.right: phoneContactList.right
        anchors.margins: 10
        z: 4
        text: phonePane.selectedSection === "CONTACTS"
              ? (phonePane.personalReadStatus === "LOCAL_SNAPSHOT"
                 ? "NO CONTACT CARDS RETURNED"
                 : "NO PHONE CONTACTS YET")
              : (phonePane.personalReadStatus === "LOCAL_SNAPSHOT"
                 ? "NO CONVERSATIONS RETURNED"
                 : "NO PHONE CHATS YET")
        color: Colors.white
        opacity: 0.8
        font.family: "GohuFont 11 Nerd Font Mono"
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }

    ChatFeed {
        id: phoneChatFeed
        anchors.top: personalReadFeedback.bottom
        anchors.left: phoneContactList.right
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: phonePane.selectedSection === "MESSAGES"
                 || phonePane.selectedSection === "CONTACTS"
        conversation: phonePane.selectedSection === "MESSAGES"
                      ? phoneContactList.selectedConversation : null
        messages: phonePane.selectedSection === "MESSAGES"
                  ? phoneReadAdapter.messages : []
        sendEnabled: false
        emptyConversationLabel: phonePane.selectedSection === "CALLS"
                                ? "PHONE CALLS NOT LINKED"
                                : phonePane.selectedSection === "CONTACTS"
                                ? (phoneReadAdapter.contactCards.length > 0
                                   ? "IPHONE CONTACTS // READ ONLY"
                                   : "PHONE CONTACTS NOT LINKED")
                                : phoneReadAdapter.conversations.length > 0
                                  ? "SELECT A PHONE CONVERSATION"
                                  : "PHONE NOT LINKED"
    }

    // Informative, content-free status on the existing MESSAGES/CONTACTS pane.
    // Never substitute MAP/PBAP presence for authenticated phone data.
    Text {
        id: phoneDataHint
        anchors.top: phoneChatFeed.top
        anchors.topMargin: 93
        anchors.left: phoneChatFeed.left
        anchors.right: phoneChatFeed.right
        anchors.margins: 16
        z: 4
        visible: phonePane.selectedSection === "MESSAGES"
                 ? phoneReadAdapter.conversations.length === 0
                 : phonePane.selectedSection === "CONTACTS"
                   && phoneReadAdapter.contactCards.length === 0
        textFormat: Text.PlainText
        text: phonePane.personalReadStatus === "LOCAL_SNAPSHOT"
              ? "BlueFerry returned an empty snapshot. SMS notifications do not imply saved message history or cached contact cards."
              : phonePane.personalReadStatus === "APPROVAL_REQUIRED"
                ? "Select APPROVE READ. Your choice is remembered for this iPhone until you revoke it."
                : phonePane.personalReadStatus === "NOT_CONSENTED"
                  ? "This tab was not included in your saved approval. Select PERMISSION ON to change it."
                  : phonePane.personalReadMessage() + "\n"
                    + phonePane.contentDiagnosticText(phonePane.selectedSection)
        color: Colors.orange
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
    }

    // CALLS is a real workspace inside the existing PHONE menu, not a
    // separate screen, and never changes the MESSAGES "Contacts" sidebar.
    Rectangle {
        id: phoneCallsWorkspace
        anchors.top: sectionToolbar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        visible: phonePane.selectedSection === "CALLS"
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan
        z: 7

        Flickable {
            anchors.fill: parent
            anchors.margins: 12
            clip: true
            contentWidth: width
            contentHeight: callsColumn.implicitHeight + 20
            flickableDirection: Flickable.VerticalFlick
            boundsBehavior: Flickable.StopAtBounds

            Column {
                id: callsColumn
                width: parent.width
                spacing: 12

                Text {
                    width: parent.width
                    text: "CALLS // IPHONE HANDS-FREE"
                    color: Colors.cyan
                    font.bold: true
                    font.pixelSize: 17
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: phonePane.callsWorkspaceMessage()
                    textFormat: Text.PlainText
                    color: phonePane.callsWorkspaceState === "READY"
                           ? Colors.green : Colors.orange
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
                Row {
                    spacing: 8
                    ActionButton {
                        width: Math.min(160, (callsColumn.width - 8) / 2)
                        height: 34
                        label: phoneCallsStatusProcess.running
                               ? "CHECKING..." : "REFRESH CALLS"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        interactive: !phoneCallsActionProcess.running
                                     && !phoneCallsStatusProcess.running
                        onTriggered: phonePane.refreshCallsWorkspace()
                    }
                    ActionButton {
                        width: Math.min(170, (callsColumn.width - 8) / 2)
                        height: 34
                        label: "DEVICE / HFP SETUP"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        onTriggered: phonePane.startSetup()
                    }
                }
                Text {
                    width: parent.width
                    visible: phonePane.callsWorkspaceState !== "READY"
                    text: "Ordinary cellular calls need BlueFerry Calls1, oFono's active system service, system D-Bus permission and WirePlumber's oFono HFP backend. This does not change your music audio route."
                    textFormat: Text.PlainText
                    color: Colors.white
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    visible: phonePane.callsWorkspaceState === "READY"
                    text: "ACTIVE PHONE CALLS // " + phonePane.liveCalls.length
                    textFormat: Text.PlainText
                    color: Colors.magenta
                    font.pixelSize: 12
                    font.bold: true
                }

                Repeater {
                    model: phonePane.callsWorkspaceState === "READY"
                           ? phonePane.liveCalls : []
                    delegate: Rectangle {
                        required property var modelData
                        width: callsColumn.width
                        height: 108
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan

                        Column {
                            anchors.fill: parent
                            anchors.margins: 8
                            spacing: 7
                            Text {
                                width: parent.width
                                text: modelData.peer
                                textFormat: Text.PlainText
                                color: Colors.white
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                            Text {
                                width: parent.width
                                text: String(modelData.state).toUpperCase()
                                      + " // " + modelData.direction
                                      + (modelData.multiparty ? " // CONFERENCE" : "")
                                textFormat: Text.PlainText
                                color: Colors.orange
                                font.pixelSize: 11
                            }
                            Row {
                                spacing: 8
                                ActionButton {
                                    width: 100
                                    height: 31
                                    visible: modelData.state === "incoming"
                                             || modelData.state === "waiting"
                                    label: "ANSWER"
                                    labelPixelSize: 10
                                    accentColor: Colors.magenta
                                    interactive: !phoneCallsActionProcess.running
                                    onTriggered: phonePane.requestCallAction("answer", modelData.id)
                                }
                                ActionButton {
                                    width: 105
                                    height: 31
                                    visible: modelData.state === "incoming"
                                             || modelData.state === "waiting"
                                    label: "DECLINE"
                                    labelPixelSize: 10
                                    accentColor: Colors.red
                                    destructive: true
                                    interactive: !phoneCallsActionProcess.running
                                    onTriggered: phonePane.requestCallAction("decline", modelData.id)
                                }
                                ActionButton {
                                    width: 105
                                    height: 31
                                    visible: modelData.state === "active"
                                             || modelData.state === "held"
                                             || modelData.state === "dialing"
                                             || modelData.state === "alerting"
                                    label: "HANG UP"
                                    labelPixelSize: 10
                                    accentColor: Colors.red
                                    destructive: true
                                    interactive: !phoneCallsActionProcess.running
                                    onTriggered: phonePane.requestCallAction("hangup", modelData.id)
                                }
                            }
                        }
                    }
                }

                Text {
                    width: parent.width
                    visible: phonePane.callsWorkspaceState === "READY"
                             && phonePane.liveCalls.length === 0
                    text: "No active or incoming cellular calls."
                    color: Colors.white
                    font.pixelSize: 11
                }

                Text {
                    width: parent.width
                    text: "PLACE A CALL // Personal iPhone"
                    color: Colors.cyan
                    font.bold: true
                    font.pixelSize: 12
                }
                Rectangle {
                    width: Math.min(340, callsColumn.width)
                    height: 36
                    border.width: 1
                    border.color: Colors.magenta
                    color: Colors.dark
                    TextInput {
                        id: phoneDialInput
                        anchors.fill: parent
                        anchors.margins: 8
                        color: Colors.magenta
                        selectionColor: Colors.yellow
                        selectedTextColor: Colors.black
                        font.pixelSize: 13
                        maximumLength: 19
                        clip: true
                        cursorDelegate: Rectangle {
                            width: 2
                            height: phoneDialInput.font.pixelSize + 2
                            color: Colors.orange
                        }
                        onTextChanged: {
                            phonePane.callsConfirmDial = false;
                            phonePane.callsPendingDial = "";
                        }
                    }
                    Text {
                        anchors.fill: parent
                        anchors.margins: 8
                        visible: phoneDialInput.text.length === 0
                        text: "Number (digits, optional leading +)"
                        color: Colors.white
                        opacity: 0.55
                        font.pixelSize: 11
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                ActionButton {
                    width: Math.min(200, callsColumn.width)
                    height: 35
                    label: "REVIEW OUTGOING CALL"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    interactive: phonePane.callsWorkspaceState === "READY"
                                 && !phoneCallsActionProcess.running
                    onTriggered: phonePane.preparePhoneDial()
                }
                Rectangle {
                    width: Math.min(380, callsColumn.width)
                    height: 116
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.orange
                    visible: phonePane.callsConfirmDial
                    Column {
                        anchors.fill: parent
                        anchors.margins: 9
                        spacing: 8
                        Text {
                            width: parent.width
                            text: "CALL VIA IPHONE: " + phonePane.callsPendingDial
                            textFormat: Text.PlainText
                            color: Colors.orange
                            font.pixelSize: 12
                            wrapMode: Text.WrapAnywhere
                        }
                        Row {
                            spacing: 8
                            ActionButton {
                                width: 125
                                height: 34
                                label: "CONFIRM CALL"
                                labelPixelSize: 10
                                accentColor: Colors.magenta
                                onTriggered: phonePane.requestCallAction(
                                    "dial", phonePane.callsPendingDial)
                            }
                            ActionButton {
                                width: 110
                                height: 34
                                label: "CANCEL"
                                labelPixelSize: 10
                                accentColor: Colors.red
                                onTriggered: {
                                    phonePane.callsConfirmDial = false;
                                    phonePane.callsPendingDial = "";
                                }
                            }
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: phonePane.canSwapCalls()
                    text: "CALL WAITING // Manage the existing cellular calls."
                    color: Colors.orange
                    font.pixelSize: 11
                }
                ActionButton {
                    width: Math.min(208, callsColumn.width)
                    height: 34
                    visible: phonePane.canSwapCalls()
                    label: "SWAP ACTIVE / HELD"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    interactive: !phoneCallsActionProcess.running
                    onTriggered: phonePane.requestCallAction("swap", "")
                }
                ActionButton {
                    width: Math.min(208, callsColumn.width)
                    height: 34
                    visible: phonePane.canHoldAnswer()
                    label: "HOLD AND ANSWER"
                    labelPixelSize: 9
                    accentColor: Colors.magenta
                    interactive: !phoneCallsActionProcess.running
                    onTriggered: phonePane.requestCallAction("hold-answer", "")
                }

                Text {
                    width: parent.width
                    visible: phonePane.activeCallId().length > 0
                    text: "IN-CALL KEYPAD // DTMF"
                    color: Colors.cyan
                    font.pixelSize: 11
                }
                Rectangle {
                    width: Math.min(240, callsColumn.width)
                    height: visible ? 34 : 0
                    visible: phonePane.activeCallId().length > 0
                    color: Colors.dark
                    border.color: Colors.cyan
                    TextInput {
                        id: callTonesInput
                        anchors.fill: parent
                        anchors.margins: 6
                        color: Colors.magenta
                        font.pixelSize: 12
                        maximumLength: 32
                        cursorDelegate: Rectangle {
                            width: 2
                            height: callTonesInput.font.pixelSize + 2
                            color: Colors.orange
                        }
                    }
                }
                ActionButton {
                    width: 160
                    height: 34
                    visible: phonePane.activeCallId().length > 0
                    label: "SEND TONES"
                    labelPixelSize: 9
                    accentColor: Colors.cyan
                    interactive: !phoneCallsActionProcess.running
                                 && /^[0-9*#]{1,32}$/.test(callTonesInput.text)
                    onTriggered: {
                        var callId = phonePane.activeCallId();
                        if (callId.length > 0)
                            phonePane.requestCallAction(
                                "tones", callId + "\t" + callTonesInput.text);
                        callTonesInput.text = "";
                    }
                }

                Text {
                    width: parent.width
                    visible: phonePane.callsActionMessage().length > 0
                    text: phonePane.callsActionMessage()
                    textFormat: Text.PlainText
                    color: Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    text: "FaceTime, decline-with-text, starting conferences and call transfer are NOT supported by this cellular HFP control. Use your iPhone for emergency calls. No call audio routing or system service changes happen in this pane."
                    textFormat: Text.PlainText
                    color: Colors.orange
                    font.pixelSize: 10
                    wrapMode: Text.WordWrap
                }
            }
        }
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
                visible: !(phonePane.stageWanted && phonePane.stagePurpose === "OFONO")
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
                width: Math.min(150, Math.max(90, (parent.width - 24) / 2))
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

            ActionButton {
                id: stagedFocusAction
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: Math.min(150, Math.max(90, (parent.width - 24) / 2))
                height: 32
                visible: phonePane.stageWanted && phonePane.stagePurpose === "OFONO"
                         && phonePane.stageState === "ALIGNED"
                label: "FOCUS TERMINAL"
                labelPixelSize: 9
                accentColor: Colors.cyan
                onTriggered: phonePane.focusStagedInstaller()
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

                // Local nickname management never changes pairing, audio,
                // BlueFerry's selected profile or Social authorization.
                Column {
                    id: phoneNicknameManager
                    width: setupColumn.width
                    spacing: 8
                    visible: phonePane.deviceObservationCheck === "CHECKED"
                             && (phonePane.deviceObservation.state === "BLUETOOTH_CONNECTED"
                                 || phonePane.deviceObservation.state === "PAIRED_OFFLINE")
                             && !phonePane.stageWanted

                    Text {
                        width: parent.width
                        textFormat: Text.PlainText
                        text: "PERSONAL DEVICE LABEL // "
                              + (phonePane.phoneNicknameCheck === "CHECKING"
                                 ? "CHECKING"
                                 : phonePane.phoneNicknameCheck === "CHECKED"
                                   && phonePane.phoneNickname.state === "PRESENT"
                                 ? phonePane.phoneNickname.nickname
                                 : "NOT SET")
                        color: Colors.magenta
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    ActionButton {
                        id: managePhoneNickname
                        width: Math.min(208, phoneNicknameManager.width)
                        height: 34
                        label: phonePane.nicknameEditorOpen ? "CLOSE NAME EDITOR"
                                                            : "MANAGE PHONE NAME"
                        labelPixelSize: 9
                        accentColor: Colors.cyan
                        interactive: !nicknameReadProcess.running
                                     && !nicknameWriteProcess.running
                        onTriggered: {
                            phonePane.nicknameEditorOpen = !phonePane.nicknameEditorOpen;
                            if (phonePane.nicknameEditorOpen) {
                                phoneNicknameInput.text =
                                    phonePane.phoneNicknameCheck === "CHECKED"
                                    && phonePane.phoneNickname.state === "PRESENT"
                                    ? phonePane.phoneNickname.nickname : "";
                                phonePane.nicknameActionStatus = "IDLE";
                            }
                        }
                    }

                    Column {
                        width: phoneNicknameManager.width
                        spacing: 8
                        visible: phonePane.nicknameEditorOpen

                        Text {
                            width: parent.width
                            text: "Rename this iPhone in Social only. Bluetooth name, pairing and audio stay unchanged."
                            color: Colors.white
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            width: parent.width
                            height: 36
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.magenta
                            clip: true

                            TextInput {
                                id: phoneNicknameInput
                                anchors.fill: parent
                                anchors.margins: 8
                                color: Colors.magenta
                                selectionColor: Colors.yellow
                                selectedTextColor: Colors.black
                                font.pixelSize: 12
                                maximumLength: 40
                                clip: true
                                cursorDelegate: Rectangle {
                                    width: 2
                                    height: phoneNicknameInput.font.pixelSize + 2
                                    color: Colors.orange
                                }
                            }

                            Text {
                                anchors.fill: phoneNicknameInput
                                visible: phoneNicknameInput.text.length === 0
                                         && !phoneNicknameInput.activeFocus
                                text: "Personal iPhone label"
                                color: Colors.white
                                opacity: 0.58
                                font.pixelSize: 12
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Row {
                            width: parent.width
                            spacing: 8

                            ActionButton {
                                width: Math.max(78, (phoneNicknameManager.width - 8) / 2)
                                height: 34
                                label: "SAVE NAME"
                                labelPixelSize: 9
                                accentColor: Colors.green
                                interactive: !nicknameReadProcess.running
                                             && !nicknameWriteProcess.running
                                onTriggered: phonePane.changePhoneNickname("save")
                            }

                            ActionButton {
                                width: Math.max(78, (phoneNicknameManager.width - 8) / 2)
                                height: 34
                                visible: phonePane.phoneNicknameCheck === "CHECKED"
                                         && phonePane.phoneNickname.state === "PRESENT"
                                label: "CLEAR NAME"
                                labelPixelSize: 9
                                destructive: true
                                accentColor: Colors.red
                                interactive: !nicknameReadProcess.running
                                             && !nicknameWriteProcess.running
                                onTriggered: phonePane.changePhoneNickname("clear")
                            }
                        }

                        Text {
                            width: parent.width
                            text: phonePane.nicknameActionStatus === "SAVED"
                                  ? "Local phone label saved."
                                  : phonePane.nicknameActionStatus === "CLEARED"
                                  ? "Local phone label cleared. iPhone pairing remains."
                                  : phonePane.nicknameActionStatus === "INVALID_NICKNAME"
                                  ? "Use a printable name of 1 to 40 characters."
                                  : phonePane.nicknameActionStatus === "NOT_CONFIRMED"
                                  ? "Could not confirm the local label change."
                                  : "PERSONAL DISPLAY ONLY // Not an account, company or phone-content permission."
                            color: Colors.orange
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                        }
                    }
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

                Text {
                    width: parent.width
                    textFormat: Text.PlainText
                    visible: phonePane.setupState === "CHECKED"
                    text: "IPHONE MESSAGE DATA // "
                          + phonePane.contentDiagnosticText("MESSAGES")
                          + "\n\nIPHONE CONTACT DATA // "
                          + phonePane.contentDiagnosticText("CONTACTS")
                    color: Colors.orange
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    lineHeight: 1.3
                }

                // Show the actual BlueFerry history keyring state here,
                // not just Bluetooth MAP/PBAP session health.
                Column {
                    id: phoneStorageSettings
                    width: setupColumn.width
                    spacing: 8
                    visible: phonePane.setupState === "CHECKED"
                             && !phonePane.stageWanted

                    Text {
                        width: parent.width
                        text: "BLUEFERRY LOCAL DATA // " + phonePane.phoneStorageState
                        textFormat: Text.PlainText
                        color: phonePane.phoneStorageState === "READY"
                               ? Colors.green : Colors.orange
                        font.pixelSize: 12
                        font.bold: true
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        width: parent.width
                        text: phonePane.phoneStorageMessage()
                              + "\nThis is BlueFerry's encrypted history and contacts cache, separate from phone Bluetooth pairing and Social permission."
                        textFormat: Text.PlainText
                        color: Colors.white
                        font.pixelSize: 11
                        wrapMode: Text.WordWrap
                    }
                    ActionButton {
                        width: Math.min(208, phoneStorageSettings.width)
                        height: 34
                        visible: phonePane.phoneStorageState === "LOCKED"
                                 || phonePane.phoneStorageState === "UNLOCK_FAILED"
                        label: phonePane.phoneStorageState === "UNLOCK_FAILED"
                               ? "RETRY UNLOCK LOCAL DATA" : "UNLOCK LOCAL DATA"
                        labelPixelSize: 9
                        accentColor: Colors.magenta
                        interactive: !phoneStorageUnlockProcess.running
                        onTriggered: phonePane.unlockBlueFerryStorage()
                    }
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
                                     || phonePane.callPrerequisiteReport.state === "SERVICE_STOPPED"
                                     || phonePane.callPrerequisiteReport.state === "AUDIO_PATH_UNVERIFIED"
                                     || phonePane.callSetupStatus === "FOLLOWUP_REQUIRED"
                                     || phonePane.callSetupStatus === "READY_TO_CONTINUE")
                        label: phonePane.callSetupStatus === "GUI_OPEN_REQUESTED"
                               || phonePane.callSetupStatus === "FOLLOWUP_REQUIRED"
                               ? "CHECK AGAIN"
                               : phonePane.callSetupStatus === "INSTALL_NOT_CONFIRMED"
                                 ? "RETRY SETUP"
                                 : phonePane.callPrerequisiteReport.state === "PACKAGE_NOT_INSTALLED"
                                   ? "SET UP CALLING" : "FINISH CALLING SETUP"
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
                        text: "Only oFono. Review and confirm the Fedora package transaction inside PHONE. Social never approves it automatically. Silverblue stages a new deployment; reboot is a separate action, never automatic."
                        color: Colors.white
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        width: parent.width
                        visible: installCallingSupport.visible
                                 && phonePane.callPrerequisiteReport.state !== "PACKAGE_NOT_INSTALLED"
                        text: "For an installed oFono service on systemd + WirePlumber 0.5+, review each step in the PHONE terminal. Setup never silently starts a service, overwrites HFP settings or enables calls. Other Linux package managers need their own installer."
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
                             ? "CALLING SETUP // TERMINAL BELOW"
                             : "BLUEFERRY SETUP // TERMINAL BELOW")
                          : phonePane.stageState === "FINISHED"
                          ? "Terminal closed. Checking the latest provider and package status..."
                          : phonePane.stageState === "UNAVAILABLE"
                          ? "Stage placement could not be verified. The terminal may remain external; no phone or audio change was made by Social."
                          : phonePane.stagePurpose === "OFONO"
                          ? "Placing the calling setup terminal inside PHONE. Review each change and approve it separately."
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
