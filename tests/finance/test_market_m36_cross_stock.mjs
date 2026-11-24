import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockRangeAnalysisPolicy.js",import.meta.url),"utf8");
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
const {captureStockReference:capture,compareStockReferences:compare}=vm.runInNewContext(js+"\n({captureStockReference,compareStockReferences})");
const apple="0000320193",msft="0000789019";
function fixture(cik,symbol,days,prices) {
    const bars=days.map((day,i)=>Object.freeze({date:"2026-11-"+String(day).padStart(2,"0"),price:prices[i]}));
    Object.freeze(bars);
    return Object.freeze({schemaVersion:1,source:"eodhd-eod",readOnly:true,
        cik,symbol,priceBasis:"CLOSE",from:"2026-11-01",to:"2026-11-10",
        retrievedAt:"2026-11-11T00:00:00Z",bars,first:{...bars[0]},last:{...bars.at(-1)}});
}
const a=fixture(apple,"AAPL.US",[2,3,5,6],[100,150,110,120]);
const b=fixture(msft,"MSFT.US",[2,4,5,6],[200,400,180,160]);
const ref=capture(a,apple,"AAPL.US");
assert.ok(ref);
assert.notEqual(ref.bars,a.bars);
assert.notEqual(ref.bars[0],a.bars[0]);
const d=compare(ref,b,msft,"MSFT.US");
assert.equal(d.state,"ready");
assert.equal(d.matched,3);
assert.equal(d.referenceUnmatched,1);
assert.equal(d.currentUnmatched,1);
assert.equal(d.from,"2026-11-02");
assert.equal(d.to,"2026-11-06");
assert.ok(Math.abs(d.referencePct-20)<1e-9);
assert.ok(Math.abs(d.currentPct+20)<1e-9);
assert.ok(Math.abs(d.gapPoints+40)<1e-9);
assert.equal(d.referenceSymbol,"AAPL.US");
assert.equal(d.currentSymbol,"MSFT.US");
assert.equal(d.readOnly,true);
assert.equal(d.noProviderCalls,true);
d.pairs[0].referencePrice=1;
assert.equal(ref.bars[0].price,100);
assert.equal(a.bars[0].price,100);
assert.equal(compare(ref,a,apple,"AAPL.US").state,"same-stock");
assert.equal(compare(ref,{...b,to:"2026-11-09"},msft,"MSFT.US").state,"window-mismatch");
assert.equal(compare(ref,{...b,priceBasis:"ADJUSTED CLOSE"},msft,"MSFT.US").state,"basis-mismatch");
assert.equal(compare(ref,fixture(msft,"MSFT.US",[3,4],[200,100]),msft,"MSFT.US").state,"insufficient");
assert.equal(compare(ref,fixture(msft,"MSFT.US",[7,8],[200,100]),msft,"MSFT.US").matched,0);
assert.equal(compare(ref,b,apple,"AAPL.US").state,"invalid");
assert.equal(capture(a,apple,"MSFT.US"),null);
assert.equal(capture({...a,retrievedAt:"bad"},apple,"AAPL.US"),null);
assert.equal(capture({...a,source:"unknown"},apple,"AAPL.US"),null);
assert.equal(capture({...a,readOnly:false},apple,"AAPL.US"),null);
assert.equal(capture({...a,first:{date:a.first.date,price:9}},apple,"AAPL.US"),null);
for(const needle of ["property var stockReference: null","RangeAnalysisPolicy.captureStockReference(snapshot,",
    "StockModePolicy.stockSymbol(stockFeed.selectedCik)","RangeAnalysisPolicy.compareStockReferences(stockReference, snapshot,",
    'label: "SAVE STOCK REF"','label: "CLEAR REF"',"COMMON CLOSE DATES",
    "DATE WINDOW MISMATCH","PRICE BASIS MISMATCH","NEED TWO COMMON CLOSE DATES",
    "UNMATCHED CLOSES","HISTORICAL CLOSE MOVEMENT // NO FILL // NO NEW REQUEST"])assert.ok(qml.includes(needle),needle);
const section=qml.slice(qml.indexOf('label: "SAVE STOCK REF"'),qml.indexOf('objectName: "marketRangeAnalysisPanel"'));
for(const forbidden of ["fetch(","reserve(","stockFeed.refresh(","Process {","writeFile("])assert.ok(!section.includes(forbidden),forbidden);
console.log("Finance Market M36 detached reference, actual common dates, window/basis refusals, no new request: PASS");
