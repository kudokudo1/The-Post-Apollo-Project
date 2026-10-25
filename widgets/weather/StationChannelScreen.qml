import QtQuick
import "../../components"
import "StationViewerPolicy.js" as ViewerPolicy

// SAFE MODE // Operator runtime crash: QS 0.3.2, Qt 6.11.2, SIGABRT in
// Qt6WebEngineCore after "Argument list is empty, the program name is not
// passed to QCoreApplication". Loading the optional WebEngine QML file can
// terminate *all of Quickshell*, so NO WebEngine object or dynamic Loader
// belongs on this NEWS code path until an independently tested renderer
// process is owned by the authorized Stage Director / viewer workstream.
// Keep the catalog / CLOSE contract usable without launching any process.
Rectangle {
    id: channelScreen

    property var selectedRecord: null
    property bool muted: true
    signal closeRequested()

    readonly property string sourceUrl:
        selectedRecord ? ViewerPolicy.safeArticleUrl(selectedRecord.url) : ""
    readonly property bool playbackAvailable: false

    color: Colors.black
    clip: true

    Rectangle {
        id: titleStrip
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 46
        color: Colors.dark
        border.width: 1
        border.color: Colors.cyan

        ActionButton {
            id: closeButton
            anchors.left: parent.left
            anchors.leftMargin: 8
            anchors.verticalCenter: parent.verticalCenter
            width: 99
            height: 31
            label: "×  CLOSE"
            labelPixelSize: 11
            onClicked: channelScreen.closeRequested()
        }

        GohuText {
            anchors.left: closeButton.right
            anchors.leftMargin: 11
            anchors.right: muteButton.left
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            text: selectedRecord ? selectedRecord.title : "NO CHANNEL SELECTED"
            color: Colors.white
            font.pixelSize: 15
            elide: Text.ElideRight
        }

        ActionButton {
            id: muteButton
            anchors.right: parent.right
            anchors.rightMargin: 9
            anchors.verticalCenter: parent.verticalCenter
            width: 99
            height: 31
            label: "MUTE: ON"
            labelPixelSize: 10
            available: channelScreen.playbackAvailable
        }
    }

    Rectangle {
        id: playerBay
        anchors.top: titleStrip.bottom
        anchors.bottom: footerStrip.top
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
        color: Colors.black
        border.width: 1
        border.color: Colors.cyan

        Column {
            anchors.centerIn: parent
            width: Math.max(0, parent.width - 48)
            spacing: 14

            GohuText {
                width: parent.width
                font.pixelSize: 20
                color: Colors.orange
                horizontalAlignment: Text.AlignHCenter
                text: "NEWS VIEWER // SAFE MODE"
            }
            SecondaryText {
                width: parent.width
                font.pixelSize: 13
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                text: "In-process QtWebEngine playback is disabled because it"
                      + " crashes Quickshell during browser startup. The channel"
                      + " catalog and controls remain available."
            }
            QuietText {
                width: parent.width
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                text: selectedRecord
                      ? String(selectedRecord.source || "SOURCE UNKNOWN")
                        + " // " + String(selectedRecord.time || "ACCESS UNVERIFIED")
                      : "NO CHANNEL SELECTED"
                wrapMode: Text.WordWrap
            }
            QuietText {
                width: parent.width
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: channelScreen.sourceUrl === ""
                      ? "NO VALID HTTPS DESTINATION"
                      : "DESTINATION REGISTERED // EXTERNAL VIEWER NOT CONNECTED"
            }
            SecondaryText {
                width: parent.width
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: "CLOSE returns to NEWS. A separate browser/video"
                      + " process with Stage Director containment is pending;"
                      + " no video or audio is launched from this view."
            }
        }
    }

    Rectangle {
        id: footerStrip
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 31
        color: Colors.dark

        QuietText {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            text: "WEBENGINE DISABLED // QUICKSHELL CRASH PROTECTION"
        }
    }
}
