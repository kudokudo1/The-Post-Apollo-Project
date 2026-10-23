import QtQuick

// Four opaque/tinted chassis strips leave the center literally unpainted.
// This is a VISUAL alpha cutout, unlike PanelWindow.mask (input-only).
// The host controls when the opening is active and owns window positioning.
Item {
    id: chassis

    property real holeX: 0
    property real holeY: 0
    property real holeWidth: 0
    property real holeHeight: 0
    property color panelColor: "black"
    property real panelOpacity: 1.0

    readonly property bool holeValid:
        width > 0 && height > 0
        && isFinite(holeX) && isFinite(holeY)
        && isFinite(holeWidth) && isFinite(holeHeight)
        && holeX >= 0 && holeY >= 0
        && holeWidth > 0 && holeHeight > 0
        && holeX + holeWidth <= width
        && holeY + holeHeight <= height

    Rectangle {
        // Above the opening.
        x: 0
        y: 0
        width: chassis.width
        height: Math.max(0, chassis.holeY)
        color: chassis.panelColor
        opacity: chassis.panelOpacity
    }

    Rectangle {
        // To the left of the opening.
        x: 0
        y: chassis.holeY
        width: Math.max(0, chassis.holeX)
        height: Math.max(0, chassis.holeHeight)
        color: chassis.panelColor
        opacity: chassis.panelOpacity
    }

    Rectangle {
        // To the right of the opening.
        x: chassis.holeX + chassis.holeWidth
        y: chassis.holeY
        width: Math.max(0, chassis.width - x)
        height: Math.max(0, chassis.holeHeight)
        color: chassis.panelColor
        opacity: chassis.panelOpacity
    }

    Rectangle {
        // Below the opening.
        x: 0
        y: chassis.holeY + chassis.holeHeight
        width: chassis.width
        height: Math.max(0, chassis.height - y)
        color: chassis.panelColor
        opacity: chassis.panelOpacity
    }
}
