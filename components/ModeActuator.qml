import QtQuick
import QtQuick.Effects

Rectangle {
    id: actuator

    property string icon: "⏭"
    property string tag: "FF"
    property bool enabledAction: true
    property bool active: true
    property color modeColor: Colors.magenta

    signal triggered()

    width: 52
    height: 40
    radius: 2

    readonly property bool hovered:
        enabledAction && mouse.containsMouse

    readonly property bool pressed:
        enabledAction && mouse.pressed

    color:
        pressed
        ? Colors.magenta
        : active
        ? Colors.yellow
        : hovered
        ? Colors.yellow
        : Colors.black

    border.width: 1
    border.color:
        pressed
        ? Colors.magenta
        : active
        ? Colors.orange
        : hovered
        ? Colors.orange
        : Colors.cyan

    RectangularShadow {
        anchors.fill: parent
        spread: actuator.pressed ? 2 : 4
        z: -1
        opacity:
            actuator.pressed
            ? 0.42
            : actuator.active
            ? 0.32
            : actuator.hovered
            ? 0.34
            : 0.16
        color:
            actuator.pressed
            ? Colors.magenta
            : actuator.active || actuator.hovered
            ? Colors.orange
            : Colors.cyan
    }

    Column {
        anchors.centerIn: parent
        anchors.verticalCenterOffset: 2
        spacing: -2

        NotoText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: actuator.icon
            font.pixelSize: 21
            color:
                actuator.pressed
                ? Colors.black
                : actuator.active
                ? actuator.modeColor
                : Colors.white
        }

        GohuText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: actuator.tag
            font.pixelSize: 10
            color:
                actuator.pressed
                ? Colors.black
                : actuator.active
                ? actuator.modeColor
                : Colors.white
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: actuator.enabledAction
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

        onClicked: actuator.triggered()
    }
}
