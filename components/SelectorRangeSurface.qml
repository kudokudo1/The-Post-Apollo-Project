import QtQuick
import QtQuick.Effects

// F5 RANGE internal surface for SelectorSlider's opt-in "range" profile.
// The owner alone acknowledges lower/upper values. This view requests exactly
// one interval on pointer release; it performs no external operations.
// Collision policy: hard stop, allowing LOW == HIGH (zero-width interval).
// No Decision 036 minimum/maximum interval-width constraint is invented.
Item {
    id: range
    property real minimumValue: 0
    property real maximumValue: 100
    property real lowerValue: 25
    property real upperValue: 75
    property real rangeStep: 1
    property int valueDecimals: 0
    property string valueSuffix: ""
    property color accentColor: Colors.cyan
    property color lowerColor: Colors.magenta
    property color upperColor: Colors.orange
    property bool enabledControl: true
    readonly property bool validDomain: Number.isFinite(minimumValue)
        && Number.isFinite(maximumValue) && maximumValue > minimumValue
    readonly property bool canInteract: enabledControl && validDomain

    readonly property real ownerLower: Math.min(
        clampValue(lowerValue), clampValue(upperValue))
    readonly property real ownerUpper: Math.max(
        clampValue(lowerValue), clampValue(upperValue))

    property bool dragActive: false
    property bool dragCancelled: false
    property bool committing: false
    property string dragTarget: "" // "lower" | "upper" | "whole"
    property string keyTarget: "lower"
    property real candidateLower: 25
    property real candidateUpper: 75
    property real initialLower: 25
    property real initialUpper: 75
    property real pointerStartY: 0
    property real pointerOffsetY: 0

    readonly property bool previewActive: dragActive && !dragCancelled
    readonly property real displayLower: previewActive
        ? candidateLower : ownerLower
    readonly property real displayUpper: previewActive
        ? candidateUpper : ownerUpper

    signal rangeRequested(real lower, real upper)

    activeFocusOnTab: true

    function clampValue(value) {
        if (!validDomain)
            return Number.isFinite(minimumValue) ? minimumValue : 0;
        const n = Number(value);
        return Math.max(minimumValue, Math.min(maximumValue,
            Number.isFinite(n) ? n : minimumValue));
    }

    function roundValue(value) {
        return Number(clampValue(value).toFixed(
            Math.max(0, Math.min(6, valueDecimals))));
    }

    function valueText(value) {
        return clampValue(value).toFixed(
            Math.max(0, Math.min(6, valueDecimals)))
            + (valueSuffix ? " " + valueSuffix : "");
    }

    function travel() {
        return Math.max(0, track.height - lowerThumb.height);
    }

    function topForValue(value) {
        if (!validDomain)
            return 0;
        return travel() * (1 - (clampValue(value) - minimumValue)
            / (maximumValue - minimumValue));
    }

    function valueAtCenter(centerY) {
        const t = travel();
        if (!validDomain || t <= 0)
            return clampValue(minimumValue);
        const normalized = Math.max(0, Math.min(1,
            (centerY - lowerThumb.height / 2) / t));
        return roundValue(minimumValue + (1 - normalized)
            * (maximumValue - minimumValue));
    }

    function cancelPreview() {
        dragCancelled = true;
        dragActive = false;
        dragTarget = "";
    }

    function beginPointer(mouse) {
        if (!canInteract)
            return;
        forceActiveFocus();
        const lowerCenter = topForValue(ownerLower) + lowerThumb.height / 2;
        const upperCenter = topForValue(ownerUpper) + upperThumb.height / 2;
        const withinBand = mouse.y > upperCenter + 10
            && mouse.y < lowerCenter - 10;
        const forceWhole = (mouse.modifiers & Qt.ShiftModifier) !== 0;
        if (forceWhole || (withinBand && Math.abs(mouse.x - width / 2) <= 8))
            dragTarget = "whole";
        else if (Math.abs(mouse.y - lowerCenter)
                < Math.abs(mouse.y - upperCenter))
            dragTarget = "lower";
        else if (Math.abs(mouse.y - upperCenter)
                < Math.abs(mouse.y - lowerCenter))
            dragTarget = "upper";
        else
            dragTarget = mouse.x < width / 2 ? "lower" : "upper";

        keyTarget = dragTarget === "whole" ? "lower" : dragTarget;
        pointerStartY = mouse.y;
        initialLower = ownerLower;
        initialUpper = ownerUpper;
        candidateLower = ownerLower;
        candidateUpper = ownerUpper;
        dragCancelled = false;
        dragActive = true;
        if (dragTarget !== "whole") {
            const center = dragTarget === "lower" ? lowerCenter : upperCenter;
            pointerOffsetY = Math.abs(mouse.y - center) <= 14
                ? mouse.y - center : 0;
            updatePointer(mouse.y);
        }
    }

    function updatePointer(y) {
        if (!canInteract || !previewActive)
            return;
        if (dragTarget === "whole") {
            // Preserve the interval width exactly until the hard endpoint.
            const width = initialUpper - initialLower;
            const delta = travel() <= 0 ? 0
                : -(y - pointerStartY) / travel()
                    * (maximumValue - minimumValue);
            candidateLower = Math.max(minimumValue,
                Math.min(maximumValue - width, initialLower + delta));
            candidateUpper = candidateLower + width;
        } else {
            const target = valueAtCenter(y - pointerOffsetY);
            if (dragTarget === "lower") {
                candidateLower = Math.min(target, initialUpper);
                candidateUpper = initialUpper;
            } else {
                candidateLower = initialLower;
                candidateUpper = Math.max(target, initialLower);
            }
        }
    }

    function finishPointer() {
        if (!dragActive)
            return;
        const low = roundValue(candidateLower);
        const high = roundValue(candidateUpper);
        if (!dragCancelled && canInteract
                && (low !== roundValue(ownerLower)
                    || high !== roundValue(ownerUpper))) {
            // Owner may synchronously echo new bounds; hold candidate visuals
            // until signal processing completes to avoid stale-position flick.
            committing = true;
            rangeRequested(low, high);
            committing = false;
        }
        dragActive = false;
        dragCancelled = false;
        dragTarget = "";
    }

    function stepTarget(direction) {
        if (!canInteract || !Number.isFinite(rangeStep) || rangeStep <= 0)
            return;
        const low = roundValue(ownerLower);
        const high = roundValue(ownerUpper);
        let nextLow = low;
        let nextHigh = high;
        if (keyTarget === "upper")
            nextHigh = Math.max(low, roundValue(high + rangeStep * direction));
        else
            nextLow = Math.min(high, roundValue(low + rangeStep * direction));
        if (nextLow !== low || nextHigh !== high)
            rangeRequested(nextLow, nextHigh);
    }

    function ownerChangedDuringDrag() {
        if (dragActive && !committing && !dragCancelled)
            cancelPreview();
    }

    onLowerValueChanged: ownerChangedDuringDrag()
    onUpperValueChanged: ownerChangedDuringDrag()
    onMinimumValueChanged: ownerChangedDuringDrag()
    onMaximumValueChanged: ownerChangedDuringDrag()
    onEnabledControlChanged: {
        if (!canInteract)
            cancelPreview();
    }

    Keys.onEscapePressed: function(event) {
        if (dragActive) {
            cancelPreview();
            event.accepted = true;
        }
    }
    Keys.onLeftPressed: function(event) {
        keyTarget = "lower";
        event.accepted = true;
    }
    Keys.onRightPressed: function(event) {
        keyTarget = "upper";
        event.accepted = true;
    }
    Keys.onUpPressed: function(event) {
        stepTarget(1);
        event.accepted = true;
    }
    Keys.onDownPressed: function(event) {
        stepTarget(-1);
        event.accepted = true;
    }

    Item {
        id: rangeTrackArea
        anchors {
            fill: parent
            topMargin: 38
            bottomMargin: 26
        }

        Rectangle {
            id: track
            anchors.centerIn: parent
            width: 12
            height: parent.height
            radius: 6
            color: "#030205"
            border.width: 1
            border.color: "#35283D"

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 2
                height: parent.height - 12
                anchors.verticalCenter: parent.verticalCenter
                color: range.accentColor
                opacity: 0.38
            }
        }

        Repeater {
            model: 5
            Rectangle {
                width: index % 2 === 0 ? 9 : 5
                height: 1
                x: 1
                y: index * range.travel() / 4
                    + lowerThumb.height / 2
                color: range.accentColor
                opacity: index % 2 === 0 ? 0.70 : 0.35
            }
        }

        Rectangle {
            id: selectedBand
            anchors.horizontalCenter: parent.horizontalCenter
            width: 8
            y: range.topForValue(range.displayUpper)
                + upperThumb.height / 2
            height: Math.max(2, range.topForValue(range.displayLower)
                - range.topForValue(range.displayUpper))
            radius: 3
            color: range.accentColor
            opacity: range.canInteract ? 0.85 : 0.25

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                opacity: 0.52
                color: range.accentColor
                z: -1
            }
        }

        Rectangle {
            id: lowerThumb
            width: 19
            height: 26
            x: 0
            y: range.topForValue(range.displayLower)
            z: 5
            radius: 3
            color: range.dragActive && range.dragTarget === "lower"
                ? Colors.yellow : Colors.white
            border.width: 1
            border.color: range.lowerColor
            opacity: range.canInteract ? 1.0 : 0.4

            RectangularShadow {
                anchors.fill: parent
                z: -1
                spread: 3
                opacity: 0.68
                color: range.lowerColor
            }

            GohuText {
                anchors.centerIn: parent
                text: "LO"
                font.pixelSize: 8
                color: Colors.black
            }

            Behavior on y {
                enabled: !range.dragActive
                NumberAnimation { duration: 100; easing.type: Easing.OutQuad }
            }
        }

        Rectangle {
            id: upperThumb
            width: 19
            height: 26
            x: parent.width - width
            y: range.topForValue(range.displayUpper)
            z: 6
            radius: 3
            color: range.dragActive && range.dragTarget === "upper"
                ? Colors.yellow : Colors.white
            border.width: 1
            border.color: range.upperColor
            opacity: range.canInteract ? 1.0 : 0.4

            RectangularShadow {
                anchors.fill: parent
                z: -1
                spread: 3
                opacity: 0.68
                color: range.upperColor
            }

            GohuText {
                anchors.centerIn: parent
                text: "HI"
                font.pixelSize: 8
                color: Colors.black
            }

            Behavior on y {
                enabled: !range.dragActive
                NumberAnimation { duration: 100; easing.type: Easing.OutQuad }
            }
        }

        MouseArea {
            id: rangeMouse
            anchors.fill: parent
            z: 8
            enabled: range.canInteract
            acceptedButtons: Qt.LeftButton
            hoverEnabled: true
            cursorShape: Qt.SizeVerCursor
            onPressed: function(mouse) { range.beginPointer(mouse); }
            onPositionChanged: function(mouse) {
                if (pressed)
                    range.updatePointer(mouse.y);
            }
            onReleased: range.finishPointer()
            onCanceled: range.cancelPreview()
            onWheel: function(wheel) {
                if (wheel.angleDelta.y !== 0) {
                    const lowerY = range.topForValue(range.ownerLower)
                        + lowerThumb.height / 2;
                    const upperY = range.topForValue(range.ownerUpper)
                        + upperThumb.height / 2;
                    range.keyTarget = Math.abs(wheel.y - lowerY)
                        < Math.abs(wheel.y - upperY) ? "lower" : "upper";
                    range.stepTarget(wheel.angleDelta.y > 0 ? 1 : -1);
                }
                wheel.accepted = true;
            }
        }
    }

    GohuText {
        x: -96
        width: 90
        y: rangeTrackArea.y + range.topForValue(range.displayLower) + 6
        horizontalAlignment: Text.AlignRight
        text: "LO // " + range.valueText(range.displayLower)
        font.pixelSize: 9
        color: range.lowerColor
    }

    GohuText {
        x: width + 6
        width: 92
        y: rangeTrackArea.y + range.topForValue(range.displayUpper) + 6
        text: "HI // " + range.valueText(range.displayUpper)
        font.pixelSize: 9
        color: range.upperColor
    }
}
