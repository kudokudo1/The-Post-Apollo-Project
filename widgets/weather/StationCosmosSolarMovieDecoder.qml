import QtQuick
import QtMultimedia
import "StationCosmosSolarMoviePolicy.js" as SolarMovies

// C36 // Optional decoder. The parent loads this FILE by URL only on an
// explicit PLAY action. The rest of Quickshell never imports QtMultimedia.
// Keep one MediaPlayer and one VideoOutput within the current widget bay.
Item {
    id: decoder
    objectName: "cosmos-c36-qt-video-decoder"
    clip: true

    property string mediaUrl: ""
    property bool active: true
    property string lastError: ""
    readonly property bool playing: player.playbackState === MediaPlayer.PlayingState
    readonly property bool seekable: player.seekable
    readonly property bool hasVideo: player.hasVideo
    readonly property int positionMs: player.position
    readonly property int durationMs: player.duration
    readonly property real progress: SolarMovies.positionFraction(positionMs,durationMs)

    function start() {
        if (!active || mediaUrl === "") return;
        lastError = "";
        player.play();
    }
    function pause() { player.pause(); }
    function toggle() {
        if (playing) pause();
        else start();
    }
    function seekFraction(fraction) {
        if (!seekable) return false;
        const ms = SolarMovies.seekPosition(fraction,durationMs);
        if (ms === null) return false;
        player.position = ms;
        return true;
    }
    onActiveChanged: {
        if (!active) player.stop();
    }

    VideoOutput {
        id: videoOutput
        objectName: "cosmos-c36-native-video-output"
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectFit
    }
    MediaPlayer {
        id: player
        objectName: "cosmos-c36-native-media-player"
        videoOutput: videoOutput
        source: decoder.active && decoder.mediaUrl !== "" ? decoder.mediaUrl : ""
        loops: MediaPlayer.Infinite
        // Solar recordings have no requested audio. Never route sound
        // into the shared Post-Apollo audio system by accident.
        audioOutput: AudioOutput { muted: true }
        onErrorOccurred: function(error, description) {
            decoder.lastError = description && description !== ""
                ? description : "MEDIA DECODE OR NETWORK ERROR";
        }
    }
    Component.onDestruction: player.stop()
}
