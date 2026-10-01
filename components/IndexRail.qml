import QtQuick
import Qt5Compat.GraphicalEffects

Item {
    id: rail

    property int count: 0
    property int currentIndex: -1
    property color accentColor: Colors.cyan
    property string sideLabel: ""
    property bool enabledRail: count > 1

    signal indexRequested(int index)

    function clampedIndex(value) {
        if (count <= 0)
            return -1;

        return Math.max(0, Math.min(count - 1, Number(value || 0)));
    }

    function indexFromY(yValue) {
        if (count <= 1)
            return 0;

        const usable = Math.max(1, height - 30);
        const clampedY = Math.max(15, Math.min(height - 15, yValue));
        const fraction = (clampedY - 15) / usable;

        return clampedIndex(Math.round(fraction * (count - 1)));
    }

    function handleY() {
        if (count <= 1 || currentIndex < 0)
            return 15;

        const usable = Math.max(1, height - 30);
        return 15 + usable * clampedIndex(currentIndex) / (count - 1);
    }

    width: 14

    Rectangle {
        width: 2
        anchors {
            top: parent.top
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
            topMargin: 12
            bottomMargin: 12
        }

        color: rail.accentColor
        opacity: rail.enabledRail ? 0.58 : 0.18

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: rail.enabledRail ? 0.35 : 0.10
            color: rail.accentColor
            transparentBorder: true
        }
    }

    Repeater {
        model: Math.min(rail.count, 11)

        Rectangle {
            width: index % 5 === 0 ? 8 : 5
            height: 1
            x: (rail.width - width) / 2
            y: rail.count <= 1
               ? rail.height / 2
               : 15
                 + (rail.height - 30)
                   * index
                   / Math.max(1, Math.min(rail.count, 11) - 1)

            color: rail.accentColor
            opacity: 0.38
        }
    }

    Rectangle {
        id: handle

        width: 12
        height: 28
        radius: 2
        anchors.horizontalCenter: parent.horizontalCenter
        y: rail.handleY() - height / 2

        color: Colors.black
        border.width: 1
        border.color: rail.accentColor
        opacity: rail.count > 0 ? 1.0 : 0.28

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 7
            samples: 9
            opacity: rail.enabledRail ? 0.68 : 0.18
            color: rail.accentColor
            transparentBorder: true
        }

        Column {
            anchors.centerIn: parent
            spacing: 3

            Repeater {
                model: 3

                Rectangle {
                    width: 6
                    height: 1
                    color: rail.accentColor
                    opacity: 0.82
                }
            }
        }

        Behavior on y {
            enabled: !dragArea.pressed

            NumberAnimation {
                duration: 90
                easing.type: Easing.OutQuad
            }
        }
    }

    MouseArea {
        id: dragArea

        anchors.fill: parent
        enabled: rail.count > 0
        hoverEnabled: true
        cursorShape: rail.enabledRail ? Qt.SizeVerCursor : Qt.ArrowCursor

        onPressed: function(mouse) {
            const index = rail.indexFromY(mouse.y);
            if (index >= 0)
                rail.indexRequested(index);
        }

        onPositionChanged: function(mouse) {
            if (!pressed)
                return;

            const index = rail.indexFromY(mouse.y);
            if (index >= 0 && index !== rail.currentIndex)
                rail.indexRequested(index);
        }

        onWheel: function(wheel) {
            if (!rail.enabledRail)
                return;

            const step = wheel.angleDelta.y > 0 ? -1 : 1;
            const base = rail.currentIndex >= 0 ? rail.currentIndex : 0;
            const index = rail.clampedIndex(base + step);

            if (index !== rail.currentIndex)
                rail.indexRequested(index);

            wheel.accepted = true;
        }
    }

    GohuText {
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: -1
        }

        rotation: -90
        text: rail.sideLabel
        font.pixelSize: 7
        color: rail.accentColor
        opacity: 0.70
    }
}
