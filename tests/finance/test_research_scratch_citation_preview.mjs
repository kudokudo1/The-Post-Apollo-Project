import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { normalizeSubmissions } from "../../scripts/finance/read_sec_filings.mjs";
import { previewEvidenceCandidates, prepareCandidateAttachDraft
} from "../../scripts/finance/research_evidence_candidates.mjs";
import { validInvestigation } from "../../scripts/finance/research_investigations.mjs";
import {
  appendScratchCitation, ScratchRefusal, RESULT_PREFIX, ERROR_PREFIX
} from "../../scripts/finance/research_scratch_citation_preview.mjs";

const now="2026-11-24T12:00:00.000Z";
const sec=normalizeSubmissions({
  cik:320193,name:"Apple Inc",
  filings:{recent:{
    accessionNumber:["0000320193-26-000111","0000320193-26-000112"],
    filingDate:["2026-11-20","2026-11-21"],
    form:["8-K","4"],
    primaryDocument:["index.htm","form4.xml"],
    acceptanceDateTime:["2026-11-20T12:00:00","2026-11-21T12:00:00"],
    items:["1.01",""]
  }}
},"0000320193",now);
const [a,b]=previewEvidenceCandidates({secSnapshot:sec}).candidates;
const scratch={
  schemaVersion:1,id:"scratch_session_1",title:"Volatile case",
  question:"What do these SEC index entries show?",
  createdAt:now,updatedAt:now,evidence:[]
};
assert.equal(validInvestigation(scratch),true);
let serial=0;
const dependencies={
  now:()=>now,
  newId:()=>"scratch_e_00000000-0000-4000-8000-"
    +String(++serial).padStart(12,"0")
};
function makeRequest(caseData,candidate,edits={
  title:candidate.title,summary:candidate.summary,url:candidate.url
}) {
  const fields=prepareCandidateAttachDraft(candidate,caseData);
  const prepared={
    schemaVersion:1,readOnly:true,preparedOnly:true,candidateKey:candidate.key,
    investigationId:caseData.id,caseRevision:0,
    fields:{source:"manual",reviewed:false,
      title:fields.title,summary:fields.summary,url:fields.url},
    notice:"UNSAVED DRAFT // SEC INDEX ONLY // FILING NOT INSPECTED"
  };
  return {
    action:"append-to-memory",scratchCase:caseData,
    candidate,prepared,edits,revision:0
  };
}
function append(request) {
  const frame=JSON.stringify(request)+"\n";
  const raw=appendScratchCitation(frame,dependencies);
  assert.ok(raw.startsWith(RESULT_PREFIX));
  const data=JSON.parse(raw.slice(RESULT_PREFIX.length));
  assert.equal(data.schemaVersion,1);
  assert.equal(data.memoryOnly,true);
  assert.equal(data.persisted,false);
  assert.equal(data.caseRevision,0);
  assert.equal(Object.hasOwn(data,"action"),false);
  assert.equal(Object.hasOwn(data,"storePath"),false);
  assert.equal(validInvestigation(data.scratchCase),true);
  return data;
}
const first=makeRequest(scratch,a,{title:"First SEC index note",
  summary:"Index metadata only. Filing text has not been inspected.",url:a.url});
const frozen=JSON.stringify(first);
const result1=append(first);
assert.equal(JSON.stringify(first),frozen,"No input mutation");
assert.equal(result1.previousCount,0);
assert.equal(result1.scratchCase.evidence.length,1);
assert.equal(result1.scratchCase.evidence[0].reviewed,false);
assert.equal(result1.scratchCase.evidence[0].source,"manual");
assert.equal(result1.scratchCase.evidence[0].title,first.edits.title);
const result2=append(makeRequest(result1.scratchCase,b));
assert.equal(result2.previousCount,1);
assert.equal(result2.scratchCase.evidence.length,2);
assert.deepEqual(result2.scratchCase.evidence[0],
  result1.scratchCase.evidence[0]);
assert.notEqual(result2.addedId,result1.addedId);
assert.equal(validInvestigation(result2.scratchCase),true);
assert.ok(Buffer.byteLength(JSON.stringify(result2),"utf8")<200000);

const refuse=(request,code)=>{
  assert.throws(()=>appendScratchCitation(JSON.stringify(request)+"\n",dependencies),
    e=>e instanceof ScratchRefusal && e.message===code);
};
refuse(makeRequest(result1.scratchCase,a),"CANDIDATE_REVIEW_REQUIRED");
refuse({...first,action:"store-scratch"},"INVALID_REQUEST");
refuse({...first,revision:1},"INVALID_REQUEST");
refuse({...first,scratchCase:{...scratch,id:"non_scratch"}},"INVALID_REQUEST");
refuse({...first,edits:{...first.edits,url:"https://www.sec.gov.evil/not-sec"}},"CANDIDATE_MISMATCH");
refuse({...first,edits:{...first.edits,title:""}},"INVALID_SCRATCH_EVIDENCE");
refuse({...first,edits:{...first.edits,summary:"x".repeat(2001)}},"INVALID_SCRATCH_EVIDENCE");
refuse({...first,prepared:{...first.prepared,readOnly:false}},"INVALID_REQUEST");
refuse({...first,prepared:{...first.prepared,fields:{
  ...first.prepared.fields,url:"https://www.sec.gov/Archives/edgar/data/1/2/3"
}}},"CANDIDATE_MISMATCH");
refuse({...first,candidate:{...a,kind:"demo-crawl"}},"INVALID_CANDIDATE_DRAFT");
refuse({...first,candidate:{...a,authenticatedProvenance:true}},"INVALID_CANDIDATE_DRAFT");
refuse({...first,scratchCase:{...scratch,evidence:[{invalid:true}]}},"INVALID_REQUEST");
refuse({...first,extra:true},"INVALID_REQUEST");
const forty=Array.from({length:40},(_,i)=>({
  ...result1.scratchCase.evidence[0],
  id:"test_"+i,url:"https://www.sec.gov/Archives/edgar/data/320193/000032019326"
    +String(100000+i)+"/index.htm"
}));
assert.equal(validInvestigation({...scratch,evidence:forty}),true);
refuse(makeRequest({...scratch,evidence:forty},b),"CANDIDATE_REVIEW_REQUIRED");

const source=fileURLToPath(new URL(
  "../../scripts/finance/research_scratch_citation_preview.mjs",import.meta.url));
let child=spawnSync(process.execPath,[source],{
  input:JSON.stringify(first)+"\n",encoding:"utf8",timeout:4000
});
assert.equal(child.status,0,child.stderr);
assert.ok(child.stdout.startsWith(RESULT_PREFIX));
assert.equal(child.stderr,"");
child=spawnSync(process.execPath,[source,"--write"],{
  input:JSON.stringify(first)+"\n",encoding:"utf8",timeout:4000
});
assert.equal(child.status,1);
assert.equal(child.stdout,"");
assert.equal(child.stderr,ERROR_PREFIX+"INVALID_ARGUMENTS\n");

const live=spawn(process.execPath,[source],{stdio:["pipe","pipe","pipe"]});
let stdout="",stderr="",timer;
live.stdout.setEncoding("utf8");live.stderr.setEncoding("utf8");
live.stdout.on("data",x=>stdout+=x);live.stderr.on("data",x=>stderr+=x);
const done=new Promise((resolve,reject)=>{live.on("close",resolve);live.on("error",reject);});
live.stdin.write(JSON.stringify(first)+"\n"); // No EOF, as in Quickshell
const status=await Promise.race([done,new Promise((_,reject)=>{
  timer=setTimeout(()=>{live.kill("SIGKILL");reject(Error("waited for EOF"));},3000);
})]);
clearTimeout(timer);live.stdin.destroy();
assert.equal(status,0,stderr);
assert.ok(stdout.startsWith(RESULT_PREFIX));
console.log("Finance Research M9b multiple memory-only scratch citations: PASS");
