"use strict";
/*
 * TASKS M13o // disposable-private-storage fixture, NEVER production.
 * The only filesystem targets are an existing owner-only 0700 directory
 * created separately under os.tmpdir()/postapollo-m13o-disposable-*.
 * No real TASKS files, Settings, session bus, keyring or source writes.
 * This fixture does NOT grant actual consent, key-release or durability
 * guarantees against malicious rollback; all authority booleans are false.
 */
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const crypto=require("node:crypto");
const model=require("./TaskEncryptedDraftTransactionM13m.cjs");
const C=fs.constants;
const NAME="checkpoint.json";
const LOCK="writer.lock";
const NO_POWER=model.NO_POWER;
const deny=status=>({ok:false,status,...NO_POWER});
const allow=(status,data={})=>({ok:true,status,...data,...NO_POWER});
const exact=(v,k)=>v&&typeof v==="object"&&!Array.isArray(v)
    &&Object.keys(v).sort().join(",")===k.slice().sort().join(",");
function privateRoot(root){
    if(process.platform!=="linux"||typeof process.getuid!=="function"
        ||process.getuid()===0||typeof root!=="string"
        ||path.dirname(root)!==os.tmpdir()
        ||!/^postapollo-m13o-disposable-[A-Za-z0-9_-]{6,64}$/.test(path.basename(root)))
        return false;
    try {
        const st=fs.lstatSync(root);
        return st.isDirectory()&&!st.isSymbolicLink()
            &&st.uid===process.getuid()&&(st.mode&0o777)===0o700
            &&fs.realpathSync(root)===root;
    }catch(e){return false;}
}
function recordValid(v){
    if(!exact(v,["format","kind","checkpoint","proposedLedger"])
        ||v.format!==1||v.kind!=="M13O_FAKE_PRIVATE_CHECKPOINT")
        return false;
    const match=model.simulateReadback({
        checkpoint:v.checkpoint,proposedLedger:v.proposedLedger,
        readbackEnvelopeRaw:v.checkpoint&&v.checkpoint.envelopeRaw
    });
    return match.ok===true&&match.persistAuthorized===false
        &&model.inspectLocked({checkpoint:v.checkpoint}).ok===true;
}
function readRecord(root){
    const name=path.join(root,NAME);
    let fd;
    try {
        fd=fs.openSync(name,C.O_RDONLY|C.O_NOFOLLOW);
        const st=fs.fstatSync(fd);
        if(!st.isFile()||st.nlink!==1||st.uid!==process.getuid()
            ||(st.mode&0o777)!==0o600||st.size<50||st.size>160000)
            return {state:"invalid"};
        const raw=fs.readFileSync(fd,"utf8");
        const v=JSON.parse(raw);
        return recordValid(v)?{state:"valid",raw,value:v}:{state:"invalid"};
    }catch(e){
        if(e.code==="ENOENT")return {state:"absent"};
        return {state:"invalid"};
    }finally{if(fd!==undefined)fs.closeSync(fd);}
}
function syncDir(root) {
    const fd=fs.openSync(root,C.O_RDONLY|C.O_DIRECTORY|C.O_NOFOLLOW);
    try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
}
function locked(root,callback){
    const name=path.join(root,LOCK);
    try{fs.mkdirSync(name,{mode:0o700});}
    catch(e){return deny("SIMULATED_LOCK_BUSY_OR_LEFTOVER");}
    let result=deny("SIMULATED_LOCKED_TRANSACTION_FAILED");
    try{result=callback();}
    catch(e){result=deny("SIMULATED_IO_OR_ATOMICITY_REFUSED");}
    finally{
        try{fs.rmdirSync(name);syncDir(root);}
        catch(e){result=deny("SIMULATED_LOCK_CLEANUP_UNVERIFIED");}
    }
    return result;
}
function commitFake({root,prepared,expectedPreviousSequence}={}){
    if(!privateRoot(root))return deny("DISPOSABLE_ROOT_REQUIRED");
    if(!Number.isSafeInteger(expectedPreviousSequence)||expectedPreviousSequence<0)
        return deny("INVALID_PREVIOUS_SEQUENCE");
    if(!prepared||prepared.ok!==true
        ||prepared.status!=="SYNTHETIC_CIPHERTEXT_PREPARED_NOT_DURABLE"
        ||prepared.persistAuthorized!==false||prepared.writeAuthorized!==false)
        return deny("FAKE_PREPARED_CHECKPOINT_REQUIRED");
    const record={format:1,kind:"M13O_FAKE_PRIVATE_CHECKPOINT",
        checkpoint:prepared.checkpoint,proposedLedger:prepared.proposedLedger};
    if(!recordValid(record))return deny("INVALID_SYNTHETIC_RECORD");
    const next=record.proposedLedger.latestCommittedSeq;
    if(next!==expectedPreviousSequence+1)
        return deny("SIMULATED_SEQUENCE_NOT_NEXT");
    return locked(root,()=>{
        const previous=readRecord(root);
        if(previous.state==="invalid")
            return deny("SIMULATED_EXISTING_RECORD_UNTRUSTED");
        if(previous.state==="absent"&&expectedPreviousSequence!==0)
            return deny("SIMULATED_MISSING_PREVIOUS_RECORD");
        if(previous.state==="valid"){
            const old=previous.value;
            if(old.proposedLedger.latestCommittedSeq!==expectedPreviousSequence)
                return deny("SIMULATED_STALE_WRITER");
            if(old.proposedLedger.installationId!==record.proposedLedger.installationId
                ||old.proposedLedger.epoch!==record.proposedLedger.epoch)
                return deny("SIMULATED_INSTALLATION_OR_EPOCH_CHANGED");
            if(old.proposedLedger.sourceDigest!==record.proposedLedger.sourceDigest
                ||old.proposedLedger.sourceGeneration!==record.proposedLedger.sourceGeneration)
                return deny("SIMULATED_SOURCE_ANCHOR_CHANGED");
        }
        const bytes=JSON.stringify(record)+"\n";
        if(Buffer.byteLength(bytes,"utf8")>160000)
            return deny("SIMULATED_RECORD_TOO_LARGE");
        const temp=path.join(root,".checkpoint-"+
            crypto.randomBytes(16).toString("hex")+".tmp");
        let fd,renamed=false;
        try {
            fd=fs.openSync(temp,C.O_WRONLY|C.O_CREAT|C.O_EXCL|C.O_NOFOLLOW,0o600);
            const written=fs.writeSync(fd,bytes);
            if(written!==Buffer.byteLength(bytes,"utf8"))
                throw Error("incomplete write");
            fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;
            fs.renameSync(temp,path.join(root,NAME));renamed=true;
            syncDir(root);
            const result=readRecord(root);
            if(result.state!=="valid"||result.raw!==bytes)
                return deny("SIMULATED_READBACK_MISMATCH");
            return allow("SIMULATED_PRIVATE_ATOMIC_RENAME_AND_READBACK_PASS",{
                fakeSequence:next,locked:true
            });
        }catch(e){
            return deny("SIMULATED_IO_OR_ATOMICITY_REFUSED");
        }finally{
            if(fd!==undefined)fs.closeSync(fd);
            if(!renamed){try{fs.unlinkSync(temp);}catch(e){}}
        }
    });
}
function inspectFake({root}={}){
    if(!privateRoot(root))return deny("DISPOSABLE_ROOT_REQUIRED");
    if(fs.existsSync(path.join(root,LOCK)))
        return deny("SIMULATED_LOCK_BUSY_OR_LEFTOVER");
    const record=readRecord(root);
    if(record.state==="absent")return deny("SIMULATED_NO_CHECKPOINT");
    if(record.state!=="valid")return deny("SIMULATED_RECORD_UNTRUSTED");
    return allow("SIMULATED_LOCKED_CIPHERTEXT_ONLY",{
        locked:true,fakeSequence:record.value.proposedLedger.latestCommittedSeq
    });
}
function clearFake({root,expectedSequence,confirmed}={}){
    if(!privateRoot(root))return deny("DISPOSABLE_ROOT_REQUIRED");
    if(confirmed!==true)return deny("SIMULATED_EXPLICIT_CLEAR_REQUIRED");
    if(!Number.isSafeInteger(expectedSequence)||expectedSequence<1)
        return deny("SIMULATED_CLEAR_SEQUENCE_REQUIRED");
    return locked(root,()=>{
        const previous=readRecord(root);
        if(previous.state!=="valid")return deny("SIMULATED_RECORD_UNTRUSTED");
        if(previous.value.proposedLedger.latestCommittedSeq!==expectedSequence)
            return deny("SIMULATED_STALE_CLEAR");
        try{
            fs.unlinkSync(path.join(root,NAME));
            syncDir(root);
            if(readRecord(root).state!=="absent")
                return deny("SIMULATED_CLEAR_UNVERIFIED");
            return allow("SIMULATED_EXPLICIT_CIPHERTEXT_CLEAR_PASS");
        }catch(e){return deny("SIMULATED_CLEAR_UNVERIFIED");}
    });
}
module.exports={commitFake,inspectFake,clearFake,NO_POWER};
