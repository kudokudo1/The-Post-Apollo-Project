import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {captureStockReference:capture,compareStockReferences:compare,summarizeCrossStockLeadership:summary}=vm.runInNewContext(js+"\n({captureStockReference,compareStockReferences,summarizeCrossStockLeadership})");
function fixture(cik,symbol,days,prices){
    const bars=days.map((day,i)=>Object.freeze({date:"2026-11-"+String(day).padStart(2,"0"),price:prices[i]}));
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,cik,symbol,priceBasis:"CLOSE",from:"2026-11-01",to:"2026-11-20",retrievedAt:"2026-11-21T00:00:00Z",bars:Object.freeze(bars),first:{...bars[0]},last:{...bars.at(-1)}});
}
const a=fixture("0000320193","AAPL.US",[2,3,4,5,6,9,10,11],[100,120,110,100,100,120,100,100]);
const b=fixture("0000789019","MSFT.US",[2,3,4,5,6,7,9,10],[200,200,220,180,240,900,240,230]);
const comparison=compare(capture(a,a.cik,a.symbol),b,b.cik,b.symbol);
const d=summary(comparison);
const copy=x=>JSON.parse(JSON.stringify(x));
const near=(x,y)=>assert.ok(Number.isFinite(x)&&Math.abs(x-y)<1e-9,x+" vs "+y);
// Baseline tie, reference leads, tie, reference leads, current leads,
// tie, current leads. Unmatched dates never appear.
assert.deepEqual(copy(d.observations.map(x=>x.leader)),["TIE","REFERENCE","TIE","REFERENCE","CURRENT","TIE","CURRENT"]);
assert.equal(d.matched,7);
assert.equal(d.referenceDates,2);
assert.equal(d.currentDates,2);
assert.equal(d.tieDates,3);
assert.equal(d.changes,1);
assert.deepEqual(copy(d.lastChange),{date:"2026-11-06",leader:"CURRENT"});
assert.equal(d.largestReference.date,"2026-11-03");
near(d.largestReference.advantagePoints,20);
assert.equal(d.largestCurrent.date,"2026-11-06");
near(d.largestCurrent.advantagePoints,20);
assert.equal(d.latest.date,"2026-11-10");
near(d.latest.gapPoints,15);
assert.equal(d.readOnly,true);
assert.equal(d.noProviderCalls,true);
assert.equal(d.observations.some(x=>x.date==="2026-11-07"||x.date==="2026-11-11"),false);
const reverse=summary(compare(capture(b,b.cik,b.symbol),a,a.cik,a.symbol));
assert.equal(reverse.changes,1);
assert.equal(reverse.latest.leader,"REFERENCE");
near(reverse.latest.gapPoints,-15);
const flat=summary(compare(capture(fixture(a.cik,a.symbol,[2,3,4],[100,100,100]),a.cik,a.symbol),fixture(b.cik,b.symbol,[2,3,4],[200,200,200]),b.cik,b.symbol));
assert.equal(flat.tieDates,3);
assert.equal(flat.changes,0);
assert.equal(flat.lastChange,null);
assert.equal(flat.largestReference,null);
assert.equal(flat.largestCurrent,null);
const tieFlip=summary(compare(capture(fixture(a.cik,a.symbol,[2,3,4,5],[100,120,100,80]),a.cik,a.symbol),fixture(b.cik,b.symbol,[2,3,4,5],[200,200,200,200]),b.cik,b.symbol));
assert.equal(tieFlip.changes,1);
assert.equal(tieFlip.lastChange.date,"2026-11-05");
assert.equal(tieFlip.latest.leader,"CURRENT");
d.observations[1].leader="TIE";
assert.equal(summary(comparison).observations[1].leader,"REFERENCE");
for(const bad of [null,{state:"invalid"},{...comparison,readOnly:false},{...comparison,matched:1},{...comparison,pairs:[...comparison.pairs].reverse()}])
    assert.equal(summary(bad),null);
for(const token of ["RangeAnalysisPolicy.summarizeCrossStockLeadership(crossStockComparison)",
    'objectName: "marketCrossStockLeadership"',"RELATIVE LEADERSHIP // FROM FIRST COMMON CLOSE",
    "OBSERVED LEAD CHANGES","TIES INCLUDE BASE DATE // CUMULATIVE, NOT DAILY WINNERS",
    "COMMON OBSERVATIONS ONLY // NO NEW REQUEST","d.observations[selected.step]"])assert.ok(qml.includes(token),token);
const section=qml.slice(qml.indexOf('objectName: "marketCrossStockLeadership"'),qml.indexOf('objectName: "marketRangeAnalysisPanel"'));
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!section.includes(forbidden),forbidden);
console.log("Finance Market M39 cumulative common-date leadership, ties, advantage and change counts: PASS");
