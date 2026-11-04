#!/usr/bin/env node
"use strict";
// M13s read-only live editor metadata. No task strings, data paths or keys.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const get=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const policy={};
vm.runInNewContext(get("widgets/tasks/TaskDraftPresencePolicyM13s.js")
    .replace(/^\.pragma library\s*/m,""),policy,{timeout:1000});
const blank={
    entryDirty:false,detailsDirty:false,
    entrySavePending:false,detailsSavePending:false,
    sourceState:"ready"
};
function powerless(v){
    for(const flag of ["draftContentRead","draftContentShared","encrypted",
        "checkpointPresent","captureEnabled","keyReleaseAuthorized",
        "restoreAuthorized","writeAuthorized"])
        assert.equal(v[flag],false,flag);
}
test("both monitored editors clean does NOT imply unmonitored editors clean",()=>{
    const v=policy.view(blank);
    assert.equal(v.status,"NO UNSAVED CHANGES IN MONITORED EDITORS");
    assert.match(v.otherScope,/PROJECT \/ PLANNER EDITORS \/\/ NOT INSPECTED/);
    assert.match(v.sourceStatus,/REVISION NOT VERIFIED/);
    assert.equal(v.recoveryStatus,"ENCRYPTED RECOVERY // OFF");
    powerless(v);
});
test("unsaved text in entry or details shows honest unsaved status, not backup",()=>{
    for(const key of ["entryDirty","detailsDirty"]){
        const v=policy.view({...blank,[key]:true});
        assert.equal(v.status,"UNSAVED EDITOR CHANGE // OBSERVED");
        assert.match(v.explanation,/NOT encrypted or recoverable/);
        assert.equal(v.checkpointPresent,false);
        powerless(v);
    }
});
test("save in flight is not marked confirmed, even when editors also dirty",()=>{
    for(const key of ["entrySavePending","detailsSavePending"]){
        const v=policy.view({...blank,[key]:true,entryDirty:true});
        assert.equal(v.status,"EDITOR SAVE // PENDING / NOT CONFIRMED");
        powerless(v);
    }
});
test("missing/injected data cannot make a false clean or reveal raw input",()=>{
    for(const x of [
        null, {}, {entryDirty:"false"},
        {...blank,detailsDirty:null},
        {...blank,entrySavePending:0},
        {...blank,detailsSavePending:"true"}
    ]){
        const v=policy.view(x);
        assert.equal(v.status,"EDITOR STATUS // NOT VERIFIED");
        powerless(v);
    }
    const v=policy.view({...blank,sourceState:"SECRET_TASK_VALUE"});
    assert.equal(v.sourceStatus,"SOURCE // UNVERIFIED");
    assert.equal(JSON.stringify(v).includes("SECRET_TASK_VALUE"),false);
    powerless(v);
});
test("all known source statuses are bounded and never create a revision claim",()=>{
    for(const name of ["ready","empty","saving","loading","error","unsupported"]){
        const v=policy.view({...blank,sourceState:name});
        assert.ok(v.sourceStatus.startsWith("SOURCE //"));
        assert.equal(v.keyReleaseAuthorized,false);
        powerless(v);
    }
    assert.match(policy.view({...blank,sourceState:"saving"}).sourceStatus,
        /NOT CONFIRMED/);
});
test("existing Hub task editor exposes only derived boolean, not text value",()=>{
    const hub=get("widgets/hub/ApolloHubTodoMini.qml");
    const tasks=get("widgets/TasksW.qml");
    const details=get("widgets/tasks/TaskDetailsPane.qml");
    assert.match(hub,/readonly property bool unsavedLocalEntryDraft:/);
    assert.match(hub,/if \(pendingWriteKind !== ""\)/);
    assert.match(hub,/return entryInput\.text !== String\(entries\[i\]\.title \|\| ""\)/);
    assert.match(tasks,/entryDirty: taskEditor\.unsavedLocalEntryDraft/);
    assert.match(tasks,/detailsDirty: taskDetails\.dirty/);
    assert.match(tasks,/entrySavePending: taskEditor\.pendingWriteKind !== ""/);
    assert.match(tasks,/detailsSavePending: taskDetails\.pendingWrite/);
    assert.match(tasks,/sourceState: ApolloHubTodoStore\.storageState/);
    assert.match(details,/readonly property bool dirty:/);
    assert.match(details,/property bool pendingWrite: false/);
    assert.doesNotMatch(tasks,/editorSignals:[\s\S]{0,500}entryInput\.text/);
    assert.doesNotMatch(tasks,/editorSignals:[\s\S]{0,500}descriptionInput\.text/);
});
test("recovery receives only booleans, displays warning and never captures",()=>{
    const sync=get("widgets/tasks/TaskSyncConnectionsPane.qml");
    const recovery=get("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    const model=get("widgets/tasks/TaskDraftPresencePolicyM13s.js");
    assert.match(sync,/property var editorSignals: null/);
    assert.match(sync,/editorSignals: syncConnections\.editorSignals/);
    assert.match(recovery,/property var editorSignals: null/);
    assert.match(recovery,/DraftPresencePolicy\.view\(editorSignals\)/);
    assert.match(recovery,/draftReport\.status/);
    assert.match(recovery,/draftReport\.sourceStatus/);
    assert.match(recovery,/draftReport\.otherScope/);
    assert.match(recovery,/RECOVERY PERMISSIONS \/\/ NOT ACTIVE/);
    for(const text of [recovery,model]){
        for(const bad of ["FileView {","Process {","secret-tool",
            "TaskEncryptedDraftHostM13k","ApolloHubTodoStore.stage(",
            "ApolloHubTodoStore.addTask(","Qt.openUrlExternally("])
            assert.equal(text.includes(bad),false,bad);
    }
    assert.equal((get("services/hub/ApolloHubTodoStore.qml")
        .match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((get("services/hub/ApolloHubTodoStore.qml")
        .match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
});
