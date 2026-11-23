import assert from "node:assert/strict";
import {test} from "node:test";
import {inspectCategoryHandoff} from "../../scripts/finance/simple_category_handoff_readiness.mjs";

function fixture() {
  const sourceKey="a".repeat(64);
  const snapshot={
    schemaVersion:1,source:"actual-budget",readOnly:true,sourceKey,
    month:"2026-11",toBudgetCents:12000,
    accounts:[{id:"checking",name:"Checking",balanceCents:40000}],
    categoryGroups:[{id:"needs",name:"Needs",hidden:false,isIncome:false}],
    categories:[{id:"groceries",name:"Groceries",groupId:"needs",
      hidden:false,budgetedCents:10000,availableCents:7500,spentCents:-2500}]
  };
  const candidate={action:"create",direction:"expense",editing:false,
    sourceKey,month:"2026-11",accountId:"checking",date:"2026-11-23",
    description:"Food",amountCents:-2000};
  const proposal={ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
    sourceKey,month:"2026-11",accountId:"checking",date:"2026-11-23",
    description:"Food",expenseAmountCents:-2000,
    categoryId:"groceries",categoryName:"Groceries",
    groupId:"needs",groupName:"Needs",availableBeforeCents:7500,
    estimatedAvailableAfterCents:5500,spentBeforeCents:-2500,
    estimatedSpentAfterCents:-4500,estimatedOverspent:false,toBudgetAfterCents:null};
  return {snapshot,candidate,proposal};
}
const inspect = x => inspectCategoryHandoff(x);
test("consistent fictional witness still cannot authorize Save",()=>{
  const result=inspect(fixture());
  assert.equal(result.ok,true);
  assert.equal(result.canSave,false);
  assert.equal(result.previewOnly,true);
  assert.equal(result.requiresFreshActualPreflight,true);
  assert.equal(result.requiresIndependentSecurityReview,true);
  assert.equal(result.witness.expectedCategoryAvailableCents,7500);
  assert.equal("requestId" in result.witness,false);
  assert.equal("action" in result.witness,false);
});
test("current normalized snapshot missing visibility metadata refuses",()=>{
  const x=fixture();
  delete x.snapshot.categories[0].hidden;
  delete x.snapshot.categoryGroups[0].hidden;
  delete x.snapshot.categoryGroups[0].isIncome;
  assert.equal(inspect(x).reason,"category-visibility-unverified");
});
test("hidden category and hidden group refuse independently",()=>{
  let x=fixture();x.snapshot.categories[0].hidden=true;
  assert.equal(inspect(x).reason,"category-not-writable");
  x=fixture();x.snapshot.categoryGroups[0].hidden=true;
  assert.equal(inspect(x).reason,"category-not-writable");
});
test("income group refuses",()=>{
  const x=fixture();x.snapshot.categoryGroups[0].isIncome=true;
  assert.equal(inspect(x).reason,"category-not-writable");
});
test("stale source and changed expense refuse",()=>{
  let x=fixture();x.candidate.sourceKey="b".repeat(64);
  assert.equal(inspect(x).reason,"new-expense-candidate-required");
  x=fixture();x.candidate.amountCents=-2100;
  assert.equal(inspect(x).reason,"matching-readonly-preview-required");
});
test("stale budget/estimate/identity refuse",()=>{
  let x=fixture();x.snapshot.categories[0].availableCents=7100;
  assert.equal(inspect(x).reason,"preview-balances-or-identity-stale");
  x=fixture();x.proposal.estimatedAvailableAfterCents=5600;
  assert.equal(inspect(x).reason,"preview-estimate-stale");
  x=fixture();x.proposal.categoryName="Other";
  assert.equal(inspect(x).reason,"preview-balances-or-identity-stale");
});
test("duplicate category and account IDs refuse",()=>{
  let x=fixture();x.snapshot.categories.push({...x.snapshot.categories[0]});
  assert.equal(inspect(x).reason,"category-ambiguous-or-unavailable");
  x=fixture();x.snapshot.accounts.push({...x.snapshot.accounts[0]});
  assert.equal(inspect(x).reason,"account-ambiguous-or-unavailable");
});
test("income, update, invalid date, positive amounts refuse",()=>{
  for(const mutate of [
    x=>{x.candidate.direction="income";},
    x=>{x.candidate.action="update";},
    x=>{x.candidate.date="2026-11-31";},
    x=>{x.candidate.amountCents=1000;}
  ]){const x=fixture();mutate(x);
    assert.equal(inspect(x).reason,"new-expense-candidate-required");
  }
});
test("forged write-ready proposal refuses",()=>{
  let x=fixture();x.proposal.writeAllowed=true;
  assert.equal(inspect(x).reason,"matching-readonly-preview-required");
  x=fixture();x.proposal.toBudgetAfterCents=3000;
  assert.equal(inspect(x).reason,"matching-readonly-preview-required");
});
test("overspending estimate is permitted only as read-only warning",()=>{
  const x=fixture();
  x.candidate.amountCents=-8000;
  x.proposal.expenseAmountCents=-8000;
  x.proposal.estimatedAvailableAfterCents=-500;
  x.proposal.estimatedSpentAfterCents=-10500;
  x.proposal.estimatedOverspent=true;
  const result=inspect(x);
  assert.equal(result.ok,true);
  assert.equal(result.canSave,false);
});
