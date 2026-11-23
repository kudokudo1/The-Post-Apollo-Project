import assert from "node:assert/strict";
import {spawn,spawnSync} from "node:child_process";
import {Readable} from "node:stream";
import {fileURLToPath} from "node:url";
import {normalizeSubmissions} from "../../scripts/finance/read_sec_filings.mjs";
import {previewEvidenceCandidates} from "../../scripts/finance/research_evidence_candidates.mjs";
import {createInvestigation} from "../../scripts/finance/research_investigations.mjs";
import {
  prepareUnsavedCitation,readDraftFrame,DraftPreviewRefusal,
  RESULT_PREFIX,ERROR_PREFIX
} from "../../scripts/finance/research_candidate_draft_preview.mjs";

const now="2026-11-23T12:00:00.000Z";
const sec=normalizeSubmissions({
  cik:320193,name:"Apple Inc",
  filings:{recent:{
    accessionNumber:["0000320193-26-000111"],filingDate:["2026-11-20"],
    form:["8-K"],primaryDocument:["index.htm"],items:["1.01"],
    acceptanceDateTime:["2026-11-20T12:33:00"]
  }}
},"0000320193",now);
const candidate=previewEvidenceCandidates({secSnapshot:sec}).candidates[0];
const investigation=createInvestigation([],{
  id:"test-case",title:"Synthetic case",question:"What does the index show?",
  timestamp:now
})[0];
const request={
  action:"prepare-draft",candidateKey:candidate.key,candidate,
  investigation,caseRevision:7
};
const frame=JSON.stringify(request)+"\n";
const before=JSON.stringify(request);
const response=prepareUnsavedCitation(frame);
assert.equal(JSON.stringify(request),before,"No source/case mutation allowed");
assert.ok(response.startsWith(RESULT_PREFIX));
const draft=JSON.parse(response.slice(RESULT_PREFIX.length));
assert.deepEqual(draft,{
  schemaVersion:1,readOnly:true,preparedOnly:true,
  candidateKey:candidate.key,investigationId:investigation.id,caseRevision:7,
  fields:{
    source:"manual",reviewed:false,
    title:candidate.title,summary:candidate.summary,url:candidate.url
  },
  notice:"UNSAVED DRAFT // SEC INDEX ONLY // FILING NOT INSPECTED"
});
assert.equal(Object.hasOwn(draft,"action"),false,"No executable attach command");

// M9a: the operator may have zero saved cases. A valid temporary case can
// still prepare fields; no collection change or storage operation occurs.
const scratch={
  schemaVersion:1,id:"scratch_session_1",title:"Temporary filing review",
  question:"What does this SEC index entry show?",
  createdAt:now,updatedAt:now,evidence:[]
};
const beforeScratch=JSON.stringify(scratch);
const scratchRequest={...request,investigation:scratch,caseRevision:0};
const scratchResponse=prepareUnsavedCitation(
  JSON.stringify(scratchRequest)+"\n");
const scratchDraft=JSON.parse(scratchResponse.slice(RESULT_PREFIX.length));
assert.equal(scratchDraft.investigationId,scratch.id);
assert.equal(scratchDraft.caseRevision,0);
assert.equal(scratchDraft.readOnly,true);
assert.equal(scratchDraft.preparedOnly,true);
assert.equal(scratchDraft.fields.source,"manual");
assert.equal(scratchDraft.fields.reviewed,false);
assert.equal(scratchDraft.fields.url,candidate.url);
assert.equal(JSON.stringify(scratch),beforeScratch);
assert.equal(Object.hasOwn(scratchDraft,"action"),false);
assert.equal(Object.hasOwn(scratchDraft,"storePath"),false);
for(const bad of [
  {...scratch,title:" "},
  {...scratch,question:""},
  {...scratch,id:"../escape"},
  {...scratch,updatedAt:"not a timestamp"},
  {...scratch,evidence: Array.from({length:41},()=>({}))}
]) assert.throws(()=>prepareUnsavedCitation(JSON.stringify({
  ...scratchRequest,investigation:bad
})+"\n"),e=>e instanceof DraftPreviewRefusal
  && e.message==="INVALID_CANDIDATE_DRAFT");

assert.ok(Buffer.byteLength(response,"utf8")<5500);
assert.deepEqual(await readDraftFrame(Readable.from([
  Buffer.from(frame.slice(0,21)),Buffer.from(frame.slice(21))
])),frame);
await assert.rejects(readDraftFrame(Readable.from(["missing newline"])),
  e=>e instanceof DraftPreviewRefusal);
await assert.rejects(readDraftFrame(Readable.from([
  Buffer.from("a".repeat(200001)+"\n")
])),e=>e instanceof DraftPreviewRefusal);

function refusal(overrides,code) {
  assert.throws(()=>prepareUnsavedCitation(JSON.stringify({
    ...request,...overrides
  })+"\n"),e=>e instanceof DraftPreviewRefusal && e.message===code);
}
refusal({candidateKey:"demo:0:https://quotes.toscrape.com/"},"INVALID_REQUEST");
refusal({candidateKey:"sec:0000320193:0000320193-26-000999"},"INVALID_REQUEST");
refusal({caseRevision:-1},"INVALID_REQUEST");
refusal({caseRevision:"7"},"INVALID_REQUEST");
refusal({action:"attach"},"INVALID_REQUEST");
refusal({candidate:{...candidate,kind:"demo-crawl"}},"INVALID_CANDIDATE_DRAFT");
refusal({candidate:{...candidate,url:"https://sec.gov.evil/fake"}},"CANDIDATE_REVIEW_REQUIRED");
refusal({candidate:{...candidate,reviewed:true}},"INVALID_CANDIDATE_DRAFT");
refusal({candidate:{...candidate,authenticatedProvenance:true}},"INVALID_CANDIDATE_DRAFT");
refusal({investigation:{...investigation,id:"../../other"}},"INVALID_CANDIDATE_DRAFT");
refusal({investigation:{...investigation,evidence:[
  {id:"existing",source:"manual",title:"Existing citation",
   summary:"Already cited",url:candidate.url,
   observedAt:now,reviewed:false}
]}},"CANDIDATE_REVIEW_REQUIRED");
refusal({extra:true},"INVALID_REQUEST");
assert.throws(()=>prepareUnsavedCitation(frame,()=>{
  throw Error("PRIVATE-PATH-DO-NOT-SHOW");
}),e=>e instanceof DraftPreviewRefusal && e.message==="CANDIDATE_DRAFT_UNAVAILABLE");
for(const invalid of [frame+frame,frame.trimEnd(),"not json\n"])
  assert.throws(()=>prepareUnsavedCitation(invalid),
    e=>e instanceof DraftPreviewRefusal);

const path=fileURLToPath(new URL(
  "../../scripts/finance/research_candidate_draft_preview.mjs",import.meta.url));
function cli(input,args=[]) {
  return spawnSync(process.execPath,[path,...args],{
    input,encoding:"utf8",timeout:3000,maxBuffer:1024*1024
  });
}
let p=cli(frame);
assert.equal(p.status,0,p.stderr);
assert.equal(p.stdout,response);
assert.equal(p.stderr,"");
p=cli(frame,["--write"]);
assert.equal(p.status,1);
assert.equal(p.stdout,"");
assert.match(p.stderr,/INVALID_ARGUMENTS/);
p=cli(JSON.stringify({...request,candidate:{...candidate,kind:"demo-crawl"}})+"\n");
assert.equal(p.status,1);
assert.equal(p.stdout,"");
assert.equal(p.stderr,ERROR_PREFIX+"INVALID_CANDIDATE_DRAFT\n");
assert.equal(p.stderr.includes("test-case"),false);

const child=spawn(process.execPath,[path],{stdio:["pipe","pipe","pipe"]});
let stdout="",stderr="",timer;
child.stdout.setEncoding("utf8");
child.stderr.setEncoding("utf8");
child.stdout.on("data",s=>stdout+=s);
child.stderr.on("data",s=>stderr+=s);
const done=new Promise((resolve,reject)=>{
  child.on("close",resolve);child.on("error",reject);
});
child.stdin.write(frame); // no EOF, matching Quickshell's Process use
const exitCode=await Promise.race([
  done,
  new Promise((_,reject)=>{
    timer=setTimeout(()=>{
      child.kill("SIGKILL");reject(Error("waited for EOF"));
    },2500);
  })
]);
clearTimeout(timer);
child.stdin.destroy();
assert.equal(exitCode,0,stderr);
assert.equal(stdout,response);
console.log("Finance Research M9 unsaved citation draft bridge: PASS");
