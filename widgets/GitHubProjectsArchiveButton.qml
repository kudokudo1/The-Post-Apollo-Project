import QtQuick
import qs.components
import qs.components as Components

// The same archive action in Projects Board, Table and Roadmap.
// Archive is separate from red Remove. Preserve two-step arming in caller.
Item {
    id: root
    height: 26 // Table default; Board (20) and Roadmap (24) override.

    property bool enabledAction: true
    property bool armed: false
    signal triggered()

    Components.ActionButton {
        anchors.fill: parent
        available: root.enabledAction
        selected: root.armed
        label: root.armed ? "CONFIRM" : "ARCHIVE"
        labelPixelSize: 10
        labelMinimumPixelSize: 8
        contentPadding: 2

        // Persistent white lettering, including hover, press and confirmation.
        // Black fill preserves contrast; orange marks the archive action.
        accentColor: Colors.orange
        idleForegroundColor: Colors.white
        hoverForegroundColor: Colors.white
        pressedForegroundColor: Colors.white
        selectedForegroundColor: Colors.white
        keyboardSelectedForegroundColor: Colors.white

        idleFillColor: Colors.black
        hoverFillColor: Colors.black
        pressedFillColor: Colors.dark
        selectedFillColor: Colors.black
        keyboardSelectedFillColor: Colors.black

        idleBorderColor: Colors.orange
        hoverBorderColor: Colors.orange
        pressedBorderColor: Colors.orange
        selectedBorderColor: Colors.orange
        keyboardSelectedBorderColor: Colors.orange

        idleContentGlowColor: Colors.orange
        hoverContentGlowColor: Colors.orange
        pressedContentGlowColor: Colors.orange
        selectedContentGlowColor: Colors.orange
        idleSoftGlowColor: Colors.orange
        hoverSoftGlowColor: Colors.orange
        pressedSoftGlowColor: Colors.orange
        selectedSoftGlowColor: Colors.orange

        onTriggered: root.triggered()
    }
}
