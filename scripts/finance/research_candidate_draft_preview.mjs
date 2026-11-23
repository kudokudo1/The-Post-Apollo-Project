#!/usr/bin/env node
// FinanceW Research M9: PREPARE AN UNSAVED CITATION DRAFT ONLY.
// Accepts an already displayed SEC index candidate and an already loaded
// local investigation. No fs, network, SEC fetch, account or store writer.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { prepareCandidateAttachDraft, CandidateRefusal
} from "./research_evidence_candidates.mjs";

export const RESULT_PREFIX = "FINANCE_RESEARCH_DRAFT_RESULT ";
export const ERROR_PREFIX = "FINANCE_RESEARCH_DRAFT_ERROR ";
const MAX_INPUT_BYTES = 200000;
const MAX_RESULT_BYTES = 5500;
const exact = (v,keys) => v && typeof v==="object" && !Array.isArray(v)
  && Object.keys(v).length===keys.length
  && keys.every(k=>Object.prototype.hasOwnProperty.call(v,k));
export class DraftPreviewRefusal extends Error {}
const refuse = code => { throw new DraftPreviewRefusal(code); };

export function prepareUnsavedCitation(frame, draftBuilder=prepareCandidateAttachDraft) {
  if(typeof frame!=="string"
      || Buffer.byteLength(frame,"utf8")>MAX_INPUT_BYTES
      || !frame.endsWith("\n") || frame.indexOf("\n")!==frame.length-1)
    refuse("INVALID_FRAME");
  let request;
  try {request=JSON.parse(frame.slice(0,-1));}
  catch {refuse("INVALID_REQUEST");}
  if(!exact(request,["action","candidateKey","candidate","investigation","caseRevision"])
      || request.action!=="prepare-draft"
      || typeof request.candidateKey!=="string"
      || !/^sec:\d{10}:\d{10}-\d{2}-\d{6}$/.test(request.candidateKey)
      || !exactObject(request.candidate) || request.candidate.key!==request.candidateKey
      || !exactObject(request.investigation)
      || !Number.isSafeInteger(request.caseRevision)
      || request.caseRevision<0 || request.caseRevision>=Number.MAX_SAFE_INTEGER)
    refuse("INVALID_REQUEST");
  let draft;
  try {draft=draftBuilder(request.candidate,request.investigation);}
  catch(e){
    if(e instanceof CandidateRefusal
        && (e.message==="INVALID_CANDIDATE_DRAFT"
            || e.message==="CANDIDATE_REVIEW_REQUIRED"))
      refuse(e.message);
    refuse("CANDIDATE_DRAFT_UNAVAILABLE");
  }
  if(!exact(draft,["action","investigationId","title","summary","url"])
      || draft.action!=="attach"
      || draft.investigationId!==request.investigation.id
      || typeof draft.title!=="string" || draft.title.length>160
      || typeof draft.summary!=="string" || draft.summary.length>2000
      || typeof draft.url!=="string" || draft.url.length>1000)
    refuse("INVALID_RESULT");
  const result={
    schemaVersion:1,readOnly:true,preparedOnly:true,
    candidateKey:request.candidateKey,
    investigationId:draft.investigationId,
    caseRevision:request.caseRevision,
    fields:{
      source:"manual",reviewed:false,
      title:draft.title,summary:draft.summary,url:draft.url
    },
    notice:"UNSAVED DRAFT // SEC INDEX ONLY // FILING NOT INSPECTED"
  };
  const payload=JSON.stringify(result);
  if(Buffer.byteLength(payload,"utf8")>MAX_RESULT_BYTES)
    refuse("RESULT_TOO_LARGE");
  return RESULT_PREFIX+payload+"\n";
}
function exactObject(v) {return v!==null && typeof v==="object" && !Array.isArray(v);}
export async function readDraftFrame(input) {
  const chunks=[];
  let total=0;
  for await(const block of input) {
    const chunk=Buffer.isBuffer(block)?block:Buffer.from(block);
    total+=chunk.length;
    if(total>MAX_INPUT_BYTES)refuse("INVALID_FRAME");
    const nl=chunk.indexOf(10);
    if(nl>=0 && nl!==chunk.length-1)refuse("INVALID_FRAME");
    chunks.push(chunk);
    if(nl>=0)return Buffer.concat(chunks).toString("utf8");
  }
  refuse("INVALID_FRAME");
}
const isMain=process.argv[1]
  && path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(isMain){
  try{
    if(process.argv.length!==2)refuse("INVALID_ARGUMENTS");
    const frame=await readDraftFrame(process.stdin);
    process.stdout.write(prepareUnsavedCitation(frame));
  }catch(e){
    process.stderr.write(ERROR_PREFIX+
      (e instanceof DraftPreviewRefusal?e.message:"DRAFT_UNAVAILABLE")+"\n");
    process.exitCode=1;
  }
}
