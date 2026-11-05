"use strict";
/*
 * TASKS M13t // Synthetic-only source-bound consent contract.
 * NEVER imported by QML, Connections or the production TASKS store.
 * The separate operator facade is available ONLY to disposable tests.
 * An in-process fixture cannot authenticate a real operator or application.
 */
const {createHash, createHmac, randomBytes, timingSafeEqual} = require("node:crypto");
const MARKER = "M13T_DISPOSABLE_ONLY";
const FEATURE = "tasks-draft-recovery";
const SCOPES = Object.freeze([
  "tasks.draft.capture.encrypted",
  "tasks.draft.preview.unlocked",
  "tasks.draft.clear.encrypted"
]);
const NO_POWER = Object.freeze({
  productionActivation:false, hostAuthenticated:false,
  callerAuthenticated:false, userConsentAuthenticated:false,
  sourceTrusted:false, keyringUnlocked:false,
  keyReleaseAuthorized:false, canCaptureDraft:false,
  canPersistDraft:false, canDecryptDraft:false,
  canPreviewDraft:false, canDeleteDraft:false,
  canRestoreDraft:false, canWriteTaskSource:false,
  realGrantActive:false
});
const exact = (obj, fields) => obj !== null && typeof obj === "object"
  && !Array.isArray(obj) && Object.keys(obj).sort().join(",") === fields.slice().sort().join(",");
const refusal = code => ({ok:false, status:code, ...NO_POWER});
const status = (code, fields={}) => ({ok:true, status:code, ...fields, ...NO_POWER});
const validId = x => typeof x === "string" && /^[a-f0-9]{32}$/.test(x);

function createDisposableModel({marker, readSavedSource, clock}={}) {
  if(marker !== MARKER || typeof readSavedSource !== "function"
    || typeof clock !== "function") throw Error("M13T_REFUSED_NOT_PRIVATE_FIXTURE");
  const sealKey = randomBytes(32);
  let optedIn = false;
  let generation = 0;
  const requests = new Map();
  const now = () => {
    const t=clock();
    return Number.isSafeInteger(t) && t>=0 && t<=Number.MAX_SAFE_INTEGER-300000 ? t : null;
  };
  function sourceDigest() {
    let data;
    try { data = readSavedSource(); } catch (_) { return null; }
    if(!Buffer.isBuffer(data) || data.length<2 || data.length>1024*1024)
      return null;
    return createHash("sha256").update(data).digest("hex");
  }
  function mac(r) {
    return createHmac("sha256",sealKey)
      .update(JSON.stringify([MARKER,FEATURE,r.id,r.scope,r.baseline,
                              r.generation,r.expiresAt]))
      .digest();
  }
  function recordFor(input) {
    if(!exact(input,["requestId","scope"]) || !validId(input.requestId)
      || !SCOPES.includes(input.scope)) return null;
    const r = requests.get(input.requestId);
    return r && r.scope === input.scope ? r : null;
  }
  const client = Object.freeze({
    propose(input) {
      if(!exact(input,["feature","scope"]) || input.feature!==FEATURE
         || !SCOPES.includes(input.scope)) return refusal("INVALID_FIXED_TASKS_SCOPE");
      const current=sourceDigest(), time=now();
      if(!current || time===null) return refusal("SAVED_SOURCE_NOT_OBSERVED");
      const id=randomBytes(16).toString("hex");
      requests.set(id,{id,scope:input.scope,baseline:current,
                       generation,createdAt:time,expiresAt:time+300000,
                       state:"PENDING",proof:null});
      return status("REVIEW_REQUIRED_NOT_AUTHORIZED",{requestId:id,
        scope:input.scope,feature:FEATURE,sourceObserved:true});
    },
    consume(input) {
      const r=recordFor(input);
      if(!r) return refusal("UNKNOWN_OR_MISMATCHED_REVIEW");
      if(!optedIn) return refusal("FEATURE_OPT_IN_OFF");
      if(r.state!=="APPROVED") return refusal("REVIEW_NOT_ACTIVE_OR_REPLAYED");
      const time=now();
      if(time===null || time>=r.expiresAt) {
        r.state="EXPIRED";
        return refusal("REVIEW_EXPIRED");
      }
      if(r.generation!==generation) return refusal("REVIEW_REVOKED");
      const current=sourceDigest();
      if(!current || current!==r.baseline) {
        r.state="SOURCE_CHANGED";
        return refusal("SAVED_SOURCE_CHANGED_REVIEW_REQUIRED");
      }
      const expected=mac(r);
      if(!Buffer.isBuffer(r.proof) || r.proof.length!==expected.length
          || !timingSafeEqual(expected,r.proof))
        return refusal("SOURCE_BOUND_REVIEW_INVALID");
      r.state="CONSUMED";
      return status("SYNTHETIC_SOURCE_BOUND_REVIEW_VERIFIED_NO_GRANT",{
        scope:r.scope,sourceObserved:true,simulatedReviewConsumed:true});
    },
    availability() {
      return status(optedIn?"SYNTHETIC_OPT_IN_RECORDED_NO_GRANT":"RECOVERY_DEFAULT_OFF",
                    {optInSimulated:optedIn});
    }
  });
  // In production, this facade would require independent host authority.
  // In this fixture the test harness holds it; no UI may import the fixture.
  const syntheticOperator = Object.freeze({
    optIn() {
      optedIn=true;
      return status("SYNTHETIC_OPT_IN_ONLY_NO_GRANT");
    },
    optOut() {
      optedIn=false;
      generation++;
      for(const r of requests.values()) r.state="REVOKED";
      return status("SYNTHETIC_OPT_OUT_REVOKED");
    },
    approve(input) {
      if(!exact(input,["requestId"]) || !validId(input.requestId))
        return refusal("INVALID_REVIEW_REFERENCE");
      const r=requests.get(input.requestId);
      if(!r) return refusal("UNKNOWN_REVIEW");
      if(!optedIn) return refusal("FEATURE_OPT_IN_OFF");
      if(r.state!=="PENDING") return refusal("REVIEW_NOT_PENDING");
      const time=now();
      if(time===null || time>=r.expiresAt) {
        r.state="EXPIRED";
        return refusal("REVIEW_EXPIRED");
      }
      if(r.generation!==generation) return refusal("REVIEW_REVOKED");
      const current=sourceDigest();
      if(!current || current!==r.baseline) {
        r.state="SOURCE_CHANGED";
        return refusal("SAVED_SOURCE_CHANGED_REVIEW_REQUIRED");
      }
      r.proof=mac(r);
      r.state="APPROVED";
      return status("SYNTHETIC_REVIEW_ACKNOWLEDGED_NO_GRANT",{scope:r.scope});
    },
    deny(input) {
      if(!exact(input,["requestId"]) || !validId(input.requestId))
        return refusal("INVALID_REVIEW_REFERENCE");
      const r=requests.get(input.requestId);
      if(!r || r.state!=="PENDING") return refusal("REVIEW_NOT_PENDING");
      r.state="DENIED";
      return status("SYNTHETIC_REVIEW_DENIED");
    }
  });
  return Object.freeze({client,syntheticOperator});
}
module.exports={MARKER,FEATURE,SCOPES,NO_POWER,createDisposableModel};
