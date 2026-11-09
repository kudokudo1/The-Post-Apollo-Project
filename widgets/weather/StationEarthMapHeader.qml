import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry
import "StationEarthOverviewPolicy.js" as Overview
import "StationEarthSubjectPanelPolicy.js" as EarthPanelPolicy

// E8 // Shared C44 header for the EARTH map-family screens. WATER,
// GROUND and SERVICES already implement the same geometry internally.
// No second map, provider, archive, or writer belongs to this header.
Item {
    id: earthHeader
    objectName: "earth-e8-c44-header"
    property string subjectRoute: ""
    readonly property bool overviewMode: subjectRoute === "earth/overview"
    readonly property var tabs: overviewMode ? Overview.TOPICS : [
        {id:"overview",label:"OVERVIEW",path:"earth/overview"},
        {id:"events",label:"MAP / EVENTS",path:"earth/maps/events"},
        {id:"full",label:"FULL MAP",path:"earth/maps/full"}
    ]
    signal routeRequested(string path)
    signal openTopicRequested(string topicId)
    height: HeaderGeometry.contentTop()
    clip: true

    GohuText {
        id: title
        objectName: "earth-e8-c44-title"
        anchors.top: parent.top
        anchors.topMargin: HeaderGeometry.inset
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.titleHeight
        verticalAlignment: Text.AlignVCenter
        text: earthHeader.overviewMode ? "EARTH // OVERVIEW"
            : earthHeader.subjectRoute === "earth/maps/full" ? "EARTH // FULL MAP"
            : earthHeader.subjectRoute === "earth/maps/events" ? "EARTH // MAP / EVENTS"
            : EarthPanelPolicy.routeLabel(earthHeader.subjectRoute)
        font.pixelSize: 12
        color: Colors.magenta
        elide: Text.ElideRight
    }

    Row {
        id: tabs
        objectName: "earth-e8-c44-mode-rail"
        anchors.top: title.bottom
        anchors.topMargin: HeaderGeometry.titleToTabs
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.tabHeight
        spacing: HeaderGeometry.tabSpacing
        Repeater {
            model: earthHeader.tabs
            delegate: ActionButton {
                required property var modelData
                objectName: earthHeader.overviewMode
                    ? "earth-e8-full-" + modelData.id
                    : "earth-e8-map-" + modelData.id
                width: HeaderGeometry.buttonWidth(tabs.width,3)
                height: HeaderGeometry.tabHeight
                label: modelData.label
                labelPixelSize: 10
                contentPadding: 1
                accentColor: Colors.cyan
                selected: !earthHeader.overviewMode
                    && earthHeader.subjectRoute === modelData.path
                onClicked: {
                    if (earthHeader.overviewMode)
                        earthHeader.openTopicRequested(modelData.id);
                    else
                        earthHeader.routeRequested(modelData.path);
                }
            }
        }
    }

    Rectangle {
        objectName: "earth-e8-c44-divider"
        anchors.top: tabs.bottom
        anchors.topMargin: HeaderGeometry.tabsToRule
        anchors.left: tabs.left
        anchors.right: tabs.right
        height: HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
}
