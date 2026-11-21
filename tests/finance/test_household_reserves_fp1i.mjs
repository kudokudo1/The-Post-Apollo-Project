#!/usr/bin/env node
// FinanceW FP1i: fictional, in-memory sinking funds only. No financial accounts.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const timelineSource=readFileSync(new URL("../../widgets/FinanceHouseholdTimelinePolicy.js",import.meta.url),"utf8");
const reserveSource=readFileSync(new URL("../../widgets/FinanceHouseholdReservePolicy.js",import.meta.url),"utf8");
const tl=vm.runInNewContext(timelineSource+"\n({project})");
const p=vm.runInNewContext(reserveSource+"\n({annotate,depositFor,fundsFor})");
const id=x=>"p-"+x.repeat(32);
const base=(ch,kind,title,monthlyCents)=>({
    id:id(ch),kind,title,targetCents:0,savedCents:0,
    monthlyCents,deadlineMonth:""
});
const income=base("a","income","Manual pay",300000);
const rent=base("b","expense","Rent",120000);
const quarter=base("c","expense","Quarterly insurance",90001);
const annual=base("d","expense","Annual registration",120000);
const bill=(ch,expense,day)=>({
    id:id(ch),kind:"bill_due",title:"",expenseId:expense.id,dueDay:day,
    date:"",amountCents:0,fundingGoalId:"",sourceMonth:""
});
const cad=(ch,expense,n,month)=>({
    id:id(ch),kind:"bill_cadence",title:"",expenseId:expense.id,dueDay:0,
    date:"",amountCents:0,fundingGoalId:"",sourceMonth:"",
    intervalMonths:n,anchorMonth:month
});
const quarterBill=bill("e",quarter,28),yearBill=bill("f",annual,29);
const q=cad("1",quarter,3,"2026-11"),a=cad("2",annual,12,"2026-12");
const rows=[income,rent,quarter,annual],schedules=[quarterBill,yearBill,q,a];
const before=JSON.stringify({rows,schedules});
const cash=tl.project(rows,schedules,"2026-11",24,"mine");
assert.equal(cash.ok,true);
const result=p.annotate(rows,schedules,cash);
assert.equal(result.ok,true);
assert.equal(result.readOnly,true);
assert.equal(result.bankVerified,false);
assert.equal(result.actualTransfersMade,false);
assert.equal(result.startingReserveKnown,false);
assert.equal(result.notAvailableCash,true);
assert.equal(result.simulatedStartingReserveCents,0);
assert.equal(result.monthlyReserveCount,2);
assert.equal(result.months.length,24);
assert.equal(result.months[0].month,"2026-11");
assert.equal(result.months[0].reserveAddedCents,40001);
assert.equal(result.months[0].reserveUsedCents,30001);
assert.equal(result.months[0].reserveBalanceCents,10000);
assert.equal(result.months[0].uncoveredPeriodicCents,60000);
assert.equal(result.months[0].unreservedChangeCents,
    cash.months[0].changeCents-10000);
assert.equal(result.months[1].reserveAddedCents,40000);
assert.equal(result.months[1].reserveUsedCents,20000);
assert.equal(result.months[1].uncoveredPeriodicCents,100000);
assert.equal(result.months[1].reserveBalanceCents,30000);
assert.equal(result.months[2].reserveUsedCents,0);
assert.equal(result.months[3].details.find(d=>d.title==="Quarterly insurance").usedCents,90001);
assert.equal(result.months[3].details.find(d=>d.title==="Quarterly insurance").unfundedCents,0);
assert.equal(result.months[13].month,"2027-12");
assert.equal(result.months[13].details.find(d=>d.title==="Annual registration").chargeCents,120000);
for(let i=0;i<24;i++){
    const m=result.months[i],original=cash.months[i];
    assert.equal(m.cumulativeUnreservedChangeCents,
        original.cumulativeChangeCents-m.reserveBalanceCents);
    assert.equal(m.unreservedChangeCents,
        original.changeCents-m.reserveAddedCents+m.reserveUsedCents);
    assert.equal(m.reserveBalanceCents>=0,true);
    assert.equal(m.reserveUsedCents<=m.reserveAddedCents+
        (i?result.months[i-1].reserveBalanceCents:0),true);
    assert.equal(result.byMonth[m.month],m);
}
assert.equal(JSON.stringify({rows,schedules}),before);
const fund={amountCents:10001,intervalMonths:3,anchorMonth:"2027-01"};
assert.equal(p.depositFor(fund,"2026-10"),0);
assert.equal(p.depositFor(fund,"2026-11"),3334);
assert.equal(p.depositFor(fund,"2026-12"),3333);
assert.equal(p.depositFor(fund,"2027-01"),3334);
assert.equal(p.depositFor(fund,"2027-02"),3334);
assert.equal(p.depositFor(fund,"2027-03"),3333);
assert.equal(p.depositFor(fund,"2027-01")+
    p.depositFor(fund,"2027-02")+p.depositFor(fund,"2027-03"),10001);
const skip={id:id("3"),kind:"bill_skip",title:"",expenseId:quarter.id,
    dueDay:0,date:"2026-11",amountCents:0,fundingGoalId:"",sourceMonth:""};
const skipCash=tl.project(rows,[...schedules,skip],"2026-11",6,"mine");
const skipReserved=p.annotate(rows,[...schedules,skip],skipCash);
assert.equal(skipReserved.ok,true);
assert.equal(skipReserved.months[0].details.find(d=>d.title==="Quarterly insurance").usedCents,0);
assert.equal(skipReserved.months[0].details.find(d=>d.title==="Quarterly insurance").heldCents,30001);
const move={id:id("4"),kind:"bill_defer",title:"",expenseId:quarter.id,
    dueDay:0,date:"2026-12-16",amountCents:0,fundingGoalId:"",
    sourceMonth:"2026-11"};
const moveCash=tl.project(rows,[...schedules,move],"2026-11",6,"mine");
const moveReserve=p.annotate(rows,[...schedules,move],moveCash);
assert.equal(moveReserve.ok,true);
assert.equal(moveReserve.months[0].reserveBalanceCents,40001);
assert.equal(moveReserve.months[1].details.find(d=>d.title==="Quarterly insurance").chargeCents,90001);
assert.equal(moveReserve.months[1].details.find(d=>d.title==="Quarterly insurance").usedCents,60001);
assert.equal(moveReserve.months[1].details.find(d=>d.title==="Quarterly insurance").unfundedCents,30000);
const noFunds=p.annotate([income,rent],[],tl.project([income,rent],[],"2026-11",6,"family"));
assert.equal(noFunds.ok,true);
assert.equal(noFunds.monthlyReserveCount,0);
assert.equal(noFunds.months[0].reserveBalanceCents,0);
assert.equal(noFunds.months[0].unreservedChangeCents,180000);
assert.equal(p.annotate(rows,schedules,{...cash,bankVerified:true}).reason,"TIMELINE_NOT_VERIFIED");
assert.equal(p.annotate(rows,schedules,{...cash,months:cash.months.slice(1)}).reason,"TIMELINE_NOT_VERIFIED");
assert.equal(p.annotate(rows,[{...q,expenseId:id("9")}],cash).reason,"INVALID_FUND_REFERENCE");
console.log("FinanceW FP1i read-only sinking fund earmark accounting: PASS");
