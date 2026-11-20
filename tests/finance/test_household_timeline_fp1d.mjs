#!/usr/bin/env node
// Entirely fictional; checks deterministic timeline and event boundaries.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const source=readFileSync(new URL("../../widgets/FinanceHouseholdTimelinePolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(source+"\n({project,indexFor,monthFor})");
const row=(hex,kind,title,targetCents,savedCents,monthlyCents,deadlineMonth="")=>({
    id:"p-"+hex.repeat(32),kind,title,targetCents,savedCents,monthlyCents,deadlineMonth
});
const income=row("a","income","Pay",0,0,300000);
const cost=row("b","expense","Rent",0,0,120000);
const goal=row("c","goal","Car purchase",40000,10000,10000,"2027-02");
const input=[income,cost,goal],before=JSON.stringify(input);
const a=p.project(input,"2026-11",6,"mine");
assert.equal(a.ok,true);
assert.equal(JSON.stringify(input),before);
assert.equal(a.contextId,"mine");
assert.equal(a.source,"LOCAL_MANUAL_TIMELINE_ONLY");
assert.equal(a.readOnly,true);
assert.equal(a.bankVerified,false);
assert.equal(a.identityVerified,false);
assert.equal(a.startingCashKnown,false);
assert.equal(a.futurePurchasesCharged,false);
assert.equal(a.actualTransfersMade,false);
assert.equal(a.months.length,6);
assert.equal(a.months[0].month,"2026-11");
assert.equal(a.months[1].month,"2026-12");
assert.equal(a.months[2].month,"2027-01");
assert.equal(a.months[3].month,"2027-02");
assert.equal(a.months[0].incomeCents,300000);
assert.equal(a.months[0].expenseCents,120000);
assert.equal(a.months[0].contributionCents,10000);
assert.equal(a.months[0].changeCents,170000);
assert.equal(a.months[0].cumulativeChangeCents,170000);
// Goal reaches manual target in month 3, no duplicate money movement or
// fabricated purchase charge in its declared deadline month.
assert.equal(a.months[2].contributionCents,10000);
assert.equal(a.months[3].contributionCents,0);
assert.equal(a.months[3].events.length,1);
assert.equal(a.months[3].events[0].status,"TARGET_FUNDED_IN_MODEL");
assert.equal(a.months[3].events[0].gapCents,0);
assert.equal(a.months[3].changeCents,180000);
const short=p.project([income,cost,{...goal,monthlyCents:2000}],"2026-11",6,"shared");
assert.equal(short.ok,true);
assert.equal(short.months[3].events[0].status,"TARGET_SHORTFALL");
assert.equal(short.months[3].events[0].gapCents,22000);
assert.equal(short.months[3].changeCents,178000);
const past=p.project([income,{...goal,deadlineMonth:"2026-09"}],"2026-11",6,"mom");
assert.equal(past.priorDeadlines.length,1);
assert.equal(past.priorDeadlines[0].status,"PAST_TARGET");
assert.equal(past.months[0].events.length,0);
assert.equal(p.project([cost,goal],"2026-11",6,"mine").reason,"ADD_MANUAL_MONTHLY_INCOME");
assert.equal(p.project([income,goal],"2026-13",6,"mine").reason,"INVALID_START_MONTH");
assert.equal(p.project([income,goal],"2026-11",36,"mine").reason,"INVALID_HORIZON");
assert.equal(p.project([income,goal],"2026-11",6,"unknown").reason,"UNKNOWN_CONTEXT");
assert.equal(p.project([income,income],"2026-11",6,"mine").reason,"DUPLICATE_RECORDS");
assert.equal(p.project([income,{...goal,deadlineMonth:"2027-00"}],"2026-11",6,"mine").reason,"INVALID_LOCAL_RECORDS");
assert.equal(p.project([income,{...goal,savedCents:50000}],"2026-11",6,"mine").reason,"INVALID_LOCAL_RECORDS");
assert.equal(p.project([income],"2026-11",24,"family").months.length,24);
assert.equal(p.indexFor("2027-01")-p.indexFor("2026-12"),1);
assert.equal(p.monthFor(p.indexFor("2026-12")+1),"2027-01");
console.log("FinanceW FP1d monthly timeline policy: PASS");
