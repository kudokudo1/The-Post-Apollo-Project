#!/usr/bin/env node
// M10: all prices fictional, no external market provider or personal token.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {STOCK_SYMBOLS} from "../../scripts/finance/market_stock_catalog.mjs";
import {SYMBOLS as SEC_SYMBOLS} from "../../scripts/finance/read_sec_price_context.mjs";
import {dayNumber,validateRange,normalizePriceRange,loadPriceRange}
  from "../../scripts/finance/read_market_price_range.mjs";
import {createMarketDataHub} from "../../scripts/finance/market_data_hub.mjs";
import {createMarketDataServer} from "../../scripts/finance/market_data_server.mjs";
import {readOptionalRange} from "../../scripts/finance/read_market_price_range_optional_hub.mjs";

const cik="0000320193", msft="0000789019", nvidia="0001045810";
const from="2026-09-01",to="2026-10-20",today="2026-10-24";
// M16: provider range catalog is deliberately larger than SEC M5 coverage.
const additional=[
  ["0001018724","AMZN.US"],
  ["0001318605","TSLA.US"],
  ["0001652044","GOOGL.US"]
];
assert.deepEqual(Object.keys(SEC_SYMBOLS),
  ["0000320193","0000789019","0001045810"]);
assert.deepEqual(Object.keys(STOCK_SYMBOLS),
  [...Object.keys(SEC_SYMBOLS),...additional.map(([cik])=>cik)]);
for (const [company,symbol] of additional)
  assert.equal(STOCK_SYMBOLS[company],symbol);
assert.equal(SEC_SYMBOLS["0001318605"],undefined);
// QML's local catalog and Node's enforced provider catalog must match exactly.
const qmlCatalog=readFileSync(new URL(
  "../../widgets/FinanceStockModePolicy.js",import.meta.url),"utf8");
const qmlPolicy=vm.runInNewContext(qmlCatalog+"\n({stockItems,stockSymbols,stockSymbol})");
assert.deepEqual(JSON.parse(JSON.stringify(qmlPolicy.stockSymbols())),STOCK_SYMBOLS);
assert.equal(qmlPolicy.stockItems().length,6);
assert.equal(qmlPolicy.stockSymbol("9999999999"),null);
const rows=[
  {date:"2026-09-01",close:100,adjusted_close:99},
  {date:"2026-09-03",close:105,adjusted_close:104},
  {date:"2026-10-20",close:110,adjusted_close:109}
];
assert.notEqual(dayNumber("2026-02-30"),dayNumber("2026-02-28"));
assert.equal(dayNumber("2026-02-30"),null);
assert.equal(validateRange(cik,from,to,today).from,from);
for(const [a,b] of [["2026-10-21","2026-10-20"],["2026-02-30","2026-03-01"],
  ["2026-04-01","2026-10-24"],["2026-09-01","2026-10-25"]])
  assert.throws(()=>validateRange(cik,a,b,today),/invalid-range/);
assert.throws(()=>validateRange("9999999999",from,to,today),/invalid-range/);
const normalized=normalizePriceRange(rows,cik,from,to,"2026-10-24T00:00:00Z");
assert.equal(normalized.priceBasis,"ADJUSTED CLOSE");
assert.equal(normalized.first.price,99);
assert.equal(normalized.last.price,109);
assert.equal(normalized.changePct,10.1);
assert.equal(normalized.bars.length,3);
const empty=normalizePriceRange([],cik,"2026-10-17","2026-10-18","now");
assert.equal(empty.first,null);
assert.equal(empty.last,null);
assert.equal(empty.changePct,null);
const mixed=normalizePriceRange(rows.map((x,i)=>({
  ...x,adjusted_close:i===1?null:x.adjusted_close
})),cik,from,to,"now");
assert.equal(mixed.priceBasis,"CLOSE");
assert.equal(mixed.first.price,100);
assert.equal(mixed.last.price,110);
for(const bad of [
  [rows[0],rows[0]],
  [{date:"2026-08-31",close:100}],
  [{date:"2026-09-04",close:-1}],
  [{date:"2026-09-04",close:"NaN"}]
])assert.throws(()=>normalizePriceRange(bad,cik,from,to,"now"),/invalid-price-data/);
let calls=0;
const http=async(url,options)=>{
  calls++;
  const parsed=new URL(url);
  assert.equal(parsed.host,"eodhd.com");
  assert.equal(parsed.pathname,"/api/eod/AAPL.US");
  assert.equal(parsed.searchParams.get("api_token"),"demo");
  assert.equal(parsed.searchParams.get("from"),from);
  assert.equal(parsed.searchParams.get("to"),to);
  assert.equal(options.redirect,"error");
  return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(rows)};
};
const remote=await loadPriceRange(cik,from,to,http,async()=>null,today);
assert.equal(remote.first.price,99);
assert.equal(calls,1);
await assert.rejects(loadPriceRange(nvidia,from,to,
  async()=>{calls++;},async()=>null,today),/provider-key-required/);
assert.equal(calls,1);
await assert.rejects(loadPriceRange(msft,from,to,
  async()=>({ok:false,status:403}),async()=>null,today),/demo-not-authorized/);
await assert.rejects(loadPriceRange(cik,"2026-02-30",to,
  async()=>{calls++;},async()=>null,today),/invalid-range/);
assert.equal(calls,1);

// New issuers must fail before any HTTP call without a private token,
// and only use the exact symbol from the explicit allowlist when given one.
let noTokenCalls=0, tokenCalls=0;
for (const [company,symbol] of additional) {
  assert.equal(validateRange(company,from,to,today).cik,company);
  assert.equal(normalizePriceRange(rows,company,from,to,"now").symbol,symbol);
  await assert.rejects(loadPriceRange(company,from,to,
    async()=>{noTokenCalls++;throw new Error("must-not-contact");},
    async()=>null,today),/provider-key-required/);
  const withToken=await loadPriceRange(company,from,to,
    async (url,options)=>{
      tokenCalls++;
      const parsed=new URL(url);
      assert.equal(parsed.pathname,"/api/eod/"+symbol);
      assert.equal(parsed.searchParams.get("api_token"),"FICTIONAL-TEST-TOKEN");
      assert.equal(options.redirect,"error");
      return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(rows)};
    },
    async()=>"FICTIONAL-TEST-TOKEN",today);
  assert.equal(withToken.symbol,symbol);
  assert.equal(withToken.readOnly,true);
}
assert.equal(noTokenCalls,0);
assert.equal(tokenCalls,3);
assert.throws(()=>validateRange("9999999999",from,to,today),/invalid-range/);

const fake=(company,start,end)=>({
  ...normalizePriceRange(rows,company,start,end,"2026-10-24T12:00:00Z")
});
// For second issuer, use same fixture price rows; ensure independent symbol.
let upstream=0;
const clock=()=> "2026-10-24T20:00:00.000Z";
const hub=createMarketDataHub({
  now:()=>Date.parse(clock()),
  adapters:{eodhd:async()=>{throw new Error("M8 date adapter should not run");}},
  rangeAdapter:async(company,start,end)=>{
    upstream++;
    if(company===nvidia)throw new Error("provider-key-required");
    return fake(company,start,end);
  }
});
const server=createMarketDataServer({hub});
await new Promise((resolve,reject)=>{
  server.once("error",reject);
  server.listen(0,"127.0.0.1",resolve);
});
const port=server.address().port;
let directs=0;
const directReader=async()=>{directs++;return fake(cik,from,to);};
try {
  const options={port,now:clock,directReader};
  const a=await readOptionalRange(cik,from,to,options);
  assert.equal(a.delivery.via,"HUB");
  assert.equal(a.delivery.state,"FETCHED");
  const b=await readOptionalRange(cik,from,to,options);
  assert.equal(b.delivery.state,"CACHED");
  assert.equal(upstream,1);
  assert.equal(directs,0);
  const c=await readOptionalRange(msft,from,to,options);
  assert.equal(c.symbol,"MSFT.US");
  assert.equal(c.delivery.state,"FETCHED");
  assert.equal(upstream,2);
  const added=await readOptionalRange("0001318605",from,to,options);
  assert.equal(added.symbol,"TSLA.US");
  assert.equal(added.delivery.via,"HUB");
  assert.equal(added.delivery.state,"FETCHED");
  assert.equal(upstream,3);
  await assert.rejects(hub.getPriceContext({
    cik:"0001318605",filingDate:to
  }),/invalid-selection/);
  await assert.rejects(readOptionalRange(nvidia,from,to,options),/provider-key-required/);
  assert.equal(directs,0);
  assert.equal(hub.health().cacheEntries,3);
  // Original SEC date-context protocol remains routed separately.
  const base="http://127.0.0.1:"+port;
  const headers={"X-Post-Apollo-Client":"financew"};
  const res=await fetch(base+"/v1/price-range?cik="+cik
    +"&from="+from+"&to="+to+"&date=2026-10-01",{headers});
  assert.equal(res.status,404);
  const invalid=await fetch(base+"/v1/price-range?cik="+cik
    +"&from=2026-01-01&to=2026-10-20",{headers});
  assert.equal(invalid.status,400);
}finally {
  await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));
}
const fallback=await readOptionalRange(cik,from,to,{
  port,directReader,now:clock
});
assert.equal(fallback.delivery.via,"DIRECT");
assert.equal(directs,1);
assert.equal(upstream,4); // AAPL + MSFT + TSLA + NVDA denial
console.log("Finance M10 historical ranges, provider gates, hub/cache/fallback fixtures: PASS");
// M17 free global equity identity search runs in the established FinanceW CI gate.
await import("./test_openfigi_stock_search.mjs");
// M18: explicit free-key worldwide price candidates and daily EOD fixtures.
await import("./test_global_free_price_bridge.mjs");
// M19: second free global provider and local request-quota regression.
await import("./test_alpha_vantage_free.mjs");
// M20: durable, cross-process local-only reservation guard and adversarial tests.
await import("./test_market_shared_quota.mjs");
// M21: zero-provider-call local quota STATUS reads, missing/unsafe/locked DB.
await import("./test_market_quota_status.mjs");
// M26: derived close-to-close RANGE movement analysis, no new provider IO.
await import("./test_market_m26_range_analysis.mjs");
// M28: optional local-only trailing session SMA 5/20 chart overlays.
await import("./test_market_m28_moving_averages.mjs");
// M29: descriptive historical SMA 5-vs-20 side changes, no new API.
await import("./test_market_m29_sma_relationship.mjs");
