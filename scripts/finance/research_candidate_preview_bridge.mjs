#!/usr/bin/env node
// FinanceW Research M7: one explicit read-only transformation of EXISTING
// SEC/Crawl snapshots. No provider calls, disk access, or persistence writes.
import { fileURLToPath } from "node:url";
import path from "node:path";
import { previewEvidenceCandidates, CandidateRefusal } from "./research_evidence_candidates.mjs";

export const RESULT_PREFIX = "FINANCE_RESEARCH_CANDIDATES_RESULT ";
export const ERROR_PREFIX = "FINANCE_RESEARCH_CANDIDATES_ERROR ";
const MAX_REQUEST_BYTES = 131072;
const MAX_RESULT_BYTES = 65536;
// The M6 source validator emits only fixed codes. Never forward unknown
// exceptions, individual URLs, titles, accession numbers or source text.
const SOURCE_REFUSALS = new Set([
  "INVALID_ISSUER_SELECTION", "INVALID_SEC_SNAPSHOT",
  "INVALID_SEC_FILING", "INVALID_SEC_URL",
  "INVALID_DEMO_SNAPSHOT", "INVALID_DEMO_PAGE",
  "INVALID_DEMO_COUNT"
]);
export class CandidateBridgeRefusal extends Error {}
function refuse(code) { throw new CandidateBridgeRefusal(code); }
function exact(value, keys) {
  return value && typeof value === "object" && !Array.isArray(value)
    && Object.keys(value).length === keys.length
    && keys.every(key=>Object.prototype.hasOwnProperty.call(value,key));
}
export function prepareCandidatePreviewResponse(frame, transform=previewEvidenceCandidates) {
  if(typeof frame!=="string"
      || Buffer.byteLength(frame,"utf8") > MAX_REQUEST_BYTES
      || !frame.endsWith("\n") || frame.indexOf("\n")!==frame.length-1)
    refuse("INVALID_FRAME");
  let request;
  try { request=JSON.parse(frame.slice(0,-1)); }
  catch { refuse("INVALID_REQUEST"); }
  if(!exact(request,["action","selectedCik","secSnapshot","crawlSnapshot"])
      || request.action!=="preview"
      || !(request.selectedCik===null
        || (typeof request.selectedCik==="string"
        && /^\d{10}$/.test(request.selectedCik)))
      || (request.secSnapshot!==null && !exactObject(request.secSnapshot))
      || (request.crawlSnapshot!==null && !exactObject(request.crawlSnapshot)))
    refuse("INVALID_REQUEST");
  let result;
  try {
    result=transform({
      secSnapshot:request.secSnapshot,
      crawlSnapshot:request.crawlSnapshot,
      selectedCik:request.selectedCik===null?undefined:request.selectedCik
    });
  }catch(error){
    if(error instanceof CandidateRefusal && SOURCE_REFUSALS.has(error.message))
      refuse(error.message);
    refuse("INVALID_SOURCE_SNAPSHOT");
  }
  if (!result || result.readOnly!==true
      || !Array.isArray(result.candidates) || result.candidates.length>36)
    refuse("INVALID_RESULT");
  const payload=JSON.stringify(result);
  if(Buffer.byteLength(payload,"utf8")>MAX_RESULT_BYTES)refuse("RESULT_TOO_LARGE");
  return RESULT_PREFIX+payload+"\n";
}
function exactObject(x) { return x!==null && typeof x==="object" && !Array.isArray(x); }
export async function readCandidateFrame(input) {
  const chunks=[];
  let total=0;
  for await(const piece of input) {
    const chunk=Buffer.isBuffer(piece)?piece:Buffer.from(piece);
    total+=chunk.length;
    if(total>MAX_REQUEST_BYTES) refuse("INVALID_FRAME");
    const nl=chunk.indexOf(10);
    if(nl>=0 && nl!==chunk.length-1) refuse("INVALID_FRAME");
    chunks.push(chunk);
    if(nl>=0)return Buffer.concat(chunks).toString("utf8");
  }
  refuse("INVALID_FRAME");
}
const isMain=process.argv[1]
  && path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(isMain){
  try {
    if(process.argv.length!==2)refuse("INVALID_ARGUMENTS");
    const frame=await readCandidateFrame(process.stdin);
    process.stdout.write(prepareCandidatePreviewResponse(frame));
  }catch(error){
    process.stderr.write(ERROR_PREFIX+
      (error instanceof CandidateBridgeRefusal?error.message:"PREVIEW_UNAVAILABLE")+"\n");
    process.exitCode=1;
  }
}
