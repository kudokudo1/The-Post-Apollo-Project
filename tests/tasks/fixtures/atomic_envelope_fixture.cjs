"use strict";

// Proxy 1 M10c. Node-only disposable CI fixture, NOT a desktop storage service.
// It illustrates one-file commit boundaries: write candidate, fsync file,
// rename over target, fsync parent directory. Never use on user's task path.
// Crash injection throws after one step; this is NOT a physical power-loss test.

const fs = require("node:fs");
const path = require("node:path");
let nonce = 0;

function failIf(stage, requested) {
    if (stage === requested) {
        const e = new Error("INJECTED_STOP_AT_" + stage);
        e.code = "INJECTED_STOP";
        throw e;
    }
}

function readEnvelope(file, policy) {
    let raw;
    try {
        raw = fs.readFileSync(file, "utf8");
    } catch (error) {
        return {ok:false,reason:error.code === "ENOENT"
            ? "NO_COMMITTED_ENVELOPE" : "READ_FAILED"};
    }
    const result = policy.decode(raw);
    return result.ok
        ? {ok:true,document:result.document,raw:raw}
        : {ok:false,reason:result.reason,raw:raw};
}

// Only a test fixture. Assumes a single process has exclusive writer rights.
// A production implementation requires a reviewed concurrency/lock contract,
// safe tmp naming, storage directory ownership and kernel/platform validation.
function atomicReplace(file, document, expectedRevision, policy, stopAt) {
    const current = readEnvelope(file,policy);
    if (!current.ok) return {ok:false,reason:"BASE_"+current.reason};
    if (current.document.revision !== expectedRevision)
        return {ok:false,reason:"STALE_REVISION"};
    const next = policy.encode(document);
    if (!next.ok) return {ok:false,reason:next.reason};
    if (document.revision <= current.document.revision)
        return {ok:false,reason:"NONINCREASING_REVISION"};

    const parent = path.dirname(file);
    const candidate = path.join(parent,
        "." + path.basename(file) + ".m10c-" + process.pid + "-" + ++nonce);

    failIf("before-create",stopAt);
    let fd;
    try {
        fd=fs.openSync(candidate,"wx",0o600);
        fs.writeFileSync(fd,next.raw,"utf8");
        failIf("after-write",stopAt);
        fs.fsyncSync(fd);
        failIf("after-file-sync",stopAt);
    } finally {
        if (fd !== undefined) fs.closeSync(fd);
    }
    fs.renameSync(candidate,file);
    failIf("after-rename",stopAt);
    const dirFd=fs.openSync(parent,"r");
    try { fs.fsyncSync(dirFd); }
    finally { fs.closeSync(dirFd); }
    failIf("after-directory-sync",stopAt);
    return {ok:true,reason:""};
}

module.exports={readEnvelope,atomicReplace};
