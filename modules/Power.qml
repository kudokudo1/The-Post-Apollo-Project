import Quickshell
import QtQuick
import Quickshell.Io
import "../components"
import QtQuick.Effects
import Quickshell.Wayland
import Qt5Compat.GraphicalEffects

PanelWindow {
    property bool menuOpen: false
    property bool confirmShutdown: false
    property bool confirmReboot: false
    property int clickCount: 0
    property int pressCount: 0
    property int selectedIndex: 0
    property int hoveredIndex: 0
    property bool keyboardActive: false

    Process {
        id: lockProcess
        command: ["swaylock"]
    }

    Process {
        id: logoutProcess
        command: ["swaymsg", "exit"]
    }

    Process {
        id: rebootProcess
        command: ["systemctl", "reboot"]
    }

    Process {
        id: shutdownProcess
        command: ["systemctl", "poweroff"]
    }

    IpcHandler {
        target: "power"

        function toggle() {
            menuOpen = !menuOpen;
            confirmShutdown = false;
            confirmReboot = false;

            if (menuOpen) {
                selectedIndex = 1;
                powerMenu.forceActiveFocus();
            }
        }
    }

    anchors {
        top: false
        bottom: true
        right: true
        left: false
    }

    margins {
        top: 00
        bottom: 10
        right: 10
        left: 00
    }

    implicitWidth: 220
    implicitHeight: 290

    color: "transparent"
    WlrLayershell.keyboardFocus: menuOpen || confirmShutdown || confirmReboot ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None

    mask: Region {
        Region {
            item: powerButton
        }

        Region {
            x: powerMenu.x
            y: powerMenu.y
            width: powerMenu.visible ? powerMenu.width : 0
            height: powerMenu.visible ? powerMenu.height : 0
        }
    }

    Item {
        id: powerArea

        width: 220
        height: 290

        anchors.right: parent.right
        anchors.bottom: parent.bottom

        DockButton {
            id: powerButton

            radius: width / 100
            width: 50
            height: 50
            z: 1

            x: 155
            y: 230

            acceptedButtons: Qt.LeftButton
            open: menuOpen || confirmShutdown || confirmReboot

            normalForegroundColor: Colors.white
            hoverForegroundColor: Colors.orange
            pressedForegroundColor: Colors.orange

            normalContentGlowColor: Colors.cyan
            hoverContentGlowColor: Colors.orange
            pressedContentGlowColor: Colors.orange

            normalDockGlowColor: Colors.cyan
            hoverDockGlowColor: Colors.orange
            pressedDockGlowColor: Colors.orange

            contentGlowIdleOpacity: 0.30
            contentGlowHoverOpacity: 0.50
            contentGlowPressedOpacity: 0.70
            contentGlowIdleRadius: 19
            contentGlowHoverRadius: 19
            contentGlowPressedRadius: 19
            contentGlowIdleSamples: 17
            contentGlowHoverSamples: 17
            contentGlowPressedSamples: 17

            softGlowSpread: 1
            softGlowIdleOpacity: 0.50
            softGlowHoverOpacity: 0.70
            softGlowPressedOpacity: 0.90

            // The original closed Power button had no wide front wash.
            // Keep that base behavior; OPEN uses the shared Git-derived 0.22.
            wideGlowIdleOpacity: 0.0
            wideGlowHoverOpacity: 0.0
            wideGlowPressedOpacity: 0.0

            contentGlowSource: powerGlyph

            Text {
                id: powerGlyph

                anchors.centerIn: parent
                text: "⏻"
                font.pixelSize: 35
                color: powerButton.foregroundColor
            }

            onHoverEntered: {
                console.log("Mouse entered button");
            }

            onHoverExited: {
                console.log("Mouse left button");
            }

            onPressedChanged: {
                if (pressed)
                    pressCount++;
            }

            onLeftClicked: {
                clickCount++;
                menuOpen = !menuOpen;
                confirmShutdown = false;
                confirmReboot = false;

                if (menuOpen) {
                    selectedIndex = 1;
                    powerMenu.forceActiveFocus();
                }

                console.log("Menu open:", menuOpen);
            }
        }
    }

    Rectangle {
        id: powerMenu

        width: 150
        height: 200
        z: 1
        color: Colors.black

        x: 35
        y: 20

        visible: menuOpen || confirmShutdown || confirmReboot
        focus: menuOpen || confirmShutdown || confirmReboot

        Keys.onPressed: function (event) {
            if (!menuOpen)
                return;
            if (event.key === Qt.Key_Escape) {
                menuOpen = false;
                event.accepted = true;
            } else if (event.key === Qt.Key_Up) {
                keyboardActive = true;

                selectedIndex--;

                if (selectedIndex < 1)
                    selectedIndex = 4;

                event.accepted = true;
            } else if (event.key === Qt.Key_Down) {
                keyboardActive = true;

                selectedIndex++;

                if (selectedIndex > 4)
                    selectedIndex = 1;

                event.accepted = true;
            } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                if (selectedIndex === 1) {
                    menuOpen = false;
                    lockProcess.running = true;
                } else if (selectedIndex === 2) {
                    menuOpen = false;
                    logoutProcess.running = true;
                } else if (selectedIndex === 3) {
                    confirmReboot = true;
                } else if (selectedIndex === 4) {
                    confirmShutdown = true;
                }
            }
        }

        // NORMAL POWER MENU
        Column {
            id: menuItems

            width: parent.width

            visible: !confirmShutdown && !confirmReboot

            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 15

            spacing: 7

            Text {
                text: "POWER MENU"

                color: Colors.cyan
                font.pixelSize: 20

                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                width: parent.width - 20
                height: 2

                color: Colors.cyan

                anchors.horizontalCenter: parent.horizontalCenter
            }

            Rectangle {
                id: lockButton

                width: parent.width
                height: 30

                color: lockMouse.pressed ? Colors.magenta : !keyboardActive && lockMouse.containsMouse ? Colors.yellow : selectedIndex === 1 ? Colors.yellow : Colors.black

                Text {
                    text: "Lock"
                    anchors.centerIn: parent

                    color: lockMouse.pressed ? Colors.black : !keyboardActive && lockMouse.containsMouse ? Colors.orange : selectedIndex === 1 ? Colors.orange : Colors.cyan

                    font.pixelSize: 20

                    layer.enabled: selectedIndex === 1 || (!keyboardActive && lockMouse.containsMouse)

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

                MouseArea {
                    id: lockMouse

                    anchors.fill: parent
                    hoverEnabled: true

                    onEntered: {
                        selectedIndex = 1;
                    }

                    onClicked: {
                        console.log("Lock clicked!");
                        menuOpen = false;
                        lockProcess.running = true;
                    }
                }

                DropShadow {
                    source: lockButton
                    anchors.fill: lockButton

                    color: lockMouse.pressed ? Colors.magenta : !keyboardActive && lockMouse.containsMouse ? Colors.orange : selectedIndex === 1 ? Colors.orange : Colors.cyan

                    opacity: lockMouse.pressed ? 0.55 : lockMouse.containsMouse ? 0.55 : selectedIndex === 1 ? 0.55 : 0

                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 12
                    samples: 25

                    z: -1
                    transparentBorder: true
                }
            }

            Rectangle {
                id: logoutButton

                width: parent.width
                height: 30

                color: logoutMouse.pressed ? Colors.magenta : !keyboardActive && logoutMouse.containsMouse ? Colors.yellow : selectedIndex === 2 ? Colors.yellow : Colors.black

                Text {
                    text: "Logout"
                    anchors.centerIn: parent

                    color: logoutMouse.pressed ? Colors.black : !keyboardActive && logoutMouse.containsMouse ? Colors.orange : selectedIndex === 2 ? Colors.orange : Colors.cyan

                    font.pixelSize: 20

                    layer.enabled: selectedIndex === 2 || (!keyboardActive && logoutMouse.containsMouse)

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

                MouseArea {
                    id: logoutMouse

                    anchors.fill: parent
                    hoverEnabled: true

                    onClicked: {
                        console.log("Logout clicked!");
                        logoutProcess.running = true;
                    }

                    onEntered: {
                        selectedIndex = 2;
                    }
                }

                DropShadow {
                    source: logoutButton
                    anchors.fill: logoutButton

                    color: logoutMouse.pressed ? Colors.magenta : selectedIndex === 2 ? Colors.orange : !keyboardActive && logoutMouse.containsMouse ? Colors.orange : Colors.cyan

                    opacity: logoutMouse.pressed ? 0.55 : selectedIndex === 2 ? 0.55 : logoutMouse.containsMouse ? 0.55 : 0

                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 12
                    samples: 25

                    z: -1
                    transparentBorder: true
                }
            }

            Rectangle {
                id: rebootButton

                width: parent.width
                height: 30

                color: rebootMouse.pressed ? Colors.red : selectedIndex === 3 ? Colors.yellow : !keyboardActive && rebootMouse.containsMouse ? Colors.yellow : Colors.black

                Text {
                    text: "Reboot"
                    anchors.centerIn: parent

                    color: rebootMouse.pressed ? Colors.black : selectedIndex === 3 ? Colors.orange : !keyboardActive && rebootMouse.containsMouse ? Colors.orange : Colors.cyan

                    font.pixelSize: 20

                    layer.enabled: selectedIndex === 3 || (!keyboardActive && rebootMouse.containsMouse)

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

                MouseArea {
                    id: rebootMouse

                    anchors.fill: parent
                    hoverEnabled: true

                    onClicked: {
                        console.log("Reboot clicked!");
                        confirmReboot = true;
                    }

                    onEntered: {
                        selectedIndex = 3;
                    }
                }

                DropShadow {
                    source: rebootButton
                    anchors.fill: rebootButton

                    color: rebootMouse.pressed ? Colors.red : selectedIndex === 3 ? Colors.orange : !keyboardActive && rebootMouse.containsMouse ? Colors.orange : Colors.cyan

                    opacity: rebootMouse.pressed ? 0.55 : selectedIndex === 3 ? 0.55 : rebootMouse.containsMouse ? 0.55 : 0

                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 12
                    samples: 25

                    z: -1
                    transparentBorder: true
                }
            }

            Rectangle {
                id: shutdownButton

                width: parent.width
                height: 30

                color: shutdownMouse.pressed ? Colors.red : selectedIndex === 4 ? Colors.yellow : shutdownMouse.containsMouse ? Colors.yellow : Colors.black

                Text {
                    text: "Shutdown"
                    anchors.centerIn: parent

                    color: shutdownMouse.pressed ? Colors.black : selectedIndex === 4 ? Colors.orange : shutdownMouse.containsMouse ? Colors.orange : Colors.cyan

                    font.pixelSize: 20

                    layer.enabled: selectedIndex === 4 || shutdownMouse.containsMouse

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

                MouseArea {
                    id: shutdownMouse

                    anchors.fill: parent
                    hoverEnabled: true

                    onClicked: {
                        console.log("Shutdown clicked!");
                        confirmShutdown = true;
                    }

                    onEntered: {
                        selectedIndex = 4;
                    }
                }

                DropShadow {
                    source: shutdownButton
                    anchors.fill: shutdownButton

                    color: shutdownMouse.pressed ? Colors.red : selectedIndex === 4 ? Colors.orange : !keyboardActive && shutdownMouse.containsMouse ? Colors.orange : Colors.cyan

                    opacity: shutdownMouse.pressed ? 0.55 : selectedIndex === 4 ? 0.55 : shutdownMouse.containsMouse ? 0.55 : 0

                    horizontalOffset: 0
                    verticalOffset: 0
                    radius: 12
                    samples: 25

                    z: -1
                    transparentBorder: true
                }
            }
        }

        DropShadow {
            id: powerMenuGlow

            source: powerMenu

            anchors.fill: powerMenu

            width: powerMenu.width - 0
            height: powerMenu.height - 0

            horizontalOffset: 0
            verticalOffset: 0
            radius: 15
            samples: 41
            z: -1

            color: Colors.cyan
            visible: menuOpen
            opacity: menuOpen ? 0.5 : 0
            transparentBorder: true
        }

        RectangularShadow {
            anchors.centerIn: powerMenu

            width: powerMenu.width - 0
            height: powerMenu.height - 0

            spread: 3
            z: -3

            visible: menuOpen
            opacity: menuOpen ? 0.7 : 0

            color: Colors.cyan
        }
    }

    // SHUTDOWN CONFIRMATION SCREEN
    Column {
        id: shutdownConfirm

        width: powerMenu.width
        height: powerMenu.height
        x: powerMenu.x
        y: powerMenu.y

        z: 10

        visible: confirmShutdown

        // anchors.horizontalCenter: parent.horizontalCenter
        // anchors.top: parent.top
        // anchors.topMargin: 25

        spacing: 20

        Text {
            text: "SHUTDOWN?"
            color: Colors.red
            font.pixelSize: 22

            anchors.horizontalCenter: parent.horizontalCenter
        }

        Rectangle {
            id: cancelshutdownButton

            width: parent.width
            height: 30

            color: cancelshutdownMouse.pressed ? Colors.magenta : cancelshutdownMouse.containsMouse ? Colors.yellow : Colors.black

            Text {
                text: "Cancel"

                color: cancelshutdownMouse.pressed ? Colors.black : cancelshutdownMouse.containsMouse ? Colors.orange : Colors.cyan

                font.pixelSize: 22
                anchors.centerIn: parent

                layer.enabled: cancelshutdownMouse.containsMouse

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

            MouseArea {
                id: cancelshutdownMouse

                anchors.fill: parent
                hoverEnabled: true

                onClicked: {
                    console.log("Shutdown cancelled!");
                    confirmShutdown = false;
                }
            }

            DropShadow {
                source: cancelshutdownButton
                anchors.fill: cancelshutdownButton

                color: cancelshutdownMouse.pressed ? Colors.magenta : cancelshutdownMouse.containsMouse ? Colors.orange : Colors.cyan

                opacity: cancelshutdownMouse.pressed ? 0.55 : cancelshutdownMouse.containsMouse ? 0.55 : 0

                horizontalOffset: 0
                verticalOffset: 0
                radius: 12
                samples: 25

                z: -1
                transparentBorder: true
            }
        }

        Rectangle {
            id: confirmshutdownButton

            width: parent.width
            height: 30

            color: confirmshutdownMouse.pressed ? Colors.red : confirmshutdownMouse.containsMouse ? Colors.yellow : Colors.black

            Text {
                text: "CONFIRM!"

                color: confirmshutdownMouse.pressed ? Colors.black : confirmshutdownMouse.containsMouse ? Colors.orange : Colors.cyan

                font.pixelSize: 20
                anchors.centerIn: parent

                layer.enabled: confirmshutdownMouse.containsMouse

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

            MouseArea {
                id: confirmshutdownMouse

                anchors.fill: parent
                hoverEnabled: true

                onClicked: {
                    console.log("Shutdown confirmed!");
                    shutdownProcess.running = true;
                }
            }

            DropShadow {
                source: confirmshutdownButton
                anchors.fill: confirmshutdownButton

                color: confirmshutdownMouse.pressed ? Colors.red : confirmshutdownMouse.containsMouse ? Colors.orange : Colors.cyan

                opacity: confirmshutdownMouse.pressed ? 0.55 : confirmshutdownMouse.containsMouse ? 0.55 : 0

                horizontalOffset: 0
                verticalOffset: 0
                radius: 12
                samples: 25

                z: -1
                transparentBorder: true
            }
        }
    }

    // REBOOT CONFIRMATION SCREEN
    Column {
        id: rebootConfirm

        width: powerMenu.width
        height: powerMenu.height
        x: powerMenu.x
        y: powerMenu.y

        z: 10

        visible: confirmReboot

        //   anchors.horizontalCenter: parent.horizontalCenter
        //   anchors.top: parent.top
        //   anchors.topMargin: 25

        spacing: 20

        Text {
            text: "REBOOT?"
            color: Colors.red
            font.pixelSize: 22

            anchors.horizontalCenter: parent.horizontalCenter
        }

        Rectangle {
            id: cancelrebootButton

            width: parent.width
            height: 30

            color: cancelrebootMouse.pressed ? Colors.magenta : cancelrebootMouse.containsMouse ? Colors.yellow : Colors.black

            Text {
                text: "Cancel"

                color: cancelrebootMouse.pressed ? Colors.black : cancelrebootMouse.containsMouse ? Colors.orange : Colors.cyan

                font.pixelSize: 22

                anchors.centerIn: parent

                layer.enabled: cancelrebootMouse.containsMouse

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

            MouseArea {
                id: cancelrebootMouse

                anchors.fill: parent
                hoverEnabled: true

                onClicked: {
                    console.log("Reboot cancelled!");
                    confirmReboot = false;
                }
            }

            DropShadow {
                source: cancelrebootButton
                anchors.fill: cancelrebootButton

                color: cancelrebootMouse.pressed ? Colors.magenta : cancelrebootMouse.containsMouse ? Colors.orange : Colors.cyan

                opacity: cancelrebootMouse.pressed ? 0.55 : cancelrebootMouse.containsMouse ? 0.55 : 0

                horizontalOffset: 0
                verticalOffset: 0
                radius: 12
                samples: 25

                z: -1
                transparentBorder: true
            }
        }

        Rectangle {
            id: confirmrebootButton

            width: parent.width
            height: 30

            color: confirmrebootMouse.pressed ? Colors.red : confirmrebootMouse.containsMouse ? Colors.yellow : Colors.black

            Text {
                text: "CONFIRM!"

                color: confirmrebootMouse.pressed ? Colors.black : confirmrebootMouse.containsMouse ? Colors.orange : Colors.cyan

                font.pixelSize: 20

                anchors.centerIn: parent

                layer.enabled: confirmrebootMouse.containsMouse

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

            MouseArea {
                id: confirmrebootMouse

                anchors.fill: parent
                hoverEnabled: true

                onClicked: {
                    console.log("Reboot confirmed!");
                    rebootProcess.running = true;
                }
            }

            DropShadow {
                source: confirmrebootButton
                anchors.fill: confirmrebootButton

                color: confirmrebootMouse.pressed ? Colors.red : confirmrebootMouse.containsMouse ? Colors.orange : Colors.cyan

                opacity: confirmrebootMouse.pressed ? 0.55 : confirmrebootMouse.containsMouse ? 0.3 : 0

                horizontalOffset: 0
                verticalOffset: 0
                radius: 12
                samples: 25

                z: -1
                transparentBorder: true
            }
        }
    }
}
