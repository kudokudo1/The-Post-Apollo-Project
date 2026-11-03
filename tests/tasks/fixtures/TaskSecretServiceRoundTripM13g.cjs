#!/usr/bin/env node
"use strict";
/*
 * TASKS M13g // disposable-only real Secret Service round-trip.
 *
 * This is NOT a production key-provider adapter. It runs only with an
 * isolated CI bus + private HOME and fake task content. The actual
 * Secret Service credential entry is created only on that fake bus.
 * No passwords/keys/drafts are passed in argv or environment, printed,
 * committed, logged, or written to task files. All messages are fixed.
 */
const fs=require("node:fs"),os=require("node:os"),path=require("node:path");
const crypto=require("node:crypto"),cp=require("node:child_process");
const {constants:C}=fs;
const cipher=require("./TaskEncryptedRecoveryM13f.cjs");
const ID="M13gSynthetic001";
const NAME="post-apollo-m13g-ci";
const DRAFT={kind:"M13F_FAKE_DRAFT",surface:"HUB",
    value:{title:"M13G_SYNTHETIC_PRIVATE_TITLE"}};
const CONTEXT={
    installationId:"M13gFakeInstall001",
    stageId:"m13a-M13gOldSession001-7-1",
    epoch:8,surface:"HUB"
};
function validRoot() {
    const home=process.env.HOME;
    if(process.env.POST_APOLLO_M13G_DISPOSABLE!=="1"
            ||typeof home!=="string"
            ||!home.startsWith(os.tmpdir()+"/postapollo-m13g-")
            ||!process.env.DBUS_SESSION_BUS_ADDRESS)
        return null;
    const root=path.join(home,"m13g-disposable");
    const st=fs.lstatSync(root);
    if(!st.isDirectory()||st.isSymbolicLink()
            ||(st.mode&0o077)!==0
            ||(typeof process.getuid==="function"&&st.uid!==process.getuid()))
        return null;
    return root;
}
function runSecretTool(args,input) {
    // The plaintext fake key enters only stdin or the private bus. Never
    // log stdout/stderr; lookup returns the fake key in process memory only.
    const p=cp.spawnSync("secret-tool",args,{
        input,encoding:"utf8",timeout:10000,maxBuffer:8192
    });
    return p.status===0?p.stdout:null;
}
function retrieve(name=ID) {
    const raw=runSecretTool(["lookup","service",NAME,"id",name]);
    if(typeof raw!=="string")return null;
    const encoded=raw.trim();
    if(!/^[A-Za-z0-9+/]{43}=$/.test(encoded))return null;
    const key=Buffer.from(encoded,"base64");
    if(key.length!==32||key.toString("base64")!==encoded)return null;
    return key;
}
function create(root) {
    const file=path.join(root,"draft.enc");
    if(fs.existsSync(file)||fs.existsSync(file+".tmp"))
        return "REFUSED_EXISTING_SOURCE";
    const key=crypto.randomBytes(32);
    try {
        const secret=key.toString("base64")+"\n";
        const stored=runSecretTool(["store",
            "--label=Post-Apollo disposable M13g only",
            "service",NAME,"id",ID],secret);
        if(stored===null)return "REFUSED_SECRET_SERVICE_STORE";
        const check=retrieve();
        if(!check||!crypto.timingSafeEqual(check,key))
            return "REFUSED_SECRET_SERVICE_READBACK";
        check.fill(0);
        const encrypted=cipher.seal({
            identity:CONTEXT,key,draft:DRAFT,optedIn:true
        });
        if(!encrypted.ok ||encrypted.persistAuthorized!==false)
            return "REFUSED_ENCRYPTION";
        const fd=fs.openSync(file,C.O_CREAT|C.O_EXCL|C.O_WRONLY|C.O_NOFOLLOW,0o600);
        try{
            fs.writeFileSync(fd,encrypted.envelopeRaw,"utf8");fs.fsyncSync(fd);
        }finally{fs.closeSync(fd);}
        const dir=fs.openSync(root,C.O_RDONLY|C.O_DIRECTORY);
        try{fs.fsyncSync(dir);}finally{fs.closeSync(dir);}
        return "SYNTHETIC_SECRET_STORED_AND_ENCRYPTED";
    }catch(e){return "REFUSED_DISPOSABLE_CREATE";}
    finally{key.fill(0);}
}
function reopen(root,missing=false) {
    const file=path.join(root,"draft.enc");
    let fd,raw;
    try{
        fd=fs.openSync(file,C.O_RDONLY|C.O_NOFOLLOW);
        const st=fs.fstatSync(fd);
        if(!st.isFile()||st.nlink!==1||(st.mode&0o077)!==0)
            return "REFUSED_UNSAFE_FILE";
        raw=fs.readFileSync(fd,"utf8");
    }catch(e){return "REFUSED_MISSING_FILE";}
    finally{if(fd!==undefined)fs.closeSync(fd);}
    const locked=cipher.inspectLocked({envelopeRaw:raw});
    if(!locked.ok||Object.hasOwn(locked,"draft"))
        return "REFUSED_LOCKED_PREVIEW";
    const key=retrieve(missing?"M13gSyntheticMissing":ID);
    if(!key)return "REFUSED_KEY_NOT_AVAILABLE";
    try{
        const verified=cipher.openAfterUnlock({
            envelopeRaw:raw,identity:CONTEXT,key,unlocked:true
        });
        if(verified.ok &&verified.reason==="SYNTHETIC_DECRYPTION_VERIFIED"
            &&verified.draft?.value?.title===DRAFT.value.title
            &&verified.writeAuthorized===false
            &&verified.persistAuthorized===false)
            return "SYNTHETIC_SECRET_SERVICE_RESTART_PASS";
        return "REFUSED_DECRYPT";
    }finally{key.fill(0);}
}
let result="REFUSED_TEST_GUARD";
try{
    const root=validRoot();
    if(root){
        if(process.argv[2]==="create")result=create(root);
        else if(process.argv[2]==="reopen")result=reopen(root);
        else if(process.argv[2]==="reopen-missing-key")
            result=reopen(root,true);
    }
}catch(e){result="REFUSED_TEST_GUARD";}
process.stdout.write(result+"\n");
process.exitCode=result.startsWith("REFUSED")?0:0;
// Intentional: refusal is a valid outcome; the isolated harness asserts
// specific fixed markers and is the only place authorizing a test PASS.
