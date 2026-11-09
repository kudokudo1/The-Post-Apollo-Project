import QtQuick
import "../../components"
import "StationEarthOverviewPolicy.js" as Overview
import "StationGroundEnvironmentPolicy.js" as Environment
import "StationSubjectHeaderGeometry.js" as HeaderGeometry

// E6 // Read-only summary companion beneath the ONE persistent EARTH map.
// Three arrow-driven topics reuse Weather Station data already on the root.
// No new process, collector, bookmark owner, geolocation or archive writer.
Rectangle {
    id: overview
    objectName: "earth-e6-overview-summary"
    color: Colors.black
    clip: true

    property var weatherService: null
    property var riverSource: null
    property var nwsAlertSource: null
    property var seismicSource: null
    property int topicIndex: 0
    // E8 // The real EARTH workspace places the C44 rail above the map.
    // Standalone source/native fixtures can retain the original E7 rail.
    property bool embeddedHeader: false
    signal openTopicRequested(string topicId)

    readonly property var currentTopic: Overview.topic(topicIndex)
    readonly property var alertRows: nwsAlertSource
        && Array.isArray(nwsAlertSource.alertList)
        ? nwsAlertSource.alertList : []
    readonly property var fireProducts:
        Environment.fireWeatherAlerts(alertRows)
    readonly property var heatIndex:
        Environment.heatIndex(
            weatherService ? weatherService.tempF : "",
            weatherService ? weatherService.humidity : "")
    readonly property var summary:
        Overview.summarize(topicIndex,riverSource,weatherService,
                           nwsAlertSource,seismicSource,heatIndex,fireProducts)
    readonly property var charts:
        Overview.microcharts(topicIndex,riverSource,weatherService,
                             nwsAlertSource,seismicSource,heatIndex,fireProducts)

    // E7 // COSMOS C44 main rail: direct entry into the three existing
    // detailed menus. The retained arrows below change only the summary.
    Row {
        id: overviewMainRail
        objectName: "earth-e7-overview-main-rail"
        visible: !overview.embeddedHeader
        anchors.top: parent.top
        anchors.topMargin: 2
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: HeaderGeometry.inset
        anchors.rightMargin: HeaderGeometry.inset
        height: overview.embeddedHeader ? 0 : HeaderGeometry.tabHeight
        spacing: HeaderGeometry.tabSpacing
        Repeater {
            model: Overview.TOPICS
            delegate: ActionButton {
                required property var modelData
                objectName: "earth-e7-main-" + modelData.id
                width: HeaderGeometry.buttonWidth(overviewMainRail.width,3)
                height: HeaderGeometry.tabHeight
                label: modelData.label
                labelPixelSize: 10
                contentPadding: 1
                selected: overview.currentTopic.id === modelData.id
                accentColor: Colors.cyan
                onClicked: overview.openTopicRequested(modelData.id)
            }
        }
    }
    Rectangle {
        id: mainDivider
        objectName: "earth-e7-overview-divider"
        visible: !overview.embeddedHeader
        anchors.top: overviewMainRail.bottom
        anchors.topMargin: HeaderGeometry.tabsToRule
        anchors.left: overviewMainRail.left
        anchors.right: overviewMainRail.right
        height: overview.embeddedHeader ? 0 : HeaderGeometry.ruleHeight
        color: Colors.cyan
    }
    Row {
        id: topicNavigation
        objectName: "earth-e6-overview-arrows"
        anchors.top: overview.embeddedHeader
            ? parent.top : mainDivider.bottom
        anchors.topMargin: 2
        anchors.left: overviewMainRail.left
        anchors.right: overviewMainRail.right
        height: 18
        spacing: 4
        ActionButton {
            objectName: "earth-e6-prev"
            width: 33
            height: parent.height
            label: "◀"
            labelPixelSize: 12
            contentPadding: 0
            accentColor: Colors.cyan
            onClicked: overview.topicIndex = Overview.wrap(overview.topicIndex-1)
        }
        GohuText {
            objectName: "earth-e6-topic-label"
            width: Math.max(0,topicNavigation.width-33-33-60
                            -3*topicNavigation.spacing)
            height: parent.height
            text: "EARTH // " + overview.summary.title
            font.pixelSize: 11
            color: Colors.magenta
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        GohuText {
            width: 60
            height: parent.height
            text: (Overview.wrap(overview.topicIndex)+1)
                + " / " + Overview.TOPICS.length
            font.pixelSize: 10
            color: Colors.cyan
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        ActionButton {
            objectName: "earth-e6-next"
            width: 33
            height: parent.height
            label: "▶"
            labelPixelSize: 12
            contentPadding: 0
            accentColor: Colors.cyan
            onClicked: overview.topicIndex = Overview.wrap(overview.topicIndex+1)
        }
    }
    Rectangle {
        id: summaryRule
        objectName: "earth-e6-summary-divider"
        anchors.top: topicNavigation.bottom
        anchors.topMargin: 1
        anchors.left: topicNavigation.left
        anchors.right: topicNavigation.right
        height: 1
        color: Colors.cyan
    }
    QuietText {
        id: topicCaption
        objectName: "earth-e6-topic-caption"
        anchors.top: summaryRule.bottom
        anchors.topMargin: 1
        anchors.left: topicNavigation.left
        anchors.right: topicNavigation.right
        height: 10
        font.pixelSize: 9
        text: overview.summary.subtitle
        elide: Text.ElideRight
        color: Colors.orange
    }
    // E7 // The footer uses only a thin baseline. The former full-menu
    // button is gone, leaving four smaller cards with room for graphs.
    QuietText {
        id: sourceFooter
        objectName: "earth-e6-source-footer"
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 2
        anchors.left: overviewMainRail.left
        anchors.right: overviewMainRail.right
        height: 10
        font.pixelSize: 8
        color: Colors.cyan
        elide: Text.ElideRight
        text: overview.summary.footer
    }
    Row {
        id: summaryCards
        objectName: "earth-e6-summary-cards"
        anchors.left: overviewMainRail.left
        anchors.right: overviewMainRail.right
        anchors.top: topicCaption.bottom
        anchors.topMargin: 2
        anchors.bottom: sourceFooter.top
        anchors.bottomMargin: 2
        spacing: 4
        clip: true

        Repeater {
            model: overview.summary.cards
            delegate: Rectangle {
                required property var modelData
                required property int index
                readonly property var plot: overview.charts[index]
                objectName: "earth-e6-metric"
                width: Math.max(1,(summaryCards.width
                    -3*summaryCards.spacing)/4)
                height: summaryCards.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                clip: true

                QuietText {
                    id: cardLabel
                    anchors.top: parent.top
                    anchors.topMargin: 2
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 3
                    anchors.rightMargin: 3
                    height: 9
                    font.pixelSize: 8
                    text: modelData.label
                    elide: Text.ElideRight
                    color: Colors.orange
                }
                GohuText {
                    id: cardValue
                    anchors.top: cardLabel.bottom
                    anchors.topMargin: 1
                    anchors.left: cardLabel.left
                    anchors.right: cardLabel.right
                    height: 17
                    font.pixelSize: 13
                    text: modelData.value
                    elide: Text.ElideRight
                    color: Colors.white
                    verticalAlignment: Text.AlignVCenter
                }
                Row {
                    id: microChart
                    objectName: "earth-e7-microchart"
                    anchors.top: cardValue.bottom
                    anchors.topMargin: 1
                    anchors.left: cardLabel.left
                    anchors.right: cardLabel.right
                    height: 10
                    spacing: 2
                    clip: true
                    QuietText {
                        width: 48
                        height: parent.height
                        font.pixelSize: 7
                        text: plot.caption
                        color: Colors.cyan
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    Item {
                        id: plotRegion
                        width: Math.max(1,microChart.width-48-microChart.spacing)
                        height: microChart.height
                        Rectangle {
                            objectName: "earth-e7-meter-track"
                            visible: plot.type === "meter"
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            height: 4
                            color: Colors.black
                            border.width: 1
                            border.color: Colors.magenta
                            Rectangle {
                                width: plot.values.length && plot.values[0] !== null
                                    ? Math.max(0,parent.width*plot.values[0]) : 0
                                height: parent.height
                                color: Colors.cyan
                            }
                        }
                        Row {
                            objectName: "earth-e7-bar-strip"
                            visible: plot.type !== "meter"
                            anchors.fill: parent
                            spacing: 2
                            Repeater {
                                model: plot.type === "meter" ? [] : plot.values
                                delegate: Item {
                                    required property var modelData
                                    width: Math.max(1,(plotRegion.width
                                        -Math.max(0,plot.values.length-1)*2)
                                        /Math.max(1,plot.values.length))
                                    height: plotRegion.height
                                    Rectangle {
                                        anchors.bottom: parent.bottom
                                        width: parent.width
                                        height: modelData === null ? 1
                                            : plot.type === "marks" ? 4
                                            : Math.max(1,Math.round(
                                                parent.height*modelData))
                                        color: modelData === null
                                            ? Colors.magenta : Colors.cyan
                                        opacity: modelData === null ? 0.25
                                            : modelData <= 0 ? 0.16 : 1.0
                                    }
                                }
                            }
                        }
                    }
                }
                QuietText {
                    anchors.left: cardLabel.left
                    anchors.right: cardLabel.right
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 2
                    height: 9
                    font.pixelSize: 8
                    text: modelData.detail
                    elide: Text.ElideRight
                    color: Colors.cyan
                }
            }
        }
    }
}
