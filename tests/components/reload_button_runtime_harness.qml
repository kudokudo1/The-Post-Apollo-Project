import QtQuick
import QtQuick.Window
import "../../components" as Shared

// Exercise the real reusable button and its inherited ActionButton pointer
// engine. Do not instantiate TimeSettings, a shell window, or a host process.
Window {
    id: harness
    width: 290
    height: 150
    visible: true
    color: "#121212"

    property int reloadRequests: 0
    readonly property color expectedYellow: Shared.Colors.yellow
    readonly property color expectedOrange: Shared.Colors.orange
    readonly property color expectedMagenta: Shared.Colors.magenta
    readonly property color expectedBlack: Shared.Colors.black

    Shared.ReloadButton {
        id: button
        objectName: "universalReloadButton"
        x: 34
        y: 35
        onReloadRequested: harness.reloadRequests += 1
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
