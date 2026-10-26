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
        textFormat: Text.StyledText
        color: Colors.white
        // Preserve the ORIGINAL glyph advances for the phone and right star.
        // The left marks retain their original place in the shaping run but
        // are transparent there; only their visible overlay moves right.
        text: "<font color='transparent'>࣪˖</font><font color='" + sessionsDock.foregroundColor
              + "'>☎︎</font>๋࣭✧"

        GohuText {
            id: sessionsLeftOrnaments
            // Move ONLY the left white marks 3px right. The phone and the
            // entire right-side sequence remain at the original text positions.
            anchors.left: parent.left
            anchors.leftMargin: 3
            anchors.baseline: parent.baseline
            font.pixelSize: sessionsIcon.font.pixelSize
            textFormat: Text.PlainText
            color: Colors.white
            text: "࣪˖"
        }
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
