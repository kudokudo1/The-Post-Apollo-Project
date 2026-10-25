#!/usr/bin/env node
// M7 fictional prices only; no calls to real market provider or private files.
import assert from "node:assert/strict";
import { createMarketDataHub } from "../../scripts/finance/market_data_hub.mjs";

const APPLE="0000320193", MSFT="0000789019", NVDA="0001045810";
const map={ [APPLE]:"AAPL.US",[MSFT]:"MSFT.US",[NVDA]:"NVDA.US" };
const fixture=(cik,date)=>({
  schemaVersion:1,source:"eodhd-eod",readOnly:true,
  symbol:map[cik],cik,filingDate:date,priceBasis:"CLOSE",
  retrievedAt:"2026-10-24T00:00:00Z",changePct:5,
  bars:[{date:"2026-10-19",price:100},{date:"2026-10-21",price:105}],
  previous:{date:"2026-10-19",price:100},filingDay:null,
  next:{date:"2026-10-21",price:105}
});
let instant=Date.parse("2026-10-24T20:00:00.000Z"),fetches=0;
const hub=createMarketDataHub({
  now:()=>instant,
  adapters:{eodhd:async (cik,date)=>{fetches++;return fixture(cik,date)}}
});
const args={cik:APPLE,filingDate:"2026-10-20"};
const first=await hub.getPriceContext(args);
assert.equal(first.hub.state,"FETCHED");
assert.equal(first.hub.provider,"eodhd");
assert.equal(first.source,"eodhd-eod");
assert.equal(first.symbol,"AAPL.US");
assert.equal(fetches,1);
first.bars[0].price=9999; // no cache object exposure
const second=await hub.getPriceContext(args);
assert.equal(second.hub.state,"CACHED");
assert.equal(second.bars[0].price,100);
assert.equal(fetches,1);
assert.equal(hub.health().cacheEntries,1);
assert.equal(hub.health().backgroundPolling,false);
assert.equal(hub.health().providerIds[0],"eodhd");
instant += 20*60*1000;
const renewed=await hub.getPriceContext(args);
assert.equal(renewed.hub.state,"FETCHED");
assert.equal(fetches,2);
await hub.getPriceContext({cik:MSFT,filingDate:"2026-10-20"});
assert.equal(fetches,3); // distinct issuer
await assert.rejects(hub.getPriceContext({cik:"9999999999",filingDate:"2026-10-20"}),/invalid-selection/);
await assert.rejects(hub.getPriceContext({cik:APPLE,filingDate:"2026-02-30"}),/invalid-selection/);
await assert.rejects(hub.getPriceContext({cik:APPLE,filingDate:"2026-10-25"}),/invalid-selection/);
await assert.rejects(hub.getPriceContext({...args,provider:"unknown"}),/unknown-provider/);
assert.equal(fetches,3);

let held, started=0;
const wait=new Promise(resolve=>held=resolve);
const slow=createMarketDataHub({now:()=>instant,adapters:{eodhd:async (cik,date)=>{
  started++;await wait;return fixture(cik,date);
}},maxConcurrent:1});
const a=slow.getPriceContext(args), b=slow.getPriceContext(args);
await assert.rejects(slow.getPriceContext({cik:MSFT,filingDate:"2026-10-20"}),/provider-busy/);
assert.equal(started,1);
assert.equal(slow.health().inFlight,1);
held();
const [aResult,bResult]=await Promise.all([a,b]);
assert.equal(aResult.hub.state,"FETCHED");
assert.equal(bResult.hub.state,"SHARED");
assert.equal(slow.health().inFlight,0);
assert.equal(started,1);

const tiny=createMarketDataHub({now:()=>instant,maxEntries:2,adapters:{eodhd:async (c,d)=>{
  return fixture(c,d);
}}});
await tiny.getPriceContext(args);
await tiny.getPriceContext({cik:MSFT,filingDate:"2026-10-20"});
await tiny.getPriceContext({cik:NVDA,filingDate:"2026-10-20"});
assert.equal(tiny.health().cacheEntries,2);

let errors=0;
const broken=createMarketDataHub({now:()=>instant,adapters:{eodhd:async (c,d)=>{
  errors++;if(errors===1)throw new Error("provider-key-required");
  return {...fixture(c,d),source:"wrong-source"};
}}});
await assert.rejects(broken.getPriceContext(args),/provider-key-required/);
await assert.rejects(broken.getPriceContext(args),/invalid-provider-snapshot/);
assert.equal(broken.health().cacheEntries,0);
assert.equal(errors,2);
await assert.rejects(Promise.resolve().then(()=>createMarketDataHub({
  adapters:{eodhd:async()=>null,unreviewed:async()=>null}
})),/invalid-selection/);

console.log("Finance market-data hub M7 TTL, issuer separation, single-flight and fail-closed fixtures: PASS");
