import QtQuick
import QtQuick.Effects

Item {
    id: root

    property var flickable: null
    property int minimumHandleHeight: 24
    property int wheelStep: 42

    width: 10
    z: 100

    visible:
        flickable
        && flickable.contentHeight > flickable.height + 1

    readonly property real maxContentY:
        flickable
        ? Math.max(
            0,
            flickable.contentHeight - flickable.height
          )
        : 0

    function handleHeight() {
        if (!flickable)
            return root.height;

        return Math.max(
            root.minimumHandleHeight,
            root.height
            * Math.min(
                1,
                flickable.height
                / Math.max(flickable.contentHeight, 1)
            )
        );
    }

    function handleY() {
        if (!flickable || root.maxContentY <= 0)
            return 0;

        return (
            flickable.contentY
            / root.maxContentY
        ) * Math.max(
            0,
            root.height - handle.height
        );
    }

    function scrollTo(mouseY) {
        if (!flickable)
            return;

        const travel = Math.max(
            0,
            root.height - handle.height
        );
        const target =
            Number(mouseY || 0)
            - handle.height / 2;

        const ratio =
            travel > 0
            ? Math.max(
                0,
                Math.min(1, target / travel)
              )
            : 0;

        flickable.contentY =
            ratio * root.maxContentY;
    }

    Rectangle {
        id: rail

        width: 5
        anchors {
            top: parent.top
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
        }

        radius: 2
        color: Colors.cyan
        opacity: 0.74
        border.width: 1
        border.color: Colors.cyan

        RectangularShadow {
            anchors.fill: parent
            z: -1
            spread: 2
            opacity: 0.20
            color: Colors.cyan
        }
    }

    Rectangle {
        id: handle

        width: 7
        height: root.handleHeight()
        x: (root.width - width) / 2
        y: root.handleY()
        radius: 2
        color: Colors.magenta
        border.width: 1
        border.color: Colors.magenta

        RectangularShadow {
            anchors.fill: parent
            z: -1
            spread: handleMouse.containsMouse ? 4 : 2
            opacity: handleMouse.containsMouse ? 0.60 : 0.42
            color: Colors.magenta
        }
    }

    MouseArea {
        id: handleMouse

        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onPressed: function(mouse) {
            root.scrollTo(mouse.y);
        }

        onPositionChanged: function(mouse) {
            if (pressed)
                root.scrollTo(mouse.y);
        }

        onWheel: function(wheel) {
            if (!root.flickable)
                return;

            const step =
                wheel.angleDelta.y > 0
                ? -root.wheelStep
                : root.wheelStep;

            root.flickable.contentY =
                Math.max(
                    0,
                    Math.min(
                        root.maxContentY,
                        root.flickable.contentY + step
                    )
                );

            wheel.accepted = true;
        }
    }
}
