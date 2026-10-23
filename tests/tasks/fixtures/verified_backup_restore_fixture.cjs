"use strict";

// PROXY 1 M10e. THROWAWAY CI BACKUP/RESTORE FIXTURE ONLY.
// Never call this against the user's Quickshell storage. Its sole purpose
// is testing byte preservation, recovery gates and simulated crash windows.
// No auto-migration, no background cleanup, no remote or live write access.

const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
let counter=0;
const sha256=bytes=>crypto.createHash("sha256").update(bytes).digest("hex");
const validId=id=>typeof id==="string" && /^[a-zA-Z0-9_-]{1,64}$/.test(id);
function halt(at,requested) {
    if(at===requested) {
        const error=new Error("INJECTED_"+at);
        error.code=at==="disk-full"?"ENOSPC":
                   at==="permission-denied"?"EACCES":"INJECTED";
        throw error;
    }
}
function regularFile(file) {
    const st=fs.lstatSync(file);
    if(!st.isFile() || st.isSymbolicLink())
        throw new Error("NOT_REGULAR_FILE");
    return fs.readFileSync(file);
}
function directory(dir) {
    const st=fs.lstatSync(dir);
    if(!st.isDirectory() || st.isSymbolicLink())
        throw new Error("UNTRUSTED_DIRECTORY");
}
function syncDirectory(dir) {
    const fd=fs.openSync(dir,"r");
    try {fs.fsyncSync(fd);} finally {fs.closeSync(fd);}
}
function writeNewSynced(file,bytes) {
    const fd=fs.openSync(file,"wx",0o600);
    try {
        fs.writeFileSync(fd,bytes);
        fs.fsyncSync(fd);
    } finally {fs.closeSync(fd);}
}
function backupName(id) {
    if(!validId(id)) throw new Error("INVALID_BACKUP_ID");
    return "backup-"+id;
}
function verifyBackup(folder) {
    directory(folder);
    const info=regularFile(path.join(folder,"manifest.json"));
    let manifest;
    try {manifest=JSON.parse(info.toString("utf8"));}
    catch {throw new Error("INVALID_MANIFEST_JSON");}
    const names=manifest && typeof manifest==="object" && !Array.isArray(manifest)
        ? Object.keys(manifest).sort().join(","):"";
    if(names!=="bytes,format,id,sha256,sourceName"
        || manifest.format!==1 || !validId(manifest.id)
        || !Number.isSafeInteger(manifest.bytes) || manifest.bytes<0
        || typeof manifest.sha256!=="string"
        || !/^[a-f0-9]{64}$/.test(manifest.sha256)
        || typeof manifest.sourceName!=="string"
        || !/^[^/\\\0]+$/.test(manifest.sourceName)
        || path.basename(folder)!==backupName(manifest.id))
        throw new Error("INVALID_MANIFEST");
    const bytes=regularFile(path.join(folder,"original.bytes"));
    if(bytes.length!==manifest.bytes || sha256(bytes)!==manifest.sha256)
        throw new Error("BACKUP_HASH_MISMATCH");
    return {manifest,bytes};
}
// Atomically *publishes a complete backup directory*, after data + manifest
// have been individually written and fsynced. No existing backup overwritten.
// Injection after rename means result is UNCERTAIN until verifyBackup().
// Assumes one owner and stable source while capturing; NOT a locking scheme.
function capture(sourceFile,backupRoot,id,stopAt) {
    directory(backupRoot);
    backupName(id);
    const initial=regularFile(sourceFile);
    const sourceName=path.basename(sourceFile);
    const folder=path.join(backupRoot,backupName(id));
    const staging=path.join(backupRoot,".pending-"+id);
    if(fs.existsSync(folder) || fs.existsSync(staging))
        throw new Error("BACKUP_ID_ALREADY_RESERVED");
    halt("permission-denied",stopAt);
    fs.mkdirSync(staging,{mode:0o700});
    halt("after-create",stopAt);
    halt("disk-full",stopAt);
    writeNewSynced(path.join(staging,"original.bytes"),initial);
    halt("after-source-copy",stopAt);
    const manifest={
        format:1,id,sourceName,bytes:initial.length,sha256:sha256(initial)
    };
    writeNewSynced(path.join(staging,"manifest.json"),
        Buffer.from(JSON.stringify(manifest)+"\n","utf8"));
    halt("after-manifest",stopAt);
    const reread=regularFile(sourceFile);
    if(sha256(reread)!==manifest.sha256 || reread.length!==initial.length)
        throw new Error("SOURCE_CHANGED_DURING_BACKUP");
    const staged=regularFile(path.join(staging,"original.bytes"));
    if(sha256(staged)!==manifest.sha256)
        throw new Error("BACKUP_READBACK_MISMATCH");
    syncDirectory(staging);
    halt("before-commit",stopAt);
    fs.renameSync(staging,folder);
    halt("after-commit",stopAt);
    syncDirectory(backupRoot);
    halt("after-root-sync",stopAt);
    return {folder,...verifyBackup(folder)};
}
// Standalone test-only restore gate. Requires an explicit fingerprint of the
// present target and a validated backup. Production restore additionally
// requires operator approval, a stop-the-world writer lock and a migration
// rollback plan. Never silently replace an unexpectedly modified target.
function restore(folder,targetFile,expectedCurrentHash,stopAt) {
    const {bytes,manifest}=verifyBackup(folder);
    if(typeof expectedCurrentHash!=="string"
            || !/^[a-f0-9]{64}$/.test(expectedCurrentHash))
        throw new Error("EXPECTED_HASH_REQUIRED");
    const before=regularFile(targetFile);
    if(sha256(before)!==expectedCurrentHash)
        throw new Error("STALE_TARGET_HASH");
    const parent=path.dirname(targetFile);
    directory(parent);
    const candidate=path.join(parent,
        "."+path.basename(targetFile)+".m10e-"+process.pid+"-"+(++counter));
    halt("permission-denied",stopAt);
    halt("disk-full",stopAt);
    writeNewSynced(candidate,bytes);
    halt("after-restore-write",stopAt);
    if(sha256(regularFile(candidate))!==manifest.sha256)
        throw new Error("RESTORE_CANDIDATE_MISMATCH");
    const latest=regularFile(targetFile);
    if(sha256(latest)!==expectedCurrentHash)
        throw new Error("TARGET_CHANGED_DURING_RESTORE");
    halt("before-restore-commit",stopAt);
    fs.renameSync(candidate,targetFile);
    halt("after-restore-commit",stopAt);
    syncDirectory(parent);
    halt("after-restore-sync",stopAt);
    return {ok:true,sha256:manifest.sha256,bytes:manifest.bytes};
}
module.exports={sha256,verifyBackup,capture,restore};
