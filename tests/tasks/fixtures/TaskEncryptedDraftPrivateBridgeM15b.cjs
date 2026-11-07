#!/usr/bin/env node
"use strict";
/*
 * TASKS M15b // ISOLATED CI encrypted draft storage integration.
 *
 * This is NOT an entrypoint for production TASKS and does NOT accept a real
 * draft, arbitrary file, actual consent, or the desktop's login keyring.
 *
 * It composes previously reviewed fake-only AES-GCM context binding (M13m),
 * private atomic ciphertext storage (M13o), and a real Secret Service item
 * on a FRESH THROWAWAY D-Bus session. Capture and preview run in separate
 * processes; ciphertext persists between them; all success is TEST ONLY.
 *
 * No key, private text, filesystem path or secret-tool stdout is logged.
 */
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const cp=require("node:child_process");
const crypto=require("node:crypto");
const model=require("./TaskEncryptedDraftTransactionM13m.cjs");
const storage=require("./TaskEncryptedDraftPrivateStorageM13o.cjs");
const {constants:C}=fs;
const SERVICE="post-apollo-m15b-disposable-ci";
const ITEM="M15bFakeDraft001";
const SOURCE={
    kind:"M13M_FAKE_SOURCE",generation:7,
    raw:JSON.stringify({kind:"M13M_FAKE_TASKS_JSON",
        documentVersion:3,marker:"FAKE_RESTART_SOURCE"})
};
const DIGEST=crypto.createHash("sha256").update(SOURCE.raw).digest("hex");
const CONTEXT={
    installationId:"M15BInstall001",epoch:7,
    stageId:"m13a-M15BInstall001-7-1",surface:"HUB"
};
const FAKE_DRAFT={
    kind:"M13M_FAKE_EDITOR_DRAFT",surface:"HUB",
    value:"FAKE_M15B_PENDING_EDITOR_DRAFT"
};
const CURRENT_LEDGER={
    kind:"M13M_FAKE_LEDGER",installationId:CONTEXT.installationId,
    epoch:CONTEXT.epoch,sourceGeneration:SOURCE.generation,
    sourceDigest:DIGEST,latestCommittedSeq:0
};
const MARKERS=new Set([
    "M15B_PRIVATE_ENCRYPTED_CAPTURE_PASS",
    "M15B_PRIVATE_LOCKED_INDICATOR_PASS",
    "M15B_PRIVATE_UNLOCKED_PREVIEW_PASS",
    "M15B_PRIVATE_MISSING_KEY_REFUSED",
    "M15B_PRIVATE_WRONG_KEY_REFUSED",
    "M15B_PRIVATE_SOURCE_CONFLICT_REFUSED",
    "M15B_PRIVATE_CIPHERTEXT_CLEAR_PASS",
    "M15B_PRIVATE_NO_CHECKPOINT_REFUSED",
    "M15B_PRIVATE_HOST_REFUSED"
]);
function directorySafe(file){
    try{
        const s=fs.lstatSync(file);
        return s.isDirectory()&&!s.isSymbolicLink()&&s.nlink>=1
            &&s.uid===process.getuid()&&(s.mode&0o777)===0o700
            &&fs.realpathSync(file)===file;
    }catch(e){return false;}
}
function privateContext() {
    if(process.platform!=="linux" || typeof process.getuid!=="function"
        ||process.getuid()===0
        ||process.env.GITHUB_ACTIONS!=="true"
        ||process.env.POST_APOLLO_M15B_DISPOSABLE_CI!=="1")
        return null;
    const home=process.env.HOME,root=process.env.POST_APOLLO_M15B_PRIVATE_ROOT;
    const bus=process.env.DBUS_SESSION_BUS_ADDRESS;
    if(typeof home!=="string" || typeof root!=="string"
        ||path.dirname(home)!==os.tmpdir()
        ||!/^postapollo-m15b-private-[A-Za-z0-9_-]{8,64}$/.test(path.basename(home))
        ||path.dirname(root)!==os.tmpdir()
        ||!/^postapollo-m13o-disposable-[A-Za-z0-9_-]{6,64}$/.test(path.basename(root))
        ||typeof bus!=="string"
        ||!/^unix:path=\/tmp\/dbus-[A-Za-z0-9_-]+(?:,.*)?$/.test(bus)
        ||process.env.XDG_CONFIG_HOME!==path.join(home,".config")
        ||process.env.XDG_DATA_HOME!==path.join(home,".local/share")
        ||process.env.XDG_CACHE_HOME!==path.join(home,".cache")
        ||!directorySafe(home)||!directorySafe(root))
        return null;
    return root;
}
function secret(args,input) {
    try {
        const r=cp.spawnSync("secret-tool",args,{
            input,encoding:"utf8",timeout:10000,maxBuffer:8192,
            stdio:[input===undefined?"ignore":"pipe","pipe","pipe"]
        });
        return r.status===0&&!r.error?r.stdout:null;
    }catch(e){return null;}
}
function getKey(item=ITEM){
    const result=secret(["lookup","service",SERVICE,"id",item]);
    if(typeof result!=="string")return null;
    const raw=result.trim();
    if(!/^[A-Za-z0-9+/]{43}=$/.test(raw))return null;
    const key=Buffer.from(raw,"base64");
    if(key.length!==32||key.toString("base64")!==raw){
        key.fill(0);return null;
    }
    return key;
}
function readRecord(root) {
    let fd;
    try{
        fd=fs.openSync(path.join(root,"checkpoint.json"),C.O_RDONLY|C.O_NOFOLLOW);
        const st=fs.fstatSync(fd);
        if(!st.isFile()||st.uid!==process.getuid()||st.nlink!==1
            ||(st.mode&0o777)!==0o600||st.size<50||st.size>160000)
            return null;
        const content=fs.readFileSync(fd,"utf8");
        const value=JSON.parse(content);
        if(value?.kind!=="M13O_FAKE_PRIVATE_CHECKPOINT"
            ||value?.format!==1)
            return null;
        return {raw:content,record:value};
    }catch(e){return null;}
    finally{if(fd!==undefined)fs.closeSync(fd);}
}
function capture(root){
    const existing=getKey();
    if(storage.inspectFake({root}).status!=="SIMULATED_NO_CHECKPOINT"
        ||existing!==null) {
        if(existing)existing.fill(0);
        return "M15B_PRIVATE_HOST_REFUSED";
    }
    const key=crypto.randomBytes(32);
    try{
        if(secret(["store",
            "--label=Post-Apollo M15b disposable CI draft only",
            "service",SERVICE,"id",ITEM],key.toString("base64")+"\n")===null)
            return "M15B_PRIVATE_HOST_REFUSED";
        const verified=getKey();
        if(!verified||!crypto.timingSafeEqual(key,verified)){
            verified?.fill(0);
            return "M15B_PRIVATE_HOST_REFUSED";
        }
        verified.fill(0);
        const prepared=model.createSyntheticCheckpoint({
            source:SOURCE,ledger:CURRENT_LEDGER,
            identity:CONTEXT,draft:FAKE_DRAFT,key,
            optedIn:true,checkpointSeq:1
        });
        if(!prepared.ok||prepared.persistAuthorized!==false
            ||prepared.writeAuthorized!==false)
            return "M15B_PRIVATE_HOST_REFUSED";
        const committed=storage.commitFake({
            root,prepared,expectedPreviousSequence:0
        });
        if(!committed.ok
            ||committed.status!=="SIMULATED_PRIVATE_ATOMIC_RENAME_AND_READBACK_PASS"
            ||committed.persistAuthorized!==false)
            return "M15B_PRIVATE_HOST_REFUSED";
        const saved=readRecord(root);
        if(!saved || saved.raw.includes(FAKE_DRAFT.value)
            ||saved.raw.includes(SOURCE.raw)
            ||saved.raw.includes(key.toString("base64")))
            return "M15B_PRIVATE_HOST_REFUSED";
        return "M15B_PRIVATE_ENCRYPTED_CAPTURE_PASS";
    }finally{key.fill(0);}
}
function locked(root){
    const out=storage.inspectFake({root});
    return out.ok&&out.status==="SIMULATED_LOCKED_CIPHERTEXT_ONLY"
        &&out.fakeSequence===1
        &&out.restoreAuthorized===false
        &&!Object.hasOwn(out,"fakePreviewMarker")
        ? "M15B_PRIVATE_LOCKED_INDICATOR_PASS"
        : "M15B_PRIVATE_HOST_REFUSED";
}
function preview(root,mode){
    const read=readRecord(root);
    if(!read)return "M15B_PRIVATE_HOST_REFUSED";
    const key=mode==="wrong-key"?crypto.randomBytes(32):
        getKey(mode==="missing-key"?"M15bMissingKey001":ITEM);
    if(!key)return mode==="missing-key"
        ? "M15B_PRIVATE_MISSING_KEY_REFUSED"
        : "M15B_PRIVATE_HOST_REFUSED";
    try{
        let source=SOURCE;
        if(mode==="source-conflict")
            source={...SOURCE,raw:JSON.stringify({
                kind:"M13M_FAKE_TASKS_JSON",documentVersion:3,
                marker:"FAKE_CHANGED_SOURCE"})};
        const result=model.evaluateSyntheticRecovery({
            checkpoint:read.record.checkpoint,
            ledger:read.record.proposedLedger,
            identity:CONTEXT,source,key,
            unlocked:true,reviewRequested:true,
            activeDraftPresent:false
        });
        if(result.ok&&result.status===
                "SYNTHETIC_PREVIEW_CANDIDATE_REQUIRES_REAL_AUTHORITY"
            &&result.fakePreviewMarker===FAKE_DRAFT.value
            &&result.restoreAuthorized===false
            &&result.previewAuthorized===false
            &&result.keyReleaseAuthorized===false)
            return "M15B_PRIVATE_UNLOCKED_PREVIEW_PASS";
        if(mode==="wrong-key"
            &&result.status==="CIPHERTEXT_AUTH_OR_KEY_REFUSED")
            return "M15B_PRIVATE_WRONG_KEY_REFUSED";
        if(mode==="source-conflict"
            &&result.status==="SOURCE_CHANGED_REVIEW_REQUIRED")
            return "M15B_PRIVATE_SOURCE_CONFLICT_REFUSED";
        return "M15B_PRIVATE_HOST_REFUSED";
    }finally{key.fill(0);}
}
function clear(root){
    const c=storage.clearFake({root,expectedSequence:1,confirmed:true});
    if(!c.ok||c.status!=="SIMULATED_EXPLICIT_CIPHERTEXT_CLEAR_PASS"
        ||c.deleteAuthorized!==false)
        return "M15B_PRIVATE_HOST_REFUSED";
    return "M15B_PRIVATE_CIPHERTEXT_CLEAR_PASS";
}
function absent(root){
    const r=storage.inspectFake({root});
    return !r.ok&&r.status==="SIMULATED_NO_CHECKPOINT"
        ? "M15B_PRIVATE_NO_CHECKPOINT_REFUSED"
        : "M15B_PRIVATE_HOST_REFUSED";
}
const actions=new Map([
    ["capture",capture],
    ["locked",locked],
    ["preview",root=>preview(root,"normal")],
    ["preview-missing-key",root=>preview(root,"missing-key")],
    ["preview-wrong-key",root=>preview(root,"wrong-key")],
    ["preview-source-conflict",root=>preview(root,"source-conflict")],
    ["clear",clear],
    ["absent",absent]
]);
const root=privateContext();
const action=process.argv.length===3?actions.get(process.argv[2]):null;
let outcome="M15B_PRIVATE_HOST_REFUSED";
if(root && action){
    try{outcome=action(root);}catch(e){outcome="M15B_PRIVATE_HOST_REFUSED";}
}
if(!MARKERS.has(outcome))outcome="M15B_PRIVATE_HOST_REFUSED";
process.stdout.write(outcome+"\n");
process.exitCode=outcome==="M15B_PRIVATE_HOST_REFUSED"?2:0;
