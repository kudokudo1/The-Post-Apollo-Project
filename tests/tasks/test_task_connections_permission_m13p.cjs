#!/usr/bin/env node
"use strict";
// M13p: display and fake review only. No host/OS/keyring/user data touched.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const m=require("./fixtures/TaskDraftConnectionsPermissionM13p.cjs");
const ROOT=path.resolve(__dirname,"../..");
const capture="tasks.draft.capture.encrypted";
const preview="tasks.draft.preview.unlocked";
const clear="tasks.draft.clear.encrypted";
const fake=scope=>({scope,requestId:"FAKE_REQUEST_000001",
    startedAtMs:1000,ttlMs:30000});
function noPower(v){
    for(const k of Object.keys(m.NO_POWER)){
        assert.equal(m.NO_POWER[k],false,k);
        assert.equal(v[k],false,k);
    }
    assert.equal(v.keyReleaseAuthorized,false);
    assert.equal(v.canWriteTaskSource,false);
    assert.equal(v.realGrantActive,false);
}
test("exact TASKS scopes use the Connections broker, distinct consent and default OFF",()=>{
    const r=[m.requirement(capture),m.requirement(preview),m.requirement(clear)];
    for(const x of r){
        assert.equal(x.ok,true,x.status);
        assert.equal(x.feature,"tasks-draft-recovery");
        assert.equal(x.providerOwner,"connections-broker");
        assert.equal(x.consumerOwner,"tasks");
        assert.equal(x.settingsLocation,"CPU++ / SETTINGS / CONNECTIONS");
        assert.equal(x.taskLocation,"TASKS / RECOVERY");
        assert.equal(x.defaultOptIn,false);
        assert.equal(x.defaultNetworkSync,false);
        noPower(x);
    }
    assert.equal(new Set(r.map(x=>x.scope)).size,3);
    assert.equal(r[0].requires,"EXPLICIT_TASKS_OPT_IN_AND_TRUSTED_HOST");
    assert.equal(r[1].requires,"SEPARATE_UNLOCK_AND_EDITOR_REVIEW");
    assert.equal(r[2].requires,"EXPLICIT_DELETION_AND_FRESH_SOURCE_REVIEW");
});
test("arbitrary provider, account, wildcard or caller-supplied operation never grants",()=>{
    for(const scope of ["*","mail.read","fires.hotspots.read",
            "tasks.draft.restore.source","tasks.draft.*","","TASKS",
            "__proto__",null,{},["tasks.draft.capture.encrypted"]]){
        const x=m.requirement(scope);
        assert.equal(x.ok,false);
        assert.equal(x.status,"UNREGISTERED_TASKS_SCOPE");
        noPower(x);
    }
    for(const v of [
        {feature:"tasks-draft-recovery",scope:capture,surface:"TASKS",account:"admin"},
        {feature:"tasks-draft-recovery",scope:capture,surface:"TASKS",approved:true},
        {feature:"tasks-draft-recovery",scope:preview,surface:"SOCIAL"},
        {feature:"proton-mail",scope:capture,surface:"TASKS"},
        {feature:"tasks-draft-recovery",scope:capture}
    ]){
        const x=m.reviewRequest(v);
        assert.equal(x.ok,false);
        noPower(x);
    }
});
test("keyring service acquisition remains availability-only and never unlocked",()=>{
    const statuses=["SERVICE_ACQUIRED","SERVICE_NOT_RUNNING",
        "SESSION_BUS_UNAVAILABLE","DBUS_PROBE_TOOL_MISSING",
        "UNEXPECTED_DBUS_RESPONSE","",null];
    for(const status of statuses){
        const v=m.providerStatus({status,unlocked:true,grantActive:true});
        assert.equal(v.ok,true);
        assert.equal(v.keyringPresent,status==="SERVICE_ACQUIRED");
        assert.equal(v.grantEnabled,false);
        assert.equal(v.canApprove,false);
        assert.equal(v.keyringUnlocked,false);
        noPower(v);
    }
    const spoof=m.providerStatus({status:"SERVICE_ACQUIRED",
        hostAuthenticated:true,keyReleaseAuthorized:true});
    assert.equal(spoof.keyringPresent,true);
    noPower(spoof);
});
test("UI review intent is display only even after a user clicks approval",()=>{
    for(const scope of [capture,preview,clear]){
        const input={feature:"tasks-draft-recovery",scope,surface:"TASKS"};
        const x=m.reviewRequest(input);
        assert.equal(x.ok,true);
        assert.equal(x.status,"REVIEW_DISPLAY_ONLY_HOST_NOT_CONNECTED");
        assert.equal(x.canApprove,false);
        assert.equal(x.disposition,"NO_SESSION_OR_KEY_ACCESS");
        assert.deepEqual(x.request,input);
        noPower(x);
        const result=m.brokerDecision(input);
        assert.equal(result.ok,false);
        assert.equal(result.status,"TRUSTED_HOST_APPROVAL_NOT_CONNECTED");
        noPower(result);
    }
});
test("fake review can acknowledge but that has no real credential authority",()=>{
    const start=m.createFakeReview(fake(capture));
    assert.equal(start.ok,true,start.status);
    assert.equal(start.fakeState.state,"PENDING");
    noPower(start);
    const approved=m.advanceFakeReview({
        fakeState:start.fakeState,event:"ACKNOWLEDGE",nowMs:1001});
    assert.equal(approved.ok,true,approved.status);
    assert.equal(approved.fakeState.state,"APPROVED");
    assert.equal(approved.simulatedAcknowledged,true);
    noPower(approved);
    const displayed=m.displayFakeState(approved.fakeState);
    assert.equal(displayed.ok,true,displayed.status);
    assert.equal(displayed.phase,"APPROVED");
    assert.equal(displayed.status,"SIMULATED_NOT_AUTHORIZED");
    assert.equal(Object.hasOwn(displayed,"requestId"),false);
    noPower(displayed);
    const revoked=m.advanceFakeReview({
        fakeState:approved.fakeState,event:"REVOKE",nowMs:1002});
    assert.equal(revoked.ok,true);
    assert.equal(revoked.fakeState.state,"REVOKED");
    noPower(revoked);
    const replay=m.advanceFakeReview({
        fakeState:revoked.fakeState,event:"ACKNOWLEDGE",nowMs:1003});
    assert.equal(replay.ok,false);
    assert.equal(replay.status,"SIMULATED_TERMINAL_REVIEW");
    noPower(replay);
});
test("fake denial, cancellation, expiry and timeout always fail closed",()=>{
    for(const event of ["DENY","CANCEL"]){
        const started=m.createFakeReview(fake(clear));
        const step=m.advanceFakeReview({
            fakeState:started.fakeState,event,nowMs:1001});
        assert.equal(step.ok,true);
        assert.equal(step.fakeState.state,event==="DENY"?"DENIED":"CANCELLED");
        noPower(step);
        const again=m.advanceFakeReview({
            fakeState:step.fakeState,event:"ACKNOWLEDGE",nowMs:1002});
        assert.equal(again.ok,false);
        noPower(again);
    }
    const st=m.createFakeReview(fake(preview));
    const expired=m.advanceFakeReview({
        fakeState:st.fakeState,event:"ACKNOWLEDGE",nowMs:31000});
    assert.equal(expired.fakeState.state,"EXPIRED");
    assert.equal(expired.simulatedAcknowledged,false);
    noPower(expired);
    const malformed=m.advanceFakeReview({
        fakeState:st.fakeState,event:"ACKNOWLEDGE",nowMs:900});
    assert.equal(malformed.ok,false);
    noPower(malformed);
});
test("rejects invented request IDs, limits TTL and refuses forged status schemas",()=>{
    for(const requestId of ["TRUE","FAKE_A","", "FAKE_"+"A".repeat(60)]){
        const out=m.createFakeReview({...fake(capture),requestId});
        assert.equal(out.ok,false);
        noPower(out);
    }
    for(const ttlMs of [0,-1,300001,1.5,Number.MAX_SAFE_INTEGER]){
        const out=m.createFakeReview({...fake(preview),ttlMs});
        assert.equal(out.ok,false);
        noPower(out);
    }
    const fresh=m.createFakeReview(fake(capture)).fakeState;
    for(const s of [
        {...fresh,kind:"M13P_REAL_REVIEW"},
        {...fresh,state:"APPROVED",reason:"AWAITING_FAKE_REVIEW"},
        {...fresh,secret:"not-allowed"},
        {...fresh,requestId:"real-session"},
        {...fresh,scope:"mail.modify"}
    ]){
        const o=m.displayFakeState(s);
        assert.equal(o.ok,false);
        noPower(o);
    }
});
test("M13p remains disconnected from live QML and shared C2 grant gate remains closed",()=>{
    const src=fs.readFileSync(path.join(ROOT,
        "tests/tasks/fixtures/TaskDraftConnectionsPermissionM13p.cjs"),"utf8");
    const todo=fs.readFileSync(path.join(ROOT,
        "services/hub/ApolloHubTodoStore.qml"),"utf8");
    const broker=fs.readFileSync(path.join(ROOT,
        "services/connections/ConnectionsBroker.qml"),"utf8");
    const policy=fs.readFileSync(path.join(ROOT,
        "services/connections/ConnectionsBrokerPolicy.js"),"utf8");
    const cpu=fs.readFileSync(path.join(ROOT,"widgets/CpuPlusW.qml"),"utf8");
    assert.doesNotMatch(src,/require\("node:(?:fs|child_process)"\)/);
    assert.doesNotMatch(src,/secret-tool|gnome-keyring|Quickshell\.env|\.writeFile|\.setText\(/);
    assert.match(src,/productionActivation:false/);
    assert.match(src,/keyReleaseAuthorized:false/);
    assert.match(src,/canWriteTaskSource:false/);
    assert.doesNotMatch(todo,/TaskDraftConnectionsPermissionM13p/);
    assert.doesNotMatch(broker,/TaskDraftConnectionsPermissionM13p/);
    assert.doesNotMatch(cpu,/TaskDraftConnectionsPermissionM13p/);
    assert.equal((todo.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((todo.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    assert.match(policy,/return \{allowed:false,reason:"TRUSTED_BROKER_NOT_ACTIVATED"\}/);
    assert.match(cpu,/\{ name: "CONNECTIONS", key: "CONNECTIONS"/);
    for(const flag of ["encryptedRecoveryEnabled",
        "encryptedRecoveryStorageAuthorized","encryptedRecoveryUnlockAuthorized",
        "encryptedDraftHostEnabled"]){
        assert.match(todo,new RegExp("readonly property bool "+flag+":\\s*false"));
    }
});
