import assert from "node:assert/strict";
import {
  createInvestigation, attachEvidence, removeEvidence,
  parseCollection, validateCollection, validEvidence
} from "../../scripts/finance/research_investigations.mjs";

const t0 = "2026-11-22T20:00:00Z";
const t1 = "2026-11-22T21:00:00Z";
const original = [];
const one = createInvestigation(original, {id:"apple-8k",title:"Apple filing",
  question:"What was disclosed in this filing?",timestamp:t0});
assert.equal(original.length, 0);
assert.equal(one.length, 1);
assert.equal(one[0].evidence.length, 0);
const sec = {id:"filing-1",source:"sec-edgar-submissions",title:"8-K filing",
  summary:"Factual source note; not a prediction.",url:"https://www.sec.gov/Archives/edgar/data/320193/abc.htm",
  observedAt:t0};
assert.equal(validEvidence(sec), true);
const two = attachEvidence(one,"apple-8k",sec,t1);
assert.equal(one[0].evidence.length,0);
assert.equal(two[0].evidence.length,1);
assert.equal(two[0].updatedAt,t1);
assert.deepEqual(parseCollection(JSON.stringify(two)),two);
assert.equal(removeEvidence(two,"apple-8k","filing-1",t1)[0].evidence.length,0);
assert.throws(()=>createInvestigation(one,{id:"apple-8k",title:"Duplicate",question:"Why?",timestamp:t1}));
assert.throws(()=>attachEvidence(two,"apple-8k",sec,t1));
assert.throws(()=>attachEvidence(two,"missing",sec,t1));
assert.throws(()=>removeEvidence(two,"apple-8k","missing",t1));
assert.equal(validEvidence({...sec,url:"https://evil.example/Archives/edgar/data/320193/abc.htm"}),false);
assert.equal(validEvidence({...sec,url:"http://www.sec.gov/Archives/edgar/data/320193/abc.htm"}),false);
assert.equal(validEvidence({...sec,url:"https://www.sec.gov@evil.example/Archives/edgar/data/320193/a"}),false);
assert.equal(validEvidence({...sec,source:"finance-demo-scrapy",url:"https://evil.example/page"}),false);
assert.equal(validEvidence({...sec,source:"unknown"}),false);
assert.equal(validEvidence({...sec,summary:"x".repeat(2001)}),false);
assert.equal(validateCollection([{...one[0],extra:"untrusted"}]),false);
assert.equal(validateCollection([one[0],one[0]]),false);
assert.equal(validateCollection(Array(51).fill(one[0])),false);
assert.throws(()=>parseCollection("{}".repeat(250001)));
const full = Array.from({length:40},(_,i)=>({...sec,id:"filing-"+i}));
const fullCollection = [{...one[0],evidence:full}];
assert.equal(validateCollection(fullCollection),true);
assert.throws(()=>attachEvidence(fullCollection,"apple-8k",{...sec,id:"overflow"},t1));
console.log("Finance Research M1 investigation policy: PASS");
