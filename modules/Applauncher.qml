import QtQuick
import Quickshell
import "../components"

DockButton {
    id: appmenuRoot

    implicitWidth: 65
    implicitHeight: 50

    property var appControlWindow
    readonly property bool menuOpen:
        appControlWindow && appControlWindow.menuOpen

    open: menuOpen

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    contentGlowSource: appmenuIcon

    // One original text run preserves glyph metrics; only the core recolors.
    GohuText {
        id: appmenuIcon
        anchors.centerIn: parent
        textFormat: Text.StyledText
        text: "-⋆<font color='" + appmenuRoot.foregroundColor + "'>♱</font>⋆-"
        font.pixelSize: 19
        font.weight: 700
        // Structural stars follow the same foreground state as the main glyph.
        color: appmenuRoot.foregroundColor
    }

    onLeftClicked: {
        console.log("applauncherbutton", "left clicked");

        if (appControlWindow)
            appControlWindow.menuOpen = !appControlWindow.menuOpen;
    }

    onRightClicked: {
        console.log("applauncherbutton", "right clicked");
    }
}
