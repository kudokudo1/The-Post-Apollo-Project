#!/usr/bin/env node
// M9b: validate and append a citation into a VOLATILE case value.
// The only output is a NEW JSON value returned to QML. No filesystem,
// network, storage, finance account, or permanent investigation mutation.
import { randomUUID } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  attachEvidence, validInvestigation, validEvidence
} from "./research_investigations.mjs";
import {
  prepareCandidateAttachDraft, CandidateRefusal
} from "./research_evidence_candidates.mjs";

export const RESULT_PREFIX = "FINANCE_RESEARCH_SCRATCH_RESULT ";
export const ERROR_PREFIX = "FINANCE_RESEARCH_SCRATCH_ERROR ";
const MAX_INPUT_BYTES = 220000;
const MAX_OUTPUT_BYTES = 200000;
const exact = (v, keys) => v !== null && typeof v === "object"
  && !Array.isArray(v) && Object.keys(v).length === keys.length
  && keys.every(k => Object.hasOwn(v,k));
export class ScratchRefusal extends Error {}
const refuse = code => {throw new ScratchRefusal(code);};

export function appendScratchCitation(frame, { now=() => new Date().toISOString(),
  newId=() => "scratch_e_" + randomUUID() }={}) {
  if(typeof frame!=="string" || !frame.endsWith("\n")
      || frame.indexOf("\n")!==frame.length-1
      || Buffer.byteLength(frame,"utf8")>MAX_INPUT_BYTES)
    refuse("INVALID_FRAME");
  let request;
  try {request=JSON.parse(frame.slice(0,-1));}
  catch {refuse("INVALID_REQUEST");}
  if(!exact(request,["action","scratchCase","candidate","prepared","edits","revision"])
      || request.action!=="append-to-memory"
      || request.revision!==0
      || !validInvestigation(request.scratchCase)
      || !request.scratchCase.id.startsWith("scratch_")
      || !exact(request.edits,["title","summary","url"])
      || !exact(request.prepared,[
        "schemaVersion","readOnly","preparedOnly","candidateKey",
        "investigationId","caseRevision","fields","notice"
      ])
      || request.prepared.schemaVersion!==1
      || request.prepared.readOnly!==true
      || request.prepared.preparedOnly!==true
      || request.prepared.caseRevision!==0
      || request.prepared.investigationId!==request.scratchCase.id
      || request.prepared.candidateKey!==request.candidate?.key
      || request.prepared.notice!==
        "UNSAVED DRAFT // SEC INDEX ONLY // FILING NOT INSPECTED"
      || !exact(request.prepared.fields,["source","reviewed","title","summary","url"])
      || request.prepared.fields.source!=="manual"
      || request.prepared.fields.reviewed!==false)
    refuse("INVALID_REQUEST");

  let canonical;
  try {canonical=prepareCandidateAttachDraft(
    request.candidate,request.scratchCase);}
  catch(e) {
    if(e instanceof CandidateRefusal &&
        (e.message==="INVALID_CANDIDATE_DRAFT"
          || e.message==="CANDIDATE_REVIEW_REQUIRED"))
      refuse(e.message);
    refuse("INVALID_CANDIDATE");
  }
  if(request.prepared.fields.title!==canonical.title
      || request.prepared.fields.summary!==canonical.summary
      || request.prepared.fields.url!==canonical.url
      || request.edits.url!==canonical.url)
    refuse("CANDIDATE_MISMATCH");

  const {title,summary,url}=request.edits;
  const evidence={
    id:newId(),source:"manual",title,summary,url,
    observedAt:request.candidate.observedAt,reviewed:false
  };
  if(!validEvidence(evidence)
      || request.scratchCase.evidence.some(e=>e.url===url))
    refuse("INVALID_SCRATCH_EVIDENCE");
  let updated;
  try {
    const timestamp=now();
    updated=attachEvidence(
      [request.scratchCase],request.scratchCase.id,evidence,timestamp)[0];
  } catch {
    refuse("SCRATCH_LIMIT_OR_REVISION");
  }
  if(!validInvestigation(updated)
      || updated.id!==request.scratchCase.id
      || updated.evidence.length!==request.scratchCase.evidence.length+1)
    refuse("INVALID_RESULT");
  const response={
    schemaVersion:1,memoryOnly:true,persisted:false,
    caseRevision:0,candidateKey:request.candidate.key,
    previousCount:request.scratchCase.evidence.length,
    addedId:evidence.id,scratchCase:updated
  };
  const json=JSON.stringify(response);
  if(Buffer.byteLength(json,"utf8")>MAX_OUTPUT_BYTES)
    refuse("RESULT_TOO_LARGE");
  return RESULT_PREFIX+json+"\n";
}

async function readOneFrame(input) {
  const chunks=[];let bytes=0;
  for await(const block of input) {
    const chunk=Buffer.isBuffer(block)?block:Buffer.from(block);
    bytes+=chunk.length;
    if(bytes>MAX_INPUT_BYTES)refuse("INVALID_FRAME");
    const i=chunk.indexOf(10);
    if(i!==-1 && i!==chunk.length-1)refuse("INVALID_FRAME");
    chunks.push(chunk);
    if(i!==-1)return Buffer.concat(chunks).toString("utf8");
  }
  refuse("INVALID_FRAME");
}
const isMain = process.argv[1]
  && path.resolve(process.argv[1])===fileURLToPath(import.meta.url);
if(isMain) {
  try {
    if(process.argv.length!==2)refuse("INVALID_ARGUMENTS");
    const frame=await readOneFrame(process.stdin);
    process.stdout.write(appendScratchCitation(frame));
  } catch (e) {
    process.stderr.write(ERROR_PREFIX+
      (e instanceof ScratchRefusal?e.message:"SCRATCH_UNAVAILABLE")+"\n");
    process.exitCode=1;
  }
}
