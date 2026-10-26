import QtQuick
import Quickshell
import "ApolloHubAudioStreamsPolicy.js" as StreamPolicy

// P3-B host adapter to the ONE Team 6 ApplicationAudioService instance.
// It cannot invent app identities or mutate PipeWire independently.
// Direct stream actions are checked against a new owner observation.
// Future APP/WINDOW/TAB policy integration requires Team 7 semantic identity.
Scope {
    id: streamGate
    required property var audioOwner
    property var pending: null
    property string feedback: "REFRESH TO OBSERVE STREAMS"
    readonly property bool busy: pending !== null
    readonly property var snapshot: StreamPolicy.snapshot(
        audioOwner ? audioOwner.sinkInputs : null,
        audioOwner ? audioOwner.observationGeneration : 0,
        audioOwner ? audioOwner.loading : false,
        audioOwner ? audioOwner.errorText : "")

    function refresh() {
        if (busy || !audioOwner) {
            feedback = "STREAM REFRESH UNAVAILABLE";
            return false;
        }
        feedback = "REFRESH REQUESTED // AWAIT OBSERVATION";
        audioOwner.refresh();
        return true;
    }

    function request(index, fingerprint, generation, action, value) {
        if (busy || !audioOwner) {
            feedback = "STREAM ACTION BUSY OR OWNER UNAVAILABLE";
            return false;
        }
        if (action !== "mute" && action !== "volume") {
            feedback = "UNSUPPORTED STREAM ACTION";
            return false;
        }
        if (action === "mute" && typeof value !== "boolean") {
            feedback = "INVALID MUTE REQUEST";
            return false;
        }
        if (action === "volume" && (!Number.isInteger(value)
                || value < 0 || value > 100)) {
            feedback = "INVALID STREAM VOLUME // 0–100%";
            return false;
        }
        if (!Number.isSafeInteger(generation) || generation < 1
                || audioOwner.observationGeneration !== generation
                || audioOwner.loading || audioOwner.errorText) {
            feedback = "STALE STREAM OBSERVATION // REFRESH";
            return false;
        }
        if (!StreamPolicy.findExact(audioOwner.sinkInputs,index,fingerprint)) {
            feedback = "STREAM IDENTITY CHANGED // REFUSED";
            return false;
        }

        pending = {index:index,identity:fingerprint,generation:generation,
                   action:action,value:value};
        feedback = "REVERIFYING LIVE STREAM // NO ACTION YET";
        requestTimeout.restart();
        audioOwner.refresh();
        return true;
    }

    function observed(inputs) {
        const req = pending;
        if (!req || !audioOwner) return;
        if (audioOwner.observationGeneration <= req.generation) return;
        pending = null;
        requestTimeout.stop();

        const current = StreamPolicy.findExact(inputs,req.index,req.identity);
        if (!current) {
            feedback = "STREAM CHANGED OR ENDED // NO ACTION";
            return;
        }
        // Only the existing Team 6 owner performs audio mutations.
        const accepted = req.action === "mute"
            ? audioOwner.setSinkInputMute([req.index],req.value)
            : audioOwner.setSinkInputVolumes([req.index],req.value);
        feedback = accepted
            ? "STREAM " + req.action.toUpperCase()
              + " REQUEST SENT // ACTUAL RESULT UNVERIFIED"
            : "STREAM ACTION REJECTED BY AUDIO OWNER";
    }

    Connections {
        target: streamGate.audioOwner
        function onRefreshed(inputs) {
            streamGate.observed(inputs);
        }
    }
    Timer {
        id: requestTimeout
        interval: 4000
        repeat: false
        onTriggered: {
            if (streamGate.pending) {
                streamGate.pending = null;
                streamGate.feedback = "STREAM RECHECK TIMED OUT // NO ACTION";
            }
        }
    }
}
