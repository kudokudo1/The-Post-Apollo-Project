#!/usr/bin/env node
"use strict";
// M13e: synthetic privacy decisions and fake M13d gestures only.
// Never reads user data, creates drafts or runs live Quickshell.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const policy=require("./fixtures/TaskDraftPrivacyDecisionM13e.cjs");
const choices=require("./fixtures/TaskOperatorDraftChoiceM13d.cjs");
const ROOT=path.resolve(__dirname,"../..");
const copy=x=>JSON.parse(JSON.stringify(x));
const SURFACES=["DETAILS","HUB","PLANNER","PROJECTS"];
function memoryProposal() {
    return {
        kind:"M13E_FAKE_PRIVACY_PROPOSAL",revision:1,
        dataClass:"UNCOMMITTED_TASK_DRAFT_ONLY",surfaces:[...SURFACES],
        persistence:"MEMORY_ONLY",storageLocation:"NONE",
        atRest:"NOT_APPLICABLE",unlock:"NONE",keyProvider:"NONE",
        backupHandling:"NONE",retentionMode:"SESSION_ONLY",reviewAfterMs:null,
        automaticDeletion:false,exportMode:"DISABLED",
        exportFormat:"NONE",exportTarget:"NONE",
        deleteScope:"DRAFT_ONLY",
        deleteConfirmation:"SEPARATE_GESTURE_REQUIRED",
        sync:"OFF",contentLogging:"DISALLOWED",
        operatorApproval:"NOT_GRANTED"
    };
}
function encryptedProposal() {
    return {...memoryProposal(),
        persistence:"LOCAL_ENCRYPTED_OPT_IN",storageLocation:"NOT_SELECTED",
        atRest:"ENCRYPTION_REQUIRED_UNVERIFIED",
        unlock:"SEPARATE_UNLOCK_REQUIRED",keyProvider:"NOT_SELECTED",
        backupHandling:"OPERATOR_DECISION_REQUIRED",
        retentionMode:"MANUAL_REVIEW",reviewAfterMs:86400000,
        exportMode:"EXPLICIT_REVIEW_ONLY",
        exportFormat:"NOT_SELECTED",exportTarget:"NOT_SELECTED"
    };
}
function noPower(x) {
    for(const key of Object.keys(policy.NO_POWER))
        assert.equal(x[key],false,key);
}
test("no policy selected is always refused; no persistence or operations",()=>{
    for(const input of [undefined,null,{},true]) {
        const result=policy.assess(input);
        assert.equal(result.ok,false);
        noPower(result);
    }
});
test("memory-only is a proposed policy, not cross-restart recovery",()=>{
    const proposed=policy.assess(memoryProposal());
    assert.equal(proposed.ok,true);
    assert.equal(proposed.status,"MEMORY_ONLY_REVIEW_CANDIDATE");
    assert.equal(proposed.draftCanSurviveProcessExit,false);
    assert.ok(proposed.risks.includes("DRAFT_LOST_ON_PROCESS_EXIT"));
    noPower(proposed);
});
test("encrypted local is only a review candidate with unresolved key/storage/backup",()=>{
    const proposed=policy.assess(encryptedProposal());
    assert.equal(proposed.ok,true);
    assert.equal(proposed.status,"ENCRYPTED_LOCAL_DESIGN_REVIEW_CANDIDATE");
    assert.equal(proposed.draftCanSurviveProcessExit,"PROPOSED_ONLY");
    for(const gap of ["KEY_PROVIDER_AND_UNLOCK",
        "REAL_STORAGE_IDENTITY_AND_PERMISSIONS",
        "NATIVE_ENCRYPTION_VERIFICATION",
        "BACKUP_AND_KEY_RECOVERY_POLICY",
        "DRAFT_ONLY_DELETION_AND_UNDO",
        "EXPORT_FORMAT_TARGET_AND_DISCLOSURE"])
        assert.ok(proposed.openDecisions.includes(gap),gap);
    noPower(proposed);
});
test("no plaintext, new sync, content logging, auto-delete, expanded scope or fake approval",()=>{
    const bad=[
        {persistence:"LOCAL_PLAINTEXT"},
        {persistence:"SYNCED_CLOUD"},
        {sync:"ON"},
        {automaticDeletion:true},
        {contentLogging:"DEBUG_FULL_DRAFT"},
        {deleteScope:"ALL_TASK_DATA"},
        {deleteConfirmation:"NONE"},
        {operatorApproval:"GRANTED"},
        {dataClass:"TASKS_JSON_AND_BACKUPS"},
        {surfaces:["HUB"]},
        {kind:"M13E_REAL_OPERATOR_CHOICE"},
        {revision:2},
        {newField:"unexpected"}
    ];
    for(const variant of bad) {
        const input={...encryptedProposal(),...variant};
        const result=policy.assess(input);
        assert.equal(result.ok,false,JSON.stringify(variant));
        noPower(result);
    }
});
test("encrypted proposal refuses unselected security boundary shortcuts",()=>{
    const bad=[
        {storageLocation:"/home/user/private"},
        {atRest:"PLAIN_TEXT"},
        {atRest:"AES256_VERIFIED"},
        {unlock:"AUTO_UNLOCK"},
        {keyProvider:"ALREADY_VERIFIED"},
        {backupHandling:"BACKUP_ALL"},
        {retentionMode:"AUTO_PURGE"},
        {reviewAfterMs:null},
        {reviewAfterMs:0},
        {reviewAfterMs:-1},
        {reviewAfterMs:2592000001},
        {reviewAfterMs:1.5},
        {exportMode:"AUTOMATIC"},
        {exportFormat:"JSON_CLEAR_TEXT"},
        {exportTarget:"SOME_EXTERNAL_URL"}
    ];
    for(const variant of bad) {
        const result=policy.assess({...encryptedProposal(),...variant});
        assert.equal(result.ok,false,JSON.stringify(variant));
        noPower(result);
    }
});
test("memory mode refuses any hidden persistence, backups or exports",()=>{
    for(const variant of [
        {storageLocation:"/tmp"},
        {atRest:"ENCRYPTION_REQUIRED_UNVERIFIED"},
        {unlock:"SEPARATE_UNLOCK_REQUIRED"},
        {keyProvider:"NOT_SELECTED"},
        {backupHandling:"OPERATOR_DECISION_REQUIRED"},
        {retentionMode:"MANUAL_REVIEW"},
        {reviewAfterMs:1000},
        {exportMode:"EXPLICIT_REVIEW_ONLY"},
        {exportFormat:"NOT_SELECTED"},
        {exportTarget:"NOT_SELECTED"}
    ]) {
        const result=policy.assess({...memoryProposal(),...variant});
        assert.equal(result.ok,false,JSON.stringify(variant));
        noPower(result);
    }
});
function fakeReview() {
    return {
        ok:true,reason:"SYNTHETIC_PIN_MATCH_REVIEW_ONLY",
        mode:"RECOVERY_REVIEW",
        stageId:"m13a-M13eOldSession001-7-1",
        reviewUrgency:"REVIEW_RECENT",
        sourceStatus:"SOURCE_AT_CANDIDATE",draftPresent:true,
        draftRetention:"HOLD_FOR_OPERATOR_REVIEW",
        draftPersistence:"NOT_APPROVED_FOR_PRODUCTION",
        writable:false,writeAuthorized:false,replayAuthorized:false,
        restoreAuthorized:false,clearDraftAuthorized:false,
        deleteDraftAuthorized:false,productionActivation:false,
        sourceTrusted:false,
        snapshot:{state:"error",writable:false,
                  items:[{id:"t1",title:"SYNTHETIC_ONLY",done:false}],
                  projects:[]},
        draft:{title:"SYNTHETIC_UNSAVED_TITLE"}
    };
}
function fakeChoice(review,action) {
    return {
        kind:"M13D_FAKE_OPERATOR_CHOICE",action,
        stageId:review.stageId,gestureId:"M13eGesture001",
        reviewDigest:choices.bindReview(review),selectedAtMs:1000000
    };
}
function fakeSecond(proposal) {
    return {
        kind:"M13D_FAKE_SECOND_GESTURE",
        decisionId:proposal.decisionId,stageId:proposal.stageId,
        action:proposal.action,gestureId:"M13eGesture002",
        acknowledgedUncertainSave:true,scope:"DRAFT_ONLY"
    };
}
test("M13d keep/export/delete intents never become privacy authorization",()=>{
    const review=fakeReview();
    for(const action of ["KEEP","EXPORT","DELETE"]) {
        const first=choices.select({review,choice:fakeChoice(review,action)});
        assert.equal(first.ok,true,first.reason);
        const final=action==="KEEP"?first:
            choices.confirm({review,proposal:first.proposal,
                confirmation:fakeSecond(first.proposal)});
        assert.equal(final.ok,true,final.reason);
        for(const assessment of [
            policy.assess(memoryProposal()),policy.assess(encryptedProposal())
        ]) {
            const result=policy.decisionBoundary({assessment,choice:final});
            assert.equal(result.ok,true,result.reason);
            assert.equal(result.action,action);
            assert.equal(result.draftDisposition,"KEEP_DRAFT");
            assert.equal(result.status,"SEPARATE_OPERATOR_AND_RUNTIME_AUTHORIZATION_REQUIRED");
            noPower(result);
        }
    }
});
test("forged ability, unapproved source and malformed choice are rejected",()=>{
    const assessment=policy.assess(encryptedProposal());
    const review=fakeReview();
    const pick=choices.select({review,choice:fakeChoice(review,"EXPORT")});
    const fakeConfirmed=choices.confirm({review,proposal:pick.proposal,
        confirmation:fakeSecond(pick.proposal)});
    for(const part of [
        {assessment:{...assessment,policyApproved:true}},
        {assessment:{...assessment,persistAuthorized:true}},
        {assessment:{...assessment,deleteAuthorized:true}},
        {choice:{...fakeConfirmed,deleteDraftAuthorized:true}},
        {choice:{...fakeConfirmed,reason:"AUTHENTICATED_OPERATOR"}},
        {choice:{...fakeConfirmed,draftDisposition:"CLEAR_DRAFT"}},
        {choice:null},
        {assessment:null}
    ]) {
        const result=policy.decisionBoundary({
            assessment,choice:fakeConfirmed,...part});
        assert.equal(result.ok,false,JSON.stringify(part).slice(0,150));
        noPower(result);
    }
});
test("test-only policy source cannot write files or alter any live TASKS flags",()=>{
    const own=fs.readFileSync(path.join(__dirname,
        "fixtures/TaskDraftPrivacyDecisionM13e.cjs"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,
        "services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.doesNotMatch(own,/\b(?:fs\.|writeFile|openSync|renameSync|unlinkSync|rmSync|spawnSync|setTimeout|FileView|Process\s*\{)/);
    assert.doesNotMatch(store+shell,/TaskDraftPrivacyDecisionM13e/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const flag of ["ticketProducerEnabled","guardedWriterEnabled",
        "independentlyAuthenticatedTicketReceipt"])
        assert.match(store,new RegExp("readonly property bool "+flag+":\\s*false"));
});
