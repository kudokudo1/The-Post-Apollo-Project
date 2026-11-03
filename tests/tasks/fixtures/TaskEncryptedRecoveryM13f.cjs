"use strict";
/*
 * TASKS M13f: isolated, NEVER-MOUNTED encryption capability fixture.
 *
 * Uses Node crypto AES-256-GCM only for synthetic drafts. No filesystem,
 * passwords, key derivation/storage, Secret Service access, OS permissions,
 * user data, new writer, operational logging, production QML, or timers.
 *
 * A caller-provided Buffer key and synthetic opt-in/unlock flags are NOT a
 * trusted key provider or authenticated user consent. No success grants
 * production persist/export/delete/replay/restore authority.
 */
const crypto=require("node:crypto");
const {createCipheriv,createDecipheriv,randomBytes}=crypto;
const NO_POWER=Object.freeze({
    productionActivation:false,sourceTrusted:false,
    persistAuthorized:false,writeAuthorized:false,
    exportAuthorized:false,deleteAuthorized:false,
    clearDraftAuthorized:false,replayAuthorized:false,
    restoreAuthorized:false,syncAuthorized:false
});
const allowedSurfaces=new Set(["HUB","DETAILS","PLANNER","PROJECTS"]);
const token=x=>typeof x==="string"&&/^[A-Za-z0-9_-]{8,80}$/.test(x);
const stage=x=>typeof x==="string"&&/^m13a-[A-Za-z0-9_-]{8,80}-[1-9][0-9]*-[1-9][0-9]*$/.test(x);
const exact=(obj,keys)=>obj&&typeof obj==="object"&&!Array.isArray(obj)
    &&Object.keys(obj).sort().join(",")===keys.slice().sort().join(",");
const reject=reason=>({ok:false,reason,...NO_POWER});
const identityValid=x=>exact(x,["installationId","stageId","epoch","surface"])
    &&token(x.installationId)&&stage(x.stageId)
    &&Number.isSafeInteger(x.epoch)&&x.epoch>0
    &&allowedSurfaces.has(x.surface);
const aad=x=>Buffer.from(JSON.stringify(["M13F_TEST_ONLY",1,
    x.installationId,x.stageId,x.epoch,x.surface]),"utf8");
const validKey=k=>Buffer.isBuffer(k)&&k.length===32;
function parseEnvelope(raw) {
    if(typeof raw!=="string"||Buffer.byteLength(raw,"utf8")>70000
        ||raw.length<60) return null;
    let v;
    try {v=JSON.parse(raw);}catch(e){return null;}
    if(!exact(v,["format","kind","cipher","nonce","tag","ciphertext"])
        ||v.format!==1||v.kind!=="M13F_TEST_ENCRYPTED_DRAFT"
        ||v.cipher!=="aes-256-gcm") return null;
    const decode=(x,min,max)=>{
        if(typeof x!=="string" ||x.length>max*2
            ||!/^[A-Za-z0-9+/]+={0,2}$/.test(x)) return null;
        const b=Buffer.from(x,"base64");
        return b.length>=min &&b.length<=max
            &&b.toString("base64")===x?b:null;
    };
    const nonce=decode(v.nonce,12,12);
    const tag=decode(v.tag,16,16);
    const ciphertext=decode(v.ciphertext,1,50000);
    return nonce&&tag&&ciphertext?{nonce,tag,ciphertext}:null;
}
function seal({identity,key,draft,optedIn}={}) {
    if(optedIn!==true) return reject("OPT_IN_REQUIRED");
    if(!identityValid(identity)) return reject("SYNTHETIC_IDENTITY_REQUIRED");
    if(!validKey(key)) return reject("EPHEMERAL_TEST_KEY_REQUIRED");
    if(!exact(draft,["kind","surface","value"]) ||
        draft.kind!=="M13F_FAKE_DRAFT" ||
        draft.surface!==identity.surface ||
        !draft.value ||typeof draft.value!=="object" ||
        Array.isArray(draft.value)) return reject("SYNTHETIC_DRAFT_REQUIRED");
    let raw;
    try {raw=JSON.stringify(draft);}catch(e){return reject("DRAFT_UNSERIALIZABLE");}
    if(typeof raw!=="string"||Buffer.byteLength(raw,"utf8")>32768)
        return reject("DRAFT_SIZE_LIMIT");
    try {
        const nonce=randomBytes(12);
        const cipher=createCipheriv("aes-256-gcm",key,nonce,
                                    {authTagLength:16});
        cipher.setAAD(aad(identity));
        const ciphertext=Buffer.concat([
            cipher.update(Buffer.from(raw,"utf8")),cipher.final()
        ]);
        const v={format:1,kind:"M13F_TEST_ENCRYPTED_DRAFT",
            cipher:"aes-256-gcm",
            nonce:nonce.toString("base64"),
            tag:cipher.getAuthTag().toString("base64"),
            ciphertext:ciphertext.toString("base64")};
        return {ok:true,reason:"SYNTHETIC_CIPHERTEXT_ONLY",
            envelopeRaw:JSON.stringify(v)+"\n",...NO_POWER};
    }catch(e){return reject("ENCRYPTION_UNAVAILABLE");}
}
function inspectLocked({envelopeRaw}={}) {
    if(!parseEnvelope(envelopeRaw)) return reject("INVALID_ENVELOPE");
    // Do not reveal title, draft contents, surface, operation, or task count.
    return {ok:true,reason:"SYNTHETIC_LOCKED_INDICATOR_ONLY",
        locked:true,recoveryAvailable:true,
        ...NO_POWER};
}
function openAfterUnlock({envelopeRaw,identity,key,unlocked}={}) {
    if(unlocked!==true) return reject("SEPARATE_UNLOCK_REQUIRED");
    if(!identityValid(identity)) return reject("SYNTHETIC_IDENTITY_REQUIRED");
    if(!validKey(key)) return reject("KEY_NOT_AVAILABLE");
    const envelope=parseEnvelope(envelopeRaw);
    if(!envelope) return reject("INVALID_ENVELOPE");
    let plaintext;
    try {
        const decipher=createDecipheriv("aes-256-gcm",key,envelope.nonce,
            {authTagLength:16});
        decipher.setAAD(aad(identity));
        decipher.setAuthTag(envelope.tag);
        plaintext=Buffer.concat([
            decipher.update(envelope.ciphertext),decipher.final()
        ]);
    }catch(e){return reject("AUTHENTICATION_OR_CONTEXT_MISMATCH");}
    let draft;
    try {draft=JSON.parse(plaintext.toString("utf8"));}
    catch(e){return reject("DECRYPTED_DRAFT_INVALID");}
    if(!exact(draft,["kind","surface","value"])||
        draft.kind!=="M13F_FAKE_DRAFT"||
        draft.surface!==identity.surface||
        !draft.value||typeof draft.value!=="object"||
        Array.isArray(draft.value))
        return reject("DECRYPTED_DRAFT_INVALID");
    // Data remains in JS heap after return. This is NOT secure memory
    // erasure or permission to display real user drafts.
    return {ok:true,reason:"SYNTHETIC_DECRYPTION_VERIFIED",
        draft,simulatedUnlocked:true,...NO_POWER};
}
module.exports={seal,openAfterUnlock,inspectLocked,NO_POWER};
