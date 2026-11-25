import assert from "node:assert/strict";
import {test} from "node:test";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import vm from "node:vm";
import {normalizeSnapshot} from "../../scripts/finance/actual_readonly.mjs";
import {prepareOfflineCategorizedReview,recheckOfflineCategorizedReview}
  from "../../scripts/finance/simple_m3d2_offline_review.mjs";

const file=fileURLToPath(new URL(
  "../../services/finance/FinanceCategorizedSaveReview.js",import.meta.url));
const source=readFileSync(file,"utf8").replace(/^\.pragma library\s*/,"");
const sandbox={};
vm.createContext(sandbox);
vm.runInContext(source,sandbox,{filename:"FinanceCategorizedSaveReview.js"});
const qmlReview=v=>sandbox.prepareOfflineCategorizedReview(v);
const qmlRecheck=v=>sandbox.recheckOfflineCategorizedReview(v);
const stable=x=>JSON.parse(JSON.stringify(x));

function fixture(){
  const month="2026-11";
  const snapshot=normalizeSnapshot({
    month,budget:{toBudget:12000,categoryGroups:[
      {id:"needs",name:"Needs",is_income:false,hidden:false,categories:[
        {id:"groceries",name:"Groceries",hidden:false,
          budgeted:10000,balance:7500,spent:-2500},
        {id:"fuel",name:"Fuel",hidden:false,budgeted:5000,balance:4500,spent:-500}
      ]}
    ]},accounts:[{id:"checking",name:"Checking",offbudget:false,closed:false}],
    balances:new Map([["checking",30000]]),
    transactionSets:new Map([["checking",[]]]),payees:[]
  });
  snapshot.sourceKey="a".repeat(64);
  const candidate={action:"create",direction:"expense",editing:false,
    sourceKey:snapshot.sourceKey,month,accountId:"checking",date:"2026-11-24",
    description:"Fictional Groceries",amountCents:-1250};
  const proposal={ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
    sourceKey:snapshot.sourceKey,month,accountId:"checking",date:"2026-11-24",
    description:"Fictional Groceries",expenseAmountCents:-1250,
    categoryId:"groceries",categoryName:"Groceries",
    groupId:"needs",groupName:"Needs",availableBeforeCents:7500,
    estimatedAvailableAfterCents:6250,spentBeforeCents:-2500,
    estimatedSpentAfterCents:-3750,estimatedOverspent:false,toBudgetAfterCents:null};
  return {snapshot,candidate,proposal,selectedCategoryId:"groceries"};
}
test("QML offline Save-readiness result is identical to authoritative M3d2 read-only contract",()=>{
  const data=fixture();
  const expected=prepareOfflineCategorizedReview(data);
  const result=qmlReview(data);
  assert.deepEqual(stable(result),stable(expected));
  assert.equal(result.ok,true);
  assert.equal(result.canSave,false);
  assert.equal(result.writeAllowed,false);
  assert.equal(result.requiresFreshActualPreflight,true);
  assert.equal(result.requiresIndependentSecurityReview,true);
  assert.equal("requestId" in result.previewFields,false);
  assert.equal("action" in result.previewFields,false);
  assert.equal("permit" in result,false);
  assert.equal("writeCommand" in result,false);
  const qmlChecked=qmlRecheck({previous:result,...data});
  const nodeChecked=recheckOfflineCategorizedReview({previous:expected,...data});
  assert.deepEqual(stable(qmlChecked),stable(nodeChecked));
  assert.equal(qmlChecked.canSave,false);
});
test("QML and Node refuse stale and malformed visibility/identity/amount identically",()=>{
  const changed=[
    x=>{x.selectedCategoryId="fuel";},
    x=>{delete x.snapshot.categories[0].hidden;},
    x=>{x.snapshot.categoryGroups[0].hidden=null;},
    x=>{x.snapshot.categories[0].hidden=true;},
    x=>{x.snapshot.categoryGroups[0].isIncome=true;},
    x=>{x.snapshot.categories[0].availableCents=400;},
    x=>{x.snapshot.toBudgetCents="11000";},
    x=>{x.snapshot.month="2026-12";},
    x=>{x.candidate.sourceKey="b".repeat(64);},
    x=>{x.candidate.description="Other";},
    x=>{x.candidate.amountCents=-1500;},
    x=>{x.candidate.date="2026-11-31";},
    x=>{x.snapshot.categories.push({...x.snapshot.categories[0]});},
    x=>{x.proposal.writeAllowed=true;},
    x=>{x.proposal.toBudgetAfterCents=100;}
  ];
  for(const change of changed){
    const data=fixture();
    change(data);
    const actual=qmlReview(data),expected=prepareOfflineCategorizedReview(data);
    assert.deepEqual(stable(actual),stable(expected));
    assert.equal(actual.ok,false,JSON.stringify(actual));
    assert.equal(actual.canSave,false);
  }
});
test("rechecks invalidate stale receipt, mutated amount and forged executable field",()=>{
  for(const change of [
    x=>{x.candidate.date="2026-11-23";},
    x=>{x.proposal.categoryId="fuel";},
    x=>{x.snapshot.categories[0].spentCents=-1000;},
    x=>{x.snapshot.sourceKey="c".repeat(64);}
  ]){
    const base=fixture(),receipt=qmlReview(base),updated=fixture();
    change(updated);
    const result=qmlRecheck({previous:receipt,...updated});
    const authoritative=recheckOfflineCategorizedReview({previous:receipt,...updated});
    assert.deepEqual(stable(result),stable(authoritative));
    assert.equal(result.ok,false);
    assert.equal(result.canSave,false);
  }
  const sample=fixture(),review=qmlReview(sample);
  review.previewFields.action="create-categorized-expense";
  assert.equal(qmlRecheck({previous:review,...sample}).canSave,false);
});
