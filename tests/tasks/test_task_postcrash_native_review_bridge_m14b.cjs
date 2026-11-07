#!/usr/bin/env node
"use strict";
/* TASKS M14b: real disposable SQLite/JSON -> strict M13z UI projection.
 * Source bytes are never taken from live TASKS or published in a UI frame.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const cp=require("node:child_process");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const FIX=path.join(ROOT,"tests/tasks/fixtures");
const LAB=path.join(FIX,"TaskPostCrashReviewLabM14b.qml");
const HARNESS=path.join(ROOT,"TaskPostCrashReviewHarnessM14b.qml");
const INSPECTOR=path.join(FIX,"TaskPostCrashSourceReviewM13y.py");
const RECEIPTS=path.join(FIX,"TaskStageSourceReceiptM12h.py");
const read=p=>fs.readFileSync(p,"utf8");
const policy=vm.createContext({});
vm.runInContext(read(path.join(ROOT,"widgets/tasks/TaskRecoveryReviewPolicyM13z.js")).replace(/^\.pragma library\s*/,""),policy,{timeout:1000});

const SETUP=[
"import importlib.util, os, pathlib, sys, uuid",
"spec=importlib.util.spec_from_file_location('m14b_m12h_fixture',sys.argv[1])",
"m=importlib.util.module_from_spec(spec)",
"spec.loader.exec_module(m)",
"db=pathlib.Path(sys.argv[2])",
"mode=sys.argv[3]",
"with m.DisposableStageReceipt(db,'m14b-test-owner-00001',bootstrap=True) as owner:",
"    stage=owner.reserve('m14b-stage-000001')",
"    if mode in ('expected','settled'):",
"        replacement=db.parent/('.m14b-fixture-'+uuid.uuid4().hex)",
"        fd=os.open(replacement,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)",
"        with os.fdopen(fd,'wb') as output:",
"            output.write(stage['payload'])",
"            output.flush()",
"            os.fsync(output.fileno())",
"        os.replace(replacement,db.parent/'fixture-only.json')",
"        d=os.open(db.parent,os.O_RDONLY|os.O_DIRECTORY)",
"        os.fsync(d)",
"        os.close(d)",
"    if mode=='settled':",
"        saved=owner.settle_after_independent_readback(stage['stageId'],stage['epoch'])",
"        assert saved['settled'],saved"
].join("\n");

function py(args) {
    return cp.spawnSync("python3",["-I","-B",...args],{
        encoding:"utf8",timeout:15000,maxBuffer:8192
    });
}
function createFixture(t,mode) {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"m14b-review-"));
    t.after(()=>fs.rmSync(temp,{recursive:true,force:true}));
    const folder=path.join(temp,"m11e-fileview-test");
    fs.mkdirSync(folder,{mode:0o700});
    fs.chmodSync(folder,0o700);
    const source=path.join(folder,"fixture-only.json");
    const seed=JSON.stringify({
        fixture:"M11E_SYNTHETIC_ONLY",revision:0,counter:0,marker:"sample"
    })+"\n";
    fs.writeFileSync(source,seed,{flag:"wx",mode:0o600});
    fs.chmodSync(source,0o600);
    const db=path.join(folder,"handoff-test.db");
    const built=py(["-c",SETUP,RECEIPTS,db,mode]);
    assert.equal(built.status,0,built.stderr);
    return {temp,folder,source,db,seed};
}
function inspect(db){
    const process=py([INSPECTOR,"--db",db]);
    assert.equal(process.status,0,process.stderr);
    assert.ok(process.stdout.length>0 && process.stdout.length<4096);
    assert.equal(process.stdout.trim().split("\n").length,1);
    return JSON.parse(process.stdout);
}
function project(frame){
    return JSON.parse(JSON.stringify(policy.syntheticResult(frame)));
}
function denyAll(view){
    assert.match(view.origin,/SYNTHETIC FIXTURE/);
    assert.equal(view.draftStatus,"KEEP UNSAVED DRAFT");
    assert.equal(view.displayStatus,"KEEP LAST CONFIRMED VIEW");
    assert.equal(view.nextStep,"MANUAL REVIEW ONLY");
    for(const key of [
        "canReplay","canRestore","canClearDraft","canDeleteCheckpoint",
        "canWriteTasks","nativeSaveAcknowledged","encryptedRecoveryEnabled",
        "liveSourceEvidenceConnected","readTaskData","keyReleaseAuthorized"
    ])assert.equal(view[key],false,key);
    for(const key of ["sourcePath","sourceHash","stageId","writerId","receipt",
                      "tasks","draftText","rawSource","fileContent","keyringToken"])
        assert.equal(Object.hasOwn(view,key),false,key);
}
test("real disposable SQLite states roundtrip through M13y and strict M13z presentation",t=>{
    const cases=[
        ["baseline","RESERVED_SOURCE_STILL_AT_BASELINE","SOURCE STILL UNCHANGED"],
        ["expected","RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED",
         "NEW BYTES // UNSETTLED RECEIPT"],
        ["settled","SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED",
         "RECEIPT SETTLED / UI NOT ACKNOWLEDGED"]
    ];
    for(const [mode,code,title] of cases){
        const x=createFixture(t,mode),before=fs.readFileSync(x.source);
        const frame=inspect(x.db);
        assert.equal(frame.classification,code,mode);
        const view=project(frame);
        assert.equal(view.title,title,mode);
        assert.equal(view.origin,"SYNTHETIC FIXTURE ONLY // NOT LIVE");
        denyAll(view);
        assert.deepEqual(fs.readFileSync(x.source),before);
        for(const secret of [x.temp,"fixture-only.json","m14b-stage-000001"]){
            assert.ok(!JSON.stringify(view).includes(secret));
        }
        for(const flag of ["savedAcknowledged","sourceOwnerAuthenticated",
                          "taskWriteAuthorized","automaticReplayAuthorized",
                          "clearDraftAuthorized"])
            assert.equal(frame[flag],false,flag);
    }
});
test("unsafe source and nonexistent journal cannot produce a trusted display",t=>{
    const x=createFixture(t,"baseline");
    const wrong=inspect(path.join(x.folder,"not-the-journal.db"));
    assert.equal(wrong.classification,"REFUSED_NOT_DISPOSABLE_M12H_PATH");
    assert.equal(project(wrong).origin,"SYNTHETIC FIXTURE // UNVERIFIED");
    const other=path.join(x.folder,"unrelated.json");
    fs.writeFileSync(other,x.seed,{mode:0o600});
    fs.unlinkSync(x.source);
    fs.symlinkSync(other,x.source);
    const unsafe=inspect(x.db);
    assert.equal(unsafe.classification,"SAVED_SOURCE_UNAVAILABLE_OR_UNSAFE");
    const view=project(unsafe);
    assert.equal(view.origin,"SYNTHETIC FIXTURE // UNVERIFIED");
    denyAll(view);
});
test("forged approval, raw source and false schema cannot upgrade the fixture",t=>{
    const x=createFixture(t,"settled"),r=inspect(x.db);
    for(const input of [
        {...r,realTaskDataRead:true},
        {...r,sourceOwnerAuthenticated:true},
        {...r,clearDraftAuthorized:true},
        {...r,approvedByUser:true},
        {...r,rawSource:"PRIVATE_TEST_CONTENT"},
        {...r,classification:"REAL_DURABLE_SAVE"},
        {...r,lastSettledRevision:-1}
    ]){
        const view=project(input);
        assert.equal(view.origin,"SYNTHETIC FIXTURE // UNVERIFIED");
        denyAll(view);
        assert.ok(!JSON.stringify(view).includes("PRIVATE_TEST_CONTENT"));
    }
});
test("standalone native QML only starts on click, only fixture path, no writer",()=>{
    const qml=read(LAB),root=read(HARNESS);
    for(const text of [
        "function fixtureOnlyPath(path)","function inspectOnce()",
        "onClicked: lab.inspectOnce()","inspector.exec([",
        "TaskPostCrashSourceReviewM13y.py",
        "ReviewPolicy.syntheticResult(value)",
        "SYNTHETIC FIXTURE ONLY // NOT LIVE",
        "readonly property bool realTaskDataAccessAuthorized: false",
        "readonly property bool durableUserSaveAcknowledged: false",
        "readonly property bool automaticReplayAuthorized: false",
        "readonly property bool draftDeletionAuthorized: false",
        "readonly property bool keyReleaseAuthorized: false"
    ])assert.ok(qml.includes(text),text);
    assert.ok(qml.includes("m11e-fileview-test")&&qml.includes("handoff-test"));
    assert.ok(qml.includes("NOT REAL TASKS"));
    assert.ok(root.includes("TaskPostCrashReviewLabM14b { id: lab }"));
    assert.ok(root.includes("productionActivated: false"));
    assert.equal((qml.match(/\bProcess\s*\{/g)||[]).length,1);
    assert.equal((qml.match(/\bFileView\s*\{/g)||[]).length,0);
    for(const forbidden of [
        "Component.onCompleted","running: true","FileDialog","Timer {",
        ".setText(",".write(",".reload(","Quickshell.dataDir",
        "XMLHttpRequest","WebEngineView","Qt.openUrlExternally"
    ])assert.ok(!qml.includes(forbidden),forbidden);
});
test("live TASKS writer, M14a callback and M13z review stay intact",()=>{
    const store=read(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"));
    const pane=read(path.join(ROOT,"widgets/tasks/TaskRecoveryStatusPaneM13q.qml"));
    const broker=read(path.join(ROOT,"services/connections/ConnectionsBroker.qml"));
    const shell=read(path.join(ROOT,"shell.qml"));
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/readonly property bool ticketProducerEnabled: false/);
    assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    assert.match(pane,/nativeSaveSignals: ApolloHubTodoStore\.nativeSaveObservationM14a/);
    for(const src of [store,pane,broker,shell])
        assert.doesNotMatch(src,/TaskPostCrashReviewLabM14b|TaskPostCrashReviewHarnessM14b/);
});
