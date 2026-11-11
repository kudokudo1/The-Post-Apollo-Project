/* MACHINE // authenticate sealed synthetic/consented Brave snapshot for
 * redacted, in-memory recovery review only. No URL is returned or logged.
 * Password is used in WebCrypto only; no storage, network, native IPC or
 * browser tab creation. The encrypted payload explicitly denies RESTORE.
 */
import {classifySelectableUrl,SEALED_KIND} from "./session-seal.mjs";

const PLAIN_KIND="machine-brave-selected-session-v1";
const UUID_BASE64=/^[A-Za-z0-9_-]+$/;
const LABEL=/^[A-Za-z][A-Za-z0-9 _.-]{0,47}$/;
const MAX_CIPHER=131072,MAX_PLAINTEXT=98304,MAX_TABS=48;
const ENVELOPE_KEYS=[
  "aad","algorithm","ciphertext","iterations","kdf","kind",
  "nonce","salt","version"
].sort().join(",");
function refuse(){throw new TypeError("SEALED SNAPSHOT REVIEW REFUSED")}
function keys(value,expected){
  return value && typeof value==="object" && !Array.isArray(value) &&
    Object.keys(value).sort().join(",")===expected.slice().sort().join(",");
}
function base64(value,min,max){
  if(typeof value!=="string"||!UUID_BASE64.test(value)||
     value.length>180000)refuse();
  let decoded;
  try{
    const standard=value.replaceAll("-","+").replaceAll("_","/");
    decoded=Uint8Array.from(atob(standard+"=".repeat((4-standard.length%4)%4)),
                               c=>c.charCodeAt(0));
  }catch{refuse()}
  if(decoded.length<min||decoded.length>max)refuse();
  let binary="";
  for(let i=0;i<decoded.length;i+=8192){
    binary+=String.fromCharCode(...decoded.subarray(i,i+8192));
  }
  if(btoa(binary).replaceAll("+","-").replaceAll("/","_").replace(/=+$/,"")!==value)
    refuse();
  return decoded;
}
export function validateSealedEnvelope(value){
  if(!value||typeof value!=="object"||Array.isArray(value)||
     Object.keys(value).sort().join(",")!==ENVELOPE_KEYS||
     value.kind!==SEALED_KIND||value.aad!==SEALED_KIND||
     value.version!==1||value.algorithm!=="AES-256-GCM"||
     value.kdf!=="PBKDF2-HMAC-SHA256"||
     !Number.isSafeInteger(value.iterations)||
     value.iterations<600000||value.iterations>2000000)refuse();
  const salt=base64(value.salt,16,16);
  const nonce=base64(value.nonce,12,12);
  const ciphertext=base64(value.ciphertext,16,MAX_CIPHER);
  return {salt,nonce,ciphertext};
}
export async function inspectSealedSnapshot(envelope,passphrase,
                                           cryptoApi=globalThis.crypto){
  if(typeof passphrase!=="string"||passphrase.length<16||
     passphrase.length>1024||!cryptoApi||!cryptoApi.subtle)refuse();
  const {salt,nonce,ciphertext}=validateSealedEnvelope(envelope);
  let plaintext;
  try{
    const secret=new TextEncoder().encode(passphrase);
    let material;
    try{
      material=await cryptoApi.subtle.importKey("raw",secret,
        "PBKDF2",false,["deriveKey"]);
    }finally{secret.fill(0)}
    const key=await cryptoApi.subtle.deriveKey({
      name:"PBKDF2",hash:"SHA-256",iterations:envelope.iterations,salt
    },material,{name:"AES-GCM",length:256},false,["decrypt"]);
    plaintext=new Uint8Array(await cryptoApi.subtle.decrypt({
      name:"AES-GCM",iv:nonce,
      additionalData:new TextEncoder().encode(SEALED_KIND),tagLength:128
    },key,ciphertext));
    if(plaintext.length>MAX_PLAINTEXT)refuse();
    const decoded=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(plaintext));
    if(!keys(decoded,["kind","version","saved_at_utc","window_label","tabs",
                       "browser_sway_identity_verified","restore_allowed"])||
       decoded.kind!==PLAIN_KIND||decoded.version!==1||
       decoded.browser_sway_identity_verified!==false||
       decoded.restore_allowed!==false||
       typeof decoded.saved_at_utc!=="string"||
       !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(decoded.saved_at_utc)||
       !Number.isFinite(Date.parse(decoded.saved_at_utc))||
       typeof decoded.window_label!=="string"||
       !LABEL.test(decoded.window_label)||
       !Array.isArray(decoded.tabs)||decoded.tabs.length<1||
       decoded.tabs.length>MAX_TABS)refuse();
    const summary=[];
    let activeCount=0,prior=-1,sensitive=0,pinned=0;
    for(const item of decoded.tabs){
      if(!keys(item,["source_position","url","pinned","was_active"])||
         !Number.isSafeInteger(item.source_position)||
         item.source_position<0||item.source_position<=prior||
         typeof item.pinned!=="boolean"||
         typeof item.was_active!=="boolean")refuse();
      prior=item.source_position;
      if(item.was_active)activeCount++;
      if(item.pinned)pinned++;
      const risk=classifySelectableUrl(item.url);
      if(risk==="excluded"||typeof item.url!=="string"||
         item.url.length>2048)refuse();
      if(risk==="sensitive")sensitive++;
      // Only the hostname, never path, query, fragment, or actual URL.
      const host=new URL(item.url).hostname.slice(0,100);
      summary.push(Object.freeze({
        position:item.source_position,hostname:host,
        pinned:item.pinned,was_active:item.was_active,risk
      }));
    }
    if(activeCount>1)refuse();
    return Object.freeze({
      status:"authenticated_redacted_review",
      window_label:decoded.window_label,
      tab_count:summary.length,pinned_count:pinned,
      sensitive_count:sensitive,
      tabs:Object.freeze(summary),
      browser_sway_identity_verified:false,
      restore_allowed:false,
      safe_actions:Object.freeze([])
    });
  }catch{
    refuse();
  }finally{
    if(plaintext)plaintext.fill(0);
  }
}
