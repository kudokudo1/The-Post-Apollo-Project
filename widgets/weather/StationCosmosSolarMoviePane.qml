import QtQuick
import "../../components"
import "StationCosmosSolarMoviePolicy.js" as SolarMovies

// C36 // One bounded native solar-media player. Decoder loads only after
// explicit PLAY, so a host missing QtMultimedia retains every other screen.
Rectangle {
    id: movie
    objectName: "cosmos-c36-solar-movie-pane"
    color: Colors.black
    border.width: 1
    border.color: Colors.magenta
    clip: true

    property bool expanded: false
    property bool playbackRequested: false
    property string channelId: "171"
    readonly property string mediaUrl: SolarMovies.url(channelId)
    readonly property bool decoderReady: decoderLoader.status === Loader.Ready
        && decoderLoader.item !== null
    readonly property bool decoderFailed: playbackRequested
        && decoderLoader.status === Loader.Error
    readonly property bool playbackRunning: decoderReady && decoderLoader.item.playing
    readonly property real playFraction: decoderReady ? decoderLoader.item.progress : 0
    readonly property string playError: decoderFailed
        ? "QTMULTIMEDIA UNAVAILABLE // INSTALLATION NOT VERIFIED"
        : decoderReady ? decoderLoader.item.lastError : ""

    signal closeRequested()
    signal expandRequested()

    function chooseChannel(id) {
        if (!SolarMovies.byId(id)) return;
        channelId = id;
        if (decoderReady) {
            decoderLoader.item.pause();
            decoderLoader.item.mediaUrl = mediaUrl;
            decoderLoader.item.start();
        }
    }
    function togglePlayback() {
        if (!playbackRequested) {
            playbackRequested = true;
            return;
        }
        if (decoderReady) {
            decoderLoader.item.toggle();
        } else if (decoderFailed) {
            playbackRequested = false;
            playbackRequested = true;
        }
    }
    function seek(fraction) {
        return decoderReady && decoderLoader.item.seekFraction(fraction);
    }
    onVisibleChanged: {
        if (!visible) playbackRequested = false;
    }

    Column {
        id: chrome
        anchors.fill: parent
        anchors.margins: 4
        spacing: 3

        Row {
            id: header
            width: parent.width
            height: 20
            spacing: 4
            ActionButton {
                objectName: "cosmos-c36-solar-movie-close"
                width: 43
                height: parent.height
                label: "BACK"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.magenta
                onClicked: movie.closeRequested()
            }
            GohuText {
                width: Math.max(1,header.width-94)
                height: parent.height
                text: "SDO // SOLAR MOVIE"
                color: Colors.white
                font.pixelSize: 9
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            ActionButton {
                objectName: "cosmos-c36-solar-movie-expand"
                width: 43
                height: parent.height
                label: movie.expanded ? "REST" : "FULL"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.yellow
                onClicked: movie.expandRequested()
            }
        }

        Row {
            id: channels
            objectName: "cosmos-c36-sdo-channel-controls"
            width: parent.width
            height: 19
            spacing: 3
            Repeater {
                model: SolarMovies.CHANNELS
                delegate: ActionButton {
                    required property var modelData
                    width: Math.max(1,(channels.width-6)/3)
                    height: channels.height
                    label: modelData.label
                    labelPixelSize: 8
                    contentPadding: 0
                    selected: movie.channelId === modelData.id
                    accentColor: Colors.cyan
                    onClicked: movie.chooseChannel(modelData.id)
                }
            }
        }

        Rectangle {
            id: playbackBay
            objectName: "cosmos-c36-bounded-video-bay"
            width: parent.width
            height: Math.max(1,chrome.height-header.height
                -channels.height-playControls.height-scrubBay.height
                -sourceNote.height-5*chrome.spacing)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Loader {
                id: decoderLoader
                objectName: "cosmos-c36-lazy-decoder-loader"
                anchors.fill: parent
                active: movie.visible && movie.playbackRequested
                // This path isolates the QtMultimedia import from all
                // ordinary Weather components and offline native CI.
                source: "StationCosmosSolarMovieDecoder.qml"
                onLoaded: {
                    if (!item) return;
                    item.active = true;
                    item.mediaUrl = movie.mediaUrl;
                    item.start();
                }
            }

            QuietText {
                anchors.centerIn: parent
                width: Math.max(1,parent.width-18)
                visible: !movie.decoderReady || movie.playError !== ""
                color: movie.decoderFailed || movie.playError !== ""
                    ? Colors.orange : Colors.cyan
                font.pixelSize: 9
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
                text: movie.playError !== "" ? movie.playError
                    : movie.playbackRequested
                    ? "LOADING SDO NATIVE MOVIE"
                    : "PRESS PLAY // NASA SDO TIME-LAPSE"
            }
        }

        Row {
            id: playControls
            objectName: "cosmos-c36-solar-media-controls"
            width: parent.width
            height: 19
            spacing: 4
            ActionButton {
                objectName: "cosmos-c36-solar-play-pause"
                width: Math.max(1,(playControls.width-4)*0.42)
                height: parent.height
                label: movie.playbackRunning ? "PAUSE" : "PLAY"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.orange
                onClicked: movie.togglePlayback()
            }
            QuietText {
                width: Math.max(1,(playControls.width-4)*0.58)
                height: parent.height
                text: movie.decoderReady
                    ? "MP4 // "+(movie.decoderLoaderStatusLabel)
                    : "NATIVE DECODER // ON DEMAND"
                color: Colors.cyan
                font.pixelSize: 8
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: scrubBay
            objectName: "cosmos-c36-sdo-seek-track"
            width: parent.width
            height: 10
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            Rectangle {
                objectName: "cosmos-c36-sdo-seek-progress"
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width*movie.playFraction
                color: Colors.orange
            }
            MouseArea {
                anchors.fill: parent
                cursorShape: movie.decoderReady
                    ? Qt.PointingHandCursor : Qt.ArrowCursor
                enabled: movie.decoderReady
                onClicked: function(mouse) {
                    movie.seek(mouse.x/Math.max(1,width));
                }
            }
        }

        QuietText {
            id: sourceNote
            width: parent.width
            height: 13
            text: "NASA SDO AIA // PUBLISHED 48H MOVIE, NOT LIVE SUVI"
            color: Colors.yellow
            font.pixelSize: 8
            elide: Text.ElideRight
        }
    }

    // Human-readable status without relying on MediaPlayer enum coercion.
    readonly property string decoderLoaderStatusLabel: movie.playbackRunning
        ? "PLAYING" : movie.decoderReady ? "PAUSED/READY" : "OFFLINE"
}
