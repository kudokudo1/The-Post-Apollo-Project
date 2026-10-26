import QtQuick
import Quickshell
import Quickshell.Io
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
    // Coordinates relative to StationChannelScreen. This is the actual
    // player bay (excluding CLOSE/MUTE header and footer), NOT a request
    // to spawn or position any external process.
    readonly property rect playerViewportRect:
        Qt.rect(playerBay.x, playerBay.y, playerBay.width, playerBay.height)
    property string viewerProbeState: "VIEWER CHECK NOT RUN"

    // V0 probes only which external browser binary could be used. The helper
    // never launches a browser, contacts a provider, or touches compositor
    // geometry. It deliberately reports containment unavailable.
    Process {
        id: viewerProbe
        command: ["python3", "-B",
                  Quickshell.shellDir + "/scripts/weather/news_viewer_preflight.py",
                  "inspect"]
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(String(text || ""));
                    channelScreen.viewerProbeState =
                        result.can_launch === false
                        && result.state === "BLOCKED_VIEWPORT_UNAVAILABLE"
                        ? String(result.message || "VIEWER NOT CONNECTED")
                        : "VIEWER PREFLIGHT CONTRACT UNAVAILABLE";
                } catch (error) {
                    channelScreen.viewerProbeState = "VIEWER PREFLIGHT UNAVAILABLE";
                }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode !== 0)
                channelScreen.viewerProbeState = "VIEWER PREFLIGHT FAILED";
        }
    }

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
            ActionButton {
                width: 170
                height: 31
                anchors.horizontalCenter: parent.horizontalCenter
                label: viewerProbe.running ? "CHECKING ENGINE" : "CHECK VIEWER"
                labelPixelSize: 11
                available: !viewerProbe.running
                onClicked: {
                    channelScreen.viewerProbeState = "CHECKING BROWSER AVAILABILITY";
                    viewerProbe.running = true;
                }
            }
            QuietText {
                width: parent.width
                color: Colors.cyan
                font.pixelSize: 11
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: channelScreen.viewerProbeState
            }
            SecondaryText {
                width: parent.width
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: "CLOSE returns to NEWS. This check cannot play video;"
                      + " a separate viewer process with verified Stage Director"
                      + " containment is still required."
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
