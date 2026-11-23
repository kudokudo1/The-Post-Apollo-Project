#!/usr/bin/env node
// FinanceW Market M31: fictional in-memory interval observations only.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const policy = readFileSync(new URL(
    "../../widgets/FinanceStockRangeAnalysisPolicy.js", import.meta.url
), "utf8");
const qml = readFileSync(new URL(
    "../../widgets/FinanceStockHistoryPane.qml", import.meta.url
), "utf8");
const {summarizePinnedInterval: analyze} = vm.runInNewContext(
    policy + "\n({summarizePinnedInterval})"
);
const copy = value => JSON.parse(JSON.stringify(value));
const price = [100, 110, 105, 120, 90, 90];
const rows = price.map((p,i) => ({
    date: "2026-11-" + String(i+2).padStart(2, "0"), price:p
}));
function snapshot(bars=rows) {
    return {
        schemaVersion:1, source:"eodhd-eod", readOnly:true,
        cik:"0000320193", symbol:"AAPL.US",
        priceBasis:"ADJUSTED CLOSE",
        from:"2026-11-01", to:"2026-11-10",
        bars, first:bars.length ? {...bars[0]} : null,
        last:bars.length ? {...bars[bars.length-1]} : null
    };
}
const frozen=snapshot();
for(const bar of frozen.bars)Object.freeze(bar);
Object.freeze(frozen.bars);
Object.freeze(frozen.first);
Object.freeze(frozen.last);
Object.freeze(frozen);
const segment=copy(analyze(frozen,1,4));
assert.deepEqual(segment, {
    from:{date:"2026-11-03",price:110},
    to:{date:"2026-11-06",price:90},
    sessions:4,observedSteps:3,
    high:{date:"2026-11-05",price:120},
    low:{date:"2026-11-06",price:90},
    maxDrawdownPct:25,
    drawdownPeak:{date:"2026-11-05",price:120},
    drawdownTrough:{date:"2026-11-06",price:90},
    upSteps:1,downSteps:2,flatSteps:0,
    priceBasis:"ADJUSTED CLOSE",pathOrder:"CHRONOLOGICAL",
    source:"loaded-eodhd-range-only",
    readOnly:true,noProviderCalls:true
});
const backwards=copy(analyze(frozen,4,1));
assert.deepEqual(backwards,segment, "interval always chronological, even when B before A");
segment.high.price=999;
assert.equal(frozen.bars[3].price,120);
assert.equal(analyze(frozen,1,4).high.price,120);
const early=analyze(frozen,0,2);
assert.equal(early.high.price,110);
assert.equal(early.low.price,100);
assert.equal(early.maxDrawdownPct,4.55);
assert.equal(early.drawdownPeak.date,"2026-11-03");
assert.equal(early.drawdownTrough.date,"2026-11-04");
assert.deepEqual([early.upSteps,early.downSteps,early.flatSteps],[1,1,0]);
const same=analyze(frozen,3,3);
assert.equal(same.sessions,1);
assert.equal(same.observedSteps,0);
assert.equal(same.high.price,120);
assert.equal(same.low.price,120);
assert.equal(same.maxDrawdownPct,0);
assert.equal(same.drawdownPeak,null);
assert.equal(same.drawdownTrough,null);
assert.deepEqual([same.upSteps,same.downSteps,same.flatSteps],[0,0,0]);
const flat=analyze(frozen,4,5);
assert.equal(flat.maxDrawdownPct,0);
assert.equal(flat.drawdownPeak,null);
assert.equal(flat.flatSteps,1);
const allUp=analyze(snapshot([
    {date:"2026-11-02",price:100},
    {date:"2026-11-03",price:125},
    {date:"2026-11-04",price:150}
]),0,2);
assert.equal(allUp.maxDrawdownPct,0);
assert.equal(allUp.upSteps,2);
assert.equal(allUp.downSteps,0);
const allDown=analyze(snapshot([
    {date:"2026-11-02",price:150},
    {date:"2026-11-03",price:125},
    {date:"2026-11-04",price:100}
]),0,2);
assert.equal(allDown.maxDrawdownPct,33.33);
assert.equal(allDown.drawdownPeak.date,"2026-11-02");
assert.equal(allDown.drawdownTrough.date,"2026-11-04");
assert.equal(allDown.downSteps,2);
assert.equal(allDown.upSteps,0);

for (const bad of [-1,6,0.5,NaN,Infinity,"1",null,undefined]) {
    assert.equal(analyze(frozen,bad,0),null);
    assert.equal(analyze(frozen,0,bad),null);
}
for (const bad of [
    null,{},snapshot([]),
    {...snapshot(),schemaVersion:2},
    {...snapshot(),source:"alpha-vantage"},
    {...snapshot(),readOnly:false},
    {...snapshot(),priceBasis:"MIXED"},
    {...snapshot(),first:{date:"2026-11-02",price:1}},
    {...snapshot(),last:{date:"2026-11-07",price:1}},
    snapshot([rows[2],rows[1]]),
    snapshot([{date:"2026-11-02",price:0}]),
    snapshot([{date:"2026-11-02",price:Infinity}]),
    snapshot([{date:"2026-11-02",price:NaN}]),
    snapshot(Array.from({length:133},()=>({date:"2026-11-02",price:100})))
]) assert.equal(analyze(bad,0,1),null);

for(const expected of [
    'readonly property var pinnedInterval: pinnedPairComparison !== null',
    'RangeAnalysisPolicy.summarizePinnedInterval(',
    'objectName: "marketPinnedIntervalAnalysisPanel"',
    'objectName: "marketPinnedIntervalAnalysisText"',
    "BETWEEN PINNED A AND B // CHRONOLOGICAL LOADED CLOSES",
    "MAX PEAK-TO-TROUGH CLOSE DECLINE ",
    "EARLIER TO LATER EVEN IF B PRECEDES A",
    "NONE OBSERVED",
    "onSnapshotChanged: clearPinnedComparison()",
    "onPriceBarsChanged:",
    "onDayModeChanged:",
    "pinnedSnapshot === snapshot"
])assert.ok(qml.includes(expected), expected);
const section=qml.slice(
    qml.indexOf('objectName: "marketPinnedIntervalAnalysisPanel"'),
    qml.indexOf('id: openSelectedInDay')
);
for(const forbidden of [
    "Process {","fetch(","stockFeed.refresh(","reserve(",
    "writeFile(","XMLHttpRequest","Qt.openUrlExternally"
]) {
    assert.ok(!section.includes(forbidden),forbidden);
    assert.ok(!policy.includes(forbidden),forbidden);
}
console.log("Finance Market M31 chronological pinned A/B loaded-close interval, drawdown/high/low and stale-source guards: PASS");
