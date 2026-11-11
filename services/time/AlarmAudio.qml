import QtQuick
import QtMultimedia

// Only instantiated for a ringing alarm or explicit sound preview.
// A missing QtMultimedia plugin cannot disable the alarm scheduler.
Item {
    id: alarmAudio

    property bool requested: false
    property real outputVolume: 0.6
    signal failed(string message)

    SoundEffect {
        id: chime
        source: Qt.resolvedUrl("../../assets/sounds/clock-alarm-chime.wav")
        volume: alarmAudio.outputVolume
        loops: SoundEffect.Infinite
        onStatusChanged: {
            if (status === SoundEffect.Ready && alarmAudio.requested)
                chime.play();
            else if (status === SoundEffect.Error)
                alarmAudio.failed("AUDIO FILE OR OUTPUT UNAVAILABLE");
        }
    }

    function start() {
        requested = true;
        if (chime.status === SoundEffect.Ready)
            chime.play();
    }

    function stop() {
        requested = false;
        chime.stop();
    }
}
