import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const policy=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {compareHistoricalIntervals:compare,observedStepChangePct:step}=vm.runInNewContext(policy+"\n({compareHistoricalIntervals,observedStepChangePct})");
function snapshot(prices){
    const bars=prices.map((price,i)=>Object.freeze({date:"2026-11-"+String(i+2).padStart(2,"0"),price}));
    Object.freeze(bars);
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik:"0000320193",symbol:"AAPL.US",priceBasis:"CLOSE",
        from:"2026-11-01",to:"2026-11-20",bars,first:{...bars[0]},last:{...bars.at(-1)}});
}
function close(actual,expected){assert.ok(Number.isFinite(actual));assert.ok(Math.abs(actual-expected)<1e-9,actual+" vs "+expected);}
const s=snapshot([100,110,121,100,90,81,81]);
const equal=compare(s,0,2,0,1);
assert.equal(equal.firstReturnPct,21);
assert.equal(equal.secondReturnPct,10);
assert.equal(equal.sameStepCount,false);
close(equal.firstStepPct,10);
close(equal.secondStepPct,10);
close(equal.stepGapPoints,0);
const opposed=compare(s,0,2,3,5);
close(opposed.firstStepPct,10);
close(opposed.secondStepPct,-10);
close(opposed.stepGapPoints,-20);
assert.equal(opposed.sameStepCount,true);
assert.equal(opposed.overlaps,false);
assert.equal(JSON.stringify(compare(s,2,0,5,3)),JSON.stringify(opposed));
close(compare(s,5,6,0,1).firstStepPct,0);
assert.equal(compare(s,0,0,1,2),null);
assert.equal(compare(s,0,2,1,7),null);
assert.equal(compare({...s,source:"unknown"},0,2,1,2),null);
for(const bad of [null,{}, {observedSteps:0,from:{price:1},to:{price:2}},
    {observedSteps:1,from:{price:0},to:{price:2}},
    {observedSteps:1,from:{price:1},to:{price:Infinity}},
    {observedSteps:1.5,from:{price:1},to:{price:2}}])assert.equal(step(bad),null);
for(const token of ["GEOMETRIC CHANGE PER OBSERVED STEP","STEP CHANGE DIFFERENCE (2 MINUS 1)",
    "DIFFERENT OBSERVED STEP COUNTS","OBSERVED CLOSE TRANSITIONS ONLY // NOT CALENDAR TIME",
    "stocks.intervalComparison.firstStepPct","stocks.intervalComparison.secondStepPct",
    "RAW RETURNS // NOT TIME-NORMALIZED // NO NEW REQUEST"])assert.ok(qml.includes(token),token);
const section=qml.slice(qml.indexOf('objectName: "marketIntervalComparison"'),qml.indexOf('id: openSelectedInDay'));
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!section.includes(forbidden),forbidden);
console.log("Finance Market M33 geometric per-observed-step comparison, unequal duration, direction, no new request: PASS");
