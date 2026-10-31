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

    implicitWidth: trayRow.implicitWidth + 13
    implicitHeight: 50

    color: Colors.black

    property bool trayButtonPressed: false
    property bool trayButtonHovered: false

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

        opacity: trayButtonPressed ? 0.6 : trayButtonHovered ? 0.5 : 0.4

        color: trayButtonPressed ? Colors.cyan : trayButtonHovered ? Colors.cyan : Colors.cyan
    }

    RectangularShadow {
        id: trayDockWideGlow

        anchors.fill: parent

        spread: 10

        z: 1

        opacity: trayButtonPressed ? 0.12 : trayButtonHovered ? 0.09 : 0.07

        color: trayButtonPressed ? Colors.cyan : trayButtonHovered ? Colors.cyan : Colors.cyan
    }

    // ===== TRAY ITEMS ===========================================

    RowLayout {
        id: trayRow

        anchors.fill: parent
        anchors.margins: 4

        spacing: 3

        Repeater {
            model: SystemTray.items

            delegate: Rectangle {
                id: trayButton

                required property var modelData

                implicitWidth: 30
                implicitHeight: 42

                color: "transparent"

                clip: false

                // ===== ICON =====================================

                Item {
                    id: trayIconContainer

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

                        // Tray selection belongs to the external item; a local
                        // click toggle cannot represent its menu/open state.
                        color: trayButtonMouse.pressed ? Colors.cyan : trayButtonMouse.containsMouse ? Colors.orange : Colors.cyan

                        transparentBorder: true
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

                    onEntered: {
                        trayDock.trayButtonHovered = true;
                    }

                    onExited: {
                        trayDock.trayButtonHovered = false;
                    }

                    onClicked: function (mouse) {
                        if (mouse.button === Qt.LeftButton) {
                            // Activate the actual tray item; no undeclared
                            // local test-state assignment may intercept this.
                            if (trayDock.isDiscordTrayItem(trayButton.modelData))
                                trayDock.openDiscordFromTray();
                            else
                                trayButton.modelData.activate();
                        }

                        if (mouse.button === Qt.RightButton) {
                            // Right-click function
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
