import QtQuick

Item {
    id: surfaceFrame

    // Structural surface only. Interaction, layout padding, rails and glow
    // compose around this component rather than becoming part of its contract.
    default property alias contentData: contentHost.data

    property color fillColor: Colors.black
    property real fillOpacity: 1.0
    property bool fillVisible: true

    property color borderColor: Colors.cyan
    property real borderOpacity: 1.0
    property real borderWidth: 1.0
    property bool borderVisible: true

    property real radius: 0
    property bool clipContent: false

    // Clean visual sources for external effect composition.
    readonly property Item frameSource: frameVisual
    readonly property Item fillSource: fillLayer
    readonly property Item contentItem: contentHost

    Rectangle {
        id: fillLayer

        anchors.fill: parent
        z: 0

        visible: surfaceFrame.fillVisible && surfaceFrame.fillOpacity > 0.0
        color: surfaceFrame.fillColor
        opacity: surfaceFrame.fillOpacity
        radius: surfaceFrame.radius
    }

    Item {
        id: contentHost

        anchors.fill: parent
        z: 1
        clip: surfaceFrame.clipContent
    }

    Rectangle {
        id: frameVisual

        anchors.fill: parent
        z: 2

        visible:
            surfaceFrame.borderVisible
            && surfaceFrame.borderWidth > 0.0
            && surfaceFrame.borderOpacity > 0.0

        color: "transparent"
        radius: surfaceFrame.radius

        border.width: surfaceFrame.borderWidth
        border.color: Qt.rgba(
            surfaceFrame.borderColor.r,
            surfaceFrame.borderColor.g,
            surfaceFrame.borderColor.b,
            surfaceFrame.borderColor.a * surfaceFrame.borderOpacity
        )
    }
}
