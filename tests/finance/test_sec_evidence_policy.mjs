#!/usr/bin/env node
// Fictional disclosure evidence. Pure local policy; no network or user files.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const src = readFileSync(new URL("../../widgets/FinanceSecEvidencePolicy.js", import.meta.url), "utf8");
const context = vm.createContext({});
const policy = vm.runInContext(src + "\n({filterFilings,filterTransactions,brief,pinEvidence})", context);

const filings = [
  {form:"4",accession:"F4"},
  {form:"8-K",accession:"F8"},
  {form:"SC 13D",accession:"FO"},
  {form:"10-Q",accession:"FQ"},
  {form:"4/A",accession:"F4A"},
  {form:"8-K/A",accession:"F8A"},
  {form:"SC 13G/A",accession:"FOA"},
  {form:"10-K/A",accession:"FKA"}
];
for (const [mode,expected] of [
  ["all",8],["insider",2],["events",2],["owners",2],["reports",2]
]) assert.equal(policy.filterFilings(filings,mode).length,expected);
assert.equal(policy.filterFilings(null,"all").length,0);
assert.equal(policy.filterFilings(filings,"something").length,8);

const tx = [
  {code:"P",date:"2026-10-01",shares:"10",pricePerShare:"12.5"},
  {code:"S",date:"2026-10-02",shares:"15",pricePerShare:"20"},
  {code:"A",date:"2026-10-03",shares:"7"},
  {code:"M",date:"2026-10-04",shares:"4"},
  {code:"F",date:"2026-10-05",shares:"1"}
];
for (const [mode,expected] of [
  ["all",5],["P",1],["S",1],["A",1],["M",1],["other",1]
]) assert.equal(policy.filterTransactions(tx,mode).length,expected);
assert.equal(policy.filterTransactions(tx,"garbage").length,0);
const cik="0000320193";
const make=(acc,form,detailKind,transactions=tx)=>({
  cik,accession:acc,form,kind:detailKind,
  retrievedAt:"2026-10-24T19:00:00Z",
  documentUrl:"https://www.sec.gov/Archives/edgar/data/320193/"+acc.replaceAll("-","")+"/report.xml",
  owners:["Fictional Owner"],transactions,
  events:[{item:"5.02",category:"DIRECTORS / OFFICERS",source:"FILING HEADING"}]
});
const a="0000320193-26-000011",b="0000320193-26-000012",c="0000320193-26-000013";
const filing=doc=>({accession:doc.accession,form:doc.form,filedAt:"2026-10-24"});
const docA=make(a,"4","form4"),docB=make(b,"8-K","form8k"),docC=make(c,"4","form4");
const facts=policy.brief(docA);
assert.match(facts.summary,/P 1  S 1  A 1  M 1  OTHER 1/);
assert.equal(facts.excerpts.length,3);
assert.equal(facts.label,"FORM 4 // NON-DERIVATIVE");
assert.equal(policy.brief(docB).excerpts[0],"ITEM 5.02 // DIRECTORS / OFFICERS [FILING HEADING]");
assert.equal(policy.brief({kind:"other"}),null);

let pins=policy.pinEvidence([],filing(docA),docA,cik);
assert.equal(pins.length,1);
pins=policy.pinEvidence(pins,filing(docA),docA,cik);
assert.equal(pins.length,1); // idempotent re-pin
pins=policy.pinEvidence(pins,filing(docB),docB,cik);
assert.equal(pins.length,2);
assert.equal(pins[0].accession,a);
assert.equal(pins[1].accession,b);
assert.equal(pins[1].facts.label,"FORM 8-K // ITEMS");
pins=policy.pinEvidence(pins,filing(docC),docC,cik);
assert.equal(pins.length,2);
assert.equal(pins[0].accession,b); // oldest evicted, stable bound
assert.equal(pins[1].accession,c);
assert.equal(policy.pinEvidence(pins,filing(docA),docA,"0000789019"),null);
assert.equal(policy.pinEvidence(pins,{...filing(docA),accession:b},docA,cik),null);
assert.equal(policy.pinEvidence(pins,filing(docA),{...docA,documentUrl:"https://bad.example/"},cik),null);
const cross = policy.pinEvidence(pins,filing({...docA,cik:"0000789019"}),
  {...docA,cik:"0000789019"},"0000789019");
assert.equal(cross.length,1);
assert.equal(cross[0].cik,"0000789019");
assert.equal(cross[0].accession,a);
console.log("Finance SEC M4 filters and issuer-bound two-slot evidence fixtures: PASS");
