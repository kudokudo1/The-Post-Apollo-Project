import QtQuick
import QtQuick.Effects

Rectangle {
    id: actuator

    property string icon: "⏭"
    property string tag: "FF"
    property bool enabledAction: true
    property bool discovered: false
    property color accentColor: Colors.magenta

    signal triggered()

    width: 44
    height: 36
    radius: 2

    readonly property bool hovered:
        enabledAction && mouse.containsMouse

    readonly property bool pressed:
        enabledAction && mouse.pressed

    property int pulsePhase: 0

    readonly property color pulseColor:
        discovered
        ? accentColor
        : pulsePhase === 0
        ? Colors.magenta
        : pulsePhase === 1
        ? Colors.orange
        : Colors.cyan

    color:
        pressed
        ? Colors.yellow
        : hovered
        ? Colors.dark
        : Colors.black

    border.width: 1
    border.color: pulseColor

    RectangularShadow {
        anchors.fill: parent
        spread: actuator.pressed ? 2 : 5
        z: -1
        opacity:
            actuator.pressed
            ? 0.30
            : actuator.hovered
            ? 0.58
            : actuator.discovered
            ? 0.34
            : 0.48
        color: actuator.pulseColor
    }

    Column {
        anchors.centerIn: parent
        spacing: -1

        NotoText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: actuator.icon
            font.pixelSize: 15
            color: actuator.pressed ? Colors.black : Colors.white
        }

        GohuText {
            anchors.horizontalCenter: parent.horizontalCenter
            text: actuator.tag
            font.pixelSize: 7
            color: actuator.pressed ? Colors.black : actuator.pulseColor
        }
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        enabled: actuator.enabledAction
        hoverEnabled: true
        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

        onClicked: {
            actuator.discovered = true;
            actuator.triggered();
        }
    }

    Timer {
        interval: 520
        repeat: true
        running: actuator.visible && !actuator.discovered

        onTriggered:
            actuator.pulsePhase = (actuator.pulsePhase + 1) % 3
    }
}
