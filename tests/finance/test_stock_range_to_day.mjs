#!/usr/bin/env node
// M13 fake-only; tests one exact returned RANGE bar transferred into DAY.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const js=readFileSync(new URL("../../widgets/FinanceStockModePolicy.js",import.meta.url),"utf8");
const policy=vm.runInNewContext(js+"\n({daySnapshotFromRange,daySession,selectWindow})");
const cik="0000320193", symbol="AAPL.US";
const from="2026-10-20", to="2026-10-22";
const source={
  schemaVersion:1,source:"eodhd-eod",readOnly:true,cik,symbol,
  from,to,priceBasis:"ADJUSTED CLOSE",retrievedAt:"2026-10-26T13:00:00.000Z",
  changePct:10,
  first:{date:from,price:100},last:{date:to,price:110},
  bars:[{date:from,price:100},{date:"2026-10-21",price:107.21},
    {date:to,price:110}],
  delivery:{via:"HUB",state:"CACHED",cachedAt:"2026-10-26T12:58:00.000Z",
    servedAt:"2026-10-26T13:00:00.000Z",
    expiresAt:"2026-10-26T14:58:00.000Z",ageSeconds:120}
};
const chosen=policy.daySnapshotFromRange(source,1,cik,from,to);
assert.ok(chosen);
assert.equal(chosen.from,"2026-10-21");
assert.equal(chosen.to,"2026-10-21");
assert.equal(chosen.cik,cik);
assert.equal(chosen.symbol,symbol);
assert.equal(chosen.source,"eodhd-eod");
assert.equal(chosen.priceBasis,"ADJUSTED CLOSE");
assert.equal(chosen.readOnly,true);
assert.equal(chosen.derivedFromRange,true);
assert.deepEqual(JSON.parse(JSON.stringify(chosen.originRange)),{from,to});
assert.equal(chosen.delivery.via,"HUB");
assert.equal(chosen.delivery.state,"CACHED");
assert.equal(chosen.delivery.cachedAt,source.delivery.cachedAt);
assert.equal(chosen.delivery.servedAt,source.delivery.servedAt);
assert.equal(chosen.changePct,null);
assert.equal(chosen.bars.length,1);
assert.equal(chosen.bars[0].date,"2026-10-21");
assert.equal(chosen.bars[0].price,107.21);
assert.equal(policy.daySession(chosen,"2026-10-21").state,"session");
assert.equal(policy.daySession(chosen,"2026-10-21").close,107.21);
assert.equal(policy.selectWindow("day",chosen.from,from,to,"2026-10-26").to,chosen.to);
assert.equal(policy.selectWindow("range",chosen.from,from,to,"2026-10-26").from,from);
// Mutation of the derived handoff must never overwrite loaded RANGE bars or
// its provenance, even if a downstream QML view changes its local snapshot.
chosen.bars[0].price=999;
chosen.delivery.servedAt="tampered";
chosen.originRange.from="tampered";
assert.equal(source.bars[1].price,107.21);
assert.equal(source.delivery.servedAt,"2026-10-26T13:00:00.000Z");
assert.equal(source.from,from);
// Each source bar can be deliberately opened, including the first & last.
for(const index of [0,2]){
  const d=policy.daySnapshotFromRange(source,index,cik,from,to);
  assert.ok(d);
  assert.equal(d.from,source.bars[index].date);
  assert.equal(d.bars[0].price,source.bars[index].price);
  assert.equal(d.changePct,null);
}
// No nearby date is fabricated; invalid issuer, date, point, source, provenance
// or a one-bar RANGE cannot be carried to DAY.
for(const index of [-1,1.5,3,NaN,null]){
  assert.equal(policy.daySnapshotFromRange(source,index,cik,from,to),null);
}
assert.equal(policy.daySnapshotFromRange(source,1,"0000789019",from,to),null);
assert.equal(policy.daySnapshotFromRange(source,1,cik,"2026-10-19",to),null);
assert.equal(policy.daySnapshotFromRange(source,1,cik,from,"2026-10-23"),null);
assert.equal(policy.daySnapshotFromRange({...source,source:"unknown"},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,readOnly:false},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,symbol:"MSFT.US"},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,priceBasis:"MIXED"},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,bars:[source.bars[0]]},0,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,bars:[
  {...source.bars[0]},{date:"2026-10-25",price:120},source.bars[2]
]},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,delivery:null},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,delivery:{
  ...source.delivery,via:"HUB",cachedAt:null
}},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,delivery:{
  ...source.delivery,via:"DIRECT",state:"CACHED"
}},1,cik,from,to),null);
assert.equal(policy.daySnapshotFromRange({...source,delivery:{
  ...source.delivery,via:"DIRECT",state:"DIRECT",cachedAt:null
}},1,cik,from,to).delivery.state,"DIRECT");
console.log("Finance M13 exact RANGE-session to DAY no-fetch handoff fixtures: PASS");
