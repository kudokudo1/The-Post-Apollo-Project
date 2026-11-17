import QtQuick
import "../components" as Shared

// Finance Budget uses a Column-owned Flickable inside a stable Rectangle.
// This sibling overlay uses explicit observable x/y/size dependencies, not
// mapToItem() to align a reparented bar after dynamic Column layout changes.
Item {
    id: root

    // Both items must be direct children of the same expected layout chain:
    // this overlay and layoutHost share a non-positioning parent; the
    // scrollTarget is a direct Column child. Fail closed if that changes.
    property Item scrollTarget: null
    property Item layoutHost: null
    readonly property bool validHierarchy:
        !!scrollTarget && !!layoutHost
        && layoutHost.parent === root.parent
        && scrollTarget.parent === layoutHost

    // Explicit QML property reads are tracked when the Column repositions
    // the viewport after labels appear, list contents change, or resize.
    x: validHierarchy ? layoutHost.x + scrollTarget.x : 0
    y: validHierarchy ? layoutHost.y + scrollTarget.y : 0
    width: validHierarchy ? Math.max(0, scrollTarget.width) : 0
    height: validHierarchy ? Math.max(0, scrollTarget.height) : 0
    visible: validHierarchy && layoutHost.visible && scrollTarget.visible
    z: 20

    Shared.NeonScrollBar {
        id: rail
        objectName: "financeBudgetRailTrack"
        flickable: root.scrollTarget
        mountingParent: root
        geometryHost: root
        // The overlay IS the actual viewport box. Box geometry avoids a
        // second coordinate map, while keeping the track inside its bounds.
        geometryMode: "box"
        handleStyle: "bar"
        rightInset: 2
        visible: root.visible && scrollable
    }
}
