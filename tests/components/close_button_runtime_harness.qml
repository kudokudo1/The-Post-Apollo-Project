import QtQuick
import QtQuick.Window
import "../../components" as Shared

// Offscreen harness for the actual registered CloseButton, not a visual mock.
Window {
    id: harness
    width: 290
    height: 150
    visible: true
    color: "#121212"

    property int closeRequests: 0

    Shared.CloseButton {
        id: button
        objectName: "universalCloseButton"
        x: 34
        y: 35
        onCloseRequested: harness.closeRequests += 1
    }

    readonly property var glyph: button.contentItem.children[0]
    readonly property var glow: button.contentItem.parent.children[1]
    readonly property bool sourceAligned:
        glow.labelIsLocalSource && glow.sourceAttached
        && Math.abs(glow.x - (button.contentItem.x + glyph.x)) < 0.1
        && Math.abs(glow.y - (button.contentItem.y + glyph.y)) < 0.1
        && Math.abs(glow.width - glyph.width) < 0.1
        && Math.abs(glow.height - glyph.height) < 0.1
}
