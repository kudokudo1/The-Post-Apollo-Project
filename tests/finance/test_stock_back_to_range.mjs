#!/usr/bin/env node
// M14 fictional sessions; no external provider, local HTTP or workspace writes.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const src=readFileSync(new URL("../../widgets/FinanceStockModePolicy.js",import.meta.url),"utf8");
const policy=vm.runInNewContext(src+
  "\n({rangeReturnTicket,rangeFromReturnTicket,daySnapshotFromRange,selectWindow})");
const cik="0000320193",from="2026-10-20",to="2026-10-23",selected=1;
const range={
  schemaVersion:1,source:"eodhd-eod",readOnly:true,cik,symbol:"AAPL.US",
  from,to,priceBasis:"ADJUSTED CLOSE",retrievedAt:"2026-10-26T14:00:00.000Z",
  changePct:10,first:{date:from,price:100},last:{date:to,price:110},
  bars:[{date:from,price:100},{date:"2026-10-21",price:105.25},
    {date:"2026-10-22",price:107},{date:to,price:110}],
  delivery:{via:"HUB",state:"CACHED",cachedAt:"2026-10-26T13:58:00.000Z",
    servedAt:"2026-10-26T14:00:00.000Z",
    expiresAt:"2026-10-26T14:58:00.000Z",ageSeconds:120}
};
const day=policy.daySnapshotFromRange(range,selected,cik,from,to);
assert.ok(day);
const ticket=policy.rangeReturnTicket(range,selected,cik,from,to);
assert.ok(ticket);
assert.equal(ticket.openedDay,"2026-10-21");
assert.equal(ticket.openedPrice,105.25);
assert.equal(ticket.index,selected);
assert.equal(ticket.cik,cik);
assert.equal(ticket.from,from);
assert.equal(ticket.to,to);
const restored=policy.rangeFromReturnTicket(ticket,day,cik,from,to);
assert.ok(restored);
assert.equal(restored.restoredFromDay,true);
assert.equal(restored.returnedFromDay,"2026-10-21");
assert.equal(restored.from,from);
assert.equal(restored.to,to);
assert.equal(restored.symbol,"AAPL.US");
assert.equal(restored.priceBasis,"ADJUSTED CLOSE");
assert.equal(restored.bars.length,4);
assert.equal(restored.bars[1].price,105.25);
assert.equal(restored.changePct,10);
assert.equal(restored.delivery.cachedAt,range.delivery.cachedAt);
assert.equal(restored.delivery.servedAt,range.delivery.servedAt);
assert.equal(restored.delivery.state,"CACHED");
assert.equal(restored.source,"eodhd-eod");
assert.equal(restored.readOnly,true);
// Opening DAY never mutates the saved RANGE dates; restoring does not fetch,
// infer extra sessions, substitute a quote or rewrite provider provenance.
assert.equal(policy.selectWindow("range",day.from,from,to,"2026-10-26").from,from);
assert.equal(policy.selectWindow("range",day.from,from,to,"2026-10-26").to,to);
restored.bars[1].price=9999;
restored.delivery.servedAt="tampered";
ticket.snapshot.bars[2].price=2222; // independent source and returned result
assert.equal(range.bars[1].price,105.25);
assert.equal(range.bars[2].price,107);
assert.equal(range.delivery.servedAt,"2026-10-26T14:00:00.000Z");
assert.equal(restored.bars[2].price,107);
assert.equal(day.bars[0].price,105.25);
// Work with a clean ticket for validation rejections.
const fresh=()=>policy.rangeReturnTicket(range,selected,cik,from,to);
const editDay=(patch)=>Object.assign({},day,patch);
assert.equal(policy.rangeFromReturnTicket(null,day,cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),day,"0000789019",from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),day,cik,"2026-10-19",to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),day,cik,from,"2026-10-24"),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({derivedFromRange:false}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({from:"2026-10-22"}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({symbol:"MSFT.US"}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({readOnly:false}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({source:"unknown"}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({
  originRange:{from:"2026-10-19",to}
}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({bars:[{
  date:"2026-10-21",price:107
}]}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({delivery:{
  ...day.delivery,state:"FETCHED"
}}),cik,from,to),null);
assert.equal(policy.rangeFromReturnTicket(fresh(),editDay({delivery:{
  ...day.delivery,cachedAt:"2026-10-26T11:00:00.000Z"
}}),cik,from,to),null);
const altered=fresh();
altered.snapshot.bars[0].price=-1;
assert.equal(policy.rangeFromReturnTicket(altered,day,cik,from,to),null);
const misordered=fresh();
misordered.snapshot.bars[1].date=misordered.snapshot.bars[0].date;
assert.equal(policy.rangeFromReturnTicket(misordered,day,cik,from,to),null);
const replaced=fresh();
replaced.snapshot.bars[1].price=999;
assert.equal(policy.rangeFromReturnTicket(replaced,day,cik,from,to),null);
assert.equal(policy.rangeReturnTicket({...range,source:"unknown"},selected,cik,from,to),null);
assert.equal(policy.rangeReturnTicket({...range,bars:[range.bars[0]]},0,cik,from,to),null);
console.log("Finance M14 bounded in-memory RANGE restoration and source-guard fixtures: PASS");
