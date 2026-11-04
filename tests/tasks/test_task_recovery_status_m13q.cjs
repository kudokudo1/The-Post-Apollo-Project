#!/usr/bin/env node
"use strict";
// TASKS M13q read-only live C2a presence display; Node runs pure JS only.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const get=p=>fs.readFileSync(path.join(root,p),"utf8");
const file="widgets/tasks/TaskRecoveryStatusPolicyM13q.js";
const policy={};
vm.runInNewContext(get(file).replace(/^\.pragma library\s*/m,""),policy,
    {filename:file,timeout:1000});
const normal={
    providerStatus:"NOT CHECKED",providerChecking:false,
    brokerCredentialActionsEnabled:false,recoveryEnabled:false,
    recoveryStorageAuthorized:false,recoveryUnlockAuthorized:false,
    draftHostEnabled:false,draftHostWriteAuthorized:false
};
function powerless(v){
    for(const k of ["realGrantActive","keyringUnlocked","canCapture",
        "canDecrypt","canPreview","canClear","canRestore","canWriteTasks"])
        assert.equal(v[k],false,k);
    assert.equal(v.statusOnly,true);
}
test("not checked is not an absent keyring, and nothing starts implicitly",()=>{
    const result=policy.view(normal);
    assert.equal(result.providerStatus,"NOT CHECKED");
    assert.equal(result.providerLabel,"KEYRING NOT CHECKED");
    assert.equal(result.providerPresent,false);
    assert.equal(result.recoveryStatus,"RECOVERY // OFF");
    assert.equal(result.checkpointStatus,"ENCRYPTED CHECKPOINT // NOT INSPECTED");
    powerless(result);
});
test("SERVICE_ACQUIRED is presence only, not unlocked or permission",()=>{
    const output=policy.view({...normal,providerStatus:"SERVICE_ACQUIRED"});
    assert.equal(output.providerStatus,"SERVICE_ACQUIRED");
    assert.equal(output.providerLabel,"KEYRING FOUND // UNLOCK UNKNOWN");
    assert.equal(output.providerPresent,true);
    assert.equal(output.recoveryStatus,"RECOVERY // OFF");
    assert.match(output.explanation,/does not prove a key is unlocked/);
    powerless(output);
});
test("known negative statuses and active probe produce truthful bounded labels",()=>{
    const expected={
        "SERVICE_NOT_RUNNING":"KEYRING SERVICE NOT RUNNING",
        "SESSION_BUS_UNAVAILABLE":"SESSION BUS UNAVAILABLE",
        "DBUS_PROBE_TOOL_MISSING":"DBUS PROBE TOOL MISSING",
        "UNEXPECTED_DBUS_RESPONSE":"KEYRING RESPONSE UNVERIFIED",
        "UNVERIFIED":"KEYRING RESPONSE UNVERIFIED"
    };
    for(const [status,label] of Object.entries(expected)){
        const result=policy.view({...normal,providerStatus:status});
        assert.equal(result.providerLabel,label);
        assert.equal(result.providerPresent,false);
        powerless(result);
    }
    const active=policy.view({...normal,
        providerStatus:"SERVICE_ACQUIRED",providerChecking:true});
    assert.equal(active.providerStatus,"CHECKING");
    assert.equal(active.providerLabel,"CHECKING LOCAL KEYRING");
    assert.equal(active.providerPresent,false);
    powerless(active);
});
test("untrusted host strings are never passed to the user interface",()=>{
    for(const status of ["<PRIVATE_SECRET>", "CONNECTED", "AUTHORIZED",
        "SERVICE_ACQUIRED\nREAL KEY", "", null, {}, undefined]) {
        const output=policy.view({...normal,providerStatus:status});
        assert.equal(output.providerStatus,"UNVERIFIED");
        assert.equal(output.providerLabel,"KEYRING STATUS UNVERIFIED");
        assert.equal(output.providerPresent,false);
        assert.equal(JSON.stringify(output).includes("<PRIVATE_SECRET>"),false);
        powerless(output);
    }
});
test("unexpected production flags do not accidentally label recovery as ON",()=>{
    for(const key of ["brokerCredentialActionsEnabled","recoveryEnabled",
        "recoveryStorageAuthorized","recoveryUnlockAuthorized","draftHostEnabled",
        "draftHostWriteAuthorized"]) {
        const output=policy.view({...normal,[key]:true,
            providerStatus:"SERVICE_ACQUIRED"});
        assert.equal(output.recoveryStatus,"RECOVERY // STATE REQUIRES REVIEW");
        assert.equal(output.providerPresent,true);
        powerless(output);
    }
    const omitted=policy.view({});
    assert.equal(omitted.recoveryStatus,"RECOVERY // STATE REQUIRES REVIEW");
    powerless(omitted);
});
test("new QML status pane listens to shared owners but only clicks the presence probe",()=>{
    const qml=get("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    assert.match(qml,/import qs\.services\.connections/);
    assert.match(qml,/import qs\.services\.hub/);
    assert.match(qml,/ConnectionsBroker\.status/);
    assert.match(qml,/ConnectionsBroker\.checking/);
    assert.match(qml,/ConnectionsBroker\.credentialActionsEnabled/);
    assert.match(qml,/ApolloHubTodoStore\.encryptedRecoveryEnabled/);
    assert.match(qml,/ApolloHubTodoStore\.encryptedRecoveryStorageAuthorized/);
    assert.match(qml,/ApolloHubTodoStore\.encryptedRecoveryUnlockAuthorized/);
    assert.match(qml,/ApolloHubTodoStore\.encryptedDraftHostEnabled/);
    assert.match(qml,/ApolloHubTodoStore\.encryptedDraftHostWriteAuthorized/);
    assert.match(qml,/RecoveryStatusPolicy\.view\(/);
    assert.match(qml,/onLeftClicked: ConnectionsBroker\.checkAvailability\(\)/);
    assert.match(qml,/available: !ConnectionsBroker\.checking/);
    assert.match(qml,/READ ONLY \/\/ NO CAPTURE \/\/ NO KEY RELEASE \/\/ NO RESTORE/);
    for(const forbidden of ["FileView {","Process {","Component.onCompleted",
        "Timer {","ConnectionsBroker.authorize(","ConnectionsBroker.requirement(",
        "secret-tool","Quickshell.execDetached(","ApolloHubTodoStore.stage(",
        "ApolloHubTodoStore.addTask(","ApolloHubTodoStore.submit(",
        "TaskEncryptedDraftHostBridgeM13k","TaskEncryptedDraftTransactionM13m"])
        assert.equal(qml.includes(forbidden),false,forbidden);
});
test("recovery is mounted only as a fifth SYNC tab with old Git modes preserved",()=>{
    const pane=get("widgets/tasks/TaskSyncConnectionsPane.qml");
    const tasks=get("widgets/TasksW.qml");
    assert.equal(pane.match(/ModeButton\s*\{/g).length,1);
    assert.equal(pane.match(/TaskRecoveryStatusPaneM13q\s*\{/g).length,1);
    assert.match(pane,/\{id:"recovery", label:"RECOVERY"\}/);
    assert.match(pane,/selectedSubmode === "recovery"/);
    assert.match(pane,/syncConnections\.submodes\.length/);
    assert.equal(pane.match(/\{id:"(?:overview|mappings|review|history|recovery)"/g).length,5);
    for(const tab of ["overview","mappings","review","history"])
        assert.match(pane,new RegExp('visible: syncConnections.selectedSubmode === "'+tab+'"'));
    assert.equal(tasks.match(/TaskSyncConnectionsPane\s*\{/g).length,1);
    assert.equal(tasks.match(/TaskRecoveryStatusPaneM13q\s*\{/g)||[].length,0);
    assert.equal((get("services/hub/ApolloHubTodoStore.qml").match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((get("services/hub/ApolloHubTodoStore.qml").match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
});
test("shared C2 authority remains closed and TASKS activation flags remain false",()=>{
    const b=get("services/connections/ConnectionsBroker.qml");
    const t=get("services/hub/ApolloHubTodoStore.qml");
    const s=get("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    assert.match(b,/readonly property bool credentialActionsEnabled: false/);
    for(const name of ["encryptedRecoveryEnabled",
        "encryptedRecoveryStorageAuthorized","encryptedRecoveryUnlockAuthorized",
        "encryptedDraftHostEnabled","encryptedDraftHostWriteAuthorized"]) {
        assert.match(t,new RegExp("readonly property bool "+name+":\\s*false"));
    }
    assert.equal(s.includes("ConnectionsBroker.authorize"),false);
    assert.equal(s.includes("ConnectionsBroker.checkAvailability()"),true);
});
