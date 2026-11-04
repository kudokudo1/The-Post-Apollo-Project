#!/usr/bin/env node
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),cp=require("node:child_process");
const ROOT=path.resolve(__dirname,"../..");
const get=x=>fs.readFileSync(path.join(ROOT,x),"utf8");
const host="tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs";
const cli=path.join(ROOT,host);
const store=get("services/hub/ApolloHubTodoStore.qml");
const bridge=get("services/hub/TaskEncryptedDraftHostBridgeM13k.qml");
const panel=get("TaskEncryptedDraftHarnessM13k.qml");
const moduleText=get("services/hub/qmldir");

function run(args,request,env={}) {
    return cp.spawnSync(process.execPath,[cli,...args],{
        input:request===undefined?undefined:JSON.stringify(request)+"\n",
        encoding:"utf8",timeout:3000,maxBuffer:4096,
        env:{...process.env,POST_APOLLO_M13K_ISOLATED:"",POST_APOLLO_M13G_DISPOSABLE:"",
            ...env}
    });
}
function refusal(output,reason) {
    assert.equal(output.status,0,output.stderr);
    assert.equal(output.stderr,"");
    const v=JSON.parse(output.stdout);
    assert.equal(v.protocol,1);
    assert.equal(v.kind,"M13K_SYNTHETIC_HOST");
    assert.equal(v.status,reason);
    assert.equal(v.syntheticRoundTripVerified,false);
    for(const k of ["productionActivation","sourceTrusted","persistAuthorized",
                     "writeAuthorized","restoreAuthorized","replayAuthorized",
                     "deleteAuthorized","keyReleaseAuthorized"])
        assert.equal(v[k],false);
}
test("host refuses invocation without explicit mode, no input and no real Secret Service call",()=>{
    refusal(run([]),"REFUSED_EXPLICIT_MODE_REQUIRED");
    refusal(run(["--single-request"],{
        protocol:1,kind:"RUN_SYNTHETIC_DRAFT",consent:"CI_ONLY"
    }),"REFUSED_NOT_DISPOSABLE_SESSION");
});
test("synthetic marker cannot be used on current actual desktop D-Bus",()=>{
    const env={
        POST_APOLLO_M13K_ISOLATED:"1",
        POST_APOLLO_M13G_DISPOSABLE:"1",
        DBUS_SESSION_BUS_ADDRESS:"unix:path=/run/user/1000/bus"
    };
    refusal(run(["--single-request"],{
        protocol:1,kind:"RUN_SYNTHETIC_DRAFT",consent:"CI_ONLY"
    },env),"REFUSED_NOT_DISPOSABLE_SESSION");
});
test("host only delegates to established isolated M13g fixture; no real draft sources",()=>{
    const h=get(host);
    assert.match(h,/TaskSecretServiceRoundTripM13g\.cjs/);
    assert.match(h,/postapollo-m13g-m13k-/);
    assert.match(h,/XDG_DATA_HOME/);
    assert.match(h,/POST_APOLLO_M13K_ISOLATED/);
    assert.match(h,/post-apollo-m13g-ci/);
    assert.match(h,/reopen-missing-key/);
    assert.match(h,/REFUSED_SYNTHETIC_CLEANUP_UNVERIFIED/);
    assert.match(h,/secret-tool".*\["clear"/);
    assert.doesNotMatch(h,/apollo-hub-todo-v1\.json|Quickshell\.dataDir/);
    assert.doesNotMatch(h,/rmSync\(|rm -rf|setText\(|\.writeTask\(/);
});
test("one-shot host releases stdin even when QML keeps writable pipe open",()=>{
    const h=get(host),p=get("tests/tasks/fixtures/TaskEncryptedDraftHeldStdinM13n.cjs");
    assert.match(h,/function finishInput\(\)/);
    assert.match(h,/process\.stdin\.unref\(\)/);
    assert.match(h,/process\.stdin\.destroy\(\)/);
    assert.equal((h.match(/finishInput\(\);/g)||[]).length,2);
    assert.match(p,/cp\.spawn\(process\.execPath/);
    assert.match(p,/stdio:\["pipe","pipe","pipe"\]/);
    assert.match(p,/child\.stdin\.write\(request\+"\\n"\)/);
    assert.doesNotMatch(p,/child\.stdin\.end\(/);
    assert.match(p,/M13N_HELD_STDIN_ENCRYPTED_CHILD_EXIT_PASS/);
    assert.match(p,/M13N_HELD_STDIN_MALFORMED_CHILD_EXIT_PASS/);
    assert.doesNotMatch(h,/\.writeTask\(|apollo-hub-todo-v1\.json/);
});
test("QML Process seam requires fake isolated env and never starts on load",()=>{
    assert.match(bridge,/readonly property bool encryptedRecoveryEnabled:\s*false/);
    assert.match(bridge,/readonly property bool productionActivation:\s*false/);
    for(const permission of ["userOptedIn","canPersistUserDraft",
            "canDecryptUserDraft","canRestoreUserDraft","canWriteTaskSource"])
        assert.match(bridge,new RegExp("readonly property bool "+permission+":\\s*false"));
    assert.match(bridge,/POST_APOLLO_M13K_ISOLATED/);
    assert.match(bridge,/POST_APOLLO_M13G_DISPOSABLE/);
    assert.match(bridge,/function startSynthetic\(\)/);
    assert.match(bridge,/Process\s*\{\s*id:\s*host/);
    assert.match(bridge,/stdinEnabled:\s*true/);
    assert.match(bridge,/SplitParser\s*\{/);
    assert.match(bridge,/host\.write\(JSON\.stringify\(/);
    assert.match(bridge,/TaskEncryptedDraftHostM13k\.cjs/);
    assert.doesNotMatch(bridge,/\brunning\s*:\s*true\b/);
    assert.doesNotMatch(bridge,/\bFileView\s*\{/);
    assert.doesNotMatch(bridge,/\.setText\(|secret-tool/);
});
test("existing singleton mounts one dormant host and retains original mutation surface",()=>{
    assert.match(store,/TaskEncryptedDraftHostBridgeM13k\s*\{\s*id:\s*encryptedDraftHostBridge/);
    for(const key of ["encryptedDraftHostEnabled","encryptedDraftHostWriteAuthorized",
        "guardedWriterEnabled","ticketProducerEnabled",
        "independentlyAuthenticatedTicketReceipt","encryptedRecoveryEnabled",
        "encryptedRecoveryStorageAuthorized","encryptedRecoveryUnlockAuthorized"])
        assert.match(store,new RegExp("readonly property bool "+key+":\\s*false"));
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.doesNotMatch(store,/function startSynthetic\(/);
    assert.match(store,/readonly property string encryptedDraftHostStatus:/);
    const expected="TaskEncryptedDraftHostBridgeM13k 1.0 TaskEncryptedDraftHostBridgeM13k.qml";
    assert.equal(moduleText.split(/\r?\n/).filter(s=>s===expected).length,1);
    assert.ok(fs.existsSync(path.join(ROOT,"services/hub/TaskEncryptedDraftHostBridgeM13k.qml")));
});
test("standalone QML panel not mounted into normal desktop",()=>{
    assert.match(panel,/TaskEncryptedDraftHostBridgeM13k\s*\{/);
    assert.match(panel,/enabled:\s*bridge\.syntheticCIEligible && !bridge\.busy/);
    assert.match(panel,/onClicked:\s*bridge\.startSynthetic\(\)/);
    assert.match(panel,/NO PRIVATE TEST SESSION/);
    assert.doesNotMatch(get("shell.qml"),/TaskEncryptedDraftHarnessM13k/);
});
