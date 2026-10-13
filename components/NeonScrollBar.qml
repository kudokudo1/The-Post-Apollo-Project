import QtQuick
import QtQuick.Effects

Item {
    id: root

    // Scroll target.
    property var flickable: null

    // Syntagma // One configurable family for both axes.
    property int orientation: Qt.Vertical
    readonly property bool horizontal: orientation === Qt.Horizontal
    property string placement: "auto"  // right/left or bottom/top
    readonly property string resolvedPlacement:
        placement === "auto" || placement === ""
        ? (horizontal ? "bottom" : "right") : placement

    // The host reserves this stable zone in its content layout (see reservedExtent).
    // No mutation of the bound Flickable's anchors/margins occurs here.
    property bool reserveSpace: true
    property bool containGlow: true
    property int glowPadding: 7
    readonly property real effectiveGlowPadding: containGlow
        ? Math.max(glowPadding,
                   handleGlowEnabled
                   ? (dropHandleGlow ? handleDropGlowRadius
                      : Math.max(barGlowPressedSpread, starGlowPressedSpread) + 2)
                   : 0,
                   railGlowEnabled ? railGlowSpread + 2 : 0)
        : 0
    readonly property real crossExtent:
        (starStyle ? starAreaWidth : barAreaWidth) + 2 * effectiveGlowPadding
    readonly property real reservedExtent:
        reserveSpace ? crossExtent + edgeInset : 0

    // Geometry.
    property int barAreaWidth: 10
    property int starAreaWidth: 16
    property int railWidth: 3
    property int barHandleWidth: 7
    property int minimumHandleHeight: 24
    property int starHandleSize: 14

    property int topInset: 5
    property int bottomInset: 5
    property int leftInset: 5       // Horizontal track's start inset.
    property int rightEndInset: 5  // Horizontal track's end inset.
    property int edgeInset: 4
    property int rightInset: edgeInset // Legacy right-edge override.
    property int leftEdgeInset: edgeInset
    property int topEdgeInset: edgeInset
    property int bottomEdgeInset: edgeInset
    property int trackTopExtension: 0

    // One component, switchable handle form.
    // Unknown values intentionally fall back to the normal bar.
    property string handleStyle: "bar"
    readonly property bool starStyle:
        String(root.handleStyle || "").toLowerCase() === "star"

    // Interaction.
    property int wheelStep: 42 // Fallback / per-instance override.
    property bool useSystemScrollSensitivity: true
    property bool reverseWheelDirection: false
    property string horizontalWheelMode: "convert" // "directional" variant.
    property string trackClickMode: "jump" // "page" rare variant.
    property bool scrollChaining: true
    property var chainFlickable: null // Host identifies outer pane.
    property bool keyboardEnabled: true
    property string interactionStyle: "progressive" // "distinct" variant.
    property color pressedHandleColor: handleColor
    property real pressedHandleScale: 1.0
    property bool interactive: true
    property bool wheelEnabled: true
    property bool clickToJump: true
    property bool preserveDragOffset: false
    property int pointerCursorShape: Qt.PointingHandCursor
    property bool autoHide: true // Compatibility: false means persistent.
    property string visibilityMode: "" // "" uses autoHide; auto/persistent/reveal/contextual.
    property string revealMode: "combined" // Or hover, scroll, focus, hover+focus, etc.
    property bool contextVisible: false
    property int fadeDuration: 500 // Shared 500 ms hold + 500 ms fade.
    property bool gradualFadeIn: false
    property real inactiveOpacity: 0.34 // ActionButton's shared unavailable default.
    property real scrollThreshold: 1

    readonly property string effectiveVisibilityMode:
        visibilityMode === "" ? (autoHide ? "auto" : "persistent")
        : visibilityMode
    property bool revealRendered: false
    property bool revealOpaque: false
    property bool scrollPulse: false
    readonly property bool focusWithinPane:
        flickable && window
        && isChildOf(window.activeFocusItem, flickable)
    readonly property bool revealTriggerActive:
        (triggerEnabled("hover") && paneHover.hovered)
        || (triggerEnabled("scroll") && scrollPulse)
        || (triggerEnabled("focus") && focusWithinPane)
        || handleMouse.pressed
    readonly property bool handleHovered:
        handleMouse.containsMouse
        && handleMouse.mouseX >= handleLoader.x
        && handleMouse.mouseX <= handleLoader.x + handleLoader.width
        && handleMouse.mouseY >= handleLoader.y
        && handleMouse.mouseY <= handleLoader.y + handleLoader.height
    readonly property color effectiveHandleColor:
        interactionStyle === "distinct" && handleMouse.pressed
        ? pressedHandleColor : handleColor


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
    property string handleGlowStyle: "rectangular"
    readonly property bool dropHandleGlow:
        String(root.handleGlowStyle || "").toLowerCase() === "drop"

    // Safe DropShadow mode, used by legacy surfaces such as Notifications.
    property real handleDropGlowRadius: 10
    property int handleDropGlowSamples: 13
    property real handleDropGlowIdleOpacity: 0.60
    property real handleDropGlowHoverOpacity: 0.60
    property real handleDropGlowPressedOpacity: 0.76
    property real handleDropGlowPressedRadius: 13

    // Normal bar glow.
    property real barGlowIdleSpread: 2
    property real barGlowHoverSpread: 4
    property real barGlowIdleOpacity: 0.42
    property real barGlowHoverOpacity: 0.60
    property real barGlowPressedSpread: 5
    property real barGlowPressedOpacity: 0.76

    // Star glow.
    property real starGlowIdleSpread: 3
    property real starGlowHoverSpread: 5
    property real starGlowIdleOpacity: 0.52
    property real starGlowHoverOpacity: 0.72
    property real starGlowPressedSpread: 6
    property real starGlowPressedOpacity: 0.86

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

    clip: containGlow
    width: horizontal
        ? (flickable ? Math.max(0, flickable.width - leftInset - rightEndInset) : 0)
        : crossExtent
    height: horizontal
        ? crossExtent
        : (flickable ? Math.max(0, flickable.height - topInset - bottomInset) : 0)
    x: !flickable ? 0
       : horizontal ? flickable.x + leftInset
       : resolvedPlacement === "left"
         ? flickable.x + leftEdgeInset
         : flickable.x + flickable.width - width - rightInset
    y: !flickable ? 0
       : !horizontal ? flickable.y + topInset
       : resolvedPlacement === "top"
         ? flickable.y + topEdgeInset
         : flickable.y + flickable.height - height - bottomEdgeInset
    z: 1000

    readonly property real trackLength: horizontal ? width : height
    readonly property real viewportExtent:
        !flickable ? 0 : (horizontal ? flickable.width : flickable.height)
    readonly property real contentExtent:
        !flickable ? 0 : (horizontal ? flickable.contentWidth : flickable.contentHeight)
    readonly property bool scrollable:
        flickable && contentExtent > viewportExtent + scrollThreshold
    readonly property real maxContentY:
        flickable ? Math.max(0, flickable.contentHeight - flickable.height) : 0
    readonly property real maxContentX:
        flickable ? Math.max(0, flickable.contentWidth - flickable.width) : 0
    readonly property real maxContentExtent: horizontal ? maxContentX : maxContentY
    readonly property real scrollRatio:
        maxContentExtent > 0 && flickable
        ? Math.max(0, Math.min(1,
             (horizontal ? flickable.contentX : flickable.contentY) / maxContentExtent))
        : 0
    visible: !!flickable
        && (effectiveVisibilityMode === "persistent"
            || (effectiveVisibilityMode === "auto" && scrollable)
            || (effectiveVisibilityMode === "contextual" && contextVisible)
            || (effectiveVisibilityMode === "reveal" && scrollable && revealRendered))
    opacity: effectiveVisibilityMode === "reveal"
        ? (revealOpaque ? 1 : 0)
        : (scrollable ? 1 : inactiveOpacity)

    Behavior on opacity {
        enabled: root.effectiveVisibilityMode === "reveal"
                 && (root.gradualFadeIn || !root.revealOpaque)
        NumberAnimation { duration: root.fadeDuration; easing.type: Easing.OutCubic }
    }

    function clamp(value, low, high) {
        return Math.max(low, Math.min(high, value));
    }
    function isChildOf(item, ancestor) {
        while (item) {
            if (item === ancestor)
                return true;
            item = item.parent;
        }
        return false;
    }
    function triggerEnabled(name) {
        const value = String(revealMode || "").toLowerCase();
        return value === "combined" || value.indexOf(name) !== -1;
    }
    function synchronizeReveal() {
        if (effectiveVisibilityMode !== "reveal" || !scrollable) {
            holdTimer.stop();
            fadeTimer.stop();
            revealRendered = false;
            revealOpaque = false;
            return;
        }
        if (revealTriggerActive) {
            holdTimer.stop();
            fadeTimer.stop();
            revealRendered = true;
            revealOpaque = true;
        } else if (revealOpaque && !holdTimer.running) {
            holdTimer.restart();
        }
    }
    onRevealTriggerActiveChanged: synchronizeReveal()
    onEffectiveVisibilityModeChanged: synchronizeReveal()
    onScrollableChanged: synchronizeReveal()
    Component.onCompleted: synchronizeReveal()

    HoverHandler {
        id: paneHover
        parent: root.flickable
        target: null
        enabled: root.effectiveVisibilityMode === "reveal"
    }
    Connections {
        target: root.flickable
        function onContentXChanged() { root.noteScrollActivity(); }
        function onContentYChanged() { root.noteScrollActivity(); }
    }
    Timer {
        id: scrollPulseTimer
        interval: 16
        onTriggered: root.scrollPulse = false
    }
    Timer {
        id: holdTimer
        interval: Math.max(0, root.fadeDuration)
        onTriggered: {
            if (root.revealTriggerActive)
                return;
            root.revealOpaque = false;
            fadeTimer.restart();
        }
    }
    Timer {
        id: fadeTimer
        interval: Math.max(0, root.fadeDuration)
        onTriggered: {
            if (!root.revealTriggerActive)
                root.revealRendered = false;
        }
    }
    function noteScrollActivity() {
        if (effectiveVisibilityMode !== "reveal" || !scrollable)
            return;
        scrollPulse = true;
        scrollPulseTimer.restart();
    }
    function normalHandleHeight() {
        if (!flickable)
            return trackLength;
        const proportional = trackLength * Math.min(1,
            viewportExtent / Math.max(contentExtent, 1));
        return Math.min(trackLength, Math.max(minimumHandleHeight, proportional));
    }
    function activeHandleExtent() {
        return Math.max(0, Math.min(trackLength,
            starStyle ? starHandleSize : normalHandleHeight()));
    }
    function activeHandleWidth() {
        return starStyle ? starHandleSize : barHandleWidth;
    }
    function handleY() {
        return scrollRatio * Math.max(0, trackLength - activeHandleExtent());
    }
    function scrollTo(pointerAxis, handleOffset) {
        if (!flickable || !interactive || !scrollable)
            return;
        const extent = activeHandleExtent();
        const travel = Math.max(0, trackLength - extent);
        const offset = handleOffset === undefined || handleOffset === null
            ? extent / 2 : Number(handleOffset);
        const ratio = travel > 0
            ? clamp((Number(pointerAxis || 0) - offset) / travel, 0, 1) : 0;
        if (horizontal)
            flickable.contentX = ratio * maxContentExtent;
        else
            flickable.contentY = ratio * maxContentExtent;
    }
    function moveBy(delta, allowChain) {
        if (!flickable || !Number.isFinite(delta) || delta === 0)
            return false;
        const axis = horizontal ? "contentX" : "contentY";
        const before = flickable[axis];
        flickable[axis] = clamp(before + delta, 0, maxContentExtent);
        const used = flickable[axis] - before;
        const remainder = delta - used;
        if (allowChain && scrollChaining && chainFlickable
                && chainFlickable !== flickable && Math.abs(remainder) > 0.01) {
            const outerMax = Math.max(0, horizontal
                ? chainFlickable.contentWidth - chainFlickable.width
                : chainFlickable.contentHeight - chainFlickable.height);
            const outerBefore = chainFlickable[axis];
            chainFlickable[axis] = clamp(outerBefore + remainder, 0, outerMax);
            return used !== 0 || chainFlickable[axis] !== outerBefore;
        }
        return used !== 0;
    }
    function wheelDelta(wheel) {
        const shift = !!(wheel.modifiers & Qt.ShiftModifier);
        let rawPixel = horizontal ? wheel.pixelDelta.x : wheel.pixelDelta.y;
        let rawAngle = horizontal ? wheel.angleDelta.x : wheel.angleDelta.y;
        if (horizontal && rawPixel === 0 && rawAngle === 0
                && (horizontalWheelMode === "convert" || shift)) {
            rawPixel = wheel.pixelDelta.y;
            rawAngle = wheel.angleDelta.y;
        }
        if (rawPixel === 0 && rawAngle === 0)
            return 0;
        const systemLines = useSystemScrollSensitivity && Qt.styleHints
            ? Qt.styleHints.wheelScrollLines : 0;
        const step = systemLines > 0 ? systemLines * 14 : wheelStep;
        const delta = rawPixel !== 0 ? -rawPixel : -rawAngle / 120 * step;
        return reverseWheelDirection ? -delta : delta;
    }
    function handleWheel(wheel) {
        if (!flickable || !wheelEnabled || !interactive || !scrollable) {
            wheel.accepted = false;
            return;
        }
        const delta = wheelDelta(wheel);
        if (!delta) {
            wheel.accepted = false;
            return;
        }
        wheel.accepted = moveBy(delta, true);
    }
    function handleKey(key, modifiers) {
        if (!keyboardEnabled || !interactive || !scrollable)
            return false;
        const step = systemWheelStep();
        let delta = 0;
        if (key === Qt.Key_PageDown) delta = viewportExtent;
        else if (key === Qt.Key_PageUp) delta = -viewportExtent;
        else if (key === Qt.Key_Home || key === Qt.Key_End) {
            const target = key === Qt.Key_Home ? 0 : maxContentExtent;
            if (horizontal) flickable.contentX = target;
            else flickable.contentY = target;
            return true;
        } else if (horizontal) {
            if (key === Qt.Key_Right) delta = step;
            else if (key === Qt.Key_Left) delta = -step;
        } else {
            if (key === Qt.Key_Down) delta = step;
            else if (key === Qt.Key_Up) delta = -step;
        }
        return delta !== 0 ? moveBy(delta, false) : false;
    }
    function systemWheelStep() {
        const lines = useSystemScrollSensitivity && Qt.styleHints
            ? Qt.styleHints.wheelScrollLines : 0;
        return lines > 0 ? lines * 14 : wheelStep;
    }
    Keys.onPressed: function(event) {
        if (root.handleKey(event.key, event.modifiers))
            event.accepted = true;
    }
    Rectangle {
        anchors.fill: parent
        color: "transparent"
        border.color: Colors.cyan
        border.width: 1
        radius: 2
        visible: root.activeFocus
        z: 101
    }

    Rectangle {
        id: rail

        width: root.horizontal ? root.width + root.trackTopExtension : root.railWidth
        height: root.horizontal ? root.railWidth : root.height + root.trackTopExtension
        x: root.horizontal ? -root.trackTopExtension : (root.width - width) / 2
        y: root.horizontal ? (root.height - height) / 2 : -root.trackTopExtension

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

        width: root.horizontal ? root.activeHandleExtent() : root.activeHandleWidth()
        height: root.horizontal ? root.activeHandleWidth() : root.activeHandleExtent()
        x: root.horizontal ? root.handleY() : (root.width - width) / 2
        y: root.horizontal ? (root.height - height) / 2 : root.handleY()
        scale: root.interactionStyle === "distinct" && handleMouse.pressed
               ? root.pressedHandleScale : 1

        sourceComponent:
            root.starStyle
            ? starHandleComponent
            : barHandleComponent
    }

    SafeDropShadow {
        anchors.fill: handleLoader

        safeSource: handleLoader.item
        requestedVisible:
            root.handleGlowEnabled
            && root.dropHandleGlow

        horizontalOffset: 0
        verticalOffset: 0
        radius: handleMouse.pressed ? root.handleDropGlowPressedRadius
               : root.handleDropGlowRadius
        samples: root.handleDropGlowSamples

        color: root.effectiveHandleColor
        opacity: handleMouse.pressed ? root.handleDropGlowPressedOpacity
                 : root.handleHovered ? root.handleDropGlowHoverOpacity
                 : root.handleDropGlowIdleOpacity

        transparentBorder: true
    }

    Component {
        id: barHandleComponent

        Rectangle {
            anchors.fill: parent

            radius: root.barHandleRadius
            color: root.effectiveHandleColor
            opacity: root.handleOpacity

            border.width: root.handleBorderWidth
            border.color: root.handleBorderColor

            RectangularShadow {
                anchors.fill: parent
                z: -1

                visible:
                    root.handleGlowEnabled
                    && !root.dropHandleGlow

                spread: handleMouse.pressed ? root.barGlowPressedSpread
                        : root.handleHovered ? root.barGlowHoverSpread
                        : root.barGlowIdleSpread
                opacity: handleMouse.pressed ? root.barGlowPressedOpacity
                         : root.handleHovered ? root.barGlowHoverOpacity
                         : root.barGlowIdleOpacity
                color: root.effectiveHandleColor
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

                property color paintColor: root.effectiveHandleColor
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

                visible:
                    root.handleGlowEnabled
                    && !root.dropHandleGlow

                spread: handleMouse.pressed ? root.starGlowPressedSpread
                        : root.handleHovered ? root.starGlowHoverSpread
                        : root.starGlowIdleSpread
                opacity: handleMouse.pressed ? root.starGlowPressedOpacity
                         : root.handleHovered ? root.starGlowHoverOpacity
                         : root.starGlowIdleOpacity
                color: root.effectiveHandleColor
            }
        }
    }

    MouseArea {
        id: handleMouse

        anchors.fill: parent

        enabled: root.interactive && root.scrollable
        hoverEnabled: true
        cursorShape:
            root.interactive
            ? root.pointerCursorShape
            : Qt.ArrowCursor

        property real dragOffset: 0
        property bool draggingHandle: false

        onPressed: function(mouse) {
            const pointer = root.horizontal ? mouse.x : mouse.y;
            const extent = root.activeHandleExtent();
            const handleStart = root.handleY();
            const insideHandle = pointer >= handleStart
                && pointer <= handleStart + extent;
            const pageMode = root.trackClickMode === "page";
            draggingHandle = insideHandle || (!pageMode && root.clickToJump);
            dragOffset = root.preserveDragOffset && insideHandle
                ? pointer - handleStart : extent / 2;
            if (pageMode && !insideHandle) {
                root.moveBy(pointer < handleStart
                    ? -root.viewportExtent : root.viewportExtent, false);
            } else if (!pageMode && root.clickToJump && !insideHandle) {
                root.scrollTo(pointer, dragOffset);
            }
        }
        onPositionChanged: function(mouse) {
            if (pressed && draggingHandle)
                root.scrollTo(root.horizontal ? mouse.x : mouse.y,
                    root.preserveDragOffset ? dragOffset : undefined);
        }
        onReleased: draggingHandle = false
        onCanceled: draggingHandle = false
        onWheel: function(wheel) { root.handleWheel(wheel); }
    }
}
