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

    // Single ownership coordinator for the initial Git/Hospital pilot.
    // Existing property readers remain compatible with the shared owner.
    KeyboardOwnershipCoordinator {
        id: keyboardOwnership
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

        onOwnerChanged: {
            if (active && (owner === "git" || owner === "hospital"
                           || owner === "notifications"))
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

    SpaceService {
        id: spaceService
    }

    // One session-wide hardware state. AppControl and CPU++ consume these
    // same instances instead of starting independent telemetry/control stacks.
    SystemTelemetry {
        id: sharedSystemTelemetry

        onFanRowsChanged: {
            sharedFanControl.reconcilePendingPercent(fanRows);
        }
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

        // Hospital

        Item {
            width: hospitalButton.implicitWidth
            height: hospitalButton.implicitHeight

            Hospital {
                id: hospitalButton

                anchors.fill: parent

                menuOpen: hospitalWindow.menuOpen

                onToggleRequested: {
                    hospitalWindow.toggle();
                }
            }

            HospitalW {
                id: hospitalWindow

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
                    gitWindow.toggle();
                }
            }

            GitW {
                id: gitWindow

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
