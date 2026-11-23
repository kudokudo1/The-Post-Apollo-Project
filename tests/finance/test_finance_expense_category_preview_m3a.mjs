import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {test} from "node:test";

const source=readFileSync(new URL("../../services/finance/FinanceExpenseCategoryPreview.js",
  import.meta.url),"utf8").replace(/^\.pragma library\s*/,"");
const ctx={};
runInNewContext(source,ctx);
const preview=ctx.previewExpenseCategory;

function snapshot(){
  return {
    schemaVersion:1,source:"actual-budget",readOnly:true,
    sourceKey:"a".repeat(64),month:"2026-11",toBudgetCents:12000,
    accounts:[{id:"checking",name:"Personal Checking",balanceCents:35000}],
    categoryGroups:[{id:"needs",name:"Needs"},{id:"wants",name:"Wants"}],
    categories:[
      {id:"groceries",name:"Groceries",groupId:"needs",
       availableCents:7500,spentCents:-2500,budgetedCents:10000},
      {id:"coffee",name:"Coffee",groupId:"wants",
       availableCents:500,spentCents:-500,budgetedCents:1000},
      {id:"rent",name:"Rent",groupId:"needs",
       availableCents:0,spentCents:-100000,budgetedCents:100000}
    ]
  };
}
function candidate(overrides={}){
  return {
    action:"create",direction:"expense",editing:false,
    sourceKey:"a".repeat(64),month:"2026-11",
    accountId:"checking",date:"2026-11-23",
    description:"Fictional Supermarket",amountCents:-1250,
    ...overrides
  };
}
test("expense category selection estimates available and spent, never writes",()=>{
  const s=snapshot(),d=candidate();
  const oldS=JSON.stringify(s),oldD=JSON.stringify(d);
  const p=preview(s,d,"groceries");
  assert.equal(p.ok,true);
  assert.equal(p.readOnly,true);
  assert.equal(p.savesToActual,false);
  assert.equal(p.writeAllowed,false);
  assert.equal(p.sourceKey,s.sourceKey);
  assert.equal(p.month,"2026-11");
  assert.equal(p.accountName,"Personal Checking");
  assert.equal(p.categoryId,"groceries");
  assert.equal(p.categoryName,"Groceries");
  assert.equal(p.groupName,"Needs");
  assert.equal(p.availableBeforeCents,7500);
  assert.equal(p.estimatedAvailableAfterCents,6250);
  assert.equal(p.spentBeforeCents,-2500);
  assert.equal(p.estimatedSpentAfterCents,-3750);
  assert.equal(p.toBudgetAfterCents,null);
  assert.equal(p.estimatedOverspent,false);
  assert.equal(JSON.stringify(s),oldS);
  assert.equal(JSON.stringify(d),oldD);
});
test("overspent estimate is clear without changing any budget record",()=>{
  const p=preview(snapshot(),candidate({amountCents:-600}),"coffee");
  assert.equal(p.ok,true);
  assert.equal(p.estimatedAvailableAfterCents,-100);
  assert.equal(p.estimatedOverspent,true);
  assert.equal(p.toBudgetAfterCents,null);
});
test("category identity must be unique and group must match exactly once",()=>{
  const dup=snapshot();
  dup.categories.push({...dup.categories[0]});
  assert.equal(preview(dup,candidate(),"groceries").reason,
    "CATEGORY AMBIGUOUS OR UNAVAILABLE");
  const dupGroup=snapshot();
  dupGroup.categoryGroups.push({...dupGroup.categoryGroups[0]});
  assert.equal(preview(dupGroup,candidate(),"groceries").reason,
    "EXPENSE GROUP AMBIGUOUS OR UNAVAILABLE");
  const missingGroup=snapshot();
  missingGroup.categoryGroups=[];
  assert.equal(preview(missingGroup,candidate(),"groceries").ok,false);
  assert.equal(preview(snapshot(),candidate(),"unknown").ok,false);
  assert.equal(preview(snapshot(),candidate(),"").ok,false);
});
test("stale source, invalid and fabricated snapshot refuse",()=>{
  for(const bad of [
    null,{...snapshot(),readOnly:false},{...snapshot(),source:"demo"},
    {...snapshot(),schemaVersion:0},{...snapshot(),sourceKey:"bad"},
    {...snapshot(),month:"2026-13"},{...snapshot(),toBudgetCents:"12000"},
    {...snapshot(),categories:null},{...snapshot(),accounts:null},
    {...snapshot(),categoryGroups:null},
  ])assert.equal(preview(bad,candidate(),"groceries").ok,false);
});
test("new expense draft only: no income, editing, transfers or stale data",()=>{
  for(const change of [
    {action:"update"},{action:"transfer"},{direction:"income"},
    {editing:true},{sourceKey:"b".repeat(64)},{month:"2026-10"},
    {date:"2026-11-31"},{date:"2026-12-01"},
    {date:"2026-11-00"},{date:"not-a-date"},
    {description:" "},{description:"Z".repeat(121)},
    {amountCents:2500},{amountCents:0},{amountCents:-1.5},
    {amountCents:-Infinity},{amountCents:-(99999999999+1)},
  ])assert.equal(preview(snapshot(),candidate(change),"groceries").reason,
    "NEW EXPENSE DRAFT REQUIRED",JSON.stringify(change));
});
test("invalid accounts and corrupt numeric category data refuse",()=>{
  assert.equal(preview(snapshot(),candidate({accountId:"missing"}),"groceries").reason,
    "ACCOUNT UNAVAILABLE");
  const dup=snapshot();dup.accounts.push({...dup.accounts[0]});
  assert.equal(preview(dup,candidate(),"groceries").reason,
    "ACCOUNT UNAVAILABLE");
  const bad=snapshot();
  bad.categories[0].availableCents="7500";
  assert.equal(preview(bad,candidate(),"groceries").reason,
    "INVALID CATEGORY BALANCE");
  const extreme=snapshot();
  extreme.categories[0].availableCents=-99999999999;
  assert.equal(preview(extreme,candidate(),"groceries").reason,
    "PROJECTED AMOUNT EXCEEDS SAFE RANGE");
});
test("policy must not contain any persistence or Actual mutation path",()=>{
  for(const forbidden of [
    "Process {","LocalStorage","fetch(","setBudgetAmount(","addTransactions(",
    "updateTransaction(","writeFile(","saveRequested","FINANCEW_",
    "api.","import ","transaction-writes-enabled","createTransaction("
  ])assert.equal(source.includes(forbidden),false,forbidden);
});
