#!/usr/bin/env node
// M10: all prices fictional, no external market provider or personal token.
import assert from "node:assert/strict";
import {dayNumber,validateRange,normalizePriceRange,loadPriceRange}
  from "../../scripts/finance/read_market_price_range.mjs";
import {createMarketDataHub} from "../../scripts/finance/market_data_hub.mjs";
import {createMarketDataServer} from "../../scripts/finance/market_data_server.mjs";
import {readOptionalRange} from "../../scripts/finance/read_market_price_range_optional_hub.mjs";

const cik="0000320193", msft="0000789019", nvidia="0001045810";
const from="2026-09-01",to="2026-10-20",today="2026-10-24";
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
  await assert.rejects(readOptionalRange(nvidia,from,to,options),/provider-key-required/);
  assert.equal(directs,0);
  assert.equal(hub.health().cacheEntries,2);
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
assert.equal(upstream,3); // 1 Apple + 1 MSFT + 1 NVDA denial
console.log("Finance M10 historical ranges, provider gates, hub/cache/fallback fixtures: PASS");
