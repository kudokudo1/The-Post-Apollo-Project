import QtQuick
import QtMultimedia
import "StationCosmosSolarMoviePolicy.js" as SolarMovies
import "StationSolarImageViewportPolicy.js" as ImageViewportPolicy

// C37 // One optional, lazily loaded native decoder. Zoom/pan changes only
// the internal clipped picture, never the panel or video source. The user's
// PLAY/PAUSE intent is separate from Qt's transient seek/buffering states.
Item {
    id: decoder
    objectName: "cosmos-c36-qt-video-decoder"
    clip: true

    property string mediaUrl: ""
    property bool active: true
    property string lastError: ""
    property bool playIntent: false
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    readonly property bool playing: player.playbackState === MediaPlayer.PlayingState
    readonly property bool stalled: player.mediaStatus === MediaPlayer.StalledMedia
    readonly property bool seekable: player.seekable
    readonly property bool hasVideo: player.hasVideo
    readonly property int positionMs: player.position
    readonly property int durationMs: player.duration
    readonly property real progress: SolarMovies.positionFraction(positionMs,durationMs)

    function clampPan() {
        const bounded = ImageViewportPolicy.clampPan(
            zoom,panX,panY,videoViewport.width,videoViewport.height,
            videoViewport.width,videoViewport.height);
        panX=bounded.x;
        panY=bounded.y;
    }
    function setZoom(nextZoom) {
        zoom=ImageViewportPolicy.zoom(nextZoom);
        clampPan();
    }
    function zoomAt(factor,x,y) {
        const next=ImageViewportPolicy.zoomAt(
            zoom,factor,panX,panY,x,y,videoViewport.width,videoViewport.height,
            videoViewport.width,videoViewport.height);
        zoom=next.zoom;
        panX=next.x;
        panY=next.y;
    }
    function panBy(dx,dy) {
        panX+=dx;
        panY+=dy;
        clampPan();
    }
    function resetView() {
        zoom=1;
        panX=0;
        panY=0;
    }
    function start() {
        if (!active || mediaUrl === "") return;
        lastError="";
        playIntent=true;
        player.play();
    }
    function pause() {
        playIntent=false;
        seekResume.stop();
        player.pause();
    }
    function toggle() {
        // Treat a decoder that is stalled or unexpectedly stopped as PLAY,
        // even if the previous user intention was to keep playing.
        if (playIntent && playing && !stalled) pause();
        else start();
    }
    function seekFraction(fraction) {
        if (!seekable) return false;
        const ms=SolarMovies.seekPosition(fraction,durationMs);
        if (ms === null) return false;
        const resume=playIntent;
        player.position=ms;
        if (resume) {
            // Some native FFmpeg backends leave a seek at a non-playing
            // frame. Resume now and once the seek has settled.
            player.play();
            seekResume.restart();
        } else {
            // A deliberately paused viewer can scrub to inspect frames.
            seekResume.stop();
            player.pause();
        }
        return true;
    }
    function seekRelative(deltaMs) {
        if (!seekable || durationMs<=0 || !isFinite(Number(deltaMs)))
            return false;
        return seekFraction((positionMs+Number(deltaMs))/durationMs);
    }
    onMediaUrlChanged: {
        seekResume.stop();
        playIntent=false;
        resetView();
    }
    onActiveChanged: {
        if (!active) {
            seekResume.stop();
            playIntent=false;
            player.stop();
        }
    }

    Timer {
        id: seekResume
        objectName: "cosmos-c37-seek-resume"
        interval: 180
        repeat: false
        onTriggered: {
            if (decoder.active && decoder.playIntent && decoder.mediaUrl !== "")
                player.play();
        }
    }

    Item {
        id: videoViewport
        objectName: "cosmos-c37-clipped-video-viewport"
        anchors.fill: parent
        clip: true
        onWidthChanged: decoder.clampPan()
        onHeightChanged: decoder.clampPan()

        VideoOutput {
            id: videoOutput
            objectName: "cosmos-c36-native-video-output"
            width: Math.max(1,videoViewport.width*decoder.zoom)
            height: Math.max(1,videoViewport.height*decoder.zoom)
            x: (videoViewport.width-width)/2+decoder.panX
            y: (videoViewport.height-height)/2+decoder.panY
            fillMode: VideoOutput.PreserveAspectFit
        }

        MouseArea {
            id: videoGesture
            objectName: "cosmos-c37-video-zoom-pan-gesture"
            anchors.fill: parent
            enabled: decoder.hasVideo
            cursorShape: decoder.zoom>1 ? Qt.OpenHandCursor : Qt.ArrowCursor
            property real lastX: 0
            property real lastY: 0
            onPressed: function(mouse) {
                lastX=mouse.x;
                lastY=mouse.y;
            }
            onPositionChanged: function(mouse) {
                if (!pressed || decoder.zoom<=1) return;
                decoder.panBy(mouse.x-lastX,mouse.y-lastY);
                lastX=mouse.x;
                lastY=mouse.y;
            }
            onWheel: function(wheel) {
                if (wheel.angleDelta.y===0) return;
                decoder.zoomAt(wheel.angleDelta.y>0 ? 1.2 : 1/1.2,
                               wheel.x,wheel.y);
                wheel.accepted=true;
            }
            onDoubleClicked: decoder.resetView()
        }
    }

    MediaPlayer {
        id: player
        objectName: "cosmos-c36-native-media-player"
        videoOutput: videoOutput
        source: decoder.active && decoder.mediaUrl !== "" ? decoder.mediaUrl : ""
        loops: MediaPlayer.Infinite
        // No audio routing changes to shared Post-Apollo devices.
        audioOutput: AudioOutput { muted: true }
        onErrorOccurred: function(error, description) {
            decoder.lastError = description && description !== ""
                ? description : "MEDIA DECODE OR NETWORK ERROR";
            decoder.playIntent=false;
            seekResume.stop();
        }
    }
    Component.onDestruction: player.stop()
}
