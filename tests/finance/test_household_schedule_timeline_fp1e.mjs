#!/usr/bin/env node
// FinanceW FP1e // fully fictional funds and due-date test vectors.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const source=readFileSync(new URL("../../widgets/FinanceHouseholdTimelinePolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(source+"\n({project,indexFor,monthFor,validSchedule})");
const id=(x)=>"p-"+x.repeat(32);
const income={id:id("a"),kind:"income",title:"Income",targetCents:0,
    savedCents:0,monthlyCents:300000,deadlineMonth:""};
const rent={id:id("b"),kind:"expense",title:"Rent",targetCents:0,
    savedCents:0,monthlyCents:120000,deadlineMonth:""};
const goal={id:id("c"),kind:"goal",title:"Vehicle reserve",targetCents:40000,
    savedCents:10000,monthlyCents:10000,deadlineMonth:"2027-01"};
const bill={id:id("d"),kind:"bill_due",title:"",expenseId:rent.id,
    dueDay:31,date:"",amountCents:0,fundingGoalId:""};
const linked={id:id("e"),kind:"purchase",title:"Vehicle parts",expenseId:"",
    dueDay:0,date:"2027-01-15",amountCents:35000,fundingGoalId:goal.id};
const newCash={id:id("f"),kind:"purchase",title:"Service",expenseId:"",
    dueDay:0,date:"2026-12-10",amountCents:50000,fundingGoalId:""};
const records=[income,rent,goal],schedules=[bill,linked,newCash];
const beforeRecords=JSON.stringify(records),beforeSchedules=JSON.stringify(schedules);
const timeline=p.project(records,schedules,"2026-11",6,"mine");
assert.equal(timeline.ok,true);
assert.equal(timeline.source,"LOCAL_MANUAL_TIMELINE_ONLY");
assert.equal(timeline.bankVerified,false);
assert.equal(timeline.futurePurchasesCharged,false);
assert.equal(timeline.actualTransfersMade,false);
assert.equal(timeline.plannedPurchaseOutflowModeled,true);
assert.equal(JSON.stringify(records),beforeRecords);
assert.equal(JSON.stringify(schedules),beforeSchedules);
assert.equal(timeline.months.length,6);
assert.equal(timeline.months[0].expenseCents,120000);
assert.equal(timeline.months[0].billEvents.length,1);
assert.equal(timeline.months[0].billEvents[0].dueDate,"2026-11-30");
assert.equal(timeline.months[0].billEvents[0].adjustedToMonthEnd,true);
assert.equal(timeline.months[0].changeCents,170000);
assert.equal(timeline.months[1].purchaseEvents[0].date,"2026-12-10");
assert.equal(timeline.months[1].purchaseNewCashCents,50000);
assert.equal(timeline.months[1].changeCents,120000);
assert.equal(timeline.months[2].events[0].status,"TARGET_FUNDED_IN_MODEL");
assert.equal(timeline.months[2].purchaseEvents.length,1);
assert.equal(timeline.months[2].purchaseEvents[0].goalFundedCents,35000);
assert.equal(timeline.months[2].purchaseEvents[0].newCashCents,0);
assert.equal(timeline.months[2].purchaseGoalFundedCents,35000);
assert.equal(timeline.months[2].purchaseNewCashCents,0);
assert.equal(timeline.months[2].changeCents,170000);
assert.equal(timeline.months[3].month,"2027-02");
assert.equal(timeline.months[3].billEvents[0].dueDate,"2027-02-28");
assert.equal(timeline.months[3].contributionCents,0);
assert.equal(timeline.months[3].changeCents,180000);
// A purchase larger than modeled reserves consumes reserved money once,
// with only its remaining cost reducing this month's free-cash projection.
const more={...linked,amountCents:55000};
const shortage=p.project(records,[bill,more],"2026-11",6,"mine");
assert.equal(shortage.ok,true);
assert.equal(shortage.months[2].purchaseGoalFundedCents,40000);
assert.equal(shortage.months[2].purchaseNewCashCents,15000);
assert.equal(shortage.months[2].changeCents,155000);
const leap=p.project([income,rent],[bill],"2028-02",6,"family");
assert.equal(leap.months[0].billEvents[0].dueDate,"2028-02-29");
assert.equal(p.project(records,[bill,{...linked,fundingGoalId:id("9")}],
    "2026-11",6,"mine").reason,"SCHEDULE_REFERENCE_MISSING");
assert.equal(p.project(records,[{...bill,expenseId:id("9")}],
    "2026-11",6,"mine").reason,"SCHEDULE_REFERENCE_MISSING");
assert.equal(p.project(records,[bill,{...bill,id:id("7")}],
    "2026-11",6,"mine").reason,"DUPLICATE_BILL_SCHEDULE");
assert.equal(p.project(records,[{...newCash,date:"2027-02-30"}],
    "2026-11",6,"mine").reason,"INVALID_LOCAL_SCHEDULES");
assert.equal(p.project([rent,goal],[bill],
    "2026-11",6,"mine").reason,"ADD_MANUAL_MONTHLY_INCOME");
const prior=p.project(records,[{...newCash,date:"2026-10-10"}],
    "2026-11",6,"mine");
assert.equal(prior.priorSchedules[0].status,"PAST_PLANNED_PAYMENT");
assert.equal(prior.months[0].purchaseNewCashCents,0);
// FP1d compatibility: the historical 4-argument call remains source-only.
assert.equal(p.project(records,"2026-11",6,"mine").ok,true);
console.log("FinanceW FP1e scheduled bill and purchase modeling: PASS");
