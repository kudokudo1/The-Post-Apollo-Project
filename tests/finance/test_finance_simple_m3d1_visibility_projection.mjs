import assert from "node:assert/strict";
import {test} from "node:test";
import {normalizeSnapshot} from "../../scripts/finance/actual_readonly.mjs";
import {inspectCategoryHandoff} from "../../scripts/finance/simple_category_handoff_readiness.mjs";

// Actual-shaped, fictional read-only values. No Actual API, process, server,
// filesystem mutations, permission or transaction writer.
function makeScenario({groupHidden=false, categoryHidden=false,
                        income=false, groupFlag=true, categoryFlag=true}={}) {
  const group={id:"needs",name:"Needs",is_income:income,
    categories:[{id:"groceries",name:"Groceries",budgeted:10000,
      balance:7500,spent:-2500}]};
  if(groupFlag) group.hidden=groupHidden;
  if(categoryFlag) group.categories[0].hidden=categoryHidden;
  const snapshot=normalizeSnapshot({
    month:"2026-11",budget:{toBudget:12000,categoryGroups:[group]},
    accounts:[{id:"checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["checking",40000]]),
    transactionSets:new Map([["checking",[]]]),payees:[]
  });
  snapshot.sourceKey="a".repeat(64);
  const candidate={action:"create",direction:"expense",editing:false,
    sourceKey:snapshot.sourceKey,month:snapshot.month,
    accountId:"checking",date:"2026-11-24",description:"Groceries",
    amountCents:-2000};
  const proposal={ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
    sourceKey:snapshot.sourceKey,month:snapshot.month,accountId:"checking",
    date:"2026-11-24",description:"Groceries",expenseAmountCents:-2000,
    categoryId:"groceries",categoryName:"Groceries",groupId:"needs",
    groupName:"Needs",availableBeforeCents:7500,spentBeforeCents:-2500,
    estimatedAvailableAfterCents:5500,estimatedSpentAfterCents:-4500,
    estimatedOverspent:false,toBudgetAfterCents:null};
  return {group,snapshot,candidate,proposal};
}
test("explicit visible expense flags survive projection and inspector remains read-only",()=>{
  const input=makeScenario();
  assert.equal(input.snapshot.categoryGroups[0].hidden,false);
  assert.equal(input.snapshot.categoryGroups[0].isIncome,false);
  assert.equal(input.snapshot.categories[0].hidden,false);
  const ready=inspectCategoryHandoff(input);
  assert.equal(ready.ok,true);
  assert.equal(ready.canSave,false);
  assert.equal(ready.previewOnly,true);
  assert.equal(ready.requiresFreshActualPreflight,true);
  assert.equal("requestId" in ready.witness,false);
  assert.equal("action" in ready.witness,false);
});
test("actual-hidden category refuses",()=>{
  const input=makeScenario({categoryHidden:true});
  assert.equal(input.snapshot.categories[0].hidden,true);
  assert.equal(inspectCategoryHandoff(input).reason,"category-not-writable");
});
test("actual-hidden group refuses",()=>{
  const input=makeScenario({groupHidden:true});
  assert.equal(input.snapshot.categoryGroups[0].hidden,true);
  assert.equal(inspectCategoryHandoff(input).reason,"category-not-writable");
});
test("missing visibility never converts into false",()=>{
  for(const input of [
    makeScenario({groupFlag:false}),
    makeScenario({categoryFlag:false})
  ]){
    assert.equal(inspectCategoryHandoff(input).reason,"category-visibility-unverified");
    assert.equal(input.snapshot.categoryGroups[0].hidden === null
      || input.snapshot.categories[0].hidden === null,true);
  }
});
test("malformed boolean visibility remains unknown, not visible",()=>{
  const input=makeScenario();
  input.group.hidden="false";
  input.group.categories[0].hidden=0;
  const remapped=normalizeSnapshot({
    month:"2026-11",budget:{toBudget:12000,categoryGroups:[input.group]},
    accounts:[{id:"checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["checking",40000]]),
    transactionSets:new Map([["checking",[]]]),payees:[]
  });
  remapped.sourceKey=input.snapshot.sourceKey;
  input.snapshot=remapped;
  assert.equal(remapped.categoryGroups[0].hidden,null);
  assert.equal(remapped.categories[0].hidden,null);
  assert.equal(inspectCategoryHandoff(input).reason,"category-visibility-unverified");
});
test("income group is absent from expense snapshot and cannot be selected",()=>{
  const input=makeScenario({income:true});
  assert.deepEqual(input.snapshot.categories,[]);
  assert.deepEqual(input.snapshot.categoryGroups,[]);
  assert.equal(inspectCategoryHandoff(input).reason,"category-ambiguous-or-unavailable");
});
test("snapshot data remains separate from write authority",()=>{
  const input=makeScenario();
  const result=inspectCategoryHandoff(input);
  assert.equal(result.canSave,false);
  assert.deepEqual(Object.keys(result.witness).sort(),[
    "accountId","categoryId","date","expectedCategoryAvailableCents",
    "expectedCategoryBudgetedCents","expectedCategorySpentCents",
    "expectedToBudgetCents","expenseAmountCents","month","sourceKey"
  ].sort());
});
