#!/usr/bin/env node
// FP1j // all fictional, no persistent settings or financial institution IO.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const source=readFileSync(new URL("../../widgets/FinanceHouseholdReservePolicy.js",import.meta.url),"utf8");
const timeline=readFileSync(new URL("../../widgets/FinanceHouseholdTimelinePolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(source+"\n({annotate,depositFor,fundsFor})");
const t=vm.runInNewContext(timeline+"\n({project})");
const id=x=>"p-"+x.repeat(32);
const row=(idChar,kind,title,monthlyCents)=>({
    id:id(idChar),kind,title,monthlyCents,targetCents:0,savedCents:0,
    deadlineMonth:""
});
const income=row("a","income","Manual income",400000);
const quarterly=row("b","expense","Quarterly bill",90000);
const annual=row("c","expense","Annual bill",120000);
const bill=(c,expense)=>({
    id:id(c),kind:"bill_due",title:"",expenseId:expense.id,
    dueDay:15,date:"",amountCents:0,fundingGoalId:"",sourceMonth:""
});
const freq=(c,expense,interval,anchor)=>({
    id:id(c),kind:"bill_cadence",title:"",expenseId:expense.id,
    dueDay:0,date:"",amountCents:0,fundingGoalId:"",sourceMonth:"",
    intervalMonths:interval,anchorMonth:anchor
});
const plans=[income,quarterly,annual];
const schedules=[
    bill("d",quarterly),bill("e",annual),
    freq("f",quarterly,3,"2027-01"),
    freq("1",annual,12,"2027-11")
];
const snapshot=JSON.stringify({plans,schedules});
const cash=t.project(plans,schedules,"2026-11",24,"mine");
assert.equal(cash.ok,true);
const def=p.annotate(plans,schedules,cash);
const explicit=p.annotate(plans,schedules,cash,100);
assert.equal(def.ok,true);
assert.equal(explicit.ok,true);
assert.equal(def.reserveMarginPercent,100);
assert.equal(def.persisted,false);
assert.equal(def.scenarioOnly,true);
for(let i=0;i<24;i++){
    assert.equal(def.months[i].reserveAddedCents,explicit.months[i].reserveAddedCents);
    assert.equal(def.months[i].reserveUsedCents,explicit.months[i].reserveUsedCents);
    assert.equal(def.months[i].reserveBalanceCents,explicit.months[i].reserveBalanceCents);
    assert.equal(def.months[i].reserveBufferHeldCents,0);
}
function inspect(margin,expectedQuarterBuffer,expectedAnnualBuffer) {
    const result=p.annotate(plans,schedules,cash,margin);
    assert.equal(result.ok,true);
    assert.equal(result.reserveMarginPercent,margin);
    assert.equal(result.source,"LOCAL_MANUAL_RESERVE_ESTIMATE");
    assert.equal(result.bankVerified,false);
    assert.equal(result.actualTransfersMade,false);
    assert.equal(result.notAvailableCash,true);
    assert.equal(result.simulatedStartingReserveCents,0);
    assert.equal(result.months.length,24);
    const byMonth=result.byMonth;
    const jan=byMonth["2027-01"];
    const quarterlyDetail=jan.details.find(d=>d.title==="Quarterly bill");
    assert.equal(quarterlyDetail.chargeCents,90000);
    assert.equal(quarterlyDetail.bufferTargetCents,expectedQuarterBuffer);
    assert.equal(quarterlyDetail.bufferHeldCents,expectedQuarterBuffer);
    assert.equal(quarterlyDetail.unfundedCents,0);
    assert.equal(byMonth["2027-04"].details.find(d=>
        d.title==="Quarterly bill").bufferHeldCents,expectedQuarterBuffer);
    const annualDetail=byMonth["2027-11"].details.find(d=>
        d.title==="Annual bill");
    assert.equal(annualDetail.chargeCents,120000);
    assert.equal(annualDetail.bufferTargetCents,expectedAnnualBuffer);
    assert.equal(annualDetail.bufferHeldCents,expectedAnnualBuffer);
    assert.equal(annualDetail.unfundedCents,0);
    for(let i=0;i<24;i++){
        const m=result.months[i],orig=cash.months[i];
        assert.equal(m.reserveBufferHeldCents>=0,true);
        assert.equal(m.reserveBufferAddedCents>=0,true);
        assert.equal(m.reserveBalanceCents>=m.reserveBufferHeldCents,true);
        assert.equal(m.unreservedChangeCents,
            orig.changeCents-m.reserveAddedCents+m.reserveUsedCents);
        assert.equal(m.cumulativeUnreservedChangeCents,
            orig.cumulativeChangeCents-m.reserveBalanceCents);
        for(const d of m.details){
            assert.equal(d.bufferHeldCents<=d.bufferTargetCents,true);
            assert.equal(d.bufferUsedCents<=d.usedCents,true);
            assert.equal(d.heldCents>=d.bufferHeldCents,true);
        }
    }
    return result;
}
const plus10=inspect(110,9000,12000);
const plus25=inspect(125,22500,30000);
assert.equal(plus10.byMonth["2026-11"].reserveBufferAddedCents,3000);
assert.equal(plus25.byMonth["2026-11"].reserveBufferAddedCents,7500);
assert.equal(plus10.byMonth["2027-02"].details.find(d=>
    d.title==="Quarterly bill").bufferAddedCents,0);
assert.equal(plus25.byMonth["2027-02"].details.find(d=>
    d.title==="Quarterly bill").bufferAddedCents,0);
assert.equal(cash.months[0].changeCents,400000);
assert.equal(cash.months[2].expenseCents,90000);
assert.equal(JSON.stringify({plans,schedules}),snapshot);
assert.equal(p.annotate(plans,schedules,cash,0).reason,"INVALID_RESERVE_CUSHION");
assert.equal(p.annotate(plans,schedules,cash,150).reason,"INVALID_RESERVE_CUSHION");
assert.equal(p.annotate(plans,schedules,cash,110.5).reason,"INVALID_RESERVE_CUSHION");
assert.equal(p.annotate(plans,schedules,cash,"110").reason,"INVALID_RESERVE_CUSHION");
assert.equal(p.annotate(plans,schedules,cash,NaN).reason,"INVALID_RESERVE_CUSHION");
const skip={id:id("2"),kind:"bill_skip",title:"",expenseId:quarterly.id,
    dueDay:0,date:"2027-01",amountCents:0,fundingGoalId:"",sourceMonth:""};
const skippedCash=t.project(plans,[...schedules,skip],"2026-11",6,"mine");
const skipped=p.annotate(plans,[...schedules,skip],skippedCash,110);
assert.equal(skipped.ok,true);
assert.equal(skipped.byMonth["2027-01"].details.find(d=>
    d.title==="Quarterly bill").chargeCents,0);
assert.equal(skipped.byMonth["2027-01"].details.find(d=>
    d.title==="Quarterly bill").bufferHeldCents,9000);
const defer={id:id("3"),kind:"bill_defer",title:"",expenseId:quarterly.id,
    dueDay:0,date:"2027-02-15",amountCents:0,fundingGoalId:"",
    sourceMonth:"2027-01"};
const deferredCash=t.project(plans,[...schedules,defer],"2026-11",6,"mine");
const deferred=p.annotate(plans,[...schedules,defer],deferredCash,110);
assert.equal(deferred.ok,true);
assert.equal(deferred.byMonth["2027-02"].details.find(d=>
    d.title==="Quarterly bill").chargeCents,90000);
assert.equal(deferred.byMonth["2027-02"].details.find(d=>
    d.title==="Quarterly bill").bufferHeldCents,9000);
console.log("FinanceW FP1j reserve cushion cases and conservation: PASS");
