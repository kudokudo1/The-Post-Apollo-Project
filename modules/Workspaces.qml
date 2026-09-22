import Quickshell
import Quickshell.Io
import QtQuick
import QtQml
import QtQuick.Layouts
import "../components"
import Quickshell.I3
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: workspacesDock

    //implicitHeight: 48
    //implicitWidth: 151
    implicitWidth: workspacesRow.implicitWidth + 13
    implicitHeight: workspacesRow.implicitHeight + 8

    color: Colors.black

    property color inactiveColor: Colors.cyan
    property color activeColor: Colors.orange

    property bool workspacesButtonPressed: false
    property bool workspacesButtonHovered: false

    RectangularShadow {
        id: workspacesDockSoftGlow

        anchors.fill: parent

        spread: 3
        z: -1

        opacity: workspacesDockMouse.pressed || workspacesDock.workspacesButtonPressed ? 0.6 : workspacesDockMouse.containsMouse || workspacesDock.workspacesButtonHovered ? 0.5 : 0.4

        color: workspacesDockMouse.pressed || workspacesDock.workspacesButtonPressed ? Colors.cyan : workspacesDockMouse.containsMouse || workspacesDock.workspacesButtonHovered ? Colors.orange : Colors.cyan
    }

    RectangularShadow {
        id: workspacesDockWideGlow

        anchors.fill: parent

        spread: 10
        z: 1

        opacity: workspacesDockMouse.pressed || workspacesDock.workspacesButtonPressed ? 0.12 : workspacesDockMouse.containsMouse || workspacesDock.workspacesButtonHovered ? 0.06 : 0.04

        color: workspacesDockMouse.pressed || workspacesDock.workspacesButtonPressed ? Colors.cyan : workspacesDockMouse.containsMouse || workspacesDock.workspacesButtonHovered ? Colors.orange : Colors.cyan
    }

    MouseArea {
        id: workspacesDockMouse

        anchors.fill: parent

        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    Process {
        id: workspacesEvents

        command: ["swaymsg", "-t", "subscribe", "[\"workspace\"]"]

        running: true

        onRunningChanged: {
            console.log("workspaceEvents running:", running);
        }

        Component.onCompleted: {
            console.log("WORKSPACE PROCESS CREATED");
        }

        stdout: SplitParser {
            onRead: data => {
                console.log("WORKSPACE EVENT:", data);
            }
        }
    }

    RowLayout {
        id: workspacesRow

        anchors.fill: parent
        anchors.margins: 4
        spacing: 3

        Repeater {
            model: I3.workspaces

            Rectangle {
                id: workspacesWorkspaceButton

                property bool isActive: I3.focusedWorkspace?.num === workspaceNumber

                property int workspaceNumber: modelData.number

                implicitWidth: visible ? 25 : 0
                implicitHeight: 42

                visible: modelData.monitor.name !== "HDMI-A-1" || workspacesWorkspaceButton.isActive || modelData.windows.length > 0

                z: workspacesWorkspaceButton.isActive ? 2 : 1

                clip: false
                color: "transparent"

                Rectangle {
                    id: workspacesIsActiveButtonBackground

                    anchors.centerIn: parent

                    width: parent.width
                    height: parent.height

                    clip: false
                    z: 0
                    opacity: 0.7

                    color: workspacesWorkspaceButton.isActive ? Colors.dark : "transparent"
                }

                Rectangle {
                    id: workspacesButtonBackground

                    anchors.centerIn: parent

                    width: parent.width + 6
                    height: parent.height + 5

                    clip: false
                    z: -1

                    color: Colors.dark

                    opacity: workspacesWorkspaceButton.isActive ? 0.0 : 0.0
                }

                DropShadow {
                    anchors.fill: workspacesButtonBackground

                    source: workspacesButtonBackground

                    z: -1

                    horizontalOffset: 0
                    verticalOffset: 0

                    radius: 20
                    samples: 21

                    color: workspacesText.workspaceColor

                    opacity: workspacesWorkspaceButton.isActive ? 0.2 : 0.0
                }

                Item {
                    id: workspacesTextContainer

                    anchors.fill: parent

                    Text {
                        id: workspacesText

                        anchors.centerIn: parent

                        text: workspacesWorkspaceButton.workspaceNumber

                        property color workspaceColor: modelData.monitor.name === "HDMI-A-1" ? (workspacesWorkspaceButton.isActive ? Colors.yellow : Colors.white) : (workspacesWorkspaceButton.isActive ? Colors.orange : Colors.cyan)

                        color: workspacesText.workspaceColor

                        font.pixelSize: 20
                    }

                    DropShadow {
                        id: workspacesTextGlow

                        source: workspacesText
                        anchors.fill: workspacesText

                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: 14
                        samples: 15

                        z: 2

                        opacity: workspacesButtonMouse.pressed ? 1.0 : workspacesButtonMouse.containsMouse ? 0.8 : 0.6

                        color: workspacesButtonMouse.pressed ? Colors.cyan : workspacesButtonMouse.containsMouse ? Colors.cyan : Colors.cyan

                        transparentBorder: true
                    }

                    DropShadow {
                        id: workspacesActiveTextGlow

                        anchors.fill: workspacesText

                        source: workspacesText

                        visible: workspacesWorkspaceButton.isActive

                        horizontalOffset: 0
                        verticalOffset: 0

                        radius: 14
                        samples: 15

                        z: 2

                        opacity: workspacesButtonMouse.pressed ? 1.0 : workspacesButtonMouse.containsMouse ? 0.8 : 0.7

                        color: workspacesText.workspaceColor

                        transparentBorder: true
                    }
                }

                // Click a specific workspace
                Process {
                    id: workspacesSwitchWorkspace

                    command: ["swaymsg", "workspace", workspacesWorkspaceButton.workspaceNumber.toString()]

                    stdout: StdioCollector {
                        onStreamFinished: {
                            console.log(text);
                        }
                    }
                }

                // Scroll between workspaces
                Process {
                    id: workspacesScrollWorkspace

                    command: ["swaymsg", "workspace", "next"]

                    stdout: StdioCollector {
                        onStreamFinished: {
                            console.log("SCROLL:", text);
                        }
                    }
                }

                // Test Process
                Process {
                    id: workspacesGetWorkspaces

                    command: ["swaymsg", "-t", "get_workspaces", "-r"]

                    stdout: StdioCollector {
                        onStreamFinished: {
                            console.log("WORKSPACES:", text);

                            var workspaces = JSON.parse(text);
                        }
                    }

                    Component.onCompleted: {
                        console.log("Starting workspace query");
                        workspacesGetWorkspaces.running = true;
                    }
                }

                MouseArea {
                    id: workspacesButtonMouse

                    anchors.fill: parent

                    hoverEnabled: true

                    onPressed: {
                        workspacesDock.workspacesButtonPressed = true;
                    }

                    onReleased: {
                        workspacesDock.workspacesButtonPressed = false;
                    }

                    onCanceled: {
                        workspacesDock.workspacesButtonPressed = false;
                    }

                    onEntered: {
                        workspacesDock.workspacesButtonHovered = true;
                    }

                    onExited: {
                        workspacesDock.workspacesButtonHovered = false;
                    }

                    onClicked: {
                        console.log("Workspace", workspacesWorkspaceButton.workspaceNumber, "clicked");

                        workspacesSwitchWorkspace.running = true;
                    }

                    // Scroll workspace
                    onWheel: function (wheel) {
                        if (wheel.angleDelta.y > 0) {
                            workspacesScrollWorkspace.command = ["swaymsg", "workspace", "prev"];
                        } else {
                            workspacesScrollWorkspace.command = ["swaymsg", "workspace", "next"];
                        }

                        workspacesScrollWorkspace.running = true;

                        wheel.accepted = true;
                    }
                }
            }
        }
    }
}
