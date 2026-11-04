#!/usr/bin/env node
"use strict";
// M13o tests operate exclusively inside newly created /tmp fake-only roots.
// No real TASKS storage, home config, login bus or Secret Service access.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const cp=require("node:child_process");
const crypto=require("node:crypto");
const model=require("./fixtures/TaskEncryptedDraftTransactionM13m.cjs");
const store=require("./fixtures/TaskEncryptedDraftPrivateStorageM13o.cjs");
const ROOT=path.resolve(__dirname,"../..");
function scratch(t){
    const root=fs.mkdtempSync(path.join(os.tmpdir(),"postapollo-m13o-disposable-"));
    fs.chmodSync(root,0o700);
    t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
    return root;
}
function scenario(){
    const source={kind:"M13M_FAKE_SOURCE",generation:7,
        raw:JSON.stringify({kind:"M13M_FAKE_TASKS_JSON",
            documentVersion:3,marker:"FAKE_CONFIRM_SOURCE"})};
    const ledger={kind:"M13M_FAKE_LEDGER",installationId:"FAKEINSTALL001",
        epoch:7,sourceGeneration:7,
        sourceDigest:crypto.createHash("sha256").update(source.raw).digest("hex"),
        latestCommittedSeq:0};
    const identity={installationId:"FAKEINSTALL001",epoch:7,
        stageId:"m13a-FAKEINSTALL001-7-1",surface:"HUB"};
    const draft={kind:"M13M_FAKE_EDITOR_DRAFT",surface:"HUB",
        value:"FAKE_PENDING_UNSAVED_DRAFT"};
    return {source,ledger,identity,draft,key:crypto.randomBytes(32)};
}
function prepared(s,checkpointSeq=1,overrides={}){
    const out=model.createSyntheticCheckpoint({
        source:s.source,ledger:s.ledger,identity:s.identity,draft:s.draft,
        key:s.key,optedIn:true,checkpointSeq,...overrides});
    assert.equal(out.ok,true,out.status);
    return out;
}
function powerless(out){
    for(const name of Object.keys(store.NO_POWER))
        assert.equal(out[name],false,name);
    assert.equal(out.productionActivation,false);
    assert.equal(out.persistAuthorized,false);
    assert.equal(out.restoreAuthorized,false);
}
test("private checkpoint uses one 0600 file and survives fresh process read",t=>{
    const root=scratch(t),s=scenario();
    try{
        const p=prepared(s);
        const wrote=store.commitFake({root,prepared:p,expectedPreviousSequence:0});
        assert.equal(wrote.ok,true,wrote.status);
        powerless(wrote);
        assert.equal(wrote.status,"SIMULATED_PRIVATE_ATOMIC_RENAME_AND_READBACK_PASS");
        assert.equal(wrote.fakeSequence,1);
        const file=path.join(root,"checkpoint.json");
        const st=fs.lstatSync(file);
        assert.equal(st.mode&0o777,0o600);
        assert.equal(st.nlink,1);
        const raw=fs.readFileSync(file,"utf8");
        assert.ok(!raw.includes(s.draft.value));
        assert.ok(!raw.includes(s.source.raw));
        assert.ok(!raw.includes(s.key.toString("base64")));
        assert.equal(JSON.parse(raw).kind,"M13O_FAKE_PRIVATE_CHECKPOINT");
        assert.equal(fs.existsSync(path.join(root,"writer.lock")),false);
        assert.deepEqual(fs.readdirSync(root),["checkpoint.json"]);
        const locked=store.inspectFake({root});
        assert.equal(locked.ok,true);
        assert.equal(locked.status,"SIMULATED_LOCKED_CIPHERTEXT_ONLY");
        assert.equal(locked.fakeSequence,1);
        assert.equal(Object.hasOwn(locked,"fakePreviewMarker"),false);
        powerless(locked);
        const code="const m=require("+JSON.stringify(path.join(ROOT,
            "tests/tasks/fixtures/TaskEncryptedDraftPrivateStorageM13o.cjs"))+
            ");const v=m.inspectFake({root:process.argv[1]});"+
            "if(!v.ok||v.fakeSequence!==1||v.restoreAuthorized!==false)process.exit(1);"+
            "console.log('M13O_FRESH_PROCESS_LOCKED_ONLY_PASS');";
        const fresh=cp.spawnSync(process.execPath,["-e",code,root],{
            encoding:"utf8",timeout:10000});
        assert.equal(fresh.status,0,fresh.stdout+"\n"+fresh.stderr);
        assert.equal(fresh.stdout.trim(),"M13O_FRESH_PROCESS_LOCKED_ONLY_PASS");
    }finally{s.key.fill(0);}
});
test("stale save cannot overwrite a newer committed fake checkpoint",t=>{
    const root=scratch(t),s=scenario();
    try{
        const p1=prepared(s),r1=store.commitFake({
            root,prepared:p1,expectedPreviousSequence:0});
        assert.equal(r1.ok,true,r1.status);
        const p2=prepared(s,2,{ledger:p1.proposedLedger});
        const stale=store.commitFake({
            root,prepared:p2,expectedPreviousSequence:0});
        assert.equal(stale.status,"SIMULATED_SEQUENCE_NOT_NEXT");
        powerless(stale);
        const r2=store.commitFake({
            root,prepared:p2,expectedPreviousSequence:1});
        assert.equal(r2.ok,true,r2.status);
        assert.equal(r2.fakeSequence,2);
        const replay=store.commitFake({
            root,prepared:p1,expectedPreviousSequence:0});
        assert.equal(replay.ok,false);
        assert.equal(replay.status,"SIMULATED_STALE_WRITER");
        powerless(replay);
        const active=store.inspectFake({root});
        assert.equal(active.fakeSequence,2);
        powerless(active);
    }finally{s.key.fill(0);}
});
test("source anchor change and installation change block replacement",t=>{
    const root=scratch(t),s=scenario();
    try{
        const p=prepared(s);
        assert.equal(store.commitFake({
            root,prepared:p,expectedPreviousSequence:0}).ok,true);
        const altered={...s.source,
            raw:JSON.stringify({kind:"M13M_FAKE_TASKS_JSON",
                documentVersion:3,marker:"FAKE_CHANGED_SOURCE"})};
        const nextLedger={...p.proposedLedger,sourceDigest:
            crypto.createHash("sha256").update(altered.raw).digest("hex")};
        const next=prepared(s,2,{source:altered,ledger:nextLedger});
        const changed=store.commitFake({
            root,prepared:next,expectedPreviousSequence:1});
        assert.equal(changed.status,"SIMULATED_SOURCE_ANCHOR_CHANGED");
        powerless(changed);
        const newId=prepared(s,2,{ledger:{
            ...p.proposedLedger,installationId:"FAKEINSTALL002"},
            identity:{...s.identity,installationId:"FAKEINSTALL002"}});
        const other=store.commitFake({
            root,prepared:newId,expectedPreviousSequence:1});
        assert.equal(other.status,"SIMULATED_INSTALLATION_OR_EPOCH_CHANGED");
        powerless(other);
        assert.equal(store.inspectFake({root}).fakeSequence,1);
    }finally{s.key.fill(0);}
});
test("non-private paths, public directory permissions and untrusted records refuse",t=>{
    const root=scratch(t),s=scenario();
    try{
        const p=prepared(s);
        for(const bad of [os.tmpdir(),path.join(root,"subdir"),"/var/tmp/fake"]) {
            const v=store.commitFake({
                root:bad,prepared:p,expectedPreviousSequence:0});
            assert.equal(v.status,"DISPOSABLE_ROOT_REQUIRED");
            powerless(v);
        }
        fs.chmodSync(root,0o755);
        const exposed=store.commitFake({
            root,prepared:p,expectedPreviousSequence:0});
        assert.equal(exposed.status,"DISPOSABLE_ROOT_REQUIRED");
        powerless(exposed);
        fs.chmodSync(root,0o700);
        const pathName=path.join(root,"checkpoint.json");
        fs.writeFileSync(pathName,"{}",{mode:0o600});
        const corrupt=store.commitFake({
            root,prepared:p,expectedPreviousSequence:0});
        assert.equal(corrupt.status,"SIMULATED_EXISTING_RECORD_UNTRUSTED");
        powerless(corrupt);
        fs.unlinkSync(pathName);
        const target=path.join(root,"fixture-target");
        fs.writeFileSync(target,"NEVER_TOUCH_THIS_FAKE_FILE",{mode:0o600});
        fs.symlinkSync(target,pathName);
        const symlink=store.inspectFake({root});
        assert.equal(symlink.status,"SIMULATED_RECORD_UNTRUSTED");
        powerless(symlink);
        const refused=store.commitFake({
            root,prepared:p,expectedPreviousSequence:0});
        assert.equal(refused.status,"SIMULATED_EXISTING_RECORD_UNTRUSTED");
        assert.equal(fs.readFileSync(target,"utf8"),"NEVER_TOUCH_THIS_FAKE_FILE");
    }finally{s.key.fill(0);}
});
test("concurrent lock or leftover lock refuses; never steals stale lock",t=>{
    const root=scratch(t),s=scenario();
    try{
        fs.mkdirSync(path.join(root,"writer.lock"),{mode:0o700});
        const p=prepared(s);
        const locked=store.commitFake({
            root,prepared:p,expectedPreviousSequence:0});
        assert.equal(locked.status,"SIMULATED_LOCK_BUSY_OR_LEFTOVER");
        powerless(locked);
        const inspect=store.inspectFake({root});
        assert.equal(inspect.status,"SIMULATED_LOCK_BUSY_OR_LEFTOVER");
        powerless(inspect);
        assert.ok(fs.existsSync(path.join(root,"writer.lock")));
        fs.rmdirSync(path.join(root,"writer.lock"));
        assert.equal(store.commitFake({
            root,prepared:p,expectedPreviousSequence:0}).ok,true);
    }finally{s.key.fill(0);}
});
test("explicit clear requires current sequence and leaves no ciphertext",t=>{
    const root=scratch(t),s=scenario();
    try{
        const p=prepared(s);
        assert.equal(store.commitFake({
            root,prepared:p,expectedPreviousSequence:0}).ok,true);
        const no=store.clearFake({root,expectedSequence:1,confirmed:false});
        assert.equal(no.status,"SIMULATED_EXPLICIT_CLEAR_REQUIRED");powerless(no);
        const stale=store.clearFake({root,expectedSequence:2,confirmed:true});
        assert.equal(stale.status,"SIMULATED_STALE_CLEAR");powerless(stale);
        assert.equal(store.inspectFake({root}).ok,true);
        const done=store.clearFake({root,expectedSequence:1,confirmed:true});
        assert.equal(done.ok,true,done.status);
        assert.equal(done.status,"SIMULATED_EXPLICIT_CIPHERTEXT_CLEAR_PASS");
        powerless(done);
        assert.equal(fs.readdirSync(root).length,0);
        const absent=store.inspectFake({root});
        assert.equal(absent.status,"SIMULATED_NO_CHECKPOINT");
        powerless(absent);
    }finally{s.key.fill(0);}
});
test("production code remains unchanged and no real keyring/path access",()=>{
    const file=fs.readFileSync(path.join(ROOT,
        "tests/tasks/fixtures/TaskEncryptedDraftPrivateStorageM13o.cjs"),"utf8");
    const storeQml=fs.readFileSync(path.join(ROOT,
        "services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(ROOT,"shell.qml"),"utf8");
    assert.match(file,/O_CREAT\|C\.O_EXCL\|C\.O_NOFOLLOW/);
    assert.match(file,/fs\.fsyncSync\(fd\)/);
    assert.match(file,/fs\.renameSync\(temp/);
    assert.match(file,/syncDir\(root\)/);
    assert.match(file,/SIMULATED_STALE_WRITER/);
    assert.match(file,/SIMULATED_SOURCE_ANCHOR_CHANGED/);
    assert.doesNotMatch(file,/secret-tool|gnome-keyring|DBUS_SESSION_BUS_ADDRESS|sudo|Quickshell\.dataDir|apollo-hub-todo-v1\.json/);
    assert.doesNotMatch(storeQml,/TaskEncryptedDraftPrivateStorageM13o/);
    assert.doesNotMatch(shell,/TaskEncryptedDraftPrivateStorageM13o/);
    assert.equal((storeQml.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((storeQml.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    for(const name of ["guardedWriterEnabled","ticketProducerEnabled",
        "encryptedRecoveryEnabled","encryptedDraftHostEnabled"])
        assert.match(storeQml,new RegExp("readonly property bool "+name+":\\s*false"));
});
