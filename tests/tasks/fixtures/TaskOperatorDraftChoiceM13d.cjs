"use strict";
/*
 * TASKS M13d // PURE, UNMOUNTED operator-intent model (synthetic only).
 *
 * Converts a fake M13c recovery review into a choice proposal, optionally
 * records a second fake gesture. NEVER exports, deletes, retries, restores,
 * clears, grants permission, holds real drafts, or interacts with a source.
 * Gesture IDs / hashes are correlations only, NOT trusted authorization.
 */
const crypto=require("node:crypto");
const digest=value=>crypto.createHash("sha256").update(value).digest("hex");
const serial=value=>JSON.stringify(value);
const exact=(x,names)=>x!==null&&typeof x==="object"&&!Array.isArray(x)
    &&Object.keys(x).sort().join(",")===names.slice().sort().join(",");
const token=x=>typeof x==="string" && /^[A-Za-z0-9_-]{8,80}$/.test(x);
const sha=x=>typeof x==="string" && /^[a-f0-9]{64}$/.test(x);
const VALID_ACTIONS=new Set(["KEEP","EXPORT","DELETE"]);
const VALID_URGENCY=new Set(["REVIEW_RECENT","REVIEW_OVERDUE","CLOCK_UNCERTAIN"]);
const VALID_SOURCE=new Set(["SOURCE_AT_LAST_CONFIRMED","SOURCE_AT_CANDIDATE",
    "SOURCE_MISSING","SOURCE_MISMATCH"]);
const NO_AUTH={
    writeAuthorized:false,replayAuthorized:false,restoreAuthorized:false,
    clearDraftAuthorized:false,deleteDraftAuthorized:false,
    exportAuthorized:false,productionActivation:false,sourceTrusted:false
};
const deny=reason=>({ok:false,reason,state:"REFUSED",...NO_AUTH});
function validReview(review) {
    if(!review||review.ok!==true ||
        review.reason!=="SYNTHETIC_PIN_MATCH_REVIEW_ONLY" ||
        review.mode!=="RECOVERY_REVIEW" ||
        !token(review.stageId.replace(/^m13a-/,"")) ||
        !VALID_URGENCY.has(review.reviewUrgency) ||
        !VALID_SOURCE.has(review.sourceStatus) ||
        review.draftPresent!==true ||
        review.draftRetention!=="HOLD_FOR_OPERATOR_REVIEW" ||
        review.draftPersistence!=="NOT_APPROVED_FOR_PRODUCTION" ||
        review.writable!==false ||
        review.writeAuthorized!==false ||
        review.replayAuthorized!==false ||
        review.restoreAuthorized!==false ||
        review.clearDraftAuthorized!==false ||
        review.deleteDraftAuthorized!==false ||
        review.productionActivation!==false ||
        review.sourceTrusted!==false ||
        !review.snapshot ||review.snapshot.state!=="error" ||
        review.snapshot.writable!==false ||
        !Array.isArray(review.snapshot.items) ||
        !Array.isArray(review.snapshot.projects) ||
        !review.draft ||typeof review.draft!=="object" ||
        Array.isArray(review.draft))
        return false;
    return true;
}
function bindReview(review) {
    // Compare only exact synthetic review content; this hash cannot
    // authenticate caller-created bytes or an unrelated production owner.
    const content=serial({stageId:review.stageId,
        sourceStatus:review.sourceStatus,reviewUrgency:review.reviewUrgency,
        draft:review.draft,snapshot:review.snapshot});
    if(typeof content!=="string" ||Buffer.byteLength(content,"utf8")>2097152)
        return null;
    return digest(content);
}
function decisionId(proposal) {
    return "m13d-"+digest(serial([
        proposal.stageId,proposal.action,proposal.gestureId,
        proposal.reviewDigest,proposal.selectedAtMs
    ])).slice(0,32);
}
function select({review,choice}={}) {
    try {
        if(!validReview(review)) return deny("VALID_M13C_RECOVERY_REVIEW_REQUIRED");
        if(!exact(choice,["kind","action","stageId","gestureId",
                         "reviewDigest","selectedAtMs"]) ||
            choice.kind!=="M13D_FAKE_OPERATOR_CHOICE" ||
            !VALID_ACTIONS.has(choice.action) ||
            choice.stageId!==review.stageId ||
            !token(choice.gestureId) ||
            !sha(choice.reviewDigest) ||
            !Number.isSafeInteger(choice.selectedAtMs) ||
            choice.selectedAtMs<0)
            return deny("EXPLICIT_SYNTHETIC_CHOICE_REQUIRED");
        const actual=bindReview(review);
        if(!actual ||actual!==choice.reviewDigest)
            return deny("REVIEW_CHANGED_SINCE_CHOICE");
        const next={
            kind:"M13D_SYNTHETIC_CHOICE_PROPOSAL",
            action:choice.action,stageId:choice.stageId,
            gestureId:choice.gestureId,selectedAtMs:choice.selectedAtMs,
            reviewDigest:actual
        };
        next.decisionId=decisionId(next);
        const state=choice.action==="KEEP"?"KEEP_NOTED_FOR_REVIEW":
            choice.action==="EXPORT"?"EXPORT_HANDOFF_REVIEW_REQUIRED":
            "DELETE_SECOND_CONFIRMATION_REQUIRED";
        return {ok:true,reason:"SYNTHETIC_CHOICE_ONLY",state,
            proposal:next,draftDisposition:"KEEP_DRAFT",
            outstandingApproval:choice.action==="KEEP"?"NONE":
                choice.action==="EXPORT"?"EXTERNAL_EXPORT_TARGET_AND_PERMISSION":
                "SECOND_GESTURE_AND_EXTERNAL_DELETE_PERMISSION",
            ...NO_AUTH};
    } catch(e) {
        return deny("CHOICE_EVALUATION_UNAVAILABLE");
    }
}
function confirm({review,proposal,confirmation}={}) {
    try {
        if(!validReview(review)) return deny("VALID_M13C_RECOVERY_REVIEW_REQUIRED");
        const fields=["kind","action","stageId","gestureId","selectedAtMs",
                      "reviewDigest","decisionId"];
        if(!exact(proposal,fields) ||
            proposal.kind!=="M13D_SYNTHETIC_CHOICE_PROPOSAL" ||
            !VALID_ACTIONS.has(proposal.action) ||proposal.action==="KEEP" ||
            proposal.stageId!==review.stageId ||
            !token(proposal.gestureId) ||
            !Number.isSafeInteger(proposal.selectedAtMs) ||
            proposal.selectedAtMs<0 ||
            !sha(proposal.reviewDigest) ||
            proposal.decisionId!==decisionId(proposal))
            return deny("VALID_PENDING_EXPORT_OR_DELETE_REQUIRED");
        if(proposal.reviewDigest!==bindReview(review))
            return deny("RECOVERY_REVIEW_CHANGED");
        if(!exact(confirmation,["kind","decisionId","stageId","action",
                                "gestureId","acknowledgedUncertainSave",
                                "scope"]) ||
            confirmation.kind!=="M13D_FAKE_SECOND_GESTURE" ||
            confirmation.decisionId!==proposal.decisionId ||
            confirmation.stageId!==proposal.stageId ||
            confirmation.action!==proposal.action ||
            !token(confirmation.gestureId) ||
            confirmation.gestureId===proposal.gestureId ||
            confirmation.acknowledgedUncertainSave!==true ||
            confirmation.scope!=="DRAFT_ONLY")
            return deny("SEPARATE_SYNTHETIC_CONFIRMATION_REQUIRED");
        // No actual export/delete, no target selected, and no claim that
        // this fake gesture came from the real operator.
        return {ok:true,reason:"SYNTHETIC_SECOND_GESTURE_RECORDED",
            state:proposal.action==="EXPORT"?"EXPORT_AWAITING_EXTERNAL_TARGET":
                "DELETE_AWAITING_EXTERNAL_AUTHORIZATION",
            decisionId:proposal.decisionId,stageId:proposal.stageId,
            action:proposal.action,
            draftDisposition:"KEEP_DRAFT",
            externalExecutionRequired:true,
            ...NO_AUTH};
    } catch(e) {
        return deny("CONFIRMATION_EVALUATION_UNAVAILABLE");
    }
}
module.exports={select,confirm,bindReview};
