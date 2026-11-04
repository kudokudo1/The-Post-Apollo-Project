#!/usr/bin/env node
"use strict";
// M13l CI tests use ONLY a synthetic copied source tree. Never launch real QS.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const cp=require("node:child_process");
const ROOT=path.resolve(__dirname,"../..");
const SCRIPT=path.join(ROOT,"tests/tasks/tools/task_m13l_native_ipc.sh");
const files=[
    "services/hub/qmldir",
    "services/hub/TaskEncryptedDraftHostBridgeM13k.qml",
    "TaskEncryptedDraftAutoHarnessM13l.qml",
    "tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs",
    "tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs",
    "tests/tasks/fixtures/TaskEncryptedRecoveryM13f.cjs"
];
function fixture(t) {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"postapollo-m13l-ci-"));
    t.after(()=>fs.rmSync(temp,{recursive:true,force:true}));
    const root=path.join(temp,"source");
    for(const f of files) {
        fs.mkdirSync(path.dirname(path.join(root,f)),{recursive:true});
        fs.copyFileSync(path.join(ROOT,f),path.join(root,f));
    }
    return {temp,root};
}
function run(mode,root,env) {
    return cp.spawnSync("bash",[SCRIPT,mode,root],{
        encoding:"utf8",timeout:6000,maxBuffer:8192,
        env:{...process.env,...env}
    });
}
test("reviewed files and module accept pure read-only preflight",t=>{
    const {root}=fixture(t);
    const r=run("--preflight",root);
    assert.equal(r.status,0,r.stdout+"\n"+r.stderr);
    assert.equal(r.stdout.trim(),"M13L_REVIEWED_SOURCE_READY");
    assert.equal(r.stderr,"");
});
test("missing module entry and absent fixture fail without modifying root",t=>{
    const {root}=fixture(t);
    const module=path.join(root,"services/hub/qmldir");
    const original=fs.readFileSync(module,"utf8");
    fs.writeFileSync(module,original.replace(
        "TaskEncryptedDraftHostBridgeM13k 1.0 TaskEncryptedDraftHostBridgeM13k.qml\n",""));
    let r=run("--preflight",root);
    assert.equal(r.status,2);
    assert.match(r.stdout,/M13L_REFUSED_MODULE_TYPE/);
    fs.writeFileSync(module,original);
    fs.unlinkSync(path.join(root,"tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs"));
    r=run("--preflight",root);
    assert.equal(r.status,2);
    assert.match(r.stdout,/M13L_REFUSED_MISSING_OR_SYMLINK_SOURCE/);
});
test("edited native harness cannot be executed or preflighted",t=>{
    const {root}=fixture(t);
    const scene=path.join(root,"TaskEncryptedDraftAutoHarnessM13l.qml");
    fs.appendFileSync(scene,"\n// not reviewed\n");
    const r=run("--preflight",root);
    assert.equal(r.status,2);
    assert.equal(r.stdout.trim(),"M13L_REFUSED_UNREVIEWED_SOURCE");
});
test("direct inside-private-test cannot use user's session bus",t=>{
    const {root,temp}=fixture(t);
    const bin=path.join(temp,"bin");
    fs.mkdirSync(bin);
    // Only stubs of *tool existence* for the refusal path, not operations.
    for(const name of ["gnome-keyring-daemon","secret-tool","quickshell"]) {
        const file=path.join(bin,name);
        fs.writeFileSync(file,"#!/bin/sh\nexit 99\n");
        fs.chmodSync(file,0o700);
    }
    const r=run("--inside-private-test",root,{
        PATH:bin+":"+process.env.PATH,
        M13L_PRIVATE_DRIVER:"1",
        DBUS_SESSION_BUS_ADDRESS:"unix:path=/run/user/1000/bus"
    });
    assert.equal(r.status,2,r.stdout+"\n"+r.stderr);
    assert.match(r.stdout,/M13L_REFUSED_NONPRIVATE_BUS/);
});
test("Bash syntax valid and native runner changes only disposable HOME",()=>{
    const r=cp.spawnSync("bash",["-n",SCRIPT],{encoding:"utf8"});
    assert.equal(r.status,0,r.stderr);
    const src=fs.readFileSync(SCRIPT,"utf8");
    assert.match(src,/--inside-private-test/);
    assert.match(src,/dbus-run-session --/);
    assert.match(src,/gnome-keyring-daemon --unlock --components=secrets/);
    assert.match(src,/postapollo-m13g-m13k-XXXXXXXX/);
    assert.match(src,/git hash-object -- "\$qml"/);
    assert.match(src,/git hash-object -- "\$scene"/);
    assert.match(src,/timeout --signal=TERM/);
    assert.match(src,/M13L_NATIVE_QML_IPC_AND_CLEANUP_PASS/);
    assert.match(src,/M13L_NATIVE_DIAGNOSTIC_COMPLETE/);
    assert.match(src,/M13L_OBSERVED_QML_LOADED/);
    assert.match(src,/M13L_QML_INTERNAL_TIMER_EXPIRED/);
    assert.match(src,/M13L_HOST_ENCRYPT_REFUSED/);
    assert.match(src,/M13L_HOST_REOPEN_REFUSED/);
    assert.match(src,/M13L_PRIVATE_SECRET_SERVICE_OWNER_UNVERIFIED/);
    assert.match(src,/org\.freedesktop\.DBus\.NameHasOwner/);
    assert.match(src,/owner_verified/);
    assert.match(src,/M13L_QML_PASS_MARKER_MISSING/);
    assert.doesNotMatch(src,/git\s+(?:pull|checkout|reset|clean|switch|rebase)\b/);
    assert.doesNotMatch(src,/quickshell\s+-p\s+.*shell\.qml/);
    assert.doesNotMatch(src,/pkill|killall|systemctl|sudo\s+/);
});
test("standalone QML harness only invokes dormant synthetic IPC; never real TASKS",()=>{
    const q=fs.readFileSync(path.join(ROOT,"TaskEncryptedDraftAutoHarnessM13l.qml"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    assert.match(q,/TaskEncryptedDraftHostBridgeM13k\s*\{/);
    assert.match(q,/bridge\.startSynthetic\(\)/);
    assert.match(q,/M13L_NATIVE_QML_IPC_PASS/);
    assert.match(q,/Qt\.quit\(\)/);
    for(const phase of ["M13L_PHASE_QML_COMPONENT_LOADED",
        "M13L_PHASE_START_ATTEMPT","M13L_PHASE_PROCESS_START_ACCEPTED",
        "M13L_PHASE_REPLY_PARSED","M13L_PHASE_BRIDGE_SETTLED",
        "M13L_PHASE_QML_TIMER_EXPIRED"])
        assert.ok(q.includes(phase),"Missing bounded QML diagnostic: "+phase);
    assert.doesNotMatch(q,/ApolloHubTodoStore\s*\{|FileView\s*\{|setText\(|secret-tool/);
    assert.doesNotMatch(fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8"),
        /TaskEncryptedDraftAutoHarnessM13l/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const gate of ["ticketProducerEnabled","guardedWriterEnabled",
        "encryptedRecoveryEnabled","encryptedDraftHostEnabled"])
        assert.match(store,new RegExp("readonly property bool "+gate+":\\s*false"));
});
