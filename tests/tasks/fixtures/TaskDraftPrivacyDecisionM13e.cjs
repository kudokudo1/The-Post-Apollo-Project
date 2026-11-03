"use strict";
/*
 * TASKS M13e: PURE, unmounted privacy DECISION-DOSSIER contract.
 *
 * This tests how the operator could choose a policy later, not whether the
 * operator has approved one. NO persistence, encryption, key access, I/O,
 * export, deletion, sync, privileged host or production QML integration.
 * A syntactically well-formed policy proposal is NEVER an authorization.
 */
const SURFACES=Object.freeze(["DETAILS","HUB","PLANNER","PROJECTS"]);
const NO_POWER=Object.freeze({
    policyApproved:false,productionActivation:false,sourceTrusted:false,
    readAuthorized:false,writeAuthorized:false,
    persistAuthorized:false,exportAuthorized:false,deleteAuthorized:false,
    clearDraftAuthorized:false,replayAuthorized:false,
    restoreAuthorized:false,syncAuthorized:false
});
const deny=reason=>({ok:false,status:"REFUSED",reason,...NO_POWER});
const exact=(value,fields)=>value!==null&&typeof value==="object"
    &&!Array.isArray(value)
    &&Object.keys(value).sort().join(",")===fields.slice().sort().join(",");
const PROPOSAL_FIELDS=[
    "kind","revision","dataClass","surfaces","persistence","storageLocation",
    "atRest","unlock","keyProvider","backupHandling","retentionMode",
    "reviewAfterMs","automaticDeletion","exportMode","exportFormat",
    "exportTarget","deleteScope","deleteConfirmation","sync",
    "contentLogging","operatorApproval"
];
function assess(proposal) {
    if(!exact(proposal,PROPOSAL_FIELDS)
        ||proposal.kind!=="M13E_FAKE_PRIVACY_PROPOSAL"
        ||proposal.revision!==1
        ||proposal.dataClass!=="UNCOMMITTED_TASK_DRAFT_ONLY"
        ||!Array.isArray(proposal.surfaces)
        ||proposal.surfaces.length!==SURFACES.length
        ||proposal.surfaces.some((s,i)=>s!==SURFACES[i])
        ||proposal.automaticDeletion!==false
        ||proposal.deleteScope!=="DRAFT_ONLY"
        ||proposal.deleteConfirmation!=="SEPARATE_GESTURE_REQUIRED"
        ||proposal.sync!=="OFF"
        ||proposal.contentLogging!=="DISALLOWED"
        ||proposal.operatorApproval!=="NOT_GRANTED")
        return deny("PRIVACY_BOUNDARY_REFUSED");
    if(proposal.persistence==="MEMORY_ONLY") {
        if(proposal.storageLocation!=="NONE"
            ||proposal.atRest!=="NOT_APPLICABLE"
            ||proposal.unlock!=="NONE"
            ||proposal.keyProvider!=="NONE"
            ||proposal.backupHandling!=="NONE"
            ||proposal.retentionMode!=="SESSION_ONLY"
            ||proposal.reviewAfterMs!==null
            ||proposal.exportMode!=="DISABLED"
            ||proposal.exportFormat!=="NONE"
            ||proposal.exportTarget!=="NONE")
            return deny("MEMORY_ONLY_POLICY_MISMATCH");
        return {ok:true,status:"MEMORY_ONLY_REVIEW_CANDIDATE",
            reason:"NO_PERSISTENCE_SELECTED_BY_TEST_PROPOSAL",
            draftCanSurviveProcessExit:false,
            risks:["DRAFT_LOST_ON_PROCESS_EXIT","NO_CROSS_RESTART_RECOVERY"],
            openDecisions:["OPERATOR_POLICY_APPROVAL","LIVE_UI_INTEGRATION"],
            ...NO_POWER};
    }
    if(proposal.persistence==="LOCAL_ENCRYPTED_OPT_IN") {
        if(proposal.storageLocation!=="NOT_SELECTED"
            ||proposal.atRest!=="ENCRYPTION_REQUIRED_UNVERIFIED"
            ||proposal.unlock!=="SEPARATE_UNLOCK_REQUIRED"
            ||proposal.keyProvider!=="NOT_SELECTED"
            ||proposal.backupHandling!=="OPERATOR_DECISION_REQUIRED"
            ||proposal.retentionMode!=="MANUAL_REVIEW"
            ||!Number.isSafeInteger(proposal.reviewAfterMs)
            ||proposal.reviewAfterMs<1
            ||proposal.reviewAfterMs>2592000000
            ||proposal.exportMode!=="EXPLICIT_REVIEW_ONLY"
            ||proposal.exportFormat!=="NOT_SELECTED"
            ||proposal.exportTarget!=="NOT_SELECTED")
            return deny("ENCRYPTED_LOCAL_REVIEW_FIELDS_REQUIRED");
        return {ok:true,status:"ENCRYPTED_LOCAL_DESIGN_REVIEW_CANDIDATE",
            reason:"NO_KEY_PROVIDER_OR_PRIVACY_DECISION_APPROVED",
            draftCanSurviveProcessExit:"PROPOSED_ONLY",
            risks:["KEY_LOSS_CAN_MAKE_DRAFT_UNRECOVERABLE",
                "SAME_USER_PROCESS_ACCESS_NOT_RESOLVED",
                "EXPORT_CAN_EXPOSE_DECRYPTED_DATA"],
            openDecisions:[
                "OPERATOR_OPT_IN","KEY_PROVIDER_AND_UNLOCK",
                "REAL_STORAGE_IDENTITY_AND_PERMISSIONS",
                "NATIVE_ENCRYPTION_VERIFICATION",
                "BACKUP_AND_KEY_RECOVERY_POLICY",
                "RETENTION_REVIEW_WINDOW",
                "EXPORT_FORMAT_TARGET_AND_DISCLOSURE",
                "DRAFT_ONLY_DELETION_AND_UNDO",
                "LIVE_UI_INTEGRATION"
            ],
            ...NO_POWER};
    }
    return deny("UNSUPPORTED_PERSISTENCE_MODE");
}
function decisionBoundary({assessment,choice}={}) {
    // M13d fake first/second gestures and the M13e policy are NOT actual
    // operator authority. Even a valid pair cannot touch data.
    if(!assessment ||assessment.ok!==true ||
        assessment.policyApproved!==false ||
        assessment.productionActivation!==false ||
        assessment.persistAuthorized!==false ||
        assessment.exportAuthorized!==false ||
        assessment.deleteAuthorized!==false)
        return deny("VALID_UNAPPROVED_POLICY_PROPOSAL_REQUIRED");
    if(!choice ||choice.ok!==true
        ||!["SYNTHETIC_CHOICE_ONLY","SYNTHETIC_SECOND_GESTURE_RECORDED"]
            .includes(choice.reason)
        ||choice.draftDisposition!=="KEEP_DRAFT"
        ||choice.writeAuthorized!==false
        ||choice.replayAuthorized!==false
        ||choice.restoreAuthorized!==false
        ||choice.exportAuthorized!==false
        ||choice.deleteDraftAuthorized!==false
        ||choice.clearDraftAuthorized!==false
        ||choice.productionActivation!==false
        ||choice.sourceTrusted!==false)
        return deny("VALID_NONACTUATING_M13D_CHOICE_REQUIRED");
    const action=choice.action||choice.proposal?.action;
    if(!["KEEP","EXPORT","DELETE"].includes(action))
        return deny("UNKNOWN_DRAFT_CHOICE");
    return {
        ok:true,status:"SEPARATE_OPERATOR_AND_RUNTIME_AUTHORIZATION_REQUIRED",
        reason:"SYNTHETIC_POLICY_AND_GESTURES_NOT_EXECUTABLE",
        action,draftDisposition:"KEEP_DRAFT",
        nextRequired:action==="KEEP"?"OPERATOR_REVIEW":
            action==="EXPORT"?"ACTUAL_TARGET_PERMISSION_AND_CONTENT_REVIEW":
            "REAL_DRAFT_IDENTITY_AND_EXPLICIT_DELETION_AUTHORIZATION",
        ...NO_POWER
    };
}
module.exports={assess,decisionBoundary,NO_POWER};
