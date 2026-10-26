.pragma library

// M11i MEMORY-ONLY observation record for an explicitly launched M11g
// synthetic Quickshell test. It is NOT an acceptance certificate or
// production-authority token. Never record file paths, JSON, IDs or stdout.
var VERSION=1;
var LIMIT=32;
var TAGS=[
    "ATTACH_REQUEST","FILE_INITIAL_LOAD","HOST_HELLO",
    "STAGE_REQUEST","HOST_ADMIT","FILE_SAVED","FILE_READBACK_OK",
    "HOST_SETTLED","FREEZE_REQUEST","HOST_FROZEN",
    "FILE_SAVE_FAILURE","FILE_LOAD_FAILURE",
    "FILE_READBACK_MISMATCH","HOST_REFUSAL",
    "RECOVERY_REVIEW","STOP_REQUEST","HOST_EXIT"
];
var PHASES=[
    "UNVERIFIED","JSON_ACTIVE","FREEZE_REQUESTED","JSON_QUIESCED",
    "RECOVERY_REVIEW","UNKNOWN"
];

function empty() {
    return {version:VERSION,sequence:0,dropped:0,events:[]};
}
function append(current,tag,phase) {
    if (!current || current.version!==VERSION
            || !Number.isSafeInteger(current.sequence)
            || current.sequence<0 || current.sequence>=1000000
            || !Array.isArray(current.events) || current.events.length>LIMIT)
        return empty();
    if (TAGS.indexOf(tag)<0) return current;
    // No caller-supplied strings except vetted enum values.
    var safePhase=PHASES.indexOf(phase)>=0 ? phase : "UNKNOWN";
    var updated=current.events.slice();
    updated.push({seq:current.sequence+1,tag:tag,phase:safePhase});
    var removed=Math.max(0,updated.length-LIMIT);
    if (removed) updated=updated.slice(removed);
    return {version:VERSION,sequence:current.sequence+1,
            dropped:current.dropped+removed,events:updated};
}
function summarize(current) {
    if (!current || !Array.isArray(current.events))
        return {chainObserved:false,saveChains:0,frozen:false,
            lastEvent:"NONE",total:0,recoveryObserved:false,
            label:"NO_EVIDENCE"};
    var order=["STAGE_REQUEST","HOST_ADMIT","FILE_SAVED",
        "FILE_READBACK_OK","HOST_SETTLED"];
    var progress=0,chains=0,recovery=false,frozen=false;
    for (var i=0;i<current.events.length;i++) {
        var tag=current.events[i].tag;
        if (tag==="RECOVERY_REVIEW" || tag==="HOST_EXIT"
                || tag==="FILE_SAVE_FAILURE" || tag==="FILE_LOAD_FAILURE"
                || tag==="HOST_REFUSAL" || tag==="FILE_READBACK_MISMATCH") {
            progress=0;
            if (tag==="RECOVERY_REVIEW" || tag==="HOST_EXIT")
                recovery=true;
        } else if (tag==="HOST_FROZEN") {
            frozen=true;
        } else if (tag==="STAGE_REQUEST") {
            progress=1;
        } else if (order[progress]===tag) {
            progress+=1;
            if (progress===order.length) {
                chains+=1;
                progress=0;
            }
        } else if (order.indexOf(tag)>=0) {
            // A skipped or out-of-order callback never counts as complete.
            progress=0;
        }
    }
    return {chainObserved:chains>0,saveChains:chains,frozen:frozen,
        lastEvent:current.events.length
            ? current.events[current.events.length-1].tag : "NONE",
        total:current.sequence,recoveryObserved:recovery,
        label:"OBSERVATION_ONLY_NOT_NATIVE_ACCEPTED"};
}
function recent(current,count) {
    if (!current || !Array.isArray(current.events)) return "NONE";
    var n=Number.isSafeInteger(count) && count>0 && count<=8 ? count:6;
    return current.events.slice(-n).map(function(x) {
        return x.seq+":"+x.tag;
    }).join("  ");
}
