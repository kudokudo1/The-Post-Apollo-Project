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
import qs.services.hub
import "services/hub/ApolloHubProcessesPolicy.js" as HubProcessesPolicy
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

    // Apollo notification destinations are delivered within this already-
    // running shell to existing widget instances. Never launch another
    // Quickshell process or mutate the active Hospital Room/Patient.
    function openApolloNotificationRoute(destination) {
        const route = destination || {};
        const widget = String(route.widget || "");
        if (widget === "cpu") {
            if (!cpuPlusWindow.menuOpen)
                cpuPlusWindow.open();
            if (route.mode === "thermal") {
                cpuPlusWindow.selectMode(2);
                cpuPlusWindow.selectThermalSubMode(route.subMode === "fan" ? 1 : 0);
            } else if (route.mode === "system") {
                cpuPlusWindow.selectMode(3);
                cpuPlusWindow.selectSystemSubMode(String(route.subMode || "ALL"));
            } else {
                return false;
            }
            shellRoot.requestControlKeyboard("cpu", "notification-route");
            return true;
        }
        if (widget === "weather") {
            const view = String(route.view || "");
            const index = weatherStationWindow.mainModes.findIndex(
                function(item) { return item.id === view; });
            if (index < 0)
                return false;
            weatherStationWindow.open();
            weatherStationWindow.currentView = view;
            weatherStationWindow.navigationIndex = index;
            shellRoot.requestControlKeyboard("weather", "notification-route");
            return true;
        }
        if (widget === "hospital") {
            if (!hospitalWindow.menuOpen)
                hospitalWindow.open();
            if (route.view === "reports")
                hospitalWindow.openReports(String(route.team || ""));
            else if (route.view === "reception")
                hospitalWindow.openReception();
            else
                return false;
            shellRoot.requestControlKeyboard("hospital", "notification-route");
            return true;
        }
        if (widget === "git") {
            if (route.view === "pull") {
                if (!gitWindow.openGithubPullRequest(
                        String(route.repository || ""), Number(route.number || 0)))
                    return false;
            } else {
                if (!gitWindow.menuOpen)
                    gitWindow.open();
                if (route.view === "operations") {
                    gitWindow.showGitPage();
                    gitWindow.showGitOperations();
                } else if (route.view === "issues") {
                    gitWindow.showGithubPage();
                    gitWindow.showGithubIssues();
                } else if (route.view === "github") {
                    gitWindow.showGithubPage();
                    gitWindow.showGithubControl();
                } else {
                    return false;
                }
            }
            shellRoot.requestControlKeyboard("git", "notification-route");
            return true;
        }
        if (widget === "notifications" && route.view === "system") {
            notificationsHubWindow.open();
            notificationsHubWindow.activeFilter = "system";
            shellRoot.requestControlKeyboard("notifications", "notification-route");
            return true;
        }
        console.warn("Notification destination unavailable:", widget);
        return false;
    }

    Connections {
        target: NotificationsService
        function onApolloNavigationRequested(destination) {
            shellRoot.openApolloNotificationRoute(destination);
        }
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
        finance: financeWindow
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
            else if (previous === "finance" && financeWindow.menuOpen)
                shellRoot.controlKeyboardOwner = "finance";
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

    // ApolloHub reads the same live WeatherService as Weather Station.
    // This bridge is read-only and starts no additional weather fetches.
    ApolloHubLiveBridge {
        id: apolloHubLive
        weatherSource: weatherService
        // Share Network dock's live iw reading; no new speed observer.
        networkDockSource: sharedNetworkDock
        // B2: same singleton already used by CPU++ and AppControl.
        systemSource: sharedSystemTelemetry
        // B4: consume the ONE Media Dock's existing controller/selection.
        // Both references are read by the bridge; it never commands playback.
        mediaControllerSource: sharedMediaDock.hubMediaController
        selectedMprisBusName: sharedMediaDock.hubSelectedMprisBusName
        // Feed the already-running dock's 2s MPD observation: no new poller.
        mpdDockSource: sharedMediaDock
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

    // Read-only Silverblue/Git update offers. Actions are gated by an
    // explicit reviewer terminal; never authorize a background OS update.
    SoftwareUpdateOfferNotificationProducer {
        id: softwareUpdateOffers
    }

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

        // Match the established right-module spacing. The App Control →
        // Workspaces gap alone keeps its original 25px separation.
        spacing: 8

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

        // Reserve the former 25px App Control → Workspaces separation:
        // 8px Row gap + 9px spacer + 8px Row gap.
        Item {
            id: appControlWorkspaceGap
            width: 9
            height: 1
        }

        // Workspaces

        Workspaces {}

        // Mediaplayer

        Mediaplayer {
            id: sharedMediaDock
        }

        // Tray

        Tray {}

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
                // Reuse the Notifications window's compositor-owned geometry.
                notificationsReference: notificationsHubWindow
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
                keyboardActive: relationshipFocus.active
                                ? relationshipFocus.owner === "finance"
                                : shellRoot.controlKeyboardOwner === "finance"
                keyboardLock: keyboardOwnership.boostOwner === "finance"
                relationshipFocusModeActive: relationshipFocus.active
                relationshipFocused: relationshipFocus.owner === "finance"

                onKeyboardOwnershipRequested:
                    shellRoot.requestControlKeyboard("finance", "pointer")

                onMenuOpenChanged: {
                    if (menuOpen)
                        shellRoot.requestControlKeyboard("finance", "open");
                    else
                        keyboardOwnership.release("finance");
                }

                // Center under Finance horizontally; align its top with
                // Hospital/Git's top chassis line vertically.
                dockCenterX: shellRoot.margins.left + leftModules.x
                             + financeHost.x + financeButton.width / 2
                chassisTopY: hospitalWindow.panelTopMargin
                             + hospitalWindow.topGlowGutter
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

        // Tasks

        Item {
            id: tasksHost
            width: tasksButton.implicitWidth
            height: tasksButton.implicitHeight

            Tasks {
                id: tasksButton
                anchors.fill: parent
                menuOpen: tasksWindow.menuOpen
                onToggleRequested: tasksWindow.toggle()
            }

            TasksW {
                id: tasksWindow
                screen: shellRoot.screen
                dockCenterX: shellRoot.margins.left + leftModules.x
                             + tasksHost.x + tasksButton.width / 2
                chassisTopY: hospitalWindow.panelTopMargin
                             + hospitalWindow.topGlowGutter

                // Navigation only. GitW owns its GitHub service and decides
                // when to READ the remote project list; TASKS never receives
                // GitHub credentials or permission to mutate remote state.
                onOpenGithubProjectsRequested: {
                    tasksWindow.menuOpen = false;
                    if (!gitWindow.menuOpen)
                        gitWindow.open();
                    gitWindow.showGithubPage();
                    gitWindow.showGithubProjects();
                    shellRoot.requestControlKeyboard("git", "cross-widget");
                }
            }
        }
    }

    // ===== CENTER MODULE ========================================

    // ApolloHubW replaces the passive Calendar dock, keeping the center
    // anchor. The focus broker/coordinator are shared-owned seams; this
    // bounded pilot uses window-local keys and OnDemand only.
    Item {
        id: apolloHubHost
        width: apolloHubButton.implicitWidth
        height: apolloHubButton.implicitHeight

        // One on-demand request when the Hub shows a CPU tile.
        // SystemTelemetry.refresh() already refuses overlapping sampling.
        // No polling loop, separate collector, or mutation rights.
        function refreshCpuTileWhenVisible() {
            if (!apolloHubWindow.menuOpen)
                return;
            const tiles = apolloHubWindow.activeTiles;
            if (!Array.isArray(tiles)
                    || !tiles.some(function(tile) {
                        return tile && tile.module === "cpu";
                    }))
                return;
            sharedSystemTelemetry.refresh();
        }

        Connections {
            target: apolloHubWindow
            function onMenuOpenChanged() {
                apolloHubHost.refreshCpuTileWhenVisible();
            }
            function onActiveTilesChanged() {
                apolloHubHost.refreshCpuTileWhenVisible();
            }
        }

        anchors {
            top: parent.top
            horizontalCenter: parent.horizontalCenter
        }
        anchors.topMargin: 8

        ApolloHub {
            id: apolloHubButton
            anchors.fill: parent
            menuOpen: apolloHubWindow.menuOpen
            onToggleRequested: apolloHubWindow.toggle()
        }

        ApolloHubW {
            id: apolloHubWindow
            screen: shellRoot.screen
            liveBridge: apolloHubLive
            // Owner windows retain the controller, subprocesses and Sway
            // geometry. Hub receives only a tiny state projection and
            // explicit typed action routing at direct button presses.
            appControlAvailable: appControlWindow !== null
            processActionGate: appControlWindow
                               ? appControlWindow.hubProcessActionGate : null
            // The existing AppControl sampler runs with its own cadence.
            // Clone only bounded display fields, no argv, user, command or
            // mutation handles and no new ProcessTelemetry instance.
            processSnapshot: appControlWindow
                             ? HubProcessesPolicy.snapshot(
                                   appControlWindow.taskRows,
                                   appControlWindow.taskSnapshotLoading,
                                   appControlWindow.taskSnapshotError)
                             : null
            socialActionsAvailable: messagingWindow !== null
            socialSnapshot: messagingWindow
                            ? ({ menuOpen: messagingWindow.menuOpen,
                                 activeAppIndex: messagingWindow.activeAppIndex })
                            : null
            onOpenAppControlRequested: {
                if (appControlWindow)
                    appControlWindow.menuOpen = true;
            }
            onOpenSocialRequested: {
                if (messagingWindow)
                    messagingWindow.menuOpen = true;
            }
            onSocialPlatformRequested: function(index) {
                if (!messagingWindow || !Number.isInteger(index)
                        || index < 0 || index > 3)
                    return;
                messagingWindow.menuOpen = true;
                // Only MessagingW owns Discord/X window and focus behavior.
                messagingWindow.activateApp(index, false);
            }
            // The Hub is not yet enrolled in Koinoikos's cross-window
            // registry; it cannot take keyboard input during that mode.
            keyboardActive: !relationshipFocus.active
            relationshipFocusModeActive: relationshipFocus.active
            relationshipFocused: false
        }
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

        Network {
            id: sharedNetworkDock
        }

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
                weatherService: weatherService
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
                notificationsReference: notificationsHubWindow

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

        // Clock and TimeW. This mirrors CPU++/Weather's owner-window
        // composition while preserving the Clock module's existing size and
        // right-click 12/24-hour behavior. TimeW stays outside Koinoikos's
        // keyboard roster until it has an explicit focus-adapter assignment.
        // Do not use anchors.fill on Clock here: its width is self-sized.
        Item {
            width: clockDock.width
            height: clockDock.height

            Clock {
                id: clockDock
                timeWindow: timewWindow
            }

            TimeW {
                id: timewWindow
                screen: Quickshell.screens.find(s => s.name === "DP-5")
                keyboardActive: !relationshipFocus.active
                relationshipFocusModeActive: relationshipFocus.active
            }
        }

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
                updatesController: softwareUpdateOffers

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
