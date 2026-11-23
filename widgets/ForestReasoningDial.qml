import QtQuick
import "../components"
import "ForestReasoningDialPolicy.js" as ReasoningPolicy

// Forest-local, four-position rotary selector, not an inference permission.
// Drag/click/wheel/keyboard request discrete indices; none of them animate
// through intermediate angles. The 15-degree gap centered at bottom is dead.
Item {
    id: root

    width: 30
    height: 30
    property int stepIndex: 0
    property bool interactive: true
    signal stepRequested(int nextStep)

    readonly property string stepLabel:
        ReasoningPolicy.labelForStep(stepIndex)
    readonly property real snappedAngle:
        ReasoningPolicy.angleForStep(stepIndex)

    activeFocusOnTab: interactive
    Accessible.role: Accessible.Slider
    Accessible.name: "Reasoning // " + stepLabel
    Accessible.description:
        "Four-position local reasoning preference: NONE, LOW, MED, HIGH. No trusted inference host is connected."

    function requestStep(value) {
        var next = ReasoningPolicy.clampStep(value);
        if (interactive && next !== stepIndex)
            stepRequested(next);
    }

    function requestPoint(x, y) {
        if (!interactive)
            return;
        var next = ReasoningPolicy.stepFromPoint(x, y, width, height);
        if (next >= 0)
            requestStep(next);
    }

    Rectangle {
        id: dialBody
        anchors.fill: parent
        radius: width / 2
        color: Colors.dark
        border.width: 2
        border.color: root.activeFocus ? Colors.blue : Colors.cyan
    }

    Repeater {
        model: 4
        delegate: Item {
            anchors.fill: parent
            rotation: ReasoningPolicy.angleForStep(index)
            Rectangle {
                anchors.top: parent.top
                anchors.topMargin: 2
                anchors.horizontalCenter: parent.horizontalCenter
                width: 2
                height: 3
                color: index === root.stepIndex ? Colors.orange : Colors.cyan
            }
        }
    }

    // Only the chosen detent angle is rendered, never a drag-time float.
    Item {
        anchors.fill: parent
        rotation: root.snappedAngle
        Rectangle {
            anchors.top: parent.top
            anchors.topMargin: 5
            anchors.horizontalCenter: parent.horizontalCenter
            width: 3
            height: 7
            radius: 1
            color: Colors.orange
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 22
        height: 13
        radius: 2
        color: Colors.dark
    }
    GohuText {
        anchors.centerIn: parent
        text: root.stepLabel
        textFormat: Text.PlainText
        font.pixelSize: 8
        font.bold: true
        color: Colors.cyan
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.interactive
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton
        onPressed: function(mouse) {
            root.forceActiveFocus();
            root.requestPoint(mouse.x, mouse.y);
        }
        onPositionChanged: function(mouse) {
            if (pressed)
                root.requestPoint(mouse.x, mouse.y);
        }
        onWheel: function(wheel) {
            if (ReasoningPolicy.stepFromPoint(
                    wheel.x, wheel.y, root.width, root.height) < 0)
                return;
            if (wheel.angleDelta.y !== 0) {
                root.requestStep(root.stepIndex + (wheel.angleDelta.y > 0 ? 1 : -1));
                wheel.accepted = true;
            }
        }
    }

    Keys.onLeftPressed: function(event) {
        root.requestStep(root.stepIndex - 1);
        event.accepted = true;
    }
    Keys.onDownPressed: function(event) {
        root.requestStep(root.stepIndex - 1);
        event.accepted = true;
    }
    Keys.onRightPressed: function(event) {
        root.requestStep(root.stepIndex + 1);
        event.accepted = true;
    }
    Keys.onUpPressed: function(event) {
        root.requestStep(root.stepIndex + 1);
        event.accepted = true;
    }
}
