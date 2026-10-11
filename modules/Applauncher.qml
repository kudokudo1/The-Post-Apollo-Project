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

    // The compound launcher mark glows as one cluster; framing stars stay white.
    Row {
        id: appmenuIcon
        anchors.centerIn: parent
        spacing: 0

        GohuText {
            text: "-⋆"
            font.pixelSize: 19
            font.weight: 700
            color: Colors.white
        }
        GohuText {
            text: "♱"
            font.pixelSize: 19
            font.weight: 700
            color: appmenuRoot.foregroundColor
        }
        GohuText {
            text: "⋆-"
            font.pixelSize: 19
            font.weight: 700
            color: Colors.white
        }
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
