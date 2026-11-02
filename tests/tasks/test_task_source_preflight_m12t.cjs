#!/usr/bin/env node
"use strict";
/* M12t // Real policy + real M10e backup fixture + read-only ticket baseline.
 * No Quickshell launch, production TASKS path, or live filesystem writes.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const gate=require("./fixtures/TaskSourcePreflightM12t.cjs");
const backup=require("./fixtures/verified_backup_restore_fixture.cjs");
const load=p=>{
    const ctx=vm.createContext({unescape,encodeURIComponent});
    const src=fs.readFileSync(path.join(root,p),"utf8")
                .replace(/^\.pragma library\s*/,"");
    vm.runInContext(src,ctx,{filename:p,timeout:1000});
    return ctx;
};
const policy=load("services/hub/ApolloHubTodoPolicy.js");
const producer=load("services/hub/TaskLocalTicketProducerM12q.js");
function setup() {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"m12t-test-"));
    const folder=path.join(temp,"m12t-disposable");
    const backupRoot=path.join(folder,"backups");
    fs.mkdirSync(folder,{mode:0o700});
    fs.mkdirSync(backupRoot,{mode:0o700});
    const source=path.join(folder,gate.SOURCE);
    const original=Buffer.from(JSON.stringify(policy.emptyDocument(),null,2)+"\n");
    fs.writeFileSync(source,original,{mode:0o600});
    const expectedSourceSha=backup.sha256(original);
    const plan=producer.plan(policy,policy.emptyDocument(),"HUB","addTask",
          {title:"M12T_SYNTHETIC_ONLY"},1000,"M12tSyntheticSession01",1);
    assert.equal(plan.admitted,true,plan.reason);
    backup.capture(source,backupRoot,"checkpoint001");
    return {
        temp,folder,source,backupRoot,original,plan,expectedSourceSha,
        inputs(){return {folder,backupId:"checkpoint001",expectedSourceSha,
                          plan,policy};},
        cleanup(){fs.rmSync(temp,{recursive:true,force:true});}
    };
}
test("already committed M10e backup and matching planned baseline allow *observation* only",()=>{
    const s=setup();
    try {
        const before=fs.readFileSync(s.source);
        const result=gate.inspect(s.inputs());
        assert.equal(result.ok,true,result.reason);
        assert.equal(result.reason,"SYNTHETIC_SOURCE_BACKUP_MATCH");
        assert.equal(result.writeAuthorized,false);
        assert.equal(result.sourceSha256,s.expectedSourceSha);
        assert.equal(result.ticketId,s.plan.ticketId);
        assert.deepEqual(fs.readFileSync(s.source),before);
        assert.deepEqual(
            backup.verifyBackup(path.join(s.backupRoot,"backup-checkpoint001")).bytes,
            before);
        assert.equal(fs.existsSync(path.join(s.folder,"m12t-write-attempt")),false);
    } finally {s.cleanup();}
});
test("outside synthetic directory and missing independent pin always refuse",()=>{
    const s=setup();
    try {
        assert.equal(gate.inspect({...s.inputs(),folder:s.temp}).ok,false);
        assert.equal(gate.inspect({...s.inputs(),expectedSourceSha:""}).ok,false);
        assert.equal(gate.inspect({...s.inputs(),backupId:"../wrong"}).ok,false);
        assert.equal(gate.inspect({...s.inputs(),plan:null}).ok,false);
        assert.deepEqual(fs.readFileSync(s.source),s.original);
    } finally {s.cleanup();}
});
test("changed source is rejected before admission, even if policy remains valid",()=>{
    const s=setup();
    try {
        const newer=Buffer.from(JSON.stringify(policy.create(
            policy.emptyDocument(),"external edit",1001).document,null,2)+"\n");
        fs.writeFileSync(s.source,newer,{mode:0o600});
        const result=gate.inspect(s.inputs());
        assert.equal(result.ok,false);
        assert.equal(result.reason,"SOURCE_BASELINE_MISMATCH");
        assert.deepEqual(fs.readFileSync(s.source),newer);
        // Spoofing a fresh pin from the modified file does not alter the
        // original independently captured backup.
        const check=gate.inspect({...s.inputs(),expectedSourceSha:backup.sha256(newer)});
        assert.equal(check.reason,"BACKUP_SOURCE_MISMATCH");
    } finally {s.cleanup();}
});
test("corrupted retained backup refuses; no automatic restore is attempted",()=>{
    const s=setup();
    try {
        const backupPath=path.join(s.backupRoot,"backup-checkpoint001","original.bytes");
        fs.writeFileSync(backupPath,Buffer.from("corrupt"),{mode:0o600});
        const result=gate.inspect(s.inputs());
        assert.equal(result.ok,false);
        assert.equal(result.reason,"BACKUP_HASH_MISMATCH");
        assert.deepEqual(fs.readFileSync(s.source),s.original);
    } finally {s.cleanup();}
});
test("wrong planned baseline refuses even when backup and source agree",()=>{
    const s=setup();
    try {
        const different=policy.create(policy.emptyDocument(),"other",1000).document;
        const wrong=producer.plan(policy,different,"HUB","addTask",
              {title:"new"},2000,"M12tSyntheticSession01",2);
        assert.equal(wrong.admitted,true);
        const result=gate.inspect({...s.inputs(),plan:wrong});
        assert.equal(result.ok,false);
        assert.equal(result.reason,"PLANNED_BASELINE_MISMATCH");
    } finally {s.cleanup();}
});
test("malformed source with a separately captured backup still fails policy",()=>{
    const s=setup();
    try {
        const invalid=Buffer.from('{"version":999,"tasks":[]}\n');
        fs.writeFileSync(s.source,invalid,{mode:0o600});
        const replacementId="invalid001";
        backup.capture(s.source,s.backupRoot,replacementId);
        const result=gate.inspect({...s.inputs(),
            backupId:replacementId,expectedSourceSha:backup.sha256(invalid)});
        assert.equal(result.ok,false);
        assert.equal(result.reason,"INVALID_TASK_SOURCE");
    } finally {s.cleanup();}
});
test("missing source, symlink and hardlink refuse without writing",()=>{
    for(const kind of ["missing","symlink","hardlink"]) {
        const s=setup();
        try {
            if(kind==="missing") fs.unlinkSync(s.source);
            if(kind==="symlink") {
                fs.unlinkSync(s.source);
                fs.symlinkSync("backups/backup-checkpoint001/original.bytes",s.source);
            }
            if(kind==="hardlink") {
                fs.linkSync(s.source,path.join(s.folder,"another-hardlink"));
            }
            const result=gate.inspect(s.inputs());
            assert.equal(result.ok,false,kind);
            assert.equal(result.writeAuthorized,false);
        } finally {s.cleanup();}
    }
});
test("fixture remains unmounted, current writer and trust gates remain disabled",()=>{
    const src=fs.readFileSync(path.join(root,"services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(root,"shell.qml"),"utf8");
    const m12s=fs.readFileSync(path.join(root,"TaskNativeStoreSmokeM12s.qml"),"utf8");
    assert.equal((src.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.equal((src.match(/\btodoFile\.setText\s*\(/g)||[]).length,1);
    assert.equal((src.match(/return stage\(TodoPolicy\./g)||[]).length,9);
    assert.match(src,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(src,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(src,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
    assert.doesNotMatch(shell,/TaskSourcePreflightM12t/);
    assert.doesNotMatch(m12s,/TaskSourcePreflightM12t/);
    const module=fs.readFileSync(path.join(root,
        "tests/tasks/fixtures/TaskSourcePreflightM12t.cjs"),"utf8");
    assert.doesNotMatch(module,/fs\.write|fs\.rename|fs\.unlink|fs\.rmSync|execSync|spawn\(/);
});
