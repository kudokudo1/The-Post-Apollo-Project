import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

Rectangle {
    id: thermalViewSelector

    required property var controller
    signal viewModeRequested(int mode)

    height: 42
    color: Colors.black
    z: 260

    Row {
        anchors.fill: parent
        anchors.leftMargin: 7
        anchors.rightMargin: 7
        anchors.topMargin: 5
        anchors.bottomMargin: 6
        spacing: 7

        Rectangle {
            id: thermalButton
            width: (parent.width - parent.spacing) / 2
            height: parent.height
            readonly property bool selected:
                controller.thermalViewMode === controller.thermalViewThermal
            readonly property bool hovered: thermalMouse.containsMouse
            readonly property bool pressed: thermalMouse.pressed
            readonly property color stateColor:
                selected ? Colors.magenta : Colors.orange
            color:
                pressed ? Colors.magenta
                : hovered || selected ? Colors.yellow
                : Colors.dark
            border.width: 1
            border.color: stateColor

            ThermalIcon {
                id: thermalIcon
                anchors.centerIn: parent
                anchors.verticalCenterOffset: 3
                iconScale: 1.0
                iconColor: thermalButton.pressed ? Colors.black : thermalButton.stateColor
                pressed: thermalButton.pressed
                glowOpacity: 0.50
            }

            DropShadow {
                anchors.fill: thermalIcon
                source: thermalIcon
                radius: 7
                samples: 5
                opacity:
                    thermalButton.pressed ? 0.0
                    : thermalButton.selected ? 0.68
                    : thermalButton.hovered ? 0.60 : 0.44
                color: thermalButton.stateColor
                transparentBorder: true
            }

            MouseArea {
                id: thermalMouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked:
                    thermalViewSelector.viewModeRequested(
                        controller.thermalViewThermal
                    )
            }

            RectangularShadow {
                anchors.fill: parent
                spread: 5
                z: -1
                opacity: thermalButton.hovered || thermalButton.selected ? 0.70 : 0.50
                color: thermalButton.stateColor
            }
        }

        Rectangle {
            id: fanButton
            width: (parent.width - parent.spacing) / 2
            height: parent.height
            readonly property bool selected:
                controller.thermalViewMode === controller.thermalViewFans
            readonly property bool hovered: fanMouse.containsMouse
            readonly property bool pressed: fanMouse.pressed
            readonly property color stateColor:
                selected ? Colors.magenta
                : hovered ? Colors.orange : Colors.omnitrix
            color:
                pressed ? Colors.magenta
                : hovered || selected ? Colors.yellow
                : Colors.dark
            border.width: 1
            border.color: stateColor

            Item {
                id: fanContent
                anchors.centerIn: parent
                width: fanRow.implicitWidth
                height: parent.height

                Row {
                    id: fanRow
                    anchors.centerIn: parent
                    spacing: 5

                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: 25
                        height: 20
                        color: "transparent"
                        border.width: 1
                        border.color: fanButton.pressed ? Colors.black : fanButton.stateColor

                        GohuText {
                            anchors.centerIn: parent
                            anchors.verticalCenterOffset: 3
                            text: "✇"
                            font.pixelSize: 19
                            color: fanButton.pressed ? Colors.black : fanButton.stateColor
                        }

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 2
                            z: -1
                            opacity: fanButton.pressed ? 0.0 : 0.24
                            color: fanButton.stateColor
                        }
                    }

                    GohuText {
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.verticalCenterOffset: 2
                        text: "༄｡°"
                        font.pixelSize: 15
                        color: fanButton.pressed ? Colors.black : fanButton.stateColor
                        layer.enabled: !fanButton.pressed
                        layer.effect: DropShadow {
                            radius: 9
                            samples: 9
                            opacity: 0.76
                            color: fanButton.stateColor
                            transparentBorder: true
                        }
                    }
                }
            }

            DropShadow {
                anchors.fill: fanContent
                source: fanContent
                radius: 9
                samples: 9
                opacity:
                    fanButton.pressed ? 0.0
                    : fanButton.selected ? 0.36
                    : fanButton.hovered ? 0.30 : 0.20
                color: fanButton.stateColor
                transparentBorder: true
            }

            MouseArea {
                id: fanMouse
                anchors.fill: parent
                hoverEnabled: true
                onClicked:
                    thermalViewSelector.viewModeRequested(
                        controller.thermalViewFans
                    )
            }

            RectangularShadow {
                anchors.fill: parent
                spread: 5
                z: -1
                opacity: fanButton.hovered || fanButton.selected ? 0.70 : 0.50
                color: fanButton.stateColor
            }
        }
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Colors.orange
        RectangularShadow {
            anchors.fill: parent
            spread: 2
            z: -1
            opacity: 0.26
            color: Colors.orange
        }
    }
}
