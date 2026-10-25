import QtQuick
import "../../components"
import "StationViewerPolicy.js" as ViewerPolicy

// NEWS metadata viewer in crash-safe mode. Reports remain inspectable, but
// QtWebEngine must never instantiate inside Quickshell until an isolated
// renderer is connected. Preserve the existing BACK / report list contract.
Rectangle {
    id: stationViewer

    property var selectedRecord: null
    signal backRequested()

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
                width: 160
                height: 34
                label: "READER DISABLED"
                labelPixelSize: 11
                available: false
            }
            QuietText {
                anchors.verticalCenter: parent.verticalCenter
                width: Math.max(90, parent.width - 170)
                font.pixelSize: 11
                elide: Text.ElideRight
                text: "CRASH PROTECTION // REPORT METADATA STILL AVAILABLE"
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
