import QtQuick
import QtQuick.Window
import "../../components" as Shared

// Render the real registered component under Qt, not a stand-in visual.
Window {
    id: harness
    width: 270
    height: 145
    visible: true
    color: "#1B0623"

    property int downRequests: 0
    property int upRequests: 0
    property int lastDownDelta: 0
    property int lastUpDelta: 0

    Shared.ResizeButton {
        id: downButton
        objectName: "resizeDownButton"
        x: 34
        y: 35
        direction: "down"
        onResizeRequested: function(delta) {
            harness.downRequests += 1;
            harness.lastDownDelta = delta;
        }
    }

    Shared.ResizeButton {
        id: upButton
        objectName: "resizeUpButton"
        x: 112
        y: 35
        direction: "up"
        onResizeRequested: function(delta) {
            harness.upRequests += 1;
            harness.lastUpDelta = delta;
        }
    }

    readonly property var downGlyph: downButton.contentItem.children[0]
    readonly property var downEffect: downButton.contentItem.parent.children[1]
    readonly property var upGlyph: upButton.contentItem.children[0]
    readonly property var upEffect: upButton.contentItem.parent.children[1]

    readonly property bool downAligned:
        downEffect.labelIsLocalSource && downEffect.sourceAttached
        && Math.abs(downEffect.x - (downButton.contentItem.x + downGlyph.x)) < 0.1
        && Math.abs(downEffect.y - (downButton.contentItem.y + downGlyph.y)) < 0.1
        && Math.abs(downEffect.width - downGlyph.width) < 0.1
        && Math.abs(downEffect.height - downGlyph.height) < 0.1

    readonly property bool upAligned:
        upEffect.labelIsLocalSource && upEffect.sourceAttached
        && Math.abs(upEffect.x - (upButton.contentItem.x + upGlyph.x)) < 0.1
        && Math.abs(upEffect.y - (upButton.contentItem.y + upGlyph.y)) < 0.1
        && Math.abs(upEffect.width - upGlyph.width) < 0.1
        && Math.abs(upEffect.height - upGlyph.height) < 0.1

    // Actual glyph ink center, not merely the GohuText layout-box center.
    // TextMetrics uses the same font, fallback and text as the rendered label.
    readonly property real downInkCenterX:
        downGlyph.x + (downGlyph.width - downButton.glyphAdvanceWidth) / 2
        + downButton.glyphInkBounds.x + downButton.glyphInkBounds.width / 2
    readonly property real downInkCenterY:
        downGlyph.y + downGlyph.baselineOffset + downButton.glyphInkBounds.y
        + downButton.glyphInkBounds.height / 2
    readonly property real upInkCenterX:
        upGlyph.x + (upGlyph.width - upButton.glyphAdvanceWidth) / 2
        + upButton.glyphInkBounds.x + upButton.glyphInkBounds.width / 2
    readonly property real upInkCenterY:
        upGlyph.y + upGlyph.baselineOffset + upButton.glyphInkBounds.y
        + upButton.glyphInkBounds.height / 2
    readonly property bool downInkCentered:
        downButton.glyphInkBounds.width > 0
        && downButton.glyphInkBounds.height > 0
        && Math.abs(downInkCenterX - downButton.width / 2) < 0.2
        && Math.abs(downInkCenterY - downButton.height / 2) < 0.2
    readonly property bool upInkCentered:
        upButton.glyphInkBounds.width > 0
        && upButton.glyphInkBounds.height > 0
        && Math.abs(upInkCenterX - upButton.width / 2) < 0.2
        && Math.abs(upInkCenterY - upButton.height / 2) < 0.2
}
