import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {normalizedIntervalChart:chart,normalizedChartPoint:point}=vm.runInNewContext(js+"\n({normalizedIntervalChart,normalizedChartPoint})");
const copy=x=>JSON.parse(JSON.stringify(x));
function fixture(prices){
    const bars=prices.map((price,i)=>Object.freeze({date:"2026-11-"+String(i+2).padStart(2,"0"),price}));
    Object.freeze(bars);
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik:"0000320193",symbol:"AAPL.US",priceBasis:"CLOSE",
        from:"2026-11-01",to:"2026-11-20",bars,first:{...bars[0]},last:{...bars.at(-1)}});
}
const s=fixture([100,110,121,200,180,160,140]);
const p=chart(s,0,2,3,6);
assert.equal(p.first[0].value,100);
assert.equal(p.second[0].value,100);
assert.deepEqual(copy(p.first.map(x=>x.step)),[0,1,2]);
assert.deepEqual(copy(p.second.map(x=>x.step)),[0,1,2,3]);
assert.equal(p.first[2].value,121);
assert.equal(p.second[3].value,70);
assert.equal(p.first[0].date,"2026-11-02");
assert.equal(p.second[0].date,"2026-11-05");
assert.equal(p.maxSteps,3);
assert.equal(p.low,70);
assert.equal(p.high,121);
assert.equal(p.priceBasis,"CLOSE");
assert.equal(p.readOnly,true);
assert.equal(p.noProviderCalls,true);
assert.deepEqual(copy(chart(s,2,0,6,3)),copy(p));
assert.deepEqual(copy(point(p,p.first[0],301,101)),copy(point(p,p.second[0],301,101)));
assert.equal(point(p,p.first[2],301,101).x,200);
assert.equal(point(p,p.first[2],301,101).y,0);
assert.equal(point(p,p.second[3],301,101).x,300);
assert.equal(point(p,p.second[3],301,101).y,100);
assert.equal(point(p,p.first[1],301,101).x,point(p,p.second[1],301,101).x);
assert.equal(point(p,p.first[2],601,201).x,400);
const flat=chart(fixture([100,100,200,200]),0,1,2,3);
assert.equal(flat.low,100);
assert.equal(flat.high,100);
assert.equal(point(flat,flat.first[0],301,101).y,50);
assert.equal(point(flat,flat.second[1],301,101).y,50);
const overlap=chart(s,0,3,2,4);
assert.equal(overlap.second.length,3);
assert.equal(overlap.second[0].value,100);
const changed=chart(s,0,2,3,6);
changed.first[0].value=1;
assert.equal(s.bars[0].price,100);
assert.equal(chart(s,0,2,3,6).first[0].value,100);
for(const bad of [-1,7,1.5,NaN,Infinity,"1",null])
    assert.equal(chart(s,0,2,3,bad),null);
assert.equal(chart(s,0,0,3,6),null);
assert.equal(chart(s,0,2,3,3),null);
assert.equal(chart({...s,source:"unknown"},0,2,3,6),null);
assert.equal(chart({...s,readOnly:false},0,2,3,6),null);
assert.equal(point(p,{step:4,value:100},301,101),null);
assert.equal(point(p,{step:1,value:NaN},301,101),null);
assert.equal(point(p,p.first[0],0,101),null);
assert.equal(point(p,p.first[0],301,Infinity),null);
for(const token of [
    "readonly property var normalizedComparison: intervalComparison !== null",
    "RangeAnalysisPolicy.normalizedIntervalChart(snapshot, savedIntervalA,",
    'objectName: "marketNormalizedIntervalChart"',
    "property var plot: stocks.normalizedComparison",
    "onPlotChanged: requestPaint()",
    "onWidthChanged: requestPaint()",
    "onHeightChanged: requestPaint()",
    'draw(chart.first,"#55CFCA")',
    'draw(chart.second,"#C74EC7")',
    "NORMALIZED INTERVALS // START = 100",
    "EACH LINE STOPS AT ITS LAST OBSERVED CLOSE",
    "OBSERVED STEPS // 0 TO ",
    "NOT CALENDAR TIME // NO NEW REQUEST"
]) assert.ok(qml.includes(token),token);
const part=qml.slice(qml.indexOf('text: "NORMALIZED INTERVALS // START = 100"'),qml.indexOf("id: openSelectedInDay"));
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!part.includes(forbidden),forbidden);
console.log("Finance Market M34 base-100 interval paths, shared step geometry, flat/unequal/reversed selection, no extra observations: PASS");
