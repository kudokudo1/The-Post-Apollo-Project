import QtQuick
import QtQuick.Effects

Rectangle {
    id: slider

    property int count: 0
    property int currentIndex: -1
    property color accentColor: Colors.cyan
    property color handleColor: Colors.white
    property color handleGlowColor: Colors.magenta
    property string sideLabel: ""
    property bool enabledSlider: count > 1

    signal indexRequested(int index)

    width: 40
    radius: 2
    color: "#09070D"
    border.width: 1
    border.color: accentColor

    RectangularShadow {
        anchors.fill: parent
        spread: 4
        z: -2
        opacity: slider.enabledSlider ? 0.22 : 0.08
        color: slider.accentColor
    }

    Rectangle {
        anchors.fill: parent
        anchors.margins: 3
        radius: 2
        color: "#120E16"
        border.width: 1
        border.color: "#322739"
    }

    function clampedIndex(value) {
        if (count <= 0)
            return -1;

        return Math.max(0, Math.min(count - 1, Number(value || 0)));
    }

    function handleTravel() {
        return Math.max(0, slot.height - thumb.height);
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
            topMargin: 13
        }

        rotation: -90
        transformOrigin: Item.Center
        text: slider.sideLabel
        font.pixelSize: 8
        color: slider.accentColor
        opacity: 0.94
    }

    Item {
        id: scaleArea

        anchors {
            top: parent.top
            bottom: parent.bottom
            left: parent.left
            right: parent.right
            topMargin: 38
            bottomMargin: 26
            leftMargin: 4
            rightMargin: 4
        }

        Repeater {
            model: Math.min(slider.count, 13)

            Item {
                width: scaleArea.width
                height: 1
                y:
                    slider.count <= 1
                    ? scaleArea.height / 2
                    : (
                        scaleArea.height - 1
                      ) * index
                        / Math.max(
                            1,
                            Math.min(slider.count, 13) - 1
                        )

                Rectangle {
                    width: index % 4 === 0 ? 8 : 5
                    height: 1
                    anchors.left: parent.left
                    color: slider.accentColor
                    opacity: index % 4 === 0 ? 0.68 : 0.32
                }

                Rectangle {
                    width: index % 4 === 0 ? 8 : 5
                    height: 1
                    anchors.right: parent.right
                    color: slider.accentColor
                    opacity: index % 4 === 0 ? 0.68 : 0.32
                }
            }
        }

        Rectangle {
            id: slot

            width: 12
            anchors {
                top: parent.top
                bottom: parent.bottom
                horizontalCenter: parent.horizontalCenter
            }

            radius: 6
            color: "#030205"
            border.width: 1
            border.color: "#35283D"

            RectangularShadow {
                anchors.fill: parent
                spread: 2
                z: -1
                opacity: 0.30
                color: Colors.black
            }

            Rectangle {
                width: 2
                anchors {
                    top: parent.top
                    bottom: parent.bottom
                    horizontalCenter: parent.horizontalCenter
                    topMargin: 6
                    bottomMargin: 6
                }

                color: slider.accentColor
                opacity: slider.count > 0 ? 0.48 : 0.14
            }

            Rectangle {
                id: thumb

                width: 28
                height: 52
                radius: 3
                anchors.horizontalCenter: parent.horizontalCenter

                y: slider.handleYForIndex()

                scale: dragArea.pressed ? 0.97 : 1.0
                color: dragArea.pressed ? Colors.yellow : Colors.white
                border.width: 1
                border.color: dragArea.pressed
                              ? Colors.orange
                              : Colors.white

                RectangularShadow {
                    anchors.fill: parent
                    spread: dragArea.pressed ? 3 : 5
                    z: -2
                    opacity: dragArea.pressed ? 0.42 : 0.62
                    color: dragArea.pressed
                           ? Colors.orange
                           : slider.handleGlowColor
                }

                Rectangle {
                    anchors {
                        left: parent.left
                        right: parent.right
                        top: parent.top
                    }

                    anchors.leftMargin: 3
                    anchors.rightMargin: 3
                    anchors.topMargin: 3
                    height: 2
                    radius: 1
                    color: dragArea.pressed ? Colors.black : Colors.white
                    opacity: 0.48
                }

                Rectangle {
                    anchors {
                        left: parent.left
                        right: parent.right
                        bottom: parent.bottom
                    }

                    anchors.leftMargin: 3
                    anchors.rightMargin: 3
                    anchors.bottomMargin: 3
                    height: 3
                    radius: 1
                    color: Colors.black
                    opacity: 0.72
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 4

                    Repeater {
                        model: 5

                        Rectangle {
                            width: 16
                            height: 2
                            radius: 1
                            color: dragArea.pressed
                                   ? Colors.black
                                   : Colors.black
                            opacity: 0.58
                        }
                    }
                }

                Behavior on y {
                    enabled: !dragArea.pressed

                    NumberAnimation {
                        duration: 110
                        easing.type: Easing.OutBack
                        easing.overshoot: 0.7
                    }
                }

                Behavior on scale {
                    NumberAnimation {
                        duration: 70
                        easing.type: Easing.OutQuad
                    }
                }
            }

            MouseArea {
                id: dragArea

                anchors {
                    top: parent.top
                    bottom: parent.bottom
                    horizontalCenter: parent.horizontalCenter
                }

                width: slider.width
                enabled: slider.count > 0
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                cursorShape: slider.enabledSlider
                             ? Qt.SizeVerCursor
                             : Qt.ArrowCursor

                property real dragOffset: 0

                onPressed: function(mouse) {
                    const localY = mapToItem(slot, mouse.x, mouse.y).y;
                    const handleTop = thumb.y;
                    const handleBottom = thumb.y + thumb.height;

                    dragOffset =
                        localY >= handleTop
                        && localY <= handleBottom
                        ? localY - handleTop
                        : thumb.height / 2;

                    const index = slider.indexFromHandleY(
                        localY - dragOffset
                    );

                    if (index >= 0 && index !== slider.currentIndex)
                        slider.indexRequested(index);
                }

                onPositionChanged: function(mouse) {
                    if (!pressed)
                        return;

                    const localY = mapToItem(slot, mouse.x, mouse.y).y;
                    const index = slider.indexFromHandleY(
                        localY - dragOffset
                    );

                    if (index >= 0 && index !== slider.currentIndex)
                        slider.indexRequested(index);
                }

                onWheel: function(wheel) {
                    if (!slider.enabledSlider)
                        return;

                    const step = wheel.angleDelta.y > 0 ? -1 : 1;
                    const base = slider.currentIndex >= 0
                        ? slider.currentIndex
                        : 0;
                    const index = slider.clampedIndex(base + step);

                    if (index !== slider.currentIndex)
                        slider.indexRequested(index);

                    wheel.accepted = true;
                }
            }
        }
    }

    GohuText {
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 8
        }

        text:
            slider.currentIndex >= 0
            ? String(slider.currentIndex + 1)
            : "—"
        font.pixelSize: 8
        color: slider.accentColor
        opacity: 0.72
    }
}
