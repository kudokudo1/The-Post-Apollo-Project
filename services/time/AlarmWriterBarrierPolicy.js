.pragma library

// BG1-B2B6: pure write-path barrier. It is connected to the mounted Clock
// in ACTIVE mode only. A local QML caller cannot certify signed authority,
// revoke the old process, or transfer the saved alarm file.
var ACTIVE = "ACTIVE";
var QUIESCING = "QUIESCING";
var RELEASED = "RELEASED";

function allowDiskMutation(phase) {
    return phase === ACTIVE;
}
function allowSchedulerTick(phase) {
    return phase === ACTIVE;
}
function allowRingAnnouncement(phase) {
    return phase === ACTIVE;
}
function allowAudioStart(phase) {
    return phase === ACTIVE;
}
function allowLocalStop(phase) {
    // STOP remains a safety action even when persistence cannot be reached.
    // The caller must report that its local audio silence was NOT saved.
    return phase === ACTIVE || phase === QUIESCING || phase === RELEASED;
}

function canBeginQuiescing(snapshot) {
    // Readiness only; never creates a transfer credential.
    if (!snapshot || typeof snapshot !== "object"
            || Array.isArray(snapshot)
            || snapshot.storageState !== "ready"
            || snapshot.pendingWrite !== false
            || snapshot.queuedWrite !== false
            || snapshot.migrationRequested !== false
            || snapshot.ringingCount !== 0
            || snapshot.previewing !== false
            || snapshot.audioState !== "IDLE"
            || typeof snapshot.notificationOutcome !== "string"
            || snapshot.notificationOutcome.length === 0
            || snapshot.notificationOutcome === "DELIVERY PENDING")
        return false;
    return true;
}

function requestPause(snapshot) {
    // There is NO authenticated installed native authority yet, nor any
    // release receipt bound to the last saved file revision and old-writer
    // process. Never infer authority from caller-supplied flags or state.
    return {
        ok:false,
        reason:canBeginQuiescing(snapshot)
              ? "AUTHENTICATED_WRITER_PAUSE_UNAVAILABLE"
              : "LOCAL_WRITER_NOT_DRAINED",
        phase:ACTIVE,
        writerStopped:false,
        releaseAcknowledged:false,
        ownsAlarmFile:false,
        canTransferOwnership:false,
        canRing:false
    };
}
