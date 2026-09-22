import QtQuick
import Quickshell
import "../../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: appSelector

    // ============================================================
    // STATE
    // ============================================================

    property int selectedIndex: 0
    property bool keyboardActive: false

    // Emitted ONLY when a button is actually clicked.
    signal appActivated(int index)

    // ============================================================
    // APPS
    // ============================================================

    property var messagingApps: [
        {
            name: "SESSIONS",
            icon: "../../assets/Sessions.png"
        },
        {
            name: "DISCORD",
            icon: ""
        },
        {
            name: "TELEGRAM",
            icon: ""
        }
    ]

    // ============================================================
    // SIZE / PANEL
    // ============================================================

    implicitWidth: 110
    implicitHeight: 700

    opacity: 0.90
    color: Colors.black

    border.width: 1
    border.color: Colors.cyan

    radius: 0

    // ============================================================
    // APP BUTTONS
    // ============================================================

    Column {
        id: appColumn

        anchors {
            top: parent.top
            horizontalCenter: parent.horizontalCenter
            topMargin: 10
        }

        spacing: 10

        Repeater {
            model: appSelector.messagingApps

            delegate: Item {
                id: buttonContainer

                required property var modelData
                required property int index

                width: 90
                height: 50

                Rectangle {
                    id: appButton

                    anchors.fill: parent

                    radius: 0
                    clip: false

                    property bool isSelected: appSelector.selectedIndex === buttonContainer.index

                    property bool isHovered: !appSelector.keyboardActive && appMouse.containsMouse

                    property bool isPressed: appMouse.pressed

                    // ============================================
                    // POWER-STYLE BUTTON COLOR
                    // ============================================

                    color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.yellow : appButton.isSelected ? Colors.yellow : Colors.dark

                    // ============================================
                    // CONTENT
                    // ============================================

                    Row {
                        id: appContent

                        anchors.centerIn: parent

                        spacing: buttonContainer.modelData.icon !== "" ? 4 : 0

                        // ========================================
                        // APP ICON
                        // ========================================

                        Item {
                            id: iconContainer

                            width: buttonContainer.modelData.icon !== "" ? 14 : 0

                            height: 18

                            visible: buttonContainer.modelData.icon !== ""

                            Image {
                                id: appIcon

                                anchors.centerIn: parent

                                width: 14
                                height: 14

                                source: buttonContainer.modelData.icon !== "" ? Qt.resolvedUrl(buttonContainer.modelData.icon) : ""

                                fillMode: Image.PreserveAspectFit

                                smooth: false

                                opacity: appButton.isPressed ? 1.0 : appButton.isSelected || appButton.isHovered ? 1.0 : 0.80
                            }

                            DropShadow {
                                anchors.fill: appIcon
                                source: appIcon

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 8
                                samples: 12

                                color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan

                                opacity: appButton.isPressed ? 0.55 : appButton.isHovered ? 0.45 : appButton.isSelected ? 0.45 : 0.18

                                transparentBorder: true
                            }
                        }

                        // ========================================
                        // APP NAME
                        // ========================================

                        Text {
                            id: appText

                            anchors.verticalCenter: parent.verticalCenter

                            text: buttonContainer.modelData.name

                            font.family: "GohuFont 11 Nerd Font Mono"

                            font.pixelSize: buttonContainer.modelData.icon !== "" ? 10 : 11

                            color: appButton.isPressed ? Colors.black : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan

                            layer.enabled: appButton.isSelected || appButton.isHovered

                            layer.effect: DropShadow {
                                color: Colors.orange

                                opacity: 1.0

                                horizontalOffset: 0
                                verticalOffset: 0

                                radius: 30
                                samples: 60

                                transparentBorder: true
                            }
                        }
                    }

                    // ============================================
                    // MOUSE
                    // ============================================

                    MouseArea {
                        id: appMouse

                        anchors.fill: parent

                        hoverEnabled: true

                        acceptedButtons: Qt.LeftButton

                        // Hover may move the visual selector,
                        // but it does NOT activate/open an app.
                        onEntered: {
                            appSelector.keyboardActive = false;
                            appSelector.selectedIndex = buttonContainer.index;
                        }

                        // The button itself owns activation.
                        onClicked: function (mouse) {
                            if (mouse.button !== Qt.LeftButton)
                                return;

                            appSelector.selectedIndex = buttonContainer.index;

                            appSelector.appActivated(buttonContainer.index);

                            console.log("Selected:", buttonContainer.modelData.name);
                        }
                    }

                    // ============================================
                    // CLOCK-STYLE CLOSE GLOW
                    // ============================================

                    RectangularShadow {
                        anchors.fill: parent

                        spread: 3

                        color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan

                        opacity: appButton.isPressed ? 0.60 : appButton.isHovered ? 0.50 : appButton.isSelected ? 0.50 : 0.0

                        z: -1
                    }

                    // ============================================
                    // CLOCK-STYLE WIDE GLOW
                    // ============================================

                    RectangularShadow {
                        anchors.fill: parent

                        spread: 10

                        color: appButton.isPressed ? Colors.magenta : appButton.isHovered ? Colors.orange : appButton.isSelected ? Colors.orange : Colors.cyan

                        opacity: appButton.isPressed ? 0.12 : appButton.isHovered ? 0.09 : appButton.isSelected ? 0.09 : 0.0

                        z: -2
                    }
                }
            }
        }
    }
}
