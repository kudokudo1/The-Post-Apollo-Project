import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices

// One independent, manual BBC World and Al Jazeera RSS control surface.
// GDELT remains a different provider with its own cooldown and analysis.
Column {
    id: publisherFeeds

    property bool stationOpen: true
    // M7 // The focused REPORTS page pins the existing request actions above
    // its scroll body. This component still owns the only two RSS services,
    // and keeps VIEW/HIDE plus headlines in the body below.
    property bool pinnedRequests: false
    // M9 // NEWS/REPORTS pins VIEW/HIDE beside the cyan headline title;
    // the same single RSS component keeps all expanded article rows below.
    property bool pinnedViews: false
    // Preserve GDELT's original visual order until the operator opens a feed.
    property string expandedPublisher: ""
    spacing: 8
    signal headlineSelected(var row)

    WeatherServices.StationPublisherRssService {
        id: bbc
        feedId: "bbc-world"
        active: publisherFeeds.stationOpen && publisherFeeds.visible
    }
    WeatherServices.StationPublisherRssService {
        id: alJazeera
        feedId: "al-jazeera-english"
        active: publisherFeeds.stationOpen && publisherFeeds.visible
    }
    readonly property var bbcBackend: bbc
    readonly property var alJazeeraBackend: alJazeera
    function requestPublisher(feedId) {
        const backend = feedId === "bbc-world" ? bbc
            : feedId === "al-jazeera-english" ? alJazeera : null;
        if (!stationOpen || !visible || !backend || !backend.canRequest)
            return false;
        expandedPublisher = feedId;
        return backend.request();
    }
    function togglePublisherView(feedId) {
        const backend = feedId === "bbc-world" ? bbc
            : feedId === "al-jazeera-english" ? alJazeera : null;
        if (!stationOpen || !visible || !backend || !backend.ready)
            return false;
        expandedPublisher = expandedPublisher === feedId ? "" : feedId;
        return true;
    }

    StationSectionDivider {
        width: parent.width
        title: "PUBLISHER NEWS // INDEPENDENT RSS SOURCES"
    }
    QuietText {
        width: parent.width
        text: "MANUAL ONLY // SEPARATE FROM GDELT // NO AUTO-RETRY OR EXTERNAL BROWSER"
        color: Colors.orange
        font.pixelSize: 9
        wrapMode: Text.WordWrap
    }

    Repeater {
        model: [
            {id:"bbc-world",short:"BBC",label:"BBC WORLD",accent:"cyan"},
            {id:"al-jazeera-english",short:"AL JAZEERA",label:"AL JAZEERA ENGLISH",
             accent:"magenta"}
        ]

        delegate: Column {
            id: publisherSourceRow
            required property var modelData
            readonly property var backend:
                modelData.id === "bbc-world" ? bbc : alJazeera
            readonly property color sourceColor:
                modelData.accent === "cyan" ? Colors.cyan : Colors.magenta
            width: publisherFeeds.width
            spacing: 5

            Row {
                width: parent.width
                visible: !(publisherFeeds.pinnedRequests && publisherFeeds.pinnedViews)
                height: visible ? 32 : 0
                spacing: 8

                ActionButton {
                    // CLASSIC keeps original inline requests; fixed REPORTS
                    // routes use the already-present top request rail.
                    visible: !publisherFeeds.pinnedRequests
                    width: publisherFeeds.pinnedRequests ? 0 : 150
                    height: 30
                    label: publisherSourceRow.backend.ready
                           ? "REFRESH " + publisherSourceRow.modelData.short
                           : "LOAD " + publisherSourceRow.modelData.short
                    labelPixelSize: 10
                    accentColor: publisherSourceRow.sourceColor
                    available: publisherSourceRow.backend.canRequest
                    onClicked: {
                        publisherFeeds.expandedPublisher =
                            publisherSourceRow.modelData.id;
                        publisherSourceRow.backend.request();
                    }
                }
                ActionButton {
                    visible: !publisherFeeds.pinnedViews
                    width: publisherFeeds.pinnedViews ? 0 : 86
                    height: 30
                    label: publisherFeeds.expandedPublisher
                           === publisherSourceRow.modelData.id ? "HIDE" : "VIEW"
                    labelPixelSize: 10
                    accentColor: publisherSourceRow.sourceColor
                    available: publisherSourceRow.backend.ready
                    onClicked: {
                        publisherFeeds.expandedPublisher =
                            publisherFeeds.expandedPublisher
                            === publisherSourceRow.modelData.id
                            ? "" : publisherSourceRow.modelData.id;
                    }
                }
                GohuText {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.max(0, parent.width - 254)
                    text: publisherSourceRow.modelData.label + " // " + publisherSourceRow.backend.sourceState
                    font.pixelSize: 11
                    color: publisherSourceRow.backend.failed ? Colors.orange : publisherSourceRow.sourceColor
                    elide: Text.ElideRight
                }
            }

            // A short source status remains in the report body after the
            // old button row is replaced by pinned VIEW/HIDE actions.
            QuietText {
                visible: publisherFeeds.pinnedViews
                width: parent.width
                text: publisherSourceRow.modelData.label + " // "
                      + publisherSourceRow.backend.sourceState
                font.pixelSize: 9
                color: publisherSourceRow.backend.failed
                    ? Colors.orange : publisherSourceRow.sourceColor
                elide: Text.ElideRight
            }
            QuietText {
                width: parent.width
                text: publisherSourceRow.backend.retryWaitSeconds > 0
                      ? "NEXT MANUAL REQUEST IN " + publisherSourceRow.backend.retryWaitSeconds + "s"
                      : publisherSourceRow.backend.ready
                        ? "LAST RECEIVED // "
                          + Qt.formatDateTime(publisherSourceRow.backend.lastUpdated, "MMM d, hh:mm AP")
                          + (publisherSourceRow.backend.usingCache ? " // SESSION CACHE" : " // FRESH REQUEST")
                        : "NOT REQUESTED // CLICK LOAD FOR PUBLISHER HEADLINES"
                font.pixelSize: 9
                color: Colors.white
                elide: Text.ElideRight
            }
            Repeater {
                model: publisherFeeds.expandedPublisher
                       === publisherSourceRow.modelData.id
                       && publisherSourceRow.backend.ready
                       ? publisherSourceRow.backend.rows : []
                delegate: Rectangle {
                    required property var modelData
                    width: publisherFeeds.width
                    height: 80
                    color: Colors.dark
                    border.width: 1
                    border.color: publisherSourceRow.sourceColor

                    Column {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 3

                        Row {
                            width: parent.width
                            height: 30
                            spacing: 6
                            GohuText {
                                width: Math.max(0, parent.width - 98)
                                height: 30
                                text: modelData.title
                                font.pixelSize: 11
                                color: Colors.white
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                            ActionButton {
                                width: 92
                                height: 29
                                label: "INSPECT"
                                labelPixelSize: 10
                                accentColor: publisherSourceRow.sourceColor
                                onClicked: publisherFeeds.headlineSelected(modelData)
                            }
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.source + " // " + modelData.time
                            font.pixelSize: 9
                            color: publisherSourceRow.sourceColor
                            elide: Text.ElideRight
                        }
                        QuietText {
                            width: parent.width
                            text: modelData.summary || "HEADLINE ONLY // ARTICLE BODY NOT LOADED"
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }
                    }
                }
            }
        }
    }

    QuietText {
        width: parent.width
        font.pixelSize: 9
        color: Colors.orange
        text: "OPEN ONE PUBLISHER AT A TIME WITH VIEW/HIDE // RSS SUMMARIES ONLY // INSPECT USES IN-STATION METADATA VIEWER // GDELT ANALYSIS IS SEPARATE"
        wrapMode: Text.WordWrap
    }
}
