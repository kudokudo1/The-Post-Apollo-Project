import QtQuick
import "../../components"
import "StationViewerPolicy.js" as ViewerPolicy

// Direct NEWS channel destination. The source rack disappears behind one
// maximized-in-bay video/web surface; CLOSE returns to the unchanged list.
// QtWebEngine itself is optional and compiled only after the operator clicks
// WATCH IN STATION. This is NOT a true Kitty/browser surface embed.
Rectangle {
    id: channelScreen

    property var selectedRecord: null
    property bool muted: true
    signal closeRequested()
    signal muteToggled()

    readonly property string sourceUrl:
        selectedRecord ? ViewerPolicy.safeArticleUrl(selectedRecord.url) : ""
    readonly property bool noRenderer: channelLoader.status === Loader.Error
    readonly property bool loadingRenderer:
        channelLoader.status === Loader.Loading
    readonly property bool blocked:
        !!(channelLoader.item && channelLoader.item.blockedNavigation)
    readonly property bool pageFailed:
        !!(channelLoader.item && channelLoader.item.loadState === "FAILED")
    readonly property string pageError:
        channelLoader.item ? String(channelLoader.item.loadError || "") : ""

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
            label: channelScreen.muted ? "MUTE: ON" : "MUTE: OFF"
            labelPixelSize: 10
            onClicked: channelScreen.muteToggled()
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

        Loader {
            id: channelLoader
            anchors.fill: parent
            anchors.margins: 2
            active: channelScreen.sourceUrl !== ""
            source: "StationNewsWebView.qml"
            onLoaded: {
                if (item) {
                    item.articleUrl = channelScreen.sourceUrl;
                    item.audioAllowed = !channelScreen.muted;
                }
            }
            onStatusChanged: {
                if (status === Loader.Error)
                    console.warn("Weather NEWS: optional QtWebEngine viewer could not be constructed; check QtWebEngine QML module and Quickshell host initialization");
            }
        }

        Column {
            anchors.centerIn: parent
            width: Math.max(0, parent.width - 40)
            spacing: 13
            visible: channelScreen.noRenderer
                     || channelScreen.pageFailed
                     || channelScreen.blocked
                     || channelScreen.sourceUrl === ""
            GohuText {
                width: parent.width
                font.pixelSize: 18
                color: Colors.orange
                horizontalAlignment: Text.AlignHCenter
                text: channelScreen.noRenderer
                      ? "WEB RENDERER NOT AVAILABLE"
                      : channelScreen.blocked
                        ? "PLAYER REDIRECT BLOCKED"
                      : channelScreen.pageFailed
                        ? "PUBLISHER PAGE FAILED"
                        : "INVALID SOURCE URL"
            }
            SecondaryText {
                width: parent.width
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 12
                text: channelScreen.noRenderer
                      ? "QtWebEngine could not load in this Quickshell runtime."
                        + " Check the QtWebEngine QML import and host initialization"
                        + " in the QS logs. The channel catalog remains available."
                      : channelScreen.blocked
                        ? "The source redirected to a different website/player"
                          + " host. That navigation was intentionally blocked."
                          + " A provider-specific adapter may be required."
                      : channelScreen.pageFailed
                        ? (channelScreen.pageError
                           ? channelScreen.pageError
                           : "The publisher refused or could not load this page.")
                      : "This entry does not provide a valid HTTPS page."
            }
        }
    }

    Rectangle {
        id: footerStrip
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        height: 31
        color: Colors.dark

        QuietText {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            text: channelScreen.noRenderer
                  ? "ENGINE ERROR // NOT AN ARTICLE ERROR"
                  : channelScreen.blocked
                    ? "CROSS-HOST NAVIGATION BLOCKED"
                  : channelScreen.pageFailed
                    ? "PAGE LOAD FAILED // NO VIDEO VERIFIED"
                  : channelScreen.loadingRenderer
                    ? "LOADING INTERNAL WEB ENGINE"
                  : "IN-STATION WEB VIEW // VIDEO PLAYBACK NOT VERIFIED"
        }
    }

    onMutedChanged: {
        if (channelLoader.item)
            channelLoader.item.audioAllowed = !muted;
    }
}
