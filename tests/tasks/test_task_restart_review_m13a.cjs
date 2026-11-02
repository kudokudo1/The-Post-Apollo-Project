#!/usr/bin/env node
"use strict";
// M13a // test-only synced checkpoint bytes, fresh child process, no replay.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const vm=require("node:vm");
const cp=require("node:child_process");
const {constants:C}=fs;
const ROOT=path.resolve(__dirname,"../..");
const helper=require("./fixtures/TaskRestartReviewM13a.cjs");
const policyFile=path.join(ROOT,"services/hub/ApolloHubTodoPolicy.js");
function loadPolicy() {
    const ctx=vm.createContext({unescape,encodeURIComponent});
    vm.runInContext(fs.readFileSync(policyFile,"utf8")
        .replace(/^\.pragma library\s*/,""),ctx,{timeout:1000,filename:policyFile});
    return ctx;
}
const policy=loadPolicy();
function docs() {
    const confirmed=policy.create(policy.emptyDocument(),"M13A_LAST_CONFIRMED",1000).document;
    const candidate=policy.update(confirmed,"t1","rename","M13A_UNCONFIRMED",1100,false).document;
    return {confirmed,candidate};
}
const draft=surface=>({surface,method:"renameTask",
    value:{text:"M13A_UNCONFIRMED",editing:"t1"}});
const inputs=(phase="RESERVED",surface="HUB")=>({
    policy,...docs(),draft:draft(surface),sessionId:"M13aSessionOld01",
    ownerEpoch:7,generation:2,sequence:1,phase
});
const reopen=(plan,sourceRaw,overrides={})=>helper.reopen({
    recordRaw:plan.recordRaw,sourceRaw,policy,
    freshSessionId:"M13aSessionNew02",freshEpoch:8,...overrides
});
function fixture() {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"pa-m13a-stage-"));
    const folder=path.join(temp,"m13a-disposable");
    fs.mkdirSync(folder,{mode:0o700});
    return {temp,folder,source:path.join(folder,helper.SOURCE),
        record:path.join(folder,"m13a-checkpoint.json"),
        cleanup(){fs.rmSync(temp,{recursive:true,force:true});}};
}
function writeExclusive(file,raw) {
    const fd=fs.openSync(file,C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,0o600);
    try {fs.writeFileSync(fd,raw);fs.fsyncSync(fd);}
    finally {fs.closeSync(fd);}
    const dir=fs.openSync(path.dirname(file),C.O_RDONLY|C.O_DIRECTORY);
    try {fs.fsyncSync(dir);} finally {fs.closeSync(dir);}
}
function read(file) {
    const fd=fs.openSync(file,C.O_RDONLY|C.O_NOFOLLOW);
    try {
        const st=fs.fstatSync(fd);
        assert.ok(st.isFile());assert.equal(st.nlink,1);
        assert.equal(st.mode&0o077,0);
        return fs.readFileSync(fd,"utf8");
    } finally {fs.closeSync(fd);}
}
const childScript=[
    "'use strict';",
    "const fs=require('node:fs'),vm=require('node:vm');",
    "const helper=require(process.argv[1]);",
    "const code=fs.readFileSync(process.argv[2],'utf8').replace(/^\\.pragma library\\s*/,'');",
    "const p=vm.createContext({unescape,encodeURIComponent});",
    "vm.runInContext(code,p,{timeout:1000});",
    "const recordRaw=fs.readFileSync(process.argv[3],'utf8');",
    "let sourceRaw=null;",
    "try{sourceRaw=fs.readFileSync(process.argv[4],'utf8');}catch(e){if(e.code!=='ENOENT')throw e;}",
    "const x=helper.reopen({recordRaw,sourceRaw,policy:p,",
    "freshSessionId:'M13aSessionNew02',freshEpoch:8});",
    "process.stdout.write(JSON.stringify({ok:x.ok,reason:x.reason,phase:x.phase,",
    "writable:x.writable,replayAuthorized:x.replayAuthorized,",
    "clearDraftAuthorized:x.clearDraftAuthorized,",
    "sourceStatus:x.sourceStatus,priorPhase:x.priorPhase,",
    "stageId:x.stageId,rows:x.items?.map(t=>t.title),",
    "draft:x.draft?.value?.text,disposition:x.disposition}));"
].join("\n");
function restart(f) {
    const cmd=cp.spawnSync(process.execPath,["-e",childScript,
        path.join(__dirname,"fixtures/TaskRestartReviewM13a.cjs"),
        policyFile,f.record,f.source],{encoding:"utf8",timeout:10000});
    assert.equal(cmd.status,0,cmd.stderr);
    return JSON.parse(cmd.stdout);
}
function blocked(x) {
    assert.equal(x.writable,false);
    assert.equal(x.replayAuthorized,false);
    assert.equal(x.clearDraftAuthorized,false);
}
for(const [phase,sourceCase,expectedStatus] of [
    ["RESERVED","old","SOURCE_AT_LAST_CONFIRMED"],
    ["RESERVED","candidate","SOURCE_AT_CANDIDATE"],
    ["SETTLED","candidate","SOURCE_AT_CANDIDATE"],
    ["SETTLED","old","SOURCE_AT_LAST_CONFIRMED"],
    ["RESERVED","missing","SOURCE_MISSING"],
    ["RESERVED","foreign","SOURCE_MISMATCH"]
]) {
    test("fresh process after "+phase+"/"+sourceCase+" retains draft, refuses replay",()=>{
        const f=fixture();
        try {
            const p=helper.make(inputs(phase));
            assert.equal(p.ok,true,p.reason);
            writeExclusive(f.record,p.recordRaw);
            if(sourceCase!=="missing") {
                const raw=sourceCase==="old"?JSON.parse(p.recordRaw).beforeRaw:
                    sourceCase==="candidate"?JSON.parse(p.recordRaw).expectedRaw:"different";
                writeExclusive(f.source,raw);
            }
            const result=restart(f);
            assert.equal(result.ok,true,result.reason);
            assert.equal(result.phase,"RECOVERY_REVIEW");
            assert.equal(result.reason,"FRESH_OWNER_REVIEW_REQUIRED");
            assert.equal(result.sourceStatus,expectedStatus);
            assert.equal(result.priorPhase,phase);
            assert.equal(result.stageId,p.stageId);
            assert.deepEqual(result.rows,["M13A_LAST_CONFIRMED"]);
            assert.equal(result.draft,"M13A_UNCONFIRMED");
            assert.equal(result.disposition,"KEEP_DRAFT");
            blocked(result);
            assert.equal(read(f.record),p.recordRaw);
        } finally {f.cleanup();}
    });
}
test("checkpoint identity is immutable: duplicate attempt EEXIST and bytes unchanged",()=>{
    const f=fixture();
    try {
        const p=helper.make(inputs());
        writeExclusive(f.record,p.recordRaw);
        assert.throws(()=>writeExclusive(f.record,p.recordRaw),
            e=>e && e.code==="EEXIST");
        assert.equal(read(f.record),p.recordRaw);
        const r=JSON.parse(read(f.record));
        assert.equal(r.stageId,"m13a-M13aSessionOld01-7-1");
    } finally {f.cleanup();}
});
test("four UI surfaces retain their independent draft instead of clearing it",()=>{
    for(const surface of ["HUB","DETAILS","PLANNER","PROJECTS"]) {
        const p=helper.make(inputs("SETTLED",surface));
        const result=reopen(p,JSON.parse(p.recordRaw).expectedRaw);
        assert.equal(result.ok,true);
        assert.equal(result.draft.surface,surface);
        assert.equal(result.draft.value.text,"M13A_UNCONFIRMED");
        assert.equal(result.items[0].title,"M13A_LAST_CONFIRMED");
        blocked(result);
    }
});
test("stale/identical owner and fake settlement cannot authorize recovery",()=>{
    const p=helper.make(inputs("SETTLED"));
    const raw=JSON.parse(p.recordRaw).expectedRaw;
    for(const extra of [
        {freshSessionId:"M13aSessionOld01"},
        {freshEpoch:7},
        {freshEpoch:6},
        {freshEpoch:0}
    ]) {
        const result=reopen(p,raw,extra);
        assert.equal(result.ok,false);
        blocked(result);
    }
});
test("checkpoint tampering, changed hashes, changed stage and unknown fields fail closed",()=>{
    const p=helper.make(inputs("RESERVED"));
    const raw=JSON.parse(p.recordRaw);
    for(const mutate of [
        x=>{x.expectedSha="0".repeat(64);},
        x=>{x.beforeRaw="corrupt";},
        x=>{x.stageId="m13a-foreign-stage-12";},
        x=>{x.phase="CONFIRMED";},
        x=>{x.extra="unapproved";},
        x=>{x.format=2;},
        x=>{x.sessionId="foreignSession99";},
        x=>{x.draft={value:{text:"stolen"}};}
    ]) {
        const altered=JSON.parse(JSON.stringify(raw));mutate(altered);
        const result=helper.reopen({recordRaw:JSON.stringify(altered),
            sourceRaw:raw.expectedRaw,policy,
            freshSessionId:"M13aSessionNew02",freshEpoch:8});
        assert.equal(result.ok,false,JSON.stringify(altered));
        blocked(result);
    }
});
test("invalid identity, missing draft and unchanged candidate never form checkpoint",()=>{
    for(const extra of [
        {sessionId:"bad"},
        {ownerEpoch:0},
        {generation:0},
        {sequence:0},
        {phase:"WRITING"},
        {draft:{surface:"HUB",method:"renameTask"}},
        {draft:{surface:"OTHER",method:"renameTask",value:{text:"x"}}},
        {candidate:docs().confirmed}
    ]) {
        const p=helper.make({...inputs(),...extra});
        assert.equal(p.ok,false);
        blocked(p);
    }
});
test("returned confirmed rows and draft are copies; no source publication",()=>{
    const p=helper.make(inputs("SETTLED"));
    const source=JSON.parse(p.recordRaw).expectedRaw;
    const r=reopen(p,source);
    r.items[0].title="tamper";
    r.draft.value.text="tamper";
    const again=reopen(p,source);
    assert.equal(again.items[0].title,"M13A_LAST_CONFIRMED");
    assert.equal(again.draft.value.text,"M13A_UNCONFIRMED");
    assert.equal(again.writable,false);
});
test("source remains unmounted and all production ticket and writer gates false",()=>{
    const own=fs.readFileSync(path.join(__dirname,"fixtures/TaskRestartReviewM13a.cjs"),"utf8");
    const store=fs.readFileSync(path.join(ROOT,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.doesNotMatch(own,/\b(?:writeFile|openSync|mkdirSync|renameSync|unlinkSync|rmSync|spawnSync)\s*\(/);
    assert.doesNotMatch(store+shell,/TaskRestartReviewM13a/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(store,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
});
