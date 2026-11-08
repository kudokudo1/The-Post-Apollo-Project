"use strict";
/* TASKS M15e // disposable single-editor snapshot transaction.
 * NEVER import into the desktop, production TASKS, or Connections.
 * Synthetic host approval is NOT process authentication or real consent.
 * The capture callback is invoked only after a single-use, source- and
 * editor-identity-bound test grant. Nothing returned exposes plaintext.
 */
const {randomBytes,createHash,createHmac,timingSafeEqual}=require("node:crypto");
const MARKER="M15E_DISPOSABLE_HOST_ONLY";
const CAPTURE="tasks.draft.capture.encrypted";
const PREVIEW="tasks.draft.preview.unlocked";
const CLEAR="tasks.draft.clear.encrypted";
const DENIED=Object.freeze({productionActivation:false,hostAuthenticated:false,
  realGrantActive:false,userConsentAuthenticated:false,keyReleaseAuthorized:false,
  canCaptureDraft:false,canPreviewDraft:false,canDeleteDraft:false,
  canWriteTaskSource:false,canRestoreDraft:false});
const exact=(v,keys)=>v&&typeof v==="object"&&!Array.isArray(v)
  &&Object.keys(v).sort().join(",")===keys.slice().sort().join(",");
const reply=(status,ok=false)=>({ok,status,...DENIED});
const key=x=>typeof x==="string"&&/^[A-Za-z0-9_-]{1,90}$/.test(x);
const positive=x=>Number.isSafeInteger(x)&&x>0;
function createDisposableHost({marker,readSource,readEditorState,readEditorSnapshot,
                               encryptSnapshot,clock}={}){
  if(marker!==MARKER||![readSource,readEditorState,readEditorSnapshot,
    encryptSnapshot,clock].every(x=>typeof x==="function"))
    throw Error("M15E_REFUSED_NOT_DISPOSABLE_TEST");
  const secret=randomBytes(32);const pending=new Map();let generation=0,enabled=false;
  const now=()=>{const x=clock();return Number.isSafeInteger(x)&&x>=0?x:null;};
  function source(){
    try{
      const s=readSource();
      if(!exact(s,["bytes","generation","ownerEpoch","committed"])
        ||!Buffer.isBuffer(s.bytes)||s.bytes.length<2||s.bytes.length>1048576
        ||!positive(s.generation)||!key(s.ownerEpoch)||s.committed!==true)
        return null;
      return {generation:s.generation,ownerEpoch:s.ownerEpoch,
        digest:createHash("sha256").update(s.bytes).digest("hex")};
    }catch(_){return null;}
  }
  function editor(target){
    try{
      const e=readEditorState(target);
      if(!exact(e,["target","identity","editEpoch","dirty","savePending"])
        ||e.target!==target||!key(e.identity)||!positive(e.editEpoch)
        ||e.dirty!==true||e.savePending!==false)return null;
      return {target:e.target,identity:e.identity,editEpoch:e.editEpoch};
    }catch(_){return null;}
  }
  const match=(a,b)=>a&&b&&Object.keys(a).every(k=>a[k]===b[k]);
  function proof(r){return createHmac("sha256",secret)
    .update(JSON.stringify([r.id,r.scope,r.target,r.source,r.editor,
      r.generation,r.deadline])).digest();}
  const client=Object.freeze({
    request(input){
      if(!exact(input,["scope","target"])||input.scope!==CAPTURE
        ||!["entry","details"].includes(input.target))return reply("WRONG_SCOPE_OR_TARGET");
      const t=now(),s=source(),e=editor(input.target);
      if(t===null||!s||!e)return reply("SOURCE_OR_EDITOR_NOT_VERIFIED");
      const id=randomBytes(16).toString("hex");
      pending.set(id,{id,scope:CAPTURE,target:input.target,source:s,editor:e,
        generation,deadline:t+30000,state:"PENDING",seal:null});
      return {ok:true,status:"SYNTHETIC_REVIEW_REQUIRED_NO_GRANT",requestId:id,...DENIED};
    },
    capture(input){
      if(!exact(input,["requestId","scope","target"])
        ||typeof input.requestId!=="string"||input.scope!==CAPTURE
        ||!["entry","details"].includes(input.target))return reply("INVALID_CAPTURE_REQUEST");
      const r=pending.get(input.requestId);
      if(!r||r.scope!==input.scope||r.target!==input.target)
        return reply("UNKNOWN_OR_WRONG_TARGET");
      if(!enabled||r.generation!==generation)return reply("REVOKED_OR_OFF");
      if(r.state!=="APPROVED")return reply("NOT_APPROVED_OR_REPLAYED");
      // Burn before any potentially reentrant/editor-controlled operation.
      r.state="CONSUMED";
      const t=now();if(t===null||t>=r.deadline)return reply("EXPIRED");
      if(!Buffer.isBuffer(r.seal)||!timingSafeEqual(proof(r),r.seal))
        return reply("INVALID_HOST_REVIEW_PROOF");
      if(!match(source(),r.source)||!match(editor(r.target),r.editor))
        return reply("STALE_SOURCE_OR_EDITOR");
      let draft;
      try{draft=readEditorSnapshot(r.target);}catch(_){return reply("EDITOR_READ_REFUSED");}
      if(!exact(draft,["target","identity","editEpoch","text"])
        ||draft.target!==r.target||draft.identity!==r.editor.identity
        ||draft.editEpoch!==r.editor.editEpoch||typeof draft.text!=="string"
        ||Buffer.byteLength(draft.text,"utf8")<1
        ||Buffer.byteLength(draft.text,"utf8")>8192)
        return reply("EDITOR_SNAPSHOT_INVALID");
      // Reobserve after the synchronous read to catch mutations during capture.
      if(!match(source(),r.source)||!match(editor(r.target),r.editor))
        return reply("SOURCE_OR_EDITOR_CHANGED_DURING_SNAPSHOT");
      let committed=false;
      try{committed=encryptSnapshot({target:r.target,identity:r.editor.identity,
        editEpoch:r.editor.editEpoch,source:r.source,text:draft.text})===true;}
      catch(_){committed=false;}
      // Do not return text, source identity, ciphertext, or a production grant.
      return reply(committed?"SYNTHETIC_ENCRYPTION_CALLBACK_ACCEPTED_NO_REAL_GRANT"
                            :"ENCRYPTION_NOT_CONFIRMED",committed);
    }
  });
  const syntheticOperator=Object.freeze({
    enable(){enabled=true;return reply("SIMULATED_OPT_IN_NO_GRANT");},
    revoke(){enabled=false;generation++;for(const r of pending.values())r.state="REVOKED";
      return reply("SIMULATED_REVOKED");},
    approve(input){
      if(!exact(input,["requestId"])||typeof input.requestId!=="string")
        return reply("INVALID_REVIEW_ID");
      const r=pending.get(input.requestId),t=now();
      if(!enabled||!r||r.state!=="PENDING"||t===null||t>=r.deadline
        ||r.generation!==generation)return reply("REVIEW_REFUSED");
      if(!match(source(),r.source)||!match(editor(r.target),r.editor)){
        r.state="INVALIDATED";return reply("STALE_REVIEW_REFUSED");
      }
      r.seal=proof(r);r.state="APPROVED";
      return reply("SYNTHETIC_APPROVAL_ONLY");
    }
  });
  return Object.freeze({client,syntheticOperator});
}
module.exports={MARKER,CAPTURE,PREVIEW,CLEAR,DENIED,createDisposableHost};
