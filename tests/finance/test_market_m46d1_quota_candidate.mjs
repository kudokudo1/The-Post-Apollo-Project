import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createRangeQuotaCandidate} from "../../scripts/finance/market_range_quota_candidate.mjs";
import {createMarketDataHub} from "../../scripts/finance/market_data_hub.mjs";
import {createMarketDataServer} from "../../scripts/finance/market_data_server.mjs";
import {readOptionalRange} from "../../scripts/finance/read_market_price_range_optional_hub.mjs";
import {quotaFetcher} from "../../scripts/finance/market_shared_quota.mjs";
const a="0000320193",b="0000789019",n="0001045810",from="2026-10-01",to="2026-10-20";
let stamp=Date.parse("2026-10-24T12:00:00Z"),attempts=0,upstreamCalls=0,secCalls=0,token="FAKE",denial="";
const reserve=provider=>{
 assert.equal(provider,"eodhd");
 if(denial)throw new Error(denial);
 return {provider,reserved:++attempts};
};
const upstream=async url=>{
 assert.equal(new URL(url).hostname,"eodhd.com");
 upstreamCalls++;
 return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify([{date:to,close:123}])};
};
const now=()=>new Date(stamp).toISOString();
assert.throws(()=>createRangeQuotaCandidate(),/dependencies-required/);
const rangeAdapter=createRangeQuotaCandidate({upstream,reserver:reserve,tokenLoader:async()=>token,today:()=>now().slice(0,10)});
await assert.rejects(rangeAdapter(a,"2026-02-30",to),/invalid-range/);
token=null;await assert.rejects(rangeAdapter(n,from,to),/provider-key-required/);
assert.equal(attempts,0);assert.equal(upstreamCalls,0);token="FAKE";
const hub=createMarketDataHub({now:()=>stamp,rangeAdapter,adapters:{eodhd:async()=>{
 secCalls++;throw new Error("local-quota-exhausted");
}}});
const global=quotaFetcher("eodhd",upstream,reserve);
await global.fetcher("https://eodhd.com/fixture");
const [f,s]=await Promise.all([hub.getPriceRange({cik:a,from,to}),hub.getPriceRange({cik:a,from,to})]);
assert.equal(f.hub.state,"FETCHED");assert.equal(s.hub.state,"SHARED");
assert.equal(attempts,2);assert.equal(upstreamCalls,2);
const server=createMarketDataServer({hub});
await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(0,"127.0.0.1",resolve);});
try{
 const opts={port:server.address().port,now,directReader:async()=>{throw new Error("DIRECT BYPASS");}};
 denial="local-quota-exhausted";
 assert.equal((await readOptionalRange(a,from,to,opts)).delivery.state,"CACHED");
 await assert.rejects(readOptionalRange(b,from,to,opts),/local-quota-exhausted/);
 denial="local-quota-unavailable";
 await assert.rejects(readOptionalRange(b,from,to,opts),/local-quota-unavailable/);
 assert.equal(attempts,2);assert.equal(upstreamCalls,2);
 assert.equal(hub.health().inFlight,0);
 // SEC error normalization stays unchanged, even with the same error text.
 await assert.rejects(hub.getPriceContext({cik:a,filingDate:to}),/provider-failed/);
 assert.equal(secCalls,1);
 stamp+=2*86400000;
 await assert.rejects(readOptionalRange(a,from,to,opts),/local-quota-unavailable/);
 assert.equal(hub.health().cacheEntries,0);
 denial="";
 assert.equal((await readOptionalRange(a,from,to,opts)).delivery.state,"FETCHED");
 assert.equal(attempts,3);assert.equal(upstreamCalls,3);
}finally{await new Promise((resolve,reject)=>server.close(e=>e?reject(e):resolve()));}
// Direct absent-hub path uses the exact same injected adapter, never double charges.
const refused=async()=>{const e=new Error("refused");e.code="ECONNREFUSED";throw e;};
const opts={fetcher:refused,directReader:rangeAdapter,now};
denial="local-quota-exhausted";
await assert.rejects(readOptionalRange(a,from,to,opts),/local-quota-exhausted/);
assert.equal(attempts,3);assert.equal(upstreamCalls,3);
denial="";
assert.equal((await readOptionalRange(a,from,to,opts)).delivery.state,"DIRECT");
assert.equal(attempts,4);assert.equal(upstreamCalls,4);
// No production import, selection or default reservation activation.
for(const path of ["market_data_hub.mjs","market_data_server.mjs","read_market_price_range.mjs","read_market_price_range_optional_hub.mjs"]){
 const src=readFileSync(new URL("../../scripts/finance/"+path,import.meta.url),"utf8");
 assert.ok(!src.includes("market_range_quota_candidate.mjs"),path);
 assert.ok(!src.includes("reserveLocal("),path);
}
console.log("M46d1 staged shared quota range adapter, typed refusal, cache, direct/hub and SEC isolation: PASS");
