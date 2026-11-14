.pragma library

// Clock BG1-B2B4: passive local writer-drain inspection, not a release API.
// All results are status-only and contain no alarm metadata or file paths.
// The current mounted AlarmManagerService still owns all actual V2 writes.

function status(snapshot) {
    if (!snapshot || typeof snapshot !== "object"
            || Array.isArray(snapshot)
            || typeof snapshot.storageState !== "string"
            || typeof snapshot.pendingWrite !== "boolean"
            || typeof snapshot.queuedWrite !== "boolean"
            || typeof snapshot.migrationRequested !== "boolean"
            || typeof snapshot.previewing !== "boolean"
            || typeof snapshot.audioState !== "string"
            || typeof snapshot.notificationOutcome !== "string"
            || !Number.isSafeInteger(snapshot.ringingCount)
            || snapshot.ringingCount < 0) {
        return {locallyDrained:false, reason:"INVALID_WRITER_SNAPSHOT",
            releaseAcknowledged:false, canTransferOwnership:false};
    }
    let reason = "LOCAL_WRITE_QUEUE_DRAINED_ONLY";
    if (snapshot.storageState !== "ready")
        reason = "WRITER_STORAGE_NOT_READY";
    else if (snapshot.pendingWrite || snapshot.queuedWrite)
        reason = "WRITER_SAVE_STILL_IN_FLIGHT";
    else if (snapshot.migrationRequested)
        reason = "WRITER_LEGACY_MIGRATION_PENDING";
    else if (snapshot.ringingCount !== 0)
        reason = "ACTIVE_ALARM_RINGING";
    else if (snapshot.previewing)
        reason = "ALARM_AUDIO_PREVIEW_ACTIVE";
    else if (snapshot.audioState !== "IDLE")
        reason = "ALARM_AUDIO_NOT_IDLE";
    else if (snapshot.notificationOutcome === "DELIVERY PENDING")
        reason = "ALARM_NOTIFICATION_IN_FLIGHT";
    return {locallyDrained:reason === "LOCAL_WRITE_QUEUE_DRAINED_ONLY",
        reason:reason, releaseAcknowledged:false, canTransferOwnership:false};
}

function requestRelease(snapshot) {
    // This will become a caller-side request ONLY after authenticated Clock
    // installed roles, kernel session binding, a durable V2 save witness and
    // an actual trusted old-writer stop/ack channel all exist. Presently none
    // exists. A locally-drained writer is still allowed to save tomorrow.
    const observed = status(snapshot);
    return {
        ok:false,
        reason:observed.locallyDrained ? "NO_TRUSTED_WRITER_RELEASE_BRIDGE"
                                      : observed.reason,
        locallyDrained:observed.locallyDrained,
        releaseAcknowledged:false,
        canTransferOwnership:false,
        ownsRealAlarmFile:false,
        canRing:false
    };
}

function writerBarrier(phase) {
    // Synthetic pure guard for the eventual mounted writer gate. No QML
    // state machine currently calls this: the live writer is unchanged.
    if (phase === "ACTIVE") return {allowSave:true, allowTick:true};
    if (phase === "QUIESCING" || phase === "RELEASED")
        return {allowSave:false, allowTick:false};
    return {allowSave:false, allowTick:false};
}
