import assert from "node:assert/strict";
import {test} from "node:test";
import {normalizeSnapshot} from "../../scripts/finance/actual_readonly.mjs";
import {validateCategorizedExpenseCommand} from "../../scripts/finance/categorized_expense_guard.mjs";
import {prepareOfflineCategorizedReview,recheckOfflineCategorizedReview}
  from "../../scripts/finance/simple_m3d2_offline_review.mjs";

function fixture(){
  const data={
    month:"2026-11",
    budget:{toBudget:12000,categoryGroups:[
      {id:"needs",name:"Needs",is_income:false,hidden:false,categories:[
        {id:"groceries",name:"Groceries",hidden:false,
          budgeted:10000,balance:7500,spent:-2500},
        {id:"fuel",name:"Fuel",hidden:false,
          budgeted:4000,balance:2500,spent:-1500}
      ]}
    ]},
    accounts:[{id:"checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["checking",40000]]),
    transactionSets:new Map([["checking",[]]]),payees:[]
  };
  const snapshot=normalizeSnapshot(data);
  snapshot.sourceKey="a".repeat(64);
  const candidate={action:"create",direction:"expense",editing:false,
    sourceKey:snapshot.sourceKey,month:"2026-11",
    accountId:"checking",date:"2026-11-24",
    description:"Fictional Market",amountCents:-2000};
  const proposal={ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
    sourceKey:snapshot.sourceKey,month:"2026-11",accountId:"checking",
    date:"2026-11-24",description:"Fictional Market",expenseAmountCents:-2000,
    categoryId:"groceries",categoryName:"Groceries",groupId:"needs",
    groupName:"Needs",availableBeforeCents:7500,spentBeforeCents:-2500,
    estimatedAvailableAfterCents:5500,estimatedSpentAfterCents:-4500,
    estimatedOverspent:false,toBudgetAfterCents:null};
  return {snapshot,candidate,proposal,selectedCategoryId:"groceries"};
}
function prep(v){return prepareOfflineCategorizedReview(v);}
function recheck(old,v){return recheckOfflineCategorizedReview({previous:old,...v});}
test("valid offline preview remains disabled and has no executable command",()=>{
  const review=prep(fixture());
  assert.equal(review.ok,true);
  assert.equal(review.canSave,false);
  assert.equal(review.writeAllowed,false);
  assert.equal(review.requiresFreshActualPreflight,true);
  assert.equal(review.requiresIndependentSecurityReview,true);
  assert.equal("action" in review.previewFields,false);
  assert.equal("requestId" in review.previewFields,false);
  assert.equal(Object.keys(review.previewFields).length,11);
  assert.equal(recheck(review,fixture()).canSave,false);
});
test("M3b schema is compatible ONLY after fictitious test action/id are added",()=>{
  const review=prep(fixture());
  assert.throws(()=>validateCategorizedExpenseCommand(review.previewFields),
    e=>e?.code==="unexpected-fields");
  const fictional={
    action:"create-categorized-expense",
    requestId:"b".repeat(32),
    ...review.previewFields
  };
  assert.deepEqual(validateCategorizedExpenseCommand(fictional),fictional);
  assert.equal("action" in review.previewFields,false);
});
test("category picker changed after preview refuses",()=>{
  const x=fixture();x.selectedCategoryId="fuel";
  assert.equal(prep(x).reason,"selected-category-changed");
});
test("date, source, month, account, amount and payee changes refuse",()=>{
  const mutations=[
    x=>{x.candidate.date="2026-11-23";},
    x=>{x.candidate.sourceKey="b".repeat(64);},
    x=>{x.snapshot.month="2026-12";},
    x=>{x.candidate.accountId="another";},
    x=>{x.candidate.amountCents=-1900;},
    x=>{x.candidate.description="Other Merchant";}
  ];
  for(const change of mutations){
    const x=fixture(),before=prep(x);assert.equal(before.ok,true);
    change(x);
    assert.equal(recheck(before,x).canSave,false);
    assert.equal(recheck(before,x).ok,false);
  }
});
test("stale category balance and changed group refuse",()=>{
  let x=fixture();
  x.snapshot.categories[0].availableCents=7400;
  assert.equal(prep(x).reason,"preview-balances-or-identity-stale");
  x=fixture();
  x.snapshot.categoryGroups[0].name="Different";
  assert.equal(prep(x).reason,"preview-balances-or-identity-stale");
});
test("hidden, missing visibility and income-group attempts refuse",()=>{
  let x=fixture();x.snapshot.categories[0].hidden=true;
  assert.equal(prep(x).reason,"category-not-writable");
  x=fixture();x.snapshot.categoryGroups[0].hidden=null;
  assert.equal(prep(x).reason,"category-visibility-unverified");
  x=fixture();x.snapshot.categoryGroups[0].isIncome=true;
  assert.equal(prep(x).reason,"category-not-writable");
});
test("forged review fields never pass recheck",()=>{
  const x=fixture(),old=prep(x);
  old.previewFields.amountCents=-9000;
  assert.equal(recheck(old,x).reason,"review-changed");
  const y=fixture(),fresh=prep(y);
  fresh.previewFields.action="create-categorized-expense";
  assert.equal(recheck(fresh,y).reason,"review-changed");
});
test("no fabricated saved balance or authority is ever returned",()=>{
  const x=fixture(),review=prep(x);
  assert.equal(review.ok,true);
  assert.equal("toBudgetAfterCents" in review.previewFields,false);
  assert.equal("saved" in review,false);
  assert.equal("permit" in review,false);
  assert.equal("writeCommand" in review,false);
  assert.equal(recheck(review,x).reason,"review-still-matches-but-save-locked");
});
test("duplicate account/category identifiers refuse",()=>{
  let x=fixture();
  x.snapshot.accounts.push({...x.snapshot.accounts[0]});
  assert.equal(prep(x).reason,"account-ambiguous-or-unavailable");
  x=fixture();
  x.snapshot.categories.push({...x.snapshot.categories[0]});
  assert.equal(prep(x).reason,"category-ambiguous-or-unavailable");
});
test("income, edited, malformed, and overspent candidates behave safely",()=>{
  let x=fixture();x.candidate.direction="income";
  assert.equal(prep(x).ok,false);
  x=fixture();x.candidate.editing=true;
  assert.equal(prep(x).ok,false);
  x=fixture();x.candidate.date="2026-11-31";
  assert.equal(prep(x).ok,false);
  x=fixture();x.candidate.amountCents=-8000;
  x.proposal.expenseAmountCents=-8000;
  x.proposal.estimatedAvailableAfterCents=-500;
  x.proposal.estimatedSpentAfterCents=-10500;
  x.proposal.estimatedOverspent=true;
  assert.equal(prep(x).canSave,false);
});
