import QtQuick
import Quickshell
import "../components"

DockButton {
    id: sessionsDock

    property var messagingWindow
    readonly property bool menuOpen:
        messagingWindow && messagingWindow.menuOpen

    implicitHeight: 50
    // A modestly tighter icon footprint; preserve the shared bar's 50px
    // vertical rail and keep 14px horizontal room for the Gohu ornaments.
    implicitWidth: Math.max(63, Math.ceil(sessionsIcon.implicitWidth) + 14)
    radius: 0

    open: menuOpen

    // Keep Social's existing green identity while closed and the standard
    // magenta foreground while open. Decorations stay white in both states.
    normalForegroundColor: Colors.omnitrix
    hoverForegroundColor: Colors.omnitrix
    pressedForegroundColor: Colors.omnitrix

    normalDockGlowColor: Colors.omnitrix
    hoverDockGlowColor: Colors.omnitrix
    pressedDockGlowColor: Colors.omnitrix

    normalContentGlowColor: Colors.omnitrix
    hoverContentGlowColor: Colors.omnitrix
    pressedContentGlowColor: Colors.omnitrix

    // Sample the complete ornament once; DockButton still owns all glow,
    // open-fill, click handling, and state-transition behavior.
    contentGlowSource: sessionsIcon

    GohuText {
        id: sessionsIcon
        anchors.centerIn: parent
        font.pixelSize: 21
        // Bring the left ornaments closer to the phone without splitting
        // the combining-mark sequence into independently shaped text nodes.
        font.letterSpacing: -0.8
        textFormat: Text.StyledText
        color: Colors.white
        // Original glyph order: ࣪˖☎︎๋࣭✧.
        // Only the telephone responds to Social's active-state color.
        text: "࣪˖<font color='" + sessionsDock.foregroundColor
              + "'>☎︎</font>๋࣭✧"
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
