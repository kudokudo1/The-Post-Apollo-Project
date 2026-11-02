"use strict";
/* TASKS M13c: PURE, DISABLED synthetic pin + review-age contract.
 * No I/O, storage, timers, credentials, crypto identity or production path.
 * A SHA-256 supplied by the caller checks equality to a separately held
 * TEST fixture pin, not authenticity. It never authorizes replay, cleanup,
 * draft removal, data restore or production writes.
 */
const crypto=require("node:crypto");
const sha=raw=>crypto.createHash("sha256").update(raw).digest("hex");
const copy=x=>JSON.parse(JSON.stringify(x));
const keys=(x,items)=>x!==null && typeof x==="object" &&
    !Array.isArray(x) && Object.keys(x).sort().join(",")===items.slice().sort().join(",");
const hex=x=>typeof x==="string" && /^[a-f0-9]{64}$/.test(x);
const token=x=>typeof x==="string" && /^[A-Za-z0-9_-]{8,96}$/.test(x);
const num=x=>Number.isSafeInteger(x) && x>=0;
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function denied(reason) {
    return {ok:false,reason,mode:"RECOVERY_REVIEW",writable:false,
        writeAuthorized:false,replayAuthorized:false,restoreAuthorized:false,
        clearDraftAuthorized:false,deleteDraftAuthorized:false,
        productionActivation:false,sourceTrusted:false};
}
function evaluate({checkpointRaw,sourceRaw,review,display,pin,
                   nowMs,reviewAfterMs}={}) {
    if(typeof checkpointRaw!=="string"
            ||Buffer.byteLength(checkpointRaw,"utf8")>2097152
            ||(sourceRaw!==null && typeof sourceRaw!=="string")
            ||(typeof sourceRaw==="string" && Buffer.byteLength(sourceRaw,"utf8")>1048576))
        return denied("INVALID_SYNTHETIC_INPUT_BYTES");
    if(!num(nowMs)||!Number.isSafeInteger(reviewAfterMs)
            ||reviewAfterMs<1 || reviewAfterMs>2592000000)
        return denied("EXPLICIT_REVIEW_WINDOW_REQUIRED");
    const pinFields=["format","kind","checkpointSha256","sourceSha256",
        "sourceMissing","stageId","priorSessionId","priorOwnerEpoch",
        "freshEpoch","draftCapturedAtMs"];
    if(!keys(pin,pinFields) ||pin.format!==1 ||
            pin.kind!=="M13C_SEPARATE_FAKE_TEST_PIN" ||
            !hex(pin.checkpointSha256) ||
            !(pin.sourceSha256===null||hex(pin.sourceSha256)) ||
            typeof pin.sourceMissing!=="boolean" ||
            !token(pin.stageId.replace(/^m13a-/,"")) ||
            !token(pin.priorSessionId) ||
            !Number.isSafeInteger(pin.priorOwnerEpoch)||pin.priorOwnerEpoch<1 ||
            !Number.isSafeInteger(pin.freshEpoch)||pin.freshEpoch<=pin.priorOwnerEpoch ||
            !num(pin.draftCapturedAtMs))
        return denied("FAKE_PIN_SHAPE_REQUIRED");
    // The test pin must be independent of the current observation. Merely
    // recomputing this SHA from altered bytes would defeat this equality
    // check, so pin provenance remains an explicit unresolved future gate.
    if(sha(checkpointRaw)!==pin.checkpointSha256)
        return denied("CHECKPOINT_BYTES_DIFFER_FROM_PIN");
    if(sourceRaw===null) {
        if(pin.sourceMissing!==true||pin.sourceSha256!==null)
            return denied("SOURCE_ABSENCE_PIN_MISMATCH");
    } else if(pin.sourceMissing!==false ||
            sha(sourceRaw)!==pin.sourceSha256)
        return denied("SOURCE_BYTES_DIFFER_FROM_PIN");
    let record;
    try {record=JSON.parse(checkpointRaw);}
    catch(e) {return denied("INVALID_CHECKPOINT_JSON");}
    if(!record ||record.format!==1 ||
            record.kind!=="M13A_FAKE_RESTART_CHECKPOINT" ||
            record.stageId!==pin.stageId ||
            record.sessionId!==pin.priorSessionId ||
            record.ownerEpoch!==pin.priorOwnerEpoch)
        return denied("PIN_STAGE_OWNER_MISMATCH");
    if(!review || review.ok!==true ||
            review.reason!=="FRESH_OWNER_REVIEW_REQUIRED" ||
            review.phase!=="RECOVERY_REVIEW" ||
            review.writable!==false||review.writeAuthorized!==false ||
            review.replayAuthorized!==false||review.restoreAuthorized!==false ||
            review.clearDraftAuthorized!==false ||
            review.priorSessionId!==pin.priorSessionId ||
            review.priorOwnerEpoch!==pin.priorOwnerEpoch ||
            review.freshEpoch!==pin.freshEpoch ||
            review.stageId!==pin.stageId ||
            !review.draft || !Array.isArray(review.items) ||
            !Array.isArray(review.projects))
        return denied("FRESH_OWNER_REVIEW_MISMATCH");
    const observed=sourceRaw===null?"SOURCE_MISSING"
        :sourceRaw===record.beforeRaw?"SOURCE_AT_LAST_CONFIRMED"
        :sourceRaw===record.expectedRaw?"SOURCE_AT_CANDIDATE"
        :"SOURCE_MISMATCH";
    if(review.sourceStatus!==observed)
        return denied("SOURCE_CLASSIFICATION_MISMATCH");
    if(!display ||display.ok!==true ||
            display.reason!=="SYNTHETIC_READ_ONLY_RECOVERY_DISPLAY" ||
            display.mode!=="READ_ONLY_RECOVERY" ||
            display.stageId!==pin.stageId ||
            display.sourceStatus!==observed ||
            display.effect!=="KEEP_DRAFT_FINAL" ||
            display.writable!==false ||
            display.writeAuthorized!==false ||
            display.replayAuthorized!==false ||
            display.restoreAuthorized!==false ||
            display.clearDraftAuthorized!==false ||
            display.productionActivation!==false ||
            !display.overlay ||display.overlay.state!=="error" ||
            display.overlay.writable!==false ||
            !same(display.overlay.items,review.items) ||
            !same(display.overlay.projects,review.projects) ||
            !same(display.draft,review.draft.value) ||
            !display.ticket ||display.ticket.state!=="REVIEW_REQUIRED" ||
            display.ticket.disposition!=="KEEP_DRAFT")
        return denied("RECOVERY_DISPLAY_MISMATCH");
    const ageMs=nowMs-pin.draftCapturedAtMs;
    // Time rollback cannot justify deletion or promote data. Preserve as
    // CLOCK_UNCERTAIN; review thresholds are caller-selected synthetic values.
    const reviewUrgency=ageMs<0?"CLOCK_UNCERTAIN"
        :ageMs>=reviewAfterMs?"REVIEW_OVERDUE":"REVIEW_RECENT";
    return {ok:true,reason:"SYNTHETIC_PIN_MATCH_REVIEW_ONLY",
        mode:"RECOVERY_REVIEW",reviewUrgency,
        sourceStatus:observed,stageId:pin.stageId,
        draftPresent:true,draftRetention:"HOLD_FOR_OPERATOR_REVIEW",
        draftPersistence:"NOT_APPROVED_FOR_PRODUCTION",
        snapshot:copy(display.overlay),
        draft:copy(display.draft),
        writable:false,writeAuthorized:false,replayAuthorized:false,
        restoreAuthorized:false,clearDraftAuthorized:false,
        deleteDraftAuthorized:false,productionActivation:false,
        sourceTrusted:false};
}
module.exports={evaluate};
