#!/usr/bin/env node
// Fictional SEC submissions fixture. No SEC network request or real contact data.
import assert from "node:assert/strict";
import {
  validateAgent, normalizeCik, normalizeSubmissions, loadSec, ISSUERS
} from "../../scripts/finance/read_sec_filings.mjs";

assert.equal(ISSUERS["0000320193"], "Apple");
assert.equal(normalizeCik(320193), "0000320193");
assert.equal(normalizeCik("320193"), "0000320193");
assert.equal(normalizeCik("0000320193"), "0000320193");
assert.equal(normalizeCik("0000320194"), "0000320194");
for (const invalid of [null, undefined, {}, false, -1, 320193.5, NaN,
  Infinity, "3.20193e5", " 320193", "320193 ", "0000000320193",
  "0000320193\\n", "abc320193"]) {
  assert.equal(normalizeCik(invalid), null, String(invalid));
}
assert.equal(validateAgent("PostApollo Finance Research analyst@testing.invalid\n"),
  "PostApollo Finance Research analyst@testing.invalid");
assert.equal(validateAgent("PostApollo Finance Research test@example.com"), null);
assert.equal(validateAgent("PostApollo Finance Research analyst@testing.invalid\nx"), null);
assert.equal(validateAgent(""), null);

const submission = {
  cik: 320193, name: "Fictional Company Fixture",
  filings: {recent:{
    accessionNumber:["0000320193-26-000013","0000320193-26-000014",
                     "0000320193-26-000015","0000320193-26-000016"],
    filingDate:["2026-10-21","2026-10-23","2026-10-22","2026-10-24"],
    form:["8-K","4","SC 13D","OTHER"],
    primaryDocument:["event.htm","insider.xml","owner.htm","other.htm"],
    acceptanceDateTime:["2026-10-21T15:00:00.000Z","2026-10-23T16:00:00.000Z",
                        "2026-10-22T20:00:00.000Z","2026-10-24T09:00:00.000Z"],
  }}
};
const data = normalizeSubmissions(submission, "0000320193", "2026-10-24T16:00:00Z");
// SEC may return a zero-padded CIK string rather than an integer.
// The pre-fix implementation failed with wrong-issuer for this valid form.
const padded = normalizeSubmissions({...submission,cik:"0000320193"}, "0000320193", "now");
assert.equal(padded.filings.length, 3);
assert.equal(normalizeSubmissions({...submission,cik:"320193"}, "0000320193", "now").filings.length, 3);
assert.throws(()=>normalizeSubmissions({...submission,cik:"0000320194"},"0000320193","now"),/wrong-issuer/);
assert.throws(()=>normalizeSubmissions({...submission,cik:"garbage"},"0000320193","now"),/wrong-issuer/);
assert.equal(data.source, "sec-edgar-submissions");
assert.equal(data.readOnly,true);
assert.equal(data.filings.length,3);
assert.deepEqual(data.filings.map(x=>x.form), ["4","SC 13D","8-K"]);
assert.equal(data.filings[0].category, "INSIDER DISCLOSURE");
assert.equal(data.filings[0].primaryDocument, "insider.xml");
assert.deepEqual(data.filings[0].items, []);
const xslSubmission = {
  ...submission,
  filings: {recent: {
    ...submission.filings.recent,
    primaryDocument: ["event.htm","xslF345X05/insider.xml","owner.htm","other.htm"],
    items: ["1.01, 5.02, 9.01","", "5.01", ""]
  }}
};
const xslResult = normalizeSubmissions(xslSubmission, "0000320193", "now");
assert.equal(xslResult.filings.length, 3);
assert.equal(xslResult.filings[0].primaryDocument, "xslF345X05/insider.xml");
assert.deepEqual(xslResult.filings[2].items, ["1.01","5.02","9.01"]);
assert.equal(xslResult.filings[0].documentUrl,
 "https://www.sec.gov/Archives/edgar/data/320193/000032019326000014/xslF345X05/insider.xml");
assert.equal(data.filings[0].filedAt, "2026-10-23");
assert.equal(data.filings[0].documentUrl,
  "https://www.sec.gov/Archives/edgar/data/320193/000032019326000014/insider.xml");
assert.throws(()=>normalizeSubmissions({...submission,cik:999},"0000320193","now"),/wrong-issuer/);
assert.throws(()=>normalizeSubmissions({...submission,filings:{recent:{form:[]}}},"0000320193","now"),/invalid-sec-data/);
assert.equal(normalizeSubmissions({
  ...submission,filings:{recent:{
    ...submission.filings.recent, primaryDocument:["../../attack","x.xml","y.htm","z.htm"]
  }}
},"0000320193","now").filings.length,2);

let calls=0;
await assert.rejects(loadSec("bad-cik",async()=>{calls++},async()=>""),/unknown-issuer/);
await assert.rejects(loadSec("0000320193",async()=>{calls++},async()=>{throw Error("identity-required")}),/identity-required/);
assert.equal(calls,0); // no network call without validated identity
const out=await loadSec("0000320193",async (url,opts)=>{
  calls++;
  assert.equal(url, "https://data.sec.gov/submissions/CIK0000320193.json");
  assert.equal(opts.method,"GET");
  assert.ok(opts.signal);
  assert.equal(opts.headers["User-Agent"],"PostApollo Finance Research analyst@testing.invalid");
  return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(submission)};
},async()=> "PostApollo Finance Research analyst@testing.invalid");
assert.equal(calls,1);
assert.equal(out.filings.length,3);
const paddedOut = await loadSec("0000320193",async()=>({
  ok:true, headers:{get:()=>null},
  text:async()=>JSON.stringify({...submission, cik:"0000320193"})
}),async()=> "PostApollo Finance Research analyst@testing.invalid");
assert.equal(paddedOut.filings.length,3);
await assert.rejects(loadSec("0000320193",async()=>({
  ok:false,headers:{get:()=>null}
}),async()=>"PostApollo Finance Research analyst@testing.invalid"),/sec-unavailable/);
console.log("FinanceW SEC EDGAR fictional submissions tests: PASS");
