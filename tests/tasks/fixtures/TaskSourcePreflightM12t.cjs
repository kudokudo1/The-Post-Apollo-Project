"use strict";

/*
 * TASKS M12t // CI-ONLY source/backup/ticket *observation* boundary.
 *
 * Reuse M10e's committed, verified backup rather than creating a new
 * backup engine. This module is never loaded by Quickshell or a production
 * process. It ONLY reads a caller-created private m12t-disposable fixture.
 * A positive result is NOT write authority: no lock, stage reservation,
 * authenticated host, live source verification, or atomic CAS is provided.
 */
const fs=require("node:fs");
const path=require("node:path");
const {constants: C}=fs;
const m10e=require("./verified_backup_restore_fixture.cjs");

const SOURCE="apollo-hub-todo-v1.json";
function refuse(reason) {
    return {ok:false,reason,writeAuthorized:false};
}
function privateRegularFile(file) {
    const st=fs.lstatSync(file);
    if(!st.isFile() || st.isSymbolicLink() || st.nlink!==1
            || (st.mode & 0o077)!==0
            || (typeof process.getuid==="function" && st.uid!==process.getuid()))
        throw Error("UNSAFE_SOURCE_FILE");
    // O_NOFOLLOW is only a bounded safeguard. Another same-user process
    // may still change the name between checks; no OS fencing is claimed.
    const fd=fs.openSync(file,C.O_RDONLY|C.O_NOFOLLOW);
    try {
        const fst=fs.fstatSync(fd);
        if(fst.ino!==st.ino || fst.dev!==st.dev || fst.nlink!==1
                || (fst.mode & 0o077)!==0)
            throw Error("SOURCE_IDENTITY_CHANGED");
        return fs.readFileSync(fd);
    } finally {fs.closeSync(fd);}
}
function inspect({folder,backupId,expectedSourceSha,plan,policy}) {
    // Hard-coded nonproduction fixture boundary. No generic filesystem
    // inspector, plugin, host or production path is exposed.
    if(typeof folder!=="string" || !path.isAbsolute(folder)
            || path.normalize(folder)!==folder
            || path.basename(folder)!=="m12t-disposable")
        return refuse("SYNTHETIC_DIRECTORY_REQUIRED");
    if(typeof backupId!=="string" || !/^[A-Za-z0-9_-]{1,64}$/.test(backupId))
        return refuse("INVALID_BACKUP_ID");
    if(typeof expectedSourceSha!=="string"
            || !/^[a-f0-9]{64}$/.test(expectedSourceSha))
        return refuse("EXPECTED_BASELINE_REQUIRED");
    if(!plan || plan.admitted!==true || plan.state!=="WRITING"
            || !plan.baseline || !plan.expectedRaw
            || !policy || typeof policy.parse!=="function"
            || typeof policy.view!=="function")
        return refuse("VALID_TICKET_PLAN_REQUIRED");
    try {
        const rootSt=fs.lstatSync(folder);
        if(!rootSt.isDirectory() || rootSt.isSymbolicLink()
                || (rootSt.mode & 0o077)!==0
                || (typeof process.getuid==="function"
                    && rootSt.uid!==process.getuid()))
            return refuse("UNSAFE_SYNTHETIC_DIRECTORY");
        const source=path.join(folder,SOURCE);
        const backupDir=path.join(folder,"backups");
        const backups=fs.lstatSync(backupDir);
        if(!backups.isDirectory() || backups.isSymbolicLink()
                || (backups.mode & 0o077)!==0
                || (typeof process.getuid==="function"
                    && backups.uid!==process.getuid()))
            return refuse("UNSAFE_BACKUP_ROOT");
        const first=privateRegularFile(source);
        if(!first.length || first.length>1048576)
            return refuse("INVALID_SOURCE_LENGTH");
        const firstSha=m10e.sha256(first);
        if(firstSha!==expectedSourceSha)
            return refuse("SOURCE_BASELINE_MISMATCH");
        // M10e.verifyBackup is the existing authoritative *synthetic*
        // backup verification, including SHA256/size/manifest comparisons.
        const backup=m10e.verifyBackup(
            path.join(backupDir,"backup-"+backupId));
        if(backup.manifest.id!==backupId
                || backup.manifest.sourceName!==SOURCE
                || backup.manifest.sha256!==expectedSourceSha
                || !backup.bytes.equals(first))
            return refuse("BACKUP_SOURCE_MISMATCH");
        const parsed=policy.parse(first.toString("utf8"));
        if(!parsed || parsed.ok!==true)
            return refuse("INVALID_TASK_SOURCE");
        const state=parsed.document.tasks.length ? "ready":"empty";
        const view=policy.view(state,parsed.document,"");
        if(JSON.stringify(view)!==JSON.stringify(plan.baseline))
            return refuse("PLANNED_BASELINE_MISMATCH");
        const candidate=policy.parse(plan.expectedRaw);
        if(!candidate || candidate.ok!==true)
            return refuse("INVALID_TICKET_CANDIDATE");
        const reread=privateRegularFile(source);
        if(!reread.equals(first))
            return refuse("SOURCE_CHANGED_DURING_PREFLIGHT");
        // This observation never issues stage, changes FileView, acquires
        // write authority or claims it can prevent a race after return.
        return {ok:true,reason:"SYNTHETIC_SOURCE_BACKUP_MATCH",
                writeAuthorized:false,sourceSha256:firstSha,
                bytes:first.length,ticketId:plan.ticketId};
    } catch (e) {
        const code=e&&e.message||"SOURCE_READ_FAILED";
        // All OS and unexpected errors fail closed without exposing private
        // fixture path in a returned result.
        return refuse([
            "UNSAFE_SOURCE_FILE","SOURCE_IDENTITY_CHANGED",
            "SOURCE_READ_FAILED","INVALID_MANIFEST_JSON",
            "INVALID_MANIFEST","BACKUP_HASH_MISMATCH",
            "NOT_REGULAR_FILE","UNTRUSTED_DIRECTORY"
        ].includes(code)?code:"PREFLIGHT_UNAVAILABLE");
    }
}
module.exports={inspect,SOURCE};
