import QtQuick

// Approved A02 V14-A floating-chevron cube. A presentation/input component;
// callers own resize state, geometry, focus, and any open popup.
ActionButton {
    id: root
    objectName: "resizeCubeButton"
    implicitWidth: 30
    implicitHeight: 30
    width: implicitWidth
    height: width

    label: ""
    showLabel: false
    accentColor: Colors.yellow
    acceptedButtons: Qt.LeftButton
    keyboardActivationSignal: "leftClicked"
    Accessible.role: Accessible.Button
    Accessible.name: "Resize window"
    Accessible.onPressAction: {
        if (root.interactive && root.available) {
            root.clicked(null)
            root.leftClicked(null)
            root.triggered(null)
        }
    }

    // Persistent yellow outline, independent magenta perimeter. Keep the
    // shared black idle, yellow hover/selected and magenta press fills.
    idleBorderColor: Colors.yellow
    hoverBorderColor: Colors.yellow
    pressedBorderColor: Colors.yellow
    selectedBorderColor: Colors.yellow
    keyboardSelectedBorderColor: Colors.yellow

    softGlowEnabled: true
    idleSoftGlowColor: Colors.magenta
    hoverSoftGlowColor: Colors.magenta
    pressedSoftGlowColor: Colors.magenta
    selectedSoftGlowColor: Colors.magenta
    keyboardSelectedSoftGlowColor: Colors.magenta
    wideGlowEnabled: false

    // The three-color artwork has its own co-registered SVG halo. Never
    // sample the entire contentHost with one monochrome effect.
    contentGlowEnabled: false
    contentGlowSource: null

    property real iconScale: 0.60
    readonly property real artworkSize: Math.max(0, Math.min(width,height) * Math.max(0,Math.min(1,iconScale)))
    readonly property int rasterSize: Math.max(1,Math.min(256,Math.ceil(artworkSize*2)))

    Item {
        anchors.centerIn: parent
        width: root.artworkSize
        height: width

        // All planes use the identical viewBox, dimensions and center.
        Image {
            objectName: "resizeCubeGlow"
            anchors.fill: parent
            source: Qt.resolvedUrl("../assets/resize/cube-v14a-glow.svg")
            sourceSize.width: root.rasterSize
            sourceSize.height: root.rasterSize
            fillMode: Image.PreserveAspectFit
            smooth: true
            opacity: root.effectiveContentGlowOpacity
        }

        // The normal bright interaction fills would otherwise hide a
        // yellow or magenta segment. A narrow dark backing is used only
        // over those fills; the approved colored core is never reordered.
        Image {
            objectName: "resizeCubeContrast"
            anchors.fill: parent
            source: Qt.resolvedUrl("../assets/resize/cube-v14a-contrast.svg")
            sourceSize.width: root.rasterSize
            sourceSize.height: root.rasterSize
            fillMode: Image.PreserveAspectFit
            smooth: true
            visible: Qt.colorEqual(root.fillColor, Colors.yellow)
                     || Qt.colorEqual(root.fillColor, Colors.magenta)
        }

        Image {
            objectName: "resizeCubeArtwork"
            anchors.fill: parent
            source: Qt.resolvedUrl("../assets/resize/cube-v14a.svg")
            sourceSize.width: root.rasterSize
            sourceSize.height: root.rasterSize
            fillMode: Image.PreserveAspectFit
            smooth: true
        }
    }
}
