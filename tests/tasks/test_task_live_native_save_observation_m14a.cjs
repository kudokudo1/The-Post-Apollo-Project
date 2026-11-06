#!/usr/bin/env node
"use strict";
/* TASKS M14a: live native callback observation without save authority. */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const get=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const policySource=get("widgets/tasks/TaskLiveNativeSavePolicyM14a.js");
const policy={};
vm.runInNewContext(policySource.replace(/^\.pragma library\s*/,""),policy,{timeout:1000});
const phases=[
  "NOT_OBSERVED","WRITE_REQUESTED","FILEVIEW_SAVED_HINT",
  "UNATTRIBUTED_SAVED_HINT","FILEVIEW_SAVE_FAILED"
];
const sourceStates=["ready","empty","saving","loading","error","unsupported"];
function packet(phase="NOT_OBSERVED",requestCount=0,sourceState="ready"){
    return {phase,requestCount,sourceState};
}
function powerless(r){
    for(const key of [
        "realSavedSourceVerified","nativeCallbackAuthenticated",
        "sourceOwnerAuthenticated","durableUserSaveAcknowledged",
        "savedBytesReadbackVerified","encryptedRecoveryEnabled",
        "canReplay","canWriteTasks","canClearDraft","canCapture",
        "canPreview","canRestore","keyReleaseAuthorized"
    ])assert.equal(r[key],false,key);
    assert.equal(r.draftDisposition,"KEEP UNSAVED DRAFT");
    assert.equal(r.lastConfirmedDisplay,"KEEP LAST CONFIRMED VIEW");
    assert.match(r.proof,/NOT VERIFIED/);
    for(const k of ["taskId","draft","filename","sourceHash",
                    "sourcePath","receipt","ticketId","errorText"])
        assert.equal(Object.hasOwn(r,k),false,k);
}
test("real native callback states are informative but never prove a save",()=>{
    for(const phase of phases){
        const count=phase==="NOT_OBSERVED"?0:1;
        const output=policy.view(packet(phase,count));
        assert.equal(output.origin,"LIVE FILEVIEW SIGNAL // APPLICATION MEMORY ONLY");
        assert.equal(output.requestedCount,count);
        assert.ok(output.status.includes("NATIVE SAVE //"));
        assert.ok(output.explanation.length>50);
        powerless(output);
    }
    const saved=policy.view(packet("FILEVIEW_SAVED_HINT",1,"ready"));
    assert.match(saved.status,/UNVERIFIED/);
    assert.match(saved.explanation,/not independent readback/);
    assert.equal(saved.nativeCallbackAuthenticated,false);
    assert.equal(saved.durableUserSaveAcknowledged,false);
});
test("source states are from finite enums, never a claimed verified revision",()=>{
    for(const state of sourceStates){
        const result=policy.view(packet("WRITE_REQUESTED",3,state));
        assert.match(result.sourceStatus,/SOURCE \/\//);
        assert.doesNotMatch(result.sourceStatus,/AUTHENTICATED|DURABLE|CONFIRMED SAVE/);
        powerless(result);
    }
});
test("unrelated callback with zero requests is conservatively unattributed",()=>{
    const result=policy.view(packet("FILEVIEW_SAVED_HINT",0));
    assert.match(result.status,/UNATTRIBUTED/);
    powerless(result);
});
test("untrusted error payloads and unknown states produce no source proof",()=>{
    const sample=packet("FILEVIEW_SAVED_HINT",1);
    for(const input of [
        null,undefined,{},true,[],packet("CONFIRMED",1),
        packet("FILEVIEW_SAVED_HINT",-1),packet("FILEVIEW_SAVED_HINT",1.7),
        packet("FILEVIEW_SAVED_HINT",1000001),packet("FILEVIEW_SAVED_HINT","1"),
        packet("FILEVIEW_SAVED_HINT",NaN),packet("FILEVIEW_SAVED_HINT",Infinity),
        packet("FILEVIEW_SAVED_HINT",1,"SAVED"),
        {...sample,savedAcknowledged:true},
        {...sample,authenticted:true},
        {...sample,raw:"PRIVATE_TASK_TEXT"},
        {...sample,sourceHash:"a".repeat(64)},
    ]){
        const output=policy.view(input);
        assert.equal(output.status,"NATIVE SAVE // OBSERVATION UNVERIFIED");
        assert.equal(output.sourceStatus,"SOURCE // UNVERIFIED");
        assert.equal(JSON.stringify(output).includes("PRIVATE_TASK_TEXT"),false);
        powerless(output);
    }
});
test("production writer increments attempt in existing stage and observes callbacks",()=>{
    const store=get("services/hub/ApolloHubTodoStore.qml");
    assert.match(store,/property string nativeSaveEventM14a: "NOT_OBSERVED"/);
    assert.match(store,/property int nativeSaveRequestsM14a: 0/);
    assert.match(store,/readonly property var nativeSaveObservationM14a:/);
    assert.match(store,/phase: nativeSaveEventM14a/);
    assert.match(store,/requestCount: nativeSaveRequestsM14a/);
    assert.match(store,/sourceState: storageState/);
    const marker="todo.nativeSaveRequestsM14a = Math.min(1000000,";
    assert.equal(store.split(marker).length-1,1);
    assert.match(store,/todo\.nativeSaveEventM14a = "WRITE_REQUESTED"/);
    assert.match(store,/onSaved: \{[\s\S]*?nativeSaveEventM14a = todo\.storageState === "saving"/);
    assert.match(store,/\? "FILEVIEW_SAVED_HINT" : "UNATTRIBUTED_SAVED_HINT"/);
    assert.match(store,/onSaveFailed: function\(error\) \{[\s\S]*?nativeSaveEventM14a = "FILEVIEW_SAVE_FAILED"/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/atomicWrites: true/);
    assert.match(store,/readonly property bool guardedWriterEnabled: false/);
    assert.match(store,/readonly property bool ticketProducerEnabled: false/);
    assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
});
test("M14a reads the existing live signal but M13z examples still remain separate",()=>{
    const pane=get("widgets/tasks/TaskRecoveryReviewPaneM13z.qml");
    const parent=get("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    const sync=get("widgets/tasks/TaskSyncConnectionsPane.qml");
    assert.match(pane,/TaskLiveNativeSavePolicyM14a\.js/);
    assert.match(pane,/nativeSaveSignals: null/);
    assert.match(pane,/NativeSavePolicy\.view\(nativeSaveSignals\)/);
    assert.match(pane,/LIVE \/\/ NATIVE SAVE SIGNAL/);
    assert.match(pane,/nativeSaveReport\.status/);
    assert.match(pane,/nativeSaveReport\.proof/);
    assert.match(pane,/readonly property bool liveSourceInspectionConnected: false/);
    assert.match(pane,/ReviewPolicy\.current\(\)/);
    assert.match(pane,/ReviewPolicy\.example\(selectedExample\)/);
    assert.match(pane,/POST-CRASH SCENARIOS \/\/ EXAMPLES ONLY/);
    assert.match(parent,/nativeSaveSignals: ApolloHubTodoStore\.nativeSaveObservationM14a/);
    assert.equal((parent.match(/TaskRecoveryReviewPaneM13z\s*\{/g)||[]).length,1);
    assert.match(parent,/DraftPresencePolicy\.view\(editorSignals\)/);
    assert.match(parent,/ConnectionsBroker\.checkAvailability\(\)/);
    assert.equal((sync.match(/TaskRecoveryStatusPaneM13q\s*\{/g)||[]).length,1);
    assert.doesNotMatch(pane,/TaskPostCrashSourceReviewM13y/);
    assert.doesNotMatch(pane,/syntheticResult\(/);
});
test("no new IO and shared Connections stays deny-all",()=>{
    const source=get("widgets/tasks/TaskLiveNativeSavePolicyM14a.js");
    const panel=get("widgets/tasks/TaskRecoveryReviewPaneM13z.qml");
    const store=get("services/hub/ApolloHubTodoStore.qml");
    const broker=get("services/connections/ConnectionsBroker.qml");
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    assert.match(store,/readonly property bool encryptedDraftHostEnabled: false/);
    for(const content of [source,panel])for(const str of [
       "FileView {","Process {","Qt.openUrlExternally","XMLHttpRequest",
       "ApolloHubTodoStore.","ConnectionsBroker.","TaskEncryptedDraft",
       "secret-tool","Settings {","Timer {","Component.onCompleted"
    ])assert.equal(content.includes(str),false,str);
    assert.doesNotMatch(store,/TaskPostCrashSourceReviewM13y/);
    assert.doesNotMatch(broker,/TaskLiveNativeSavePolicyM14a/);
});
