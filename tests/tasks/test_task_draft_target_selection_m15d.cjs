#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const context=vm.createContext({});
vm.runInContext(read("widgets/tasks/TaskDraftTargetPolicyM15d.js")
    .replace(/^\.pragma library\s*/,""),context,{timeout:1000});
const P=context;
const blank={entryDirty:false,detailsDirty:false,
    entrySavePending:false,detailsSavePending:false,sourceState:"ready"};
function noPowers(report){
    for(const key of [
      "targetIdentityVerified","realSourceRevisionVerified",
      "encryptedStorageAuthorized","consentAuthenticated",
      "keyReleaseAuthorized","captureAuthorized","previewAuthorized",
      "draftClearingAuthorized","sourceWriteAuthorized","taskTextRead",
      "taskTextTransferred","checkpointCreated"
    ])assert.equal(report[key],false,key);
    for(const hidden of [
        "taskId","draftText","entryTitle","description","savedTask",
        "sourcePath","key","secret","sourceHash","envelope"
    ])assert.equal(Object.hasOwn(report,hidden),false,hidden);
    assert.equal(report.captureStatus,"ENCRYPTED CAPTURE // NOT AUTHORIZED");
    assert.match(report.scopeLabel,/PLANNER \/ PROJECTS NOT INSPECTED/);
}
test("no source or invalid schema refuses selection without echo",()=>{
    for(const candidate of [
        null,{},[],{...blank,entryDirty:"true"},
        {...blank,detailsDirty:null},{...blank,entrySavePending:1},
        {...blank,detailsSavePending:"false"},
        {...blank,sourceState:"SECRET"},
        {...blank,description:"VERY_PRIVATE_TEXT"},
        {...blank,taskId:"t-00001"},
        {...blank,credential:"SECRET_TOKEN"}
    ]){
        const report=P.view(candidate,"entry");
        assert.equal(report.state,"UNVERIFIED");
        assert.equal(report.selectedTarget,"none");
        assert.equal(report.entryAvailable,false);
        assert.equal(report.detailsAvailable,false);
        assert.ok(!JSON.stringify(report).includes("VERY_PRIVATE"));
        assert.ok(!JSON.stringify(report).includes("SECRET_TOKEN"));
        noPowers(report);
    }
});
test("empty editor and one-dirty editor require explicit intent",()=>{
    const empty=P.view(blank,"none");
    assert.equal(empty.state,"NO_UNSAVED_EDITOR");
    assert.equal(empty.selectedTarget,"none");
    noPowers(empty);
    for(const target of ["entry","details"]){
        const dirty={...blank,[target==="entry"?"entryDirty":"detailsDirty"]:true};
        const observed=P.view(dirty,"none");
        assert.equal(observed.state,"CHOOSE_EDITOR");
        assert.equal(observed.selectedTarget,"none");
        assert.equal(observed[target+"Available"],true);
        const chosen=P.view(dirty,target);
        assert.equal(chosen.state,target==="entry"?"ENTRY_SELECTED":"DETAILS_SELECTED");
        assert.equal(chosen.selectedTarget,target);
        assert.equal(chosen.captureAuthorized,false);
        noPowers(chosen);
    }
});
test("two simultaneous dirty drafts never combine or auto-select",()=>{
    const both={...blank,entryDirty:true,detailsDirty:true};
    const pending=P.view(both,"none");
    assert.equal(pending.state,"BOTH_DIRTY_CHOOSE_ONE");
    assert.equal(pending.entryAvailable,true);
    assert.equal(pending.detailsAvailable,true);
    assert.equal(pending.selectedTarget,"none");
    for(const target of ["entry","details"]){
        const report=P.view(both,target);
        assert.equal(report.selectedTarget,target);
        assert.ok(report.state.endsWith("_SELECTED"));
        noPowers(report);
    }
    assert.equal(P.view(both,"unknown").selectedTarget,"none");
});
test("pending save and invalid source prevent selecting an editor",()=>{
    for(const status of ["saving","loading","error","unsupported"]){
        const r=P.view({...blank,sourceState:status,entryDirty:true},"entry");
        assert.equal(r.entryAvailable,false);
        assert.equal(r.detailsAvailable,false);
        assert.match(r.state,/SAVE_IN_PROGRESS|SOURCE_REVIEW_REQUIRED/);
        noPowers(r);
    }
    for(const prop of ["entrySavePending","detailsSavePending"]){
        const r=P.view({...blank,entryDirty:true,[prop]:true},"entry");
        assert.equal(r.state,"SAVE_IN_PROGRESS");
        assert.equal(r.entryAvailable,false);
        assert.equal(r.detailsAvailable,false);
        noPowers(r);
    }
});
test("selected editor becomes stale when draft is cleaned",()=>{
    const r=P.view(blank,"details");
    assert.equal(r.state,"SELECTED_EDITOR_CLEAN");
    assert.equal(r.selectedTarget,"details");
    assert.equal(r.detailsAvailable,false);
    noPowers(r);
    const v=P.view({...blank,detailsDirty:true,sourceState:"empty"},"details");
    assert.equal(v.state,"DETAILS_SELECTED");
    assert.match(v.sourceStatus,/REVISION UNVERIFIED/);
    noPowers(v);
});
test("M15d mounted only on existing recovery path, no payload transport",()=>{
    const qml=read("widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml");
    const parent=read("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    const app=read("widgets/TasksW.qml");
    const presence=read("widgets/tasks/TaskDraftPresencePolicyM13s.js");
    const store=read("services/hub/ApolloHubTodoStore.qml");
    const broker=read("services/connections/ConnectionsBroker.qml");
    assert.match(qml,/import "TaskDraftTargetPolicyM15d.js" as DraftTargetPolicy/);
    assert.match(qml,/DraftTargetPolicy\.view\(editorSignals, selectedDraftTarget\)/);
    assert.match(qml,/property var editorSignals: null/);
    assert.match(qml,/selectedDraftTarget: "none"/);
    assert.match(parent,/editorSignals: recoveryStatus\.editorSignals/);
    assert.match(app,/entryDirty: taskEditor\.unsavedLocalEntryDraft/);
    assert.match(app,/detailsDirty: taskDetails\.dirty/);
    assert.match(app,/entrySavePending: taskEditor\.pendingWriteKind !== ""/);
    assert.match(app,/detailsSavePending: taskDetails\.pendingWrite/);
    assert.match(app,/sourceState: ApolloHubTodoStore\.storageState/);
    assert.match(presence,/draftContentShared: false/);
    assert.match(qml,/interactive: modelData\.id === "none"/);
    assert.match(qml,/label:"NEW \/ RENAME"/);
    assert.match(qml,/label:"DETAILS"/);
    assert.match(qml,/access\.selectedDraftTarget = modelData\.id/);
    assert.match(qml,/available: false/);
    assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.doesNotMatch(parent,/ConnectionsBroker\.(?:requirement|authorize)\(/);
});
test("new selector has no network, file, host, credential or plaintext actor",()=>{
    for(const file of [
        "widgets/tasks/TaskDraftTargetPolicyM15d.js",
        "widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml"
    ]){
        const code=read(file);
        for(const forbidden of [
            "Process {","FileView {","Timer {","Settings {",
            "ConnectionsBroker.authorize(","secret-tool","crypto.",
            "Qt.openUrlExternally","XMLHttpRequest","localStorage",
            "descriptionInput.text","entryInput.text","TaskEncryptedDraftPrivateBridgeM15b",
            "TaskRecoveryConsentSourceM13t", "TaskEncryptedDraftHostM13k",
            ".setText(", ".write(", ".reload("
        ])assert.ok(!code.includes(forbidden),file+" has "+forbidden);
    }
});
