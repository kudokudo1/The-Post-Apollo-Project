import assert from "node:assert/strict";
import { spawnSync, spawn } from "node:child_process";
import { Readable } from "node:stream";
import { fileURLToPath } from "node:url";
import { normalizeSubmissions } from "../../scripts/finance/read_sec_filings.mjs";
import { normalizeCrawl } from "../../scripts/finance/read_scrapy_crawl.mjs";
import {
  prepareCandidatePreviewResponse, readCandidateFrame, CandidateBridgeRefusal,
  RESULT_PREFIX, ERROR_PREFIX
} from "../../scripts/finance/research_candidate_preview_bridge.mjs";

const timestamp="2026-11-23T12:00:00.000Z";
const sec=normalizeSubmissions({
  cik:320193,name:"Apple Inc",
  filings:{recent:{
    accessionNumber:["0000320193-26-000111"],filingDate:["2026-11-20"],
    form:["8-K"],primaryDocument:["index.htm"],
    acceptanceDateTime:["2026-11-20T12:33:00"],items:["1.01"]
  }}
},"0000320193",timestamp);
const crawl=normalizeCrawl([{
  schemaVersion:1,source:"finance-demo-scrapy",readOnly:true,
  url:"https://quotes.toscrape.com/page/1/",
  title:"Sample quote",observedAt:timestamp,links:[],snippets:["Public demo"]
}]);
const request={action:"preview",selectedCik:"0000320193",
  secSnapshot:sec,crawlSnapshot:crawl};
const frame=JSON.stringify(request)+"\n";
const inputBefore=JSON.stringify(request);
const result=prepareCandidatePreviewResponse(frame);
assert.equal(JSON.stringify(request),inputBefore,"Preview must not mutate source input");
assert.ok(result.startsWith(RESULT_PREFIX));
const payload=JSON.parse(result.slice(RESULT_PREFIX.length));
assert.deepEqual(payload.counts,{sec:1,demo:1,attachablePreview:1});
assert.equal(payload.candidates[0].kind,"sec-index");
assert.equal(payload.candidates[0].reviewed,false);
assert.equal(payload.candidates[0].authenticatedProvenance,false);
assert.equal(payload.candidates[1].eligibleForDraft,false);

// M8a: the live SEC reader presents up to 30 recent submissions, not one.
// Exercise actual normalized shapes and the upper bound of JSON/IPC output.
const accessionNumber=Array.from({length:30},(_,i)=>
  "0000320193-26-"+String(i+111).padStart(6,"0"));
const filingDate=Array.from({length:30},()=>"2026-11-20");
const forms=Array.from({length:30},(_,i)=>i%3===0?"4":"8-K");
const documents=Array.from({length:30},(_,i)=>i%3===0
  ? "xslF345X05/wk-form4-"+String(i+111)+".xml":"index.htm");
const populatedSec=normalizeSubmissions({
  cik:320193,name:"Apple Inc",
  filings:{recent:{
    accessionNumber,filingDate,form:forms,primaryDocument:documents,
    acceptanceDateTime:Array.from({length:30},()=>"2026-11-20T12:33:00"),
    items:Array.from({length:30},(_,i)=>i%3===0?"":"1.01, 9.01")
  }}
},"0000320193",timestamp);
assert.equal(populatedSec.filings.length,30);
const maxFrame=JSON.stringify({...request,secSnapshot:populatedSec})+"\n";
const maxOutput=prepareCandidatePreviewResponse(maxFrame);
const maxPayload=JSON.parse(maxOutput.slice(RESULT_PREFIX.length));
assert.deepEqual(maxPayload.counts,{sec:30,demo:1,attachablePreview:30});
assert.equal(maxPayload.candidates.length,31);
assert.ok(maxPayload.candidates.slice(0,30).every(x=>
  x.kind==="sec-index" && x.reviewed===false
    && x.authenticatedProvenance===false));
assert.equal(maxPayload.candidates[30].eligibleForDraft,false);
// M8b: recreate the Python spider's exact ISO output. The old M6
// validator rejected +00:00 and six fractional digits after Crawl accepted
// them, which caused a combined SEC/Crawl preview to fail completely.
const scrapyCrawl=normalizeCrawl([{
  schemaVersion:1,source:"finance-demo-scrapy",readOnly:true,
  url:"https://quotes.toscrape.com/",
  title:"Synthetic Scrapy source",
  observedAt:"2026-11-23T14:42:00.123456+00:00",
  links:["https://quotes.toscrape.com/page/2/"],
  snippets:["Demo text"]
}]);
const bridgeFrame=JSON.stringify({
  ...request,secSnapshot:populatedSec,crawlSnapshot:scrapyCrawl
})+"\n";
const bridgeOutput=prepareCandidatePreviewResponse(bridgeFrame);
const bridgeResult=JSON.parse(bridgeOutput.slice(RESULT_PREFIX.length));
assert.deepEqual(bridgeResult.counts,{sec:30,demo:1,attachablePreview:30});
assert.equal(bridgeResult.candidates[30].observedAt,
  "2026-11-23T14:42:00.123456+00:00");
assert.equal(bridgeResult.candidates[30].eligibleForDraft,false);
const malformedDemo={...scrapyCrawl,pages:[
  {...scrapyCrawl.pages[0],observedAt:"NOT A VALID TIMESTAMP"}]};
assert.throws(()=>prepareCandidatePreviewResponse(JSON.stringify({
  ...request,crawlSnapshot:malformedDemo
})+"\n"),e=>e instanceof CandidateBridgeRefusal
  && e.message==="INVALID_DEMO_PAGE");
assert.throws(()=>prepareCandidatePreviewResponse(JSON.stringify({
  ...request,secSnapshot:{...sec,source:"untrusted"}
})+"\n"),e=>e instanceof CandidateBridgeRefusal
  && e.message==="INVALID_SEC_SNAPSHOT");
assert.ok(Buffer.byteLength(maxOutput,"utf8")<65536);
assert.ok(maxOutput.length<66000);
assert.match(payload.notice,/NO AUTOMATIC SOURCE VERIFICATION/);
assert.equal(prepareCandidatePreviewResponse(JSON.stringify({
  action:"preview",selectedCik:null,secSnapshot:null,crawlSnapshot:null
})+"\n").includes('"secPresent":false'),true);
assert.deepEqual(await readCandidateFrame(Readable.from([
  Buffer.from(frame.slice(0,11)),Buffer.from(frame.slice(11))
])),frame);
const refuses=e=>e instanceof CandidateBridgeRefusal;
await assert.rejects(readCandidateFrame(Readable.from([Buffer.from(frame.trim())])),refuses);
await assert.rejects(readCandidateFrame(Readable.from([
  Buffer.from("x".repeat(131073)+"\n")
])),refuses);
for(const bad of [
  frame+frame,frame.trimEnd(),JSON.stringify({...request,action:"create"})+"\n",
  JSON.stringify({...request,selectedCik:"0000789019"})+"\n",
  JSON.stringify({...request,extra:"hidden"})+"\n",
  JSON.stringify({...request,secSnapshot:{...sec,source:"manual"}})+"\n",
  JSON.stringify({...request,crawlSnapshot:{...crawl,readOnly:false}})+"\n",
  JSON.stringify({...request,selectedCik:"bogus"})+"\n"
]) assert.throws(()=>prepareCandidatePreviewResponse(bad),refuses);
let calls=0;
assert.throws(()=>prepareCandidatePreviewResponse(frame,()=>{calls++;throw Error("secret file path");}),
  e=>refuses(e)&&e.message==="INVALID_SOURCE_SNAPSHOT");
assert.equal(calls,1);

const script=fileURLToPath(new URL(
  "../../scripts/finance/research_candidate_preview_bridge.mjs",import.meta.url));
function cli(text,args=[]) {
  return spawnSync(process.execPath,[script,...args],{
    input:text,encoding:"utf8",timeout:3000,maxBuffer:1024*1024
  });
}
let actual=cli(frame);
assert.equal(actual.status,0,actual.stderr);
assert.equal(actual.stdout,result);
assert.equal(actual.stderr,"");
for(const bad of ['{"action":"remove"}\n','x\n',frame+frame]) {
  actual=cli(bad);
  assert.equal(actual.status,1);
  assert.equal(actual.stdout,"");
  assert.ok(actual.stderr.startsWith(ERROR_PREFIX));
}
actual=cli(frame,["--allow-writes"]);
assert.equal(actual.status,1);
assert.equal(actual.stdout,"");
assert.match(actual.stderr,/INVALID_ARGUMENTS/);

// Quickshell leaves stdin connected: the subprocess must finish on one LF.
const child=spawn(process.execPath,[script],{stdio:["pipe","pipe","pipe"]});
let stdout="",stderr="",timer;
child.stdout.setEncoding("utf8");
child.stderr.setEncoding("utf8");
child.stdout.on("data",part=>stdout+=part);
child.stderr.on("data",part=>stderr+=part);
const childExit=new Promise((resolve,reject)=>{
  child.on("close",resolve);child.on("error",reject);
});
child.stdin.write(frame);
const exitCode=await Promise.race([
  childExit,
  new Promise((_,reject)=>{
    timer=setTimeout(()=>{
      child.kill("SIGKILL");
      reject(new Error("Candidate preview bridge waited for stdin EOF"));
    },2500);
  })
]);
clearTimeout(timer);
child.stdin.destroy();
assert.equal(exitCode,0,stderr);
assert.equal(stdout,result);
console.log("Finance Research M7 candidate preview bridge: PASS");
