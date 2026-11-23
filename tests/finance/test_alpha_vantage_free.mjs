#!/usr/bin/env node
// Finance M19: fake-only free Alpha Vantage symbol discovery and raw EOD bars.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {
  ALPHA_TOKEN_FILE,ALPHA_FREE_LIMIT,validTicker,validSymbol,validRange,
  normalizeMatches,searchAlpha,normalizeDaily,loadAlphaDaily
} from "../../scripts/finance/read_alpha_vantage_free.mjs";

const file=path=>readFileSync(new URL(path,import.meta.url),"utf8");
const query="ASML",symbol="ASML.AMS",other="ASML";
const token="FAKE_ALPHA_FREE_KEY";
const sample=[
  {"1. symbol":symbol,"2. name":"ASML Holding N.V.","3. type":"Equity",
    "4. region":"Netherlands","8. currency":"EUR"},
  {"1. symbol":other,"2. name":"ASML ADR","3. type":"Equity",
    "4. region":"United States","8. currency":"USD"},
  {"1. symbol":"SAP.DEX","2. name":"SAP","3. type":"Equity",
    "4. region":"Germany","8. currency":"EUR"},
  {"1. symbol":"ASML.ETF","2. name":"ASML ETF","3. type":"ETF",
    "4. region":"United States","8. currency":"USD"}
];
const today="2026-11-22",from="2026-11-01",to="2026-11-20";
assert.equal(ALPHA_FREE_LIMIT,25);
assert.ok(ALPHA_TOKEN_FILE.endsWith("/finance-market/alpha-vantage-token.txt"));
assert.equal(validTicker(query),query);
assert.equal(validSymbol(symbol),symbol);
assert.deepEqual(validRange(from,to,today),{from,to});
for(const invalid of ["","asml","../secret","ASML/US","A B","X".repeat(31)])
  assert.throws(()=>validTicker(invalid),/invalid-ticker/);
for(const invalid of ["","asml.ams","A..B","../../../tmp","AB C"])
  assert.throws(()=>validSymbol(invalid),/invalid-symbol/);
for(const [a,b,c] of [
  ["2026-11-21","2026-11-01",today],
  ["2026-02-30","2026-11-01",today],
  ["2026-01-01","2026-11-20",today],
  ["2026-11-01","2026-11-23",today]
])assert.throws(()=>validRange(a,b,c),/invalid-range/);
const result=normalizeMatches({bestMatches:sample},query,"now");
assert.equal(result.items.length,2);
assert.deepEqual(result.items.map(x=>x.symbol),[symbol,other]);
assert.deepEqual(result.items.map(x=>x.currency),["EUR","USD"]);
assert.equal(result.items[0].matchedOpenFigi,false);
assert.equal(result.priceLinked,false);
assert.equal(result.source,"alpha-vantage-symbol-search");
assert.equal(normalizeMatches({bestMatches:[sample[0],sample[0]]},
  query,"now").items.length,1);
for(const invalid of [{bestMatches:null},{bestMatches:new Array(26).fill(sample[0])},
  {Note:"api limit"}, {Information:"premium membership"},
  {"Error Message":"Unknown symbol"}])
  assert.throws(()=>normalizeMatches(invalid,query,"now"),
    /provider-invalid|provider-rate-or-entitlement|provider-symbol-unavailable/);

let calls=0;
const searchFetch=async(url,options)=>{
  calls++;
  const u=new URL(url);
  assert.equal(u.origin,"https://www.alphavantage.co");
  assert.equal(u.pathname,"/query");
  assert.equal(u.searchParams.get("function"),"SYMBOL_SEARCH");
  assert.equal(u.searchParams.get("keywords"),query);
  assert.equal(u.searchParams.get("apikey"),token);
  assert.equal(u.searchParams.get("outputsize"),null);
  assert.equal(options.method,"GET");
  assert.equal(options.redirect,"error");
  return {status:200,ok:true,headers:{get:()=>null},
    text:async()=>JSON.stringify({bestMatches:sample})};
};
await assert.rejects(searchAlpha(query,searchFetch,async()=>null),
  /provider-key-required/);
assert.equal(calls,0);
const matching=await searchAlpha(query,searchFetch,async path=>{
  assert.equal(path,ALPHA_TOKEN_FILE);return token;
},()=> "2026-11-22T21:00:00Z");
assert.equal(calls,1);
assert.equal(matching.items[0].symbol,symbol);
for(const response of [
  {status:429,ok:false},
  {status:403,ok:false},
  {status:401,ok:false},
  {status:200,ok:true,headers:{get:()=>193000}},
  {status:200,ok:true,headers:{get:()=>null},text:async()=>"<html>oops</html>"},
  {status:200,ok:true,headers:{get:()=>null},
    text:async()=>JSON.stringify({Information:"25 requests reached"})}
]) {
  await assert.rejects(searchAlpha(query,async()=>response,async()=>token),
    /provider-rate-or-entitlement|provider-not-entitled|provider-key-invalid|provider-response-too-large|provider-invalid/);
}
const series={
  "2026-11-02":{"1. open":"102.0","4. close":"100.0"},
  "2026-11-12":{"1. open":"103.0","4. close":"105.0"},
  "2026-11-20":{"1. open":"108.0","4. close":"110.0"}
};
const daily={"Meta Data":{"2. Symbol":symbol,
  "3. Last Refreshed":"2026-11-20","4. Output Size":"Compact"},
  "Time Series (Daily)":series};
const normalized=normalizeDaily(daily,symbol,"EUR",from,to,"now");
assert.equal(normalized.source,"alpha-vantage-daily-compact");
assert.equal(normalized.priceBasis,"CLOSE");
assert.equal(normalized.currency,"EUR");
assert.equal(normalized.currencySource,"alpha-vantage-symbol-search");
assert.equal(normalized.identityVerified,false);
assert.equal(normalized.compactMaxBars,100);
assert.equal(normalized.compactMayBeTruncated,false);
assert.equal(normalized.first.price,100);
assert.equal(normalized.last.price,110);
assert.equal(normalized.changePct,10);
assert.equal(normalized.bars.length,3);
const empty=normalizeDaily(daily,symbol,"EUR","2026-11-21","2026-11-22","now");
assert.equal(empty.first,null);
assert.equal(empty.bars.length,0);
assert.equal(empty.changePct,null);
const packed={};
for(let i=0;i<100;i++){
  const date=new Date(Date.UTC(2026,6,1+i)).toISOString().slice(0,10);
  packed[date]={"4. close":String(i+1)};
}
const truncated=normalizeDaily({"Meta Data":{"2. Symbol":symbol},
  "Time Series (Daily)":packed},symbol,"EUR","2026-01-01",today,"now");
assert.equal(truncated.compactMayBeTruncated,true);
assert.equal(truncated.returnedBars,100);
assert.throws(()=>normalizeDaily({"Meta Data":{"2. Symbol":other},
  "Time Series (Daily)":series},symbol,"EUR",from,to,"now"),/provider-invalid/);
for(const bad of [
  {"Meta Data":{"2. Symbol":symbol},"Time Series (Daily)":{
    "2026-02-30":{"4. close":"10"}}},
  {"Meta Data":{"2. Symbol":symbol},"Time Series (Daily)":{
    "2026-11-20":{"4. close":"-100"}}},
  {"Meta Data":{"2. Symbol":symbol},"Time Series (Daily)":{}},
  {"Meta Data":{"2. Symbol":symbol},"Time Series (Daily)":
    Object.fromEntries(Array.from({length:101},(_,i)=>[
      new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10),
      {"4. close":"100"}]))}
])assert.throws(()=>normalizeDaily(bad,symbol,"EUR",from,to,"now"),/provider-invalid/);

let priceCalls=0;
const historyFetch=async(url,options)=>{
  priceCalls++;
  const u=new URL(url);
  assert.equal(u.origin,"https://www.alphavantage.co");
  assert.equal(u.searchParams.get("function"),"TIME_SERIES_DAILY");
  assert.equal(u.searchParams.get("symbol"),symbol);
  assert.equal(u.searchParams.get("outputsize"),"compact");
  assert.equal(u.searchParams.get("apikey"),token);
  assert.equal(options.redirect,"error");
  return {ok:true,status:200,headers:{get:()=>null},
    text:async()=>JSON.stringify(daily)};
};
await assert.rejects(loadAlphaDaily(symbol,"EUR",from,to,historyFetch,
  async()=>null,today),/provider-key-required/);
assert.equal(priceCalls,0);
const hist=await loadAlphaDaily(symbol,"EUR",from,to,historyFetch,
  async()=>token,today,()=> "2026-11-22T21:00:00Z");
assert.equal(hist.bars.length,3);
assert.equal(hist.priceBasis,"CLOSE");
assert.equal(priceCalls,1);
for(const wrong of [
  [symbol,"???",from,to],
  ["ASML/AMS","EUR",from,to],
  [symbol,"EUR","2026-01-01",to]
])await assert.rejects(loadAlphaDaily(...wrong,historyFetch,
  async()=>token,today),/invalid-symbol|invalid-currency|invalid-range/);
assert.equal(priceCalls,1);

const service=file("../../services/finance/FinanceAlphaVantageFreeService.qml");
const ui=file("../../widgets/FinanceAlphaVantageFreePane.qml");
const parent=file("../../widgets/FinanceGlobalPricePane.qml");
const eod=file("../../services/finance/FinanceGlobalPriceService.qml");
const oldStock=file("../../services/finance/FinanceStockHistoryReadService.qml");
assert.ok(service.includes('function chooseIdentity(item) {'));
assert.ok(service.includes('function lookup() {'));
assert.ok(service.includes('function chooseListing(item) {'));
assert.ok(service.includes('function loadHistory() {'));
assert.ok(service.includes('requestedIdentity!==identity.figi'));
assert.ok(service.includes('data.symbol!==selectedListing.symbol'));
assert.ok(service.includes('data.currency!==selectedListing.currency'));
assert.ok(service.includes('data.priceBasis!=="CLOSE"'));
assert.ok(service.includes('data.compactMaxBars!==100'));
assert.ok(service.includes('requestsThisRuntime++;'));
assert.ok(service.includes('if(!monitoring)clear();'));
assert.ok(service.includes('Quickshell.shellPath("scripts/finance/read_alpha_vantage_free.mjs")'));
assert.equal((service.match(/reader.exec\(\[/g)||[]).length,2);
assert.ok(ui.includes('ALPHA VANTAGE // FREE DAILY PRICES'));
assert.ok(ui.includes('label: "BACK TO EODHD"'));
assert.ok(ui.includes('"LOAD ALPHA VANTAGE DAILY CLOSES"'));
assert.ok(ui.includes('av.chooseListing(modelData)'));
assert.ok(ui.includes('av.selectPreset(modelData.days)'));
assert.ok(ui.includes('NOT ACCOUNT REMAINING'));
assert.ok(ui.includes('Canvas {'));
assert.ok(parent.includes('FinanceAlphaVantageFreePane {'));
assert.ok(parent.includes('alphaPane.inspectInstrument(priceFeed.identity)'));
assert.ok(parent.includes('priceView.alphaOpen'));
assert.ok(parent.includes('priceFeed.requestsThisRuntime'));
assert.ok(eod.includes('readonly property int advertisedFreeDailyAllowance: 20'));
assert.ok(eod.includes('function freeAttemptAllowed() {'));
assert.equal((eod.match(/requestsThisRuntime\+\+;/g)||[]).length,2);
assert.equal((oldStock.match(/reader.exec\(\[/g)||[]).length,1);
for(const src of [service,ui,eod,parent]){
  for(const forbidden of ["financeWrite.submit(","financeFundingWrite.submit(",
    "Qt.openUrlExternally","writeFile(","setInterval(",
    "https://clob.polymarket.com/order"])
    assert.ok(!src.includes(forbidden),forbidden);
}
console.log("Finance M19 free Alpha Vantage EOD, listing verification, compact bounds and local quota contracts: PASS");
