#!/usr/bin/env node
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const src=readFileSync(new URL("../../widgets/FinanceHouseholdPlanningPolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(src+"\n({contexts,context,moneyCents,compare})");
assert.equal(p.contexts().length,5);
for(const id of ["mine","shared","mom","granny","family"]){
    const c=p.context(id);
    assert.equal(c.id,id);
    assert.equal(c.authorized,false);
    assert.equal(c.connected,false);
    assert.equal(c.hasRecords,false);
}
assert.equal(p.context("bogus"),null);
const contexts=p.contexts();contexts[0].label="FAKE";
assert.equal(p.context("mine").label,"MINE");
assert.equal(p.moneyCents("10.05"),1005);
assert.equal(p.moneyCents("0"),0);
for(const bad of ["-1","1e4","1.999","$100"," 100","100 ","garbage","99999999.99"])
    assert.equal(p.moneyCents(bad),null,bad);
function sample(patch={}){
    return Object.assign({contextId:"mine",upfrontText:"1800.00",
        operatingText:"85.00",alternativeText:"140.00",
        hourValueText:"12.00",extraHours:2,horizonMonths:36},patch);
}
const input=sample(),original=JSON.stringify(input);
const x=p.compare(input);
assert.equal(JSON.stringify(input),original);
assert.equal(x.ok,true);
assert.equal(x.contextId,"mine");
assert.equal(x.readOnly,true);
assert.equal(x.persisted,false);
assert.equal(x.bankDataUsed,false);
assert.equal(x.accountsReferenced,0);
assert.equal(x.source,"HYPOTHETICAL_INPUT_ONLY");
assert.equal(x.timeMonthlyCents,2400);
assert.equal(x.optionTotalCents,572400);
assert.equal(x.alternativeTotalCents,504000);
assert.equal(x.optionSavingsCents,-68400);
assert.equal(x.breakEvenMonths,59);
for(const id of ["shared","mom","granny","family"])
    assert.equal(p.compare(sample({contextId:id})).contextId,id);
assert.equal(p.compare(sample({contextId:"nobody"})).reason,"UNKNOWN_CONTEXT");
assert.equal(p.compare(sample({upfrontText:"-100"})).reason,"INVALID_MONEY");
assert.equal(p.compare(sample({extraHours:-1})).reason,"INVALID_TIME");
assert.equal(p.compare(sample({horizonMonths:361})).reason,"INVALID_HORIZON");
assert.equal(p.compare({...sample(),token:"secret"}).reason,"INVALID_INPUT_FIELDS");
assert.equal(p.compare(null).reason,"INVALID_INPUT");
assert.equal(p.compare(sample({upfrontText:"0",operatingText:"0",
    alternativeText:"0",extraHours:0})).breakEvenMonths,null);
assert.equal(p.compare(sample({upfrontText:"0",operatingText:"80",
    alternativeText:"120",extraHours:0})).breakEvenMonths,0);
const high=p.compare(sample({horizonMonths:360,upfrontText:"9999999.99",
    operatingText:"9999999.99",alternativeText:"9999999.99",
    hourValueText:"9999999.99",extraHours:168}));
assert.equal(high.ok,true);
assert.ok(Number.isSafeInteger(high.optionTotalCents));
console.log("FinanceW FP1a hypothetical policy: PASS");
