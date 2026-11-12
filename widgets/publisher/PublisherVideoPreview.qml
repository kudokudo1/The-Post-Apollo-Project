import QtQuick
import QtMultimedia
import "../../components"

// Loaded ONLY when an explicitly selected, locally reverified video is shown.
// Playback is muted and requires the user's button press. No remote URLs.
Item {
    id: preview
    property url source: ""
    onVisibleChanged: if (!visible) player.stop()
    onSourceChanged: player.stop()

    MediaPlayer {
        id: player
        source: preview.source
        videoOutput: videoCanvas
        audioOutput: AudioOutput { muted: true }
    }
    VideoOutput {
        id: videoCanvas
        anchors.fill: parent
        anchors.bottomMargin: 37
        fillMode: VideoOutput.PreserveAspectFit
    }
    Row {
        width: parent.width
        height: 34
        spacing: 8
        anchors.bottom: parent.bottom
        ActionButton {
            width: (parent.width - parent.spacing) / 2
            height: 32
            label: player.playing ? "PAUSE PREVIEW" : "PLAY PREVIEW"
            accentColor: Colors.cyan
            onTriggered: {
                if (player.playing) player.pause();
                else player.play();
            }
        }
        ActionButton {
            width: (parent.width - parent.spacing) / 2
            height: 32
            label: "STOP"
            accentColor: Colors.orange
            onTriggered: player.stop()
        }
    }
}
