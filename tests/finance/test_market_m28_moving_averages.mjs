#!/usr/bin/env node
// FinanceW Market M28: fixed, local trailing 5/20 observed-session averages.
// Fictional prices only. Never contacts EODHD/Alpha or a live SQLite ledger.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const policy=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const api=vm.runInNewContext(policy+"\n({summarizeRange,movingAverageSeries})");
const bar=(date,price)=>({date,price});
function snapshot(bars) {
    return {
        schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik:"0000320193",symbol:"AAPL.US",
        priceBasis:"CLOSE",from:"2026-11-01",to:"2026-11-25",
        bars,first:bars[0]?{...bars[0]}:null,
        last:bars.length?{...bars[bars.length-1]}:null
    };
}
function rows(prices) {
    return prices.map((price,i)=>bar("2026-11-"+String(i+1).padStart(2,"0"),price));
}
const prices=[100,110,105,120,90,90];
const frozen=snapshot(rows(prices));
for(const item of frozen.bars)Object.freeze(item);
Object.freeze(frozen.bars);
Object.freeze(frozen.first);
Object.freeze(frozen.last);
Object.freeze(frozen);
const output=JSON.parse(JSON.stringify(api.movingAverageSeries(frozen)));
assert.equal(output.sma5.length,2);
assert.deepEqual(output.sma5.map(x=>x.index),[4,5]);
assert.deepEqual(output.sma5.map(x=>x.price),[105,103]);
assert.deepEqual(output.sma5.map(x=>x.date),["2026-11-05","2026-11-06"]);
assert.deepEqual(output.sma20,[]);
assert.equal(output.latest5,103);
assert.equal(output.latest20,null);
assert.equal(output.sessions,6);
assert.equal(output.priceBasis,"CLOSE");
assert.equal(output.source,"loaded-eodhd-range-only");
assert.equal(output.readOnly,true);
assert.equal(output.noProviderCalls,true);
output.sma5[0].price=1;
assert.equal(frozen.bars[4].price,90);

const twenty=api.movingAverageSeries(snapshot(rows(
    Array.from({length:20},(_,i)=>i+1))));
assert.equal(twenty.sma5.length,16);
assert.equal(twenty.sma20.length,1);
assert.equal(twenty.sma20[0].index,19);
assert.equal(twenty.sma20[0].date,"2026-11-20");
assert.equal(twenty.latest20,10.5);
assert.equal(twenty.latest5,18);
const allFlat=api.movingAverageSeries(snapshot(rows(
    Array.from({length:25},()=>7))));
assert.equal(allFlat.sma5.length,21);
assert.equal(allFlat.sma20.length,6);
assert.equal(allFlat.latest5,7);
assert.equal(allFlat.latest20,7);
assert.equal(allFlat.sma5[0].index,4);
assert.equal(allFlat.sma20[0].index,19);
const four=api.movingAverageSeries(snapshot(rows([1,2,3,4])));
assert.deepEqual(JSON.parse(JSON.stringify(four.sma5)),[]);
assert.deepEqual(JSON.parse(JSON.stringify(four.sma20)),[]);
assert.equal(four.latest5,null);
assert.equal(four.latest20,null);
const one=api.movingAverageSeries(snapshot(rows([1])));
assert.equal(one.latest5,null);
assert.equal(one.latest20,null);

for(const invalid of [
    snapshot([]),
    {...snapshot(rows([1,2,3,4,5])),schemaVersion:2},
    {...snapshot(rows([1,2,3,4,5])),readOnly:false},
    {...snapshot(rows([1,2,3,4,5])),source:"alpha-vantage"},
    {...snapshot(rows([1,2,3,4,5])),priceBasis:"MIXED"},
    snapshot(rows([1,2,NaN,4,5])),
    snapshot(rows([1,2,Infinity,4,5])),
    snapshot(rows([1,2,-3,4,5])),
    snapshot(rows([1,2,0,4,5])),
    {...snapshot(rows([1,2,3,4,5])),first:{date:"2026-11-01",price:99}},
    {...snapshot(rows([1,2,3,4,5])),bars:rows([1,2,3,4,5]).reverse()},
    snapshot(Array.from({length:133},()=>bar("2026-11-01",100)))
])assert.equal(api.movingAverageSeries(invalid),null);

for(const required of [
    "readonly property var averageOverlay:",
    "priceBars.length >= 5 && rangeAnalysis !== null",
    "RangeAnalysisPolicy.movingAverageSeries(snapshot)",
    "onAverageOverlayChanged: priceCanvas.requestPaint()",
    "onShowAveragesChanged: priceCanvas.requestPaint()",
    'objectName: "marketMovingAverageToggle"',
    'label: stocks.showAverages ? "HIDE 5/20 SMA" : "SHOW 5/20 SMA"',
    "onLeftClicked: stocks.showAverages = !stocks.showAverages",
    'objectName: "marketMovingAverageSummary"',
    'drawAverage(moving.sma5,"#ED981A")',
    'drawAverage(moving.sma20,"#D8CAFF")',
    "NEED 20 LOADED SESSIONS",
    "NOT A LIVE QUOTE OR TRADE SIGNAL"
])assert.ok(qml.includes(required),required);
const section=qml.slice(qml.indexOf('id: averageToggle'),
                        qml.indexOf('objectName: "marketMovingAverageSummary"'));
assert.ok(!section.includes("Process {"));
assert.ok(!section.includes("stockFeed.refresh("));
assert.ok(!section.includes("market_shared_quota"));
assert.ok(!section.includes("fetch("));
assert.ok(!section.includes("writeFile("));
for(const forbidden of [
    "fetch(", "XMLHttpRequest","reserve(","subprocess",
    "Qt.openUrlExternally","Math.random(","setInterval(","writeFile(","sqlite3"
])assert.ok(!policy.includes(forbidden),forbidden);
console.log("Finance Market M28 local trailing SMA 5/20, incomplete windows, no network or stale data: PASS");
