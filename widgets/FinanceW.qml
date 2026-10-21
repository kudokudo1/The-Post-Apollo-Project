import QtQuick
import Quickshell
import Quickshell.Wayland
import "../components"

// Blank FinanceW chassis only. No services, money data, or input editors.
PanelWindow {
    id: root

    property bool menuOpen: false

    // Display coordinates relative to DP-5, supplied by shell.qml.
    property real dockCenterX: 0
    property real chassisTopY: 0

    // The visible chassis is exactly 9:16; gutter belongs to its glow.
    readonly property int frameWidth: 432
    readonly property int frameHeight: 768
    readonly property int glowGutter: 12

    function toggle() {
        menuOpen = !menuOpen;
    }

    implicitWidth: frameWidth + glowGutter * 2
    implicitHeight: frameHeight + glowGutter * 2

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    // Clamp the panel to its screen if the dock layout becomes wider.
    margins {
        // Match Hospital/Git's visible frame top, not the Finance dock bottom.
        top: Math.max(0, Math.round(root.chassisTopY - root.glowGutter))
        left: Math.max(0, Math.min(
            Math.max(0, root.screen ? root.screen.width - root.implicitWidth : 0),
            Math.round(root.dockCenterX - root.implicitWidth / 2)
        ))
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay

    // Blank chassis has no text editor or keyboard shortcuts. Never steal
    // focus from Hospital, Git, or the terminal just to display it.
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
    focusable: false

    color: "transparent"
    surfaceFormat.opaque: false

    // Map once: repeated show/hide of layer-shell windows previously caused
    // native crashes. A zero-size input mask makes the closed panel inert.
    visible: true
    mask: Region {
        x: root.glowGutter
        y: root.glowGutter
        width: root.menuOpen ? root.frameWidth : 0
        height: root.menuOpen ? root.frameHeight : 0
    }

    WindowPanelFrame {
        anchors.fill: parent
        anchors.margins: root.glowGutter
        visible: root.menuOpen

        fillColor: Colors.black
        fillOpacity: 0.95
        borderColor: Colors.omnitrix
        borderWidth: 1
        radius: 0

        glowVisible: root.menuOpen
        glowColor: Colors.omnitrix
    }
}
