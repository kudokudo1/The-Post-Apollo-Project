import QtQuick
import QtQuick.Effects
import QtQuick.Controls
import QtQuick.Shapes

Item {
    id: root

    // Scroll target.
    property var flickable: null
    // Opt in for ListView/GridView: their origin can move when rows are
    // inserted, removed or sized lazily. Other consumers retain legacy math.
    property bool accountForContentOrigin: false
    // Positioner-owned content may mount its overlay into a non-positioning
    // ancestor without counting the scrollbar as a Column/Row layout child.
    property Item mountingParent: null

    // Track follows the usable side of its box by default, independently
    // from the Flickable's content position. Explicit legacy/specialty rails
    // can select "viewport", retaining their original geometry.
    property string geometryMode: "box" // "box" | "viewport"
    property Item geometryHost: null     // Optional explicit box/section bounds.
    property int boxTopInset: 2
    property int boxBottomInset: 2
    property int boxLeftInset: 2
    property int boxRightEndInset: 2
    readonly property Item effectiveGeometryHost:
        geometryHost ? geometryHost : parent
    // Do not follow a parent Flickable's scrolling content or reinterpret
    // intentional protruding rails as ordinary box-edge tracks.
    readonly property bool hostIsScrollingContent:
        effectiveGeometryHost && effectiveGeometryHost.parent
        && effectiveGeometryHost.parent.contentItem === effectiveGeometryHost
        && effectiveGeometryHost.parent.flickableDirection !== undefined
    readonly property bool boxSideGeometry:
        geometryMode !== "viewport"
        && effectiveGeometryHost
        && (geometryHost || (!hostIsScrollingContent
                             && effectiveGeometryHost.flickableDirection === undefined))
        && trackTopExtension <= 0

    // Find the usable side between real header/footer siblings of the pane.
    // No implicit 5px viewport inset is added to this box-side track.
    function boxUsableBounds() {
        const host = effectiveGeometryHost;
        if (!host || !flickable)
            return Qt.point(0, 0);
        const length = horizontal ? host.width : host.height;
        const origin = flickable.mapToItem(host, 0, 0);
        const paneStart = horizontal ? origin.x : origin.y;
        const paneEnd = paneStart + (horizontal ? flickable.width : flickable.height);
        let start = 0;
        let end = Math.max(0, length);
        // Only direct siblings of the viewport delimit its local section.
        // A mounted outer host can supply exact geometry via geometryHost.
        if (flickable.parent === host) {
            const peers = host.children;
            for (let i = 0; i < peers.length; ++i) {
                const item = peers[i];
                if (!item || item === flickable || item === root
                        || !item.visible || item.width <= 0 || item.height <= 0)
                    continue;
                const near = horizontal ? item.x : item.y;
                const far = near + (horizontal ? item.width : item.height);
                if (far <= paneStart + 0.5)
                    start = Math.max(start, far);
                else if (near >= paneEnd - 0.5)
                    end = Math.min(end, near);
            }
        }
        return Qt.point(start, Math.max(start, end));
    }
    readonly property point boxBounds: boxUsableBounds()
    readonly property real boxStart: Math.max(0, boxBounds.x
        + (horizontal ? boxLeftInset : boxTopInset))
    readonly property real boxEnd: Math.max(boxStart, boxBounds.y
        - (horizontal ? boxRightEndInset : boxBottomInset))
    readonly property point boxOrigin:
        effectiveGeometryHost && parent && effectiveGeometryHost !== parent
        ? effectiveGeometryHost.mapToItem(parent, 0, 0) : Qt.point(0, 0)

    // Syntagma // One configurable family for both axes.
    property int orientation: Qt.Vertical
    readonly property bool horizontal: orientation === Qt.Horizontal
    property string placement: "auto"  // right/left or bottom/top
    readonly property string resolvedPlacement:
        placement === "auto" || placement === ""
        ? (horizontal ? "bottom" : "right") : placement

    // Three independent measurements (audit issues 01/02, operator-approved):
    //   crossExtent: physical scrollbar width; never inflated by glow;
    //   effectiveGlowPadding: a recommendation for effects outside that width;
    //   reservedExtent: what the HOST reserves in its own layout.
    // Neither reservation nor effect padding silently enlarges hit geometry.
    // No mutation of the bound Flickable's anchors/margins occurs here.
    property bool reserveSpace: true
    property bool reserveGlowSpace: false // Optional host-side wider clearance.
    property bool containGlow: true      // Normal track; deliberate rail extensions retain legacy visibility.
    property int glowPadding: 7
    readonly property real effectiveGlowPadding: containGlow
        ? Math.max(glowPadding,
                   handleGlowEnabled
                   ? (dropHandleGlow ? handleDropGlowRadius
                      : (starStyle ? effectiveStarPressedSpread
                         : effectiveBarPressedSpread) + 2)
                   : 0,
                   railGlowEnabled ? railGlowSpread + 2 : 0)
        : 0
    readonly property real crossExtent:
        starStyle ? starAreaWidth : barAreaWidth
    readonly property real reservedExtent:
        reserveSpace
        ? crossExtent + edgeInset
          + (reserveGlowSpace ? 2 * effectiveGlowPadding : 0)
        : 0

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
    property int rightEndInset: 5   // Horizontal track's end inset.
    // Hosts which already reserve endpoint gaps can disable a duplicate 5px
    // insertion without overwriting the actual approved per-axis defaults.
    property bool viewportHasEndpointClearance: false
    readonly property int effectiveTopInset: viewportHasEndpointClearance ? 0 : topInset
    readonly property int effectiveBottomInset: viewportHasEndpointClearance ? 0 : bottomInset
    readonly property int effectiveLeftInset: viewportHasEndpointClearance ? 0 : leftInset
    readonly property int effectiveRightEndInset: viewportHasEndpointClearance ? 0 : rightEndInset
    property int edgeInset: 4
    property int rightInset: edgeInset // Legacy right-edge override.
    property int leftEdgeInset: edgeInset
    property int topEdgeInset: edgeInset
    property int bottomEdgeInset: edgeInset
    property int trackTopExtension: 0

    // One component, switchable handle form.
    // Unknown values intentionally fall back to the normal bar.
    property string handleStyle: "bar"
    // Scoped renderer alternative for systems where a Canvas-backed star
    // has a visible rail but an unpainted handle. The default star Canvas
    // and all existing consumers stay unchanged.
    property bool starSceneGraphRenderer: false
    readonly property bool starStyle:
        String(root.handleStyle || "").toLowerCase() === "star"

    // Interaction.
    property int wheelStep: 42 // Fallback / per-instance override.
    property bool useSystemScrollSensitivity: true
    property bool reverseWheelDirection: false
    property string horizontalWheelMode: "convert" // "directional" variant.
    property string trackClickMode: "jump" // "page" rare variant.
    // Operator-approved #09: inner scrolling stops at its own boundary.
    // Explicit opt-in "chain" is available for exceptional host surfaces.
    property string nestedScrollMode: "contain" // "chain" is a variant.
    readonly property bool scrollChaining: nestedScrollMode === "chain"
    property var chainFlickable: null // Explicit host-owned outer pane.
    property bool captureNestedPaneWheel: true // Scoped to real nested Flickables.
    readonly property bool nestedPaneDetected: isNestedWithinFlickable()
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
        flickable && Window.activeFocusItem
        && isChildOf(Window.activeFocusItem, flickable)
    // Hover/handle objects can already be gone while QML reevaluates a
    // binding during startup, target reparenting, or teardown.
    readonly property bool revealTriggerActive:
        (triggerEnabled("hover")
            && ((paneHover ? paneHover.hovered : false)
                || (handleMouse ? handleMouse.containsMouse : false)))
        || (triggerEnabled("scroll") && scrollPulse)
        || (triggerEnabled("focus") && focusWithinPane)
        || (handleMouse ? handleMouse.pressed : false)
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
    property color railGlowColor: railColor

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
    // -1 derives the pressed state from each consumer's existing idle/hover
    // difference; a deliberately quiet hover stays quiet when pressed.
    property real handleDropGlowPressedOpacity: -1
    property real handleDropGlowPressedRadius: -1
    readonly property real effectiveDropPressedOpacity:
        handleDropGlowPressedOpacity >= 0 ? handleDropGlowPressedOpacity
        : progressivePressedValue(handleDropGlowIdleOpacity,
                                  handleDropGlowHoverOpacity)
    readonly property real effectiveDropPressedRadius:
        handleDropGlowPressedRadius >= 0 ? handleDropGlowPressedRadius
        : handleDropGlowRadius

    // Normal bar glow.
    property real barGlowIdleSpread: 2
    property real barGlowHoverSpread: 4
    property real barGlowIdleOpacity: 0.42
    property real barGlowHoverOpacity: 0.60
    property real barGlowPressedSpread: -1
    property real barGlowPressedOpacity: -1
    readonly property real effectiveBarPressedSpread:
        barGlowPressedSpread >= 0 ? barGlowPressedSpread
        : progressivePressedValue(barGlowIdleSpread, barGlowHoverSpread)
    readonly property real effectiveBarPressedOpacity:
        barGlowPressedOpacity >= 0 ? barGlowPressedOpacity
        : progressivePressedValue(barGlowIdleOpacity, barGlowHoverOpacity)

    // Star glow.
    property real starGlowIdleSpread: 3
    property real starGlowHoverSpread: 5
    property real starGlowIdleOpacity: 0.52
    property real starGlowHoverOpacity: 0.72
    property real starGlowPressedSpread: -1
    property real starGlowPressedOpacity: -1
    readonly property real effectiveStarPressedSpread:
        starGlowPressedSpread >= 0 ? starGlowPressedSpread
        : progressivePressedValue(starGlowIdleSpread, starGlowHoverSpread)
    readonly property real effectiveStarPressedOpacity:
        starGlowPressedOpacity >= 0 ? starGlowPressedOpacity
        : progressivePressedValue(starGlowIdleOpacity, starGlowHoverOpacity)

    // Star geometry.
    property real starOuterRadius: starHandleSize * 0.443
    property real starInnerRadius: starHandleSize * 0.20
    property real starLineWidth: 1

    // Same 10 vertices as the existing Canvas, rendered through the Qt
    // Quick scene graph so no Canvas texture upload is required.
    function starSvgPath(width, height) {
        if (width <= 0 || height <= 0)
            return "";
        const centerX = width / 2;
        const centerY = height / 2;
        let segments = [];
        for (let index = 0; index < 10; ++index) {
            const radius = index % 2 === 0 ? starOuterRadius : starInnerRadius;
            const angle = -Math.PI / 2 + index * Math.PI / 5;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            segments.push((index === 0 ? "M " : "L ") + x + " " + y);
        }
        return segments.join(" ") + " Z";
    }

    // Optional overlay for semantic markers/ticks/activity points.
    property Component railDecoration: null

    property alias railItem: rail
    property alias handleItem: handleLoader

    parent:
        mountingParent ? mountingParent
        : flickable && flickable.parent ? flickable.parent : null

    // Audit 04 // An explicitly extended rail (Git Repository: +33px)
    // intentionally draws outside the normal viewport. Preserve that existing
    // appearance instead of clipping off the extension. Standard tracks keep
    // containment; hosts with extended rails remain responsible for their
    // surrounding glow-safe area.
    clip: containGlow && trackTopExtension <= 0
    width: !flickable ? 0
        : horizontal
          ? (boxSideGeometry ? Math.max(0, boxEnd - boxStart)
                             : Math.max(0, flickable.width - effectiveLeftInset - effectiveRightEndInset))
          : crossExtent
    height: !flickable ? 0
        : horizontal ? crossExtent
          : (boxSideGeometry ? Math.max(0, boxEnd - boxStart)
                             : Math.max(0, flickable.height - effectiveTopInset - effectiveBottomInset))
    readonly property point mountOrigin:
        flickable && mountingParent
        ? flickable.mapToItem(mountingParent, 0, 0)
        : Qt.point(flickable ? flickable.x : 0, flickable ? flickable.y : 0)
    // Box coordinates are independent from viewport margins and content rows.
    // The viewport mode remains an explicit compatibility/exception path.
    x: !flickable ? 0
       : boxSideGeometry
         ? boxOrigin.x + (horizontal ? boxStart
             : resolvedPlacement === "left" ? leftEdgeInset
             : effectiveGeometryHost.width - width - rightInset)
       : horizontal ? mountOrigin.x + effectiveLeftInset
       : resolvedPlacement === "left"
         ? mountOrigin.x + leftEdgeInset
         : mountOrigin.x + flickable.width - width - rightInset
    y: !flickable ? 0
       : boxSideGeometry
         ? boxOrigin.y + (!horizontal ? boxStart
             : resolvedPlacement === "top" ? topEdgeInset
             : effectiveGeometryHost.height - height - bottomEdgeInset)
       : !horizontal ? mountOrigin.y + effectiveTopInset
       : resolvedPlacement === "top"
         ? mountOrigin.y + topEdgeInset
         : mountOrigin.y + flickable.height - height - bottomEdgeInset
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
    readonly property real contentStart:
        flickable && accountForContentOrigin
        ? (horizontal ? flickable.originX : flickable.originY) : 0
    readonly property real contentEnd: contentStart + maxContentExtent
    readonly property real scrollRatio:
        maxContentExtent > 0 && flickable
        ? Math.max(0, Math.min(1,
             ((horizontal ? flickable.contentX : flickable.contentY) - contentStart)
             / maxContentExtent))
        : 0
    visible: !!flickable
        && (effectiveVisibilityMode === "persistent"
            || (effectiveVisibilityMode === "auto" && scrollable)
            || (effectiveVisibilityMode === "contextual" && contextVisible)
            || (effectiveVisibilityMode === "reveal" && scrollable && revealRendered))
    // Legacy persistent consumers own per-layer fading. Applying a second
    // whole-root fade changes Workflow Library / Repository Profile artwork.
    // Explicit persistent mode opts into the shared disabled root opacity;
    // empty visibilityMode keeps the existing autoHide:false appearance.
    opacity: effectiveVisibilityMode === "reveal"
        ? (revealOpaque ? 1 : 0)
        : (effectiveVisibilityMode === "persistent"
           && visibilityMode !== "" && !scrollable
           ? inactiveOpacity : 1)

    Behavior on opacity {
        enabled: root.effectiveVisibilityMode === "reveal"
                 && (root.gradualFadeIn || !root.revealOpaque)
        NumberAnimation { duration: root.fadeDuration; easing.type: Easing.OutCubic }
    }

    function clamp(value, low, high) {
        return Math.max(low, Math.min(high, value));
    }
    function progressivePressedValue(idleValue, hoverValue) {
        // Do not flatten deliberate same-intensity idle/hover recipes.
        return hoverValue + Math.max(0, hoverValue - idleValue) * 0.5;
    }
    function isNestedWithinFlickable() {
        if (!flickable) return false;
        let item = flickable.parent;
        while (item) {
            if (item !== flickable
                    && item.contentY !== undefined
                    && item.contentHeight !== undefined
                    && item.flickableDirection !== undefined)
                return true;
            item = item.parent;
        }
        return false;
    }
    function keyboardOwnedByTextInput() {
        const focusItem = Window.activeFocusItem;
        if (!focusItem || !isChildOf(focusItem, flickable))
            return false;
        return focusItem.readOnly !== undefined
               || focusItem.inputMethodHints !== undefined;
    }
    function handleFocusedPaneKey(event) {
        if (!focusWithinPane || keyboardOwnedByTextInput())
            return false;
        const consumed = handleKey(event.key, event.modifiers);
        if (consumed) event.accepted = true;
        return consumed;
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
    // Full inner-list wheel capture only for actual nested Flickables.
    // Non-nested lists keep Qt's existing native wheel handling.
    WheelHandler {
        id: nestedWheelGuard
        parent: root.flickable
        target: null
        blocking: true
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
        enabled: root.captureNestedPaneWheel && root.nestedPaneDetected
                 && root.nestedScrollMode === "contain"
        onWheel: function(event) {
            if (!root.flickable) {
                event.accepted = true;
                return;
            }
            const amount = root.wheelDelta(event);
            if (root.scrollable && amount !== 0)
                root.moveBy(amount, false);
            // No remaining delta can scroll an outer pane.
            event.accepted = true;
        }
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
            flickable.contentX = contentStart + ratio * maxContentExtent;
        else
            flickable.contentY = contentStart + ratio * maxContentExtent;
    }
    function moveBy(delta, allowChain) {
        if (!flickable || !Number.isFinite(delta) || delta === 0)
            return false;
        const axis = horizontal ? "contentX" : "contentY";
        const before = flickable[axis];
        flickable[axis] = clamp(before + delta, contentStart, contentEnd);
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
        const systemLines = useSystemScrollSensitivity && Application.styleHints
            ? Application.styleHints.wheelScrollLines : 0;
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
        // Containment consumes the wheel even when already at the end:
        // never let the outer pane move. Chaining is a deliberate variant.
        const moved = moveBy(delta, scrollChaining);
        wheel.accepted = !scrollChaining || moved;
    }
    function handleKey(key, modifiers) {
        if (!keyboardEnabled || !interactive || !scrollable
                || (modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)))
            return false;
        const step = systemWheelStep();
        let delta = 0;
        if (key === Qt.Key_PageDown) delta = viewportExtent;
        else if (key === Qt.Key_PageUp) delta = -viewportExtent;
        else if (key === Qt.Key_Home || key === Qt.Key_End) {
            const target = key === Qt.Key_Home ? contentStart : contentEnd;
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
        const lines = useSystemScrollSensitivity && Application.styleHints
            ? Application.styleHints.wheelScrollLines : 0;
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
            color: root.railGlowColor
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
        radius: handleMouse.pressed && handleMouse.draggingHandle
                ? root.effectiveDropPressedRadius : root.handleDropGlowRadius
        samples: root.handleDropGlowSamples

        color: root.effectiveHandleColor
        opacity: handleMouse.pressed && handleMouse.draggingHandle
                 ? root.effectiveDropPressedOpacity
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

                spread: handleMouse.pressed && handleMouse.draggingHandle
                        ? root.effectiveBarPressedSpread
                        : root.handleHovered ? root.barGlowHoverSpread
                        : root.barGlowIdleSpread
                opacity: handleMouse.pressed && handleMouse.draggingHandle
                         ? root.effectiveBarPressedOpacity
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
                visible: !root.starSceneGraphRenderer

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

            // Alternative rendering of precisely the same star path.
            // Only TASKS opts in. The shared Loader, hit region, movement,
            // auto visibility and glow semantics remain owned by this component.
            Shape {
                id: starGraphic
                anchors.fill: parent
                visible: root.starSceneGraphRenderer
                antialiasing: true

                ShapePath {
                    fillColor: root.effectiveHandleColor
                    strokeColor: root.effectiveHandleColor
                    strokeWidth: root.starLineWidth
                    joinStyle: ShapePath.RoundJoin
                    PathSvg {
                        path: root.starSvgPath(starGraphic.width, starGraphic.height)
                    }
                }
            }

            RectangularShadow {
                anchors.fill: parent
                z: -1

                visible:
                    root.handleGlowEnabled
                    && !root.dropHandleGlow

                spread: handleMouse.pressed && handleMouse.draggingHandle
                        ? root.effectiveStarPressedSpread
                        : root.handleHovered ? root.starGlowHoverSpread
                        : root.starGlowIdleSpread
                opacity: handleMouse.pressed && handleMouse.draggingHandle
                         ? root.effectiveStarPressedOpacity
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
            const across = root.horizontal ? mouse.y : mouse.x;
            const crossStart = root.horizontal ? handleLoader.y : handleLoader.x;
            const crossEnd = crossStart
                + (root.horizontal ? handleLoader.height : handleLoader.width);
            const insideHandle = pointer >= handleStart
                && pointer <= handleStart + extent
                && across >= crossStart && across <= crossEnd;
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
