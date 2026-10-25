#!/usr/bin/env node
// M8 tests use fake provider prices and fake/ephemeral loopback endpoints only.
import assert from "node:assert/strict";
import { readOptionalPrice, validPort, connectionRefused }
  from "../../scripts/finance/read_sec_price_optional_hub.mjs";
import { createMarketDataHub } from "../../scripts/finance/market_data_hub.mjs";
import { createMarketDataServer } from "../../scripts/finance/market_data_server.mjs";

const cik="0000320193", date="2026-10-20";
const clock=()=> "2026-10-24T20:00:00.000Z";
const prices=()=> ({
  schemaVersion:1,source:"eodhd-eod",readOnly:true,
  cik,symbol:"AAPL.US",filingDate:date,retrievedAt:clock(),
  priceBasis:"CLOSE",changePct:5,
  previous:{date:"2026-10-19",price:100},filingDay:null,
  next:{date:"2026-10-21",price:105},
  bars:[{date:"2026-10-19",price:100},{date:"2026-10-21",price:105}]
});
let direct=0,hubRequests=0;
const directReader=async()=>{direct++;return prices();};
const refused=()=>new TypeError("fetch failed",{cause:{code:"ECONNREFUSED"}});
assert.equal(validPort(48731),true);
assert.equal(validPort(0),false);
assert.equal(validPort(65536),false);
assert.equal(connectionRefused(refused()),true);
assert.equal(connectionRefused(new Error("timed out")),false);

// Absent hub is the ONLY condition allowing direct fallback.
const fallback=await readOptionalPrice(cik,date,{
  fetcher:async url=>{hubRequests++;assert.match(url,/\/v1\/health$/);throw refused();},
  directReader, now:clock
});
assert.equal(fallback.delivery.via,"DIRECT");
assert.equal(fallback.delivery.state,"DIRECT");
assert.equal(fallback.delivery.cachedAt,null);
assert.equal(fallback.source,"eodhd-eod");
assert.equal(direct,1);
assert.equal(hubRequests,1);

// Invalid requests cannot query hub or the upstream provider.
await assert.rejects(readOptionalPrice("not-a-cik",date,{
  fetcher:async()=>{hubRequests++;},directReader,now:clock
}),/invalid-selection/);
await assert.rejects(readOptionalPrice(cik,"2026-10-25",{
  fetcher:async()=>{hubRequests++;},directReader,now:clock
}),/invalid-selection/);
assert.equal(direct,1);
assert.equal(hubRequests,1);

const healthy={schemaVersion:1,service:"post-apollo-market-hub",readOnly:true,
  providerIds:["eodhd"],backgroundPolling:false};
const envelope={...prices(),hub:{provider:"eodhd",state:"CACHED",
  cachedAt:"2026-10-24T19:40:00.000Z",servedAt:clock(),
  expiresAt:"2026-10-24T20:40:00.000Z",ageSeconds:1200}};
const fakeResponse=(body,status=200)=>({
  ok:status===200,status,
  headers:{get:()=>null},text:async()=>JSON.stringify(body)
});
const fakeFetcher=async(url,opts)=>{
  hubRequests++;
  assert.equal(opts.method,"GET");
  assert.equal(opts.redirect,"error");
  assert.equal(opts.headers["X-Post-Apollo-Client"],"financew");
  if(url.endsWith("/v1/health"))return fakeResponse(healthy);
  assert.match(url,/\/v1\/price-context\?cik=0000320193&date=2026-10-20$/);
  return fakeResponse(envelope);
};
const hit=await readOptionalPrice(cik,date,{fetcher:fakeFetcher,directReader,now:clock});
assert.equal(hit.delivery.via,"HUB");
assert.equal(hit.delivery.state,"CACHED");
assert.equal(hit.delivery.ageSeconds,1200);
assert.equal(hit.delivery.cachedAt,"2026-10-24T19:40:00.000Z");
assert.equal(direct,1);

// A healthy listener's errors must never secretly cause a direct fetch.
const denial=async(url,opts)=>url.endsWith("/v1/health")
  ?fakeResponse(healthy):fakeResponse({error:"provider-key-required"},503);
await assert.rejects(readOptionalPrice(cik,date,{
  fetcher:denial,directReader,now:clock
}),/provider-key-required/);
assert.equal(direct,1);
const invalidHealth=async()=>fakeResponse({...healthy,service:"unknown"});
await assert.rejects(readOptionalPrice(cik,date,{
  fetcher:invalidHealth,directReader,now:clock
}),/hub-unhealthy/);
await assert.rejects(readOptionalPrice(cik,date,{
  fetcher:async()=>{throw new Error("timed out");},directReader,now:clock
}),/hub-unhealthy/);
const stale=async(url)=>url.endsWith("/v1/health")
  ?fakeResponse(healthy):fakeResponse({...envelope,cik:"0000789019"});
await assert.rejects(readOptionalPrice(cik,date,{
  fetcher:stale,directReader,now:clock
}),/hub-invalid-response/);
const missingMeta=async(url)=>url.endsWith("/v1/health")
  ?fakeResponse(healthy):fakeResponse(prices());
await assert.rejects(readOptionalPrice(cik,date,{
  fetcher:missingMeta,directReader,now:clock
}),/hub-invalid-response/);
const hubRefusedOnPrice=async(url)=>url.endsWith("/v1/health")
  ?fakeResponse(healthy):Promise.reject(refused());
await assert.rejects(readOptionalPrice(cik,date,{
  fetcher:hubRefusedOnPrice,directReader,now:clock
}),/hub-unhealthy/);
assert.equal(direct,1);

// Full integration with the *actual M7 local HTTP server*, using fictional
// adapter data, ephemeral 127.0.0.1 port, and no external fetches.
let upstream=0;
const hub=createMarketDataHub({
  now:()=>Date.parse(clock()),
  adapters:{eodhd:async()=>{upstream++;return prices();}}
});
const server=createMarketDataServer({hub});
await new Promise((resolve,reject)=>{
  server.once("error",reject);
  server.listen(0,"127.0.0.1",resolve);
});
const port=server.address().port;
try {
  let served=await readOptionalPrice(cik,date,{
    port,directReader,now:clock
  });
  assert.equal(served.delivery.via,"HUB");
  assert.equal(served.delivery.state,"FETCHED");
  assert.equal(served.previous.price,100);
  served=await readOptionalPrice(cik,date,{
    port,directReader,now:clock
  });
  assert.equal(served.delivery.state,"CACHED");
  assert.equal(upstream,1);
  assert.equal(direct,1);
} finally {
  await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));
}
const afterStop=await readOptionalPrice(cik,date,{port,directReader,now:clock});
assert.equal(afterStop.delivery.via,"DIRECT");
assert.equal(direct,2);
assert.equal(upstream,1);
console.log("Finance M8 optional hub/direct fallback, integrity and real loopback integration: PASS");
