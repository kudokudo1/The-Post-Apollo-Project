#!/usr/bin/env node
"use strict";
// M12z: all actual file creation occurs ONLY inside private mkdtemp test roots.
// The reusable contract exports no filesystem mutation. Fake installation
// evidence models structure, NOT any production provenance or write right.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const vm=require("node:vm");
const {constants:C}=fs;
const root=path.resolve(__dirname,"../..");
const missing=require("./fixtures/TaskSourcePreflightM12t.cjs");
const first=require("./fixtures/TaskFirstCreateContractM12z.cjs");
function loadPolicy() {
    const ctx=vm.createContext({unescape,encodeURIComponent});
    const filename=path.join(root,"services/hub/ApolloHubTodoPolicy.js");
    vm.runInContext(fs.readFileSync(filename,"utf8")
                    .replace(/^\.pragma library\s*/,""),ctx,
                    {filename,timeout:1000});
    return ctx;
}
const policy=loadPolicy();
function fixture() {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"m12z-fixture-"));
    const folder=path.join(temp,"m12t-disposable");
    const backups=path.join(folder,"backups");
    fs.mkdirSync(folder,{mode:0o700});
    fs.mkdirSync(backups,{mode:0o700});
    const source=path.join(folder,first.SOURCE);
    return {temp,folder,backups,source,
        cleanup(){fs.rmSync(temp,{force:true,recursive:true});}};
}
const evidence=()=>({
    kind:"M12Z_FAKE_INSTALL_EVIDENCE",firstRun:true,
    generation:1,instanceId:"M12zFixture0001",sourceName:first.SOURCE
});
function plan(f,extras={}) {
    const absence=missing.classifyAbsent({
        folder:f.folder,declaredFreshInstall:true,policy
    });
    return first.prepare({absence,policy,evidence:evidence(),...extras});
}
function createExclusive(f,p) {
    // Node 'wx' is O_CREAT | O_EXCL. Additional O_NOFOLLOW prevents
    // following a pre-existing symlink at this synthetic source basename.
    const fd=fs.openSync(f.source,C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,0o600);
    try {
        fs.writeFileSync(fd,Buffer.from(p.expectedRaw,"utf8"));
        fs.fsyncSync(fd);
    } finally {fs.closeSync(fd);}
    const dirfd=fs.openSync(f.folder,C.O_RDONLY|C.O_DIRECTORY);
    try {fs.fsyncSync(dirfd);} finally {fs.closeSync(dirfd);}
    return {status:"EXCLUSIVELY_CREATED",noOverwrite:true,sourceName:first.SOURCE};
}
function independentReadback(f) {
    const fd=fs.openSync(f.source,C.O_RDONLY|C.O_NOFOLLOW);
    try {
        const st=fs.fstatSync(fd);
        assert.ok(st.isFile());
        assert.equal(st.nlink,1);
        assert.equal(st.mode & 0o077,0);
        return fs.readFileSync(fd);
    } finally {fs.closeSync(fd);}
}
function checkDenied(out) {
    assert.equal(out.writeAuthorized,false);
    assert.equal(out.bootstrapAuthorized,false);
    assert.equal(out.restoreAuthorized,false);
}
test("declared first install with fake evidence prepares candidate but no authority",()=>{
    const f=fixture();
    try {
        const p=plan(f);
        assert.equal(p.candidate,true,p.reason);
        assert.equal(p.reason,"SYNTHETIC_EXCLUSIVE_CREATE_CANDIDATE");
        assert.equal(p.credentialStatus,"FAKE_ONLY");
        checkDenied(p);
        assert.equal(fs.existsSync(f.source),false);
    } finally {f.cleanup();}
});
test("real exclusive-create syscall and independent readback prove SYNTHETIC receipt only",()=>{
    const f=fixture();
    try {
        const p=plan(f);
        assert.equal(p.candidate,true,p.reason);
        const receipt=createExclusive(f,p);
        const bytes=independentReadback(f);
        const result=first.observe({plan:p,exclusiveResult:receipt,readback:bytes,policy});
        assert.equal(result.simulatedConfirmed,true,result.reason);
        assert.equal(result.reason,"SYNTHETIC_CREATE_AND_READBACK");
        assert.equal(result.sourceSha256,p.sha256);
        checkDenied(result);
        assert.equal(missing.classifyAbsent({
            folder:f.folder,declaredFreshInstall:true,policy
        }).classification,"EXISTING_SOURCE");
    } finally {f.cleanup();}
});
test("second exclusive create refuses existing source and preserves original bytes",()=>{
    const f=fixture();
    try {
        const p=plan(f);
        createExclusive(f,p);
        const before=independentReadback(f);
        assert.throws(()=>createExclusive(f,p),e=>e && e.code==="EEXIST");
        assert.deepEqual(independentReadback(f),before);
    } finally {f.cleanup();}
});
test("lost acknowledgment after create requires readback or review, never automatic retry",()=>{
    const f=fixture();
    try {
        const p=plan(f);
        createExclusive(f,p);
        const absentReceipt=first.observe({plan:p,policy,readback:independentReadback(f)});
        assert.equal(absentReceipt.reason,"EXCLUSIVE_CREATE_NOT_PROVEN");
        checkDenied(absentReceipt);
        assert.throws(()=>createExclusive(f,p),e=>e && e.code==="EEXIST");
        assert.equal(missing.classifyAbsent({
            folder:f.folder,declaredFreshInstall:true,policy
        }).classification,"EXISTING_SOURCE");
    } finally {f.cleanup();}
});
test("missing final readback or changed bytes cannot be confirmed",()=>{
    const f=fixture();
    try {
        const p=plan(f);
        const receipt=createExclusive(f,p);
        assert.equal(first.observe({plan:p,exclusiveResult:receipt,policy})
                     .reason,"INDEPENDENT_READBACK_REQUIRED");
        fs.writeFileSync(f.source,Buffer.from("changed"),{flag:"w"});
        const result=first.observe({plan:p,exclusiveResult:receipt,
            readback:independentReadback(f),policy});
        assert.equal(result.reason,"READBACK_BYTES_MISMATCH");
        checkDenied(result);
    } finally {f.cleanup();}
});
test("existing source, dangling symlink, and backup history block candidate",()=>{
    for(const scenario of ["existing","dangling","backup","pending"]) {
        const f=fixture();
        try {
            if(scenario==="existing")
                fs.writeFileSync(f.source,"{}",{mode:0o600});
            if(scenario==="dangling")
                fs.symlinkSync("missing-target",f.source);
            if(scenario==="backup")
                fs.writeFileSync(path.join(f.backups,"backup-old"),"history",{mode:0o600});
            if(scenario==="pending")
                fs.writeFileSync(path.join(f.backups,".pending-old"),"history",{mode:0o600});
            const p=plan(f);
            assert.equal(p.candidate,false,scenario);
            assert.equal(p.reason,"ABSENCE_REVIEW_REQUIRED");
            checkDenied(p);
        } finally {f.cleanup();}
    }
});
test("missing, wrong, or stale synthetic attestation never prepares candidate",()=>{
    const f=fixture();
    try {
        const cases=[null,{}, {...evidence(),kind:"REAL_INSTALL"},
            {...evidence(),generation:2},
            {...evidence(),firstRun:false},
            {...evidence(),instanceId:"x"},
            {...evidence(),sourceName:"other.json"}];
        for(const item of cases) {
            const p=plan(f,{evidence:item});
            assert.equal(p.candidate,false);
            assert.equal(p.reason,"SYNTHETIC_INSTALL_EVIDENCE_REQUIRED");
            checkDenied(p);
        }
        const a=missing.classifyAbsent({
            folder:f.folder,declaredFreshInstall:false,policy
        });
        const p=first.prepare({absence:a,policy,evidence:evidence()});
        assert.equal(p.reason,"ABSENCE_REVIEW_REQUIRED");
        checkDenied(p);
    } finally {f.cleanup();}
});
test("forged or invalid settlement evidence remains fail closed",()=>{
    const f=fixture();
    try {
        const p=plan(f),bytes=Buffer.from(p.expectedRaw,"utf8");
        for(const receipt of [null,{},{
            status:"CREATED",noOverwrite:true,sourceName:first.SOURCE
        },{
            status:"EXCLUSIVELY_CREATED",noOverwrite:false,sourceName:first.SOURCE
        },{
            status:"EXCLUSIVELY_CREATED",noOverwrite:true,sourceName:"other.json"
        }]) {
            const outcome=first.observe({plan:p,exclusiveResult:receipt,
                                         readback:bytes,policy});
            assert.equal(outcome.simulatedConfirmed,false);
            checkDenied(outcome);
        }
        const tampered={...p,sha256:"0".repeat(64)};
        assert.equal(first.observe({plan:tampered,exclusiveResult:{
            status:"EXCLUSIVELY_CREATED",noOverwrite:true,sourceName:first.SOURCE
        },readback:bytes,policy}).reason,"CANDIDATE_INTEGRITY_MISMATCH");
    } finally {f.cleanup();}
});
test("test-only source is never imported or enabled by the production writer",()=>{
    const contract=fs.readFileSync(path.join(root,
        "tests/tasks/fixtures/TaskFirstCreateContractM12z.cjs"),"utf8");
    const store=fs.readFileSync(path.join(root,
        "services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(root,"shell.qml"),"utf8");
    assert.doesNotMatch(contract,/\bfs\s*\.\s*(?:write|rename|unlink|rmSync|openSync|mkdir)/);
    assert.doesNotMatch(store,/TaskFirstCreateContractM12z|M12Z_FAKE_INSTALL_EVIDENCE/);
    assert.doesNotMatch(shell,/TaskFirstCreateContractM12z/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((store.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(store,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(store,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
});
