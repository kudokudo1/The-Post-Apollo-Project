import QtQuick
import QtQuick.Window
import "../../components" as Shared

// The real ActionButton is loaded, not a mock geometry function.
// Introspect the default content host's one glyph and one sampled effect.
// Run only in the offscreen Qt test environment.
Window {
    id: harness
    width: 480
    height: 240
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

    Shared.ActionButton {
        id: redButton
        objectName: "redActionButton"
        x: 200; y: 16; width: 140; height: 38
        label: "DELETE"
        accentColor: Shared.Colors.red
        destructive: true
    }
    Shared.CloseButton {
        objectName: "redActionCloseComparison"
        x: 360; y: 16
    }
    Shared.ActionButton {
        objectName: "redNormalComparison"
        x: 200; y: 80
        label: "NORMAL"
        accentColor: Shared.Colors.red
        normalFace: true
    }
    Shared.ActionButton {
        objectName: "redExplicitComparison"
        x: 200; y: 130
        label: "CUSTOM"
        accentColor: Shared.Colors.red
        idleForegroundColor: Shared.Colors.cyan
    }
    Shared.ActionButton {
        objectName: "deliberateBroadComparison"
        x: 350; y: 80; width: 100; height: 30
        label: "SPECIAL"
        washSafePerimeter: false
    }
    Shared.ActionButton {
        objectName: "quietComparison"
        x: 350; y: 130; width: 100; height: 30
        label: "QUIET"
        softGlowEnabled: false
        contentGlowEnabled: false
    }
    Shared.ModeButton {
        objectName: "hierarchyModeButton"
        x: 15; y: 160; width: 110; height: 50
        iconText: "M"
        labelText: "MODE"
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
