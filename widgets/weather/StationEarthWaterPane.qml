import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// E2 // One original StationGround renderer, three water instruments.
// Route switching changes the focused original section, not the collector.
Rectangle {
    id: water
    objectName: "earth-e2-water-pane"
    color: Colors.black
    clip: true
    property string subjectRoute: "earth/water/rivers"
    property var weatherService: null
    property var nwsAlertSource: null
    property var seismicSource: null
    property var lightningSource: null
    property var riverSource: null
    property var persistentCacheStore: null
    property var liveHistoryStore: null
    property real runtimeNowMs: 0
    signal routeRequested(string path)

    GohuText {
        id: title
        objectName: "earth-e2-water-title"
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: HeaderGeometry.inset
        height: HeaderGeometry.titleHeight
        text: "EARTH // WATER"
        font.pixelSize: 12
        color: Colors.magenta
        verticalAlignment: Text.AlignVCenter
    }
    Row {
        id: modes
        objectName: "earth-e2-water-tabs"
        anchors.top: title.bottom
        anchors.topMargin: HeaderGeometry.titleToTabs
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.tabHeight
        spacing: HeaderGeometry.tabSpacing
        Repeater {
            model: [
                {label:"RIVERS",path:"earth/water/rivers"},
                {label:"MARINE",path:"earth/water/marine"},
                {label:"COAST",path:"earth/water/coast"}
            ]
            delegate: ActionButton {
                required property var modelData
                width: HeaderGeometry.buttonWidth(modes.width,3)
                height: HeaderGeometry.tabHeight
                label: modelData.label
                labelPixelSize: 10
                contentPadding: 1
                selected: water.subjectRoute === modelData.path
                    || (modelData.path === "earth/water/rivers"
                        && water.subjectRoute.indexOf(
                            "earth/water/rivers/") === 0)
                accentColor: Colors.cyan
                onClicked: water.routeRequested(modelData.path)
            }
        }
    }
    Rectangle {
        id: rule
        objectName: "earth-e2-water-divider"
        anchors.top: modes.bottom
        anchors.topMargin: HeaderGeometry.tabsToRule
        anchors.left: modes.left
        anchors.right: modes.right
        height: HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
    StationGround {
        id: originalGround
        objectName: "earth-e2-water-original-ground"
        anchors.top: rule.bottom
        anchors.topMargin: HeaderGeometry.ruleToContent
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        subjectRoute: water.subjectRoute
        weatherService: water.weatherService
        nwsAlertSource: water.nwsAlertSource
        seismicSource: water.seismicSource
        lightningSource: water.lightningSource
        riverSource: water.riverSource
        persistentCacheStore: water.persistentCacheStore
        liveHistoryStore: water.liveHistoryStore
        runtimeNowMs: water.runtimeNowMs
        onRouteRequested: function(path) {water.routeRequested(path);}
    }
}
