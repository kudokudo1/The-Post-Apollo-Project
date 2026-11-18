.pragma library

// BG1-B2B18: QML-side, unauthenticated final-revision candidate parser.
// This does not verify a signed native sender, kernel peer, release floor,
// Quickshell process or disk sync. Never calls FileView, pause or takeover.
var ACTION = "OBSERVE_FINAL_CANDIDATE";
var MAX_FRAME = 512;
var HEX64 = /^[0-9a-f]{64}$/;

function status(reason, syntax, generation) {
    return {
        ok: false,
        reason: reason,
        frameSyntaxObserved: syntax === true,
        localSaveGenerationMatched: generation === true,
        nativeSenderAuthenticated: false,
        quickshellProcessBound: false,
        durableRevisionWitnessed: false,
        writerStopped: false,
        releaseAcknowledged: false,
        oldWriterRestartPrevented: false,
        canTransferOwnership: false,
        canRing: false,
        canNotify: false
    };
}

function inactiveStatus() {
    return status("NATIVE_QML_BRIDGE_NOT_INSTALLED", false, false);
}

function inspectCandidate(raw, local) {
    // SplitParser strips delimiters; newline, NUL or an oversized frame
    // inside a delivered message must still be rejected without a log.
    if (typeof raw !== "string" || raw.length < 1
            || raw.length > MAX_FRAME || /[\r\n\0]/.test(raw))
        return status("NATIVE_QML_FRAME_REFUSED", false, false);
    let parsed;
    try {
        parsed = JSON.parse(raw);
    } catch (_) {
        return status("NATIVE_QML_FRAME_REFUSED", false, false);
    }
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object"
            || parsed.action !== ACTION || parsed.v !== 1
            || !Number.isSafeInteger(parsed.generation)
            || parsed.generation <= 0
            || typeof parsed.nonce !== "string"
            || !HEX64.test(parsed.nonce)
            || typeof parsed.sourceDigest !== "string"
            || !HEX64.test(parsed.sourceDigest))
        return status("NATIVE_QML_FRAME_REFUSED", false, false);
    // Exact canonical serialization rejects duplicate keys, alternate
    // whitespace, extra "trusted" fields, and numeric ambiguity.
    const canonical = '{"action":"OBSERVE_FINAL_CANDIDATE","generation":'
        + parsed.generation + ',"nonce":"' + parsed.nonce
        + '","sourceDigest":"' + parsed.sourceDigest + '","v":1}';
    if (raw !== canonical)
        return status("NATIVE_QML_FRAME_REFUSED", false, false);
    // Observe a matching local generation, never a trusted disk revision.
    const matched = local && typeof local === "object"
        && !Array.isArray(local)
        && local.phase === "QUIESCING"
        && local.localQueueDrained === true
        && Number.isSafeInteger(local.acceptedGeneration)
        && local.acceptedGeneration === parsed.generation
        && local.observedSaveGeneration === parsed.generation;
    return status(matched
        ? "LOCAL_SAVE_GENERATION_CANDIDATE_ONLY"
        : "LOCAL_FINAL_SAVE_NOT_WITNESSED", true, matched);
}
