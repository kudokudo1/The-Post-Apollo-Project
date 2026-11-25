import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const p=vm.runInNewContext(js+"\n({captureGlobalHistory,retainedGlobalRange,summarizeRange,movingAverageSeries,movingAverageRelationship,compareSelectedToLast,comparePinnedRangeSessions,summarizePinnedInterval,compareHistoricalIntervals,normalizedIntervalChart,inspectNormalizedStep,captureStockReference})");
const identity={figi:"BBG000000001",ticker:"ASML",name:"ASML search",exchCode:"NA"};
const bars=Array.from({length:25},(_,i)=>({date:"2026-11-"+String(i+1).padStart(2,"0"),price:100+i}));
const data={schemaVersion:1,readOnly:true,identityVerified:false,source:"eodhd-eod",
    symbol:"ASML.AS",currency:"EUR",currencySource:"eodhd-search",priceBasis:"ADJUSTED CLOSE",
    from:"2026-11-01",to:"2026-11-25",retrievedAt:"2026-11-26T00:00:00Z",
    bars,first:bars[0],last:bars[24]};
const eod=p.captureGlobalHistory(identity,{symbol:data.symbol,code:"ASML",exchange:"AS",name:"ASML",currency:"EUR"},data);
const av=p.captureGlobalHistory(identity,{symbol:"ASML.AMS",region:"Netherlands",name:"ASML",currency:"EUR"},
    {...data,source:"alpha-vantage-daily-compact",symbol:"ASML.AMS",priceBasis:"CLOSE",
        currencySource:"alpha-vantage-symbol-search",compactMaxBars:100,returnedBars:100,compactMayBeTruncated:true});
for(const [snapshot,source] of [[eod,"loaded-eodhd-range-only"],[av,"loaded-alpha-vantage-range-only"]]){
    assert.ok(snapshot);assert.equal(p.retainedGlobalRange(snapshot),true);
    const stats=p.summarizeRange(snapshot);
    assert.equal(stats.source,source);assert.equal(stats.sessions,25);
    assert.equal(stats.high.price,124);assert.equal(stats.maxDrawdownPct,0);
    assert.equal(p.movingAverageSeries(snapshot).latest20,114.5);
    assert.equal(p.movingAverageRelationship(snapshot).latestSide,"ABOVE");
    assert.equal(p.compareSelectedToLast(snapshot,0).deltaPct,24);
    assert.equal(p.comparePinnedRangeSessions(snapshot,0,10).deltaPct,10);
    assert.equal(p.summarizePinnedInterval(snapshot,10,0).observedSteps,10);
    assert.equal(p.compareHistoricalIntervals(snapshot,0,10,10,24).firstReturnPct,10);
    const chart=p.normalizedIntervalChart(snapshot,0,10,10,24);
    assert.equal(chart.source,source);
    assert.equal(p.inspectNormalizedStep(chart,0).first.value,100);
    assert.equal(p.inspectNormalizedStep(chart,14).first,null);
    assert.equal(p.captureStockReference(snapshot,"0000320193","ASML.AS"),null);
    for(const bad of [{...snapshot,noProviderCalls:false},{...snapshot,identityVerified:true},
        {...snapshot,cik:"0000320193"},{...snapshot,currency:"USD"},
        {...snapshot,listing:{...snapshot.listing,venue:"wrong"}},
        {...snapshot,first:{...snapshot.first,price:1}}])
        assert.equal(p.summarizeRange(bad),null);
}
assert.equal(p.summarizeRange({...av,compactMayBeTruncated:"true"}),null);
assert.equal(p.summarizeRange({...av,priceBasis:"ADJUSTED CLOSE"}),null);
assert.equal(p.summarizeRange({...av,identity:undefined,listing:undefined}),null);
assert.equal(p.summarizeRange({...data,source:"alpha-vantage"}),null);
assert.equal(p.summarizeRange({...data,identityVerified:undefined}).sessions,25);
const price=qml.slice(qml.indexOf('objectName: "marketResearchPriceSection"'),qml.indexOf("id: openSelectedInDay"));
assert.ok(!price.includes("$"),"hardcoded currency in single-stock analysis");
for(const token of ["RangeAnalysisPolicy.retainedGlobalRange(snapshot)","stocks.priceUnit",
    "if (globalHistoryActive || rangeAnalysis === null || !stockFeed) return;",
    "&& !globalHistoryActive && rangeAnalysis !== null && stockFeed",
    "CROSS-STOCK PENDING"]) assert.ok(qml.includes(token),token);
assert.ok(!js.includes("..."),"unsupported QML object spread");
console.log("Finance Market M44 global EODHD/Alpha same-stock analytics, provenance, currency and legacy comparison isolation: PASS");
