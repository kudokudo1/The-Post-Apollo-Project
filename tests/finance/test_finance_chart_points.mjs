#!/usr/bin/env node
// Pure JS selection of returned daily sessions. Does not contact EODHD/hub.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const script=readFileSync(
  new URL("../../widgets/FinanceStockChartPointPolicy.js", import.meta.url), "utf8");
const policy=vm.runInNewContext(script+"\n({pointAt,nearestPoint,selectedBar})");
const series=[
  {date:"2026-10-20",price:100},
  {date:"2026-10-21",price:150},
  {date:"2026-10-22",price:200}
];
const width=101,height=81;
function coords(index,bars=series,w=width,h=height) {
  return policy.pointAt(bars,w,h,index);
}
const first=coords(0),middle=coords(1),last=coords(2);
assert.deepEqual([first.x,first.y],[0,80]);
assert.deepEqual([middle.x,middle.y],[50,40]);
assert.deepEqual([last.x,last.y],[100,0]);
assert.equal(policy.nearestPoint(series,width,height,1,79,18),0);
assert.equal(policy.nearestPoint(series,width,height,50,41,18),1);
assert.equal(policy.nearestPoint(series,width,height,100,1,18),2);
assert.equal(policy.nearestPoint(series,width,height,50,80,18),-1);
assert.equal(policy.nearestPoint(series,width,height,50,41,0),-1);
assert.equal(policy.nearestPoint(series,width,height,-1,20,18),-1);
assert.equal(policy.nearestPoint(series,width,height,102,20,18),-1);
assert.equal(policy.nearestPoint(series,width,height,40,NaN,18),-1);
assert.equal(policy.nearestPoint(series,0,height,4,2,18),-1);
assert.equal(policy.pointAt(series,4,80,0),null);
assert.equal(policy.pointAt(series,101,80,3),null);
assert.equal(policy.pointAt([],101,80,0),null);
assert.equal(policy.pointAt([{date:"2026-10-21",price:100}],101,80,0),null);
assert.equal(policy.pointAt([...series,{date:"2026-10-23",price:Infinity}],101,80,0),null);

// Selected value must come from exact provider-returned row, not interpolated.
const chosen=policy.selectedBar(series,1);
assert.equal(chosen.date,"2026-10-21");
assert.equal(chosen.price,150);
assert.equal(chosen.index,1);
chosen.price=777;
assert.equal(series[1].price,150); // copy, not mutable source.
assert.equal(policy.selectedBar(series,-1),null);
assert.equal(policy.selectedBar(series,3),null);
assert.equal(policy.selectedBar(series,1.5),null);
assert.equal(policy.selectedBar([],0),null);
assert.equal(policy.selectedBar([{date:"2026-02-29",price:0}],0),null);

// Flat-price windows should show a horizontal line and stable hit geometry.
const flat=[
  {date:"2026-10-20",price:123},
  {date:"2026-10-21",price:123}
];
assert.deepEqual([coords(0,flat).x,coords(0,flat).y],[0,80]);
assert.deepEqual([coords(1,flat).x,coords(1,flat).y],[100,80]);
assert.equal(policy.nearestPoint(flat,101,81,100,79,18),1);

// Test dense 132-bar range and narrow compact width: select *actual* row
// based on both x and y, no invented weekend points or date estimates.
const dense=Array.from({length:132},(_,i)=>({
  date:"2026-01-"+String(i+1).padStart(2,"0"),price:90+(i%16)*2
}));
const compactWidth=244,compactHeight=156;
for(const index of [0,13,48,97,131]){
  const pos=coords(index,dense,compactWidth,compactHeight);
  assert.ok(pos);
  assert.equal(policy.nearestPoint(dense,compactWidth,compactHeight,
    pos.x,pos.y,0.5),index);
}
const narrow=coords(97,dense,compactWidth,compactHeight);
assert.equal(policy.selectedBar(dense,
  policy.nearestPoint(dense,compactWidth,compactHeight,
    narrow.x,narrow.y,0.5)).price,dense[97].price);
console.log("Finance M12 actual chart-point hit testing and session selection fixtures: PASS");
