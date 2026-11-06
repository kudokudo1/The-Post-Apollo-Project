.pragma library

// TASKS M14a // Passive projection of native FileView callback metadata.
// No source bytes, receipts, principal IDs, hashes, file paths or draft data.
// This is a live application-local HINT, never independently verified source.
// QML reads this one in-memory object from ApolloHubTodoStore; no IO.
var PHASES = {
    NOT_OBSERVED: {
        title:"NATIVE SAVE // NO CALLBACK OBSERVED THIS SESSION",
        explanation:"No FileView save callback has been recorded since this Quickshell session started. This says nothing about earlier sessions or the current file."
    },
    WRITE_REQUESTED: {
        title:"NATIVE SAVE // WRITE REQUESTED",
        explanation:"The existing TASKS writer requested a save. The native completion callback has not yet been observed for this latest attempt."
    },
    FILEVIEW_SAVED_HINT: {
        title:"NATIVE SAVE // CALLBACK OBSERVED / UNVERIFIED",
        explanation:"Quickshell's FileView onSaved handler ran while storage was saving. This is a callback hint, not independent readback, an authenticated writer receipt or proof of disk durability."
    },
    UNATTRIBUTED_SAVED_HINT: {
        title:"NATIVE SAVE // UNATTRIBUTED CALLBACK",
        explanation:"FileView onSaved ran outside a recognized saving state. It cannot be matched to a task edit or a durable source revision."
    },
    FILEVIEW_SAVE_FAILED: {
        title:"NATIVE SAVE // FAILURE CALLBACK OBSERVED",
        explanation:"FileView reported a failed save. The previous confirmed task view must remain authoritative; any unsaved edit needs review."
    }
};
var SOURCE_STATES = {
    loading:"SOURCE // LOADING",
    ready:"SOURCE // READY (REVISION UNVERIFIED)",
    empty:"SOURCE // EMPTY (REVISION UNVERIFIED)",
    saving:"SOURCE // SAVE PENDING (NOT CONFIRMED)",
    error:"SOURCE // ERROR / REVIEW REQUIRED",
    unsupported:"SOURCE // UNSUPPORTED / REVIEW REQUIRED"
};
function exact(data) {
    if(!data || typeof data!=="object" || Array.isArray(data))return false;
    return JSON.stringify(Object.keys(data).sort())===
        JSON.stringify(["phase","requestCount","sourceState"].sort());
}
function view(data) {
    var valid=exact(data) &&
        typeof data.phase==="string" &&
        Object.prototype.hasOwnProperty.call(PHASES,data.phase) &&
        typeof data.sourceState==="string" &&
        Object.prototype.hasOwnProperty.call(SOURCE_STATES,data.sourceState) &&
        typeof data.requestCount==="number" &&
        isFinite(data.requestCount) && Math.floor(data.requestCount)===data.requestCount &&
        data.requestCount>=0 && data.requestCount<=1000000;
    var phase=valid ? data.phase : "UNVERIFIED";
    var status=valid ? PHASES[phase] : {
        title:"NATIVE SAVE // OBSERVATION UNVERIFIED",
        explanation:"The live callback metadata is unavailable or malformed. No claim about the saved file can be made."
    };
    // A callback cannot be attributed to an application save without a
    // matching request. Even with one, this remains a non-authoritative hint.
    if(valid && data.requestCount===0 && phase==="FILEVIEW_SAVED_HINT") {
        status=PHASES.UNATTRIBUTED_SAVED_HINT;
        phase="UNATTRIBUTED_SAVED_HINT";
    }
    return {
        origin:"LIVE FILEVIEW SIGNAL // APPLICATION MEMORY ONLY",
        status:status.title,
        explanation:status.explanation,
        sourceStatus:valid ? SOURCE_STATES[data.sourceState]
                           : "SOURCE // UNVERIFIED",
        requestedCount:valid ? data.requestCount : null,
        proof:"CALLBACK PROVENANCE AND SAVED BYTES // NOT VERIFIED",
        draftDisposition:"KEEP UNSAVED DRAFT",
        lastConfirmedDisplay:"KEEP LAST CONFIRMED VIEW",
        realSavedSourceVerified:false,
        nativeCallbackAuthenticated:false,
        sourceOwnerAuthenticated:false,
        durableUserSaveAcknowledged:false,
        savedBytesReadbackVerified:false,
        encryptedRecoveryEnabled:false,
        canReplay:false,canWriteTasks:false,canClearDraft:false,
        canCapture:false,canPreview:false,canRestore:false,
        keyReleaseAuthorized:false
    };
}
