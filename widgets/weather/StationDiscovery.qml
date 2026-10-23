import QtQuick
import "../../components"
import "../../services/weather" as WeatherServices

// Source-first stage. All records shown come from a backend, never examples.
// MAP is an event index before an actual map canvas is integrated; RADIO is
// a stream directory before MediaDeck's persistent transport is connected.
Rectangle {
    id: stationDiscovery

    property string domain: "map"
    property bool stationOpen: true

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
                {name:"GDELT DOC // ARTICLE LIST", state:"SOURCE CONNECTED"},
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
                    text: source.failed ? "FETCH FAILED"
                          : source.loading && !source.ready ? "RECEIVING"
                          : source.ready ? "RECEIVED " + source.rows.length
                            : "OFFLINE"
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
                        text: modelData.url !== "" ? modelData.action : "NO LINK"
                        color: entryMouse.containsMouse ? Colors.yellow : Colors.cyan
                        font.pixelSize: 11
                    }

                    MouseArea {
                        id: entryMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: modelData.url !== ""
                                     ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: {
                            if (modelData.url !== "")
                                Qt.openUrlExternally(modelData.url);
                        }
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

    NeonScrollBar {
        flickable: discoveryScroll
        handleStyle: "star"
        geometryHost: stationDiscovery
        visible: scrollable
    }
}
