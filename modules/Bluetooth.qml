import QtQuick
import Quickshell
import "../components"

DockButton {
    id: bluetoothDock

    implicitHeight: 50
    implicitWidth: 85

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.white
    pressedForegroundColor: Colors.white

    normalContentGlowColor: Colors.cyan
    hoverContentGlowColor: Colors.orange
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: Colors.cyan
    hoverDockGlowColor: Colors.orange
    pressedDockGlowColor: Colors.magenta

    contentGlowSource: bluetoothText

    Text {
        id: bluetoothText
        anchors.centerIn: parent

        text: "(˓✟˒)"
        font.pixelSize: 20
        color: bluetoothDock.foregroundColor
    }
}
