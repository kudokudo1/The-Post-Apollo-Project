import QtQuick
import Quickshell
import QtQuick.Layouts
import Quickshell.Services.SystemTray
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

        opacity: trayButtonPressed ? 0.12 : trayButtonHovered ? 0.06 : 0.04

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

                //property bool clickTest: false

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

                    DropShadow {
                        id: trayIconGlow

                        anchors.fill: trayIcon

                        source: trayIcon

                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: 14
                        samples: 15

                        z: 2

                        opacity: trayButtonMouse.pressed ? 1.0 : trayButtonMouse.containsMouse ? 0.8 : 0.6

                        color: trayButton.clickTest ? Colors.magenta : trayButtonMouse.pressed ? Colors.cyan : trayButtonMouse.containsMouse ? Colors.orange : Colors.cyan

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
                            trayButton.clickTest = !trayButton.clickTest;

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
