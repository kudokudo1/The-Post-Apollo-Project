import QtQuick
import QtQuick.Effects

Item {
    id: root

    // Scroll target.
    property var flickable: null

    // Geometry.
    property int barAreaWidth: 10
    property int starAreaWidth: 16
    property int railWidth: 3
    property int barHandleWidth: 7
    property int minimumHandleHeight: 24
    property int starHandleSize: 14

    property int topInset: 0
    property int bottomInset: 0
    property int rightInset: 2
    property int trackTopExtension: 0

    // One component, switchable handle form.
    // Unknown values intentionally fall back to the normal bar.
    property string handleStyle: "bar"
    readonly property bool starStyle:
        String(root.handleStyle || "").toLowerCase() === "star"

    // Interaction.
    property int wheelStep: 42
    property bool interactive: true
    property bool wheelEnabled: true
    property bool clickToJump: true
    property bool autoHide: true
    property real scrollThreshold: 1

    // Rail appearance.
    property color railColor: Colors.cyan
    property real railOpacity: 0.82
    property real railRadius: 1
    property int railBorderWidth: 0
    property color railBorderColor: railColor
    property bool railGlowEnabled: true
    property real railGlowSpread: 2
    property real railGlowOpacity: 0.24

    // Handle appearance.
    property color handleColor: Colors.magenta
    property real handleOpacity: 1.0
    property real barHandleRadius: 2
    property int handleBorderWidth: 1
    property color handleBorderColor: handleColor
    property bool handleGlowEnabled: true

    // Normal bar glow.
    property real barGlowIdleSpread: 2
    property real barGlowHoverSpread: 4
    property real barGlowIdleOpacity: 0.42
    property real barGlowHoverOpacity: 0.60

    // Star glow.
    property real starGlowIdleSpread: 3
    property real starGlowHoverSpread: 5
    property real starGlowIdleOpacity: 0.52
    property real starGlowHoverOpacity: 0.72

    // Star geometry.
    property real starOuterRadius: starHandleSize * 0.443
    property real starInnerRadius: starHandleSize * 0.20
    property real starLineWidth: 1

    // Optional overlay for semantic markers/ticks/activity points.
    property Component railDecoration: null

    property alias railItem: rail
    property alias handleItem: handleLoader

    parent:
        flickable && flickable.parent
        ? flickable.parent
        : null

    width: root.starStyle
           ? root.starAreaWidth
           : root.barAreaWidth

    height:
        flickable
        ? Math.max(
            0,
            flickable.height
            - root.topInset
            - root.bottomInset
          )
        : 0

    x:
        flickable
        ? flickable.x
          + flickable.width
          - width
          - root.rightInset
        : 0

    y:
        flickable
        ? flickable.y + root.topInset
        : 0

    z: 1000

    readonly property bool scrollable:
        flickable
        && flickable.contentHeight
           > flickable.height + root.scrollThreshold

    visible:
        flickable
        && (!root.autoHide || root.scrollable)

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
        return root.starStyle
            ? root.starHandleSize
            : root.normalHandleHeight();
    }

    function activeHandleWidth() {
        return root.starStyle
            ? root.starHandleSize
            : root.barHandleWidth;
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
        if (!flickable || !root.interactive)
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

        width: root.railWidth

        anchors {
            top: parent.top
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
            topMargin: -root.trackTopExtension
        }

        radius: root.railRadius
        color: root.railColor
        opacity: root.railOpacity

        border.width: root.railBorderWidth
        border.color: root.railBorderColor

        RectangularShadow {
            anchors.fill: parent
            z: -1

            visible: root.railGlowEnabled
            spread: root.railGlowSpread
            opacity: root.railGlowOpacity
            color: root.railColor
        }

        Loader {
            anchors.fill: parent
            z: 4

            active: root.railDecoration !== null
            sourceComponent: root.railDecoration
        }
    }

    Loader {
        id: handleLoader

        width: root.activeHandleWidth()
        height: root.activeHandleExtent()

        x: (root.width - width) / 2
        y: root.handleY()

        sourceComponent:
            root.starStyle
            ? starHandleComponent
            : barHandleComponent
    }

    Component {
        id: barHandleComponent

        Rectangle {
            anchors.fill: parent

            radius: root.barHandleRadius
            color: root.handleColor
            opacity: root.handleOpacity

            border.width: root.handleBorderWidth
            border.color: root.handleBorderColor

            RectangularShadow {
                anchors.fill: parent
                z: -1

                visible: root.handleGlowEnabled

                spread:
                    handleMouse.containsMouse
                    ? root.barGlowHoverSpread
                    : root.barGlowIdleSpread

                opacity:
                    handleMouse.containsMouse
                    ? root.barGlowHoverOpacity
                    : root.barGlowIdleOpacity

                color: root.handleColor
            }
        }
    }

    Component {
        id: starHandleComponent

        Item {
            anchors.fill: parent
            opacity: root.handleOpacity

            Canvas {
                id: starCanvas

                property color paintColor: root.handleColor
                property real paintOuterRadius: root.starOuterRadius
                property real paintInnerRadius: root.starInnerRadius
                property real paintLineWidth: root.starLineWidth

                anchors.fill: parent
                antialiasing: true

                onPaintColorChanged: requestPaint()
                onPaintOuterRadiusChanged: requestPaint()
                onPaintInnerRadiusChanged: requestPaint()
                onPaintLineWidthChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()

                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();
                    ctx.clearRect(0, 0, width, height);

                    const cx = width / 2;
                    const cy = height / 2;

                    ctx.beginPath();

                    for (let i = 0; i < 10; ++i) {
                        const radius =
                            i % 2 === 0
                            ? paintOuterRadius
                            : paintInnerRadius;
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
                    ctx.fillStyle = paintColor.toString();
                    ctx.strokeStyle = paintColor.toString();
                    ctx.lineWidth = paintLineWidth;
                    ctx.fill();
                    ctx.stroke();
                }
            }

            RectangularShadow {
                anchors.fill: parent
                z: -1

                visible: root.handleGlowEnabled

                spread:
                    handleMouse.containsMouse
                    ? root.starGlowHoverSpread
                    : root.starGlowIdleSpread

                opacity:
                    handleMouse.containsMouse
                    ? root.starGlowHoverOpacity
                    : root.starGlowIdleOpacity

                color: root.handleColor
            }
        }
    }

    MouseArea {
        id: handleMouse

        anchors.fill: parent

        enabled: root.interactive
        hoverEnabled: true
        cursorShape:
            root.interactive
            ? Qt.PointingHandCursor
            : Qt.ArrowCursor

        onPressed: function(mouse) {
            if (root.clickToJump)
                root.scrollTo(mouse.y);
        }

        onPositionChanged: function(mouse) {
            if (pressed)
                root.scrollTo(mouse.y);
        }

        onWheel: function(wheel) {
            if (!root.flickable || !root.wheelEnabled) {
                wheel.accepted = false;
                return;
            }

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
