import QtQuick
import QtQuick.Effects

Item {
    id: panelFrame

    // Visual chassis only. Window placement, focus, masks, keyboard policy,
    // interaction and Sway behavior stay owned by the caller.
    default property alias contentData: surface.contentData

    property alias fillColor: surface.fillColor
    property alias fillOpacity: surface.fillOpacity
    property alias fillVisible: surface.fillVisible

    property alias borderColor: surface.borderColor
    property alias borderOpacity: surface.borderOpacity
    property alias borderWidth: surface.borderWidth
    property alias borderVisible: surface.borderVisible

    property alias radius: surface.radius
    property alias clipContent: surface.clipContent

    // Lets a caller fade the visible panel/content without also weakening
    // the independently tuned outer glow.
    property real surfaceOpacity: 1.0

    property bool glowVisible: true
    property color glowColor: borderColor

    property real closeGlowSpread: 6
    property real closeGlowOpacity: 0.38

    property real wideGlowSpread: 12
    property real wideGlowOpacity: 0.12

    readonly property Item surfaceItem: surface
    readonly property Item frameSource: surface.frameSource
    readonly property Item fillSource: surface.fillSource
    readonly property Item contentItem: surface.contentItem

    RectangularShadow {
        anchors.fill: surface
        z: -2

        visible:
            panelFrame.glowVisible
            && panelFrame.closeGlowOpacity > 0.0

        spread: panelFrame.closeGlowSpread
        color: panelFrame.glowColor
        opacity: panelFrame.closeGlowOpacity
    }

    RectangularShadow {
        anchors.fill: surface
        z: -3

        visible:
            panelFrame.glowVisible
            && panelFrame.wideGlowOpacity > 0.0

        spread: panelFrame.wideGlowSpread
        color: panelFrame.glowColor
        opacity: panelFrame.wideGlowOpacity
    }

    SurfaceFrame {
        id: surface

        anchors.fill: parent
        opacity: panelFrame.surfaceOpacity
    }
}
