#!/usr/bin/env node
// All tests use fictional markets and an injected fetcher. No network is called.
import assert from "node:assert/strict";
import { normalizeMarket, normalizePayload, loadMarkets } from "../../scripts/finance/read_polymarket.mjs";

const sample = {
  id: "1234", active: true, closed: false,
  question: "Will an imaginary event happen?",
  outcomes: '["No","Yes"]', outcomePrices: '["0.375","0.625"]',
  volume24hr: "13500.75", liquidityNum: "2481.9",
  oneDayPriceChange: "0.035"
};
const m = normalizeMarket(sample);
assert.equal(m.yesPct, 62.5); // outcomes can arrive No/Yes, never guess order
assert.equal(m.noPct, 37.5);
assert.equal(m.volume24h, 13501);
assert.equal(m.change24hPct, 3.5);
assert.equal(m.question, sample.question);
assert.equal(normalizeMarket({...sample, active:false}), null);
assert.equal(normalizeMarket({...sample, closed:true}), null);
assert.equal(normalizeMarket({...sample, outcomePrices:'["999","0.1"]'}), null);
assert.equal(normalizeMarket({...sample, outcomes:"not-json"}), null);
assert.equal(normalizeMarket({...sample, question:""}), null);
assert.equal(normalizeMarket({...sample, id:"evil"}), null);
assert.equal(normalizeMarket({...sample, volume24hr:"n/a", liquidity:null}).volume24h, null);
const payload = normalizePayload([
  {...sample, id:"1234", volume24hr:"10"},
  {...sample, id:"1235", volume24hr:"999"},
  {...sample, id:"1234", volume24hr:"10000"}, // duplicate ID ignored
  {...sample, id:"1236", active:false}
], "2026-10-24T15:00:00.000Z");
assert.equal(payload.source,"polymarket-gamma");
assert.equal(payload.readOnly,true);
assert.deepEqual(payload.markets.map(x=>x.id), ["1235","1234"]);
assert.equal(payload.markets.length, 2);
const calls = [];
const loaded = await loadMarkets(async (url, opts) => {
  calls.push({url,opts});
  return {ok:true,json:async()=>[sample]};
});
assert.equal(calls.length, 1);
assert.equal(calls[0].opts.method, "GET");
assert.equal(new URL(calls[0].url).host,"gamma-api.polymarket.com");
assert.equal(loaded.markets[0].yesPct,62.5);
await assert.rejects(loadMarkets(async()=>({ok:false})),/upstream-unavailable/);
assert.throws(()=>normalizePayload({markets:[]},new Date().toISOString()),/invalid-feed/);
console.log("FinanceW Market M1 fictional Polymarket fixture tests: PASS");
