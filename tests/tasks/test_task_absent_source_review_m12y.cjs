#!/usr/bin/env node
"use strict";
// TASKS M12y: synthetic read-only missing-source triage. No QML/native call,
// no production data, no restore and absolutely no bootstrap write authority.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const os=require("node:os");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const gate=require("./fixtures/TaskSourcePreflightM12t.cjs");
const backup=require("./fixtures/verified_backup_restore_fixture.cjs");
const sourcePath=path.join(root,"services/hub/ApolloHubTodoPolicy.js");
function loadPolicy() {
    const context=vm.createContext({unescape,encodeURIComponent});
    vm.runInContext(fs.readFileSync(sourcePath,"utf8")
                    .replace(/^\.pragma library\s*/,""),
                    context,{timeout:1000,filename:sourcePath});
    return context;
}
const policy=loadPolicy();
function fixture() {
    const temp=fs.mkdtempSync(path.join(os.tmpdir(),"m12y-review-"));
    const folder=path.join(temp,"m12t-disposable");
    const backupDir=path.join(folder,"backups");
    fs.mkdirSync(folder,{mode:0o700});
    fs.mkdirSync(backupDir,{mode:0o700});
    const source=path.join(folder,gate.SOURCE);
    const bytes=Buffer.from(JSON.stringify(policy.emptyDocument(),null,2)+"\n");
    return {
        temp,folder,backupDir,source,bytes,
        inputs(declaredFreshInstall=true) {
            return {folder,declaredFreshInstall,policy};
        },
        cleanup() {fs.rmSync(temp,{force:true,recursive:true});}
    };
}
function review(input) {
    const result=gate.classifyAbsent(input);
    assert.equal(result.ok,false);
    assert.equal(result.writeAuthorized,false);
    assert.equal(result.bootstrapAuthorized,false);
    assert.equal(result.restoreAuthorized,false);
    return result;
}

test("declared empty installation is still merely a candidate for review",()=>{
    const f=fixture();
    try {
        const result=review(f.inputs());
        assert.equal(result.classification,"POSSIBLE_FRESH_INSTALL");
        assert.equal(result.reason,"INDEPENDENT_INSTALL_PROVENANCE_REQUIRED");
        assert.equal(fs.existsSync(f.source),false);
        assert.equal(fs.readdirSync(f.backupDir).length,0);
    } finally {f.cleanup();}
});
test("missing file with no first-install declaration means recovery review",()=>{
    const f=fixture();
    try {
        const result=review(f.inputs(false));
        assert.equal(result.classification,"MISSING_SOURCE_REVIEW");
        assert.equal(result.reason,"FRESH_INSTALL_NOT_DECLARED");
        assert.equal(fs.existsSync(f.source),false);
    } finally {f.cleanup();}
});
test("existing file and dangling symlink never become a new install",()=>{
    for(const variant of ["real","dangling"]) {
        const f=fixture();
        try {
            if(variant==="real") fs.writeFileSync(f.source,f.bytes,{mode:0o600});
            else fs.symlinkSync("does-not-exist",f.source);
            const result=review(f.inputs());
            assert.equal(result.classification,"EXISTING_SOURCE");
            assert.equal(result.reason,"SOURCE_EXISTS_USE_EXISTING_PREFLIGHT");
        } finally {f.cleanup();}
    }
});
test("committed source backup plus missing source is history, not empty boot",()=>{
    const f=fixture();
    try {
        fs.writeFileSync(f.source,f.bytes,{mode:0o600});
        backup.capture(f.source,f.backupDir,"checkpoint001");
        fs.unlinkSync(f.source);
        const result=review(f.inputs());
        assert.equal(result.classification,"MISSING_SOURCE_REVIEW");
        assert.equal(result.reason,"BACKUP_OR_PENDING_HISTORY_PRESENT");
        assert.equal(fs.existsSync(f.source),false);
        assert.deepEqual(backup.verifyBackup(
            path.join(f.backupDir,"backup-checkpoint001")).bytes,f.bytes);
    } finally {f.cleanup();}
});
test("incomplete or unrecognized backup artifact still blocks fresh boot",()=>{
    for(const name of [".pending-stage001","suspicious.txt"]) {
        const f=fixture();
        try {
            fs.writeFileSync(path.join(f.backupDir,name),"not trusted",{mode:0o600});
            const result=review(f.inputs());
            assert.equal(result.classification,"MISSING_SOURCE_REVIEW");
            assert.equal(result.reason,"BACKUP_OR_PENDING_HISTORY_PRESENT");
        } finally {f.cleanup();}
    }
});
test("unsafe or missing synthetic directories refuse closed",()=>{
    for(const variant of ["bad-root","bad-backup","missing-backup"]) {
        const f=fixture();
        try {
            if(variant==="bad-root") fs.chmodSync(f.folder,0o755);
            if(variant==="bad-backup") fs.chmodSync(f.backupDir,0o755);
            if(variant==="missing-backup") fs.rmdirSync(f.backupDir);
            const result=review(f.inputs());
            assert.equal(result.classification,"REFUSE");
            if(variant==="bad-root")
                assert.equal(result.reason,"UNSAFE_SYNTHETIC_DIRECTORY");
            if(variant==="bad-backup")
                assert.equal(result.reason,"UNSAFE_BACKUP_ROOT");
        } finally {f.cleanup();}
    }
});
test("wrong paths, missing declaration and invalid policy refuse",()=>{
    const f=fixture();
    try {
        for(const input of [
            {...f.inputs(),folder:f.temp},
            {...f.inputs(),folder:"m12t-disposable"},
            {...f.inputs(),declaredFreshInstall:"yes"},
            {...f.inputs(),policy:null},
            {...f.inputs(),policy:{emptyDocument(){return {}},
                validate(){return {ok:true};}}},
        ]) {
            const result=review(input);
            assert.equal(result.classification,"REFUSE");
        }
    } finally {f.cleanup();}
});
test("preflight remains read-only and production flags remain disabled",()=>{
    const store=fs.readFileSync(path.join(root,
          "services/hub/ApolloHubTodoStore.qml"),"utf8");
    const shell=fs.readFileSync(path.join(root,"shell.qml"),"utf8");
    const helper=fs.readFileSync(path.join(root,
          "tests/tasks/fixtures/TaskSourcePreflightM12t.cjs"),"utf8");
    assert.match(store,/readonly property bool ticketProducerEnabled:\s*false/);
    assert.match(store,/readonly property bool guardedWriterEnabled:\s*false/);
    assert.match(store,/readonly property bool independentlyAuthenticatedTicketReceipt:\s*false/);
    assert.equal((store.match(/\bFileView\s*\{/g)||[]).length,1);
    assert.doesNotMatch(shell,/TaskSourcePreflightM12t|classifyAbsent/);
    assert.doesNotMatch(helper,/fs\.write|fs\.rename|fs\.unlink|fs\.rmSync|execSync|spawn\(/);
    assert.match(helper,/writeAuthorized:false/);
});
