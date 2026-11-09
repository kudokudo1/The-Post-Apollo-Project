import QtQuick
import "../../components"
import "StationNewsCatalogPolicy.js" as Catalog
import "StationMediaSubjectPanelPolicy.js" as MediaPolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// MEDIA M1 // Read-only dashboard: explains the current route/source
// ownership without pretending that unmounted NEWS and RADIO providers are
// currently connected. The active owners are loaded only on their screens.
Rectangle {
    id: services
    objectName: "media-m1-services"
    color: Colors.black
    clip: true
    property string viewMode: "runtime"
    property bool embeddedHeader: false
    readonly property var routeRows: [
        {name:"NEWS // GDELT",owner:"StationNewsHub / StationDiscovery",
         state:"NOT MOUNTED ON SERVICES",scope:"REPORTS // EXPLICIT REQUEST"},
        {name:"RADIO // MPD",owner:"StationRadio / HEADLESS MEDIA",
         state:"NOT MOUNTED ON SERVICES",scope:"SELECT // LOAD // PLAY"},
        {name:"WATCH // CATALOG",owner:"StationNewsHub",
         state:Catalog.channels.length+" KNOWN DESTINATIONS",
         scope:"PUBLISHER PAGE // NOT VERIFIED LIVE"},
        {name:"CREATORS // SAVED",owner:"StationNewsHub / CREATOR STORE",
         state:"NOT MOUNTED ON SERVICES",
         scope:"SAVED CHANNELS // ON-DEMAND UPLOADS"}
    ]
    readonly property var details: [
        {label:"NEWS",value:"GDELT",detail:"REPORTS / ALERTS // SHARED OWNER"},
        {label:"RADIO",value:"MPD",detail:"NO AUTOPLAY // USER ACTIVATION"},
        {label:"CATALOG",value:String(Catalog.channels.length),
         detail:"DESTINATIONS // NOT LIVE CHANNEL COUNT"},
        {label:"ROUTES",value:String(Object.keys(MediaPolicy.ROUTES).length),
         detail:"MEDIA SUBJECTS // CANONICAL ROUTES"}
    ]

    Column {
        anchors.fill: parent
        anchors.margins: HeaderGeometry.inset
        spacing: 5
        Row {
            id: serviceTabs
            objectName: "media-m1-services-modes"
            width: parent.width
            height: services.embeddedHeader ? 0 : 25
            visible: !services.embeddedHeader
            spacing: HeaderGeometry.tabSpacing
            Repeater {
                model:[{id:"runtime",label:"RUNTIME // OWNERS"},
                       {id:"sources",label:"SOURCE DIRECTORY"}]
                delegate: ActionButton {
                    required property var modelData
                    width: HeaderGeometry.buttonWidth(serviceTabs.width,2)
                    height: serviceTabs.height
                    label: modelData.label
                    labelPixelSize: 9
                    selected: services.viewMode===modelData.id
                    accentColor: Colors.cyan
                    onClicked: services.viewMode=modelData.id
                }
            }
        }
        StationSectionDivider {
            width: parent.width
            title: services.viewMode==="runtime"
                ? "MEDIA // SERVICES // RUNTIME BOUNDARY"
                : "MEDIA // SERVICES // SOURCE OWNERSHIP"
        }
        QuietText {
            width: parent.width
            font.pixelSize: 9
            color: Colors.orange
            wrapMode: Text.WordWrap
            text: "THIS IS A READ-ONLY DIRECTORY // INACTIVE OWNERS ARE NOT LIVE HEALTH PROBES"
        }
        Grid {
            id: metrics
            width: parent.width
            columns: 2
            columnSpacing: 4
            rowSpacing: 4
            visible: services.viewMode==="runtime"
            Repeater {
                model: services.details
                delegate: Rectangle {
                    required property var modelData
                    width: Math.max(1,(metrics.width-metrics.columnSpacing)/2)
                    height: 52
                    color: Colors.dark
                    border.width: 1
                    border.color: Colors.cyan
                    Column {
                        anchors.fill:parent
                        anchors.margins: 4
                        spacing: 2
                        QuietText {
                            width: parent.width
                            text: modelData.label
                            font.pixelSize: 9
                            color: Colors.orange
                        }
                        GohuText {
                            width: parent.width
                            text: modelData.value
                            font.pixelSize: 13
                            color: Colors.white
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            text: modelData.detail
                            font.pixelSize: 8
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
        Flickable {
            id: ownershipScroll
            objectName: "media-m1-services-source-scroll"
            width: parent.width
            height: Math.max(0,services.height-serviceTabs.height-42)
            visible: services.viewMode==="sources"
            clip: true
            contentWidth: width
            contentHeight: sourceRows.implicitHeight
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id:sourceRows
                width:parent.width
                spacing:4
                Repeater {
                    model: services.routeRows
                    delegate: Rectangle {
                        required property var modelData
                        width: sourceRows.width
                        height: 48
                        color: Colors.dark
                        border.color: Colors.cyan
                        border.width: 1
                        Column {
                            anchors.fill:parent
                            anchors.margins:4
                            spacing:2
                            GohuText {
                                text: modelData.name+" // "+modelData.state
                                font.pixelSize:10
                                color:Colors.white
                                elide:Text.ElideRight
                                width:parent.width
                            }
                            QuietText {
                                text:modelData.owner+" // "+modelData.scope
                                font.pixelSize:9
                                color:Colors.cyan
                                elide:Text.ElideRight
                                width:parent.width
                            }
                        }
                    }
                }
            }
        }
        QuietText {
            width:parent.width
            text:"LIVE FEED STATUS BELONGS TO NEWS / RADIO WHILE THE RESPECTIVE OWNER IS MOUNTED"
            color:Colors.magenta
            font.pixelSize:8
            elide:Text.ElideRight
        }
    }
    NeonScrollBar {
        flickable:ownershipScroll
        handleStyle:"star"
        geometryHost:services
        visible:ownershipScroll.visible && scrollable
    }
}
