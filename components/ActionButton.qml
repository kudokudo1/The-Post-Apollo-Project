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

    // Base identity. These defaults are AppControl-derived starting points,
    // not a claim that every migrated button should be normalized to them.
    property color accentColor: Colors.cyan
    property color destructiveColor: Colors.red

    property color idleFillColor: Colors.black
    property color hoverFillColor: Colors.yellow
    property color pressedFillColor:
        destructive ? destructiveColor : Colors.magenta
    property color selectedFillColor: Colors.yellow
    property color keyboardSelectedFillColor: selectedFillColor

    property color idleForegroundColor: accentColor
    property color hoverForegroundColor: Colors.orange
    property color pressedForegroundColor: Colors.black
    property color selectedForegroundColor: Colors.magenta
    property color keyboardSelectedForegroundColor: selectedForegroundColor

    property color idleBorderColor: accentColor
    property color hoverBorderColor: Colors.orange
    property color pressedBorderColor:
        destructive ? Colors.black : Colors.magenta
    property color selectedBorderColor: Colors.magenta
    property color keyboardSelectedBorderColor: Colors.orange

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

    property color idleContentGlowColor: accentColor
    property color hoverContentGlowColor: Colors.orange
    property color pressedContentGlowColor:
        destructive ? destructiveColor : Colors.magenta
    property color selectedContentGlowColor: Colors.magenta
    property color keyboardSelectedContentGlowColor: Colors.orange

    property real contentGlowIdleOpacity: 0.34
    property real contentGlowHoverOpacity: 0.72
    property real contentGlowPressedOpacity: 0.0
    property real contentGlowSelectedOpacity: 0.72
    property real contentGlowKeyboardSelectedOpacity: 0.72

    property real contentGlowRadius: 7
    property int contentGlowSamples: 7

    // Primary action halo. AppControl commonly uses one rectangular halo.
    property bool softGlowEnabled: true
    property real softGlowSpread: 3
    property real softGlowMargin: 0

    property color idleSoftGlowColor: accentColor
    property color hoverSoftGlowColor: Colors.orange
    property color pressedSoftGlowColor:
        destructive ? destructiveColor : Colors.magenta
    property color selectedSoftGlowColor: Colors.magenta
    property color keyboardSelectedSoftGlowColor: Colors.orange

    property real softGlowIdleOpacity: 0.22
    property real softGlowHoverOpacity: 0.56
    property real softGlowPressedOpacity: 0.60
    property real softGlowSelectedOpacity: 0.56
    property real softGlowKeyboardSelectedOpacity: 0.56

    // Optional second halo for richer descendants such as GitW's local
    // ActionButton. Disabled by default so compact controls stay lightweight.
    property bool wideGlowEnabled: false
    property real wideGlowSpread: 10

    property color idleWideGlowColor: idleSoftGlowColor
    property color hoverWideGlowColor: hoverSoftGlowColor
    property color pressedWideGlowColor: pressedSoftGlowColor
    property color selectedWideGlowColor: selectedSoftGlowColor
    property color keyboardSelectedWideGlowColor:
        keyboardSelectedSoftGlowColor

    property real wideGlowIdleOpacity: 0.015
    property real wideGlowHoverOpacity: 0.08
    property real wideGlowPressedOpacity: 0.10
    property real wideGlowSelectedOpacity: 0.07
    property real wideGlowKeyboardSelectedOpacity: 0.08

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
        : keyboardSelected
        ? keyboardSelectedFillColor
        : selected
        ? selectedFillColor
        : hovered
        ? hoverFillColor
        : idleFillColor

    readonly property color foregroundColor:
        pressed
        ? pressedForegroundColor
        : keyboardSelected
        ? keyboardSelectedForegroundColor
        : selected
        ? selectedForegroundColor
        : hovered
        ? hoverForegroundColor
        : idleForegroundColor

    readonly property color activeBorderColor:
        pressed
        ? pressedBorderColor
        : keyboardSelected
        ? keyboardSelectedBorderColor
        : selected
        ? selectedBorderColor
        : hovered
        ? hoverBorderColor
        : idleBorderColor

    readonly property int activeBorderWidth:
        pressed
        ? pressedBorderWidth
        : keyboardSelected
        ? keyboardSelectedBorderWidth
        : selected
        ? selectedBorderWidth
        : hovered
        ? hoverBorderWidth
        : idleBorderWidth

    readonly property color contentGlowColor:
        pressed
        ? pressedContentGlowColor
        : keyboardSelected
        ? keyboardSelectedContentGlowColor
        : selected
        ? selectedContentGlowColor
        : hovered
        ? hoverContentGlowColor
        : idleContentGlowColor

    readonly property real stateContentGlowOpacity:
        pressed
        ? contentGlowPressedOpacity
        : keyboardSelected
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
        : keyboardSelected
        ? keyboardSelectedSoftGlowColor
        : selected
        ? selectedSoftGlowColor
        : hovered
        ? hoverSoftGlowColor
        : idleSoftGlowColor

    readonly property real stateSoftGlowOpacity:
        pressed
        ? softGlowPressedOpacity
        : keyboardSelected
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
        : keyboardSelected
        ? keyboardSelectedWideGlowColor
        : selected
        ? selectedWideGlowColor
        : hovered
        ? hoverWideGlowColor
        : idleWideGlowColor

    readonly property real stateWideGlowOpacity:
        pressed
        ? wideGlowPressedOpacity
        : keyboardSelected
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

            readonly property point sourceOrigin:
                sourceAttached
                ? actionButton.contentGlowSource.mapToItem(
                      contentLayer,
                      0,
                      0
                  )
                : Qt.point(0, 0)

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

    RectangularShadow {
        anchors.fill: parent
        anchors.margins: -actionButton.softGlowMargin

        spread: actionButton.softGlowSpread
        z: -1

        visible:
            actionButton.softGlowEnabled
            && actionButton.effectiveSoftGlowOpacity > 0.0

        opacity: actionButton.effectiveSoftGlowOpacity
        color: actionButton.softGlowColor
    }

    RectangularShadow {
        anchors.fill: parent

        spread: actionButton.wideGlowSpread
        z: -2

        visible:
            actionButton.wideGlowEnabled
            && actionButton.effectiveWideGlowOpacity > 0.0

        opacity: actionButton.effectiveWideGlowOpacity
        color: actionButton.wideGlowColor
    }
}
