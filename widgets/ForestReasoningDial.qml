import QtQuick
import "../components"
import "ForestReasoningDialPolicy.js" as ReasoningPolicy

// A compact viewport for the established Post-Apollo hardware dial.
// The shared SelectorDial owns ALL physical 3D artwork and step animation.
// Forest alone controls sizing, the 15-degree bottom dead-zone and per-Tree
// local-only reasoning preference. No model, voice or session dispatch.
Item {
    id: root

    width: 34
    height: 34
    clip: true
    property int stepIndex: 0
    property bool interactive: true
    signal stepRequested(int nextStep)

    readonly property string stepLabel:
        ReasoningPolicy.labelForStep(stepIndex)
    // The shared hardware's built-in knob center is (68, 76) in its
    // original 136 x 160 coordinates. Scale around that fixed center.
    readonly property real hardwareScale:
        Math.min(width, height) / 116

    activeFocusOnTab: interactive
    Accessible.role: Accessible.Slider
    Accessible.name: "Reasoning // " + stepLabel
    Accessible.description:
        "Four-position local reasoning preference: NONE, LOW, MED, HIGH. No trusted inference host is connected."

    function requestStep(value) {
        const next = ReasoningPolicy.clampStep(value);
        if (!interactive || next === stepIndex)
            return;
        // Use the real Post-Apollo dial's bounded, stepped settling motion.
        // The callback still only requests an in-memory Tree preference.
        sharedHardwareDial.requestNumericValue(next);
    }

    function requestPoint(x, y) {
        if (!interactive)
            return;
        const next = ReasoningPolicy.stepFromPoint(x, y, width, height);
        // Reject the 15-degree bottom gap AND the interior label area.
        if (next >= 0)
            requestStep(next);
    }

    SelectorDial {
        id: sharedHardwareDial
        width: 136
        height: 160
        x: root.width / 2 - 68 * root.hardwareScale
        y: root.height / 2 - 76 * root.hardwareScale
        transform: Scale {
            origin.x: 0
            origin.y: 0
            xScale: root.hardwareScale
            yScale: root.hardwareScale
        }

        labelText: ""
        selectorMode: "continuous"
        arcSweepAngle: 345
        // QtQuick angles: right=0, bottom=90. With a 345-degree sweep,
        // SelectorDial's default arcStartAngle=97.5 and end=442.5.
        // This leaves the required 15-degree gap centered at six o'clock.
        minimumValue: 0
        maximumValue: 3
        currentValue: root.stepIndex
        valueStep: 1
        valueDecimals: 0
        snapContinuousToStep: true
        numericDetentInterval: 1
        numericDetentOrigin: 0
        showNumericDetentTicks: true
        numericReferenceValues: [0, 1, 2, 3]
        options: ["NONE", "LOW", "MED", "HIGH"]
        displayOptions: ["N", "L", "M", "H"]
        readoutText: ""

        accentColor: Colors.cyan
        markerColor: Colors.orange
        labelColor: Colors.cyan
        interactive: root.interactive
        // The outer viewport accepts gesture input so the dead bottom
        // sector cannot accidentally reach SelectorDial's internal handlers.
        activeFocusOnTab: false
        onValueRequested: function(value) {
            if (root.interactive) {
                const next = ReasoningPolicy.clampStep(value);
                if (next !== root.stepIndex)
                    root.stepRequested(next);
            }
        }
    }

    // Keep the center label legible after reducing the original 90px
    // hardware body for the composer. The actual knob stays shared.
    Rectangle {
        anchors.centerIn: parent
        width: 24
        height: 12
        radius: 2
        color: Colors.dark
        opacity: 0.92
    }
    GohuText {
        anchors.centerIn: parent
        text: root.stepLabel
        textFormat: Text.PlainText
        font.pixelSize: 8
        font.bold: true
        color: Colors.cyan
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: "transparent"
        border.width: 1
        border.color: root.activeFocus ? Colors.blue : Colors.cyan
    }

    // The Post-Apollo hardware renders below; this unpainted capture
    // surface filters input through the previously tested 15-degree policy.
    MouseArea {
        anchors.fill: parent
        enabled: root.interactive
        preventStealing: true
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
            const withinArc = ReasoningPolicy.stepFromPoint(
                wheel.x, wheel.y, root.width, root.height);
            // Always consume this gesture. Outside the arc it is a no-op,
            // not a leaked wheel event to the shared unbounded handler.
            wheel.accepted = true;
            if (withinArc < 0 || wheel.angleDelta.y === 0)
                return;
            root.requestStep(root.stepIndex + (wheel.angleDelta.y > 0 ? 1 : -1));
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
