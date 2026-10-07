import QtQuick
import Quickshell
import "../components"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

DockButton {
    id: sessionsDock

    property var messagingWindow
    readonly property bool menuOpen:
        messagingWindow && messagingWindow.menuOpen

    implicitHeight: 50
    implicitWidth: 25
    radius: 0

    open: menuOpen

    normalDockGlowColor: Colors.omnitrix
    hoverDockGlowColor: Colors.omnitrix
    pressedDockGlowColor: Colors.omnitrix

    normalContentGlowColor: Colors.omnitrix
    hoverContentGlowColor: Colors.omnitrix
    pressedContentGlowColor: Colors.omnitrix

    contentGlowIdleOpacity: 0.60
    contentGlowHoverOpacity: 0.80
    contentGlowPressedOpacity: 1.0
    contentGlowHoverRadius: 14
    contentGlowPressedRadius: 14
    contentGlowHoverSamples: 15
    contentGlowPressedSamples: 15

    softGlowIdleOpacity: 0.40
    softGlowHoverOpacity: 0.50
    softGlowPressedOpacity: 0.60

    wideGlowIdleOpacity: 0.07
    wideGlowHoverOpacity: 0.10
    wideGlowPressedOpacity: 0.11

    contentGlowSource: sessionsIcon

    Image {
        id: sessionsIcon

        anchors.centerIn: parent

        source: Qt.resolvedUrl("../assets/Sessions.png")

        width: sessionsDock.width - 10
        height: sessionsDock.height - 5

        fillMode: Image.PreserveAspectFit
        smooth: false
    }

    ColorOverlay {
        anchors.fill: sessionsIcon
        source: sessionsIcon
        color: Colors.magenta
        visible: sessionsDock.open
    }

    onLeftClicked: {
        // Do not change MessagingW.menuOpen while DockButton's internal
        // MouseArea is still delivering the click. Finish the event first.
        Qt.callLater(function () {
            if (!sessionsDock.messagingWindow)
                return;

            sessionsDock.messagingWindow.menuOpen =
                !sessionsDock.messagingWindow.menuOpen;
        });
    }
}
