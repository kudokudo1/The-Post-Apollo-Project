import QtQuick
import Quickshell
import "../components"

DockButton {
    id: dock

    implicitWidth: Math.max(118, gitMark.implicitWidth + 18)
    implicitHeight: 50

    property bool menuOpen: false

    open: menuOpen

    // Keep Git's semantic yellow perimeter and orange artwork while its
    // numerical intensity follows the new shared dock recipe.
    normalContentGlowColor: Colors.orange
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.orange
    normalDockGlowColor: Colors.yellow
    hoverDockGlowColor: Colors.yellow
    pressedDockGlowColor: Colors.yellow

    contentGlowSource: gitMark

    signal toggleRequested()

    Row {
        id: gitMark

        anchors.centerIn: parent
        spacing: 5

        GohuText {
            id: gitDataMark

            text: ""
            font.pixelSize: 38
            anchors.verticalCenter: parent.verticalCenter
            color: dock.open ? dock.openForegroundColor : Colors.white
            opacity: 1.0

            transform: Scale {
                origin.x: gitDataMark.width / 2
                origin.y: gitDataMark.height / 2
                xScale: 0.54
                yScale: 1.26
            }
        }

        // Keep the cat shaped as one mark; the parenthesis is white closed,
        // magenta on open, matching the shared DockButton foreground state.
        GohuText {
            id: gitCatMark
            anchors.verticalCenter: parent.verticalCenter
            textFormat: Text.StyledText
            text: "≽<font color='" + dock.foregroundColor + "'>(</font>•⩊•マ≼"
            font.pixelSize: 16
            color: dock.open ? dock.openForegroundColor : Colors.yellow
        }
    }

    onLeftClicked: {
        dock.toggleRequested();
    }

}
