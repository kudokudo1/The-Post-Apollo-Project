import QtQuick
import "../../components"
import "StationViewerPolicy.js" as ViewerPolicy

// Reusable Weather Station VIEW destination. This first adapter handles GDELT
// NEWS records. Later MAP/video adapters can reuse its OPEN / VIEW / BACK
// lifecycle without promising that all renderers are terminal applications.
Rectangle {
    id: stationViewer

    property var selectedRecord: null
    signal backRequested()

    readonly property string articleUrl:
        selectedRecord ? ViewerPolicy.safeArticleUrl(selectedRecord.url) : ""
    readonly property bool canReadWeb: articleUrl !== ""
    property bool webRequested: false
    property bool audioAllowed: false
    readonly property bool isChannel:
        selectedRecord && selectedRecord.kind === "channel"
    readonly property bool webFailed:
        webRequested && (webLoader.status === Loader.Error
                         || (webLoader.item
                             && (webLoader.item.loadState === "FAILED"
                                 || webLoader.item.blockedNavigation)))
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
                width: 155
                height: 34
                label: stationViewer.webRequested
                       ? (stationViewer.isChannel ? "CLOSE CHANNEL" : "CLOSE ARTICLE")
                       : (stationViewer.isChannel ? "WATCH IN STATION" : "READ ARTICLE")
                labelPixelSize: 12
                available: stationViewer.canReadWeb || stationViewer.webRequested
                onClicked: {
                    stationViewer.webRequested = !stationViewer.webRequested;
                }
            }

            ActionButton {
                width: 114
                height: 34
                visible: stationViewer.isChannel
                label: stationViewer.audioAllowed ? "MUTE" : "ENABLE AUDIO"
                labelPixelSize: 10
                available: stationViewer.webRequested
                onClicked: {
                    stationViewer.audioAllowed = !stationViewer.audioAllowed;
                    if (webLoader.item)
                        webLoader.item.audioAllowed = stationViewer.audioAllowed;
                }
            }

            QuietText {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(90, parent.width - (stationViewer.isChannel ? 290 : 165))
                font.pixelSize: 11
                elide: Text.ElideRight
                text: stationViewer.webRequested
                      ? "GUARDED WEB RENDERER // NO POPUPS OR EXTERNAL TABS"
                      : stationViewer.canReadWeb
                      ? (stationViewer.isChannel
                         ? "OFFICIAL SITE // PLAYBACK DEPENDS ON PROVIDER"
                         : "WEBPAGE LOADS HERE ONLY WHEN REQUESTED")
                      : "FULL ARTICLE URL UNAVAILABLE"
            }
        }

        Rectangle {
            width: parent.width
            height: Math.max(140, stationViewer.height - y - 47)
            clip: true
            color: Colors.black
            border.width: 1
            border.color: Colors.cyan

            // Importing QtWebEngine is optional and lazy. An unavailable
            // module must never prevent the metadata view from working.
            Loader {
                id: webLoader
                anchors.fill: parent
                anchors.margins: 2
                active: stationViewer.webRequested && stationViewer.canReadWeb
                source: "StationNewsWebView.qml"
                onLoaded: {
                    if (item) {
                        item.articleUrl = stationViewer.articleUrl;
                        item.audioAllowed = stationViewer.audioAllowed;
                    }
                }
            }

            Column {
                anchors.centerIn: parent
                width: Math.max(0, parent.width - 32)
                spacing: 10
                visible: !stationViewer.webRequested || stationViewer.webFailed

                GohuText {
                    width: parent.width
                    font.pixelSize: 16
                    color: stationViewer.webFailed ? Colors.orange : Colors.cyan
                    horizontalAlignment: Text.AlignHCenter
                    text: stationViewer.webFailed
                          ? "ARTICLE RENDERER UNAVAILABLE"
                          : "INTERNAL NEWS VIEW // READY"
                }
                SecondaryText {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 12
                    text: stationViewer.webFailed
                          ? "This site could not be loaded here. The report title,"
                            + " source and time remain available above."
                          : stationViewer.isChannel
                            ? "This entry is a source directory record, not proof"
                              + " of live playback. WATCH IN STATION attempts"
                              + " the provider website here. Restricted players"
                              + " may refuse embedded playback."
                            : "This record contains a headline and source information."
                              + " Select READ ARTICLE to try the original webpage"
                              + " inside Weather Station. A headline is not the"
                              + " full article."
                }
            }
        }

        QuietText {
            width: parent.width
            font.pixelSize: 10
            text: stationViewer.isChannel
                  ? "INTERNAL VIEW ONLY // NO AUTOPLAY // PROVIDER ACCESS RULES APPLY"
                  : "EXTERNAL BROWSER NOT OPENED // ARTICLE CONTENT MAY BE RESTRICTED"
            elide: Text.ElideRight
        }
    }
}
