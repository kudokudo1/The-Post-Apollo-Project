import QtQuick
import Quickshell
import "../components"

DockButton {
    id: dock

    implicitHeight: 50
    implicitWidth: Math.max(72, hospitalMark.implicitWidth + 18)

    // Keep these exposed so the mark can be tuned without rebuilding the button.
    property int beatPixelSize: 11
    property int centerPixelSize: 28
    property int markSpacing: 0

    property bool menuOpen: false
    signal toggleRequested()

    open: menuOpen

    normalForegroundColor: Colors.white
    hoverForegroundColor: Colors.magenta
    pressedForegroundColor: Colors.magenta

    normalContentGlowColor: Colors.magenta
    hoverContentGlowColor: Colors.magenta
    pressedContentGlowColor: Colors.magenta

    normalDockGlowColor: Colors.magenta
    hoverDockGlowColor: Colors.magenta
    pressedDockGlowColor: Colors.magenta

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
    wideGlowHoverOpacity: 0.09
    wideGlowPressedOpacity: 0.12

    contentGlowSource: hospitalMark

    Row {
        id: hospitalMark

        anchors.centerIn: parent
        spacing: dock.markSpacing
        height: 34

        Text {
            height: hospitalMark.height
            text: "ﮩ٨ـﮩﮩ"
            font.pixelSize: dock.beatPixelSize
            verticalAlignment: Text.AlignVCenter
            color: dock.foregroundColor
        }

        NotoText {
            height: hospitalMark.height
            text: "⚚"
            font.pixelSize: dock.centerPixelSize
            verticalAlignment: Text.AlignVCenter
            color: dock.foregroundColor
        }

        Text {
            height: hospitalMark.height
            text: "ﮩ٨ـﮩ"
            font.pixelSize: dock.beatPixelSize
            verticalAlignment: Text.AlignVCenter
            color: dock.foregroundColor
        }
    }

    onLeftClicked: {
        dock.toggleRequested();
    }
}
