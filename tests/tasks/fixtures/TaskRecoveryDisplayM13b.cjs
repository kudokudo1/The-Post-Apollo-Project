"use strict";
/*
 * TASKS M13b: PURE, unmounted, disabled recovery-display composition.
 * Consumes M13a's fake fresh-owner review and M12o/M12p ticket reducers.
 * Does not import live QML, access disk, authenticate a stage or authorize
 * source mutation, draft deletion, automatic retry, or production UI wiring.
 */
const copy=x=>JSON.parse(JSON.stringify(x));
const SOURCES=new Set(["SOURCE_AT_LAST_CONFIRMED","SOURCE_AT_CANDIDATE",
    "SOURCE_MISSING","SOURCE_MISMATCH"]);
const deny=reason=>({ok:false,reason,mode:"REFUSED",
    writeAuthorized:false,replayAuthorized:false,
    restoreAuthorized:false,clearDraftAuthorized:false});
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function project({review,ticket,link,contract,presenter,pendingHub}={}) {
    try {
        if(!review || review.ok!==true ||
                review.reason!=="FRESH_OWNER_REVIEW_REQUIRED" ||
                review.phase!=="RECOVERY_REVIEW" ||review.state!=="error" ||
                review.writable!==false ||
                review.writeAuthorized!==false ||
                review.replayAuthorized!==false ||
                review.restoreAuthorized!==false ||
                review.clearDraftAuthorized!==false ||
                review.disposition!=="KEEP_DRAFT" ||
                !SOURCES.has(review.sourceStatus) ||
                !Array.isArray(review.items)||!Array.isArray(review.projects) ||
                typeof review.stageId!=="string" ||
                typeof review.priorSessionId!=="string" ||
                !Number.isSafeInteger(review.priorOwnerEpoch) ||
                !Number.isSafeInteger(review.freshEpoch) ||
                review.freshEpoch<=review.priorOwnerEpoch ||
                !review.draft || typeof review.draft!=="object")
            return deny("VALID_FRESH_OWNER_REVIEW_REQUIRED");
        if(!contract ||typeof contract.reconcile!=="function" ||
                typeof contract.supported!=="function" ||
                !ticket ||typeof ticket!=="object" ||
                !contract.supported(ticket.surface,ticket.method) ||
                ticket.state!=="QUEUED" ||
                ticket.disposition!=="KEEP_DRAFT" ||
                typeof ticket.ticketId!=="string" ||
                !ticket.baseline ||!ticket.expected ||
                !Array.isArray(ticket.baseline.items) ||
                !Array.isArray(ticket.baseline.projects) ||
                !equal(ticket.baseline.items,review.items) ||
                !equal(ticket.baseline.projects,review.projects) ||
                !equal(ticket.draft,review.draft.value) ||
                ticket.surface!==review.draft.surface ||
                ticket.method!==review.draft.method)
            return deny("M12O_TICKET_BASELINE_OR_DRAFT_MISMATCH");
        // This synthetic link checks association, not trust. A caller can
        // fabricate it; production requires independently proven stage owner.
        if(!link ||typeof link!=="object" ||
                link.stageId!==review.stageId ||
                link.priorSessionId!==review.priorSessionId ||
                link.priorOwnerEpoch!==review.priorOwnerEpoch ||
                link.ticketId!==ticket.ticketId ||
                link.surface!==ticket.surface ||
                link.method!==ticket.method)
            return deny("SYNTHETIC_STAGE_TICKET_LINK_REQUIRED");
        const items=copy(review.items),projects=copy(review.projects);
        const total=items.length;
        const remaining=items.filter(x=>x && x.done===false).length;
        if(total!==ticket.baseline.total ||
                remaining!==ticket.baseline.remaining ||
                total-remaining!==ticket.baseline.completed ||
                !items.every(x=>x && typeof x.id==="string" &&
                    typeof x.title==="string" && typeof x.done==="boolean"))
            return deny("CONFIRMED_COUNTS_INVALID");
        const overlay={state:"error",writable:false,error:"RECOVERY_REVIEW",
            total,remaining,completed:total-remaining,items,projects};
        const event={ticketId:ticket.ticketId,state:"REVIEW_REQUIRED"};
        let result;
        if(ticket.surface==="HUB") {
            if(!presenter ||typeof presenter.advance!=="function" ||
                    !pendingHub || !pendingHub.ticket ||
                    pendingHub.ticket.ticketId!==ticket.ticketId ||
                    !equal(pendingHub.ticket,ticket))
                return deny("M12P_HUB_PENDING_REQUIRED");
            const outcome=presenter.advance(contract,pendingHub,event,overlay);
            if(!outcome ||outcome.effect!=="KEEP_DRAFT_FINAL" ||
                    !outcome.pending ||!outcome.pending.ticket ||
                    outcome.pending.ticket.state!=="REVIEW_REQUIRED" ||
                    outcome.pending.ticket.disposition!=="KEEP_DRAFT")
                return deny("HUB_RECOVERY_PRESENTATION_REFUSED");
            result=outcome.pending.ticket;
        } else {
            result=contract.reconcile(ticket,event,overlay);
            if(!result ||result.state!=="REVIEW_REQUIRED" ||
                    result.disposition!=="KEEP_DRAFT")
                return deny("CONSUMER_RECOVERY_PRESENTATION_REFUSED");
        }
        return {
            ok:true,reason:"SYNTHETIC_READ_ONLY_RECOVERY_DISPLAY",
            mode:"READ_ONLY_RECOVERY",stageId:review.stageId,
            sourceStatus:review.sourceStatus,priorPhase:review.priorPhase,
            overlay,draft:copy(review.draft.value),ticket:copy(result),
            effect:"KEEP_DRAFT_FINAL",writable:false,
            writeAuthorized:false,replayAuthorized:false,
            restoreAuthorized:false,clearDraftAuthorized:false,
            productionActivation:false
        };
    } catch(e) {
        return deny("RECOVERY_DISPLAY_UNAVAILABLE");
    }
}
module.exports={project};
