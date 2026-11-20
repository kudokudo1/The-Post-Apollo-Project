#!/usr/bin/env node
// Fictional values only. One scheduled bill is moved, not duplicated.
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
const src=readFileSync(new URL("../../widgets/FinanceHouseholdTimelinePolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(src+"\n({coverage,project})");
const id=c=>"p-"+c.repeat(32);
const income={id:id("a"),kind:"income",title:"Pay",targetCents:0,savedCents:0,monthlyCents:300000,deadlineMonth:""};
const rent={id:id("b"),kind:"expense",title:"Rent",targetCents:0,savedCents:0,monthlyCents:120000,deadlineMonth:""};
const phone={id:id("c"),kind:"expense",title:"Phone",targetCents:0,savedCents:0,monthlyCents:10000,deadlineMonth:""};
const bill={id:id("d"),kind:"bill_due",title:"",expenseId:rent.id,dueDay:28,date:"",amountCents:0,fundingGoalId:"",sourceMonth:""};
const deferred={id:id("e"),kind:"bill_defer",title:"",expenseId:rent.id,dueDay:0,date:"2026-12-15",amountCents:0,fundingGoalId:"",sourceMonth:"2026-11"};
const rows=[income,rent,phone],plans=[bill,deferred];
const unchanged=JSON.stringify({rows,plans});
const cov=p.coverage(rows,plans);
assert.equal(cov.ok,true);
assert.equal(cov.monthlyExpenseCount,2);
assert.equal(cov.datedExpenseCount,1);
assert.equal(cov.undatedExpenseCount,1);
assert.equal(cov.deferredPaymentCount,1);
assert.equal(cov.allObligationsKnown,false);
const model=p.project(rows,plans,"2026-11",6,"mine");
assert.equal(model.ok,true);
assert.equal(model.bankVerified,false);
assert.equal(model.months.length,6);
assert.equal(model.months[0].month,"2026-11");
assert.equal(model.months[0].baseExpenseCents,130000);
assert.equal(model.months[0].expenseCents,10000);
assert.equal(model.months[0].movedFromEvents[0].sourceMonth,"2026-11");
assert.equal(model.months[0].billEvents.length,0);
assert.equal(model.months[0].changeCents,290000);
assert.equal(model.months[1].month,"2026-12");
assert.equal(model.months[1].expenseCents,130000);
assert.equal(model.months[1].movedPaymentCents,120000);
assert.equal(model.months[1].movedToEvents[0].targetDate,"2026-12-15");
assert.equal(model.months[1].billEvents.length,1);
assert.equal(model.months[1].changeCents,50000);
assert.equal(model.months[2].expenseCents,130000);
assert.equal(model.months[2].movedPaymentCents,0);
assert.equal(model.months[2].changeCents,170000);
assert.equal(JSON.stringify({rows,plans}),unchanged);
assert.equal(p.coverage(rows,[deferred]).reason,"SCHEDULE_REFERENCE_MISSING");
assert.equal(p.coverage(rows,[bill,{...deferred,id:id("f")}]).reason,"DUPLICATE_BILL_DEFERRAL");
assert.equal(p.coverage(rows,[bill,deferred,{id:id("1"),kind:"bill_skip",title:"",expenseId:rent.id,dueDay:0,date:"2026-11",amountCents:0,fundingGoalId:"",sourceMonth:""}]).reason,"CONFLICTING_BILL_EXCEPTION");
assert.equal(p.coverage(rows,[bill,{...deferred,date:"2026-11-29"}]).reason,"INVALID_LOCAL_SCHEDULES");
// Source month before the visible period: only the later target outflow is shown.
const carry=p.project(rows,[bill,{...deferred,sourceMonth:"2026-10"}],"2026-11",6,"mine");
assert.equal(carry.months[0].expenseCents,130000);
assert.equal(carry.months[1].movedPaymentCents,120000);
// A later month outside the horizon does not invent an in-range payment.
const outside=p.project(rows,[bill,{...deferred,date:"2028-01-20"}],"2026-11",6,"mine");
assert.equal(outside.months[0].movedFromEvents.length,1);
assert.equal(outside.months.every(r=>r.movedPaymentCents===0),true);
// Old 8-field v2 rows remain readable.
const legacy={...bill};delete legacy.sourceMonth;
assert.equal(p.project(rows,[legacy],"2026-11",6,"mine").ok,true);
console.log("FinanceW FP1g deferred-bill projections: PASS");
