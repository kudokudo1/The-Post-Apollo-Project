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
    // C37 // Verify the real MP4 accepts seeking in both playing and
    // explicitly paused states. Zoom/pan must not resize or replace it.
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
                if (!decoder.playIntent)
                    return root.fail("PLAYING_SEEK_LOST_AUTO_RESUME_INTENT");
                root.phase = 2;
                return;
            }
            if (root.phase === 2) {
                if (decoder.positionMs < 650) return;
                decoder.pause();
                if (decoder.playIntent) return root.fail("PAUSE_INTENT_NOT_RECORDED");
                decoder.setZoom(2);
                decoder.panBy(30,-20);
                if (decoder.zoom !== 2 || decoder.panX === 0)
                    return root.fail("ZOOM_AND_PAN_NOT_APPLIED");
                decoder.zoomAt(1.2,50,50);
                decoder.resetView();
                if (decoder.zoom !== 1 || decoder.panX !== 0 || decoder.panY !== 0)
                    return root.fail("FIT_DID_NOT_RESET");
                if (!decoder.seekFraction(0.25))
                    return root.fail("PAUSED_SEEK_REJECTED");
                if (decoder.playIntent)
                    return root.fail("PAUSED_SEEK_AUTOPLAYED_UNEXPECTEDLY");
                root.phase = 3;
                return;
            }
            if (root.phase === 3) {
                if (decoder.playing) return;
                if (Math.abs(decoder.positionMs-decoder.durationMs*0.25)>400)
                    return;
                if (!decoder.hasVideo || decoder.progress < 0
                    || decoder.progress > 1)
                    return root.fail("PAUSED_FRAME_OR_PROGRESS_INVALID");
                decoder.start();
                if (!decoder.seekRelative(200))
                    return root.fail("RELATIVE_SEEK_REJECTED");
                if (!decoder.playIntent)
                    return root.fail("RESUME_SEEK_LOST_PLAY_INTENT");
                root.phase = 4;
                return;
            }
            if (root.phase === 4) {
                if (!decoder.playing) return;
                root.done = true;
                console.log("C36_NATIVE_PASS // QTMULTIMEDIA_REAL_MP4_DECODING_VIDEO_TRACK_SEEK_PAUSE");
                console.log("C37_NATIVE_PASS // PAUSED_SCRUB_PLAYING_SEEK_ZOOM_PAN_FIT");
                decoder.active = false;
                Qt.quit();
            }
        }
    }
}
