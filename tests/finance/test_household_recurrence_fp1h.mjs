#!/usr/bin/env node
// All money is fictional and local. Per-charge cadence must change the math.
import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
const source=readFileSync(new URL("../../widgets/FinanceHouseholdTimelinePolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(source+"\n({coverage,project,chargeOccurs})");
const id=c=>"p-"+c.repeat(32);
const expense=(ch,title,cents)=>({id:id(ch),kind:"expense",title,
    targetCents:0,savedCents:0,monthlyCents:cents,deadlineMonth:""});
const income={id:id("a"),kind:"income",title:"Income",targetCents:0,
    savedCents:0,monthlyCents:300000,deadlineMonth:""};
const rent=expense("b","Rent",120000);
const phone=expense("c","Phone",5000);
const quarterly=expense("d","Quarterly insurance",90000);
const annual=expense("e","Annual registration",120000);
const bill=(ch,exp,day)=>({id:id(ch),kind:"bill_due",title:"",expenseId:exp.id,
    dueDay:day,date:"",amountCents:0,fundingGoalId:"",sourceMonth:""});
const cadence=(ch,exp,interval,anchor)=>({id:id(ch),kind:"bill_cadence",title:"",
    expenseId:exp.id,dueDay:0,date:"",amountCents:0,fundingGoalId:"",
    sourceMonth:"",intervalMonths:interval,anchorMonth:anchor});
const qrBill=bill("f",quarterly,31),annBill=bill("1",annual,29);
const rentBill=bill("2",rent,31),q=cadence("3",quarterly,3,"2026-11");
const a=cadence("4",annual,12,"2026-12");
const rows=[income,rent,phone,quarterly,annual];
const schedule=[rentBill,qrBill,q,annBill,a];
const before=JSON.stringify({rows,schedule});
const coverage=p.coverage(rows,schedule);
assert.equal(coverage.ok,true);
assert.equal(coverage.quarterlyBillCount,1);
assert.equal(coverage.annualBillCount,1);
assert.equal(coverage.cadenceCount,2);
assert.equal(coverage.amountInterpretation,"PER_CHARGE_WHEN_CADENCE_SET");
assert.equal(coverage.allObligationsKnown,false);
assert.equal(coverage.undatedExpenseCount,1);
const t=p.project(rows,schedule,"2026-11",24,"mine");
assert.equal(t.ok,true);
assert.equal(t.bankVerified,false);
assert.equal(t.months[0].month,"2026-11");
assert.equal(t.months[0].expenseCents,215000);
assert.equal(t.months[0].billEvents.length,2);
assert.equal(t.months[0].billEvents[1].dueDate,"2026-11-30");
assert.equal(t.months[0].changeCents,85000);
assert.equal(t.months[1].month,"2026-12");
assert.equal(t.months[1].expenseCents,245000);
assert.equal(t.months[1].billEvents.find(e=>e.expenseId===annual.id).intervalMonths,12);
assert.equal(t.months[1].changeCents,55000);
assert.equal(t.months[2].month,"2027-01");
assert.equal(t.months[2].expenseCents,125000);
assert.equal(t.months[2].changeCents,175000);
assert.equal(t.months[3].month,"2027-02");
assert.equal(t.months[3].expenseCents,215000);
assert.equal(t.months[3].billEvents.find(e=>e.expenseId===quarterly.id).dueDate,"2027-02-28");
assert.equal(t.months[13].month,"2027-12");
assert.equal(t.months[13].expenseCents,245000);
assert.equal(t.months.filter(m=>m.billEvents.some(e=>e.expenseId===annual.id)).length,2);
assert.equal(t.months.filter(m=>m.billEvents.some(e=>e.expenseId===quarterly.id)).length,8);
assert.equal(JSON.stringify({rows,schedule}),before);
assert.equal(p.chargeOccurs("2026-10",q),false);
assert.equal(p.chargeOccurs("2026-11",q),true);
assert.equal(p.chargeOccurs("2026-12",q),false);
assert.equal(p.chargeOccurs("2027-02",q),true);
const skip={id:id("5"),kind:"bill_skip",title:"",expenseId:quarterly.id,
    dueDay:0,date:"2026-11",amountCents:0,fundingGoalId:"",sourceMonth:""};
const omitted=p.project(rows,[...schedule,skip],"2026-11",6,"mine");
assert.equal(omitted.months[0].expenseCents,125000);
assert.equal(omitted.months[0].exceptionEvents[0].excludedCents,90000);
assert.equal(omitted.months[1].expenseCents,245000);
const defer={id:id("6"),kind:"bill_defer",title:"",expenseId:quarterly.id,
    dueDay:0,date:"2026-12-20",amountCents:0,fundingGoalId:"",sourceMonth:"2026-11"};
const delayed=p.project(rows,[...schedule,defer],"2026-11",6,"mine");
assert.equal(delayed.months[0].expenseCents,125000);
assert.equal(delayed.months[0].movedFromEvents[0].movedCents,90000);
assert.equal(delayed.months[1].expenseCents,245000);
assert.equal(delayed.months[1].movedPaymentCents,90000);
assert.equal(delayed.months[1].changeCents,-35000);
assert.equal(delayed.months[3].expenseCents,215000);
assert.equal(p.coverage(rows,[...schedule,{...skip,date:"2026-12"}]).reason,
    "INVALID_RECURRENCE_EXCEPTION");
assert.equal(p.coverage(rows,[...schedule,{...defer,sourceMonth:"2026-12",date:"2027-01-20"}]).reason,
    "INVALID_RECURRENCE_EXCEPTION");
assert.equal(p.coverage(rows,[...schedule,skip,defer]).reason,
    "CONFLICTING_BILL_EXCEPTION");
assert.equal(p.coverage(rows,[...schedule,{...q,id:id("7")}]).reason,
    "DUPLICATE_BILL_CADENCE");
assert.equal(p.coverage(rows,[...schedule,{...q,id:id("8"),expenseId:id("9")}]).reason,
    "SCHEDULE_REFERENCE_MISSING");
const startInFuture=p.project(rows,[rentBill,qrBill,{...q,anchorMonth:"2027-05"}],
    "2026-11",6,"mine");
assert.equal(startInFuture.months.slice(0,6).filter(m=>
    m.billEvents.some(e=>e.expenseId===quarterly.id)).length,0);
// Legacy v3 with no cadence stays monthly.
const legacy=[rentBill,qrBill,annBill];
assert.equal(p.project(rows,legacy,"2026-11",6,"mine").months[0].expenseCents,335000);
console.log("FinanceW FP1h quarterly and annual cadence accounting: PASS");
