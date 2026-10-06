import QtQuick
import QtQuick.Effects

Item {
    id: root

    property var flickable: null
    property int minimumHandleHeight: 24
    property int wheelStep: 42
    property bool starHandle: false

    parent:
        flickable && flickable.parent
        ? flickable.parent
        : null

    width: starHandle ? 16 : 10
    height:
        flickable
        ? flickable.height
        : 0

    x:
        flickable
        ? flickable.x
          + flickable.width
          - width
          - 2
        : 0

    y:
        flickable
        ? flickable.y
        : 0

    z: 1000

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

    readonly property real scrollRatio:
        maxContentY > 0 && flickable
        ? Math.max(
            0,
            Math.min(
                1,
                flickable.contentY / maxContentY
            )
          )
        : 0

    function normalHandleHeight() {
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

    function activeHandleExtent() {
        return root.starHandle
            ? 14
            : root.normalHandleHeight();
    }

    function handleY() {
        const extent = root.activeHandleExtent();

        return root.scrollRatio
            * Math.max(
                0,
                root.height - extent
              );
    }

    function scrollTo(mouseY) {
        if (!flickable)
            return;

        const extent = root.activeHandleExtent();
        const travel = Math.max(
            0,
            root.height - extent
        );
        const target =
            Number(mouseY || 0)
            - extent / 2;

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

        width: 3
        anchors {
            top: parent.top
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
        }

        radius: 1
        color: Colors.cyan
        opacity: 0.82

        RectangularShadow {
            anchors.fill: parent
            z: -1
            spread: 2
            opacity: 0.24
            color: Colors.cyan
        }
    }

    Rectangle {
        id: normalHandle

        visible: !root.starHandle

        width: 7
        height: root.normalHandleHeight()
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
            opacity:
                handleMouse.containsMouse
                ? 0.60
                : 0.42
            color: Colors.magenta
        }
    }

    Item {
        id: starHandleItem

        visible: root.starHandle

        width: 14
        height: 14
        x: (root.width - width) / 2
        y: root.handleY()

        Canvas {
            id: starCanvas

            anchors.fill: parent
            antialiasing: true

            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                ctx.clearRect(0, 0, width, height);

                const cx = width / 2;
                const cy = height / 2;
                const outer = 6.2;
                const inner = 2.8;

                ctx.beginPath();

                for (let i = 0; i < 10; ++i) {
                    const radius =
                        i % 2 === 0
                        ? outer
                        : inner;
                    const angle =
                        -Math.PI / 2
                        + i * Math.PI / 5;
                    const px =
                        cx + Math.cos(angle) * radius;
                    const py =
                        cy + Math.sin(angle) * radius;

                    if (i === 0)
                        ctx.moveTo(px, py);
                    else
                        ctx.lineTo(px, py);
                }

                ctx.closePath();
                ctx.fillStyle =
                    Colors.magenta.toString();
                ctx.strokeStyle =
                    Colors.magenta.toString();
                ctx.lineWidth = 1;
                ctx.fill();
                ctx.stroke();
            }
        }

        RectangularShadow {
            anchors.fill: parent
            z: -1
            spread: handleMouse.containsMouse ? 5 : 3
            opacity:
                handleMouse.containsMouse
                ? 0.72
                : 0.52
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
