#!/usr/bin/env node
// Only loopback HTTP and fictional injected prices; never an external request.
import assert from "node:assert/strict";
import { createMarketDataHub } from "../../scripts/finance/market_data_hub.mjs";
import { createMarketDataServer } from "../../scripts/finance/market_data_server.mjs";

const cik="0000320193", filingDate="2026-10-20";
const now=Date.parse("2026-10-24T20:00:00.000Z");
let calls=0;
const hub=createMarketDataHub({now:()=>now,adapters:{eodhd:async(c,d)=>{
  calls++;
  if(c==="0001045810") throw new Error("provider-key-required");
  return {schemaVersion:1,source:"eodhd-eod",readOnly:true,
    cik:c,filingDate:d,symbol:c===cik?"AAPL.US":"MSFT.US",
    priceBasis:"CLOSE",retrievedAt:"2026-10-24T19:00:00Z",
    previous:{date:"2026-10-19",price:100},
    next:{date:"2026-10-21",price:105},
    filingDay:null,changePct:5,
    bars:[{date:"2026-10-19",price:100},{date:"2026-10-21",price:105}]};
}}});
const server=createMarketDataServer({hub});
await new Promise((resolve,reject)=>{
  server.once("error",reject);
  server.listen(0,"127.0.0.1",resolve);
});
try {
  const base="http://127.0.0.1:"+server.address().port;
  const authorized={headers:{"X-Post-Apollo-Client":"financew"}};
  let result=await fetch(base+"/v1/health",authorized);
  assert.equal(result.status,200);
  let j=await result.json();
  assert.equal(j.readOnly,true);
  assert.equal(j.cacheEntries,0);
  assert.deepEqual(j.providerIds,["eodhd"]);

  const url=base+"/v1/price-context?cik="+cik+"&date="+filingDate;
  result=await fetch(url,authorized);
  assert.equal(result.status,200);
  j=await result.json();
  assert.equal(j.hub.state,"FETCHED");
  assert.equal(j.symbol,"AAPL.US");
  assert.equal(j.previous.date,"2026-10-19");
  result=await fetch(url,authorized);
  assert.equal(result.status,200);
  assert.equal((await result.json()).hub.state,"CACHED");
  assert.equal(calls,1);

  // A browser-originated request must not be enough to trigger a fetch.
  result=await fetch(url,{headers:{Origin:"https://unrelated.invalid",
    "X-Post-Apollo-Client":"financew"}});
  assert.equal(result.status,403);
  result=await fetch(url);
  assert.equal(result.status,403);
  result=await fetch(url,{...authorized,method:"POST"});
  assert.equal(result.status,405);
  result=await fetch(base+"/v1/price-context?cik=bad&date=2026-10-20",authorized);
  assert.equal(result.status,400);
  result=await fetch(base+"/v1/price-context?cik="+cik+"&date=2026-10-20&provider=unreviewed",authorized);
  assert.equal(result.status,400);
  result=await fetch(base+"/v1/price-context?cik="+cik+"&date=2026-10-20&date=2026-10-21",authorized);
  assert.equal(result.status,404);
  result=await fetch(base+"/v1/admin",authorized);
  assert.equal(result.status,404);
  result=await fetch(base+"/v1/price-context?cik=0001045810&date=2026-10-20",authorized);
  assert.equal(result.status,503);
  assert.deepEqual(await result.json(),{error:"provider-key-required"});
  result=await fetch(base+"/v1/health",authorized);
  j=await result.json();
  assert.equal(j.cacheEntries,1); // failure not cached
  assert.equal(calls,2);
  console.log("Finance market-data hub M7 guarded loopback API offline fixtures: PASS");
} finally {
  await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));
}
