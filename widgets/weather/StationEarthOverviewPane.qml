import QtQuick
import "../../components"
import "StationEarthOverviewPolicy.js" as Overview
import "StationGroundEnvironmentPolicy.js" as Environment

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

    Row {
        id: topicNavigation
        objectName: "earth-e6-overview-arrows"
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        anchors.topMargin: 2
        height: 23
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
            font.pixelSize: 12
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
        anchors.topMargin: 2
        anchors.left: topicNavigation.left
        anchors.right: topicNavigation.right
        height: 2
        color: Colors.cyan
    }

    QuietText {
        id: topicCaption
        objectName: "earth-e6-topic-caption"
        anchors.top: summaryRule.bottom
        anchors.topMargin: 2
        anchors.left: topicNavigation.left
        anchors.right: topicNavigation.right
        height: 12
        font.pixelSize: 9
        text: overview.summary.subtitle
        elide: Text.ElideRight
        color: Colors.orange
    }

    ActionButton {
        id: fullMenu
        objectName: "earth-e6-open-topic"
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 3
        anchors.right: topicNavigation.right
        height: 21
        width: 128
        label: "OPEN FULL MENU"
        labelPixelSize: 9
        contentPadding: 1
        accentColor: Colors.magenta
        onClicked: overview.openTopicRequested(overview.currentTopic.id)
    }

    QuietText {
        id: sourceFooter
        objectName: "earth-e6-source-footer"
        anchors.left: topicNavigation.left
        anchors.right: fullMenu.left
        anchors.rightMargin: 5
        anchors.verticalCenter: fullMenu.verticalCenter
        height: 12
        font.pixelSize: 8
        color: Colors.cyan
        elide: Text.ElideRight
        text: overview.summary.footer
    }

    Row {
        id: summaryCards
        objectName: "earth-e6-summary-cards"
        anchors.left: topicNavigation.left
        anchors.right: topicNavigation.right
        anchors.top: topicCaption.bottom
        anchors.topMargin: 3
        anchors.bottom: fullMenu.top
        anchors.bottomMargin: 3
        spacing: 4
        clip: true

        Repeater {
            model: overview.summary.cards
            delegate: Rectangle {
                required property var modelData
                objectName: "earth-e6-metric"
                width: Math.max(1,(summaryCards.width
                    -3*summaryCards.spacing)/4)
                height: summaryCards.height
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                clip: true

                QuietText {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 4
                    height: 10
                    font.pixelSize: 8
                    text: modelData.label
                    elide: Text.ElideRight
                    color: Colors.orange
                }
                GohuText {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.margins: 4
                    height: 18
                    font.pixelSize: 14
                    text: modelData.value
                    elide: Text.ElideRight
                    color: Colors.white
                    verticalAlignment: Text.AlignVCenter
                }
                QuietText {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 4
                    height: 10
                    font.pixelSize: 8
                    text: modelData.detail
                    elide: Text.ElideRight
                    color: Colors.cyan
                }
            }
        }
    }
}
