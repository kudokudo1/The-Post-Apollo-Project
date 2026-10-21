import Quickshell
import QtQuick
import Quickshell.Io
import Quickshell.Wayland

import "modules"
import "components"

import "widgets"
import "widgets/messanger"
import "widgets/weather"
import "widgets/notifications"

import "services/weather"
import "services/system"
import qs.services.notifications

import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: shellRoot

    // This shell is developed by multiple concurrent writers. Quickshell's
    // automatic file watcher can reload partially-updated QML graphs while
    // shader-backed items are being detached, which has repeatedly crashed
    // QtQuick in QQuickShaderEffectSource::itemChange() on Qt 6.11.
    //
    // Keep the live shell stable while files change. Apply updates with an
    // explicit process restart instead of in-process hot reload.
    Component.onCompleted: {
        Quickshell.watchFiles = false;
    }

    // Nurse 3c // opt-in only. A missed QML Timer deadline reveals that the
    // main event loop could not process this timer promptly; it is NOT a
    // function profiler and does not attribute the cause of the delay.
    // Keep this lightweight, dormant by default, and independent of focus.
    readonly property bool syntagmaLagProbeEnabled:
        String(Quickshell.env("POST_APOLLO_UI_LAG_PROBE") || "").trim() === "1"
    // Diagnostic correlation only: never drives widget state or focus.
    property double syntagmaHospitalLastModeChangeMs: 0

    Timer {
        id: syntagmaEventLoopProbe
        interval: 100
        repeat: true
        running: shellRoot.syntagmaLagProbeEnabled
        property double previousTickMs: 0

        onRunningChanged: {
            if (running)
                previousTickMs = Date.now();
        }

        onTriggered: {
            const now = Date.now();
            const elapsed = now - previousTickMs;
            previousTickMs = now;

            if (elapsed >= 350) {
                const modeAgeMs = shellRoot.syntagmaHospitalLastModeChangeMs > 0
                                  ? now - shellRoot.syntagmaHospitalLastModeChangeMs : -1;
                console.warn(
                    "SYNTAGMA_LAG_PROBE // event-loop interval "
                    + elapsed + "ms (target 100ms)"
                    + " // git=" + gitWindow.menuOpen
                    + " hospital=" + hospitalWindow.menuOpen
                    + " notifications=" + notificationsHubWindow.menuOpen
                    + " tsMs=" + now
                    + " hospitalMode=" + (hospitalWindow.operationsSurface || "surgery")
                    + " hospitalModeAgeMs=" + modeAgeMs
                );
            }
        }
    }

    function reportSyntagmaToggleTime(widgetName, startMs, nowOpen) {
        if (!syntagmaLagProbeEnabled)
            return;

        console.warn(
            "SYNTAGMA_LAG_PROBE // " + widgetName
            + " dock toggle synchronous=" + (Date.now() - startMs)
            + "ms // nowOpen=" + nowOpen
        );
    }

    // Opt-in, in-process diagnostic only. Disabled by default. Only
    // navigation key codes and Qt focus-state metadata are logged, never text.
    property bool focusKeyTraceEnabled: false

    IpcHandler {
        target: "focusKeyTrace"

        function start(): void {
            shellRoot.focusKeyTraceEnabled = true;
        }

        function stop(): void {
            shellRoot.focusKeyTraceEnabled = false;
        }

        function status(): bool {
            return shellRoot.focusKeyTraceEnabled;
        }
    }

    // Single ownership coordinator for the initial Git/Hospital pilot.
    // Existing property readers remain compatible with the shared owner.
    KeyboardOwnershipCoordinator {
        id: keyboardOwnership

        // Opt-in read-only trace: logical owner changes and temporary
        // Exclusive acquisition start/end can be correlated with actual
        // Git/Hospital Shortcut activation in the same Quickshell log.
        onOwnerChanged: {
            if (shellRoot.focusKeyTraceEnabled)
                console.warn("FOCUS_KEY_TRACE // coordinator // owner-changed"
                             + " tsMs=" + Date.now()
                             + " owner=" + owner
                             + " boost=" + boostOwner);
        }
        onBoostOwnerChanged: {
            if (shellRoot.focusKeyTraceEnabled)
                console.warn("FOCUS_KEY_TRACE // coordinator // boost-changed"
                             + " tsMs=" + Date.now()
                             + " owner=" + owner
                             + " boost=" + boostOwner);
        }
    }
    property alias controlKeyboardOwner: keyboardOwnership.owner

    function requestControlKeyboard(id, reason) {
        // Koinoikos selection and ordinary menu ownership cannot diverge:
        // a pointer-entry/open request in that mode must update both.
        if (relationshipFocus.active && relationshipFocus.owner !== id)
            relationshipFocus.selectOwner(id);
        return keyboardOwnership.claim(id, reason);
    }

    function swapControlKeyboardOwner() {
        if (!hospitalWindow.menuOpen || !gitWindow.menuOpen)
            return;

        shellRoot.requestControlKeyboard(
            controlKeyboardOwner === "hospital" ? "git" : "hospital",
            "ctrl-tab"
        );
    }

    // Sway owns Koinoikos directional navigation, Quickshell owns the
    // focusable layer-shell menu registry and the selected menu keyboard.
    RelationshipFocusBroker {
        id: relationshipFocus
        appControl: appControlWindow
        hospital: hospitalWindow
        git: gitWindow
        cpu: cpuPlusWindow
        weather: weatherStationWindow
        notifications: notificationsHubWindow
        hostOwner: shellRoot.controlKeyboardOwner
        boostOwner: keyboardOwnership.boostOwner

        onOwnerChanged: {
            // Koinoikos selection and the shared logical keyboard owner must
            // agree for EVERY registered widget. The coordinator grants an
            // Exclusive pulse only to the adapters that already use it.
            if (active && owner !== "")
                keyboardOwnership.claim(owner, "koinoikos");
        }

        onPreviousOwnerRestorationRequested: function(previous) {
            // The previous shared owner is remembered without forcing
            // another compositor steal when the held gesture ends.
            if (previous === "hospital" && hospitalWindow.menuOpen)
                shellRoot.controlKeyboardOwner = "hospital";
            else if (previous === "git" && gitWindow.menuOpen)
                shellRoot.controlKeyboardOwner = "git";
            else if (previous === "notifications" && notificationsHubWindow.menuOpen)
                shellRoot.controlKeyboardOwner = "notifications";
        }
    }

    screen: Quickshell.screens.find(s => s.name === "DP-5")

    anchors {
        top: true
        bottom: false
        left: true
        right: true
    }

    margins {
        left: 50
        right: 50
        bottom: 3
    }

    // ===== BAR ==================================================

    WlrLayershell.layer: WlrLayer.Bottom

    implicitHeight: 70

    color: "transparent"

    Shortcut {
        sequence: "Ctrl+Tab"
        context: Qt.ApplicationShortcut
        enabled: !relationshipFocus.active
                 && hospitalWindow.menuOpen && gitWindow.menuOpen
        onActivated: shellRoot.swapControlKeyboardOwner()
    }

    // Sway owns the global Mod4 keystrokes; these IPC functions route them
    // into the exact same toggle functions used by the taskbar buttons.
    IpcHandler {
        target: "controlMenus"

        function git(): void {
            gitWindow.toggle();
        }

        function hospital(): void {
            hospitalWindow.toggle();
        }
    }

    // ===== SERVICES =============================================

    WeatherService {
        id: weatherService
    }

    // Official NWS alerts only when an operator-pinned geographic point exists.
    NwsOfficialAlertNotificationProducer {}

    // Observe existing AQI readings without touching Weather Station fetching.
    WeatherAqiNotificationProducer {
        weatherService: weatherService
    }

    // Daily current-conditions brief from existing weather readings only.
    WeatherReportNotificationProducer {
        weatherService: weatherService
    }

    SpaceService {
        id: spaceService
    }

    // Daily observational brief from the same Space data as Weather Station.
    SolarReportNotificationProducer {
        spaceService: spaceService
    }

    // Storm transitions from the SAME NOAA Kp observations, not new polling.
    SolarStormNotificationProducer {
        spaceService: spaceService
    }

    // One session-wide hardware state. AppControl and CPU++ consume these
    // same instances instead of starting independent telemetry/control stacks.
    SystemTelemetry {
        id: sharedSystemTelemetry

        onFanRowsChanged: {
            sharedFanControl.reconcilePendingPercent(fanRows);
        }
    }

    // Hardware-limit warnings reuse CPU++ / AppControl's existing samples.
    CpuPlusThermalNotificationProducer {
        telemetry: sharedSystemTelemetry
    }

    // Read-only fan tachometer alerts gated by reported hwmon minimums.
    CpuPlusFanHealthNotificationProducer {
        telemetry: sharedSystemTelemetry
    }

    // Informational SYSTEM report from the same existing sample stream.
    CpuPlusSystemNotificationProducer {
        telemetry: sharedSystemTelemetry
    }

    // Sustained RAM/root-filesystem pressure from the SAME existing samples.
    ResourcePressureNotificationProducer {
        telemetry: sharedSystemTelemetry
    }

    // Monitor health uses actual completed CPU++ observations, not optimistic
    // errorText clearing at the start of a refresh.
    CpuPlusTelemetryHealthNotificationProducer {
        telemetry: sharedSystemTelemetry
    }

    // Notifications storage outcomes observe its existing FileView statuses;
    // there is no second persistence backend.
    NotificationsPersistenceHealthProducer {}

    FanControl {
        id: sharedFanControl

        onRefreshRequested: sharedSystemTelemetry.refresh()

        onErrorRaised: function(message) {
            sharedSystemTelemetry.errorText = String(message || "");
        }
    }

    // ===== BAR DECORATION =======================================

    Rectangle {
        anchors.centerIn: parent

        width: parent.width
        height: 50

        opacity: 0.1

        color: "transparent"
    }

    Rectangle {
        id: cyanLine

        anchors.centerIn: parent

        width: parent.width
        height: 2

        color: Colors.cyan
    }

    DropShadow {
        anchors.fill: cyanLine

        source: cyanLine

        horizontalOffset: 0
        verticalOffset: 0

        radius: 18
        samples: 37

        color: "transparent"
    }

    Rectangle {
        anchors.centerIn: parent

        width: 4
        height: 20

        opacity: 0.7

        color: Colors.cyan
    }

    // ===== LEFT MODULES =========================================

    Row {
        id: leftModules

        anchors {
            top: parent.top
            left: parent.left
        }

        anchors.topMargin: 8
        anchors.leftMargin: 5

        spacing: 25

        // App Launcher

        Item {
            width: appLauncherButton.implicitWidth
            height: appLauncherButton.implicitHeight

            Applauncher {
                id: appLauncherButton

                anchors.fill: parent

                appControlWindow: appControlWindow
            }

            AppControlW {
                id: appControlWindow

                systemTelemetry: sharedSystemTelemetry
                fanControl: sharedFanControl
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "appcontrol"
            }
        }

        // Workspaces

        Workspaces {}

        // Tray

        Tray {}

        // Mediaplayer

        Mediaplayer {}

        // Finance

        Item {
            id: financeHost
            width: financeButton.implicitWidth
            height: financeButton.implicitHeight

            Finance {
                id: financeButton
                anchors.fill: parent
                menuOpen: financeWindow.menuOpen
                onToggleRequested: financeWindow.toggle()
            }

            FinanceW {
                id: financeWindow
                screen: shellRoot.screen

                // Align the portrait panel's center beneath this dock item,
                // including the bar's actual left margin and Row position.
                dockCenterX: shellRoot.margins.left + leftModules.x
                             + financeHost.x + financeButton.width / 2
                dockBottomY: shellRoot.margins.top + leftModules.y
                             + financeHost.y + financeButton.height
            }
        }

        // Hospital

        Item {
            width: hospitalButton.implicitWidth
            height: hospitalButton.implicitHeight

            Hospital {
                id: hospitalButton

                anchors.fill: parent

                menuOpen: hospitalWindow.menuOpen

                onToggleRequested: {
                    const startMs = shellRoot.syntagmaLagProbeEnabled
                                    ? Date.now() : 0;
                    hospitalWindow.toggle();
                    shellRoot.reportSyntagmaToggleTime(
                        "hospital", startMs, hospitalWindow.menuOpen
                    );
                }
            }

            HospitalW {
                id: hospitalWindow
                focusKeyTraceEnabled: shellRoot.focusKeyTraceEnabled

                screen: Quickshell.screens.find(s => s.name === "DP-5")
                keyboardActive: relationshipFocus.active
                                ? relationshipFocus.owner === "hospital"
                                : shellRoot.controlKeyboardOwner === "hospital"
                // Even with both menus open, no indefinite Exclusive.
                // Exclusive is only the coordinator's bounded acquisition.
                keyboardLock: keyboardOwnership.boostOwner === "hospital"
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "hospital"

                onKeyboardOwnershipRequested:
                    shellRoot.requestControlKeyboard("hospital", "pointer")

                onGithubPullRequestRequested: function(repository, number) {
                    gitWindow.openGithubPullRequest(
                        repository,
                        number
                    );
                    shellRoot.requestControlKeyboard("git", "cross-widget");
                }

                // Operator-enabled lag correlation: observe the existing
                // Hospital view signal without altering or delaying its work.
                onOperationsSurfaceChanged: {
                    if (shellRoot.syntagmaLagProbeEnabled) {
                        const now = Date.now();
                        shellRoot.syntagmaHospitalLastModeChangeMs = now;
                        console.warn("SYNTAGMA_LAG_PROBE // hospital mode-change"
                                     + " tsMs=" + now
                                     + " to=" + (operationsSurface || "surgery")
                                     + " open=" + menuOpen);
                    }
                }

                onMenuOpenChanged: {
                    if (menuOpen)
                        shellRoot.requestControlKeyboard("hospital", "open");
                    else
                        keyboardOwnership.release("hospital");
                }
            }
        }

        // Git

        Item {
            width: gitButton.implicitWidth
            height: gitButton.implicitHeight

            Git {
                id: gitButton

                anchors.fill: parent

                menuOpen: gitWindow.menuOpen

                onToggleRequested: {
                    const startMs = shellRoot.syntagmaLagProbeEnabled
                                    ? Date.now() : 0;
                    gitWindow.toggle();
                    shellRoot.reportSyntagmaToggleTime(
                        "git", startMs, gitWindow.menuOpen
                    );
                }
            }

            GitW {
                id: gitWindow
                focusKeyTraceEnabled: shellRoot.focusKeyTraceEnabled

                screen: Quickshell.screens.find(s => s.name === "DP-5")
                keyboardActive: relationshipFocus.active
                                ? relationshipFocus.owner === "git"
                                : shellRoot.controlKeyboardOwner === "git"
                keyboardLock: keyboardOwnership.boostOwner === "git"
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "git"

                onKeyboardOwnershipRequested:
                    shellRoot.requestControlKeyboard("git", "pointer")

                onMenuOpenChanged: {
                    if (menuOpen)
                        shellRoot.requestControlKeyboard("git", "open");
                    else
                        keyboardOwnership.release("git");
                }
            }
        }
    }

    // ===== CENTER MODULE ========================================

    Calendar {
        id: calendarModule

        anchors {
            top: parent.top
            horizontalCenter: parent.horizontalCenter
        }

        anchors.topMargin: 8
    }

    // ===== RIGHT MODULES ========================================

    Row {
        id: rightModules

        anchors {
            top: parent.top
            right: parent.right
        }

        anchors.topMargin: 8
        anchors.rightMargin: 5

        spacing: 8

        // Network

        Network {}

        // Bluetooth

        Bluetooth {}

        // CPU

        Item {
            width: cpuButton.implicitWidth
            height: cpuButton.implicitHeight

            Cpu {
                id: cpuButton
                anchors.fill: parent

                cpuPlusWindow: cpuPlusWindow
                systemTelemetry: sharedSystemTelemetry
                fanControl: sharedFanControl
            }

            CpuPlusW {
                id: cpuPlusWindow

                screen: Quickshell.screens.find(s => s.name === "DP-5")

                appControlWindow: appControlWindow
                systemTelemetry: sharedSystemTelemetry
                fanControl: sharedFanControl
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "cpu"
            }
        }

        // Weather

        Item {
            width: weatherButton.implicitWidth
            height: weatherButton.implicitHeight

            Weather {
                id: weatherButton

                anchors.fill: parent

                weatherStationWindow: weatherStationWindow
            }

            WeatherStationW {
                id: weatherStationWindow

                screen: Quickshell.screens.find(s => s.name === "DP-5")

                weatherService: weatherService
                spaceService: spaceService
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "weather"
            }
        }

        // Volume

        Volumebar {}

        // Messaging

        Item {
            width: sessionsButton.implicitWidth
            height: sessionsButton.implicitHeight

            Sessions {
                id: sessionsButton

                anchors.fill: parent

                messagingWindow: messagingWindow
            }

            MessagingW {
                id: messagingWindow

                anchors {
                    top: true
                    bottom: false
                    left: false
                    right: true
                }

                margins {
                    top: 0
                    left: 100
                    right: 13
                }
            }
        }

        // Clock

        Clock {}

        // Notifications

        Item {
            width: notificationsHubButton.implicitWidth
            height: notificationsHubButton.implicitHeight

            NotificationsHub {
                id: notificationsHubButton

                anchors.fill: parent

                menuOpen: notificationsHubWindow.menuOpen

                onToggleRequested: {
                    notificationsHubWindow.toggle();
                }
            }

            // Incoming notification popup

            Notifications {}

            // Notification history / control hub

            NotificationsHubW {
                id: notificationsHubWindow

                screen: Quickshell.screens.find(s => s.name === "DP-5")
                keyboardActive: relationshipFocus.active
                                ? relationshipFocus.owner === "notifications"
                                : shellRoot.controlKeyboardOwner === "notifications"
                keyboardLock: keyboardOwnership.boostOwner === "notifications"
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "notifications"

                onKeyboardOwnershipRequested:
                    shellRoot.requestControlKeyboard("notifications", "pointer")

                onMenuOpenChanged: {
                    if (menuOpen)
                        shellRoot.requestControlKeyboard("notifications", "open");
                    else
                        keyboardOwnership.release("notifications");
                }
            }
        }
    }

    // ===== POWER ================================================

    Power {}
}
