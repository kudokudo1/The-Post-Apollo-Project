#!/usr/bin/env node
"use strict";
// TASKS M13m // fake-only pure policy tests; no user files or Secret Service.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
const model=require("./fixtures/TaskEncryptedDraftTransactionM13m.cjs");
const ROOT=path.resolve(__dirname,"../..");
const fakeSource=(marker="FAKE_SOURCE_A",generation=7)=>({
    kind:"M13M_FAKE_SOURCE",generation,
    raw:JSON.stringify({kind:"M13M_FAKE_TASKS_JSON",documentVersion:3,marker})
});
function scenario() {
    const source=fakeSource();
    const ledger={kind:"M13M_FAKE_LEDGER",installationId:"FAKEINSTALL001",
        epoch:7,sourceGeneration:source.generation,
        sourceDigest:crypto.createHash("sha256").update(source.raw).digest("hex"),
        latestCommittedSeq:0};
    const identity={installationId:"FAKEINSTALL001",
        stageId:"m13a-FAKEINSTALL001-7-1",epoch:7,surface:"HUB"};
    const draft={kind:"M13M_FAKE_EDITOR_DRAFT",surface:"HUB",
        value:"FAKE_UNFINISHED_EDITOR_TEXT"};
    const key=crypto.randomBytes(32);
    return {source,ledger,identity,draft,key};
}
const capture=(s,overrides={})=>model.createSyntheticCheckpoint({
    ...s,optedIn:true,checkpointSeq:1,...overrides
});
const recover=(s,p,overrides={})=>model.evaluateSyntheticRecovery({
    checkpoint:p.checkpoint,source:s.source,ledger:p.proposedLedger,
    identity:s.identity,key:s.key,unlocked:true,
    reviewRequested:true,activeDraftPresent:false,...overrides
});
function powerless(response) {
    assert.equal(typeof response.status,"string");
    for(const [k,v] of Object.entries(model.NO_POWER)) {
        assert.equal(v,false,k);
        assert.equal(response[k],false,k);
    }
    assert.equal(response.writeAuthorized,false);
    assert.equal(response.restoreAuthorized,false);
    assert.equal(response.keyReleaseAuthorized,false);
    assert.equal(response.productionActivation,false);
}
test("fake checkpoint encrypts draft with source identity, remains non-durable and powerless",()=>{
    const s=scenario();
    try {
        const p=capture(s);
        assert.equal(p.ok,true,p.status);
        assert.equal(p.status,"SYNTHETIC_CIPHERTEXT_PREPARED_NOT_DURABLE");
        powerless(p);
        assert.equal(p.checkpoint.format,1);
        assert.equal(p.checkpoint.sourceDigest,s.ledger.sourceDigest);
        assert.equal(p.checkpoint.sourceGeneration,7);
        assert.equal(p.proposedLedger.latestCommittedSeq,1);
        assert.equal(p.checkpoint.checkpointSeq,1);
        assert.ok(!p.checkpoint.envelopeRaw.includes(s.draft.value));
        assert.ok(!p.checkpoint.envelopeRaw.includes(s.source.raw));
        assert.ok(!p.checkpoint.envelopeRaw.includes(s.key.toString("base64")));
        const locked=model.inspectLocked({checkpoint:p.checkpoint});
        assert.equal(locked.ok,true);
        assert.equal(locked.locked,true);
        assert.equal(Object.hasOwn(locked,"fakePreviewMarker"),false);
        powerless(locked);
        const match=model.simulateReadback({
            checkpoint:p.checkpoint,proposedLedger:p.proposedLedger,
            readbackEnvelopeRaw:p.checkpoint.envelopeRaw
        });
        assert.equal(match.ok,true);
        assert.equal(match.status,"SYNTHETIC_BYTES_MATCH_NOT_DURABLE");
        powerless(match);
        const review=recover(s,p);
        assert.equal(review.ok,true,review.status);
        assert.equal(review.fakePreviewMarker,s.draft.value);
        assert.equal(review.disposition,"PREVIEW_ONLY_NO_APPLY");
        powerless(review);
    }finally{s.key.fill(0);}
});
test("opt-in, fake source schema, baseline, stage and next sequence gate capture",()=>{
    const s=scenario();
    try {
        const cases=[
            [capture(s,{optedIn:false}),"SIMULATED_OPT_IN_REQUIRED"],
            [capture(s,{source:{...s.source,raw:"{}"}}),"INVALID_FAKE_SOURCE"],
            [capture(s,{source:fakeSource("FAKE_DIFFERENT")}),"SOURCE_NOT_LAST_CONFIRMED"],
            [capture(s,{identity:{...s.identity,epoch:9}}),"INSTALLATION_OR_EPOCH_MISMATCH"],
            [capture(s,{identity:{...s.identity,installationId:"FAKEOTHER001"}}),"INSTALLATION_OR_EPOCH_MISMATCH"],
            [capture(s,{checkpointSeq:2}),"CHECKPOINT_SEQUENCE_NOT_NEXT"],
            [capture(s,{ledger:null}),"INVALID_FAKE_LEDGER"],
            [capture(s,{draft:{...s.draft,value:"REAL_DRAFT_TEXT"}}),"FAKE_EDITOR_DRAFT_REQUIRED"],
            [capture(s,{draft:{...s.draft,surface:"DETAILS"}}),"FAKE_EDITOR_DRAFT_REQUIRED"],
        ];
        for(const [out,status] of cases){
            assert.equal(out.ok,false,status);
            assert.equal(out.status,status);
            assert.equal(Object.hasOwn(out,"checkpoint"),false);
            powerless(out);
        }
    }finally{s.key.fill(0);}
});
test("readback mismatches refuse and never assert actual persistence",()=>{
    const s=scenario();
    try {
        const p=capture(s);
        for(const out of [
            model.simulateReadback({checkpoint:p.checkpoint,
                proposedLedger:p.proposedLedger,
                readbackEnvelopeRaw:p.checkpoint.envelopeRaw+" "}),
            model.simulateReadback({checkpoint:p.checkpoint,
                proposedLedger:{...p.proposedLedger,latestCommittedSeq:0},
                readbackEnvelopeRaw:p.checkpoint.envelopeRaw}),
            model.simulateReadback({checkpoint:p.checkpoint,
                proposedLedger:null,
                readbackEnvelopeRaw:p.checkpoint.envelopeRaw})
        ]) {
            assert.equal(out.ok,false);
            powerless(out);
        }
    }finally{s.key.fill(0);}
});
test("stale checkpoint, external source change and missing ledger refuse before decrypt",()=>{
    const s=scenario();
    try{
        const p=capture(s);
        const cases=[
            [recover(s,p,{ledger:{...p.proposedLedger,latestCommittedSeq:2}}),
                "STALE_OR_UNCOMMITTED_CHECKPOINT"],
            [recover(s,p,{source:fakeSource("FAKE_CHANGED")}),
                "SOURCE_CHANGED_REVIEW_REQUIRED"],
            [recover(s,p,{source:fakeSource("FAKE_SOURCE_A",8)}),
                "SOURCE_CHANGED_REVIEW_REQUIRED"],
            [recover(s,p,{ledger:null}),"TRUSTED_LEDGER_UNAVAILABLE"],
            [recover(s,p,{identity:{...s.identity,stageId:"m13a-FAKEINSTALL001-7-2"}}),
                "IDENTITY_OR_CONTEXT_MISMATCH"],
            [recover(s,p,{identity:{...s.identity,surface:"PLANNER"}}),
                "IDENTITY_OR_CONTEXT_MISMATCH"]
        ];
        for(const [out,status] of cases){
            assert.equal(out.ok,false,status);
            assert.equal(out.status,status);
            assert.equal(Object.hasOwn(out,"fakePreviewMarker"),false);
            powerless(out);
        }
    }finally{s.key.fill(0);}
});
test("active editor draft, missing review and missing unlock never disclose plaintext",()=>{
    const s=scenario();
    try{
        const p=capture(s);
        const cases=[
            [recover(s,p,{activeDraftPresent:true}),"ACTIVE_EDITOR_DRAFT_REVIEW_REQUIRED"],
            [recover(s,p,{activeDraftPresent:undefined}),"ACTIVE_EDITOR_DRAFT_REVIEW_REQUIRED"],
            [recover(s,p,{reviewRequested:false}),"SEPARATE_USER_REVIEW_REQUIRED"],
            [recover(s,p,{unlocked:false}),"SEPARATE_UNLOCK_REQUIRED"],
            [recover(s,p,{key:crypto.randomBytes(32)}),"CIPHERTEXT_AUTH_OR_KEY_REFUSED"],
        ];
        for(const [out,status] of cases) {
            assert.equal(out.ok,false,status);
            assert.equal(out.status,status);
            assert.equal(Object.hasOwn(out,"fakePreviewMarker"),false);
            powerless(out);
        }
    }finally{s.key.fill(0);}
});
test("tampered ciphertext and alternate metadata are rejected",()=>{
    const s=scenario();
    try {
        const p=capture(s);
        const parsed=JSON.parse(p.checkpoint.envelopeRaw);
        parsed.tag=parsed.tag[0]==="A"?"B"+parsed.tag.slice(1):"A"+parsed.tag.slice(1);
        const damaged={...p.checkpoint,envelopeRaw:JSON.stringify(parsed)+"\n"};
        const out=recover(s,{...p,checkpoint:damaged});
        assert.equal(out.ok,false);
        assert.equal(out.status,"CIPHERTEXT_AUTH_OR_KEY_REFUSED");
        powerless(out);
        const changed={...p.checkpoint,sourceDigest:"0".repeat(64)};
        const refused=recover(s,{...p,checkpoint:changed});
        assert.equal(refused.ok,false);
        assert.equal(refused.status,"SOURCE_CHANGED_REVIEW_REQUIRED");
        powerless(refused);
    }finally{s.key.fill(0);}
});
test("source and policy inventory stay disconnected from actual TASKS",()=>{
    const file=path.join(ROOT,"tests/tasks/fixtures/TaskEncryptedDraftTransactionM13m.cjs");
    const code=fs.readFileSync(file,"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.match(code,/TaskEncryptedRecoveryM13f\.cjs/);
    assert.match(code,/SYNTHETIC_CIPHERTEXT_PREPARED_NOT_DURABLE/);
    assert.match(code,/SOURCE_CHANGED_REVIEW_REQUIRED/);
    assert.match(code,/STALE_OR_UNCOMMITTED_CHECKPOINT/);
    assert.doesNotMatch(code,/require\("node:fs"\)|secret-tool|dbus-send|FileView|writeFile|setText|process\.env|apollo-hub-todo-v1\.json/);
    assert.doesNotMatch(store,/TaskEncryptedDraftTransactionM13m/);
    assert.doesNotMatch(shell,/TaskEncryptedDraftTransactionM13m/);
    for(const k of ["guardedWriterEnabled","ticketProducerEnabled",
        "encryptedRecoveryEnabled","encryptedDraftHostEnabled"])
        assert.match(store,new RegExp("readonly property bool "+k+":\\s*false"));
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
});
