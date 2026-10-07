import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects
import "../../components"

Item {
    id: fanSafetyLock

    required property var controller
    property var sensor: null
    readonly property bool unlocked:
        sensor ? controller.fanControlUnlocked(sensor) : false

    signal toggled()

    width: 30
    height: 26
    z: 50
    visible: sensor !== null

    Rectangle {
        anchors.fill: parent
        anchors.margins: 3
        color: Colors.black
        opacity: 0.96
        border.width: 1
        border.color: Colors.omnitrix

        RectangularShadow {
            anchors.fill: parent
            anchors.margins: -3
            spread: 3
            z: -1
            opacity: fanMouse.containsMouse ? 0.42 : 0.22
            color: Colors.omnitrix
        }

        GohuText {
            anchors.centerIn: parent
            text: fanSafetyLock.unlocked ? "☍" : ""
            font.pixelSize: fanSafetyLock.unlocked ? 15 : 12
            color: Colors.omnitrix
            layer.enabled: Window.window !== null
            layer.effect: DropShadow {
                radius: 4
                samples: 5
                opacity: 0.42
                color: Colors.omnitrix
                transparentBorder: true
            }
        }
    }

    MouseArea {
        id: fanMouse
        anchors.fill: parent
        hoverEnabled: true
        onClicked: {
            if (fanSafetyLock.sensor) {
                fanSafetyLock.controller.toggleFanControlUnlocked(
                    fanSafetyLock.sensor
                );
                fanSafetyLock.toggled();
            }
        }
    }
}
