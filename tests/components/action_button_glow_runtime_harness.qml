import QtQuick
import QtQuick.Window
import "../../components" as Shared

// The real ActionButton is loaded, not a mock geometry function.
// Introspect the default content host's one glyph and one sampled effect.
// Run only in the offscreen Qt test environment.
Window {
    id: harness
    width: 420
    height: 170
    visible: true
    color: "#1B0623"

    Shared.ActionButton {
        id: labelButton
        objectName: "glowLabelButton"
        x: 15
        y: 14
        width: 135
        height: 38
        label: "EDIT"
    }

    Shared.ActionButton {
        id: customButton
        objectName: "customGlowButton"
        x: 15
        y: 75
        width: 150
        height: 34
        label: ""
        contentGlowSource: customMark
        Item {
            id: customMark
            x: 19
            y: 7
            width: 55
            height: 17
        }
    }

    readonly property var sourceGlyph:
        labelButton.contentItem.children[0]
    readonly property var glyphEffect:
        labelButton.contentItem.parent.children[1]
    readonly property var customEffect:
        customButton.contentItem.parent.children[1]

    readonly property real expectedX:
        labelButton.contentItem.x + sourceGlyph.x
    readonly property real expectedY:
        labelButton.contentItem.y + sourceGlyph.y
    readonly property real glowX: glyphEffect.x
    readonly property real glowY: glyphEffect.y
    readonly property real glyphWidth: sourceGlyph.width
    readonly property real glyphHeight: sourceGlyph.height
    readonly property real glowWidth: glyphEffect.width
    readonly property real glowHeight: glyphEffect.height
    readonly property bool localOrigin: glyphEffect.labelIsLocalSource
    readonly property bool hasSource: glyphEffect.sourceAttached
    readonly property bool customUsesFallback: !customEffect.labelIsLocalSource
}
