#!/usr/bin/env node
"use strict";
// TASKS M15c // live recovery UI has real catalog-read only, never grant.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const ctx=vm.createContext({});
vm.runInContext(read("widgets/tasks/TaskEncryptedDraftAccessPolicyM15c.js")
    .replace(/^\.pragma library\s*/,""),ctx,{timeout:1000});
const Policy=ctx;
const MODES=["capture","preview","clear"];
const SCOPES=[
    "tasks.draft.capture.encrypted",
    "tasks.draft.preview.unlocked",
    "tasks.draft.clear.encrypted"
];
function meta(overrides={}) {
    return {
        providerStatus:"SERVICE_ACQUIRED",
        providerChecking:false,
        credentialActionsEnabled:false,
        brokerKnown:false,
        brokerGrantEnabled:false,
        recoveryEnabled:false,
        storageAuthorized:false,
        unlockAuthorized:false,
        draftHostEnabled:false,
        draftHostWriteAuthorized:false,
        editorStatus:"UNSAVED EDITOR CHANGE // OBSERVED",
        ...overrides
    };
}
function noPower(x) {
    for(const key of [
        "operationAvailable","hostAuthenticated","userConsentAuthenticated",
        "keyReleaseAuthorized","encryptedCaptureAuthorized",
        "encryptedPreviewAuthorized","encryptedClearAuthorized",
        "sourceWriteAuthorized","automaticReplayAuthorized",
        "draftClearAuthorized","realCheckpointInspected",
        "draftTextRead","draftTextTransferred"
    ])assert.equal(x[key],false,key);
    assert.equal(x.draftDisposition,"KEEP UNSAVED DRAFT");
    assert.equal(x.confirmation,"SEPARATE CONFIRMATION REQUIRED");
    for(const forbidden of ["taskId","draft","draftText","sourcePath",
        "key","secret","receipt","requestId","userId","sourceHash"])
        assert.equal(Object.hasOwn(x,forbidden),false,forbidden);
}
test("three scopes match existing M13p and remain independently denied",()=>{
    const prior=read("tests/tasks/fixtures/TaskDraftConnectionsPermissionM13p.cjs");
    for(let i=0;i<MODES.length;i++){
        const out=Policy.view(meta(),MODES[i],true);
        assert.equal(out.scope,SCOPES[i]);
        assert.ok(prior.includes(SCOPES[i]));
        assert.ok(out.title.length>8);
        assert.ok(out.description.length>60);
        assert.match(out.status,/NOT REGISTERED/);
        noPower(out);
    }
    assert.equal(Policy.view(meta(),"untrusted",true).scope,SCOPES[0]);
});
test("readiness preflight is interactive display only, not a consent token",()=>{
    for(const mode of MODES){
        const notInspected=Policy.view(meta(),mode,false);
        assert.equal(notInspected.status,"ACCESS NOT CHECKED");
        assert.match(notInspected.explanation,/CHECK REQUIREMENTS/);
        noPower(notInspected);
        const reviewed=Policy.view(meta(),mode,true);
        assert.equal(reviewed.status,"TASKS CREDENTIAL PROVIDER // NOT REGISTERED");
        assert.equal(reviewed.requiredOwner,"CPU++ // SETTINGS // CONNECTIONS");
        noPower(reviewed);
    }
});
test("keyring found is insufficient even when caller asserts broker registration",()=>{
    for(const status of ["NOT CHECKED","SERVICE_ACQUIRED","SERVICE_NOT_RUNNING",
        "SESSION_BUS_UNAVAILABLE","DBUS_PROBE_TOOL_MISSING",
        "UNEXPECTED_DBUS_RESPONSE","CHECKING"]){
        for(const mode of MODES){
            const input=meta({providerStatus:status,brokerKnown:true});
            const result=Policy.view(input,mode,true);
            noPower(result);
            assert.equal(result.status,"TRUSTED CONSENT + KEY HOST // NOT CONNECTED");
            assert.match(result.explanation,/still disabled/);
        }
    }
});
test("unexpected enabled flags produce review warning, never permitted action",()=>{
    const flags=["credentialActionsEnabled","brokerGrantEnabled",
        "recoveryEnabled","storageAuthorized","unlockAuthorized",
        "draftHostEnabled","draftHostWriteAuthorized"];
    for(const flag of flags){
        const out=Policy.view(meta({[flag]:true}),"preview",true);
        assert.equal(out.status,"UNEXPECTED AUTHORITY STATE // REVIEW REQUIRED",flag);
        noPower(out);
    }
});
test("editor presence is booleans only, never draft text or implicit save",()=>{
    const clean=Policy.view(meta({brokerKnown:true,
        editorStatus:"NO UNSAVED CHANGES IN MONITORED EDITORS"}),"capture",true);
    assert.equal(clean.status,"NO MONITORED UNSAVED DRAFT");
    noPower(clean);
    const unknown=Policy.view(meta({brokerKnown:true,
        editorStatus:"EDITOR STATUS // NOT VERIFIED"}),"capture",true);
    assert.equal(unknown.status,"EDITOR STATUS // NOT VERIFIED");
    noPower(unknown);
    const pending=Policy.view(meta({brokerKnown:true,
        editorStatus:"EDITOR SAVE // PENDING / NOT CONFIRMED"}),"capture",true);
    assert.match(pending.status,/NOT CONNECTED/);
    noPower(pending);
});
test("malformed metadata and injected draft fields fail closed with no echo",()=>{
    const payload=meta();
    for(const candidate of [
        null,undefined,[],true,{},
        {...payload,credentialActionsEnabled:"false"},
        {...payload,brokerKnown:1},
        {...payload,providerStatus:"KEYRING_UNLOCKED"},
        {...payload,editorStatus:"PRIVATE_DRAFT_VALUE"},
        {...payload,draftText:"PRIVATE_DRAFT_VALUE"},
        {...payload,taskId:"private-item"},
        {...payload,key:"FAKE_SECRET"},
        {...payload,providerChecking:null}
    ]){
        const out=Policy.view(candidate,"clear",true);
        assert.equal(out.status,"ACCESS STATE NOT VERIFIED");
        assert.ok(!JSON.stringify(out).includes("PRIVATE_"));
        noPower(out);
    }
});
test("production mount uses existing store/editor metadata only",()=>{
    const qml=read("widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml");
    const parent=read("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    const sync=read("widgets/tasks/TaskSyncConnectionsPane.qml");
    const store=read("services/hub/ApolloHubTodoStore.qml");
    const broker=read("services/connections/ConnectionsBroker.qml");
    assert.equal((parent.match(/TaskEncryptedDraftAccessPaneM15c\s*\{/g)||[]).length,1);
    assert.ok(parent.indexOf("LOCAL EDITORS // UNSAVED CONTENT STATUS")
        <parent.indexOf("TaskEncryptedDraftAccessPaneM15c"));
    assert.ok(parent.indexOf("TaskEncryptedDraftAccessPaneM15c")
        <parent.indexOf("TaskLocalSourceInspectPaneM15a"));
    assert.doesNotMatch(parent,/ConnectionsBroker\.requirement\(/);
    assert.doesNotMatch(parent,/ConnectionsBroker\.authorize\(/);
    assert.match(parent,/brokerKnown: false/);
    assert.match(parent,/brokerGrantEnabled: false/);
    assert.match(parent,/credentialActionsEnabled: ConnectionsBroker\.credentialActionsEnabled/);
    assert.match(parent,/editorStatus: recoveryStatus\.draftReport\.status/);
    assert.match(parent,/recoveryEnabled: ApolloHubTodoStore\.encryptedRecoveryEnabled/);
    assert.match(parent,/draftHostWriteAuthorized: ApolloHubTodoStore\.encryptedDraftHostWriteAuthorized/);
    assert.equal((sync.match(/TaskRecoveryStatusPaneM13q\s*\{/g)||[]).length,1);
    assert.match(qml,/onLeftClicked: access\.requirementsChecked = true/);
    assert.match(qml,/available: false/);
    assert.equal((qml.match(/\bActionButton\s*\{/g)||[]).length,2);
    assert.equal((qml.match(/^\s*onLeftClicked:/gm)||[]).length,1);
    assert.match(qml,/readonly property bool canCaptureDraft: false/);
    assert.match(qml,/readonly property bool canUnlockPreview: false/);
    assert.match(qml,/readonly property bool canDeleteCheckpoint: false/);
    assert.match(qml,/readonly property bool canWriteTaskSource: false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
});
test("no network, subprocess, file actors, fake fixtures or plaintext bridge",()=>{
    const files=["widgets/tasks/TaskEncryptedDraftAccessPaneM15c.qml",
                 "widgets/tasks/TaskEncryptedDraftAccessPolicyM15c.js"];
    for(const f of files){
        const src=read(f);
        for(const bad of [
            "Process {","FileView {","Timer {","Settings {",
            "Component.onCompleted","Qt.openUrlExternally",
            "XMLHttpRequest","secret-tool","ConnectionsBroker.authorize(",
            "TaskEncryptedDraftPrivateBridgeM15b","TaskRecoveryConsentSourceM13t",
            "TaskDraftConnectionsPermissionM13p","TaskEncryptedDraftHostM13k",
            ".setText(",".reload(",".write(","localStorage"
        ])assert.ok(!src.includes(bad),f+" invokes "+bad);
    }
});
