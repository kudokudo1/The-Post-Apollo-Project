import assert from "node:assert/strict";
import { auditResearchSnapshot, AuditRefusal
} from "../../scripts/finance/research_investigation_source_health.mjs";
import { createInvestigation, validateCollection
} from "../../scripts/finance/research_investigations.mjs";

const clock="2026-11-23T12:00:00Z";
const old="2026-01-01T00:00:00Z";
const recent="2026-11-22T12:00:00Z";
const future="2026-11-24T12:00:00Z";
const initial="2026-01-01T00:00:00Z";
const manual=(id,url,observedAt,reviewed) => ({
  id,source:"manual",title:"Research link "+id,
  summary:"Locally entered observation",url,observedAt,
  ...(reviewed===undefined?{}:{reviewed})
});
const empty={schemaVersion:1,revision:0,investigations:[]};
const emptyResult=auditResearchSnapshot(empty,{asOf:clock});
assert.equal(emptyResult.status,"no-local-flags");
assert.equal(emptyResult.metrics.caseCount,0);
assert.equal(emptyResult.findingsTotal,0);
assert.equal(emptyResult.omittedFindings,0);
assert.match(emptyResult.notice,/NO WEB FETCH/);

const cases=[
  ...createInvestigation([],{
    id:"empty-case",title:"No citations",question:"Need any evidence?",timestamp:initial
  }),
  ...createInvestigation([],{
    id:"source-case",title:"Filing research",question:"What changed?",timestamp:initial
  }),
  ...createInvestigation([],{
    id:"other-case",title:"Second context",question:"Another angle?",timestamp:initial
  })
];
cases[1].evidence=[
  manual("old-link","https://EXAMPLE.com/report",old,false),
  manual("same-link","https://example.com/report",recent,true),
  {id:"sec-one",source:"sec-edgar-submissions",title:"Declared SEC link",
    summary:"A URL label is not proof of a fetched filing",
    url:"https://www.sec.gov/Archives/edgar/data/320193/report.htm",
    observedAt:future},
  {id:"demo-one",source:"finance-demo-scrapy",title:"Demo content",
    summary:"Fictional training source",
    url:"https://quotes.toscrape.com/page/1/",observedAt:recent}
];
cases[2].evidence=[
  manual("cross-case","https://EXAMPLE.com/report",recent,false)
];
assert.equal(validateCollection(cases),true);
const snapshot={schemaVersion:1,revision:17,investigations:cases};
const frozenBefore=JSON.stringify(snapshot);
const report=auditResearchSnapshot(snapshot,{asOf:clock});
assert.equal(JSON.stringify(snapshot),frozenBefore,"Audit must not mutate source records");
assert.equal(report.sourceRevision,17);
assert.equal(report.assessedAt,clock);
assert.equal(report.staleDays,180);
assert.equal(report.status,"local-flags-present");
assert.deepEqual(report.metrics,{
  caseCount:3,
  evidenceCount:5,
  emptyCases:1,
  manualEvidence:3,
  manuallyMarkedReviewed:1,
  manualReviewPending:2,
  declaredSecEvidence:1,
  demoEvidence:1,
  reusedUrlsWithinCase:1,
  oldObservations:1,
  futureObservations:1,
  provenanceVerifiedByAudit:0
});
assert.equal(report.findingsTotal,7);
assert.equal(report.findings.length,7);
assert.equal(report.omittedFindings,0);
assert.deepEqual(report.findings[0],{
  code:"CASE_HAS_NO_EVIDENCE",investigationId:"empty-case",evidenceId:null
});
for (const expected of [
  "CASE_HAS_NO_EVIDENCE",
  "MANUAL_REVIEW_PENDING",
  "REPEATED_SOURCE_URL_IN_CASE",
  "OBSERVATION_OLDER_THAN_WINDOW",
  "OBSERVATION_IN_FUTURE",
  "DEMO_SOURCE_NOT_FINANCIAL_EVIDENCE"
]) assert.ok(report.findings.some(x=>x.code===expected),expected);
assert.ok(!report.findings.some(x=>x.evidenceId==="cross-case"
  && x.code==="REPEATED_SOURCE_URL_IN_CASE"),
  "A source URL may be intentionally reused in another case");
for(const finding of report.findings) {
  assert.deepEqual(Object.keys(finding),["code","investigationId","evidenceId"]);
  assert.ok(!JSON.stringify(finding).includes("https://"),
    "Findings must not leak original URLs or text");
}
assert.equal(report.metrics.provenanceVerifiedByAudit,0,
  "A local review flag and SEC label can never establish authenticated provenance");
assert.deepEqual(auditResearchSnapshot(snapshot,{asOf:clock}),report);

for(const [candidate,options,code] of [
  [{...snapshot,extra:true},{asOf:clock},"INVALID_RESEARCH_SNAPSHOT"],
  [{...snapshot,revision:-1},{asOf:clock},"INVALID_RESEARCH_SNAPSHOT"],
  [{...snapshot,investigations:[cases[0],cases[0]]},{asOf:clock},
    "INVALID_RESEARCH_SNAPSHOT"],
  [snapshot,{asOf:"2026-11-23"},"INVALID_AUDIT_OPTIONS"],
  [snapshot,{asOf:"not a date"},"INVALID_AUDIT_OPTIONS"],
  [snapshot,{asOf:clock,staleDays:0},"INVALID_AUDIT_OPTIONS"],
  [snapshot,{asOf:clock,staleDays:3651},"INVALID_AUDIT_OPTIONS"],
  [snapshot,{asOf:clock,staleDays:1.5},"INVALID_AUDIT_OPTIONS"]
]) assert.throws(()=>auditResearchSnapshot(candidate,options),
  e=>e instanceof AuditRefusal && e.message===code);

const boundary=manual("boundary","https://example.com/boundary",
  "2026-11-22T12:00:00Z",true);
const boundaryCase={...cases[1],evidence:[boundary]};
assert.equal(auditResearchSnapshot({
  schemaVersion:1,revision:2,investigations:[boundaryCase]
},{asOf:clock,staleDays:1}).metrics.oldObservations,0);

// Bound output to 100 details even for valid full-capacity collections.
// Complete numeric counts must still reflect every item.
const maxCases=Array.from({length:50},(_,i)=>({
  schemaVersion:1,id:"case-"+i,title:"Fixture",question:"Any evidence?",
  createdAt:initial,updatedAt:initial,
  evidence:Array.from({length:40},(_,j)=>
    manual("link-"+j,"https://example.com/same",old,false))
}));
assert.equal(validateCollection(maxCases),true);
const massive=auditResearchSnapshot({
  schemaVersion:1,revision:99,investigations:maxCases
},{asOf:clock});
assert.equal(massive.metrics.caseCount,50);
assert.equal(massive.metrics.evidenceCount,2000);
assert.equal(massive.metrics.reusedUrlsWithinCase,1950);
assert.equal(massive.metrics.manualReviewPending,2000);
assert.equal(massive.metrics.oldObservations,2000);
assert.equal(massive.findingsTotal,5950);
assert.equal(massive.findings.length,100);
assert.equal(massive.omittedFindings,5850);
assert.equal(massive.metrics.provenanceVerifiedByAudit,0);
console.log("Finance Research M5 read-only source health: PASS");
