import QtQuick
import QtQuick.Effects

Rectangle {
    id: slider

    property int count: 0
    property int currentIndex: -1
    property color accentColor: Colors.cyan
    property color handleColor: Colors.white
    property color handleGlowColor: Colors.magenta
    property color activityGlowColor: Colors.magenta
    property var activityPoints: []
    property string sideLabel: ""
    // F2 VALUE is opt-in. Existing INDEX users retain the exact default.
    property string selectorProfile: "index" // "index" | "value"
    readonly property bool valueMode: selectorProfile === "value"
    property real minimumValue: 0
    property real maximumValue: 100
    property real currentValue: 0
    property real valueStep: 1 // keyboard/wheel; pointer is continuous
    property int valueDecimals: 0
    property string valueSuffix: ""
    property bool valueDragActive: false
    property real valueDragHandleY: -1
    property var lastDragRequestedValue: null
    readonly property bool validValueDomain: Number.isFinite(minimumValue)
        && Number.isFinite(maximumValue) && maximumValue > minimumValue
    property bool enabledSlider: valueMode ? validValueDomain : count > 1

    signal valueRequested(real value)

    function clampedValue(value) {
        if (!validValueDomain)
            return Number.isFinite(minimumValue) ? minimumValue : 0;
        const requested = Number(value);
        const candidate = Number.isFinite(requested) ? requested : minimumValue;
        return Math.max(minimumValue, Math.min(maximumValue, candidate));
    }

    function reportedValue(value) {
        return Number(clampedValue(value)
            .toFixed(Math.max(0, Math.min(6, valueDecimals))));
    }

    function valueText(value) {
        const places = Math.max(0, Math.min(6, valueDecimals));
        return clampedValue(value).toFixed(places)
            + (valueSuffix ? " " + valueSuffix : "");
    }

    function handleYForValue(value) {
        if (!validValueDomain)
            return 0;
        const ratio = (clampedValue(value) - minimumValue)
            / (maximumValue - minimumValue);
        // Higher values rise; the filled track grows up from minimum.
        return handleTravel() * (1 - ratio);
    }

    function valueForHandleY(y) {
        if (!validValueDomain)
            return clampedValue(minimumValue);
        const travel = handleTravel();
        if (travel <= 0)
            return clampedValue(currentValue);
        const normalizedY = Math.max(0, Math.min(travel, y)) / travel;
        return minimumValue + (1 - normalizedY)
            * (maximumValue - minimumValue);
    }

    function requestDragValue(handleY) {
        if (!valueMode || !enabledSlider)
            return;
        const next = reportedValue(valueForHandleY(handleY));
        if (next === lastDragRequestedValue
                || (lastDragRequestedValue === null
                    && next === reportedValue(currentValue)))
            return;
        lastDragRequestedValue = next;
        valueRequested(next);
    }

    function stepValue(direction) {
        if (!valueMode || !enabledSlider
                || !Number.isFinite(valueStep) || valueStep <= 0)
            return;
        const next = reportedValue(clampedValue(currentValue)
            + direction * valueStep);
        if (next !== reportedValue(currentValue))
            valueRequested(next);
    }

    onSelectorProfileChanged: {
        if (!valueMode) {
            valueDragActive = false;
            valueDragHandleY = -1;
            lastDragRequestedValue = null;
        }
    }

    // F1 INDEX pilot is strictly opt-in. All existing Git/Hospital sliders
    // remain on their original immediate-request semantics by default.
    property string indexInteraction: "legacy" // "legacy" | "preview-release"
    property var optionLabels: []
    property int previewIndex: -1
    property real previewHandleY: -1
    property bool previewCancelled: false
    // Do not derive the preview handoff from MouseArea.pressed:
    // Qt clears pressed before onReleased processes the selection request.
    // That briefly re-targeted the thumb toward the *old* committed index.
    property bool previewGestureActive: false
    readonly property bool indexPilot: indexInteraction === "preview-release"
    readonly property bool previewActive: indexPilot
        && previewGestureActive && !previewCancelled
    readonly property int displayedIndex: previewActive && previewIndex >= 0
        ? previewIndex : currentIndex

    signal indexRequested(int index)

    activeFocusOnTab: indexPilot || valueMode

    function indexLabel(index) {
        if (index < 0)
            return "—";
        const items = optionLabels || [];
        return index < items.length ? String(items[index]) : String(index + 1);
    }

    function cancelIndexPreview() {
        if (!indexPilot)
            return;
        previewCancelled = true;
        previewGestureActive = false;
        previewIndex = -1;
        previewHandleY = -1;
    }

    onIndexInteractionChanged: {
        // A menu can turn the real REMOTE pilot OFF at any point.
        // Abandon its preview before resuming the original legacy path.
        if (!indexPilot) {
            previewGestureActive = false;
            previewIndex = -1;
            previewHandleY = -1;
        }
    }

    // Owner data changing during an unfinished drag invalidates its preview.
    onCurrentIndexChanged: {
        if (indexPilot && dragArea && dragArea.pressed)
            cancelIndexPreview();
    }
    onCountChanged: {
        if (indexPilot && dragArea && dragArea.pressed)
            cancelIndexPreview();
    }

    Keys.onEscapePressed: function(event) {
        if (!indexPilot || !dragArea.pressed)
            return;
        cancelIndexPreview();
        event.accepted = true;
    }

    Keys.onUpPressed: function(event) {
        if (valueMode) {
            stepValue(1);
            event.accepted = true;
            return;
        }
        if (!indexPilot || !enabledSlider)
            return;
        const next = clampedIndex(currentIndex - 1);
        if (next !== currentIndex)
            indexRequested(next);
        event.accepted = true;
    }

    Keys.onDownPressed: function(event) {
        if (valueMode) {
            stepValue(-1);
            event.accepted = true;
            return;
        }
        if (!indexPilot || !enabledSlider)
            return;
        const next = clampedIndex(currentIndex + 1);
        if (next !== currentIndex)
            indexRequested(next);
        event.accepted = true;
    }

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

    function handleYForIndex(index) {
        const selected = index === undefined ? currentIndex : index;
        if (count <= 1 || selected < 0)
            return 0;

        return handleTravel()
            * clampedIndex(selected)
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
            model: slider.valueMode ? 5 : Math.min(slider.count, 13)

            Item {
                width: scaleArea.width
                height: 1
                y:
                    slider.valueMode
                    ? (scaleArea.height - 1) * index / 4
                    : slider.count <= 1
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
                opacity: (slider.valueMode || slider.count > 0)
                    ? 0.48 : 0.14
            }

            // F2 VALUE: visual fill belongs to the live numeric position.
            // This is not a claim that an external operation completed.
            Rectangle {
                id: valueFill
                visible: slider.valueMode
                width: 4
                x: (parent.width - width) / 2
                y: Math.max(0, Math.min(slot.height,
                    thumb.y + thumb.height / 2))
                height: Math.max(0, slot.height - y)
                radius: 2
                color: slider.accentColor
                opacity: slider.enabledSlider ? 0.72 : 0.20
            }

            Repeater {
                model: slider.valueMode ? [] : (slider.activityPoints || [])

                Item {
                    required property int index
                    required property var modelData

                    readonly property int branchIndex:
                        Number(modelData.index || 0)
                    readonly property real intensity:
                        Math.max(
                            0,
                            Math.min(
                                1,
                                Number(modelData.intensity || 0)
                            )
                        )

                    width: 14
                    height: 7
                    anchors.horizontalCenter: parent.horizontalCenter
                    z: 5
                    visible: intensity > 0

                    y:
                        slider.count <= 1
                        ? (slot.height - height) / 2
                        : (
                            slot.height - height
                          )
                          * slider.clampedIndex(branchIndex)
                          / Math.max(1, slider.count - 1)

                    RectangularShadow {
                        anchors.centerIn: parent
                        width: 2
                        height: 2
                        radius: 1
                        spread: 2
                        opacity: 0.32 * parent.intensity
                        color: slider.activityGlowColor
                    }

                    RectangularShadow {
                        anchors.centerIn: parent
                        width: 1
                        height: 1
                        radius: 1
                        spread: 1
                        opacity: 0.92 * parent.intensity
                        color: slider.activityGlowColor
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: {
                            slider.indexRequested(parent.branchIndex);
                        }
                    }
                }
            }

            RectangularShadow {
                id: thumbGlow

                x: thumb.x
                y: thumb.y
                width: thumb.width
                height: thumb.height
                z: 2
                spread: dragArea.pressed ? 3 : 5
                opacity: dragArea.pressed ? 0.42 : 0.62
                color: dragArea.pressed
                       ? Colors.orange
                       : slider.handleGlowColor
            }

            Rectangle {
                id: thumb

                width: 28
                height: 52
                radius: 3
                anchors.horizontalCenter: parent.horizontalCenter
                z: 3

                // During a direct pilot drag, follow actual pointer travel
                // between discrete detents; only the requested index snaps.
                y: slider.valueMode
                    ? (slider.valueDragActive && dragArea.hasMoved
                        ? slider.valueDragHandleY
                        : slider.handleYForValue(slider.currentValue))
                    : slider.previewActive && dragArea.hasMoved
                    ? slider.previewHandleY
                    : slider.handleYForIndex(slider.displayedIndex)

                scale: dragArea.pressed ? 0.97 : 1.0
                color: dragArea.pressed ? Colors.yellow : Colors.white
                border.width: 1
                border.color: dragArea.pressed
                              ? Colors.orange
                              : Colors.white

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
                    // A track click animates toward the initial target.
                    // The first real drag takes over at the visible position.
                    enabled: !dragArea.pressed
                        || ((slider.indexPilot || slider.valueMode)
                            && !dragArea.hasMoved)

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
                enabled: slider.valueMode
                    ? slider.enabledSlider
                    : slider.count > 0
                        && (!slider.indexPilot || slider.enabledSlider)
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                cursorShape: slider.enabledSlider
                             ? Qt.SizeVerCursor
                             : Qt.ArrowCursor

                property real dragOffset: 0
                property real pressStartY: 0
                property bool hasMoved: false

                onPressed: function(mouse) {
                    const localY = mapToItem(slot, mouse.x, mouse.y).y;
                    const handleTop = thumb.y;
                    const handleBottom = thumb.y + thumb.height;

                    dragOffset =
                        localY >= handleTop
                        && localY <= handleBottom
                        ? localY - handleTop
                        : thumb.height / 2;

                    if (slider.valueMode) {
                        slider.forceActiveFocus();
                        hasMoved = false;
                        pressStartY = localY;
                        slider.valueDragHandleY = thumb.y;
                        slider.lastDragRequestedValue = null;
                        slider.valueDragActive = true;
                        slider.requestDragValue(localY - dragOffset);
                        return;
                    }

                    const index = slider.indexFromHandleY(
                        localY - dragOffset
                    );

                    if (slider.indexPilot) {
                        slider.forceActiveFocus();
                        slider.previewCancelled = false;
                        hasMoved = false;
                        pressStartY = localY;
                        slider.previewHandleY = thumb.y;
                        slider.previewIndex = index;
                        // Latch independently of pressed until the release
                        // handler finishes dispatching the commit request.
                        slider.previewGestureActive = true;
                        return;
                    }

                    if (index >= 0 && index !== slider.currentIndex)
                        slider.indexRequested(index);
                }

                onPositionChanged: function(mouse) {
                    if (!pressed)
                        return;

                    const localY = mapToItem(slot, mouse.x, mouse.y).y;

                    if (slider.valueMode) {
                        if (!hasMoved && Math.abs(localY - pressStartY) > 2) {
                            const visibleY = thumb.y;
                            slider.valueDragHandleY = visibleY;
                            dragOffset = localY - visibleY;
                            hasMoved = true;
                        }
                        if (hasMoved) {
                            slider.valueDragHandleY = Math.max(
                                0, Math.min(slider.handleTravel(),
                                    localY - dragOffset));
                            slider.requestDragValue(slider.valueDragHandleY);
                        }
                        return;
                    }

                    if (slider.indexPilot) {
                        if (slider.previewCancelled)
                            return;
                        if (!hasMoved && Math.abs(localY - pressStartY) > 2) {
                            // Capture thumb's live animated position rather
                            // than jumping from an old or future index.
                            const visibleY = thumb.y;
                            slider.previewHandleY = visibleY;
                            dragOffset = localY - visibleY;
                            hasMoved = true;
                        }
                        if (hasMoved) {
                            slider.previewHandleY = Math.max(
                                0, Math.min(slider.handleTravel(),
                                    localY - dragOffset));
                            slider.previewIndex =
                                slider.indexFromHandleY(slider.previewHandleY);
                        }
                        return;
                    }

                    const index = slider.indexFromHandleY(
                        localY - dragOffset
                    );

                    if (index >= 0 && index !== slider.currentIndex)
                        slider.indexRequested(index);
                }

                onReleased: {
                    if (slider.valueMode) {
                        slider.valueDragActive = false;
                        slider.valueDragHandleY = -1;
                        slider.lastDragRequestedValue = null;
                        hasMoved = false;
                        return;
                    }
                    if (!slider.indexPilot)
                        return;
                    const finalIndex = slider.previewCancelled
                        ? -1 : slider.previewIndex;
                    // Keep the preview's visual position latched WHILE the
                    // owner handles the release request. GitService.selectRemote
                    // acknowledges its new index synchronously, so when the
                    // latch drops there is no frame targeting the old index.
                    if (finalIndex >= 0 && finalIndex !== slider.currentIndex)
                        slider.indexRequested(finalIndex);
                    slider.previewGestureActive = false;
                    slider.previewIndex = -1;
                    slider.previewHandleY = -1;
                    slider.previewCancelled = false;
                    hasMoved = false;
                }

                onCanceled: {
                    if (slider.valueMode) {
                        // Live numeric requests already acknowledged by the
                        // owner are not undone by pointer cancellation.
                        slider.valueDragActive = false;
                        slider.valueDragHandleY = -1;
                        slider.lastDragRequestedValue = null;
                        hasMoved = false;
                    } else if (slider.indexPilot) {
                        slider.cancelIndexPreview();
                        hasMoved = false;
                    }
                }

                onWheel: function(wheel) {
                    if (slider.valueMode) {
                        if (slider.enabledSlider)
                            slider.stepValue(wheel.angleDelta.y > 0 ? 1 : -1);
                        wheel.accepted = true;
                        return;
                    }
                    // Never leak a wheel event through the test overlay
                    // while a preview drag is owning pointer interaction.
                    if (slider.indexPilot && pressed) {
                        wheel.accepted = true;
                        return;
                    }
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

    // The current value readout remains committed; preview floats beside
    // the handle only while a different index is being explored.
    GohuText {
        visible: slider.previewActive
            && slider.previewIndex >= 0
            && slider.previewIndex !== slider.currentIndex
        x: slider.width + 8
        y: Math.max(38, Math.min(slider.height - height - 26,
            scaleArea.y + thumb.y + thumb.height / 2 - height / 2))
        text: "PRE // " + slider.indexLabel(slider.previewIndex)
        font.pixelSize: 9
        color: Colors.yellow
        layer.enabled: visible
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Colors.orange
            shadowOpacity: 0.64
            shadowBlur: 0.64
        }
    }

    Rectangle {
        anchors.fill: parent
        z: 12
        visible: (slider.indexPilot || slider.valueMode)
            && slider.activeFocus
        color: "transparent"
        radius: slider.radius
        border.width: 2
        border.color: Colors.cyan
    }

    GohuText {
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: 8
        }

        text: slider.valueMode
            ? slider.valueText(slider.currentValue)
            : slider.currentIndex >= 0
            ? String(slider.currentIndex + 1)
            : "—"
        font.pixelSize: 8
        color: slider.accentColor
        opacity: 0.72
    }
}
