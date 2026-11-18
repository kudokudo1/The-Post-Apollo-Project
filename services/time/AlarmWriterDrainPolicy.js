.pragma library

// BG1-B2B15: pure preflight for an already-accepted FileView save drain.
// This NEVER validates native Clock authority or grants a writer release.
var ACTIVE = "ACTIVE";
var DRAINING = "DRAINING";
var QUIESCING = "QUIESCING";
var FAILED = "FAILED";

function canStart(snapshot) {
    if (!snapshot || typeof snapshot !== "object" || Array.isArray(snapshot))
        return false;
    // An accepted pending write may finish after intake is frozen.
    if (snapshot.storageState !== "ready" && snapshot.storageState !== "saving")
        return false;
    if (typeof snapshot.pendingWrite !== "boolean"
            || typeof snapshot.queuedWrite !== "boolean"
            || typeof snapshot.migrationRequested !== "boolean"
            || typeof snapshot.previewing !== "boolean"
            || !Number.isSafeInteger(snapshot.ringingCount)
            || snapshot.ringingCount !== 0
            || snapshot.previewing
            || snapshot.audioState !== "IDLE"
            || typeof snapshot.notificationOutcome !== "string"
            || snapshot.notificationOutcome.length === 0
            || snapshot.notificationOutcome === "DELIVERY PENDING")
        return false;
    if (snapshot.storageState === "saving" && !snapshot.pendingWrite)
        return false;
    if (snapshot.queuedWrite && !snapshot.pendingWrite)
        return false;
    if (snapshot.migrationRequested && !snapshot.pendingWrite)
        return false;
    return true;
}

function canFinish(snapshot, acceptedGeneration, observedGeneration) {
    return Number.isSafeInteger(acceptedGeneration)
        && acceptedGeneration >= 0
        && Number.isSafeInteger(observedGeneration)
        && observedGeneration === acceptedGeneration
        && snapshot && !Array.isArray(snapshot)
        && snapshot.storageState === "ready"
        && snapshot.pendingWrite === false
        && snapshot.queuedWrite === false
        && snapshot.migrationRequested === false
        && snapshot.ringingCount === 0
        && snapshot.previewing === false
        && snapshot.audioState === "IDLE"
        && typeof snapshot.notificationOutcome === "string"
        && snapshot.notificationOutcome.length > 0
        && snapshot.notificationOutcome !== "DELIVERY PENDING";
}

function queuedFlushAllowed(phase, draining, acceptingNewEdits, fromSavedCallback) {
    return phase === ACTIVE && draining === true
        && acceptingNewEdits === false && fromSavedCallback === true;
}

function status(phase, draining, snapshot, acceptedGeneration,
                observedGeneration) {
    const complete = phase === QUIESCING && !draining
        && canFinish(snapshot, acceptedGeneration, observedGeneration);
    return {
        phase: phase,
        localQueueDrained: complete,
        acceptedGeneration: acceptedGeneration,
        observedSaveGeneration: observedGeneration,
        // onSaved is a callback, NOT fsync or durable source-file evidence.
        finalRevisionDurablyWitnessed: false,
        writerStopped: false,
        releaseAcknowledged: false,
        canTransferOwnership: false,
        canRing: false
    };
}
