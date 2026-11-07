#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const cp=require("node:child_process");
const ROOT=path.resolve(__dirname,"../..");
const WORKER=path.join(ROOT,"tests/tasks/fixtures/TaskEncryptedDraftPrivateBridgeM15b.cjs");
const RUNNER=path.join(ROOT,"tests/tasks/tools/task_m15b_encrypted_draft_bridge.sh");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
test("direct worker is always refused in a normal app environment",()=>{
    const tmp=fs.mkdtempSync(path.join(os.tmpdir(),"m15b-refusal-"));
    try {
        const r=cp.spawnSync(process.execPath,[WORKER,"capture"],{
            encoding:"utf8",timeout:8000,
            env:{PATH:process.env.PATH,HOME:tmp,
                 POST_APOLLO_M15B_DISPOSABLE_CI:"1",
                 GITHUB_ACTIONS:"true",
                 DBUS_SESSION_BUS_ADDRESS:"unix:path=/run/user/1000/bus"}
        });
        assert.equal(r.status,2,r.stderr);
        assert.equal(r.stdout.trim(),"M15B_PRIVATE_HOST_REFUSED");
        assert.equal(r.stderr,"");
        assert.deepEqual(fs.readdirSync(tmp),[]);
    } finally {fs.rmSync(tmp,{recursive:true,force:true});}
});
test("standalone D-Bus harness is denied outside disposable CI",()=>{
    const r=cp.spawnSync("bash",[RUNNER,"--run"],{
        encoding:"utf8",timeout:8000,
        env:{...process.env,GITHUB_ACTIONS:"false",
             POST_APOLLO_M15B_DISPOSABLE_CI:"0",
             DBUS_SESSION_BUS_ADDRESS:"unix:path=/run/user/1000/bus"}
    });
    assert.equal(r.status,2,r.stdout+r.stderr);
    assert.equal(r.stdout.trim(),"M15B_PRIVATE_RUN_REFUSED");
    assert.equal(r.stderr,"");
    const syntax=cp.spawnSync("bash",["-n",RUNNER],{encoding:"utf8"});
    assert.equal(syntax.status,0,syntax.stderr);
});
test("bridge explicitly composes M13m AES-GCM source binding and M13o atomic storage",()=>{
    const src=read("tests/tasks/fixtures/TaskEncryptedDraftPrivateBridgeM15b.cjs");
    const driver=read("tests/tasks/tools/task_m15b_encrypted_draft_bridge.sh");
    for(const item of [
        "TaskEncryptedDraftTransactionM13m.cjs",
        "TaskEncryptedDraftPrivateStorageM13o.cjs",
        "createSyntheticCheckpoint(",
        "commitFake(",
        "inspectFake(",
        "evaluateSyntheticRecovery(",
        "clearFake(",
        "secret-tool",
        "privateContext()",
        "crypto.timingSafeEqual",
        "POST_APOLLO_M15B_DISPOSABLE_CI",
        "M15B_PRIVATE_ENCRYPTED_CAPTURE_PASS",
        "M15B_PRIVATE_UNLOCKED_PREVIEW_PASS",
        "M15B_PRIVATE_WRONG_KEY_REFUSED",
        "M15B_PRIVATE_SOURCE_CONFLICT_REFUSED",
        "M15B_PRIVATE_HOST_REFUSED",
        "key.fill(0)"
    ]) assert.ok(src.includes(item),"missing: "+item);
    for(const step of [
       "dbus-",
       "gnome-keyring-daemon --unlock --components=secrets",
       "verify capture ",
       "verify locked ",
       "verify preview-missing-key ",
       "verify preview-wrong-key ",
       "verify preview-source-conflict ",
       "verify preview ",
       "verify clear ",
       "verify absent ",
       "secret-tool clear service post-apollo-m15b-disposable-ci",
       "M15B_REAL_KEYRING_PRIVATE_CIPHERTEXT_RESTART_PASS"
    ]) assert.ok(driver.includes(step),"missing: "+step);
    assert.doesNotMatch(driver,/\b(?:sudo|pkill|killall|systemctl)\b/);
    assert.doesNotMatch(src,/process\.stdout\.write\(key|console\.log\(key|TaskRecoveryProviderHostM13i/);
    assert.doesNotMatch(driver,/quickshell -p|qs -p|git reset|git clean|git pull/);
});
test("production TASKS and shared Connections remain hard-disabled",()=>{
    const store=read("services/hub/ApolloHubTodoStore.qml");
    const broker=read("services/connections/ConnectionsBroker.qml");
    const qs=read("shell.qml");
    const recovery=read("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    const worker=read("tests/tasks/fixtures/TaskEncryptedDraftPrivateBridgeM15b.cjs");
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const field of [
        "encryptedRecoveryEnabled","encryptedRecoveryStorageAuthorized",
        "encryptedRecoveryUnlockAuthorized","encryptedDraftHostEnabled",
        "encryptedDraftHostWriteAuthorized","ticketProducerEnabled"
    ]) assert.match(store,new RegExp("readonly property bool "+field+":\\s*false"));
    assert.match(broker,/readonly property bool credentialActionsEnabled:\s*false/);
    for(const text of [store,qs,recovery,broker]){
        assert.doesNotMatch(text,/TaskEncryptedDraftPrivateBridgeM15b/);
        assert.doesNotMatch(text,/task_m15b_encrypted_draft_bridge/);
    }
    assert.doesNotMatch(worker,/ApolloHubTodoStore|Quickshell\.dataDir|apollo-hub-todo-v1\.json/);
});
