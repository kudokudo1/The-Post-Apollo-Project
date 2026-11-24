import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {captureStockReference:capture,compareStockReferences:compare,crossStockNormalizedChart:chart,normalizedChartPoint:point,normalizedStepAtX:pick,inspectCrossStockDate:inspect}=vm.runInNewContext(js+"\n({captureStockReference,compareStockReferences,crossStockNormalizedChart,normalizedChartPoint,normalizedStepAtX,inspectCrossStockDate})");
function fixture(cik,symbol,days,prices){
    const bars=days.map((day,i)=>Object.freeze({date:"2026-11-"+String(day).padStart(2,"0"),price:prices[i]}));
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,cik,symbol,priceBasis:"ADJUSTED CLOSE",from:"2026-11-01",to:"2026-11-10",retrievedAt:"2026-11-11T00:00:00Z",bars:Object.freeze(bars),first:{...bars[0]},last:{...bars.at(-1)}});
}
const a=fixture("0000320193","AAPL.US",[2,3,5,6],[100,150,110,120]);
const b=fixture("0000789019","MSFT.US",[2,4,5,6],[200,400,180,160]);
const d=compare(capture(a,a.cik,a.symbol),b,b.cik,b.symbol);
const p=chart(d);
for(const row of d.pairs)Object.freeze(row);
Object.freeze(d.pairs);Object.freeze(d);
const near=(x,y)=>assert.ok(Number.isFinite(x)&&Math.abs(x-y)<1e-9,x+" vs "+y);
const zero=inspect(d,0);
assert.equal(zero.date,"2026-11-02");
assert.equal(zero.reference.price,100);
assert.equal(zero.current.price,200);
assert.equal(zero.gapPoints,0);
assert.equal(zero.reference.value,100);
assert.equal(zero.current.value,100);
assert.equal(pick(p,301,150),1);
assert.equal(pick(p,601,300),1);
assert.equal(pick(p,301,300),2);
assert.equal(pick(p,301,-1),-1);
const mid=inspect(d,pick(p,301,150));
assert.equal(mid.date,"2026-11-05");
assert.equal(mid.reference.date,mid.current.date);
assert.equal(mid.reference.symbol,"AAPL.US");
assert.equal(mid.current.symbol,"MSFT.US");
assert.equal(mid.reference.price,110);
assert.equal(mid.current.price,180);
near(mid.reference.value,110);near(mid.current.value,90);
near(mid.reference.changePct,10);near(mid.current.changePct,-10);
near(mid.gapPoints,-20);
assert.equal(mid.priceBasis,"ADJUSTED CLOSE");
assert.equal(mid.from,"2026-11-02");
assert.equal(mid.readOnly,true);
assert.equal(mid.noProviderCalls,true);
assert.equal(point(p,mid.reference,301,101).x,150);
assert.equal(point(p,mid.current,301,101).x,150);
near(inspect(d,2).gapPoints,-40);
mid.reference.price=1;
assert.equal(inspect(d,1).reference.price,110);
assert.equal(d.pairs[1].referencePrice,110);
const reversed=compare(capture(b,b.cik,b.symbol),a,a.cik,a.symbol);
near(inspect(reversed,1).gapPoints,20);
for(const step of [-1,3,1.5,NaN,Infinity,"1",null])assert.equal(inspect(d,step),null);
for(const bad of [null,{state:"invalid"},{...d,state:"basis-mismatch"},{...d,readOnly:false},
    {...d,noProviderCalls:false},{...d,matched:2},{...d,pairs:[...d.pairs].reverse()},
    {...d,pairs:[d.pairs[0],{...d.pairs[1],currentPrice:0},d.pairs[2]]}])
    assert.equal(inspect(bad,1),null);
for(const token of ["onCrossStockChartChanged: crossStockSelectedStep = -1",
    "RangeAnalysisPolicy.inspectCrossStockDate(crossStockComparison,",
    "onDateDetailChanged: requestPaint()", 'objectName: "marketCrossStockDatePicker"',
    'objectName: "marketCrossStockDateDetail"', "step === stocks.crossStockSelectedStep ? -1 : step",
    "mark(selected.reference", "mark(selected.current", "COMMON CLOSE DATE ",
    "CURRENT MINUS REF // ", "LOADED CLOSES ONLY // CLICK AGAIN TO CLEAR"])
    assert.ok(qml.includes(token),token);
const section=qml.slice(qml.indexOf('objectName: "marketCrossStockNormalizedChart"'),qml.indexOf('objectName: "marketRangeAnalysisPanel"'));
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!section.includes(forbidden),forbidden);
console.log("Finance Market M38 common-date cursor, actual closes, relative changes, reset and no new request: PASS");
