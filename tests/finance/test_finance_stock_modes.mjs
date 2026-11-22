#!/usr/bin/env node
// Pure source-selection fixtures with fictional daily bars, no outside fetch.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
import {normalizePriceRange,validateRange}
  from "../../scripts/finance/read_market_price_range.mjs";

const src=readFileSync(new URL("../../widgets/FinanceStockModePolicy.js",import.meta.url),"utf8");
const scope=vm.createContext({});
const policy=vm.runInContext(src+"\n({calendarDay,selectWindow,presetWindow,daySession})",scope);
const today="2026-10-24";
const w=(mode,day,start,end)=>policy.selectWindow(mode,day,start,end,today);
const day=w("day","2026-10-21","2026-09-01","2026-10-01");
assert.equal(day.kind,"day");
assert.equal(day.from,"2026-10-21");
assert.equal(day.to,"2026-10-21");
assert.deepEqual(validateRange("0000320193",day.from,day.to,today),{
  cik:"0000320193",from:"2026-10-21",to:"2026-10-21"
});
const range=w("range","2026-10-21","2026-09-01","2026-10-01");
assert.equal(range.kind,"range");
assert.equal(range.from,"2026-09-01");
assert.equal(range.to,"2026-10-01");
// DAY does not overwrite RANGE dates or vice versa.
assert.equal(w("day","2026-10-22",range.from,range.to).from,"2026-10-22");
assert.equal(w("range","2026-10-22",range.from,range.to).from,"2026-09-01");
assert.equal(w("day","2026-02-30",range.from,range.to),null);
assert.equal(w("day","2026-10-25",range.from,range.to),null);
assert.equal(w("day","1999-12-31",range.from,range.to),null);
assert.equal(w("other","2026-10-21",range.from,range.to),null);
assert.equal(w("range","2026-10-21","2026-10-22","2026-10-21"),null);
assert.equal(w("range","2026-10-21","2026-04-01","2026-10-24"),null);
assert.equal(policy.calendarDay("2026-02-30"),null);
assert.notEqual(policy.calendarDay("2024-02-29"),null);

// M15 quick calendar windows end today, are inclusive and never exceed 180.
for (const count of [7,30,90,180]) {
  const preset=policy.presetWindow(count,today);
  assert.equal(preset.kind,"range");
  assert.equal(preset.to,today);
  assert.equal(policy.calendarDay(preset.to)-policy.calendarDay(preset.from)+1,count);
  assert.deepEqual(validateRange("0000320193",preset.from,preset.to,today),{
    cik:"0000320193",from:preset.from,to:preset.to
  });
}
assert.equal(policy.presetWindow(7,today).from,"2026-10-18");
assert.equal(policy.presetWindow(181,today),null);
assert.equal(policy.presetWindow(0,today),null);
assert.equal(policy.presetWindow("7",today),null);
assert.equal(policy.presetWindow(30,"not-a-date"),null);
assert.equal(policy.presetWindow(7,"2000-01-01"),null);
assert.equal(policy.presetWindow(7,"2000-01-07").from,"2000-01-01");
assert.equal(policy.presetWindow(7,"2024-03-01").from,"2024-02-24");

const readSource=relative=>readFileSync(new URL(relative,import.meta.url),"utf8");
const marketService=readSource("../../services/finance/FinanceStockHistoryReadService.qml");
const stocksPane=readSource("../../widgets/FinanceStockHistoryPane.qml");
const presetHandler=marketService.split("function selectPresetRange(days) {")[1]
  ?.split("function selectDayDate(day) {")[0];
assert.ok(presetHandler,"M15 source handler must exist");
assert.match(presetHandler,/!monitoring.*displayMode !== "range".*loading.*reader.running/);
assert.match(presetHandler,/StockModePolicy.presetWindow\(days, dateOffset\(0\)\)/);
assert.match(presetHandler,/startDate = window.from;/);
assert.match(presetHandler,/endDate = window.to;/);
assert.match(presetHandler,/clear\(\);/);
assert.doesNotMatch(presetHandler,/reader.exec|refresh\(|writeFile|Qt.openUrlExternally/);
for (const label of ["7D","30D","90D","180D"])
  assert.ok(stocksPane.includes('label:"'+label+'"'));
assert.ok(stocksPane.includes("stocks.stockFeed.selectPresetRange(modelData.days)"));
assert.ok(stocksPane.includes("visible: !stocks.dayMode"));
assert.equal((marketService.match(/reader.exec\(\[/g)||[]).length,1);

// Provider returns real session row only. No weekend/holiday approximation.
const cik="0000320193";
const session=normalizePriceRange(
  [{date:"2026-10-21",close:123.45,adjusted_close:122.7}],
  cik,"2026-10-21","2026-10-21","2026-10-24T00:00:00Z");
assert.equal(session.bars.length,1);
assert.equal(session.changePct,null);
const found=policy.daySession(session,"2026-10-21");
assert.equal(found.state,"session");
assert.equal(found.close,122.7);
const weekend=normalizePriceRange(
  [],cik,"2026-10-24","2026-10-24","2026-10-24T00:00:00Z");
assert.equal(weekend.bars.length,0);
assert.equal(policy.daySession(weekend,"2026-10-24").state,"no-session");
assert.equal(policy.daySession(weekend,"2026-10-21").state,"invalid");
assert.equal(policy.daySession(session,"2026-10-22").state,"invalid");
assert.equal(policy.daySession({...session,bars:[
  {date:"2026-10-21",price:122.7},{date:"2026-10-21",price:123}
]},"2026-10-21").state,"invalid");
console.log("Finance M11 DAY/RANGE selector, single-session and no-session fixtures: PASS");
