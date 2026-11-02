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

    // Keep Social's existing green identity while closed. In the open
    // state, both ornament runs join the telephone's magenta foreground
    // and the DockButton's existing magenta composite artwork glow.
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
        // Right-side unstyled stars use this default; phone stays styled
        // separately via DockButton.foregroundColor.
        color: sessionsDock.open ? sessionsDock.openForegroundColor : Colors.white
        // Preserve original text advances: neither the larger phone nor the
        // independently positioned left ornament can resize the DockButton.
        // The invisible original phone keeps the right stars exactly in place.
        text: "<font color='transparent'>࣪˖☎︎</font>๋࣭✧"

        GohuText {
            id: sessionsLeftOrnaments
            // Original left-only offset was +3px. Shift by another +7px.
            // Right-side ornaments retain the original shaping position.
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.baseline: parent.baseline
            font.pixelSize: sessionsIcon.font.pixelSize
            textFormat: Text.PlainText
            // Left overlay must match the right stars when Social is open.
            color: sessionsDock.open ? sessionsDock.openForegroundColor : Colors.white
            text: "࣪˖"
        }

        // Measure the original phone width without changing the shaping run.
        // Invisible; the same 21px Gohu glyph remains the width reference.
        GohuText {
            id: sessionsPhoneAdvance
            visible: false
            font.pixelSize: sessionsIcon.font.pixelSize
            textFormat: Text.PlainText
            text: "☎︎"
        }

        GohuText {
            id: sessionsPhoneFace
            // Enlarge ONLY the phone artwork. The parent styled text retains
            // its previous implicitWidth and the dock keeps its existing size.
            x: sessionsLeftOrnaments.implicitWidth
               + (sessionsPhoneAdvance.implicitWidth - implicitWidth) / 2
            anchors.baseline: parent.baseline
            font.pixelSize: 24
            textFormat: Text.PlainText
            text: "☎︎"
            color: sessionsDock.foregroundColor
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
