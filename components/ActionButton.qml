import QtQuick
import Quickshell
import QtQuick.Effects

Rectangle {
    id: actionButton

    // Arbitrary action artwork/content belongs inside this shell.
    // Simple consumers can use label; rich consumers can compose their own
    // content and bind to foregroundColor / hovered / pressed / selected.
    default property alias contentData: contentHost.data
    property alias contentItem: contentHost
    property alias interactionData: interactionHost.data
    property alias interactionItem: interactionHost

    // Semantic state.
    property bool available: true
    property bool interactive: available
    property bool selected: false
    property bool keyboardSelected: false
    // Additional cursor flags never overwrite another widget's existing
    // keyboardSelected binding. Stationary mouse hover can remain secondary.
    property bool contentKeyboardPrimary: false
    property bool contentKeyboardNavigationActive: false
    property var contentNavigator: null
    readonly property bool cursorPrimaryNotActivated:
        (keyboardSelected || contentKeyboardPrimary) && !selected
    readonly property bool pointerSecondaryHovered:
        contentKeyboardNavigationActive && hovered
        && !contentKeyboardPrimary && !keyboardSelected
    // Content navigators may point at this button without changing its
    // existing keyboardSelected binding or mouse interaction. Activation
    // requires a deliberate per-button opt-in ("leftClicked"/"triggered").
    property bool keyboardNavTarget: true
    property string keyboardActivationSignal: ""
    property bool suppressHover: false
    property bool hoverWhenUnavailable: false
    property bool destructive: false

    property int acceptedButtons: Qt.LeftButton | Qt.RightButton
    property int pointerCursorShape: Qt.PointingHandCursor

    // Convenience label. Rich actions can leave label empty and provide
    // arbitrary content through the default content slot instead.
    property string label: ""
    property bool showLabel: label.length > 0
    property int labelPixelSize: 10
    property int labelMinimumPixelSize: 8
    property int labelFontSizeMode: Text.FixedSize
    property int labelHorizontalAlignment: Text.AlignHCenter
    property int labelElide: Text.ElideRight
    property int contentPadding: 8

    // Optional optical alignment for single-glyph descendants. Zero leaves
    // every existing ActionButton label centered by its text layout box.
    property real labelCenterOffsetX: 0
    property real labelCenterOffsetY: 0
    property alias labelItem: labelText

    // Base identity. These defaults are AppControl-derived starting points,
    // not a claim that every migrated button should be normalized to them.
    property color accentColor: Colors.cyan
    property color destructiveColor: Colors.red

    // Compatibility flag for contextual selectors: use the wash-safe
    // outline, without suppressing intentional interaction fills.
    property bool normalFace: false

    // Red actions have their own filled-state recipe. Close × and specialized
    // controls may explicitly opt out; normal-face selectors stay separate.
    property bool redActionFace: !normalFace && Qt.colorEqual(accentColor, Colors.red)
    // Ordinary actions sample an outline, never a filled shadow surface.
    // Red actions and explicitly wide/composite recipes retain their original
    // broad halos by default. Specialized callers may explicitly opt out.
    property bool washSafePerimeter: normalFace || (!redActionFace && !wideGlowEnabled)
    property bool perimeterGlowEnabled: normalFace || (washSafePerimeter && softGlowEnabled)
    property real perimeterGlowOpacity: effectiveSoftGlowOpacity

    property color idleFillColor: Colors.black
    property color hoverFillColor: Colors.yellow
    // Stationary secondary hover shows orange artwork/border/glow on black,
    // never the primary cursor's yellow fill.
    property color secondaryHoverFillColor: idleFillColor
    property color pressedFillColor:
        destructive ? destructiveColor : Colors.magenta
    property color selectedFillColor: redActionFace ? Colors.black : Colors.yellow
    property color keyboardSelectedFillColor: redActionFace ? Colors.yellow : selectedFillColor

    property color idleForegroundColor: redActionFace ? Colors.white : accentColor
    property color hoverForegroundColor: redActionFace ? Colors.white : Colors.orange
    property color pressedForegroundColor: Colors.black
    property color selectedForegroundColor: redActionFace ? Colors.red : Colors.magenta
    property color keyboardSelectedForegroundColor: hoverForegroundColor

    property color idleBorderColor: accentColor
    property color hoverBorderColor: redActionFace ? Colors.red : Colors.orange
    property color pressedBorderColor:
        destructive ? Colors.black : Colors.magenta
    property color selectedBorderColor: redActionFace ? Colors.red : Colors.magenta
    property color keyboardSelectedBorderColor: redActionFace ? Colors.red : Colors.orange

    property int idleBorderWidth: 1
    property int hoverBorderWidth: 1
    property int pressedBorderWidth: 1
    property int selectedBorderWidth: 1
    property int keyboardSelectedBorderWidth: 2

    // Availability is deliberately separate from interactivity. Most older
    // buttons fade the whole control, while richer AppControl buttons keep the
    // shell present and independently attenuate fill/border/content/glow.
    //
    // Whole-control fade example:
    //   unavailableOpacity: 0.34
    //
    // Layered fade example:
    //   unavailableOpacity: 1.0
    //   unavailableFillOpacity: 0.05
    //   unavailableBorderOpacity: 0.42
    //   unavailableContentOpacity: 0.44
    //   unavailableContentGlowOpacity: 0.12
    //   unavailableSoftGlowOpacity: 0.06
    property real availableOpacity: 1.0
    property real unavailableOpacity: 0.34

    property real unavailableFillOpacity: 1.0
    property real unavailableBorderOpacity: 1.0
    property real unavailableContentOpacity: 1.0

    // Negative values mean "keep the current state glow and let the overall
    // unavailableOpacity do the fading". Non-negative values override the
    // glow layer directly for AppControl-style layered availability.
    property real unavailableContentGlowOpacity: -1.0
    property real unavailableSoftGlowOpacity: -1.0
    property real unavailableWideGlowOpacity: -1.0

    // Content glow. A single-label button glows its label by default. Rich
    // actions can point this at a specific artwork item or the whole content.
    property bool contentGlowEnabled: true
    property Item contentGlowSource:
        showLabel ? labelText : contentHost
    // Normal labels track their source geometry by default, so changing
    // text, layout, or label width cannot leave the sampled glow behind.
    // Custom effect sources retain their existing cross-parent fallback.
    // Legacy consumers may explicitly set false for a reviewed exception.
    property bool trackLabelGlowLocally: true

    property color idleContentGlowColor: accentColor
    property color hoverContentGlowColor: redActionFace ? Colors.red : Colors.orange
    property color pressedContentGlowColor:
        destructive ? destructiveColor : Colors.magenta
    property color selectedContentGlowColor: redActionFace ? Colors.red : Colors.magenta
    property color keyboardSelectedContentGlowColor: redActionFace ? Colors.red : Colors.orange

    property real contentGlowIdleOpacity: VisualLanguage.actionContentIdleOpacity
    property real contentGlowHoverOpacity: VisualLanguage.actionContentHoverOpacity
    property real contentGlowPressedOpacity: VisualLanguage.actionContentPressedOpacity
    property real contentGlowSelectedOpacity: VisualLanguage.actionContentSelectedOpacity
    property real contentGlowKeyboardSelectedOpacity: contentGlowHoverOpacity

    property real contentGlowRadius: 7
    property int contentGlowSamples: 7

    // Primary action halo. AppControl commonly uses one rectangular halo.
    property bool softGlowEnabled: !normalFace
    property real softGlowSpread: 3
    property real softGlowMargin: 0

    property color idleSoftGlowColor: accentColor
    property color hoverSoftGlowColor: redActionFace ? Colors.red : Colors.orange
    property color pressedSoftGlowColor:
        destructive ? destructiveColor : Colors.magenta
    property color selectedSoftGlowColor: redActionFace ? Colors.red : Colors.magenta
    property color keyboardSelectedSoftGlowColor: redActionFace ? Colors.red : Colors.orange

    property real softGlowIdleOpacity: redActionFace ? 0.48 : 0.22
    property real softGlowHoverOpacity: redActionFace ? 0.70 : 0.56
    property real softGlowPressedOpacity: 0.60
    property real softGlowSelectedOpacity: redActionFace ? 0.70 : 0.56
    property real softGlowKeyboardSelectedOpacity: redActionFace ? 0.70 : 0.56

    // Optional second halo for richer descendants such as GitW's local
    // ActionButton. Disabled by default so compact controls stay lightweight.
    property bool wideGlowEnabled: redActionFace
    property real wideGlowSpread: 10

    property color idleWideGlowColor: idleSoftGlowColor
    property color hoverWideGlowColor: hoverSoftGlowColor
    property color pressedWideGlowColor: pressedSoftGlowColor
    property color selectedWideGlowColor: selectedSoftGlowColor
    property color keyboardSelectedWideGlowColor:
        keyboardSelectedSoftGlowColor

    property real wideGlowIdleOpacity: redActionFace ? 0.22 : 0.015
    property real wideGlowHoverOpacity: redActionFace ? 0.32 : 0.08
    property real wideGlowPressedOpacity: 0.10
    property real wideGlowSelectedOpacity: redActionFace ? 0.32 : 0.07
    property real wideGlowKeyboardSelectedOpacity: redActionFace ? 0.32 : 0.08

    readonly property bool pointerActive:
        interactive || hoverWhenUnavailable

    readonly property bool hovered:
        !suppressHover
        && mouse.containsMouse
        && (available || hoverWhenUnavailable)

    readonly property bool pressed:
        interactive && mouse.pressed

    readonly property bool effectiveSelected:
        selected || keyboardSelected

    readonly property color fillColor:
        pressed
        ? pressedFillColor
        : cursorPrimaryNotActivated
        ? keyboardSelectedFillColor
        : selected
        ? selectedFillColor
        : hovered
        ? (pointerSecondaryHovered ? secondaryHoverFillColor : hoverFillColor)
        : idleFillColor

    readonly property color foregroundColor:
        pressed
        ? pressedForegroundColor
        : cursorPrimaryNotActivated
        ? keyboardSelectedForegroundColor
        : selected
        ? selectedForegroundColor
        : hovered
        ? hoverForegroundColor
        : idleForegroundColor

    readonly property color activeBorderColor:
        pressed
        ? pressedBorderColor
        : cursorPrimaryNotActivated
        ? keyboardSelectedBorderColor
        : selected
        ? selectedBorderColor
        : hovered
        ? hoverBorderColor
        : idleBorderColor

    readonly property int activeBorderWidth:
        pressed
        ? pressedBorderWidth
        : cursorPrimaryNotActivated
        ? keyboardSelectedBorderWidth
        : selected
        ? selectedBorderWidth
        : hovered
        ? hoverBorderWidth
        : idleBorderWidth

    readonly property color contentGlowColor:
        pressed
        ? pressedContentGlowColor
        : cursorPrimaryNotActivated
        ? keyboardSelectedContentGlowColor
        : selected
        ? selectedContentGlowColor
        : hovered
        ? hoverContentGlowColor
        : idleContentGlowColor

    readonly property real stateContentGlowOpacity:
        pressed
        ? contentGlowPressedOpacity
        : cursorPrimaryNotActivated
        ? contentGlowKeyboardSelectedOpacity
        : selected
        ? contentGlowSelectedOpacity
        : hovered
        ? contentGlowHoverOpacity
        : contentGlowIdleOpacity

    readonly property real effectiveContentGlowOpacity:
        !available && unavailableContentGlowOpacity >= 0.0
        ? unavailableContentGlowOpacity
        : stateContentGlowOpacity

    readonly property color softGlowColor:
        pressed
        ? pressedSoftGlowColor
        : cursorPrimaryNotActivated
        ? keyboardSelectedSoftGlowColor
        : selected
        ? selectedSoftGlowColor
        : hovered
        ? hoverSoftGlowColor
        : idleSoftGlowColor

    readonly property real stateSoftGlowOpacity:
        pressed
        ? softGlowPressedOpacity
        : cursorPrimaryNotActivated
        ? softGlowKeyboardSelectedOpacity
        : selected
        ? softGlowSelectedOpacity
        : hovered
        ? softGlowHoverOpacity
        : softGlowIdleOpacity

    readonly property real effectiveSoftGlowOpacity:
        !available && unavailableSoftGlowOpacity >= 0.0
        ? unavailableSoftGlowOpacity
        : stateSoftGlowOpacity

    readonly property color wideGlowColor:
        pressed
        ? pressedWideGlowColor
        : cursorPrimaryNotActivated
        ? keyboardSelectedWideGlowColor
        : selected
        ? selectedWideGlowColor
        : hovered
        ? hoverWideGlowColor
        : idleWideGlowColor

    readonly property real stateWideGlowOpacity:
        pressed
        ? wideGlowPressedOpacity
        : cursorPrimaryNotActivated
        ? wideGlowKeyboardSelectedOpacity
        : selected
        ? wideGlowSelectedOpacity
        : hovered
        ? wideGlowHoverOpacity
        : wideGlowIdleOpacity

    readonly property real effectiveWideGlowOpacity:
        !available && unavailableWideGlowOpacity >= 0.0
        ? unavailableWideGlowOpacity
        : stateWideGlowOpacity

    implicitWidth: 112
    implicitHeight: 30
    radius: 0
    clip: false

    opacity:
        available
        ? availableOpacity
        : unavailableOpacity

    color:
        actionButton.withOpacity(
            fillColor,
            available ? 1.0 : unavailableFillOpacity
        )

    border.width: activeBorderWidth
    border.color:
        actionButton.withOpacity(
            activeBorderColor,
            available ? 1.0 : unavailableBorderOpacity
        )

    function withOpacity(baseColor, alphaValue) {
        const alpha = Math.max(0.0, Math.min(1.0, Number(alphaValue)));
        return Qt.rgba(
            baseColor.r,
            baseColor.g,
            baseColor.b,
            baseColor.a * alpha
        );
    }

    signal triggered(var mouseEvent)
    signal clicked(var mouseEvent)
    signal leftClicked(var mouseEvent)
    signal rightClicked(var mouseEvent)
    signal hoverEntered()
    signal hoverExited()
    signal pointerMoved(var mouseEvent)
    signal pressStateChanged(bool pressed)
    signal wheel(var wheelEvent)

    Item {
        id: contentLayer

        anchors.fill: parent
        z: 1

        Item {
            id: contentHost
            anchors.fill: parent

            opacity:
                actionButton.available
                ? 1.0
                : actionButton.unavailableContentOpacity

            GohuText {
                id: labelText

                anchors.centerIn: parent
                anchors.horizontalCenterOffset: actionButton.labelCenterOffsetX
                anchors.verticalCenterOffset: actionButton.labelCenterOffsetY
                width: Math.max(0, parent.width - actionButton.contentPadding)

                visible: actionButton.showLabel
                text: actionButton.label

                font.pixelSize: actionButton.labelPixelSize
                fontSizeMode: actionButton.labelFontSizeMode
                minimumPixelSize: actionButton.labelMinimumPixelSize

                horizontalAlignment: actionButton.labelHorizontalAlignment
                elide: actionButton.labelElide

                color: actionButton.foregroundColor
            }
        }

        SafeDropShadow {
            id: contentGlow

            readonly property bool labelIsLocalSource:
                sourceAttached && actionButton.trackLabelGlowLocally
                && actionButton.contentGlowSource === labelText
                && labelText.parent === contentHost
            readonly property point sourceOrigin:
                !sourceAttached ? Qt.point(0, 0)
                : labelIsLocalSource
                  ? Qt.point(contentHost.x + labelText.x,
                             contentHost.y + labelText.y)
                  : actionButton.contentGlowSource.mapToItem(
                        contentLayer, 0, 0
                    )

            x: sourceOrigin.x
            y: sourceOrigin.y
            width:
                sourceAttached
                ? actionButton.contentGlowSource.width
                : 0
            height:
                sourceAttached
                ? actionButton.contentGlowSource.height
                : 0

            safeSource: actionButton.contentGlowSource
            requestedVisible:
                actionButton.contentGlowEnabled
                && actionButton.effectiveContentGlowOpacity > 0.0

            horizontalOffset: 0
            verticalOffset: 0
            radius: actionButton.contentGlowRadius
            samples: actionButton.contentGlowSamples

            color: actionButton.contentGlowColor
            opacity: actionButton.effectiveContentGlowOpacity
            transparentBorder: true
        }
    }

    MouseArea {
        id: mouse

        anchors.fill: parent
        z: 10

        enabled: actionButton.pointerActive
        hoverEnabled: true
        acceptedButtons: actionButton.acceptedButtons

        cursorShape:
            actionButton.interactive
            ? actionButton.pointerCursorShape
            : Qt.ArrowCursor

        onEntered: {
            actionButton.hoverEntered();
        }

        onExited: {
            actionButton.hoverExited();
        }

        onPositionChanged: function(mouseEvent) {
            // Actual mouse movement reunifies the selectors. Entering
            // due to a layout change or remaining stationary does not.
            const nav = actionButton.contentNavigator;
            if (nav && actionButton.keyboardNavTarget
                    && typeof nav.followPointer === "function")
                nav.followPointer(actionButton);
            actionButton.pointerMoved(mouseEvent);
        }

        onPressedChanged: {
            actionButton.pressStateChanged(
                actionButton.interactive && pressed
            );
        }

        onClicked: function(mouseEvent) {
            if (!actionButton.interactive)
                return;

            actionButton.clicked(mouseEvent);

            if (mouseEvent.button === Qt.LeftButton) {
                actionButton.leftClicked(mouseEvent);
                actionButton.triggered(mouseEvent);
            } else if (mouseEvent.button === Qt.RightButton) {
                actionButton.rightClicked(mouseEvent);
            }
        }

        onWheel: function(wheelEvent) {
            actionButton.wheel(wheelEvent);
        }
    }

    // Rich action consumers may place nested interactive controls here.
    // This host intentionally sits above the shared pointer layer so controls
    // such as AppControl's favorite star remain independently clickable.
    Item {
        id: interactionHost
        anchors.fill: parent
        z: 20
    }

    // Only the perimeter is sampled, and the result is behind the opaque
    // parent face. No full-rectangle color source, no imperative state writes.
    Loader {
        id: normalPerimeter
        objectName: "actionButtonNormalPerimeter"
        anchors.fill: parent
        z: -1
        active: actionButton.washSafePerimeter && actionButton.perimeterGlowEnabled
            && actionButton.perimeterGlowOpacity > 0 && actionButton.available && actionButton.visible
        visible: active
        sourceComponent: Rectangle {
            color: "transparent"
            border.width: 1
            border.color: actionButton.activeBorderColor
            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: actionButton.softGlowColor
                shadowOpacity: actionButton.perimeterGlowOpacity
                shadowBlur: 0.5
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
            }
        }
    }

    RectangularShadow {
        objectName: "actionButtonBroadSoftGlow"
        anchors.fill: parent
        anchors.margins: -actionButton.softGlowMargin

        spread: actionButton.softGlowSpread
        z: -1

        visible:
            !actionButton.washSafePerimeter && actionButton.softGlowEnabled
            && actionButton.effectiveSoftGlowOpacity > 0.0

        opacity: actionButton.effectiveSoftGlowOpacity
        color: actionButton.softGlowColor
    }

    RectangularShadow {
        objectName: "actionButtonBroadWideGlow"
        anchors.fill: parent

        spread: actionButton.wideGlowSpread
        z: -2

        visible:
            !actionButton.washSafePerimeter && actionButton.wideGlowEnabled
            && actionButton.effectiveWideGlowOpacity > 0.0

        opacity: actionButton.effectiveWideGlowOpacity
        color: actionButton.wideGlowColor
    }
}
