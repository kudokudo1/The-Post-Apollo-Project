import QtQuick
import "../../components"
import "StationViewerPolicy.js" as ViewerPolicy

// NEWS metadata viewer in crash-safe mode. Reports remain inspectable, but
// QtWebEngine must never instantiate inside Quickshell until an isolated
// renderer is connected. Preserve the existing BACK / report list contract.
Rectangle {
    id: stationViewer

    property var selectedRecord: null
    property bool locationLoading: false
    property bool locationReady: false
    property bool locationFailed: false
    property string locationError: ""
    property var locationRows: []
    property string locationFeedName: ""
    property string locationSliceUtc: ""
    property string locationMatchMethod: ""
    property string locationSemantics: ""
    signal backRequested()
    signal locateRequested()
    signal showOnMapRequested()

    readonly property string articleUrl:
        selectedRecord ? ViewerPolicy.safeArticleUrl(selectedRecord.url) : ""
    readonly property bool canReadWeb: false
    readonly property bool isChannel:
        selectedRecord && selectedRecord.kind === "channel"
    color: Colors.black

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 9

        Row {
            width: parent.width
            height: 36
            spacing: 10

            ActionButton {
                width: 100
                height: 34
                label: "◂  BACK"
                labelPixelSize: 12
                onClicked: stationViewer.backRequested()
            }

            GohuText {
                anchors.verticalCenter: parent.verticalCenter
                text: stationViewer.isChannel ? "NEWS // CHANNEL VIEW"
                      : "NEWS // INTERNAL VIEWER"
                color: Colors.cyan
                font.pixelSize: 17
            }
        }

        StationSectionDivider {
            width: parent.width
            title: stationViewer.isChannel ? "SELECTED SOURCE // REGISTERED DESTINATION"
                                          : "GDELT DISCOVERY // SELECTED REPORT"
        }

        Rectangle {
            width: parent.width
            height: 123
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan

            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 8

                GohuText {
                    width: parent.width
                    text: selectedRecord ? selectedRecord.title : "NO REPORT SELECTED"
                    font.pixelSize: 16
                    color: Colors.white
                    wrapMode: Text.WordWrap
                    maximumLineCount: 3
                    elide: Text.ElideRight
                }
                SecondaryText {
                    width: parent.width
                    text: selectedRecord ? selectedRecord.source : "SOURCE UNAVAILABLE"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
                QuietText {
                    width: parent.width
                    text: selectedRecord ? selectedRecord.time : "TIME UNAVAILABLE"
                    font.pixelSize: 11
                }
            }
        }

        Row {
            width: parent.width
            height: 36
            spacing: 10

            ActionButton {
                width: 150
                height: 34
                label: "READER DISABLED"
                labelPixelSize: 10
                available: false
            }

            ActionButton {
                width: 170
                height: 34
                label: stationViewer.locationLoading
                       ? "LOCATING..."
                       : "LOCATE MENTIONS"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: !stationViewer.isChannel
                           && stationViewer.articleUrl !== ""
                           && stationViewer.selectedRecord
                           && String(
                                  stationViewer.selectedRecord.rawTime || ""
                              ) !== ""
                           && !stationViewer.locationLoading
                onClicked: stationViewer.locateRequested()
            }

            ActionButton {
                width: 142
                height: 34
                label: "SHOW ON MAP"
                labelPixelSize: 10
                accentColor: Colors.magenta
                available: stationViewer.locationReady
                           && stationViewer.locationRows.length > 0
                onClicked: stationViewer.showOnMapRequested()
            }

            QuietText {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(90, parent.width - 492)
                font.pixelSize: 10
                elide: Text.ElideRight
                text: stationViewer.locationReady
                      && stationViewer.locationRows.length > 0
                      ? "TRANSFER VERIFIED GKG MENTIONS TO MAP"
                      : "GKG LOOKUP IS MANUAL // ARTICLE URL + SEENDATE JOIN"
            }
        }

        Rectangle {
            width: parent.width
            height: visible ? 170 : 0
            visible: !stationViewer.isChannel
                     && (stationViewer.locationLoading
                         || stationViewer.locationReady
                         || stationViewer.locationFailed)
            clip: true
            color: Colors.dark
            border.width: 1
            border.color: stationViewer.locationFailed
                          ? Colors.orange
                          : stationViewer.locationReady
                            ? Colors.magenta : Colors.cyan

            Column {
                anchors.fill: parent
                anchors.margins: 9
                spacing: 5

                Row {
                    width: parent.width
                    spacing: 10

                    GohuText {
                        width: 210
                        text: stationViewer.locationLoading
                              ? "READING GKG SLICE"
                              : stationViewer.locationFailed
                                ? "LOCATION LOOKUP FAILED"
                                : "MENTIONED LOCATIONS // "
                                  + stationViewer.locationRows.length
                        font.pixelSize: 10
                        color: stationViewer.locationFailed
                               ? Colors.orange : Colors.magenta
                    }

                    QuietText {
                        width: Math.max(0, parent.width - 220)
                        text: stationViewer.locationReady
                              ? (stationViewer.locationFeedName || "GKG")
                                + " // "
                                + (stationViewer.locationSliceUtc || "--")
                                + " // "
                                + (stationViewer.locationMatchMethod || "--")
                              : stationViewer.locationError
                        elide: Text.ElideRight
                        font.pixelSize: 9
                    }
                }

                Column {
                    width: parent.width
                    spacing: 3
                    visible: stationViewer.locationReady
                             && stationViewer.locationRows.length > 0

                    Repeater {
                        model: stationViewer.locationRows.slice(0, 5)

                        delegate: Row {
                            required property var modelData
                            width: parent.width
                            spacing: 10

                            GohuText {
                                width: 290
                                text: modelData.name
                                elide: Text.ElideRight
                                font.pixelSize: 9
                                color: Colors.white
                            }

                            QuietText {
                                width: 170
                                text: modelData.typeLabel
                                elide: Text.ElideRight
                                font.pixelSize: 8
                                color: Colors.cyan
                            }

                            QuietText {
                                width: 220
                                text: Number(modelData.latitude).toFixed(2)
                                      + ", "
                                      + Number(modelData.longitude).toFixed(2)
                                font.pixelSize: 8
                            }

                            QuietText {
                                width: Math.max(0, parent.width - 710)
                                text: "MENTIONS "
                                      + modelData.mentionCount
                                      + " // OFFSET "
                                      + modelData.firstOffset
                                elide: Text.ElideRight
                                font.pixelSize: 8
                            }
                        }
                    }
                }

                QuietText {
                    visible: stationViewer.locationReady
                             && stationViewer.locationRows.length === 0
                    width: parent.width
                    text: stationViewer.locationError !== ""
                          ? stationViewer.locationError
                          : "ARTICLE MATCHED // NO GKG LOCATION MENTIONS"
                    font.pixelSize: 9
                    color: Colors.orange
                }

                QuietText {
                    width: parent.width
                    text: stationViewer.locationSemantics !== ""
                          ? stationViewer.locationSemantics
                          : "MENTIONED PLACES ONLY // NOT VERIFIED EVENT LOCATION"
                    elide: Text.ElideRight
                    font.pixelSize: 8
                    color: Colors.orange
                }
            }
        }

        Rectangle {
            width: parent.width
            height: Math.max(140, stationViewer.height - y - 47)
            clip: true
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            Column {
                anchors.centerIn: parent
                width: Math.max(0, parent.width - 32)
                spacing: 10

                GohuText {
                    width: parent.width
                    font.pixelSize: 16
                    color: Colors.orange
                    horizontalAlignment: Text.AlignHCenter
                    text: "INTERNAL ARTICLE RENDERER // SAFE MODE"
                }
                SecondaryText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 12
                    text: "The original article page cannot be opened here"
                          + " until an isolated web renderer is connected."
                          + " Quickshell's in-process WebEngine caused a"
                          + " fatal crash. The headline, publisher and time"
                          + " remain available above."
                }
                QuietText {
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    font.pixelSize: 11
                    text: stationViewer.articleUrl === ""
                          ? "FULL ARTICLE URL UNAVAILABLE"
                          : "ARTICLE HTTPS DESTINATION REGISTERED"
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 10
            text: "WEBENGINE DISABLED // NO BROWSER PROCESS LAUNCHED"
            elide: Text.ElideRight
        }
    }
}
