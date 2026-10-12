import QtQuick
import QtQuick.Effects

Item {
    id: dialRoot

    property string labelText: "SELECT"
    property var options: []
    property var displayOptions: []
    // "discrete" preserves the accepted Git behavior. "continuous" exposes
    // a numerical range; "zones" assigns names to angular regions. Neither
    // free-position variant snaps on pointer release.
    property string selectorMode: "discrete"
    property real arcStartAngle: -210
    property real arcSweepAngle: 300
    readonly property real boundedSweep: Math.max(1, Math.min(359, arcSweepAngle))
    property real minimumValue: 0
    property real maximumValue: 100
    property real currentValue: 0
    property real valueStep: 1
    property int valueDecimals: 0
    property int currentIndex: 0
    readonly property real previewNumericValue: selectorMode === "continuous"
        ? valueForAngle(visualAngle) : currentValue
    property string readoutText: selectorMode === "continuous"
        ? Number(previewNumericValue).toFixed(Math.max(0, Math.min(6, valueDecimals)))
        : selectedValue ? selectedValue.toUpperCase() : ""
    property bool interactive: selectorMode === "continuous"
        ? maximumValue > minimumValue
        : options && options.length > 1
    property bool keyboardSelected: false
    property var keyboardHost: null

    property color accentColor: Colors.cyan
    property color markerColor: Colors.orange
    property color labelColor: Colors.cyan
    // Operation state comes from the owning module, never inferred from a selection.
    property string loadingState: "idle" // idle, loading, success, error
    property real loadingProgress: -1 // -1: indeterminate; otherwise 0..1
    property color failureColor: Colors.red
    property bool persistentFailure: false
    property int completionPulseCount: 3
    property int feedbackPulsePhase: 0
    property bool dialHovered: false
    property int hoveredOptionIndex: -1
    readonly property bool rotating: dragging || motionActive
    readonly property real ringGlowStrength: !interactive ? 0.10
        : rotating ? 0.95 : dialHovered ? 0.64 : 0.28

    readonly property string selectedValue:
        options && options.length > 0 && currentIndex >= 0 && currentIndex < options.length
        ? String(options[currentIndex])
        : ""

    property real visualAngle: -90
    property bool dragging: false
    property real lastPointerAngle: 0
    property real angularVelocity: 0 // degrees per second
    property real lastMoveTime: 0
    property real pendingTargetAngle: -90
    property bool motionActive: false
    property bool inertial: false
    property int pendingIndex: -1
    property bool pendingNumeric: false
    property real pendingNumericValue: 0
    // Keep a free-position angle when its owning module echoes a zone commit.
    property int echoZoneIndex: -1
    property real flickThreshold: 980 // deliberate release, tuned by live testing
    property real frictionPerFrame: 0.925
    property real settleThreshold: 36
    property int dragDetentIndex: -1
    // Visual detent preview is independent of the externally committed index.
    property int previewIndex: -1
    readonly property int indicatedIndex: previewIndex >= 0 ? previewIndex : currentIndex

    signal selectionRequested(int index, string value)
    signal valueRequested(real value)

    width: 136
    height: 160
    activeFocusOnTab: true
    opacity: interactive ? 1.0 : 0.42
    Behavior on opacity { NumberAnimation { duration: 125 } }

    onLoadingStateChanged: {
        feedbackTimer.stop();
        feedbackPulsePhase = 0;
        if (loadingState === "success"
                || (loadingState === "error" && !persistentFailure))
            feedbackTimer.start();
        progressCanvas.requestPaint();
    }
    onLoadingProgressChanged: progressCanvas.requestPaint()
    onAccentColorChanged: progressCanvas.requestPaint()
    onFailureColorChanged: progressCanvas.requestPaint()

    Timer {
        id: feedbackTimer
        interval: 105
        repeat: true
        onTriggered: {
            dialRoot.feedbackPulsePhase++;
            if (dialRoot.feedbackPulsePhase >= dialRoot.completionPulseCount * 2) {
                stop();
                dialRoot.feedbackPulsePhase = 0;
                if (dialRoot.loadingState === "success"
                        || (dialRoot.loadingState === "error" && !dialRoot.persistentFailure))
                    dialRoot.loadingState = "idle";
            }
        }
    }

    function optionGlowStrength(index) {
        if (index === indicatedIndex)
            return rotating ? 1.0 : dialHovered ? 0.92 : 0.78;
        return index === hoveredOptionIndex ? 0.76 : 0.22;
    }

    function boundedAngle(angle) {
        return Math.max(arcStartAngle,
                        Math.min(arcStartAngle + boundedSweep, Number(angle)));
    }

    function valueForAngle(angle) {
        const ratio = (boundedAngle(angle) - arcStartAngle) / boundedSweep;
        return minimumValue + ratio * (maximumValue - minimumValue);
    }

    function angleForValue(value) {
        const span = maximumValue - minimumValue;
        if (span <= 0)
            return arcStartAngle;
        const fraction = Math.max(0, Math.min(1, (Number(value) - minimumValue) / span));
        return arcStartAngle + fraction * boundedSweep;
    }

    function reportedValue(value) {
        const decimals = Math.max(0, Math.min(6, valueDecimals));
        return Number(Math.max(minimumValue, Math.min(maximumValue, value)).toFixed(decimals));
    }

    function finishFreePosition() {
        const mode = selectorMode;
        const target = boundedAngle(visualAngle);
        visualAngle = target;
        inertial = false;
        inertiaTimer.stop();
        pendingIndex = -1;
        pendingNumeric = false;
        motionActive = false;
        previewIndex = -1;
        if (mode === "continuous") {
            const value = reportedValue(valueForAngle(target));
            if (value !== reportedValue(currentValue))
                valueRequested(value);
        } else if (mode === "zones" && optionCount() > 0) {
            const zone = indexForAngle(target);
            echoZoneIndex = zone;
            if (zone !== currentIndex)
                selectionRequested(zone, String(options[zone]));
            else
                echoZoneIndex = -1;
        }
    }

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
        if (selectorMode === "continuous") {
            // Optional labels are reference marks across the numeric range.
            return arcStartAngle + boundedSweep * (count <= 1 ? 0 : index / (count - 1));
        }
        if (selectorMode === "zones")
            return arcStartAngle + boundedSweep * (index + 0.5) / Math.max(1, count);
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
        if (selectorMode === "zones") {
            const fraction = (boundedAngle(angle) - arcStartAngle) / boundedSweep;
            return Math.max(0, Math.min(count - 1, Math.floor(fraction * count)));
        }
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

    function stopMotion() {
        // Clear the pending target before stopping animations so obsolete
        // requests cannot issue a late commit.
        pendingIndex = -1;
        pendingNumeric = false;
        echoZoneIndex = -1;
        inertial = false;
        motionActive = false;
        inertiaTimer.stop();
        settleAnimation.stop();
        previewIndex = -1;
    }

    function settleAnimationReset() {
        settleAnimation.duration = 165;
    }

    function settleAtCurrentAngle() {
        inertial = false;
        inertiaTimer.stop();
        if (selectorMode !== "discrete") {
            finishFreePosition();
            return;
        }
        pendingIndex = indexForAngle(visualAngle);
        previewIndex = pendingIndex;
        pendingTargetAngle = nearestEquivalent(angleForIndex(pendingIndex), visualAngle);
        settleAnimation.duration = 165;
        settleAnimation.from = visualAngle;
        settleAnimation.to = pendingTargetAngle;
        settleAnimation.start();
    }

    function requestIndex(index) {
        const count = optionCount();
        if (count <= 0 || !interactive || dragging)
            return;
        if (selectorMode === "continuous") {
            requestNumericValue(valueForAngle(angleForIndex(Math.max(0, Math.min(count - 1, index)))));
            return;
        }
        const next = selectorMode === "zones"
            ? Math.max(0, Math.min(count - 1, Number(index)))
            : normalizedIndex(index);
        const destination = selectorMode === "zones"
            ? angleForIndex(next)
            : nearestEquivalent(angleForIndex(next), visualAngle);
        stopMotion();
        pendingIndex = next;
        previewIndex = next;
        motionActive = true;
        pendingTargetAngle = destination;
        settleAnimation.from = visualAngle;
        settleAnimation.to = destination;
        settleAnimation.duration = 115;
        settleAnimation.start();
    }

    function requestNumericValue(value) {
        if (selectorMode !== "continuous" || !interactive || dragging)
            return;
        const next = Math.max(minimumValue, Math.min(maximumValue, Number(value)));
        const destination = angleForValue(next);
        stopMotion();
        pendingNumeric = true;
        pendingNumericValue = next;
        motionActive = true;
        pendingTargetAngle = destination;
        settleAnimation.from = visualAngle;
        settleAnimation.to = destination;
        settleAnimation.duration = 115;
        settleAnimation.start();
    }

    function stepIndex(delta) {
        if (!interactive)
            return;
        if (selectorMode === "continuous") {
            const base = pendingNumeric ? pendingNumericValue : currentValue;
            requestNumericValue(base + Number(delta) * Math.max(0.000001, valueStep));
        } else {
            requestIndex((pendingIndex >= 0 ? pendingIndex : currentIndex) + Number(delta));
        }
    }

    function snapToCurrent() {
        if (selectorMode === "continuous") {
            visualAngle = angleForValue(currentValue);
            return;
        }
        if (optionCount() <= 0)
            return;
        visualAngle = selectorMode === "zones" ? angleForIndex(currentIndex)
            : nearestEquivalent(angleForIndex(currentIndex), visualAngle);
    }

    onCurrentIndexChanged: {
        if (selectorMode === "zones" && currentIndex === echoZoneIndex) {
            echoZoneIndex = -1;
            return;
        }
        echoZoneIndex = -1;
        if (!dragging && !motionActive && selectorMode !== "continuous")
            snapToCurrent();
    }

    onCurrentValueChanged: {
        if (selectorMode === "continuous" && !dragging && !motionActive)
            snapToCurrent();
    }

    onSelectorModeChanged: {
        stopMotion();
        dragging = false;
        snapToCurrent();
    }
    onArcStartAngleChanged: {
        if (selectorMode !== "discrete" && !dragging && !motionActive)
            snapToCurrent();
    }
    onArcSweepAngleChanged: {
        if (selectorMode !== "discrete" && !dragging && !motionActive)
            snapToCurrent();
    }

    onOptionsChanged: {
        stopMotion();
        if (!dragging)
            snapToCurrent();
    }

    onInteractiveChanged: {
        if (!interactive) {
            stopMotion();
            dragging = false;
            snapToCurrent();
        }
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

    NumberAnimation {
        id: settleAnimation
        target: dialRoot
        property: "visualAngle"
        duration: 165
        easing.type: Easing.OutBack
        easing.overshoot: 0.42
        onFinished: {
            if (!dialRoot.motionActive)
                return;
            if (dialRoot.selectorMode === "continuous") {
                const value = dialRoot.reportedValue(dialRoot.pendingNumericValue);
                dialRoot.motionActive = false;
                dialRoot.pendingNumeric = false;
                dialRoot.previewIndex = -1;
                if (value !== dialRoot.reportedValue(dialRoot.currentValue))
                    dialRoot.valueRequested(value);
                return;
            }
            if (dialRoot.pendingIndex < 0)
                return;
            const finishedIndex = dialRoot.pendingIndex;
            dialRoot.motionActive = false;
            dialRoot.pendingIndex = -1;
            dialRoot.previewIndex = -1;
            if (finishedIndex !== dialRoot.currentIndex)
                dialRoot.selectionRequested(finishedIndex, String(dialRoot.options[finishedIndex]));
        }
    }

    Timer {
        id: inertiaTimer
        interval: 16
        repeat: true
        onTriggered: {
            if (!dialRoot.inertial || !dialRoot.interactive) {
                stop();
                return;
            }
            dialRoot.angularVelocity *= dialRoot.frictionPerFrame;
            const nextAngle = dialRoot.visualAngle
                + dialRoot.angularVelocity * interval / 1000;
            if (dialRoot.selectorMode !== "discrete") {
                dialRoot.visualAngle = dialRoot.boundedAngle(nextAngle);
                if (nextAngle !== dialRoot.visualAngle) {
                    dialRoot.finishFreePosition();
                    return;
                }
            } else {
                dialRoot.visualAngle = nextAngle;
            }
            if (dialRoot.selectorMode !== "continuous")
                dialRoot.previewIndex = dialRoot.indexForAngle(dialRoot.visualAngle);
            if (Math.abs(dialRoot.angularVelocity) < dialRoot.settleThreshold)
                dialRoot.settleAtCurrentAngle();
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

        // Physical interaction ring: outside the cyan status ring.
        // Keep the original dark chassis edge; glow indicates hover/rotation.
        Rectangle {
            id: outerInteractionRing
            anchors.centerIn: parent
            width: 98
            height: 98
            radius: 49
            color: "#121018"
            border.width: 1
            border.color: "#49414F"
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: dialRoot.accentColor
                shadowOpacity: dialRoot.ringGlowStrength * 0.56
                shadowBlur: 0.72
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

            // The operator's middle cyan ring. At idle it retains its
            // accepted appearance; during work it becomes a dim track for
            // a visible loading/progress arc at the SAME circumference.
            Rectangle {
                id: centerStatusRing
                anchors.centerIn: parent
                width: 72
                height: 72
                radius: 36
                color: "transparent"
                border.width: 2
                border.color: dialRoot.accentColor
                opacity: dialRoot.loadingState === "idle" ? 1.0 : 0.16
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: dialRoot.accentColor
                    shadowOpacity: dialRoot.loadingState === "idle"
                                   ? dialRoot.ringGlowStrength : 0.0
                    shadowBlur: 0.78
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

            // Animated feedback ON the 72px middle cyan ring, not the
            // white hub. The pointer stays in front of the ring.
            Item {
                id: loadingCenter
                anchors.centerIn: parent
                width: 78
                height: 78
                visible: dialRoot.loadingState !== "idle"

                Canvas {
                    id: progressCanvas
                    anchors.fill: parent
                    property real sweep: dialRoot.loadingState !== "loading" ? 360
                        : dialRoot.loadingProgress < 0 ? 100
                        : Math.max(0, Math.min(1, dialRoot.loadingProgress)) * 360
                    onSweepChanged: requestPaint()
                    onPaint: {
                        const ctx = getContext("2d");
                        ctx.reset();
                        ctx.clearRect(0, 0, width, height);
                        ctx.beginPath();
                        ctx.arc(width / 2, height / 2, 34,
                                -Math.PI / 2,
                                -Math.PI / 2 + sweep * Math.PI / 180);
                        ctx.strokeStyle = dialRoot.loadingState === "error"
                            ? dialRoot.failureColor.toString()
                            : dialRoot.accentColor.toString();
                        ctx.lineWidth = 3.5;
                        ctx.lineCap = "round";
                        ctx.stroke();
                    }
                    opacity: dialRoot.loadingState === "loading" ? 1.0
                        : dialRoot.loadingState === "error" && dialRoot.persistentFailure ? 1.0
                        : dialRoot.feedbackPulsePhase % 2 === 0 ? 1.0 : 0.12
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: dialRoot.loadingState === "error"
                            ? dialRoot.failureColor : dialRoot.accentColor
                        shadowOpacity: 0.85
                        shadowBlur: 0.72
                    }
                    RotationAnimation on rotation {
                        from: 0
                        to: 360
                        duration: 950
                        loops: Animation.Infinite
                        running: dialRoot.loadingState === "loading"
                                 && dialRoot.loadingProgress < 0
                        onStopped: progressCanvas.rotation = 0
                    }
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
                        shadowOpacity: 0.85
                        shadowBlur: 0.75
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
                    color: index === dialRoot.indicatedIndex
                           ? dialRoot.markerColor
                           : dialRoot.labelColor

                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: optionMark.index === dialRoot.indicatedIndex
                                     ? dialRoot.markerColor
                                     : dialRoot.labelColor
                        shadowOpacity: dialRoot.optionGlowStrength(optionMark.index)
                        shadowBlur: optionMark.index === dialRoot.indicatedIndex ? 0.85 : 0.46
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    enabled: dialRoot.interactive
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor

                    onEntered: {
                        dialRoot.hoveredOptionIndex = optionMark.index;
                        if (dialRoot.keyboardHost)
                            dialRoot.keyboardHost.selectGitControlFromMouse(dialRoot);
                    }

                    onExited: {
                        if (dialRoot.hoveredOptionIndex === optionMark.index)
                            dialRoot.hoveredOptionIndex = -1;
                    }

                    onPositionChanged: {
                        if (dialRoot.keyboardHost)
                            dialRoot.keyboardHost.selectGitControlFromMouse(dialRoot);
                    }

                    onClicked: {
                        if (dialRoot.keyboardHost)
                            dialRoot.keyboardHost.selectGitControlFromMouse(dialRoot);

                        dialRoot.forceActiveFocus();
                        dialRoot.requestIndex(optionMark.index);

                        if (dialRoot.keyboardHost)
                            dialRoot.keyboardHost.restoreGitKeyboardFocus(false);
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

            onEntered: {
                dialRoot.dialHovered = true;
                if (dialRoot.keyboardHost)
                    dialRoot.keyboardHost.selectGitControlFromMouse(dialRoot);
            }

            onExited: {
                if (!dialRoot.dragging)
                    dialRoot.dialHovered = false;
            }

            onPositionChanged: function(mouse) {
                if (dialRoot.keyboardHost)
                    dialRoot.keyboardHost.selectGitControlFromMouse(dialRoot);

                if (!pressed || !dialRoot.dragging)
                    return;

                const cx = mouse.x - width / 2;
                const cy = mouse.y - height / 2;
                const radius = Math.sqrt(cx * cx + cy * cy);

                if (radius < 15)
                    return;

                const angle = dialRoot.pointerAngle(mouse.x, mouse.y, width, height);
                const delta = dialRoot.normalizeDelta(angle - dialRoot.lastPointerAngle);

                dialRoot.visualAngle = dialRoot.selectorMode === "discrete"
                    ? dialRoot.visualAngle + delta
                    : dialRoot.boundedAngle(dialRoot.visualAngle + delta);
                dialRoot.lastPointerAngle = angle;
                const now = Date.now();
                const elapsed = now - dialRoot.lastMoveTime;
                if (elapsed > 0 && elapsed < 120) {
                    const instantaneous = delta * 1000 / elapsed;
                    dialRoot.angularVelocity = dialRoot.angularVelocity * 0.35
                                               + instantaneous * 0.65;
                }
                dialRoot.lastMoveTime = now;

                if (dialRoot.selectorMode !== "continuous") {
                    const detent = dialRoot.indexForAngle(dialRoot.visualAngle);
                    if (detent !== dialRoot.dragDetentIndex) {
                        dialRoot.dragDetentIndex = detent;
                        dialRoot.previewIndex = detent;
                    }
                }
            }

            onPressed: function(mouse) {
                if (dialRoot.keyboardHost)
                    dialRoot.keyboardHost.selectGitControlFromMouse(dialRoot);

                dialRoot.forceActiveFocus();
                dialRoot.stopMotion();
                dialRoot.angularVelocity = 0;
                dialRoot.lastMoveTime = Date.now();
                dialRoot.dragging = true;
                dialRoot.dragDetentIndex = dialRoot.currentIndex;
                dialRoot.previewIndex = dialRoot.selectorMode === "continuous"
                    ? -1 : dialRoot.currentIndex;
                dialRoot.lastPointerAngle = dialRoot.pointerAngle(
                    mouse.x,
                    mouse.y,
                    width,
                    height
                );
            }

            onReleased: {
                if (!dialRoot.dragging)
                    return;

                dialRoot.dragging = false;
                dialRoot.dialHovered = containsMouse;
                dialRoot.motionActive = true;
                // A stale velocity reading after holding the pointer still
                // must not cause accidental inertia.
                const recentlyMoving = Date.now() - dialRoot.lastMoveTime < 85;
                const atBound = dialRoot.selectorMode !== "discrete"
                    && (dialRoot.visualAngle <= dialRoot.arcStartAngle
                        || dialRoot.visualAngle >= dialRoot.arcStartAngle + dialRoot.boundedSweep);
                if (!atBound && recentlyMoving
                        && Math.abs(dialRoot.angularVelocity) >= dialRoot.flickThreshold) {
                    dialRoot.inertial = true;
                    inertiaTimer.start();
                } else {
                    dialRoot.settleAnimationReset();
                    dialRoot.settleAtCurrentAngle();
                }

                if (dialRoot.keyboardHost)
                    dialRoot.keyboardHost.restoreGitKeyboardFocus(false);
            }

            onCanceled: {
                dialRoot.dragging = false;
                dialRoot.dialHovered = containsMouse;
                dialRoot.stopMotion();
                dialRoot.snapToCurrent();

                if (dialRoot.keyboardHost)
                    dialRoot.keyboardHost.restoreGitKeyboardFocus(false);
            }

            onWheel: function(wheel) {
                if (wheel.angleDelta.y === 0)
                    return;

                dialRoot.forceActiveFocus();
                dialRoot.stepIndex(wheel.angleDelta.y > 0 ? -1 : 1);

                if (dialRoot.keyboardHost)
                    dialRoot.keyboardHost.restoreGitKeyboardFocus(false);

                wheel.accepted = true;
            }
        }

        // Keyboard ring appears both while the dial is selected by the
        // Git spatial navigator and while it owns direct dial focus.
        Rectangle {
            anchors.centerIn: parent
            width: 110
            height: 110
            radius: 55
            color: "transparent"
            border.width:
                dialRoot.activeFocus || dialRoot.keyboardSelected
                ? 2 : 0
            border.color:
                dialRoot.activeFocus
                ? Colors.magenta
                : Colors.orange
            opacity:
                dialRoot.activeFocus || dialRoot.keyboardSelected
                ? 0.82 : 0.0
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
