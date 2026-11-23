#!/usr/bin/env node
// M20: fictional, no external key/provider, no host FinanceW quota file writes.
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {
  parseReservation,reserveLocal,quotaFetcher
} from "../../scripts/finance/market_shared_quota.mjs";

const day="2026-11-23";
const payload=(provider,limit,count)=>({
  schemaVersion:1,scope:"post-apollo-market-local-v1",
  provider,utcDay:day,reserved:count,limit,notAccountBalance:true
});
const line=(provider,limit,count)=>
  "FINANCE_LOCAL_QUOTA "+JSON.stringify(payload(provider,limit,count))+"\n";
assert.deepEqual(parseReservation(line("eodhd",20,1),"eodhd"),
  payload("eodhd",20,1));
assert.deepEqual(parseReservation(line("alpha-vantage",25,25),"alpha-vantage"),
  payload("alpha-vantage",25,25));
for(const bad of [
  "FINANCE_LOCAL_QUOTA not-json",
  "FINANCE_LOCAL_QUOTA "+JSON.stringify({...payload("eodhd",20,2),reserved:21}),
  "FINANCE_LOCAL_QUOTA "+JSON.stringify({...payload("eodhd",20,2),notAccountBalance:false}),
  "FINANCE_LOCAL_QUOTA "+JSON.stringify({...payload("eodhd",20,2),provider:"alpha-vantage"}),
  "FINANCE_LOCAL_QUOTA "+JSON.stringify({...payload("eodhd",20,2),utcDay:"2026-02-30"}),
  "FINANCE_LOCAL_QUOTA "+JSON.stringify({...payload("eodhd",20,2),scope:"account-quota"}),
  "FINANCE_LOCAL_QUOTA_ERROR local-quota-unavailable"
])assert.throws(()=>parseReservation(bad,"eodhd"),/local-quota-unavailable/);
assert.throws(()=>parseReservation(
  "FINANCE_LOCAL_QUOTA_ERROR local-quota-exhausted","eodhd"),
  /local-quota-exhausted/);
let requested=0;
const fauxRunner=(exe,args,options)=>{
  requested++;
  assert.equal(exe,"/usr/bin/env");
  assert.equal(args[0],"python3");
  assert.ok(args[1].endsWith("/market_shared_quota.py"));
  assert.equal(args[2],"reserve");
  assert.equal(args[3],"eodhd");
  assert.equal(options.timeout,6000);
  assert.equal(options.maxBuffer,2048);
  return line("eodhd",20,1);
};
assert.equal(reserveLocal("eodhd",fauxRunner).reserved,1);
assert.equal(requested,1);
assert.throws(()=>reserveLocal("unknown",fauxRunner),/local-quota-unavailable/);
assert.equal(requested,1);
assert.throws(()=>reserveLocal("eodhd",()=>{throw {
  stdout:"FINANCE_LOCAL_QUOTA_ERROR local-quota-exhausted\n"
};}),/local-quota-exhausted/);
assert.throws(()=>reserveLocal("eodhd",()=>{throw {
  stderr:"storage failed"
};}),/local-quota-unavailable/);
let network=0,reserved=0;
const transport=quotaFetcher("alpha-vantage",
  async()=>{network++;return {ok:true};},
  name=>{
    reserved++;
    assert.equal(name,"alpha-vantage");
    return payload(name,25,reserved);
  });
assert.equal(transport.latest(),null);
await transport.fetcher("https://example.invalid/");
assert.equal(network,1);
assert.equal(reserved,1);
assert.equal(transport.latest().notAccountBalance,true);
await transport.fetcher("https://example.invalid/");
assert.equal(network,2);
assert.equal(transport.latest().reserved,2);
const denied=quotaFetcher("eodhd",async()=>{
  throw Error("network must not run");
},()=>{throw Error("local-quota-exhausted");});
await assert.rejects(denied.fetcher("https://example.invalid/"),
  /local-quota-exhausted/);
assert.equal(denied.latest(),null);

const read=relative=>readFileSync(new URL(relative,import.meta.url),"utf8");
const eod=read("../../scripts/finance/read_global_eodhd_history.mjs");
const alpha=read("../../scripts/finance/read_alpha_vantage_free.mjs");
const eodService=read("../../services/finance/FinanceGlobalPriceService.qml");
const avService=read("../../services/finance/FinanceAlphaVantageFreeService.qml");
const eodUi=read("../../widgets/FinanceGlobalPricePane.qml");
const avUi=read("../../widgets/FinanceAlphaVantageFreePane.qml");
const ledger=read("../../scripts/finance/market_shared_quota.py");
assert.ok(eod.includes('const local=quotaFetcher("eodhd");'));
assert.ok(alpha.includes('const local=quotaFetcher("alpha-vantage");'));
for(const src of [eod,alpha]) {
  assert.ok(src.includes('if(local.latest())result.localQuota=local.latest();'));
  assert.ok(src.includes('"local-quota-exhausted","local-quota-unavailable"'));
  assert.ok(src.includes('error?.message==="local-quota-exhausted"'));
}
for(const [src,provider,limit]of [
  [eodService,"eodhd",20],[avService,"alpha-vantage",25]
]){
  assert.ok(src.includes('property var sharedQuota: null'));
  assert.ok(src.includes('data.localQuota.provider!=="'+provider+'"'));
  assert.ok(src.includes("data.localQuota.limit!=="+limit));
  assert.ok(src.includes('data.localQuota.notAccountBalance!==true'));
  assert.ok(src.includes('sharedQuota=data.localQuota;'));
  assert.ok(src.includes('LOCAL QUOTA STORAGE UNSAFE OR UNAVAILABLE'));
}
for(const ui of [eodUi,avUi]){
  assert.ok(ui.includes('LOCAL SHARED RESERVED'));
  assert.ok(ui.includes('NOT ACCOUNT'));
}
assert.ok(ledger.includes("BEGIN IMMEDIATE"));
assert.ok(ledger.includes("ON CONFLICT(provider,utc_day) DO UPDATE"));
assert.ok(ledger.includes('getattr(os, "O_NOFOLLOW"'));
assert.ok(ledger.includes("notAccountBalance"));
assert.ok(!ledger.includes("api_token"));
assert.ok(!ledger.includes("apikey"));
assert.equal((ledger.match(/def reserve\(/g)||[]).length,1);
// Executable Python regression operates ONLY in tempfile.TemporaryDirectory.
const python=fileURLToPath(new URL("./test_market_shared_quota.py",import.meta.url));
const output=execFileSync("/usr/bin/env",["python3",python],{
  encoding:"utf8",timeout:25000,maxBuffer:100000
});
assert.match(output,/Finance M20 atomic shared local quota.*PASS/);
console.log("Finance M20 shared reservation reader/response guards, fail-closed quota errors, and UI source contracts: PASS");
