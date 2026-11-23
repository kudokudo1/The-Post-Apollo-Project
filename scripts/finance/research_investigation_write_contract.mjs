// FinanceW Research M4b: pure write-intent and acknowledgement contract.
// NO child process, filesystem, network, broker, or background execution.
// This is NOT an authorization/activation mechanism.
import { randomUUID } from "node:crypto";
import { isDeepStrictEqual } from "node:util";
import {
  createInvestigation, attachEvidence, removeEvidence, validateCollection
} from "./research_investigations.mjs";

const ACK_PREFIX = "FINANCE_RESEARCH_STORE_RESULT ";
const MAX_ACK_BYTES = 500100;
const MAX_COMMAND_BYTES = 8192;
const ID = /^[a-zA-Z0-9_-]{1,64}$/;
const FIELDS = Object.freeze({
  create: ["action", "title", "question"],
  attach: ["action", "investigationId", "title", "summary", "url"],
  remove: ["action", "investigationId", "evidenceId"]
});

export class WriteRefusal extends Error {}
function refuse(code) { throw new WriteRefusal(code); }
function exact(obj, keys) {
  return obj !== null && typeof obj === "object" && !Array.isArray(obj)
    && Object.keys(obj).length === keys.length
    && keys.every(key => Object.prototype.hasOwnProperty.call(obj, key));
}
function validDocument(doc) {
  return exact(doc, ["schemaVersion", "revision", "investigations"])
    && doc.schemaVersion === 1
    && Number.isSafeInteger(doc.revision)
    && doc.revision >= 0 && doc.revision < Number.MAX_SAFE_INTEGER - 1
    && validateCollection(doc.investigations);
}
function identifier(newId, prefix) {
  const value = newId();
  // The supplied generator must produce a UUID; never derive identity from a title.
  if (typeof value !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value))
    refuse("INVALID_GENERATED_ID");
  const id = prefix + value;
  if (!ID.test(id)) refuse("INVALID_GENERATED_ID");
  return id;
}
function timestamp(clock) {
  const value = clock();
  if (typeof value !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,3})?Z$/.test(value)
      || !Number.isFinite(Date.parse(value)))
    refuse("INVALID_CLOCK");
  return value;
}
export function prepareResearchWrite(request, current,
    {clock = () => new Date().toISOString(), newId = randomUUID} = {}) {
  if (!validDocument(current)) refuse("INVALID_SNAPSHOT");
  if (!request || !Object.prototype.hasOwnProperty.call(FIELDS, request.action)
      || !exact(request, FIELDS[request.action])) refuse("INVALID_INTENT");
  const stamp = timestamp(clock);
  const expectedRevision = current.revision;
  let command, investigations;
  try {
    if (request.action === "create") {
      const id = identifier(newId, "case-");
      command = {action:"create", expectedRevision, id,
        title:request.title, question:request.question, timestamp:stamp};
      investigations = createInvestigation(current.investigations, command);
    } else if (request.action === "attach") {
      const id = identifier(newId, "source-");
      // User-entered URLs are manually cited, NOT authenticated SEC/Crawl data.
      const evidence = {id, source:"manual", title:request.title,
        summary:request.summary, url:request.url, observedAt:stamp, reviewed:false};
      command = {action:"attach", expectedRevision,
        investigationId:request.investigationId, evidence, timestamp:stamp};
      investigations = attachEvidence(current.investigations,
        request.investigationId, evidence, stamp);
    } else {
      command = {action:"remove", expectedRevision,
        investigationId:request.investigationId, evidenceId:request.evidenceId,
        timestamp:stamp};
      investigations = removeEvidence(current.investigations,
        request.investigationId, request.evidenceId, stamp);
    }
  } catch (error) {
    if (error instanceof WriteRefusal) throw error;
    refuse("INVALID_RESEARCH_CHANGE");
  }
  const expected = {schemaVersion:1, revision:expectedRevision+1, investigations};
  const frame = JSON.stringify(command) + "\n";
  if (Buffer.byteLength(frame,"utf8") > MAX_COMMAND_BYTES) refuse("COMMAND_TOO_LARGE");
  if (!validDocument(expected)) refuse("INVALID_EXPECTED_STATE");
  // No I/O is performed. A future reviewed adapter must use these exact bytes
  // and refuse to generate an automatic retry after an unknown outcome.
  return {frame, command, expected, priorRevision:expectedRevision};
}
export function acknowledgeResearchWrite(raw, proposal) {
  if (!proposal || !validDocument(proposal.expected)
      || !Number.isSafeInteger(proposal.priorRevision)
      || proposal.expected.revision !== proposal.priorRevision + 1)
    refuse("INVALID_PROPOSAL");
  if (typeof raw !== "string" || Buffer.byteLength(raw,"utf8") > MAX_ACK_BYTES
      || !raw.startsWith(ACK_PREFIX) || !raw.endsWith("\n")
      || raw.indexOf("\n") !== raw.length - 1) refuse("INVALID_ACK");
  let doc;
  try { doc = JSON.parse(raw.slice(ACK_PREFIX.length, -1)); }
  catch { refuse("INVALID_ACK"); }
  if (!validDocument(doc)) refuse("INVALID_ACK");
  if (!isDeepStrictEqual(doc,proposal.expected)) refuse("ACK_MISMATCH");
  return doc;
}
// An unknown/failed result never means the mutation was rolled back.
// The controller must preserve the draft, disable writes and require a read.
export function writeFailureState() {
  return {state:"review-required",
    message:"WRITE OUTCOME UNKNOWN // KEEP DRAFT // RELOAD BEFORE ANOTHER ACTION",
    allowRetry:false};
}
