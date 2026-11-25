import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const p=vm.runInNewContext(js+"\n({captureGlobalHistory,captureGlobalStockReference,compareGlobalStockReferences,crossStockNormalizedChart,inspectCrossStockDate,summarizeCrossStockLeadership,crossStockGapChart})");
function fixture(ticker,figi,days,prices,{alpha=false,currency="EUR",basis="CLOSE",to="2026-11-10",venue="AS"}={}) {
    const identity={ticker,figi,name:ticker,exchCode:"NA"};
    const symbol=ticker+(alpha?".AMS":"."+venue);
    const listing={symbol,code:ticker,exchange:venue,region:"Netherlands",currency,name:ticker};
    const bars=days.map((d,i)=>({date:"2026-11-"+String(d).padStart(2,"0"),price:prices[i]}));
    return p.captureGlobalHistory(identity,listing,{schemaVersion:1,readOnly:true,identityVerified:false,
        source:alpha?"alpha-vantage-daily-compact":"eodhd-eod",symbol,currency,
        currencySource:alpha?"alpha-vantage-symbol-search":"eodhd-search",priceBasis:basis,
        from:"2026-11-01",to,retrievedAt:"2026-11-11T00:00:00Z",bars,first:bars[0],last:bars.at(-1),
        compactMaxBars:100,returnedBars:100,compactMayBeTruncated:alpha});
}
const i="BBG000000001",j="BBG000000002";
const near=(x,y)=>assert.ok(Number.isFinite(x)&&Math.abs(x-y)<1e-9,x+" vs "+y);
for(const alpha of [false,true]){
    const a=fixture("ASML",i,[2,3,5,6],[100,900,110,120],{alpha});
    const b=fixture("ADYEN",j,[2,4,5,6],[200,700,180,160],{alpha});
    const ref=p.captureGlobalStockReference(a);
    assert.ok(ref);assert.notEqual(ref.bars,a.bars);assert.notEqual(ref.identity,a.identity);
    assert.equal(ref.identityVerified,false);assert.equal(ref.cik,undefined);
    const c=p.compareGlobalStockReferences(ref,b);
    assert.equal(c.state,"ready");assert.equal(c.currency,"EUR");assert.equal(c.matched,3);
    assert.equal(c.referenceUnmatched,1);assert.equal(c.currentUnmatched,1);
    assert.equal(c.referenceTruncated,alpha);assert.equal(c.identityVerified,false);
    near(c.referencePct,20);near(c.currentPct,-20);near(c.gapPoints,-40);
    const chart=p.crossStockNormalizedChart(c);
    assert.equal(chart.source,alpha?"loaded-alpha-vantage-common-dates-only":"loaded-eodhd-common-dates-only");
    const detail=p.inspectCrossStockDate(c,1);
    assert.equal(detail.date,"2026-11-05");assert.equal(detail.reference.currency,"EUR");
    assert.equal(detail.current.currency,"EUR");near(detail.gapPoints,-20);
    assert.equal(p.summarizeCrossStockLeadership(c).referenceDates,2);
    near(p.crossStockGapChart(c).points[2].value,-40);
    near(p.compareGlobalStockReferences(b,ref).gapPoints,40);
    assert.equal(p.compareGlobalStockReferences(ref,a).state,"same-stock");
    assert.equal(p.compareGlobalStockReferences(ref,fixture("ASML",j,[2,6],[100,110],{alpha})).state,"same-stock");
    assert.equal(p.compareGlobalStockReferences(ref,fixture("OTHER",i,[2,6],[100,110],{alpha})).state,"same-stock");
    assert.equal(p.compareGlobalStockReferences(ref,fixture("ADYEN",j,[2,6],[100,110],{alpha:!alpha})).state,"provider-mismatch");
    assert.equal(p.compareGlobalStockReferences(ref,fixture("ADYEN",j,[2,6],[100,110],{alpha,currency:"USD"})).state,"currency-mismatch");
    assert.equal(p.compareGlobalStockReferences(ref,fixture("ADYEN",j,[2,6],[100,110],{alpha,to:"2026-11-09"})).state,"window-mismatch");
    assert.equal(p.compareGlobalStockReferences(ref,fixture("ADYEN",j,[7,8],[100,110],{alpha})).state,"insufficient");
    if(!alpha)assert.equal(p.compareGlobalStockReferences(ref,fixture("ADYEN",j,[2,6],[100,110],{basis:"ADJUSTED CLOSE"})).state,"basis-mismatch");
    assert.equal(p.compareGlobalStockReferences(ref,{...b,currency:"USD"}).state,"invalid");
    assert.equal(p.crossStockNormalizedChart({...c,currency:"???"}),null);
    c.pairs[0].referencePrice=1;assert.equal(ref.bars[0].price,100);
}
for(const token of ["RangeAnalysisPolicy.captureGlobalStockReference(snapshot)",
    "RangeAnalysisPolicy.compareGlobalStockReferences(stockReference,snapshot)",
    "PROVIDER MISMATCH","CURRENCY MISMATCH // NO FX CONVERSION",
    "LEGACY AND GLOBAL REFERENCES CANNOT BE MIXED","p.currency +",
    'researchView=stockReference !== null && stockReference.identity ? "compare" : "price"'])
    assert.ok(qml.includes(token),token);
assert.ok(!js.includes("..."),"unsupported QML JS spread");
console.log("Finance Market M45 global matched-date comparisons, provider/currency/basis refusals, leadership and gap reuse: PASS");
