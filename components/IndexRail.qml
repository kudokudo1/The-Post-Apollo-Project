import QtQuick
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: rail

    property int count: 0
    property int currentIndex: -1
    property color accentColor: Colors.cyan
    property string sideLabel: ""
    property bool enabledRail: count > 1

    signal indexRequested(int index)

    width: 24
    color: Colors.black
    border.width: 1
    border.color: rail.accentColor

    RectangularShadow {
        anchors.fill: parent
        spread: 3
        z: -1
        opacity: rail.enabledRail ? 0.20 : 0.08
        color: rail.accentColor
    }

    function clampedIndex(value) {
        if (count <= 0)
            return -1;

        return Math.max(0, Math.min(count - 1, Number(value || 0)));
    }

    function handleTravel() {
        return Math.max(0, track.height - handle.height);
    }

    function handleYForIndex() {
        if (count <= 1 || currentIndex < 0)
            return 0;

        return handleTravel()
            * clampedIndex(currentIndex)
            / Math.max(1, count - 1);
    }

    function indexFromHandleY(handleY) {
        if (count <= 1)
            return 0;

        const travel = Math.max(1, handleTravel());
        const clampedY = Math.max(0, Math.min(travel, handleY));
        const fraction = clampedY / travel;

        return clampedIndex(Math.round(fraction * (count - 1)));
    }

    GohuText {
        anchors {
            horizontalCenter: parent.horizontalCenter
            top: parent.top
            topMargin: 8
        }

        rotation: -90
        transformOrigin: Item.Center
        text: rail.sideLabel
        font.pixelSize: 7
        color: rail.accentColor
        opacity: 0.82
    }

    Rectangle {
        id: track

        width: 10

        anchors {
            top: parent.top
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
            topMargin: 34
            bottomMargin: 10
        }

        color: rail.accentColor
        opacity: rail.count > 0 ? 0.90 : 0.18

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 4
            samples: 5
            opacity: rail.enabledRail ? 0.30 : 0.08
            color: rail.accentColor
            transparentBorder: true
        }

        Repeater {
            model: Math.min(rail.count, 11)

            Rectangle {
                width: parent.width
                height: 1

                y:
                    rail.count <= 1
                    ? track.height / 2
                    : (
                        track.height - 1
                      ) * index
                        / Math.max(
                            1,
                            Math.min(rail.count, 11) - 1
                        )

                color: Colors.black
                opacity: index % 5 === 0 ? 0.72 : 0.42
            }
        }

        Rectangle {
            id: handle

            width: 6
            anchors.horizontalCenter: parent.horizontalCenter

            height:
                rail.count <= 1
                ? 30
                : Math.max(
                    30,
                    Math.min(
                        58,
                        track.height
                        / Math.max(2, Math.min(rail.count, 12))
                        * 2
                    )
                )

            y: rail.handleYForIndex()

            color: Colors.magenta

            RectangularShadow {
                anchors.fill: parent
                spread: 2
                z: -1
                opacity: 0.46
                color: Colors.magenta
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
            acceptedButtons: Qt.LeftButton
            cursorShape: rail.enabledRail ? Qt.SizeVerCursor : Qt.ArrowCursor

            property real dragOffset: 0

            onPressed: function(mouse) {
                const handleTop = handle.y;
                const handleBottom = handle.y + handle.height;

                dragOffset =
                    mouse.y >= handleTop
                    && mouse.y <= handleBottom
                    ? mouse.y - handleTop
                    : handle.height / 2;

                const index = rail.indexFromHandleY(
                    mouse.y - dragOffset
                );

                if (index >= 0 && index !== rail.currentIndex)
                    rail.indexRequested(index);
            }

            onPositionChanged: function(mouse) {
                if (!pressed)
                    return;

                const index = rail.indexFromHandleY(
                    mouse.y - dragOffset
                );

                if (index >= 0 && index !== rail.currentIndex)
                    rail.indexRequested(index);
            }

            onWheel: function(wheel) {
                if (!rail.enabledRail)
                    return;

                const step = wheel.angleDelta.y > 0 ? -1 : 1;
                const base = rail.currentIndex >= 0
                    ? rail.currentIndex
                    : 0;
                const index = rail.clampedIndex(base + step);

                if (index !== rail.currentIndex)
                    rail.indexRequested(index);

                wheel.accepted = true;
            }
        }
    }
}
