#!/usr/bin/env node
// Finance Market M30: fictional two-point in-memory comparisons. No provider IO.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {comparePinnedRangeSessions:compare}=vm.runInNewContext(
    js+"\n({comparePinnedRangeSessions})");
const value=x=>JSON.parse(JSON.stringify(x));
const prices=[100,110,105,120,90,90];
const bars=prices.map((price,i)=>({
    date:"2026-11-"+String(i+2).padStart(2,"0"),price
}));
const fixture=(rows=bars)=>({
    schemaVersion:1,source:"eodhd-eod",readOnly:true,
    cik:"0000320193",symbol:"AAPL.US",
    priceBasis:"ADJUSTED CLOSE",from:"2026-11-01",to:"2026-11-10",
    bars:rows,first:rows[0]?{...rows[0]}:null,
    last:rows.length?{...rows[rows.length-1]}:null
});
const frozen=fixture();
for(const bar of frozen.bars)Object.freeze(bar);
Object.freeze(frozen.bars);
Object.freeze(frozen.first);
Object.freeze(frozen.last);
Object.freeze(frozen);

const forward=value(compare(frozen,1,4));
assert.deepEqual(forward,{
    start:{index:1,date:"2026-11-03",price:110},
    end:{index:4,date:"2026-11-06",price:90},
    deltaPrice:-20,deltaPct:-18.18,
    observedSteps:3,order:"FORWARD",priceBasis:"ADJUSTED CLOSE",
    source:"loaded-eodhd-range-only",readOnly:true,noProviderCalls:true
});
forward.start.price=0;
assert.equal(frozen.bars[1].price,110);
const backward=value(compare(frozen,4,0));
assert.deepEqual(backward,{
    start:{index:4,date:"2026-11-06",price:90},
    end:{index:0,date:"2026-11-02",price:100},
    deltaPrice:10,deltaPct:11.11,
    observedSteps:4,order:"BACKWARD",priceBasis:"ADJUSTED CLOSE",
    source:"loaded-eodhd-range-only",readOnly:true,noProviderCalls:true
});
const same=compare(frozen,3,3);
assert.equal(same.deltaPrice,0);
assert.equal(same.deltaPct,0);
assert.equal(same.observedSteps,0);
assert.equal(same.order,"SAME");
const flat=compare(frozen,4,5);
assert.equal(flat.deltaPrice,0);
assert.equal(flat.deltaPct,0);
assert.equal(flat.observedSteps,1);
assert.equal(flat.order,"FORWARD");
const one=compare(fixture([{date:"2026-11-02",price:23}]),0,0);
assert.equal(one.order,"SAME");
assert.equal(one.observedSteps,0);
assert.equal(one.deltaPct,0);

for(const invalid of [-1,6,1.5,NaN,Infinity,"1",null,undefined]) {
    assert.equal(compare(frozen,invalid,0),null);
    assert.equal(compare(frozen,0,invalid),null);
}
for(const bad of [
    null,{},fixture([]),
    {...fixture(),readOnly:false},
    {...fixture(),schemaVersion:9},
    {...fixture(),source:"alpha-vantage"},
    {...fixture(),priceBasis:"MIXED"},
    {...fixture(),first:{date:"2026-11-02",price:400}},
    {...fixture(),last:{date:"2026-11-07",price:400}},
    fixture([bars[2],bars[1]]),
    fixture([{date:"2026-11-02",price:0}]),
    fixture([{date:"2026-11-02",price:NaN}]),
    fixture([{date:"2026-11-02",price:Infinity}]),
    fixture(Array.from({length:133},()=>({date:"2026-11-02",price:1})))
])assert.equal(compare(bad,0,1),null);

for(const expected of [
    "property int pinnedPointIndex: -1",
    "property var pinnedSnapshot: null",
    "pinnedSnapshot === snapshot",
    "readonly property bool pinValid:",
    "readonly property var pinnedPairComparison:",
    "RangeAnalysisPolicy.comparePinnedRangeSessions(",
    "selectedPointIndex !== pinnedPointIndex",
    "function clearPinnedComparison()",
    "function pinCurrentPoint()",
    "onSnapshotChanged: clearPinnedComparison()",
    "onRangeAnalysisChanged:",
    "onPriceBarsChanged:",
    "onDayModeChanged:",
    "onPinnedPointIndexChanged: priceCanvas.requestPaint()",
    "onPinValidChanged: priceCanvas.requestPaint()",
    'objectName: "marketPinnedSessionActions"',
    'objectName: "marketPinSessionButton"',
    'objectName: "marketClearPinButton"',
    'objectName: "marketPinnedSessionHint"',
    'objectName: "marketPinnedPairComparisonPanel"',
    'objectName: "marketPinnedPairComparisonText"',
    'label: "PIN AS A"',
    'label: "CLEAR PIN A"',
    "stocks.pinnedSnapshot = null",
    "ctx.strokeStyle=\"#F2D24D\"",
    "OBSERVED SESSION STEPS",
    "LOADED CLOSES ONLY // NO NEW REQUEST",
    'id: openSelectedInDay'
].filter(x=>x!=="stocks.pinnedSnapshot = null")) {
    assert.ok(qml.includes(expected),expected);
}
const controls=qml.slice(
    qml.indexOf('objectName: "marketPinnedSessionActions"'),
    qml.indexOf('id: openSelectedInDay'));
assert.ok(controls.length>200);
for(const forbidden of ["Process {","fetch(","reserve(","stockFeed.refresh(","writeFile(","XMLHttpRequest"]) {
    assert.ok(!controls.includes(forbidden),forbidden);
    assert.ok(!js.includes(forbidden),forbidden);
}
assert.match(qml,/onPriceBarsChanged:\s*{[^}]*clearPinnedComparison\(\)/);
assert.match(qml,/onDayModeChanged:\s*{[^}]*clearPinnedComparison\(\)/);
assert.match(qml,/onRangeAnalysisChanged:\s*{\s*if \(rangeAnalysis === null\) clearPinnedComparison\(\)/);
console.log("Finance Market M30 pinned A/B loaded-session comparison, backward/forward and stale pin resets: PASS");
