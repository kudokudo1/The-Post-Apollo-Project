#!/usr/bin/env node
// M29: fictional only. Observe the *loaded* SMA5/SMA20 sides, not trade signals.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const policy=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const api=vm.runInNewContext(policy+"\n({movingAverageRelationship})");
const roundtrip=value=>JSON.parse(JSON.stringify(value));

function fixture(values) {
    const bars=values.map((price,i)=>({
        date:new Date(Date.UTC(2026,8,1+i)).toISOString().slice(0,10),
        price
    }));
    return {
        schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik:"0000320193",symbol:"AAPL.US",
        priceBasis:"CLOSE",from:"2026-09-01",to:"2026-12-31",
        bars,first:bars[0]?{...bars[0]}:null,
        last:bars.length?{...bars[bars.length-1]}:null
    };
}

const one=api.movingAverageRelationship(fixture([100]));
assert.deepEqual(roundtrip(one),{
    state:"insufficient",sessions:1,requiredSessions:20,
    source:"loaded-eodhd-range-only",readOnly:true,noProviderCalls:true
});
const nineteen=api.movingAverageRelationship(fixture(Array(19).fill(100)));
assert.equal(nineteen.state,"insufficient");
assert.equal(nineteen.sessions,19);
assert.equal(nineteen.requiredSessions,20);

const equal=api.movingAverageRelationship(fixture(Array(20).fill(100)));
assert.equal(equal.state,"ready");
assert.equal(equal.latestSide,"EQUAL");
assert.equal(equal.spreadPrice,0);
assert.equal(equal.spreadPct,0);
assert.equal(equal.sideChanges,0);
assert.equal(equal.movedAbove,0);
assert.equal(equal.movedBelow,0);
assert.equal(equal.lastChange,null);
assert.equal(equal.latestDate,"2026-09-20");

const above=api.movingAverageRelationship(fixture([
    ...Array(19).fill(100),120
]));
assert.equal(above.latestSide,"ABOVE");
assert.equal(above.sideChanges,0); // first defined side is not a flip
assert.equal(above.spreadPrice,3);
assert.equal(above.spreadPct,2.97);
const below=api.movingAverageRelationship(fixture([
    ...Array(19).fill(100),80
]));
assert.equal(below.latestSide,"BELOW");
assert.equal(below.sideChanges,0);
assert.equal(below.spreadPrice,-3);
assert.equal(below.spreadPct,-3.03);

// Reconstructed strictly from the same fixed-length test bars. No external
// data: after initial equality, SMA5 goes above, then below, then above.
const fifty=fixture([
    ...Array(20).fill(100),
    ...Array(10).fill(200),
    ...Array(10).fill(50),
    ...Array(10).fill(200)
]);
for (const bar of fifty.bars)Object.freeze(bar);
Object.freeze(fifty.bars);
Object.freeze(fifty.first);
Object.freeze(fifty.last);
Object.freeze(fifty);
const result=roundtrip(api.movingAverageRelationship(fifty));
assert.equal(result.state,"ready");
assert.equal(result.sessions,50);
assert.equal(result.latestSide,"ABOVE");
assert.equal(result.sideChanges,2);
assert.equal(result.movedAbove,1);
assert.equal(result.movedBelow,1);
assert.deepEqual(result.lastChange,{
    date:fifty.bars[42].date,index:42,direction:"ABOVE"
});
assert.equal(result.source,"loaded-eodhd-range-only");
assert.equal(result.readOnly,true);
assert.equal(result.noProviderCalls,true);
assert.equal(result.priceBasis,"CLOSE");
assert.ok(Number.isFinite(result.spreadPct));
result.lastChange.direction="BELOW";
assert.equal(fifty.bars[42].price,200);
assert.equal(api.movingAverageRelationship(fifty).lastChange.direction,"ABOVE");

for(const bad of [
    null,{},fixture([]),
    {...fifty,source:"unknown-source"},
    {...fifty,readOnly:false},
    {...fifty,priceBasis:"MIXED"},
    {...fifty,first:{date:fifty.first.date,price:1}},
    {...fifty,bars:fifty.bars.slice().reverse()},
    fixture([100,100,NaN,...Array(20).fill(100)]),
    fixture(Array(133).fill(1))
])assert.equal(api.movingAverageRelationship(bad),null);

for(const required of [
    "readonly property var averageRelationship:",
    "averageOverlay !== null",
    "RangeAnalysisPolicy.movingAverageRelationship(snapshot)",
    'objectName: "marketMovingAverageRelationship"',
    "SMA 5 VS SMA 20 // HISTORICAL RELATIONSHIP",
    "SMA 5 VS SMA 20 // INSUFFICIENT LOADED HISTORY",
    "OBSERVED SIDE CHANGES ",
    "LAST OBSERVED SIDE CHANGE ",
    "NEED 20 OBSERVED SESSIONS",
    "NOT A LIVE QUOTE OR TRADE SIGNAL"
])assert.ok(qml.includes(required),required);
const section=qml.slice(
    qml.indexOf('objectName: "marketMovingAverageRelationship"'),
    qml.indexOf('text: "CYAN = DAILY CLOSES // CLICK A DATA POINT'));
for(const forbidden of [
    "Process {","stockFeed.refresh(","fetch(","reserve(","writeFile(","XMLHttpRequest"
])assert.ok(!section.includes(forbidden),forbidden);
for(const forbidden of [
    "fetch(","reserve(","Process {","writeFile(","sqlite3","setInterval(","Math.random("
])assert.ok(!policy.includes(forbidden),forbidden);
console.log("Finance Market M29 historical SMA5/20 relationship, equality/side flips, no API or stale source: PASS");
