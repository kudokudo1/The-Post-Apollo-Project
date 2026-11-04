import QtQuick
import Quickshell
import "../components"

// City identity: white star ornaments, yellow central city.
// Closed perimeter/artwork halo is blue; open perimeter/artwork halo magenta.
DockButton {
    id: companyDock

    property bool menuOpen: false
    signal toggleRequested()

    implicitHeight: 50
    implicitWidth: Math.max(86, Math.ceil(companyMark.implicitWidth) + 22)
    open: menuOpen

    normalForegroundColor: Colors.yellow
    hoverForegroundColor: Colors.yellow
    pressedForegroundColor: Colors.yellow
    openForegroundColor: Colors.yellow

    normalContentGlowColor: Colors.blue
    hoverContentGlowColor: Colors.blue
    pressedContentGlowColor: Colors.blue
    normalDockGlowColor: Colors.blue
    hoverDockGlowColor: Colors.blue
    pressedDockGlowColor: Colors.blue
    openGlowColor: Colors.magenta

    // Black selected fill keeps yellow center and white ornaments legible.
    openFillColor: Colors.black
    contentGlowSource: companyMark

    Row {
        id: companyMark
        anchors.centerIn: parent
        spacing: 1

        NotoText {
            anchors.verticalCenter: parent.verticalCenter
            textFormat: Text.PlainText
            text: ". ݁₊⊹"
            font.pixelSize: 21
            color: Colors.white
        }

        NotoText {
            anchors.verticalCenter: parent.verticalCenter
            textFormat: Text.PlainText
            // U+FE0E requests monochrome text rendering so yellow tint
            // is not silently replaced by a platform color-emoji glyph.
            text: "🏙︎"
            font.pixelSize: 24
            color: Colors.yellow
        }

        NotoText {
            anchors.verticalCenter: parent.verticalCenter
            textFormat: Text.PlainText
            text: "๋࣭⭑"
            font.pixelSize: 21
            color: Colors.white
        }
    }

    onLeftClicked: toggleRequested()
}
