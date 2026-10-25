#!/usr/bin/env node
// Two distinct finance consumers share one hub cache, no upstream HTTP.
// The standalone Market STOCKS view passes a reference date, while SEC passes
// a filing date; cache reuse is valid only when both CIK+date are identical.
import assert from "node:assert/strict";
import {createMarketDataHub} from "../../scripts/finance/market_data_hub.mjs";
import {createMarketDataServer} from "../../scripts/finance/market_data_server.mjs";
import {readOptionalPrice} from "../../scripts/finance/read_sec_price_optional_hub.mjs";

const apple="0000320193", microsoft="0000789019", date="2026-10-20";
const now=Date.parse("2026-10-24T20:00:00.000Z");
const symbols={ [apple]:"AAPL.US", [microsoft]:"MSFT.US" };
const dates={ [date]:["2026-10-19","2026-10-21"],"2026-10-19":["2026-10-18","2026-10-20"]};
let providerCalls=0, directCalls=0;
const hub=createMarketDataHub({
  now:()=>now,
  adapters:{eodhd:async(cik,ref)=>{
    providerCalls++;
    const sessions=dates[ref];
    assert.ok(sessions);
    return {schemaVersion:1,source:"eodhd-eod",readOnly:true,
      cik,symbol:symbols[cik],filingDate:ref,
      retrievedAt:"2026-10-24T18:00:00.000Z",priceBasis:"CLOSE",
      previous:{date:sessions[0],price:100},
      filingDay:null,next:{date:sessions[1],price:105},changePct:5,
      bars:[{date:sessions[0],price:100},{date:sessions[1],price:105}]};
  }}
});
const server=createMarketDataServer({hub});
await new Promise((resolve,reject)=>{
  server.once("error",reject);
  server.listen(0,"127.0.0.1",resolve);
});
try {
  const port=server.address().port;
  const opts={port,now:()=>new Date(now).toISOString(),
    directReader:async()=>{directCalls++;throw new Error("unexpected direct");}};
  const sec=await readOptionalPrice(apple,date,opts);       // SEC inspector
  assert.equal(sec.delivery.via,"HUB");
  assert.equal(sec.delivery.state,"FETCHED");
  const stocks=await readOptionalPrice(apple,date,opts);    // Market STOCKS
  assert.equal(stocks.delivery.state,"CACHED");
  assert.equal(stocks.symbol,"AAPL.US");
  assert.equal(stocks.previous.date,sec.previous.date);
  assert.equal(providerCalls,1); // Real cache shared across consumers.
  assert.equal(directCalls,0);
  const differentDate=await readOptionalPrice(apple,"2026-10-19",opts);
  assert.equal(differentDate.delivery.state,"FETCHED");
  assert.equal(providerCalls,2);
  const otherIssuer=await readOptionalPrice(microsoft,date,opts);
  assert.equal(otherIssuer.delivery.state,"FETCHED");
  assert.equal(otherIssuer.symbol,"MSFT.US");
  assert.equal(providerCalls,3);
  const again=await readOptionalPrice(apple,date,opts);
  assert.equal(again.delivery.state,"CACHED");
  assert.equal(providerCalls,3);
  assert.equal(hub.health().cacheEntries,3);
  assert.equal(hub.health().backgroundPolling,false);
  console.log("Finance M9 SEC and STOCKS same-key cache sharing, issuer/date isolation: PASS");
} finally {
  await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));
}
