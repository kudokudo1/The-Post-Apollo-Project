#!/usr/bin/env node
"use strict";
/* M13z // no fake LIVE source ACK from a display of M13y fixtures. */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const policySource=read("widgets/tasks/TaskRecoveryReviewPolicyM13z.js");
const ctx=vm.createContext({});
vm.runInContext(policySource.replace(/^\.pragma library\s*/,""),ctx,
                {filename:"TaskRecoveryReviewPolicyM13z.js",timeout:1000});
const P=ctx;
const json=x=>JSON.parse(JSON.stringify(x));
const names=["baseline","expected","settled"];
const codes=[
    "RESERVED_SOURCE_STILL_AT_BASELINE",
    "RESERVED_SOURCE_MATCHES_EXPECTED_UNACKNOWLEDGED",
    "SETTLED_SOURCE_MATCHES_UI_UNACKNOWLEDGED"
];
function noPower(output){
    for(const field of [
        "canReplay","canRestore","canClearDraft","canDeleteCheckpoint",
        "canWriteTasks","nativeSaveAcknowledged","encryptedRecoveryEnabled",
        "liveSourceEvidenceConnected","readTaskData","keyReleaseAuthorized"
    ])assert.equal(output[field],false,field);
    assert.equal(output.draftStatus,"KEEP UNSAVED DRAFT");
    assert.equal(output.displayStatus,"KEEP LAST CONFIRMED VIEW");
    assert.equal(output.nextStep,"MANUAL REVIEW ONLY");
    for(const field of ["sourceHash","draft","taskId","stageId","ticket",
                        "lastSettledRevision","key","credential"])
        assert.equal(Object.hasOwn(output,field),false,field);
}
function fixture(index) {
    const scenario=P.SCENARIOS[names[index]];
    const data={
        classification:scenario.classification,
        lastSettledRevision:index===2?1:0,
        pendingStagePresent:scenario.pendingStagePresent,
        sourcePosition:scenario.sourcePosition,
        draftDisposition:"KEEP_DRAFT",
        lastConfirmedDisplay:"KEEP_LAST_CONFIRMED",
        nextAction:"OPERATOR_REVIEW_ONLY",
        fixtureOnly:true,
        journalReadOnly:true
    };
    for(const key of P.M13Y_FALSE_FLAGS)data[key]=false;
    return data;
}
test("M13z live source review is explicitly disconnected at all times",()=>{
    const live=P.current();
    assert.equal(live.origin,"LIVE // SOURCE REVIEW NOT CONNECTED");
    assert.equal(live.title,"SAVE STATE NOT VERIFIED");
    assert.match(live.explanation,/No live source journal is connected/);
    noPower(live);
    assert.notDeepEqual(json(live),json(P.example("baseline")));
});
test("all three operator previews map exact M13y crash states, always examples",()=>{
    for(let i=0;i<names.length;i++){
        const demo=P.example(names[i]);
        assert.equal(demo.origin,"EXAMPLE ONLY // NOT A LIVE SAVE");
        assert.ok(demo.title.length>8);
        assert.ok(demo.explanation.length>50);
        noPower(demo);
        const projected=P.syntheticResult(fixture(i));
        assert.equal(projected.origin,"SYNTHETIC FIXTURE ONLY // NOT LIVE");
        assert.equal(projected.title,demo.title);
        assert.equal(projected.headline,demo.headline);
        noPower(projected);
    }
    const normal=P.example("baseline");
    const expected=P.example("expected");
    const settled=P.example("settled");
    assert.match(normal.title,/UNCHANGED/);
    assert.match(expected.title,/UNSETTLED/);
    assert.match(settled.title,/UI NOT ACKNOWLEDGED/);
});
test("unknown, missing and script-shaped example ids never become source facts",()=>{
    for(const id of [null,undefined,"","real","confirmed","saved",
        "<PRIVATE_TASK_CONTENT>",{},["settled"],1]){
        const view=P.example(id);
        assert.equal(view.origin,"EXAMPLE // UNKNOWN CASE");
        assert.equal(view.title,"SAVE STATE NOT VERIFIED");
        noPower(view);
        assert.doesNotMatch(JSON.stringify(view),/PRIVATE_TASK_CONTENT/);
    }
});
test("untrusted or malformed M13y receipts never grant ACK, retry or preview",()=>{
    const base=fixture(1);
    const cases=[null,{},true,[],{...base,classification:"CONFIRMED"},
                 {...base,sourcePosition:"BASELINE"},
                 {...base,pendingStagePresent:false},
                 {...base,fixtureOnly:false},
                 {...base,journalReadOnly:false},
                 {...base,expectedSourceSha256:"a".repeat(64)},
                 {...base,lastSettledRevision:-1},
                 {...base,lastSettledRevision:1.5},
                 {...base,lastSettledRevision:"2"},
                 {...base,draftDisposition:"DELETE_DRAFT"},
                 {...base,nextAction:"AUTO_REPLAY"},
                 {...base,lastConfirmedDisplay:"SHOW_UNCONFIRMED"},
                 {...base,sourceOwnerAuthenticated:true},
                 {...base,savedAcknowledged:true},
                 {...base,previewAuthorized:true},
                 {...base,clearDraftAuthorized:true},
                 {...base,taskWriteAuthorized:true},
                 {...base,keyReleaseAuthorized:true}];
    for(const candidate of cases){
        const output=P.syntheticResult(candidate);
        assert.equal(output.origin,"SYNTHETIC FIXTURE // UNVERIFIED");
        noPower(output);
    }
});
test("all M13y authority fields are required literal false",()=>{
    const example=fixture(2);
    for(const key of P.M13Y_FALSE_FLAGS){
        const active=P.syntheticResult({...example,[key]:true});
        const omitted={...example};delete omitted[key];
        assert.equal(active.origin,"SYNTHETIC FIXTURE // UNVERIFIED",key);
        assert.equal(P.syntheticResult(omitted).origin,
                     "SYNTHETIC FIXTURE // UNVERIFIED",key);
        noPower(active);
    }
});
test("no raw source data, filename, stage, task or fake principal leaves policy",()=>{
    const receipt={...fixture(2),sourceSha256:"a".repeat(64),
                   taskTitle:"PRIVATE_TITLE",approvedByUser:true};
    const rendered=P.syntheticResult(receipt);
    assert.equal(rendered.origin,"SYNTHETIC FIXTURE // UNVERIFIED");
    for(const blocked of ["PRIVATE_TITLE","aaaa","stage","approvedByUser"])
        assert.ok(!JSON.stringify(rendered).includes(blocked),blocked);
    noPower(rendered);
    const inspector=read("tests/tasks/fixtures/TaskPostCrashSourceReviewM13y.py");
    for(const code of codes)assert.ok(inspector.includes(code),code);
});
test("M13z mounts exactly once in existing RECOVERY, after live editor draft",()=>{
    const newPane=read("widgets/tasks/TaskRecoveryReviewPaneM13z.qml");
    const sync=read("widgets/tasks/TaskSyncConnectionsPane.qml");
    const existing=read("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    assert.equal((existing.match(/TaskRecoveryReviewPaneM13z\s*\{/g)||[]).length,1);
    assert.ok(existing.indexOf("draftReport.otherScope")
              <existing.indexOf("TaskRecoveryReviewPaneM13z {"));
    assert.ok(existing.indexOf("TaskRecoveryReviewPaneM13z {")
              <existing.indexOf("RECOVERY PERMISSIONS // NOT ACTIVE"));
    assert.match(existing,/DraftPresencePolicy\.view\(editorSignals\)/);
    assert.match(existing,/RecoveryStatusPolicy\.view\(/);
    assert.match(existing,/ConnectionsBroker\.checkAvailability\(\)/);
    assert.match(existing,/READ ONLY \/\/ NO CAPTURE \/\/ NO KEY RELEASE \/\/ NO RESTORE/);
    assert.equal((sync.match(/TaskRecoveryStatusPaneM13q\s*\{/g)||[]).length,1);
    assert.match(sync,/\{id:"recovery", label:"RECOVERY"\}/);
    assert.match(newPane,/readonly property bool liveSourceInspectionConnected: false/);
    assert.match(newPane,/ReviewPolicy\.current\(\)/);
    assert.match(newPane,/ReviewPolicy\.example\(selectedExample\)/);
    assert.match(newPane,/onTriggered: review\.selectedExample=modelData\.id/);
    assert.match(newPane,/NO REPLAY \/\/ NO RESTORE \/\/ NO DRAFT DELETE/);
    assert.match(newPane,/EXAMPLE/);
    assert.doesNotMatch(newPane,/syntheticResult\(/);
    assert.doesNotMatch(newPane,/TaskPostCrashSourceReviewM13y/);
});
test("single JSON writer and encrypted recovery/Connections deny-all unchanged",()=>{
    const store=read("services/hub/ApolloHubTodoStore.qml");
    const broker=read("services/connections/ConnectionsBroker.qml");
    const review=read("widgets/tasks/TaskRecoveryReviewPaneM13z.qml");
    const presentation=read("widgets/tasks/TaskRecoveryReviewPolicyM13z.js");
    const old=read("widgets/tasks/TaskRecoveryStatusPaneM13q.qml");
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/readonly property bool ticketProducerEnabled: false/);
    assert.match(store,/readonly property bool encryptedRecoveryEnabled: false/);
    assert.match(store,/readonly property bool encryptedDraftHostEnabled: false/);
    assert.match(broker,/readonly property bool credentialActionsEnabled: false/);
    for(const content of [review,presentation]){
        for(const forbidden of ["FileView {","Process {","XMLHttpRequest",
          "Settings {","Qt.openUrlExternally","Keyring","secret-tool",
          "ApolloHubTodoStore.","ConnectionsBroker.","fetch(","writeFile(",
          "localStorage","Timer {","Component.onCompleted"])
            assert.ok(!content.includes(forbidden),"unexpected actor "+forbidden);
    }
    assert.doesNotMatch(store+broker,/TaskRecoveryReviewPaneM13z/);
    assert.doesNotMatch(old,/TaskPostCrashSourceReviewM13y/);
});
