#!/usr/bin/env node
// M4r private pipe only. Standard Node crypto, no filesystem or network access
// other than reading stdin and writing the single response to stdout.
import { randomBytes, pbkdf2Sync, createCipheriv, createDecipheriv } from "node:crypto";
import { readSync } from "node:fs";
import { TextDecoder } from "node:util";

const KIND="post-apollo-financew-manual-portable-v1";
const ITERATIONS=600000, MAX_PLAIN=262144, MAX_FRAME=400000;
const exact=(obj,keys)=>obj!==null && typeof obj==="object" && !Array.isArray(obj)
    && Object.keys(obj).length===keys.length && keys.every(k=>Object.hasOwn(obj,k));
const need=(condition)=>{if(!condition)throw Error("REFUSED");};
const encode=b=>b.toString("base64url");
function decode(s,max) {
    need(typeof s==="string" && s.length<=Math.ceil(max*4/3)
        && /^[A-Za-z0-9_-]+$/.test(s));
    const bytes=Buffer.from(s,"base64url");
    need(bytes.length<=max && encode(bytes)===s);
    return bytes;
}
function key(password,salt){
    need(typeof password==="string" && [...password].length>=12
        && Buffer.byteLength(password,"utf8")<=1024
        && !/[\u0000-\u001f\u007f]/.test(password));
    return pbkdf2Sync(password,salt,ITERATIONS,32,"sha256");
}
const aad=Buffer.from(KIND,"utf8");
function seal(password,plain){
    const data=decode(plain,MAX_PLAIN);
    const salt=randomBytes(16),nonce=randomBytes(12),k=key(password,salt);
    try{
        const cipher=createCipheriv("aes-256-gcm",k,nonce);
        cipher.setAAD(aad);
        const encrypted=Buffer.concat([cipher.update(data),cipher.final(),cipher.getAuthTag()]);
        return {kind:KIND,version:1,algorithm:"AES-256-GCM",kdf:"PBKDF2-HMAC-SHA256",
                iterations:ITERATIONS,salt:encode(salt),nonce:encode(nonce),ciphertext:encode(encrypted)};
    }finally{k.fill(0);data.fill(0);}
}
function open(password,e){
    need(exact(e,["kind","version","algorithm","kdf","iterations","salt","nonce","ciphertext"])
        && e.kind===KIND && e.version===1 && e.algorithm==="AES-256-GCM"
        && e.kdf==="PBKDF2-HMAC-SHA256" && e.iterations===ITERATIONS);
    const salt=decode(e.salt,16),nonce=decode(e.nonce,12),data=decode(e.ciphertext,MAX_PLAIN+16);
    need(salt.length===16 && nonce.length===12 && data.length>16);
    const k=key(password,salt);
    let part,plain;
    try{
        const decipher=createDecipheriv("aes-256-gcm",k,nonce);
        decipher.setAAD(aad);
        decipher.setAuthTag(data.subarray(-16));
        part=decipher.update(data.subarray(0,-16));
        plain=Buffer.concat([part,decipher.final()]);
        need(plain.length<=MAX_PLAIN);
        return encode(plain);
    }finally{k.fill(0);if(part)part.fill(0);if(plain)plain.fill(0);}
}
try{
    const chunks=[];
    let total=0;
    while(true){
        const buffer=Buffer.alloc(8192);
        const n=readSync(0,buffer,0,buffer.length,null);
        if(n===0)break;
        total+=n;need(total<=MAX_FRAME);
        chunks.push(buffer.subarray(0,n));
    }
    const frame=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(Buffer.concat(chunks)));
    let result;
    if(exact(frame,["action","password","plain"]) && frame.action==="seal")
        result={envelope:seal(frame.password,frame.plain)};
    else if(exact(frame,["action","password","envelope"]) && frame.action==="open")
        result={plain:open(frame.password,frame.envelope)};
    else throw Error("REFUSED");
    process.stdout.write(JSON.stringify(result)+"\n");
}catch{
    // No secret, decrypted bytes, stack trace or input echo on failure.
    process.stderr.write("BANKING_PORTABLE_CRYPTO_REFUSED\n");
    process.exitCode=1;
}
