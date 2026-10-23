#!/usr/bin/env node
"use strict";
// PROXY 1 / M10e. All file operations occur ONLY in mkdtempSync-owned
// throwaway fixture directories inside CI, never in the user's desktop.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const fixture=require("./fixtures/verified_backup_restore_fixture.cjs");
const root=fs.mkdtempSync(path.join(os.tmpdir(),"tasks-m10e-fixture-"));
function directory(name) {
    const p=path.join(root,name);
    fs.mkdirSync(p);
    return p;
}
let testCount=0;
function specimen(label) {
    const dir=directory("specimen-"+(++testCount)+"-"+label);
    const source=path.join(dir,"apollo-hub-todo-v1.json");
    const backups=path.join(dir,"backups");
    fs.mkdirSync(backups);
    // Preserve unusual whitespace, UTF-8, timestamps, unknown extension.
    // Backup happens BEFORE migration validation. The migration can refuse
    // a future unknown field without losing the original raw source.
    const raw=Buffer.from(
        '{\n  "version": 3,\n  "nextId": 13, \n' +
        '  "projects": [{"id":"p2","name":"日本語 🔒",'+
        '"createdAtMs":1700000000000,"updatedAtMs":1700000000123}],\n'+
        '  "tasks": [{"id":"t12","title":"Restore test",'+
        '"done":false,"createdAtMs":1700000000000,'+
        '"updatedAtMs":1700000000888,"priority":"high",'+
        '"description":"caf\u00e9","dueDate":"2026-10-23","projectId":"p2"}],\n'+
        '  "nextProjectId": 8,\n  "futureField": "keep original bytes"\n}\n',"utf8");
    fs.writeFileSync(source,raw);
    return {dir,source,backups,raw};
}
function injected(fn,marker) {
    assert.throws(fn,err=>err.message==="INJECTED_"+marker,
        "missing "+marker+" injected interruption");
}
try {
    const normal=specimen("normal");
    const before=fs.readFileSync(normal.source);
    const backed=fixture.capture(normal.source,normal.backups,"snapshot001");
    assert.equal(backed.manifest.format,1);
    assert.equal(backed.manifest.id,"snapshot001");
    assert.equal(backed.manifest.bytes,normal.raw.length);
    assert.equal(backed.manifest.sha256,fixture.sha256(normal.raw));
    assert.deepEqual(backed.bytes,normal.raw,"backup must be byte-exact");
    assert.deepEqual(fs.readFileSync(normal.source),before,
        "source must remain exactly unchanged");
    const verified=fixture.verifyBackup(backed.folder);
    assert.deepEqual(verified.bytes,normal.raw);
    assert.equal(fs.statSync(backed.folder).isDirectory(),true);
    assert.equal(fs.statSync(path.join(backed.folder,"original.bytes")).mode & 0o777,0o600);
    assert.equal(fs.statSync(backed.folder).mode & 0o777,0o700);
    assert.throws(()=>fixture.capture(normal.source,normal.backups,"snapshot001"),
        /BACKUP_ID_ALREADY_RESERVED/,"backup never overwrites an ID");

    // Each simulated crash boundary leaves the committed backup name absent
    // before rename, or fully verifiable after rename. Uncommitted staging
    // leftovers are *never* treated as a committed backup.
    for(const [stage,committed] of [
        ["permission-denied",false],
        ["disk-full",false],
        ["after-create",false],
        ["after-source-copy",false],
        ["after-manifest",false],
        ["before-commit",false],
        ["after-commit",true],
        ["after-root-sync",true]
    ]) {
        const v=specimen(stage);
        injected(()=>fixture.capture(v.source,v.backups,"backup1",stage),stage);
        const committedDir=path.join(v.backups,"backup-backup1");
        assert.equal(fs.existsSync(committedDir),committed,stage);
        if(committed) {
            const recovered=fixture.verifyBackup(committedDir);
            assert.deepEqual(recovered.bytes,v.raw,stage);
        }
        assert.deepEqual(fs.readFileSync(v.source),v.raw,
            "never alter source on failed backup: "+stage);
    }
    // A failed capture leaves a reserved incomplete candidate; repeating
    // with the SAME ID must refuse instead of adopting incomplete backup.
    const interrupted=specimen("retry");
    injected(()=>fixture.capture(interrupted.source,interrupted.backups,
        "repeat","after-manifest"),"after-manifest");
    assert.throws(()=>fixture.capture(interrupted.source,
        interrupted.backups,"repeat"),/BACKUP_ID_ALREADY_RESERVED/);

    // Integrity checks reject wrong manifest checksum, wrong raw bytes,
    // altered manifest shape, symbolic links and invalid identifiers.
    const tampered=specimen("tamper");
    const backup=fixture.capture(tampered.source,tampered.backups,"safe");
    const rawCopy=fs.readFileSync(path.join(backup.folder,"original.bytes"));
    fs.appendFileSync(path.join(backup.folder,"original.bytes"),"intrusion");
    assert.throws(()=>fixture.verifyBackup(backup.folder),/BACKUP_HASH_MISMATCH/);
    fs.writeFileSync(path.join(backup.folder,"original.bytes"),rawCopy);
    const manPath=path.join(backup.folder,"manifest.json");
    const originalManifest=fs.readFileSync(manPath);
    fs.writeFileSync(manPath,'{"format":1,"id":"safe","sha256":"bad"}');
    assert.throws(()=>fixture.verifyBackup(backup.folder),/INVALID_MANIFEST/);
    fs.writeFileSync(manPath,originalManifest);
    const readlink=path.join(tampered.backups,"link");
    fs.symlinkSync(backup.folder,readlink);
    assert.throws(()=>fixture.verifyBackup(readlink),/UNTRUSTED_DIRECTORY/);
    assert.throws(()=>fixture.capture(tampered.source,tampered.backups,"../bad"),
        /INVALID_BACKUP_ID/);

    // Restoring to a changed target requires the expected current checksum.
    // A valid backup is NOT permission to replace unrelated or newer work.
    const restored=specimen("restore");
    const trusted=fixture.capture(restored.source,restored.backups,"original");
    const target=path.join(restored.dir,"working.json");
    const newer=Buffer.from('{"version":4,"pending":["op1"],"content":"NEW WORK"}\n');
    fs.writeFileSync(target,newer);
    assert.throws(()=>fixture.restore(trusted.folder,target,
        fixture.sha256(Buffer.from("wrong"))),/STALE_TARGET_HASH/);
    assert.deepEqual(fs.readFileSync(target),newer);
    assert.throws(()=>fixture.restore(trusted.folder,target,null),
        /EXPECTED_HASH_REQUIRED/);
    const result=fixture.restore(trusted.folder,target,fixture.sha256(newer));
    assert.equal(result.ok,true);
    assert.deepEqual(fs.readFileSync(target),restored.raw);
    assert.equal(result.sha256,fixture.sha256(restored.raw));

    for(const [stage,shouldRestore] of [
        ["permission-denied",false],
        ["disk-full",false],
        ["after-restore-write",false],
        ["before-restore-commit",false],
        ["after-restore-commit",true],
        ["after-restore-sync",true]
    ]) {
        const v=specimen("restore-"+stage);
        const safe=fixture.capture(v.source,v.backups,"x");
        const target=path.join(v.dir,"target.json");
        fs.writeFileSync(target,newer);
        injected(()=>fixture.restore(safe.folder,target,
            fixture.sha256(newer),stage),stage);
        assert.deepEqual(fs.readFileSync(target),
            shouldRestore?v.raw:newer,stage);
        if(shouldRestore)
            assert.equal(fixture.sha256(fs.readFileSync(target)),
                fixture.verifyBackup(safe.folder).manifest.sha256);
    }

    // Invalid backups cannot be restored; guard is checked before writing.
    const denied=specimen("no-restore-tamper");
    const b=fixture.capture(denied.source,denied.backups,"s");
    const target2=path.join(denied.dir,"destination.json");
    fs.writeFileSync(target2,newer);
    fs.appendFileSync(path.join(b.folder,"original.bytes"),"bad");
    assert.throws(()=>fixture.restore(b.folder,target2,fixture.sha256(newer)),
        /BACKUP_HASH_MISMATCH/);
    assert.deepEqual(fs.readFileSync(target2),newer);

    // Backups capture exact bytes even if later migration declines them.
    // No test reads any real Quickshell or user file.
    for(const forbidden of [
        "Quickshell.dataDir","gh project ","/var/home/mapple/",
        "ApolloHubTodoStore.qml","process.env.HOME"
    ]) {
        const code=fs.readFileSync(
            "tests/tasks/fixtures/verified_backup_restore_fixture.cjs","utf8");
        assert.equal(code.includes(forbidden),false,forbidden);
    }
    console.log("Proxy 1 M10e byte-perfect backup, restore and failure gates: PASS");
} finally {
    fs.rmSync(root,{recursive:true,force:true});
}
