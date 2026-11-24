import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {captureStockReference:capture,compareStockReferences:compare,crossStockGapChart:chart,crossStockGapPoint:point,inspectCrossStockDate:inspect,normalizedStepAtX:pick}=vm.runInNewContext(js+"\n({captureStockReference,compareStockReferences,crossStockGapChart,crossStockGapPoint,inspectCrossStockDate,normalizedStepAtX})");
function fixture(cik,symbol,days,prices){
    const bars=days.map((day,i)=>Object.freeze({date:"2026-11-"+String(day).padStart(2,"0"),price:prices[i]}));
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,cik,symbol,priceBasis:"CLOSE",from:"2026-11-01",to:"2026-11-10",retrievedAt:"2026-11-11T00:00:00Z",bars:Object.freeze(bars),first:{...bars[0]},last:{...bars.at(-1)}});
}
const a=fixture("0000320193","AAPL.US",[2,3,5,6],[100,900,120,80]);
const b=fixture("0000789019","MSFT.US",[2,4,5,6],[200,800,200,200]);
const compared=compare(capture(a,a.cik,a.symbol),b,b.cik,b.symbol);
for(const row of compared.pairs)Object.freeze(row);
Object.freeze(compared.pairs);Object.freeze(compared);
const p=chart(compared);
const copy=x=>JSON.parse(JSON.stringify(x));
const near=(x,y)=>assert.ok(Number.isFinite(x)&&Math.abs(x-y)<1e-9,x+" vs "+y);
assert.deepEqual(copy(p.points.map(x=>x.date)),["2026-11-02","2026-11-05","2026-11-06"]);
assert.equal(p.maxSteps,2);near(p.extent,20);
near(p.points[0].value,0);near(p.points[1].value,-20);near(p.points[2].value,20);
for(let i=0;i<p.points.length;i++)near(p.points[i].value,inspect(compared,i).gapPoints);
assert.equal(p.referenceSymbol,"AAPL.US");assert.equal(p.currentSymbol,"MSFT.US");
assert.equal(p.readOnly,true);assert.equal(p.noProviderCalls,true);
near(point(p,p.points[0],301,101).y,50);
near(point(p,p.points[1],301,101).y,100);
near(point(p,p.points[2],301,101).y,0);
assert.equal(point(p,p.points[1],301,101).x,150);
assert.equal(pick(p,301,150),1);assert.equal(pick(p,601,300),1);
const rev=chart(compare(capture(b,b.cik,b.symbol),a,a.cik,a.symbol));
near(rev.points[1].value,20);near(rev.points[2].value,-20);
const flat=chart(compare(capture(fixture(a.cik,a.symbol,[2,6],[100,100]),a.cik,a.symbol),fixture(b.cik,b.symbol,[2,6],[200,200]),b.cik,b.symbol));
assert.equal(flat.extent,1);assert.equal(point(flat,flat.points[1],301,101).y,50);
const rising=chart(compare(capture(fixture(a.cik,a.symbol,[2,6],[100,100]),a.cik,a.symbol),fixture(b.cik,b.symbol,[2,6],[200,202]),b.cik,b.symbol));
near(rising.points[1].value,1);near(rising.extent,1);
p.points[0].value=999;assert.equal(chart(compared).points[0].value,0);
for(const bad of [null,{state:"invalid"},{...compared,readOnly:false},{...compared,matched:1},{...compared,pairs:[...compared.pairs].reverse()}])assert.equal(chart(bad),null);
for(const bad of [{step:-1,value:0},{step:3,value:0},{step:1,value:Infinity},{step:1,value:21},null])assert.equal(point(p,bad,301,101),null);
assert.equal(point(p,{step:0,value:0},0,101),null);
assert.equal(point({...p,extent:0},{step:0,value:0},301,101),null);
for(const token of ["property bool showCrossStockGap: false","RangeAnalysisPolicy.crossStockGapChart(crossStockComparison)",
    'objectName: "marketCrossStockGapToggle"','objectName: "marketCrossStockGapChart"',
    'objectName: "marketCrossStockGapPicker"',"property int selectedStep: stocks.crossStockSelectedStep",
    "onSelectedStepChanged: requestPaint()","CLICK EITHER CHART // SHARED CURSOR",
    "POSITIVE = CURRENT LEADS // NEGATIVE = REFERENCE LEADS",
    "CUMULATIVE GAP // NOT DAILY RETURNS OR CALENDAR SPACING"])assert.ok(qml.includes(token),token);
const section=qml.slice(qml.indexOf('objectName: "marketCrossStockGapToggle"'),qml.indexOf('objectName: "marketRangeAnalysisPanel"'));
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!section.includes(forbidden),forbidden);
console.log("Finance Market M40 signed common-date gap, symmetric zero scale, shared cursor and no extra request: PASS");
