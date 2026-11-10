import QtQuick
import "../../components"
import "StationNewsCatalogPolicy.js" as Catalog
import "StationMediaSubjectPanelPolicy.js" as MediaPolicy
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// MEDIA M6 // SERVICES owns last-observed NEWS diagnostics only. Publisher
// LOAD/REFRESH and VIEW return to NEWS → REPORTS. No background GDELT owner.
Rectangle {
    id: services
    objectName: "media-m1-services"
    color: Colors.black
    clip: true
    property string viewMode: "runtime"
    property bool embeddedHeader: false
    property bool stationOpen: true
    property double newsObservedMs: 0
    property string newsFeedBadge: "NEWS NOT YET OBSERVED"
    property var newsRuntimeRows: []
    property var newsSourceRows: []
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
        {label:"NEWS",value:"GDELT",detail:"HEADLINES // SOURCE OWNER IS NEWS"},
        {label:"RADIO",value:"MPD",detail:"NO AUTOPLAY // USER ACTIVATION"},
        {label:"CATALOG",value:String(Catalog.channels.length),
         detail:"DESTINATIONS // NOT LIVE CHANNEL COUNT"},
        {label:"ROUTES",value:String(Object.keys(MediaPolicy.ROUTES).length),
         detail:"MEDIA SUBJECTS // CANONICAL ROUTES"}
    ]
    readonly property var serviceTabs: [
        {id:"runtime",label:"RUNTIME // OWNERS"},
        {id:"sources",label:"SOURCE DIRECTORY"}
    ]

    Column {
        anchors.fill: parent
        anchors.margins: HeaderGeometry.inset
        spacing: 4
        Row {
            id: localTabs
            objectName: "media-m1-services-modes"
            width: parent.width
            height: services.embeddedHeader ? 0 : 25
            visible: !services.embeddedHeader
            spacing: HeaderGeometry.tabSpacing
            Repeater {
                model: services.serviceTabs
                delegate: ActionButton {
                    required property var modelData
                    width: HeaderGeometry.buttonWidth(localTabs.width,2)
                    height: localTabs.height
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
            text: "READ-ONLY STATUS // INACTIVE NEWS IS NEVER A LIVE HEALTH PROBE"
        }
        Flickable {
            id: servicesScroll
            objectName: "media-m5-services-body-scroll"
            width: parent.width
            height: Math.max(0,services.height
                - HeaderGeometry.inset*2 - localTabs.height - 37)
            clip: true
            contentWidth: width
            contentHeight: body.implicitHeight + 12
            boundsBehavior: Flickable.StopAtBounds
            Column {
                id: body
                width: servicesScroll.width
                spacing: 5

                Column {
                    id: runtimeContent
                    objectName: "media-m5-runtime-content"
                    width: body.width
                    spacing: 5
                    visible: services.viewMode==="runtime"
                    Grid {
                        id: metrics
                        width: parent.width
                        columns: 2
                        columnSpacing: 4
                        rowSpacing: 4
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
                                    anchors.fill: parent
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
                    StationSectionDivider {
                        width: parent.width
                        title: "NEWS FEED // LAST OBSERVED RUNTIME"
                    }
                    GohuText {
                        width: parent.width
                        font.pixelSize: 10
                        text: services.newsObservedMs>0
                            ? services.newsFeedBadge + " // LAST OBSERVED "
                              + Qt.formatDateTime(new Date(services.newsObservedMs),
                                                   "hh:mm:ss AP")
                            : "NEWS NOT OBSERVED THIS SESSION // OPEN NEWS → REPORTS"
                        color: services.newsObservedMs>0 ? Colors.cyan : Colors.orange
                        elide: Text.ElideRight
                    }
                    Repeater {
                        model: services.newsRuntimeRows
                        delegate: Rectangle {
                            required property var modelData
                            width: runtimeContent.width
                            height: 27
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan
                            Row {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 7
                                QuietText {
                                    width: Math.max(80,parent.width*0.67)
                                    text: modelData.name
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: Math.max(0,parent.width-160)
                                    text: modelData.state
                                    font.pixelSize: 9
                                    color: Colors.orange
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                Column {
                    id: sourceContent
                    objectName: "media-m5-source-content"
                    width: body.width
                    spacing: 4
                    visible: services.viewMode==="sources"
                    Repeater {
                        model: services.routeRows
                        delegate: Rectangle {
                            required property var modelData
                            width: sourceContent.width
                            height: 48
                            color: Colors.dark
                            border.color: Colors.cyan
                            border.width: 1
                            Column {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 2
                                GohuText {
                                    text: modelData.name+" // "+modelData.state
                                    font.pixelSize: 10
                                    color: Colors.white
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                                QuietText {
                                    text:modelData.owner+" // "+modelData.scope
                                    font.pixelSize: 9
                                    color:Colors.cyan
                                    elide: Text.ElideRight
                                    width: parent.width
                                }
                            }
                        }
                    }
                    StationSectionDivider {
                        width: parent.width
                        title: "GDELT // SOURCE RACK // LAST OBSERVED"
                    }
                    QuietText {
                        width: parent.width
                        text: services.newsObservedMs>0
                            ? "SOURCE STATE CAPTURED WHEN NEWS WAS MOUNTED"
                            : "NO NEWS STATE YET // VISIT NEWS → REPORTS"
                        color: Colors.orange
                        font.pixelSize: 9
                    }
                    Repeater {
                        model: services.newsSourceRows
                        delegate: Rectangle {
                            required property var modelData
                            width: sourceContent.width
                            height: 29
                            color: Colors.dark
                            border.width: 1
                            border.color: Colors.cyan
                            Row {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 8
                                QuietText {
                                    width: Math.max(0,parent.width*0.7)
                                    text: modelData.name
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                }
                                GohuText {
                                    width: Math.max(0,parent.width*0.28)
                                    text: modelData.state
                                    font.pixelSize: 9
                                    color: Colors.orange
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }


            }
        }
    }
    NeonScrollBar {
        flickable: servicesScroll
        handleStyle: "star"
        geometryHost: services
        visible: scrollable
    }
}
