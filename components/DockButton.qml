import QtQuick
import Quickshell
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

Rectangle {
    id: dockButton

    // Arbitrary module artwork lives inside the reusable visual shell.
    default property alias contentData: contentHost.data

    property bool open: false
    property bool interactive: true
    property int acceptedButtons: Qt.LeftButton | Qt.RightButton

    // Fill + foreground state.
    property color closedFillColor: Colors.black
    property color openFillColor: Colors.yellow

    property color normalForegroundColor: Colors.white
    property color hoverForegroundColor: normalForegroundColor
    property color pressedForegroundColor: normalForegroundColor
    property color openForegroundColor: Colors.magenta

    // Content glow and dock halo colors.
    // Defaults are intentionally derived from the Git button.
    property color normalContentGlowColor: Colors.orange
    property color hoverContentGlowColor: Colors.orange
    property color pressedContentGlowColor: Colors.orange

    property color normalDockGlowColor: Colors.yellow
    property color hoverDockGlowColor: Colors.yellow
    property color pressedDockGlowColor: Colors.yellow

    property color openGlowColor: Colors.magenta

    // Git-derived content glow values.
    property real contentGlowIdleOpacity: 0.76
    property real contentGlowHoverOpacity: 0.96
    property real contentGlowPressedOpacity: 1.0
    property real contentGlowOpenOpacity: 1.0

    property real contentGlowIdleRadius: 14
    property real contentGlowActiveRadius: 18
    property int contentGlowIdleSamples: 15
    property int contentGlowActiveSamples: 21

    // Git-derived tight rear halo.
    property real softGlowIdleOpacity: 0.32
    property real softGlowHoverOpacity: 0.48
    property real softGlowPressedOpacity: 0.60
    property real softGlowOpenOpacity: 0.86
    property real softGlowSpread: 3

    // Git-derived wide front-facing wash.
    property real wideGlowIdleOpacity: 0.06
    property real wideGlowHoverOpacity: 0.09
    property real wideGlowPressedOpacity: 0.12
    property real wideGlowOpenOpacity: 0.22
    property real wideGlowSpread: 10

    property bool contentGlowEnabled: true
    property bool softGlowEnabled: true
    property bool wideGlowEnabled: true

    // Optional exact artwork source for the content glow. Consumers with
    // composite/custom marks should point this at the mark itself.
    property Item contentGlowSource: contentHost

    readonly property bool hovered: interactive && mouse.containsMouse
    readonly property bool pressed: interactive && mouse.pressed
    readonly property bool energized: open || pressed || hovered

    readonly property color foregroundColor: open
                                             ? openForegroundColor
                                             : pressed
                                             ? pressedForegroundColor
                                             : hovered
                                             ? hoverForegroundColor
                                             : normalForegroundColor

    readonly property color contentGlowColor: open
                                              ? openGlowColor
                                              : pressed
                                              ? pressedContentGlowColor
                                              : hovered
                                              ? hoverContentGlowColor
                                              : normalContentGlowColor

    readonly property color dockGlowColor: open
                                           ? openGlowColor
                                           : pressed
                                           ? pressedDockGlowColor
                                           : hovered
                                           ? hoverDockGlowColor
                                           : normalDockGlowColor

    readonly property real contentGlowOpacity: open
                                                ? contentGlowOpenOpacity
                                                : pressed
                                                ? contentGlowPressedOpacity
                                                : hovered
                                                ? contentGlowHoverOpacity
                                                : contentGlowIdleOpacity

    readonly property real softGlowOpacity: open
                                             ? softGlowOpenOpacity
                                             : pressed
                                             ? softGlowPressedOpacity
                                             : hovered
                                             ? softGlowHoverOpacity
                                             : softGlowIdleOpacity

    readonly property real wideGlowOpacity: open
                                             ? wideGlowOpenOpacity
                                             : pressed
                                             ? wideGlowPressedOpacity
                                             : hovered
                                             ? wideGlowHoverOpacity
                                             : wideGlowIdleOpacity

    implicitWidth: 130
    implicitHeight: 50

    color: open ? openFillColor : closedFillColor
    clip: false

    signal clicked(var mouseEvent)
    signal leftClicked(var mouseEvent)
    signal rightClicked(var mouseEvent)
    signal hoverEntered()
    signal hoverExited()

    Item {
        id: contentHost

        anchors.fill: parent
        z: 0
    }

    DropShadow {
        readonly property point sourceOrigin: dockButton.contentGlowSource
                                              ? dockButton.contentGlowSource.mapToItem(dockButton, 0, 0)
                                              : Qt.point(0, 0)

        x: sourceOrigin.x
        y: sourceOrigin.y
        width: dockButton.contentGlowSource ? dockButton.contentGlowSource.width : 0
        height: dockButton.contentGlowSource ? dockButton.contentGlowSource.height : 0

        source: dockButton.contentGlowSource

        horizontalOffset: 0
        verticalOffset: 0

        radius: dockButton.energized
                ? dockButton.contentGlowActiveRadius
                : dockButton.contentGlowIdleRadius

        samples: dockButton.energized
                 ? dockButton.contentGlowActiveSamples
                 : dockButton.contentGlowIdleSamples

        z: 2
        visible: dockButton.contentGlowEnabled
        opacity: dockButton.contentGlowOpacity
        color: dockButton.contentGlowColor

        transparentBorder: true
    }

    MouseArea {
        id: mouse

        anchors.fill: parent
        z: 10

        enabled: dockButton.interactive
        hoverEnabled: true
        acceptedButtons: dockButton.acceptedButtons

        onEntered: {
            dockButton.hoverEntered();
        }

        onExited: {
            dockButton.hoverExited();
        }

        onClicked: function(mouseEvent) {
            dockButton.clicked(mouseEvent);

            if (mouseEvent.button === Qt.LeftButton)
                dockButton.leftClicked(mouseEvent);
            else if (mouseEvent.button === Qt.RightButton)
                dockButton.rightClicked(mouseEvent);
        }
    }

    RectangularShadow {
        anchors.fill: parent

        spread: dockButton.softGlowSpread
        z: -1

        visible: dockButton.softGlowEnabled
        opacity: dockButton.softGlowOpacity
        color: dockButton.dockGlowColor
    }

    RectangularShadow {
        anchors.fill: parent

        spread: dockButton.wideGlowSpread
        z: 1

        visible: dockButton.wideGlowEnabled
        opacity: dockButton.wideGlowOpacity
        color: dockButton.dockGlowColor
    }
}
