import QtQuick
import QtQuick.Window
import Quickshell
import "widgets/weather" as Weather

// C36 // Disposable decoder test using a generated LOCAL MP4.
// No solar URL, machine state, audio routing, network or desktop activation.
ShellRoot {
    id: root
    property int ticks: 0
    property int phase: 0
    property bool done: false
    function fail(message) {
        if (done) return;
        done = true;
        console.error("C36_NATIVE_FAIL // " + message);
        Qt.quit();
    }
    Window {
        id: shell
        visible: true
        width: 480
        height: 280
        color: "black"
        Weather.StationCosmosSolarMovieDecoder {
            id: decoder
            objectName: "cosmos-c36-native-synthetic-decoder"
            anchors.fill: parent
            active: true
            mediaUrl: "C36_SAMPLE_VIDEO_URL"
        }
    }
    Timer {
        interval: 120
        running: !root.done
        repeat: true
        onTriggered: {
            root.ticks++;
            if (root.ticks > 180)
                return root.fail("VIDEO_DECODER_TIMEOUT // "+decoder.lastError);
            if (root.phase === 0) {
                if (decoder.mediaUrl === "" || decoder.width < 400)
                    return root.fail("VIDEO_SOURCE_MOUNT_MISSING");
                decoder.start();
                root.phase = 1;
                return;
            }
            if (decoder.lastError !== "")
                return root.fail("DECODER_ERROR // "+decoder.lastError);
            if (root.phase === 1) {
                if (!decoder.playing || !decoder.hasVideo
                    || decoder.durationMs < 1000
                    || decoder.positionMs < 200) return;
                if (!decoder.seekable || !decoder.seekFraction(0.5))
                    return root.fail("VIDEO_NOT_SEEKABLE");
                root.phase = 2;
                return;
            }
            if (root.phase === 2) {
                if (decoder.positionMs < 650) return;
                decoder.pause();
                root.phase = 3;
                return;
            }
            if (root.phase === 3) {
                if (decoder.playing) return;
                if (!decoder.hasVideo || decoder.progress < 0
                    || decoder.progress > 1)
                    return root.fail("VIDEO_TRACK_OR_PROGRESS_INVALID");
                root.done = true;
                console.log("C36_NATIVE_PASS // QTMULTIMEDIA_REAL_MP4_DECODING_VIDEO_TRACK_SEEK_PAUSE");
                decoder.active = false;
                Qt.quit();
            }
        }
    }
}
