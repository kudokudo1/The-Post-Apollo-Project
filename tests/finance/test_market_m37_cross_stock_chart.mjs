import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {captureStockReference:capture,compareStockReferences:compare,crossStockNormalizedChart:chart,normalizedChartPoint:point}=vm.runInNewContext(js+"\n({captureStockReference,compareStockReferences,crossStockNormalizedChart,normalizedChartPoint})");
function fixture(cik,symbol,days,prices){
    const bars=days.map((day,i)=>Object.freeze({date:"2026-11-"+String(day).padStart(2,"0"),price:prices[i]}));
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,cik,symbol,priceBasis:"CLOSE",from:"2026-11-01",to:"2026-11-10",retrievedAt:"2026-11-11T00:00:00Z",bars:Object.freeze(bars),first:{...bars[0]},last:{...bars.at(-1)}});
}
const a=fixture("0000320193","AAPL.US",[2,3,5,6],[100,150,110,120]);
const b=fixture("0000789019","MSFT.US",[2,4,5,6],[200,400,180,160]);
const ref=capture(a,a.cik,a.symbol);
const compared=compare(ref,b,b.cik,b.symbol);
const p=chart(compared);
const copy=x=>JSON.parse(JSON.stringify(x));
const near=(x,y)=>assert.ok(Math.abs(x-y)<1e-9,x+" vs "+y);
assert.deepEqual(copy(p.first.map(x=>x.date)),["2026-11-02","2026-11-05","2026-11-06"]);
assert.deepEqual(copy(p.second.map(x=>x.date)),copy(p.first.map(x=>x.date)));
assert.deepEqual(copy(p.first.map(x=>x.step)),[0,1,2]);
assert.equal(p.first[0].value,100);
assert.equal(p.second[0].value,100);
near(p.first[1].value,110);
near(p.second[1].value,90);
near(p.first[2].value,120);
near(p.second[2].value,80);
near(p.high,120);near(p.low,80);
assert.equal(p.maxSteps,2);
assert.equal(p.referenceSymbol,"AAPL.US");
assert.equal(p.currentSymbol,"MSFT.US");
assert.equal(p.source,"loaded-eodhd-common-dates-only");
assert.equal(p.readOnly,true);
assert.equal(p.noProviderCalls,true);
assert.equal(point(p,p.first[1],301,101).x,150);
assert.equal(point(p,p.second[1],301,101).x,150);
near(point(p,p.first[2],301,101).y,0);
near(point(p,p.second[2],301,101).y,100);
const flat=chart(compare(capture(fixture(a.cik,a.symbol,[2,6],[100,100]),a.cik,a.symbol),fixture(b.cik,b.symbol,[2,6],[200,200]),b.cik,b.symbol));
assert.equal(flat.high,100);assert.equal(flat.low,100);
assert.equal(point(flat,flat.first[1],301,101).y,50);
p.first[0].value=1;
assert.equal(compared.pairs[0].referencePrice,100);
assert.equal(chart(compared).first[0].value,100);
for(const bad of [null,{state:"invalid"},{...compared,state:"basis-mismatch"},
    {...compared,state:"window-mismatch"},{...compared,readOnly:false},
    {...compared,noProviderCalls:false},{...compared,matched:2},
    {...compared,referenceSymbol:compared.currentSymbol},
    {...compared,from:"2026-11-01"},
    {...compared,pairs:[...compared.pairs].reverse()},
    {...compared,pairs:[{...compared.pairs[0],referencePrice:0},...compared.pairs.slice(1)]},
    {...compared,pairs:[{...compared.pairs[0],currentPrice:Infinity},...compared.pairs.slice(1)]},
    {...compared,pairs:[{...compared.pairs[0],date:"invalid"},...compared.pairs.slice(1)]}])
    assert.equal(chart(bad),null);
for(const token of ["RangeAnalysisPolicy.crossStockNormalizedChart(crossStockComparison)",
    'objectName: "marketCrossStockNormalizedChart"',"property var plot: stocks.crossStockChart",
    "FIRST COMMON CLOSE = 100","EQUAL SPACING BY COMMON OBSERVATION // NOT CALENDAR TIME",
    "UNMATCHED CLOSES EXCLUDED // NO NEW REQUEST"])assert.ok(qml.includes(token),token);
const section=qml.slice(qml.indexOf('objectName: "marketCrossStockNormalizedChart"'),qml.indexOf('objectName: "marketRangeAnalysisPanel"'));
for(const token of ['onPlotChanged: requestPaint()','onWidthChanged: requestPaint()','onHeightChanged: requestPaint()','draw(chart.first,"#55CFCA")','draw(chart.second,"#C74EC7")'])assert.ok(section.includes(token),token);
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!section.includes(forbidden),forbidden);
console.log("Finance Market M37 common-date base-100 stock paths, shared axes, invalid/flat data and no new request: PASS");
