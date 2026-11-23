import assert from "node:assert/strict";
import { normalizeSubmissions } from "../../scripts/finance/read_sec_filings.mjs";
import { normalizeCrawl } from "../../scripts/finance/read_scrapy_crawl.mjs";
import {
  previewEvidenceCandidates, prepareCandidateAttachDraft, CandidateRefusal
} from "../../scripts/finance/research_evidence_candidates.mjs";
import {
  createInvestigation, attachEvidence
} from "../../scripts/finance/research_investigations.mjs";
import { prepareResearchWrite } from "../../scripts/finance/research_investigation_write_contract.mjs";

const observed="2026-11-23T12:00:00.000Z";
const cik="0000320193";
const SEC_DOC="https://www.sec.gov/Archives/edgar/data/320193/000032019326000111/index.htm";
const sec = normalizeSubmissions({
  cik:320193,name:"Apple Inc",
  filings:{recent:{
    accessionNumber:["0000320193-26-000111"],
    filingDate:["2026-11-20"],
    form:["8-K"],
    primaryDocument:["index.htm"],
    items:["1.01"],
    acceptanceDateTime:["2026-11-20T12:33:00"]
  }}
},cik,observed);
assert.equal(sec.filings.length,1);
assert.equal(sec.filings[0].documentUrl,SEC_DOC);
const demo = normalizeCrawl([{
  schemaVersion:1,source:"finance-demo-scrapy",readOnly:true,
  url:"https://quotes.toscrape.com/page/1/",
  title:"Demonstration quotes",
  observedAt:observed,
  links:["https://quotes.toscrape.com/page/2/"],
  snippets:["Sample non-financial text"]
}]);
assert.equal(demo.pages.length,1);

const before=JSON.stringify({sec,demo});
const preview=previewEvidenceCandidates({secSnapshot:sec,crawlSnapshot:demo,selectedCik:cik});
assert.equal(JSON.stringify({sec,demo}),before,"Preview must never mutate source snapshots");
assert.deepEqual(preview.counts,{sec:1,demo:1,attachablePreview:1});
assert.equal(preview.candidates.length,2);
assert.equal(preview.schemaVersion,1);
assert.equal(preview.readOnly,true);
assert.equal(preview.secPresent,true);
assert.equal(preview.demoPresent,true);
assert.match(preview.notice,/NO AUTOMATIC SOURCE VERIFICATION/);

const filing=preview.candidates[0];
assert.equal(filing.kind,"sec-index");
assert.equal(filing.sourceLabel,"SEC EDGAR // INDEX");
assert.equal(filing.url,SEC_DOC);
assert.equal(filing.observedAt,observed);
assert.equal(filing.key,"sec:0000320193:0000320193-26-000111");
assert.equal(filing.eligibleForDraft,true);
assert.equal(filing.reviewed,false);
assert.equal(filing.authenticatedProvenance,false);
assert.match(filing.summary,/not been inspected/);
assert.match(filing.notice,/REVIEW OFFICIAL FILING/);

const sandbox=preview.candidates[1];
assert.equal(sandbox.kind,"demo-crawl");
assert.equal(sandbox.sourceLabel,"DEMO CRAWL // SAVED SNAPSHOT");
assert.equal(sandbox.eligibleForDraft,false);
assert.equal(sandbox.authenticatedProvenance,false);
assert.match(sandbox.notice,/BLOCKED/);

const investigations=createInvestigation([],{
  id:"test-case",title:"Quarterly source notes",
  question:"What did the issuer disclose?",timestamp:observed
});
const item=investigations[0];
const draft=prepareCandidateAttachDraft(filing,item);
assert.deepEqual(draft,{
  action:"attach",investigationId:"test-case",
  title:filing.title,summary:filing.summary,url:SEC_DOC
});
const proposal=prepareResearchWrite(draft,{
  schemaVersion:1,revision:0,investigations
},{
  clock:()=>observed,
  newId:()=>"12345678-1234-4234-8234-123456789abc"
});
assert.equal(proposal.expected.revision,1);
assert.equal(proposal.command.evidence.source,"manual",
  "Source preview must not silently become authenticated SEC evidence");
assert.equal(proposal.command.evidence.reviewed,false);
assert.equal(proposal.command.evidence.url,SEC_DOC);
assert.equal(proposal.command.action,"attach");
assert.equal(item.evidence.length,0,"Draft generation must not save evidence");

const saved=attachEvidence(investigations,item.id,proposal.command.evidence,observed);
assert.throws(()=>prepareCandidateAttachDraft(filing,saved[0]),
  e=>e instanceof CandidateRefusal && e.message==="CANDIDATE_REVIEW_REQUIRED");
assert.throws(()=>prepareCandidateAttachDraft(sandbox,item),
  e=>e instanceof CandidateRefusal && e.message==="INVALID_CANDIDATE_DRAFT");
assert.throws(()=>prepareCandidateAttachDraft({...filing,reviewed:true},item),
  e=>e instanceof CandidateRefusal);
assert.throws(()=>prepareCandidateAttachDraft({...filing,authenticatedProvenance:true},item),
  e=>e instanceof CandidateRefusal);
assert.throws(()=>prepareCandidateAttachDraft({...filing,url:"https://www.sec.gov.evil/Archives/edgar/data/320193/index.htm"},item),
  e=>e instanceof CandidateRefusal);
assert.throws(()=>prepareCandidateAttachDraft({...filing,url:SEC_DOC+"?redirect=1"},item),
  e=>e instanceof CandidateRefusal);
assert.throws(()=>prepareCandidateAttachDraft(filing,{...item,id:"../fake"}),
  e=>e instanceof CandidateRefusal);

const missing=previewEvidenceCandidates();
assert.deepEqual(missing.counts,{sec:0,demo:0,attachablePreview:0});
assert.equal(missing.secPresent,false);
assert.equal(missing.demoPresent,false);
const emptySec=previewEvidenceCandidates({
  secSnapshot:{...sec,filings:[]},selectedCik:cik
});
assert.equal(emptySec.counts.sec,0);
assert.equal(emptySec.secPresent,true);
assert.notDeepEqual(missing,emptySec,
  "Missing source must not be misrepresented as a successful empty feed");

for(const malformed of [
  {...sec,cik:"0000789019"},
  {...sec,issuer:"Fake Apple"},
  {...sec,source:"manual"},
  {...sec,retrievedAt:"not-a-date"},
  {...sec,filings:[...sec.filings,sec.filings[0]]},
  {...sec,filings:[{...sec.filings[0],documentUrl:
    "https://www.sec.gov.evil/Archives/edgar/data/320193/000032019326000111/index.htm"}]},
  {...sec,filings:[{...sec.filings[0],documentUrl:SEC_DOC+"?token=sneaky"}]},
  {...sec,filings:[{...sec.filings[0],primaryDocument:"../private"}]},
  {...sec,filings:[{...sec.filings[0],form:"unknown"}]},
  {...sec,filings:[{...sec.filings[0],items:["; rm -rf /"]}]}
]) assert.throws(()=>previewEvidenceCandidates({secSnapshot:malformed}),
  e=>e instanceof CandidateRefusal);
assert.throws(()=>previewEvidenceCandidates({
  secSnapshot:sec,selectedCik:"0000789019"
}),e=>e instanceof CandidateRefusal);
assert.throws(()=>previewEvidenceCandidates({selectedCik:cik}),
  e=>e instanceof CandidateRefusal);
for(const malformed of [
  {...demo,readOnly:false},
  {...demo,pageCount:2},
  {...demo,linkCount:99},
  {...demo,pages:[{...demo.pages[0],url:"https://quotes.toscrape.com.evil/page/1/"}]},
  {...demo,pages:[{...demo.pages[0],url:"https://quotes.toscrape.com:443/page/1/"}]},
  {...demo,pages:[...demo.pages,demo.pages[0]]},
  {...demo,pages:[{...demo.pages[0],observedAt:"yesterday"}]}
]) assert.throws(()=>previewEvidenceCandidates({crawlSnapshot:malformed}),
  e=>e instanceof CandidateRefusal);

assert.equal(previewEvidenceCandidates({secSnapshot:sec}).candidates.length,1);
assert.equal(previewEvidenceCandidates({crawlSnapshot:demo}).candidates.length,1);
console.log("Finance Research M6 source candidates: PASS");
