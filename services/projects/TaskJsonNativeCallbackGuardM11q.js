.pragma library

// M11q standalone M11m native-test callback fence. Pure, side-effect-free.
// This is NOT a production writer, a security nonce or OS admission authority.
// FileView signals do not carry stage IDs: unexpected signals must still
// be treated as ambiguous, never attributed to an active save automatically.
function ticket(generation, epoch, stageId, fixturePath) {
    return {generation:generation, epoch:epoch, stageId:stageId,
        fixturePath:fixturePath};
}
function canDeferredReadback(now, captured) {
    if (!now || !captured || typeof now!=="object" ||
            typeof captured!=="object") return false;
    return now.attached === true && now.connected === true
        && now.hostRunning === true
        && now.fileState === "VERIFYING"
        && typeof now.pendingRaw === "string" && now.pendingRaw.length > 0
        && typeof now.pendingStageId === "string" && now.pendingStageId.length > 0
        && typeof now.fixturePath === "string" && now.fixturePath.length > 0
        && Number.isSafeInteger(now.generation) && now.generation >= 1
        && Number.isSafeInteger(now.epoch) && now.epoch >= 0
        && captured.generation === now.generation
        && captured.epoch === now.epoch
        && captured.stageId === now.pendingStageId
        && captured.fixturePath === now.fixturePath;
}
function settledReplyEligible(state, reply, expectedEpoch) {
    if (!state || !reply || typeof state!=="object" ||
            typeof reply!=="object") return false;
    return state.attached === true && state.connected === true
        && state.hostRunning === true && state.fileState === "SETTLING"
        && typeof state.pendingRaw === "string" && state.pendingRaw.length > 0
        && typeof state.pendingStageId === "string" && state.pendingStageId.length > 0
        && Number.isSafeInteger(state.epoch) && state.epoch >= 0
        && reply.kind === "verify" && reply.ok === true
        && reply.pending === false && reply.phase === "JSON_ACTIVE"
        && reply.stageId === state.pendingStageId
        && reply.epoch === expectedEpoch && state.epoch === expectedEpoch;
}
