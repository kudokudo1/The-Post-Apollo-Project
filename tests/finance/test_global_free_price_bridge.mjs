#!/usr/bin/env node
// Finance M18: entirely fictional global equities and EODHD responses.
// No personal EODHD token, live prices, files, writes or network requests.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {
  validateTicker,validateSymbol,validateWindow,normalizeCandidates,
  findCandidates,normalizeHistory,readHistory
} from "../../scripts/finance/read_global_eodhd_history.mjs";

const read=relative=>readFileSync(new URL(relative,import.meta.url),"utf8");
const ticker="ASML",eur="ASML.AS",usd="ASML.US";
const today="2026-11-22",from="2026-11-01",to="2026-11-20";
const token="FICTIONAL_FREE_TOKEN";
const eurListing={Code:ticker,Exchange:"AS",Name:"ASML Holding NV",
  Type:"Common Stock",Country:"Netherlands",Currency:"EUR",
  ISIN:"NL0010273215"};
const usdListing={...eurListing,Exchange:"US",Currency:"USD",
  Name:"ASML Holding ADR",ISIN:"USN070592100"};
const rows=[
  {date:"2026-11-02",close:100,adjusted_close:99},
  {date:"2026-11-12",close:105,adjusted_close:104},
  {date:"2026-11-20",close:110,adjusted_close:109}
];
assert.equal(validateTicker(ticker),ticker);
assert.deepEqual(validateSymbol(eur),{code:ticker,exchange:"AS",symbol:eur});
assert.deepEqual(validateWindow(from,to,today),{from,to});
for(const bad of ["", "asml", "../../.US", "ASML/US","ASML US", "x".repeat(31)]) {
  assert.throws(()=>validateTicker(bad),/invalid-ticker/);
}
for(const bad of ["ASML","ASML/AS","https://evil.com","ASML..",
  "ASML.as","A".repeat(50)+".US"]){
  assert.throws(()=>validateSymbol(bad),/invalid-symbol|invalid-ticker/);
}
for(const [start,end,now] of [
  ["2026-11-20","2026-11-01",today],["2026-02-30",to,today],
  ["2026-01-01",to,today],[from,"2026-11-23",today],
  ["1999-12-31",to,today]
])assert.throws(()=>validateWindow(start,end,now),/invalid-range/);
const found=normalizeCandidates([eurListing,usdListing,
  {...eurListing,Type:"ETF"}, {...eurListing,Code:"ASMA"},
  {...eurListing,Exchange:"AS"}],ticker,"2026-11-22T20:00:00Z");
assert.equal(found.source,"eodhd-search");
assert.equal(found.readOnly,true);
assert.equal(found.priceLinked,false);
assert.equal(found.items.length,2);
assert.equal(found.items[0].symbol,eur);
assert.equal(found.items[0].currency,"EUR");
assert.equal(found.items[1].symbol,usd);
assert.equal(found.items[1].currency,"USD");
assert.notEqual(found.items[0].symbol,found.items[1].symbol);
assert.equal(found.items[0].isin,"NL0010273215");
assert.equal(normalizeCandidates([{...eurListing,Currency:"???"}],
  ticker,"now").items.length,0);
for(const invalid of [{error:"denied"},new Array(26).fill(eurListing),null])
  assert.throws(()=>normalizeCandidates(invalid,ticker,"now"),/provider-invalid/);
let searches=0;
const fetchSearch=async(url,opts)=>{
  searches++;
  const parsed=new URL(url);
  assert.equal(parsed.host,"eodhd.com");
  assert.equal(parsed.pathname,"/api/search/"+ticker);
  assert.equal(parsed.searchParams.get("api_token"),token);
  assert.equal(parsed.searchParams.get("fmt"),"json");
  assert.equal(parsed.searchParams.get("limit"),"25");
  assert.equal(parsed.searchParams.get("type"),"stock");
  assert.equal(opts.method,"GET");
  assert.equal(opts.redirect,"error");
  return {ok:true,status:200,headers:{get:()=>null},
    text:async()=>JSON.stringify([eurListing,usdListing])};
};
await assert.rejects(findCandidates(ticker,fetchSearch,
  async()=>null),/provider-key-required/);
assert.equal(searches,0);
const candidates=await findCandidates(ticker,fetchSearch,async()=>token,
  ()=>"2026-11-22T20:00:00Z");
assert.equal(candidates.items.length,2);
assert.equal(searches,1);
assert.equal(candidates.items[0].symbol,eur);
for(const [status,pattern] of [[429,/rate-limited/],[401,/provider-key-invalid/],
  [402,/provider-not-entitled/],[403,/provider-not-entitled/],
  [503,/provider-unavailable/]]) {
  await assert.rejects(findCandidates(ticker,async()=>({ok:false,status}),
    async()=>token),pattern);
}
await assert.rejects(findCandidates(ticker,async()=>({
  ok:true,status:200,headers:{get:()=>129000}
}),async()=>token),/provider-response-too-large/);
await assert.rejects(findCandidates(ticker,async()=>({
  ok:true,status:200,headers:{get:()=>null},
  text:async()=>"<html>nope</html>"
}),async()=>token),/provider-invalid/);

const normalized=normalizeHistory(rows,eur,"EUR",from,to,"2026-11-22T20:00:00Z");
assert.equal(normalized.source,"eodhd-eod");
assert.equal(normalized.readOnly,true);
assert.equal(normalized.currencySource,"eodhd-search");
assert.equal(normalized.identityVerified,false);
assert.equal(normalized.symbol,eur);
assert.equal(normalized.currency,"EUR");
assert.equal(normalized.priceBasis,"ADJUSTED CLOSE");
assert.equal(normalized.first.price,99);
assert.equal(normalized.last.price,109);
assert.equal(normalized.bars.length,3);
assert.equal(normalized.changePct,10.1);
const mixed=normalizeHistory(rows.map((x,i)=>({
  ...x,adjusted_close:i===1?null:x.adjusted_close
})),eur,"EUR",from,to,"now");
assert.equal(mixed.priceBasis,"CLOSE");
assert.equal(mixed.first.price,100);
const empty=normalizeHistory([],eur,"EUR",from,to,"now");
assert.equal(empty.changePct,null);
assert.equal(empty.first,null);
for(const invalid of [
  [rows[0],rows[0]], [{...rows[0],close:-1}],
  [{...rows[0],date:"2026-10-31"}], [{...rows[0],date:"2026-02-30"}],
  new Array(133).fill(rows[0])
])assert.throws(()=>normalizeHistory(invalid,eur,"EUR",from,to,"now"),
  /invalid-price-data/);
let prices=0;
const fetchEod=async(url,opts)=>{
  prices++;
  const parsed=new URL(url);
  assert.equal(parsed.host,"eodhd.com");
  assert.equal(parsed.pathname,"/api/eod/"+eur);
  assert.equal(parsed.searchParams.get("api_token"),token);
  assert.equal(parsed.searchParams.get("from"),from);
  assert.equal(parsed.searchParams.get("to"),to);
  assert.equal(parsed.searchParams.get("period"),"d");
  assert.equal(opts.redirect,"error");
  return {ok:true,status:200,headers:{get:()=>null},
    text:async()=>JSON.stringify(rows)};
};
await assert.rejects(readHistory(eur,"EUR",from,to,fetchEod,
  async()=>null,today),/provider-key-required/);
assert.equal(prices,0);
const result=await readHistory(eur,"EUR",from,to,fetchEod,
  async()=>token,today,()=> "2026-11-22T21:00:00Z");
assert.equal(result.currency,"EUR");
assert.equal(result.bars[1].price,104);
assert.equal(prices,1);
await assert.rejects(readHistory("ASML/AS","EUR",from,to,fetchEod,
  async()=>token,today),/invalid-symbol/);
await assert.rejects(readHistory(eur,"$$$",from,to,fetchEod,
  async()=>token,today),/invalid-currency/);
await assert.rejects(readHistory(eur,"EUR","2026-01-01",to,fetchEod,
  async()=>token,today),/invalid-range/);
assert.equal(prices,1);

const service=read("../../services/finance/FinanceGlobalPriceService.qml");
const pane=read("../../widgets/FinanceGlobalPricePane.qml");
const discovery=read("../../widgets/FinanceStockDiscoveryPane.qml");
const historic=read("../../services/finance/FinanceStockHistoryReadService.qml");
const finder=read("../../services/finance/FinanceStockDiscoveryService.qml");
assert.ok(service.includes('function chooseIdentity(item) {'));
assert.ok(service.includes('function lookup() {'));
assert.ok(service.includes('function chooseListing(row) {'));
assert.ok(service.includes('function loadHistory() {'));
assert.ok(service.includes('if (!monitoring || loading || reader.running'));
assert.ok(service.includes('data.identityVerified!==false'));
assert.ok(service.includes('data.currency!==selectedListing.currency'));
assert.ok(service.includes('data.symbol!==selectedListing.symbol'));
assert.ok(service.includes('requestedIdentity!==identity.figi'));
assert.ok(service.includes('Quickshell.shellPath("scripts/finance/read_global_eodhd_history.mjs")'));
assert.ok(service.includes('if (!monitoring) clear();'));
assert.equal((service.match(/reader.exec\(\[/g)||[]).length,2);
assert.ok(pane.includes('label: "BACK TO SEARCH"'));
assert.ok(pane.includes('"FIND EODHD PRICE LISTINGS"'));
assert.ok(pane.includes('"LOAD SELECTED DAILY HISTORY"'));
assert.ok(pane.includes('priceFeed.chooseListing(modelData)'));
assert.ok(pane.includes('priceFeed.selectPreset(modelData.days)'));
assert.ok(pane.includes('NOT FIGI VERIFIED'));
assert.ok(pane.includes('Canvas {'));
assert.ok(discovery.includes('label: "PRICE OPTIONS"'));
assert.ok(discovery.includes('FinanceGlobalPricePane {'));
assert.ok(discovery.includes('discovery.inspectPrice(modelData)'));
assert.equal((historic.match(/reader.exec\(\[/g)||[]).length,1);
assert.equal((finder.match(/reader.exec\(\[/g)||[]).length,1);
for(const text of [service,pane,discovery]){
  for(const forbidden of ["financeWrite.submit(","financeFundingWrite.submit(",
    "Qt.openUrlExternally","writeFile(","setInterval(",
    "https://clob.polymarket.com/order"])
    assert.ok(!text.includes(forbidden),forbidden);
}
console.log("Finance M18 free EODHD global listing choice, currencies, normalized daily closes and UI isolation: PASS");
