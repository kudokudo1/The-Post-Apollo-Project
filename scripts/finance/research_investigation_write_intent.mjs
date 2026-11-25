// FinanceW Research M10c: pure, bounded durable intent frame for M2's
// existing exclusive writer lock. No filesystem, network or authorization.
import {createHash,randomUUID} from "node:crypto";
import {validateCollection} from "./research_investigations.mjs";

export const MAX_INTENT_BYTES = 1024;
export const INTENT_SCHEMA = 1;
const ACTIONS = new Set(["create","attach","remove"]);
const HEX64 = /^[a-f0-9]{64}$/;
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const FIELDS=["schemaVersion","operationId","action","priorRevision",
  "proposedRevision","priorFingerprint","proposedFingerprint"];
const exact=(item,fields)=>item!==null && typeof item==="object"
  && !Array.isArray(item) && Object.keys(item).length===fields.length
  && fields.every(f=>Object.prototype.hasOwnProperty.call(item,f));
function validDocument(doc) {
  return exact(doc,["schemaVersion","revision","investigations"])
    && doc.schemaVersion===1 && Number.isSafeInteger(doc.revision)
    && doc.revision>=0 && doc.revision<Number.MAX_SAFE_INTEGER
    && validateCollection(doc.investigations);
}
export function documentFingerprint(doc) {
  if(!validDocument(doc)) throw new TypeError("INVALID_RESEARCH_DOCUMENT");
  // M10b's existing probe uses the same canonical JSON.stringify fingerprint.
  return createHash("sha256").update(JSON.stringify(doc)).digest("hex");
}
export function validWriteIntent(intent) {
  return exact(intent,FIELDS) && intent.schemaVersion===INTENT_SCHEMA
    && typeof intent.operationId==="string" && UUID.test(intent.operationId)
    && ACTIONS.has(intent.action)
    && Number.isSafeInteger(intent.priorRevision)
    && intent.priorRevision>=0 && intent.priorRevision<Number.MAX_SAFE_INTEGER-1
    && intent.proposedRevision===intent.priorRevision+1
    && typeof intent.priorFingerprint==="string" && HEX64.test(intent.priorFingerprint)
    && typeof intent.proposedFingerprint==="string" && HEX64.test(intent.proposedFingerprint)
    && intent.priorFingerprint!==intent.proposedFingerprint;
}
export function prepareWriteIntent(command,prior,proposed,newId=randomUUID) {
  if(!validDocument(prior) || !validDocument(proposed)
      || !command || !ACTIONS.has(command.action)
      || command.expectedRevision!==prior.revision
      || proposed.revision!==prior.revision+1)
    throw new TypeError("INVALID_RESEARCH_INTENT");
  const operationId=newId();
  const intent={schemaVersion:INTENT_SCHEMA,operationId,
    action:command.action,priorRevision:prior.revision,
    proposedRevision:proposed.revision,
    priorFingerprint:documentFingerprint(prior),
    proposedFingerprint:documentFingerprint(proposed)};
  if(!validWriteIntent(intent)) throw new TypeError("INVALID_RESEARCH_INTENT");
  return intent;
}
export function encodeWriteIntent(intent) {
  if(!validWriteIntent(intent)) throw new TypeError("INVALID_RESEARCH_INTENT");
  const encoded=JSON.stringify(intent)+"\n";
  if(Buffer.byteLength(encoded,"utf8")>MAX_INTENT_BYTES)
    throw new TypeError("INVALID_RESEARCH_INTENT");
  return encoded;
}
export function parseWriteIntent(raw) {
  if(typeof raw!=="string" || Buffer.byteLength(raw,"utf8")>MAX_INTENT_BYTES
    || !raw.endsWith("\n") || raw.indexOf("\n")!==raw.length-1)
    throw new TypeError("INVALID_RESEARCH_INTENT");
  let intent;
  try {intent=JSON.parse(raw.slice(0,-1));}
  catch {throw new TypeError("INVALID_RESEARCH_INTENT");}
  if(!validWriteIntent(intent) || encodeWriteIntent(intent)!==raw)
    throw new TypeError("INVALID_RESEARCH_INTENT");
  return intent;
}
export function compareObservedWriteIntent(intent,observed) {
  if(!validWriteIntent(intent) || !validDocument(observed)) return "UNAVAILABLE";
  const fingerprint=documentFingerprint(observed);
  if(observed.revision===intent.proposedRevision
      && fingerprint===intent.proposedFingerprint)
    return "PROPOSED_MATCH_OBSERVED";
  if(observed.revision===intent.priorRevision
      && fingerprint===intent.priorFingerprint)
    return "PRIOR_MATCH_OBSERVED";
  return "DIFFERENT_DOCUMENT";
}
// No unlock, retry, resume, recovery commit or write transaction is exposed.
