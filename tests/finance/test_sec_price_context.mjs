#!/usr/bin/env node
// Fictional daily prices: offline, injected HTTP, no EODHD or SEC contact.
import assert from "node:assert/strict";
import {normalizePrices,loadPrices,SYMBOLS} from "../../scripts/finance/read_sec_price_context.mjs";
const cic="0000320193";
const bars=[
 {date:"2026-10-19",open:200,close:200,adjusted_close:199.5},
 {date:"2026-10-20",open:202,close:201,adjusted_close:200.5},
 {date:"2026-10-21",open:203,close:204,adjusted_close:203.5},
 {date:"2026-10-23",open:199,close:198,adjusted_close:197.5},
]; // 22nd has no row (e.g. holiday); don't fabricate a trading day.
const data=normalizePrices(bars,cic,"2026-10-22","2026-10-24T12:00:00Z");
assert.equal(data.source,"eodhd-eod");
assert.equal(data.symbol,"AAPL.US");
assert.equal(data.priceBasis,"ADJUSTED CLOSE");
assert.equal(data.previous.date,"2026-10-21");
assert.equal(data.next.date,"2026-10-23");
assert.equal(data.filingDay,null);
assert.equal(data.changePct,-2.95);
assert.equal(data.bars.length,4);
const sameDay=normalizePrices(bars,cic,"2026-10-21","now");
assert.equal(sameDay.previous.date,"2026-10-20");
assert.equal(sameDay.filingDay.date,"2026-10-21");
assert.equal(sameDay.next.date,"2026-10-23");
// Both price points must use the same basis if one day's adjustment is absent.
const mixed=normalizePrices(bars.map((x,i)=>({
  ...x,adjusted_close:i===1?null:x.adjusted_close
})),cic,"2026-10-22","now");
assert.equal(mixed.priceBasis,"CLOSE");
assert.equal(mixed.previous.price,204);
assert.equal(mixed.next.price,198);
const noAfter=normalizePrices(bars.slice(0,2),cic,"2026-10-22","now");
assert.equal(noAfter.next,null);
assert.equal(noAfter.changePct,null);
assert.throws(()=>normalizePrices([],cic,"2026-10-22","now"),/invalid-price-data/);
assert.throws(()=>normalizePrices(bars,cic,"2026-02-30","now"),/invalid-price-data/);
assert.throws(()=>normalizePrices([...bars,bars[0]],cic,"2026-10-22","now"),/invalid-price-data/);
assert.throws(()=>normalizePrices([{date:"2026-09-01",close:1}],cic,"2026-10-22","now"),/invalid-price-data/);
assert.throws(()=>normalizePrices([{date:"2026-10-22",close:-1}],cic,"2026-10-22","now"),/invalid-price-data/);
assert.equal(SYMBOLS["0001045810"],"NVDA.US");

let calls=0;
const http=async (url,options)=>{
  calls++;
  const u=new URL(url);
  assert.equal(u.hostname,"eodhd.com");
  assert.equal(u.pathname,"/api/eod/AAPL.US");
  assert.equal(u.searchParams.get("api_token"),"demo");
  assert.equal(u.searchParams.get("from"),"2026-10-12");
  assert.equal(u.searchParams.get("to"),"2026-10-24");
  assert.equal(options.method,"GET");
  return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(bars)};
};
const response=await loadPrices(cic,"2026-10-22",http,async()=>null,"2026-10-24");
assert.equal(response.previous.date,"2026-10-21");
assert.equal(calls,1);
await assert.rejects(loadPrices("0000789019","2026-10-22",
  async()=>{calls++},async()=>null,"2026-10-24"),/provider-key-required/);
assert.equal(calls,1);
await assert.rejects(loadPrices(cic,"2026-10-25",
  async()=>{calls++},async()=>null,"2026-10-24"),/invalid-selection/);
assert.equal(calls,1);
await assert.rejects(loadPrices("invalid","2026-10-22",
  async()=>{calls++},async()=>null,"2026-10-24"),/invalid-selection/);
assert.equal(calls,1);
const msft=await loadPrices("0000789019","2026-10-22",
  async(url)=>{calls++;assert.ok(url.includes("MSFT.US"));assert.ok(url.includes("api_token=private_example_token"));
    return {ok:true,headers:{get:()=>null},text:async()=>JSON.stringify(bars)};},
  async()=> "private_example_token","2026-10-24");
assert.equal(msft.symbol,"MSFT.US");
assert.equal(calls,2);
await assert.rejects(loadPrices(cic,"2026-10-22",
  async()=>({ok:false,headers:{get:()=>null}}),async()=>null,"2026-10-24"),/provider-unavailable/);
console.log("Finance SEC M5 fictional market date alignment and provider access: PASS");
