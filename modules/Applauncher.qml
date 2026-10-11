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

    GohuText {
        id: appmenuIcon
        anchors.centerIn: parent

        text: "-⋆♱⋆-"
        font.pixelSize: 19
        font.weight: 700
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
