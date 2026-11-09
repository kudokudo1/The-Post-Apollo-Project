import QtQuick
import "../../components"
import "StationSubjectHeaderGeometry.js" as HeaderGeometry
import "StationNewsCatalogPolicy.js" as Catalog

// MEDIA M2 // One fixed C44 title + a contextual primary mode/filter row.
// RADIO uses its one real radio controller's presets; NEWS uses the
// original NEWS channel sections; SERVICES uses its actual dashboard modes.
// WATCH / CREATORS / OVERVIEW retain the cross-MEDIA navigation.
Item {
    id: mediaHeader
    objectName: "media-m1-c44-header"
    property string subjectRoute: ""
    property var radioPresets: []
    property int radioPresetIndex: 0
    property bool radioCanOperate: false
    property string radioStatus: ""
    property color radioStatusColor: Colors.white
    property string newsSection: "REPORTS"
    property string servicesMode: "runtime"
    readonly property string activeMode:
        subjectRoute === "media/overview" ? "overview"
        : subjectRoute.indexOf("media/news/") === 0 ? "news"
        : subjectRoute.indexOf("media/radio/") === 0 ? "radio"
        : subjectRoute.indexOf("media/creators/") === 0 ? "creators"
        : subjectRoute === "media/services/health" ? "services"
        : "watch"

    readonly property var sections: [
        {id:"overview",label:"OVERVIEW",path:"media/overview"},
        {id:"news",label:"NEWS",path:"media/news/full"},
        {id:"watch",label:"WATCH",path:"media/watch/live"},
        {id:"radio",label:"RADIO",path:"media/radio/full"},
        {id:"creators",label:"CREATORS",path:"media/creators/saved"},
        {id:"services",label:"SERVICES",path:"media/services/health"}
    ]
    readonly property var servicesSections: [
        {id:"runtime",label:"RUNTIME // OWNERS"},
        {id:"sources",label:"SOURCE DIRECTORY"},
        {id:"feeds",label:"PUBLISHER FEEDS"}
    ]
    readonly property var railItems:
        activeMode === "radio" ? radioPresets
        : activeMode === "news" || activeMode === "overview" ? Catalog.sections
        : activeMode === "services" ? servicesSections
        : sections

    signal routeRequested(string path)
    signal radioPresetRequested(int index)
    signal newsSectionRequested(string section)
    signal servicesModeRequested(string mode)

    height: HeaderGeometry.contentTop()
    clip: true

    GohuText {
        id: headerTitle
        objectName: "media-m1-c44-title"
        anchors.top: parent.top
        anchors.topMargin: HeaderGeometry.inset
        anchors.left: parent.left
        anchors.right: mediaHeader.activeMode==="radio"
            ? radioStatusLabel.left : parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: HeaderGeometry.titleHeight
        text: mediaHeader.activeMode === "radio" ? "◉ RADIO // NEWS FIRST"
            : mediaHeader.activeMode === "news"
              ? "NEWS // " + mediaHeader.newsSection
            : mediaHeader.activeMode === "overview"
              ? "MEDIA // OVERVIEW // NEWS"
            : "MEDIA // " + mediaHeader.activeMode.toUpperCase()
        font.pixelSize: 12
        color: Colors.magenta
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    GohuText {
        id: radioStatusLabel
        objectName: "media-m2-radio-fixed-status"
        anchors.top: headerTitle.top
        anchors.right: parent.right
        anchors.rightMargin: HeaderGeometry.inset
        width: mediaHeader.activeMode==="radio" ? 115 : 0
        height: HeaderGeometry.titleHeight
        text: mediaHeader.radioStatus
        font.pixelSize: 9
        color: mediaHeader.radioStatusColor
        elide: Text.ElideRight
        horizontalAlignment: Text.AlignRight
        verticalAlignment: Text.AlignVCenter
        visible: mediaHeader.activeMode==="radio"
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
            model: mediaHeader.railItems
            delegate: ActionButton {
                required property var modelData
                required property int index
                objectName: "media-m2-mode-" + String(
                    (mediaHeader.activeMode==="news" || mediaHeader.activeMode==="overview") ? modelData
                    : mediaHeader.activeMode==="radio" ? modelData.name
                    : modelData.id).toLowerCase().replace(/[^a-z0-9]+/g,"-")
                width: HeaderGeometry.buttonWidth(
                    modeRail.width, Math.max(1,mediaHeader.railItems.length))
                height: HeaderGeometry.tabHeight
                label: mediaHeader.activeMode==="radio" ? modelData.name
                    : mediaHeader.activeMode==="news" || mediaHeader.activeMode==="overview" ? modelData
                    : modelData.label
                labelPixelSize: 9
                contentPadding: 1
                selected: mediaHeader.activeMode==="radio"
                    ? index===mediaHeader.radioPresetIndex
                    : mediaHeader.activeMode==="news" || mediaHeader.activeMode==="overview"
                    ? modelData===mediaHeader.newsSection
                    : mediaHeader.activeMode==="services"
                    ? modelData.id===mediaHeader.servicesMode
                    : modelData.id===mediaHeader.activeMode
                available: mediaHeader.activeMode!=="radio"
                    || mediaHeader.radioCanOperate
                accentColor: Colors.cyan
                onClicked: {
                    if(mediaHeader.activeMode==="radio")
                        mediaHeader.radioPresetRequested(index);
                    else if(mediaHeader.activeMode==="news" || mediaHeader.activeMode==="overview")
                        mediaHeader.newsSectionRequested(modelData);
                    else if(mediaHeader.activeMode==="services")
                        mediaHeader.servicesModeRequested(modelData.id);
                    else
                        mediaHeader.routeRequested(modelData.path);
                }
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
