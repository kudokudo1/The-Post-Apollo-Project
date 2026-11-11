import QtQuick
import QtMultimedia
import qs.services.sounds

// Bounded built-in sounds only. No user-controlled filesystem path enters
// this audio component. Optional media backend cannot disable scheduling.
Item {
    id: audio
    property string soundId: "chime"
    property real outputVolume: 0.6
    property bool requested: false
    readonly property bool customTone: /^user-[0-9a-f]{64}$/.test(soundId)
    readonly property string importedToneUrl:
        customTone ? SoundLibraryService.sourceFor(soundId) : ""
    readonly property bool usingFallback: customTone && importedToneUrl === ""
    signal failed(string message)
    signal playing()
    signal stopped()

    SoundEffect {
        id: effect
        // Source comes ONLY from the sound library's validated catalog or
        // these three package-owned WAV files; never from an alarm text field.
        source: audio.customTone && !audio.usingFallback
            ? audio.importedToneUrl
            : audio.soundId === "soft"
            ? Qt.resolvedUrl("../../assets/sounds/clock-alarm-soft.wav")
            : audio.soundId === "urgent"
            ? Qt.resolvedUrl("../../assets/sounds/clock-alarm-urgent.wav")
            : Qt.resolvedUrl("../../assets/sounds/clock-alarm-chime.wav")
        loops: SoundEffect.Infinite
        volume: audio.outputVolume
        onStatusChanged: {
            if (status === SoundEffect.Ready && audio.requested)
                effect.play();
            else if (status === SoundEffect.Error) {
                if (audio.customTone && !audio.usingFallback) {
                    // Fail audibly rather than dropping a live alarm when
                    // a previously validated file becomes unreadable.
                    audio.failed("CUSTOM TONE ERROR // CHIME FALLBACK");
                    audio.soundId = "chime";
                } else
                    audio.failed("AUDIO FORMAT OR OUTPUT UNAVAILABLE");
            }
        }
        onPlayingChanged: {
            if (playing)
                audio.playing();
            else
                audio.stopped();
        }
    }

    function start() {
        requested = true;
        if (usingFallback)
            failed("CUSTOM TONE MISSING // CHIME FALLBACK");
        if (effect.status === SoundEffect.Ready)
            effect.play();
    }
    function stop() {
        requested = false;
        effect.stop();
    }
}
