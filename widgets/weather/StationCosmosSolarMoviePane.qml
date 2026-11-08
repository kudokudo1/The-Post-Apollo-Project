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
    readonly property bool playbackRunning: decoderReady
        && decoderLoader.item.playing && !decoderLoader.item.stalled
    readonly property bool playbackIntent: decoderReady && decoderLoader.item.playIntent
    readonly property real videoZoom: decoderReady ? decoderLoader.item.zoom : 1
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
    function stepTime(deltaMs) {
        return decoderReady && decoderLoader.item.seekRelative(deltaMs);
    }
    function zoomBy(delta) {
        if (decoderReady) decoderLoader.item.setZoom(videoZoom+delta);
    }
    function fitVideo() {
        if (decoderReady) decoderLoader.item.resetView();
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

        Row {
            id: zoomControls
            objectName: "cosmos-c37-solar-movie-zoom-controls"
            width: parent.width
            height: 19
            spacing: 3
            ActionButton {
                objectName: "cosmos-c37-video-zoom-out"
                width: 40
                height: parent.height
                label: "ZOOM -"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: movie.zoomBy(-0.25)
            }
            ActionButton {
                objectName: "cosmos-c37-video-zoom-in"
                width: 40
                height: parent.height
                label: "ZOOM +"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: movie.zoomBy(0.25)
            }
            ActionButton {
                objectName: "cosmos-c37-video-fit"
                width: 35
                height: parent.height
                label: "FIT"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.yellow
                onClicked: movie.fitVideo()
            }
            QuietText {
                width: Math.max(1,zoomControls.width-124)
                height: parent.height
                text: "VIDEO " + Math.round(movie.videoZoom*100) + "% // WHEEL + DRAG"
                color: Colors.cyan
                font.pixelSize: 8
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }

        Rectangle {
            id: playbackBay
            objectName: "cosmos-c36-bounded-video-bay"
            width: parent.width
            height: Math.max(1,chrome.height-header.height
                -channels.height-zoomControls.height-playControls.height
                -scrubBay.height-sourceNote.height-6*chrome.spacing)
            color: Colors.dark
            border.width: 1
            border.color: Colors.cyan
            clip: true

            Loader {
                id: decoderLoader
                objectName: "cosmos-c36-lazy-decoder-loader"
                anchors.fill: parent
                // Inset the native video texture from the playback frame;
                // the existing cyan/magenta instrument dividers remain visible.
                anchors.margins: 4
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
                objectName: "cosmos-c37-back-one-second"
                width: Math.max(28,(playControls.width-12)*0.17)
                height: parent.height
                label: "-1s"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: movie.stepTime(-1000)
            }
            ActionButton {
                objectName: "cosmos-c36-solar-play-pause"
                width: Math.max(40,(playControls.width-12)*0.27)
                height: parent.height
                label: movie.playbackRunning ? "PAUSE" : "PLAY"
                labelPixelSize: 9
                contentPadding: 0
                accentColor: Colors.orange
                onClicked: movie.togglePlayback()
            }
            ActionButton {
                objectName: "cosmos-c37-forward-one-second"
                width: Math.max(28,(playControls.width-12)*0.17)
                height: parent.height
                label: "+1s"
                labelPixelSize: 8
                contentPadding: 0
                accentColor: Colors.cyan
                onClicked: movie.stepTime(1000)
            }
            QuietText {
                width: Math.max(1,playControls.width-12
                    -Math.max(28,(playControls.width-12)*0.17)*2
                    -Math.max(40,(playControls.width-12)*0.27))
                height: parent.height
                text: movie.decoderReady
                    ? "MP4 // "+movie.decoderLoaderStatusLabel
                    : "NATIVE // ON DEMAND"
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
                // Small wheel steps permit paused frame inspection without
                // turning the time-lapse into a separate image gallery.
                onWheel: function(wheel) {
                    if (wheel.angleDelta.y===0) return;
                    movie.stepTime(wheel.angleDelta.y>0 ? 200 : -200);
                    wheel.accepted=true;
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
    readonly property string decoderLoaderStatusLabel: !movie.decoderReady
        ? "OFFLINE"
        : movie.decoderLoader.item.stalled ? "BUFFERING"
        : movie.playbackRunning ? "PLAYING"
        : movie.playbackIntent ? "RESUMING"
        : "PAUSED/READY"
}
