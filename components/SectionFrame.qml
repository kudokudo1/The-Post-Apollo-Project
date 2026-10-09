import QtQuick

Item {
    id: sectionFrame

    // Surface structure plus content insets only. Internal layout remains
    // completely owned by the caller.
    default property alias contentData: contentHost.data

    property alias fillColor: surface.fillColor
    property alias fillOpacity: surface.fillOpacity
    property alias fillVisible: surface.fillVisible

    property alias borderColor: surface.borderColor
    property alias borderOpacity: surface.borderOpacity
    property alias borderWidth: surface.borderWidth
    property alias borderVisible: surface.borderVisible

    property alias radius: surface.radius
    property alias clipContent: surface.clipContent

    // Convenience symmetric inset with independently overridable sides.
    property real inset: 0
    property real leftInset: inset
    property real rightInset: inset
    property real topInset: inset
    property real bottomInset: inset

    readonly property Item surfaceItem: surface
    readonly property Item frameSource: surface.frameSource
    readonly property Item fillSource: surface.fillSource
    readonly property Item contentItem: contentHost

    SurfaceFrame {
        id: surface

        anchors.fill: parent

        Item {
            id: contentHost

            anchors {
                fill: parent
                leftMargin: sectionFrame.leftInset
                rightMargin: sectionFrame.rightInset
                topMargin: sectionFrame.topInset
                bottomMargin: sectionFrame.bottomInset
            }
        }
    }
}
