import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices
import "StationViewerPolicy.js" as ViewerPolicy

// Source-first stage. All records shown come from a backend, never examples.
// MAP is an event index before an actual map canvas is integrated; RADIO is
// a stream directory before MediaDeck's persistent transport is connected.
Rectangle {
    id: stationDiscovery

    property string domain: "map"
    property bool stationOpen: true
    property bool viewerOpen: false
    property var selectedNews: null

    // Expose the child provider's actual NEWS state to the Station header.
    // Configured is not the same thing as received articles.
    readonly property string feedBadge: {
        if (source.failed)
            return source.errorText
                   + (source.retryWaitSeconds > 0
                      ? " // RETRY " + source.retryWaitSeconds + "s" : "");
        if (source.loading)
            return "READING // NEWS";
        if (source.ready)
            return "NEWS LIVE // " + source.rows.length;
        if (source.retryWaitSeconds > 0)
            return "WAIT // RETRY " + source.retryWaitSeconds + "s";
        return "CONNECTING // NEWS";
    }
    readonly property color feedBadgeColor:
        source.failed ? Colors.orange
        : source.loading ? Colors.orange
        : source.ready ? Colors.magenta : Colors.orange


    // NEWS selection stays in the Station. GDELT supplies a headline record,
    // not verified article body text.
    function openRow(row) {
        if (domain === "news") {
            const next = ViewerPolicy.normalizeNews(row);
            if (!next) return;
            selectedNews = next;
            viewerOpen = true;
            return;
        }
        // MAP's real internal event/map adapter is a later bounded stage.
        // Preserve its existing path without changing other domain ownership.
        if (row && row.url)
            Qt.openUrlExternally(row.url);
    }

    function closeViewer() {
        viewerOpen = false;
        selectedNews = null;
    }

    onDomainChanged: closeViewer()
    onStationOpenChanged: { if (!stationOpen) closeViewer(); }

    readonly property string modeTitle:
        domain === "map" ? "⌖  MAP // EVENT SOURCES"
        : domain === "news" ? "▤  NEWS // HEADLINES"
        : "◉  RADIO // STATIONS"
    readonly property string providerTitle:
        domain === "map" ? "NASA EONET // OPEN NATURAL EVENTS"
        : domain === "news" ? "GDELT DOC // WORLD EVENT HEADLINES"
        : "RADIO BROWSER // TOP VOTED STREAMS"
    readonly property string sourceCaution:
        domain === "map" ? "EVENT INDEX CONNECTED // SPATIAL MAP CANVAS NOT YET WIRED"
        : domain === "news" ? "ARTICLE DISCOVERY // NOT YET LIVE VIDEO OR STORY CLUSTERS"
        : "STATION DIRECTORY // PERSISTENT PLAYBACK NOT YET WIRED"
    readonly property var plannedSources: {
        if (domain === "map")
            return [
                {name:"NASA EONET // EVENT INDEX", state:"SOURCE CONNECTED"},
                {name:"USGS // EARTHQUAKES", state:"GROUND FEED EXISTS"},
                {name:"RAINVIEWER // RADAR TILES", state:"NOT WIRED"},
                {name:"NASA FIRMS // FIRE HOTSPOTS", state:"NOT WIRED"},
                {name:"MAP CANVAS / LAYER SWITCHER", state:"NOT WIRED"}
            ];
        if (domain === "news")
            return [
                {name:"GDELT DOC // ARTICLE LIST", state:"ENDPOINT CONFIGURED"},
                {name:"TOPICS / SOURCES / REGIONS", state:"NOT WIRED"},
                {name:"LIVE NEWS / VIDEO", state:"NOT WIRED"},
                {name:"STORY CLUSTERS / DOSSIERS", state:"NOT WIRED"}
            ];
        return [
            {name:"RADIO BROWSER // STATION LIST", state:"SOURCE CONNECTED"},
            {name:"COUNTRY / LANGUAGE / TAGS", state:"NOT WIRED"},
            {name:"MEDIA DECK // PERSISTENT PLAYBACK", state:"NOT WIRED"},
            {name:"STATION FAVORITES", state:"NOT WIRED"},
            {name:"RF / SDR / NOAA WEATHER RADIO", state:"HARDWARE LATER"}
        ];
    }

    WeatherServices.StationDiscoveryService {
        id: source
        domain: stationDiscovery.domain
        active: stationDiscovery.stationOpen && stationDiscovery.visible
    }

    color: Colors.black

    Flickable {
        id: discoveryScroll
        anchors.fill: parent
        visible: !stationDiscovery.viewerOpen
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentWidth: width
        contentHeight: Math.max(height, content.y + content.implicitHeight + 12)

        Column {
            id: content
            x: 20
            y: 12
            width: Math.max(0, discoveryScroll.width - 40)
            spacing: 12

            Row {
                width: parent.width
                spacing: 20

                GohuText {
                    text: stationDiscovery.modeTitle
                    color: Colors.cyan
                    font.pixelSize: 23
                }

                GohuText {
                    text: source.failed ? source.errorText
                          : source.loading ? "RECEIVING"
                          : source.ready ? "RECEIVED " + source.rows.length
                            : source.retryWaitSeconds > 0 ? "WAITING" : "OFFLINE"
                    font.pixelSize: 12
                    color: source.failed ? Colors.orange
                           : source.ready ? Colors.cyan : Colors.white
                }
            }

            StationSectionDivider {
                width: parent.width
                title: "SOURCE RACK // WHAT IS CONNECTED"
            }

            Column {
                width: parent.width
                spacing: 5

                Repeater {
                    model: stationDiscovery.plannedSources

                    delegate: Row {
                        required property var modelData
                        width: content.width
                        spacing: 16

                        GohuText {
                            width: Math.max(150, content.width - 250)
                            text: modelData.name
                            color: Colors.white
                            font.pixelSize: 12
                        }

                        GohuText {
                            text: modelData.state
                            color: modelData.state === "SOURCE CONNECTED"
                                   || modelData.state === "GROUND FEED EXISTS"
                                   ? Colors.cyan : Colors.orange
                            font.pixelSize: 11
                        }
                    }
                }
            }

            StationSectionDivider {
                width: parent.width
                title: stationDiscovery.providerTitle
            }

            Row {
                width: parent.width
                height: stationDiscovery.domain === "news" ? 34 : 0
                visible: stationDiscovery.domain === "news"
                spacing: 12
                ActionButton {
                    width: 102
                    height: 30
                    label: "RETRY NEWS"
                    labelPixelSize: 11
                    available: source.canRetry
                    onClicked: source.refresh()
                }
                QuietText {
                    anchors.verticalCenter: parent.verticalCenter
                    text: source.retryWaitSeconds > 0
                          ? "NEXT REQUEST IN " + source.retryWaitSeconds + "s"
                          : source.failed ? "REQUEST FAILED // RETRY AVAILABLE"
                          : source.loading ? "REQUEST IN PROGRESS"
                          : "ON DEMAND // 15-MIN REFRESH"
                    font.pixelSize: 11
                }
            }

            QuietText {
                width: parent.width
                text: stationDiscovery.sourceCaution
                font.pixelSize: 11
            }

            QuietText {
                visible: source.failed || !source.ready || source.rows.length === 0
                width: parent.width
                text: source.failed
                      ? source.errorText + " // PRIOR DATA MAY BE STALE"
                      : source.loading ? "RECEIVING REMOTE RECORDS"
                      : source.retryWaitSeconds > 0
                        ? "REQUEST HELD // PROVIDER COOLDOWN"
                      : source.ready ? "NO RECORDS RETURNED"
                        : "BACKEND NOT YET AVAILABLE"
                font.pixelSize: 12
            }

            Repeater {
                model: source.ready ? source.rows : []

                delegate: Rectangle {
                    required property var modelData
                    width: content.width
                    height: 88
                    color: Colors.dark
                    border.width: 1
                    border.color: entryMouse.containsMouse ? Colors.yellow
                                  : Colors.cyan

                    Column {
                        anchors.left: parent.left
                        anchors.right: openLabel.left
                        anchors.top: parent.top
                        anchors.leftMargin: 12
                        anchors.topMargin: 8
                        anchors.rightMargin: 12
                        spacing: 6

                        GohuText {
                            width: parent.width
                            text: modelData.title
                            color: Colors.white
                            elide: Text.ElideRight
                            font.pixelSize: 15
                        }

                        SecondaryText {
                            width: parent.width
                            text: modelData.detail
                            elide: Text.ElideRight
                            font.pixelSize: 12
                        }

                        QuietText {
                            width: parent.width
                            text: modelData.time
                            elide: Text.ElideRight
                            font.pixelSize: 10
                        }
                    }

                    GohuText {
                        id: openLabel
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: 12
                        text: stationDiscovery.domain === "news" ? "VIEW HERE"
                              : modelData.url !== "" ? modelData.action : "NO LINK"
                        color: entryMouse.containsMouse ? Colors.yellow : Colors.cyan
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: entryMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: stationDiscovery.domain === "news"
                                     || modelData.url !== ""
                                     ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: stationDiscovery.openRow(modelData)
                    }
                }
            }

            QuietText {
                width: parent.width
                text: source.ready
                      ? "LAST RECEIVED // "
                        + Qt.formatDateTime(source.lastUpdated, "hh:mm") + " LOCAL"
                      : "LAST RECEIVED // --"
                font.pixelSize: 11
            }
        }
    }

    // Destroy the optional webpage when backing out, retaining the discovery
    // list position and its existing provider connection.
    Component {
        id: newsViewerComponent
        StationViewerHost {
            selectedRecord: stationDiscovery.selectedNews
            onBackRequested: stationDiscovery.closeViewer()
        }
    }
    Loader {
        anchors.fill: parent
        active: stationDiscovery.viewerOpen
        sourceComponent: newsViewerComponent
        z: 3
    }

    NeonScrollBar {
        flickable: discoveryScroll
        handleStyle: "star"
        geometryHost: stationDiscovery
        visible: !stationDiscovery.viewerOpen && scrollable
    }
}
