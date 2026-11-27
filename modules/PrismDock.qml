import Quickshell
import QtQuick
import Quickshell.Wayland
import "../components"

// PRISM // Standalone bottom-left dock module, immediately beside Trash.
// This first pass presents the approved shared button artwork and its selected
// border only. The contextual dictionary and menu are deliberately not mounted.
PanelWindow {
    id: prismDock
    objectName: "prismDock"
    property bool previewSelected: false

    anchors {
        top: false
        bottom: true
        left: true
        right: false
    }

    // Trash's visible 50x50 face occupies screen x=25..75 and ends 20px
    // above the bottom. Prism begins at x=83: an 8px dock-family gap.
    margins {
        top: 0
        bottom: 10
        left: 73
        right: 0
    }
    implicitWidth: 70
    implicitHeight: 70
    color: "transparent"
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    focusable: false

    // No dead window rectangle or panel input over Trash / other widgets.
    mask: Region {
        item: prismButton
    }

    PrismButton {
        id: prismButton
        objectName: "postApolloPrismButton"
        x: 10
        y: 10
        width: 50
        height: 50
        selected: prismDock.previewSelected
        Accessible.description: "Prism artwork preview. Select to inspect the held-open border; dictionary not yet connected."
        onLeftClicked: prismDock.previewSelected = !prismDock.previewSelected
    }
}
