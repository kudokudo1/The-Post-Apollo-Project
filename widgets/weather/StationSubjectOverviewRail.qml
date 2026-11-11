import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// W21 // One shared C44-style full-width overview rail for WEATHER/MAGICK.
// Navigation only: no provider, timer, page collector or saved state.
Item {
    id: overviewRail
    objectName: "station-w21-shared-overview-rail"
    property var routes: []
    signal routeRequested(string path)
    height: visible ? 31 : 0

    Row {
        id: longButtons
        objectName: "station-w21-full-width-buttons"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 25
        spacing: HeaderGeometry.tabSpacing
        Repeater {
            model: overviewRail.routes
            delegate: ActionButton {
                required property var modelData
                objectName: "station-w21-overview-route"
                width: HeaderGeometry.buttonWidth(longButtons.width,
                                                  overviewRail.routes.length)
                height: longButtons.height
                label: modelData.label
                labelPixelSize: 10
                contentPadding: 1
                accentColor: Colors.cyan
                onClicked: overviewRail.routeRequested(modelData.path)
            }
        }
    }
    Rectangle {
        objectName: "station-w21-overview-divider"
        anchors.left: longButtons.left
        anchors.right: longButtons.right
        anchors.top: longButtons.bottom
        anchors.topMargin: 3
        height: HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
}
