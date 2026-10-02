import QtQuick
import QtQuick.Effects

Item {
    id: dialRoot

    property string labelText: "SELECT"
    property var options: []
    property var displayOptions: []
    property int currentIndex: 0
    property string readoutText: selectedValue ? selectedValue.toUpperCase() : ""
    property bool interactive: options && options.length > 1

    property color accentColor: Colors.cyan
    property color markerColor: Colors.orange
    property color labelColor: Colors.cyan

    readonly property string selectedValue:
        options && options.length > 0 && currentIndex >= 0 && currentIndex < options.length
        ? String(options[currentIndex])
        : ""

    property real visualAngle: -90
    property bool dragging: false
    property real lastPointerAngle: 0
    property int dragDetentIndex: -1

    signal selectionRequested(int index, string value)

    width: 136
    height: 160
    activeFocusOnTab: true

    function optionCount() {
        return options ? options.length : 0;
    }

    function normalizedIndex(index) {
        const count = optionCount();

        if (count <= 0)
            return 0;

        return ((Number(index) % count) + count) % count;
    }

    function angleForIndex(index) {
        const count = optionCount();

        if (count <= 1)
            return -90;

        return -90 + (360 * normalizedIndex(index) / count);
    }

    function nearestEquivalent(angle, reference) {
        let candidate = Number(angle);
        const anchor = Number(reference);

        while (candidate - anchor > 180)
            candidate -= 360;

        while (candidate - anchor < -180)
            candidate += 360;

        return candidate;
    }

    function indexForAngle(angle) {
        const count = optionCount();

        if (count <= 1)
            return 0;

        const step = 360 / count;
        let wrapped = (Number(angle) + 90) % 360;

        if (wrapped < 0)
            wrapped += 360;

        return normalizedIndex(Math.round(wrapped / step));
    }

    function pointerAngle(x, y, widthValue, heightValue) {
        return Math.atan2(
            Number(y) - Number(heightValue) / 2,
            Number(x) - Number(widthValue) / 2
        ) * 180 / Math.PI;
    }

    function normalizeDelta(delta) {
        let value = Number(delta);

        while (value > 180)
            value -= 360;

        while (value < -180)
            value += 360;

        return value;
    }

    function optionDisplay(index) {
        if (displayOptions
                && displayOptions.length === optionCount()
                && index >= 0
                && index < displayOptions.length)
            return String(displayOptions[index]);

        if (!options || index < 0 || index >= options.length)
            return "";

        return String(options[index]).toUpperCase();
    }

    function requestIndex(index) {
        const count = optionCount();

        if (count <= 0)
            return;

        const next = normalizedIndex(index);

        selectionRequested(next, String(options[next]));

        if (!dragging)
            visualAngle = nearestEquivalent(angleForIndex(next), visualAngle);
    }

    function stepIndex(delta) {
        if (!interactive)
            return;

        requestIndex(currentIndex + Number(delta));
    }

    function snapToCurrent() {
        if (optionCount() <= 0)
            return;

        visualAngle = nearestEquivalent(angleForIndex(currentIndex), visualAngle);
    }

    onCurrentIndexChanged: {
        if (!dragging)
            snapToCurrent();
    }

    onOptionsChanged: {
        if (!dragging)
            snapToCurrent();
    }

    Component.onCompleted: snapToCurrent()

    Keys.onLeftPressed: function(event) {
        stepIndex(-1);
        event.accepted = true;
    }

    Keys.onDownPressed: function(event) {
        stepIndex(-1);
        event.accepted = true;
    }

    Keys.onRightPressed: function(event) {
        stepIndex(1);
        event.accepted = true;
    }

    Keys.onUpPressed: function(event) {
        stepIndex(1);
        event.accepted = true;
    }

    Behavior on visualAngle {
        enabled: !dialRoot.dragging

        NumberAnimation {
            duration: 135
            easing.type: Easing.OutBack
            easing.overshoot: 0.8
        }
    }

    GohuText {
        anchors {
            top: parent.top
            horizontalCenter: parent.horizontalCenter
        }

        text: dialRoot.labelText
        font.pixelSize: 10
        color: Colors.magenta

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Colors.magenta
            shadowOpacity: 0.42
            shadowBlur: 0.45
        }
    }

    Item {
        id: dialStage

        anchors {
            top: parent.top
            topMargin: 18
            horizontalCenter: parent.horizontalCenter
        }

        width: 116
        height: 116

        // Deep dock well.
        Rectangle {
            anchors.centerIn: parent
            width: 106
            height: 106
            radius: 53
            color: "#060108"

            border {
                width: 2
                color: "#332238"
            }
        }

        // Offset lower-right layer makes the hardware stand proud of the dock.
        Rectangle {
            x: 10
            y: 12
            width: 94
            height: 94
            radius: 47
            color: "#09060D"

            border {
                width: 1
                color: "#211827"
            }
        }

        // Raised surrounding ring.
        Rectangle {
            anchors.centerIn: parent
            width: 98
            height: 98
            radius: 49
            color: "#121018"

            border {
                width: 1
                color: "#49414F"
            }
        }

        Rectangle {
            id: modeBody

            anchors.centerIn: parent
            width: 90
            height: 90
            radius: 45
            color: "#19171F"
            clip: true

            border {
                width: 1
                color: "#3D3746"
            }

            Rectangle {
                anchors {
                    left: parent.left
                    right: parent.right
                    top: parent.top
                    leftMargin: 14
                    rightMargin: 14
                    topMargin: 4
                }

                height: 2
                radius: 1
                color: "#5E5867"
                opacity: 0.42
            }

            // Deterministic molded-plastic grain. It is deliberately static.
            Canvas {
                anchors.fill: parent
                opacity: 0.12

                function hash(n) {
                    const value = Math.sin(n * 12.9898 + 78.233) * 43758.5453;
                    return value - Math.floor(value);
                }

                onPaint: {
                    const ctx = getContext("2d");
                    ctx.reset();

                    for (let y = 2; y < height - 2; y += 4) {
                        for (let x = 2; x < width - 2; x += 4) {
                            const seed = ((x * 73856093) ^ (y * 19349663)) >>> 0;
                            const r = (seed % 1000) / 1000.0;

                            if (r < 0.085) {
                                ctx.fillStyle = ((seed >> 5) & 1) === 1
                                    ? "#FFFFFF"
                                    : "#000000";
                                ctx.globalAlpha = 0.20 + (((seed >> 10) % 35) / 170.0);
                                ctx.fillRect(x + (seed % 2), y + ((seed >> 2) % 2), 1, 1);
                            }
                        }
                    }

                    ctx.globalAlpha = 1.0;
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 72
                height: 72
                radius: 36
                color: "transparent"

                border {
                    width: 2
                    color: dialRoot.accentColor
                }
            }

            // Slightly recessed center plate.
            Rectangle {
                x: (parent.width - 35) / 2 + 2
                y: (parent.height - 35) / 2 + 3
                width: 35
                height: 35
                radius: 17.5
                color: "#09060C"

                border {
                    width: 1
                    color: "#18121C"
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 33
                height: 33
                radius: 16.5
                color: "#28232D"

                border {
                    width: 1
                    color: "#5B5361"
                }

                Rectangle {
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                        leftMargin: 8
                        rightMargin: 8
                        topMargin: 4
                    }

                    height: 2
                    radius: 1
                    color: "#77717D"
                    opacity: 0.46
                }
            }

            Rectangle {
                anchors.centerIn: parent
                width: 17
                height: 17
                radius: 8.5
                color: Colors.white

                border {
                    width: 1
                    color: "#A0B2B7"
                }
            }

            // Full-diameter physical selector handle.
            Item {
                id: selectorHandle

                anchors.centerIn: parent
                width: 78
                height: 11
                transformOrigin: Item.Center
                rotation: dialRoot.visualAngle

                Rectangle {
                    x: 3
                    y: 4
                    width: 72
                    height: 7
                    color: "#78858A"
                }

                Rectangle {
                    x: 3
                    y: 1
                    width: 72
                    height: 7
                    color: Colors.white

                    border {
                        width: 1
                        color: "#B8C8CC"
                    }
                }

                Rectangle {
                    id: selectorHead

                    x: 67
                    y: 2
                    width: 5
                    height: 5
                    color: dialRoot.markerColor

                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: dialRoot.markerColor
                        shadowOpacity: 0.74
                        shadowBlur: 0.62
                    }
                }
            }
        }

        // Each printed position is itself a direct-jump control.
        Repeater {
            model: dialRoot.optionCount()

            delegate: Item {
                id: optionMark

                required property int index

                readonly property real labelAngle: dialRoot.angleForIndex(index)
                readonly property real labelRadius: 48
                readonly property real radians: labelAngle * Math.PI / 180

                width: 38
                height: 16

                x: dialStage.width / 2
                   + Math.cos(radians) * labelRadius
                   - width / 2
                y: dialStage.height / 2
                   + Math.sin(radians) * labelRadius
                   - height / 2

                GohuText {
                    anchors.centerIn: parent
                    text: dialRoot.optionDisplay(index)
                    font.pixelSize: dialRoot.optionCount() > 4 ? 6 : 7
                    color: index === dialRoot.currentIndex
                           ? dialRoot.markerColor
                           : dialRoot.labelColor

                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: optionMark.index === dialRoot.currentIndex
                                     ? dialRoot.markerColor
                                     : dialRoot.labelColor
                        shadowOpacity:
                            optionMark.index === dialRoot.currentIndex
                            ? 0.92
                            : 0.22
                        shadowBlur:
                            optionMark.index === dialRoot.currentIndex
                            ? 0.72
                            : 0.28
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: dialRoot.interactive
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onClicked: {
                        dialRoot.forceActiveFocus();
                        dialRoot.requestIndex(optionMark.index);
                    }
                }
            }
        }

        MouseArea {
            id: rotaryMouse

            anchors.centerIn: parent
            width: 90
            height: 90

            enabled: dialRoot.interactive
            hoverEnabled: true
            acceptedButtons: Qt.LeftButton
            cursorShape: dialRoot.dragging
                         ? Qt.ClosedHandCursor
                         : Qt.OpenHandCursor

            onPressed: function(mouse) {
                dialRoot.forceActiveFocus();
                dialRoot.dragging = true;
                dialRoot.dragDetentIndex = dialRoot.currentIndex;
                dialRoot.lastPointerAngle = dialRoot.pointerAngle(
                    mouse.x,
                    mouse.y,
                    width,
                    height
                );
            }

            onPositionChanged: function(mouse) {
                if (!pressed || !dialRoot.dragging)
                    return;

                const cx = mouse.x - width / 2;
                const cy = mouse.y - height / 2;
                const radius = Math.sqrt(cx * cx + cy * cy);

                // A real rotary gesture loses leverage at the axle. Ignore the
                // center dead-zone instead of turning a straight drag into a slider.
                if (radius < 15)
                    return;

                const angle = dialRoot.pointerAngle(mouse.x, mouse.y, width, height);
                const delta = dialRoot.normalizeDelta(angle - dialRoot.lastPointerAngle);

                dialRoot.visualAngle += delta;
                dialRoot.lastPointerAngle = angle;

                const detent = dialRoot.indexForAngle(dialRoot.visualAngle);

                if (detent !== dialRoot.dragDetentIndex) {
                    dialRoot.dragDetentIndex = detent;
                    dialRoot.selectionRequested(detent, String(dialRoot.options[detent]));
                }
            }

            onReleased: {
                dialRoot.dragging = false;
                dialRoot.snapToCurrent();
            }

            onCanceled: {
                dialRoot.dragging = false;
                dialRoot.snapToCurrent();
            }

            onWheel: function(wheel) {
                if (wheel.angleDelta.y === 0)
                    return;

                dialRoot.forceActiveFocus();
                dialRoot.stepIndex(wheel.angleDelta.y > 0 ? -1 : 1);
                wheel.accepted = true;
            }
        }

        // Focus ring is intentionally subtle; it only appears for keyboard use.
        Rectangle {
            anchors.centerIn: parent
            width: 110
            height: 110
            radius: 55
            color: "transparent"
            border.width: dialRoot.activeFocus ? 1 : 0
            border.color: Colors.magenta
            opacity: dialRoot.activeFocus ? 0.72 : 0.0
        }
    }

    GohuText {
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 1
        }

        width: parent.width - 6
        text: dialRoot.readoutText
        horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
        font.pixelSize: 8
        color: dialRoot.interactive ? Colors.white : Colors.orange
        opacity: dialRoot.interactive ? 0.82 : 0.72
    }
}
