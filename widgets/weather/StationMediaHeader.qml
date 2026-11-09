import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry
import "StationMediaSubjectPanelPolicy.js" as MediaPanelPolicy

// MEDIA M1 // COSMOS/EARTH C44 title, five direct family modes, and rule.
// All content is mounted beneath this fixed header. Existing collectors,
// playback controls, and channel viewers remain their original owners.
Item {
    id: mediaHeader
    objectName: "media-m1-c44-header"
    property string subjectRoute: ""
    readonly property string activeMode:
        subjectRoute === "media/overview" ? "overview"
        : subjectRoute.indexOf("media/news/") === 0 ? "news"
        : subjectRoute.indexOf("media/radio/") === 0 ? "radio"
        : subjectRoute === "media/services/health" ? "services"
        : "watch"
    readonly property var sections: [
        {id:"overview",label:"OVERVIEW",path:"media/overview"},
        {id:"news",label:"NEWS",path:"media/news/full"},
        {id:"watch",label:"WATCH",path:"media/watch/live"},
        {id:"radio",label:"RADIO",path:"media/radio/full"},
        {id:"services",label:"SERVICES",path:"media/services/health"}
    ]
    signal routeRequested(string path)
    height: HeaderGeometry.contentTop()
    clip: true

    GohuText {
        id: headerTitle
        objectName: "media-m1-c44-title"
        anchors.top: parent.top
        anchors.topMargin: HeaderGeometry.inset
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.titleHeight
        text: "MEDIA // " + mediaHeader.activeMode.toUpperCase()
        font.pixelSize: 12
        color: Colors.magenta
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    Row {
        id: modeRail
        objectName: "media-m1-c44-mode-rail"
        anchors.top: headerTitle.bottom
        anchors.topMargin: HeaderGeometry.titleToTabs
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.tabHeight
        spacing: HeaderGeometry.tabSpacing
        Repeater {
            model: mediaHeader.sections
            delegate: ActionButton {
                required property var modelData
                objectName: "media-m1-mode-" + modelData.id
                width: HeaderGeometry.buttonWidth(modeRail.width,5)
                height: HeaderGeometry.tabHeight
                label: modelData.label
                labelPixelSize: 9
                contentPadding: 1
                selected: mediaHeader.activeMode === modelData.id
                accentColor: Colors.cyan
                onClicked: mediaHeader.routeRequested(modelData.path)
            }
        }
    }
    Rectangle {
        objectName: "media-m1-c44-divider"
        anchors.top: modeRail.bottom
        anchors.topMargin: HeaderGeometry.tabsToRule
        anchors.left: modeRail.left
        anchors.right: modeRail.right
        height: HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
}
