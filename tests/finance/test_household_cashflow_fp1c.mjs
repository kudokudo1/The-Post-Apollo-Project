#!/usr/bin/env node
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const src=readFileSync(new URL("../../widgets/FinanceHouseholdCashFlowPolicy.js",import.meta.url),"utf8");
const p=vm.runInNewContext(src+"\n({summarize,monthIndex,goalStatus})");
const id="p-"+"a".repeat(32);
const goal={id,kind:"goal",title:"Vehicle",targetCents:1200000,
    savedCents:300000,monthlyCents:25000,deadlineMonth:"2027-11"};
const expense={id:"p-"+"b".repeat(32),kind:"expense",title:"Rent",
    targetCents:0,savedCents:0,monthlyCents:125000,deadlineMonth:""};
const income={id:"p-"+"c".repeat(32),kind:"income",title:"Take-home pay",
    targetCents:0,savedCents:0,monthlyCents:250000,deadlineMonth:""};
const s=p.summarize([income,expense,goal],12);
assert.equal(s.ok,true);
assert.equal(s.source,"LOCAL_MANUAL_PLAN_ONLY");
assert.equal(s.readOnly,true);
assert.equal(s.verifiedBankBalance,false);
assert.equal(s.monthlyChangeCents,100000);
assert.equal(s.horizonChangeCents,1200000);
assert.equal(s.expenseCents,125000);
assert.equal(s.incomeCents,250000);
assert.equal(s.contributionCents,25000);
assert.equal(p.summarize([goal,expense],12).reason,"ADD_MANUAL_MONTHLY_INCOME");
assert.equal(p.summarize([income,{...goal,deadlineMonth:"2027-13"}],12).ok,false);
assert.equal(p.summarize([income,{...goal,savedCents:1200001}],12).ok,false);
assert.equal(p.summarize([income],0).reason,"INVALID_HORIZON");
assert.equal(p.summarize([income],361).reason,"INVALID_HORIZON");
const completed={...goal,savedCents:goal.targetCents};
assert.equal(p.summarize([income,expense,completed],12).contributionCents,0);
assert.equal(p.monthIndex("2027-11")-p.monthIndex("2026-11"),12);
const g=p.goalStatus(goal,"2026-11");
assert.equal(g.ok,true);
assert.equal(g.monthsAtRate,36);
assert.equal(g.monthsToDeadline,12);
assert.equal(g.requiredMonthlyCents,75000);
assert.equal(g.gapMonthlyCents,50000);
assert.equal(p.goalStatus(goal,"2028-01").requiredMonthlyCents,null);
assert.equal(p.goalStatus({...goal,deadlineMonth:""},"2026-11").monthsToDeadline,null);
console.log("FinanceW FP1c forecast/goal arithmetic: PASS");
