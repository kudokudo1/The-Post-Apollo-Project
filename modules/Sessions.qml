import QtQuick
import Quickshell
import "../components"

DockButton {
    id: sessionsDock

    property var messagingWindow
    readonly property bool menuOpen:
        messagingWindow && messagingWindow.menuOpen

    implicitHeight: 50
    // The new decorated telephone needs more room than the original PNG.
    // Follow the original text metrics rather than clipping its ornaments.
    implicitWidth: Math.max(65, Math.ceil(sessionsIcon.implicitWidth) + 16)
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

    NotoText {
        id: sessionsIcon
        anchors.centerIn: parent
        font.pixelSize: 22
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
