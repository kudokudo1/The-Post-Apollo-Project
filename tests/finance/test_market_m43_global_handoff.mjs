import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const read=p=>readFileSync(new URL("../../widgets/"+p,import.meta.url),"utf8");
const policy=read("FinanceStockRangeAnalysisPolicy.js"),qml=read("FinanceStockHistoryPane.qml");
const {captureGlobalHistory:capture}=vm.runInNewContext(policy+"\n({captureGlobalHistory})");
const identity={figi:"BBG000000001",ticker:"ASML",name:"ASML search result",exchCode:"NA"};
const listing={symbol:"ASML.AS",code:"ASML",exchange:"AS",name:"ASML provider listing",currency:"EUR"};
const rows=[{date:"2026-11-02",price:100},{date:"2026-11-04",price:110}];
const eod={schemaVersion:1,readOnly:true,identityVerified:false,source:"eodhd-eod",symbol:listing.symbol,currency:"EUR",currencySource:"eodhd-search",priceBasis:"ADJUSTED CLOSE",from:"2026-11-01",to:"2026-11-06",retrievedAt:"2026-11-06T21:00:00Z",bars:rows,first:{...rows[0]},last:{...rows[1]},changePct:999};
const a=capture(identity,listing,eod);
assert.ok(a);assert.equal(a.currency,"EUR");assert.equal(a.source,"eodhd-eod");
assert.equal(a.identityVerified,false);assert.equal(a.cik,undefined);
assert.equal(a.listing.venue,"AS");assert.equal(a.identity.figi,identity.figi);
assert.ok(Math.abs(a.changePct-10)<1e-9);
assert.notEqual(a.bars,rows);assert.notEqual(a.bars[0],rows[0]);
assert.notEqual(a.identity,identity);assert.notEqual(a.listing,listing);
const avListing={symbol:"ASML.AMS",name:"ASML Alpha listing",region:"Netherlands",currency:"EUR"};
const av={...eod,source:"alpha-vantage-daily-compact",symbol:avListing.symbol,currencySource:"alpha-vantage-symbol-search",priceBasis:"CLOSE",compactMaxBars:100,returnedBars:100,compactMayBeTruncated:true};
const b=capture(identity,avListing,av);
assert.ok(b);assert.equal(b.source,"alpha-vantage-daily-compact");assert.equal(b.compactMayBeTruncated,true);assert.equal(b.listing.venue,"Netherlands");
const empty=capture(identity,listing,{...eod,bars:[],first:null,last:null});
assert.ok(empty);assert.equal(empty.changePct,null);assert.equal(empty.first,null);
for(const bad of [null,{...eod,source:"other"},{...eod,identityVerified:true},{...eod,readOnly:false},
    {...eod,symbol:"OTHER.AS"},{...eod,currency:"USD"},{...eod,currencySource:"unknown"},
    {...eod,priceBasis:"MIXED"},{...eod,from:"2020-01-01"},{...eod,retrievedAt:"bad"},
    {...eod,bars:[...rows].reverse()},{...eod,first:{...rows[0],price:1}},
    {...eod,bars:[{date:"2026-11-02",price:Infinity}],last:rows[0]}])
    assert.equal(capture(identity,listing,bad),null);
assert.equal(capture({...identity,figi:"bad"},listing,eod),null);
assert.equal(capture({...identity,ticker:"OTHER"},listing,eod),null);
assert.equal(capture(identity,{...listing,exchange:"XX"},eod),null);
assert.equal(capture(identity,avListing,{...av,priceBasis:"ADJUSTED CLOSE"}),null);
assert.equal(capture(identity,avListing,{...av,returnedBars:1}),null);
assert.equal(capture(identity,avListing,{...av,compactMayBeTruncated:"true"}),null);
const f=qml.slice(qml.indexOf("function acceptGlobalHistory("),qml.indexOf("readonly property string priceUnit"));
const ctx={discoveryOpen:true,visible:true,stockFeed:{monitoring:true},RangeAnalysisPolicy:{captureGlobalHistory:capture},
    stockReference:null,globalHistory:null,globalHandoffMessage:"",controlsExpanded:true,researchView:"compare",scroll:{contentY:90}};
vm.createContext(ctx);vm.runInContext(f,ctx);
assert.equal(ctx.acceptGlobalHistory(identity,listing,eod),true);
assert.equal(ctx.discoveryOpen,false);assert.equal(ctx.researchView,"price");assert.equal(ctx.controlsExpanded,false);
assert.equal(ctx.scroll.contentY,0);assert.equal(ctx.globalHistory.bars[0].price,100);
rows[0].price=1;identity.name="changed";listing.name="changed";
assert.equal(ctx.globalHistory.bars[0].price,100);assert.equal(ctx.globalHistory.identity.name,"ASML search result");
const saved=ctx.globalHistory;
assert.equal(ctx.acceptGlobalHistory(identity,listing,eod),false);assert.equal(ctx.globalHistory,saved);
ctx.discoveryOpen=true;assert.equal(ctx.acceptGlobalHistory(identity,listing,null),false);
assert.equal(ctx.globalHistory,saved);assert.match(ctx.globalHandoffMessage,/REFUSED/);
ctx.returnToLegacyHistory();assert.equal(ctx.globalHistory,null);
for(const token of ["readonly property var snapshot: globalHistoryActive ? globalHistory",
    "RangeAnalysisPolicy.retainedGlobalRange(snapshot)",
    "readonly property string priceUnit: globalHistoryActive ? globalHistory.currency",
    "RETURN TO LEGACY STOCKS","FIGI MATCH NOT VERIFIED","COMPARE MATCHING PROVIDER, CURRENCY, BASIS AND WINDOW",
    "onHistoryChosen: function(identity, listing, snapshot)","id: priceCanvas",
    "if (!stocks.globalHistoryActive && stocks.stockFeed) stocks.stockFeed.refresh()"])
    assert.ok(qml.includes(token),token);
for(const p of ["FinanceGlobalPricePane.qml","FinanceAlphaVantageFreePane.qml"]){
    const s=read(p);assert.ok(s.includes('label: "USE IN STOCKS"'));assert.ok(s.includes("signal historyChosen("));
}
assert.ok(read("FinanceStockDiscoveryPane.qml").includes("discovery.historyChosen(identity,listing,snapshot)"));
for(const forbidden of ["refresh(","fetch(","reserve(","exec(","writeFile("])assert.ok(!f.includes(forbidden),forbidden);
console.log("Finance Market M43 global provider handoff, detached bars, real currency, listing guards and legacy isolation: PASS");
