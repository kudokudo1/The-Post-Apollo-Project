"use strict";

// PROXY 1 M10f: Node-only THROWAWAY test fixture for one cooperative writer.
// DO NOT use on live ApolloHubTodoStore or the user's Quickshell data.
// Creates only caller-selected fixture paths. No automatic stale-lock steal,
// no GitHub request, and no live integration with Quickshell's FileView.
const fs=require("node:fs");
const path=require("node:path");
const crypto=require("node:crypto");
let nonce=0;

function error(reason) { return {ok:false,reason}; }
function directory(dir) {
    const stat=fs.lstatSync(dir);
    if(!stat.isDirectory() || stat.isSymbolicLink())
        throw Error("UNTRUSTED_DIRECTORY");
}
function regular(file) {
    const stat=fs.lstatSync(file);
    if(!stat.isFile() || stat.isSymbolicLink())
        throw Error("UNTRUSTED_FILE");
    return fs.readFileSync(file);
}
function fsyncDirectory(dir) {
    const fd=fs.openSync(dir,"r");
    try { fs.fsyncSync(fd); } finally {fs.closeSync(fd);}
}
function sha256(bytes) {
    return crypto.createHash("sha256").update(bytes).digest("hex");
}
function inject(at,stopAt) {
    if(at===stopAt) {
        const e=Error("INJECTED_"+at);
        e.code="INJECTED";
        throw e;
    }
}
function lockPath(file) { return file+".m10f-lock"; }

function acquire(file) {
    // mkdir is exclusive on local filesystems for competing cooperative
    // writers, but is not a general lease service or remote-filesystem lock.
    directory(path.dirname(file));
    regular(file);
    const lock=lockPath(file);
    try { fs.mkdirSync(lock,{mode:0o700}); }
    catch (e) {
        if(e.code==="EEXIST") return error("LOCK_HELD_OR_RECOVERY_REQUIRED");
        throw e;
    }
    // If writing or syncing this metadata fails, intentionally leave the
    // lock directory. Other writers must not "repair" it automatically.
    const token=crypto.randomBytes(24).toString("hex");
    const owner={format:1,pid:process.pid,token};
    const fd=fs.openSync(path.join(lock,"owner.json"),"wx",0o600);
    try {
        fs.writeFileSync(fd,JSON.stringify(owner)+"\n","utf8");
        fs.fsyncSync(fd);
    } finally {fs.closeSync(fd);}
    fsyncDirectory(lock);
    fsyncDirectory(path.dirname(file));
    return {ok:true,lease:{file,lock,token}};
}
function requireOwner(lease) {
    if(!lease || typeof lease.token!=="string"
            || !/^[a-f0-9]{48}$/.test(lease.token)
            || typeof lease.file!=="string"
            || lease.lock!==lockPath(lease.file))
        throw Error("INVALID_LEASE");
    directory(lease.lock);
    const meta=regular(path.join(lease.lock,"owner.json"));
    let owner;
    try {owner=JSON.parse(meta.toString("utf8"));}
    catch {throw Error("CORRUPT_OWNER");}
    if(!owner || owner.format!==1 || owner.token!==lease.token
            || owner.pid!==process.pid)
        throw Error("LOCK_NOT_OWNED");
}
function inspect(lease,policy) {
    requireOwner(lease);
    const original=regular(lease.file);
    const decoded=policy.decode(original.toString("utf8"));
    if(!decoded.ok) return error("COMMITTED_"+decoded.reason);
    return {ok:true,revision:decoded.document.revision,
            document:decoded.document,sha256:sha256(original)};
}
function commit(lease,expectedRevision,expectedHash,newDocument,policy,stopAt) {
    requireOwner(lease);
    const old=inspect(lease,policy);
    if(!old.ok) return old;
    if(old.revision!==expectedRevision) return error("STALE_REVISION");
    if(typeof expectedHash!=="string" || !/^[a-f0-9]{64}$/.test(expectedHash))
        return error("EXPECTED_HASH_REQUIRED");
    if(old.sha256!==expectedHash) return error("STALE_SOURCE_HASH");
    if(!newDocument || newDocument.revision!==expectedRevision+1)
        return error("REVISION_STEP_REQUIRED");
    const encoded=policy.encode(newDocument);
    if(!encoded.ok) return error("INVALID_NEXT_"+encoded.reason);
    const bytes=Buffer.from(encoded.raw,"utf8");
    const parent=path.dirname(lease.file);
    const tmp=path.join(parent,"."+path.basename(lease.file)+
        ".m10f-"+process.pid+"-"+(++nonce)+"-"+lease.token.slice(0,12));
    inject("before-create",stopAt);
    const fd=fs.openSync(tmp,"wx",0o600);
    try {
        fs.writeFileSync(fd,bytes);
        inject("after-write",stopAt);
        fs.fsyncSync(fd);
        inject("after-file-sync",stopAt);
    } finally {fs.closeSync(fd);}
    // Re-read the committed original while still owning the cooperative
    // writer lock. This does not protect against NON-cooperative writers.
    const current=inspect(lease,policy);
    if(!current.ok || current.sha256!==old.sha256)
        return error("SOURCE_CHANGED_DURING_COMMIT");
    inject("before-rename",stopAt);
    fs.renameSync(tmp,lease.file);
    inject("after-rename",stopAt);
    fsyncDirectory(parent);
    inject("after-directory-sync",stopAt);
    const verified=inspect(lease,policy);
    if(!verified.ok || verified.revision!==newDocument.revision
            || verified.sha256!==sha256(bytes))
        return error("COMMIT_NOT_VERIFIED");
    return {ok:true,reason:"",revision:verified.revision,
            sha256:verified.sha256};
}
function release(lease) {
    requireOwner(lease);
    fs.unlinkSync(path.join(lease.lock,"owner.json"));
    fs.rmdirSync(lease.lock);
    fsyncDirectory(path.dirname(lease.file));
    return {ok:true};
}
module.exports={acquire,inspect,commit,release,lockPath};
