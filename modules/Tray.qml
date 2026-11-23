import QtQuick
import Quickshell
import QtQuick.Layouts
import Quickshell.Services.SystemTray
import qs.services.social
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: trayDock

    // Never collapse to a 13px black sliver when SystemTray.items is empty.
    // Dynamic icon rows grow naturally, with their entire group centered.
    implicitWidth: Math.max(92, trayRow.implicitWidth + 16)
    implicitHeight: 50

    color: Colors.black
    border.width: 1
    border.color: accentColor
    radius: 0

    property bool trayButtonPressed: false
    // Observe the whole 92px+ plaque, including gaps and the empty state.
    // A passive HoverHandler coexists with every app's own MouseArea, so
    // it does not steal native left/right-click activation.
    HoverHandler {
        id: trayHoverHandler
        blocking: false
    }
    readonly property bool trayButtonHovered: trayHoverHandler.hovered

    // The native menu is the one truthful "open" state available from
    // StatusNotifier. Running apps are not necessarily open windows.
    // Hold only the most recently opened anchor and release on close or
    // delegate destruction so removing an app cannot latch a magenta tray.
    property var openMenuAnchor: null
    readonly property bool trayMenuOpen: openMenuAnchor !== null
                                         && openMenuAnchor.visible

    // Workspace-style precedence: actual menu OPEN > hover/press > idle.
    // The perimeter, two outer halos, empty label and marker agree.
    readonly property color accentColor:
        trayMenuOpen ? Colors.magenta
        : (trayButtonPressed || trayButtonHovered ? Colors.orange : Colors.cyan)

    // Exact application identity, never a substring match on a random tray
    // tooltip. Other applications retain their own native tray activation.
    function isDiscordTrayItem(item) {
        const id = String(item.id || "").trim().toLowerCase().replace(/\.desktop$/, "");
        const title = String(item.title || "").trim().toLowerCase();
        const tooltip = String(item.tooltipTitle || "").trim().toLowerCase();
        return id === "vesktop" || id === "dev.vencord.vesktop"
               || id === "discord" || title === "vesktop" || title === "discord"
               || tooltip === "vesktop" || tooltip === "discord";
    }

    // Lutris's AppIndicator commonly publishes an application-owned menu
    // while Activate may be a no-op. Match exact known identities only;
    // never rewrite another application's tray activation semantics.
    function isLutrisTrayItem(item) {
        const id = String(item.id || "").trim().toLowerCase().replace(/\.desktop$/, "");
        const title = String(item.title || "").trim().toLowerCase();
        return id === "lutris" || id === "net.lutris.lutris"
               || id === "net_lutris_lutris" || title === "lutris";
    }

    function openDiscordFromTray() {
        // Both Tray and MessagingW run in this Quickshell instance. Signal
        // Social directly instead of spawning a qs CLI process, which may
        // target a different instance or fail without reporting to this UI.
        SocialTrayBridge.requestDiscordActivation();
    }

    // ===== DOCK GLOW ============================================

    RectangularShadow {
        id: trayDockSoftGlow

        anchors.fill: parent

        spread: 3

        z: -1

        opacity: trayMenuOpen ? 0.72
                 : trayButtonPressed ? 0.6 : trayButtonHovered ? 0.5 : 0.4

        color: trayDock.accentColor
    }

    RectangularShadow {
        id: trayDockWideGlow

        anchors.fill: parent

        spread: 10

        z: 1

        opacity: trayMenuOpen ? 0.18
                 : trayButtonPressed ? 0.12 : trayButtonHovered ? 0.09 : 0.07

        color: trayDock.accentColor
    }

    // ===== EMPTY STATE / VISIBLE GOHU LABEL =====================
    // The label describes an empty native tray; it is not an inert button
    // masquerading as a real external application icon.
    Column {
        id: emptyTrayState
        anchors.centerIn: parent
        spacing: 1
        visible: trayItems.count === 0

        GohuText {
            width: 92
            horizontalAlignment: Text.AlignHCenter
            text: "TRAY"
            font.pixelSize: 14
            color: trayDock.accentColor
        }
        GohuText {
            width: 92
            horizontalAlignment: Text.AlignHCenter
            text: "NO ICONS"
            font.pixelSize: 9
            color: Colors.white
        }
    }

    Rectangle {
        width: 34
        height: 2
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 3
        color: trayDock.accentColor
        opacity: 0.85
    }

    // ===== TRAY ITEMS ===========================================

    RowLayout {
        id: trayRow

        // Without a centered RowLayout, a single 30px icon in the new
        // 92px minimum-width plaque would sit against the left edge.
        anchors.centerIn: parent

        spacing: 3

        Repeater {
            id: trayItems
            model: SystemTray.items

            delegate: Rectangle {
                id: trayButton

                required property var modelData

                // Match Workspaces.qml's 25 × 42 delegate footprint.
                implicitWidth: 25
                implicitHeight: 42

                color: "transparent"

                clip: false

                // A live SystemTray.items delegate represents an application
                // registered with the independent StatusNotifier watcher.
                // The registration survives pointer movement, native-menu
                // closure, and Quickshell restarts. When the item unregisters,
                // the delegate (and therefore its active state) disappears.
                // This measures an open/running TRAY application, not a
                // visible Sway window.
                readonly property bool appRegistered:
                    trayButton.modelData !== null
                    && trayButton.modelData !== undefined

                z: trayButton.appRegistered ? 2 : 1

                // Match the Workspace active-over-hover precedence for
                // each registered app: MAGENTA remains until unregister.
                readonly property color iconAccentColor:
                    trayButton.appRegistered ? Colors.magenta
                    : (trayButtonMouse.containsMouse || trayButtonMouse.pressed
                       ? Colors.orange : Colors.cyan)

                Component.onDestruction: {
                    if (trayDock.openMenuAnchor === trayNativeMenu)
                        trayDock.openMenuAnchor = null;
                }

                // ===== WORKSPACE-EXACT CARD LAYERS ==============
                // Workspaces.qml uses a transparent inactive rectangle,
                // a dark active rectangle, and a fully transparent larger
                // sampled backing. Keep the active card while the item's
                // registered application lives, just like a focused
                // Workspace keeps its card after the pointer leaves.
                readonly property bool cardEmphasized: trayButton.appRegistered

                Rectangle {
                    id: trayActiveButtonBackground
                    anchors.centerIn: parent
                    width: parent.width
                    height: parent.height
                    clip: false
                    z: 0
                    opacity: 0.7
                    color: trayButton.cardEmphasized ? Colors.dark : "transparent"
                }

                Rectangle {
                    id: trayButtonBackground
                    anchors.centerIn: parent
                    width: parent.width + 6
                    height: parent.height + 5
                    clip: false
                    z: -1
                    color: Colors.dark
                    // Keep the Workspace's explicit invisible state layer.
                    opacity: trayButton.cardEmphasized ? 0.0 : 0.0
                }

                SafeDropShadow {
                    id: trayButtonBackgroundGlow
                    anchors.fill: trayButtonBackground
                    safeSource: trayButtonBackground
                    z: -1
                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 20
                    samples: 21
                    color: trayButton.iconAccentColor
                    opacity: trayButton.cardEmphasized ? 0.2 : 0.0
                }

                // ===== ICON AND DUAL WORKSPACE GLOWS ============
                Item {
                    id: trayIconContainer
                    z: 1

                    anchors.fill: parent

                    Image {
                        id: trayIcon

                        anchors.centerIn: parent

                        width: 22
                        height: 22

                        source: trayButton.modelData.icon

                        fillMode: Image.PreserveAspectFit

                        smooth: false
                    }

                    SafeDropShadow {
                        id: trayIconGlow

                        anchors.fill: trayIcon

                        safeSource: trayIcon

                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: 14
                        samples: 15

                        z: 2

                        opacity: trayButtonMouse.pressed ? 1.0 : trayButtonMouse.containsMouse ? 0.95 : 0.75

                        // As on Workspaces, cyan remains the base image aura.
                        color: Colors.cyan

                        transparentBorder: true
                    }

                    SafeDropShadow {
                        id: trayActiveIconGlow
                        anchors.fill: trayIcon
                        safeSource: trayIcon
                        horizontalOffset: 0
                        verticalOffset: 0
                        radius: 14
                        samples: 15
                        z: 2
                        visible: trayButton.appRegistered
                        opacity: trayButtonMouse.pressed ? 1.0
                                 : trayButtonMouse.containsMouse ? 0.95 : 0.75
                        color: trayButton.iconAccentColor
                        transparentBorder: true
                    }
                }

                // Menu entries, labels, enablement and submenu behavior
                // are supplied by the *application* through StatusNotifier.
                // Quickshell displays that real menu; Post-Apollo does not
                // invent a second per-application command list.
                QsMenuAnchor {
                    id: trayNativeMenu
                    menu: trayButton.modelData.menu
                    anchor.item: trayButton
                    // This is a BOTTOM dock. Expand toward the screen above,
                    // rather than trying to draw the menu below its edge.
                    anchor.edges: Edges.Top
                    anchor.gravity: Edges.Top

                    // The OUTER tray frame reflects this native menu's
                    // visible state. Each app card separately reflects the
                    // lifecycle of its StatusNotifier registration.
                    onOpened: trayDock.openMenuAnchor = trayNativeMenu
                    onClosed: {
                        if (trayDock.openMenuAnchor === trayNativeMenu)
                            trayDock.openMenuAnchor = null;
                    }
                }

                // ===== MOUSE ====================================

                MouseArea {
                    id: trayButtonMouse

                    anchors.fill: parent

                    hoverEnabled: true

                    acceptedButtons: Qt.LeftButton | Qt.RightButton

                    onPressed: {
                        trayDock.trayButtonPressed = true;
                    }

                    onReleased: {
                        trayDock.trayButtonPressed = false;
                    }

                    onCanceled: {
                        trayDock.trayButtonPressed = false;
                    }

                    onClicked: function (mouse) {
                        if (mouse.button === Qt.LeftButton) {
                            // Some StatusNotifier entries are menu-only:
                            // activate() would be a no-op for those apps.
                            // A Lutris AppIndicator may advertise
                            // onlyMenu=false yet ignore Activate entirely.
                            // Its own native menu is the safe visible
                            // fallback, not an untracked process launch.
                            const nativeMenuAvailable = trayButton.modelData.hasMenu
                                                        && trayButton.modelData.menu;
                            if (trayButton.modelData.onlyMenu
                                    || (nativeMenuAvailable
                                        && trayDock.isLutrisTrayItem(trayButton.modelData))) {
                                if (nativeMenuAvailable)
                                    trayNativeMenu.open();
                            } else if (trayDock.isDiscordTrayItem(trayButton.modelData)) {
                                trayDock.openDiscordFromTray();
                            } else {
                                trayButton.modelData.activate();
                            }
                        }

                        if (mouse.button === Qt.RightButton) {
                            // No synthetic menu for an application that
                            // does not advertise a native menu handle.
                            if (trayButton.modelData.hasMenu
                                    && trayButton.modelData.menu)
                                trayNativeMenu.open();
                        }
                    }

                    onWheel: function (wheel) {

                        // Scroll function

                        wheel.accepted = true;
                    }
                }
            }
        }
    }
}
