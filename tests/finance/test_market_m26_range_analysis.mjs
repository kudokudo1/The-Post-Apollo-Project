#!/usr/bin/env node
// Market M26: deterministic close-only RANGE stats, no API/IO/worker mutations.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const policy = readFileSync(new URL(
    "../../widgets/FinanceStockRangeAnalysisPolicy.js", import.meta.url
), "utf8");
const qml = readFileSync(new URL(
    "../../widgets/FinanceStockHistoryPane.qml", import.meta.url
), "utf8");
const api = vm.runInNewContext(policy + "\n({summarizeRange})");
function bar(date, price) { return {date,price}; }
const rows = [
    bar("2026-11-02",100),
    bar("2026-11-03",110),
    bar("2026-11-04",105),
    bar("2026-11-05",120),
    bar("2026-11-06",90),
    bar("2026-11-09",90)
];
function fixture(bars=rows) {
    return {
        schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik:"0000320193",symbol:"AAPL.US",
        priceBasis:"ADJUSTED CLOSE",from:"2026-11-01",to:"2026-11-10",
        bars,first:bars.length?{...bars[0]}:null,
        last:bars.length?{...bars[bars.length-1]}:null,
        delivery:{via:"DIRECT",state:"DIRECT"}
    };
}
function comparable(x) { return JSON.parse(JSON.stringify(x)); }
const frozen = fixture();
for (const item of frozen.bars) Object.freeze(item);
Object.freeze(frozen.bars);
Object.freeze(frozen.first);
Object.freeze(frozen.last);
Object.freeze(frozen);
const actual = comparable(api.summarizeRange(frozen));
assert.deepEqual(actual, {
    sessions:6, priceBasis:"ADJUSTED CLOSE",
    high:{date:"2026-11-05",price:120},
    low:{date:"2026-11-06",price:90},
    maxDrawdownPct:25,
    peak:{date:"2026-11-05",price:120},
    trough:{date:"2026-11-06",price:90},
    upSteps:2, downSteps:2, flatSteps:1,
    largestUpPct:14.29, largestDownPct:-25,
    source:"loaded-eodhd-range-only",
    noProviderCalls:true,readOnly:true
});
assert.notEqual(actual.high, frozen.bars[3]);
actual.high.price = 1;
assert.equal(frozen.bars[3].price, 120);

const single = comparable(api.summarizeRange(fixture([bar("2026-11-03",101)])));
assert.equal(single.sessions,1);
assert.deepEqual([single.upSteps,single.downSteps,single.flatSteps], [0,0,0]);
assert.equal(single.maxDrawdownPct,0);
assert.equal(single.largestUpPct,null);
assert.equal(single.largestDownPct,null);

const rising = api.summarizeRange(fixture([
    bar("2026-11-02",2),bar("2026-11-03",3),bar("2026-11-04",4)
]));
assert.equal(rising.maxDrawdownPct,0);
assert.equal(rising.upSteps,2);
assert.equal(rising.downSteps,0);
assert.equal(rising.largestDownPct,null);
const falling = api.summarizeRange(fixture([
    bar("2026-11-02",4),bar("2026-11-03",3),bar("2026-11-04",2)
]));
assert.equal(falling.maxDrawdownPct,50);
assert.equal(falling.upSteps,0);
assert.equal(falling.downSteps,2);
assert.equal(falling.largestUpPct,null);
const flat = api.summarizeRange(fixture([
    bar("2026-11-02",7),bar("2026-11-03",7)
]));
assert.equal(flat.maxDrawdownPct,0);
assert.equal(flat.flatSteps,1);

// Peak-to-trough is chronological, not simply global high vs global low.
// Early low before a later high cannot become a drawdown from that high.
const ordering = api.summarizeRange(fixture([
    bar("2026-11-02",50),bar("2026-11-03",100),bar("2026-11-04",80)
]));
assert.equal(ordering.maxDrawdownPct,20);
assert.equal(ordering.peak.date,"2026-11-03");
assert.equal(ordering.trough.date,"2026-11-04");

for (const invalid of [
    fixture([]),
    {...fixture(),source:"alpha-vantage"},
    {...fixture(),readOnly:false},
    {...fixture(),schemaVersion:2},
    {...fixture(),priceBasis:"MIXED"},
    {...fixture(),from:"2026-11-32"},
    {...fixture(),to:"2026-11-01"},
    {...fixture(),bars:rows.slice(0,3).concat(rows[2]),last:{...rows[2]}},
    {...fixture(),bars:[rows[2],rows[1]],first:rows[2],last:rows[1]},
    fixture([bar("2026-11-02",NaN)]),
    fixture([bar("2026-11-02",Infinity)]),
    fixture([bar("2026-11-02",-1)]),
    fixture([bar("2026-11-02",10000000)]),
    fixture([bar("2026-11-22",8)]),
    fixture([bar("2026-02-30",8)]),
    {...fixture(),first:{date:"2026-11-02",price:999}},
    {...fixture(),last:{date:"2026-11-09",price:999}},
    fixture(Array.from({length:133},(_,i)=>bar("2026-11-02",100+i)))
]) assert.equal(api.summarizeRange(invalid), null,JSON.stringify(invalid).slice(0,100));

for(const expected of [
    'import "FinanceStockRangeAnalysisPolicy.js" as RangeAnalysisPolicy',
    'readonly property var rangeAnalysis:',
    "RangeAnalysisPolicy.summarizeRange(snapshot)",
    'objectName: "marketRangeAnalysisPanel"',
    'objectName: "marketRangeAnalysisSummary"',
    'MAX PEAK-TO-TROUGH DROP',
    'SESSION STEPS // UP',
    'NOT INTRADAY EXTREMES OR A VOLATILITY FORECAST',
    'NO NEW REQUEST'
]) assert.ok(qml.includes(expected),expected);
const part = qml.slice(qml.indexOf('objectName: "marketRangeAnalysisPanel"'),
                       qml.indexOf('id: backToRange'));
assert.ok(!part.includes("Process {"));
assert.ok(!part.includes("Qt.openUrlExternally"));
assert.ok(!part.includes("stockFeed.refresh()"));
assert.ok(!part.includes("market_shared_quota"));
assert.ok(!part.includes("fetch("));
assert.ok(!part.includes("writeFile("));
for(const forbidden of [
    "fetch(", "XMLHttpRequest", "Qt.openUrlExternally", "subprocess",
    "Process {", "reserve(", "sqlite", "setInterval(", "Math.random("
])assert.ok(!policy.includes(forbidden),forbidden);
console.log("Finance Market M26 loaded-range close-only stats, chronological drawdown, no IO or stale source: PASS");
