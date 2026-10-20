import QtQuick
import Quickshell
import qs.services.notifications
import "AudioOutputHealthPolicy.js" as OutputPolicy

// Uses existing Volume bar PipeWire.defaultAudioSink readiness. Timer below
// only confirms a *change* after 4 seconds; it never polls audio devices.
// No mute/volume changes, WirePlumber operations, MPD or Hi-Fi dependencies.
Scope {
    id: producer
    required property bool outputReady
    property bool bootstrapped: false
    property var state: OutputPolicy.initial()

    function observe() {
        const at = Date.now();
        const decision = OutputPolicy.transition(
            producer.state, producer.outputReady, at);
        producer.state = decision.state;
        if (producer.state.candidate !== "")
            confirmChange.restart();
        else
            confirmChange.stop();

        if (!decision.event || !NotificationsService.historyReady)
            return;
        const restored = decision.event === "restored";
        NotificationsService.pushRich({
            "source": "AUDIO",
            "sourceId": "audio-default-output-health",
            "category": "internal",
            "severity": restored ? "normal" : "warning",
            "title": restored ? "AUDIO // DEFAULT OUTPUT READY AGAIN"
                              : "AUDIO // DEFAULT OUTPUT NOT READY",
            "message": restored
                ? "The desktop default audio output reports ready again."
                : "The desktop default audio output has stayed not-ready."
                  + " An output switch or service restart may be responsible."
                  + " Review Volume and PipeWire diagnostics.",
            "tags": ["audio", "system", "default-output-health"],
            "context": {
                "eventType": restored ? "audio-default-output-restored"
                                      : "audio-default-output-unavailable",
                "origin": "apollo",
                "domain": "system",
                "observation": "default PipeWire audio sink readiness only",
                "observedAtUtc": new Date(at).toISOString()
            }
        });
    }

    onOutputReadyChanged: {
        if (producer.bootstrapped)
            producer.observe();
    }
    Timer {
        id: confirmChange
        interval: 4000
        repeat: false
        running: false
        onTriggered: producer.observe()
    }
    Component.onCompleted: {
        producer.bootstrapped = true;
        producer.observe();
    }
}
