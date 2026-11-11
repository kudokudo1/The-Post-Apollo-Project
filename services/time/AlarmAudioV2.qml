import QtQuick
import QtMultimedia

// Bounded built-in sounds only. No user-controlled filesystem path enters
// this audio component. Optional media backend cannot disable scheduling.
Item {
    id: audio
    property string soundId: "chime"
    property real outputVolume: 0.6
    property bool requested: false
    signal failed(string message)
    signal playing()

    SoundEffect {
        id: effect
        source: audio.soundId === "soft"
            ? Qt.resolvedUrl("../../assets/sounds/clock-alarm-soft.wav")
            : audio.soundId === "urgent"
            ? Qt.resolvedUrl("../../assets/sounds/clock-alarm-urgent.wav")
            : Qt.resolvedUrl("../../assets/sounds/clock-alarm-chime.wav")
        loops: SoundEffect.Infinite
        volume: audio.outputVolume
        onStatusChanged: {
            if (status === SoundEffect.Ready && audio.requested)
                effect.play();
            else if (status === SoundEffect.Error)
                audio.failed("AUDIO FORMAT OR OUTPUT UNAVAILABLE");
        }
        onPlayingChanged: {
            if (playing)
                audio.playing();
        }
    }

    function start() {
        requested = true;
        if (effect.status === SoundEffect.Ready)
            effect.play();
    }
    function stop() {
        requested = false;
        effect.stop();
    }
}
