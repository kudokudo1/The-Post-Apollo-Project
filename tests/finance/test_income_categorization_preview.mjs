import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {summarizeIncomeCandidates,previewIncomeCategory}
  from "../../scripts/finance/income_categorization_preview.mjs";

function fixture() {
  return {
    month:"2026-10",
    budget:{categoryGroups:[
      {name:"Expenses",is_income:false,categories:[{id:"food",name:"Food"}]},
      {name:"Income",is_income:true,categories:[{id:"salary",name:"Income"}]}
    ]},
    accounts:[{id:"checking",name:"Fictional Checking",offbudget:false,closed:false},
      {id:"off",name:"Investment",offbudget:true,closed:false}],
    transactionSets:new Map([["checking",[
      {id:"a",date:"2026-10-03",account:"checking",amount:15000},
      {id:"b",date:"2026-10-10",account:"checking",amount:25000,category:"salary"},
      {id:"c",date:"2026-10-05",account:"checking",amount:6000,transfer_id:"transfer"},
      {id:"d",date:"2026-10-06",account:"checking",amount:4000,is_parent:true},
      {id:"e",date:"2026-10-07",account:"checking",amount:1100,category_id:"food"},
      {id:"f",date:"2026-10-08",account:"checking",amount:-1500},
      {id:"g",date:"2026-10-09",account:"checking",amount:3000}
    ]],["off",[{id:"h",date:"2026-10-11",amount:100000}] ]])
  };
}
test("only positive uncategorized non-transfer items appear as potential review candidates",()=>{
  const f=fixture(),before=JSON.stringify(f.transactionSets.get("checking"));
  const r=summarizeIncomeCandidates(f);
  assert.equal(r.readOnly,true);
  assert.equal(r.categorizationVerified,false);
  assert.equal(r.completeness,"selected-month-review");
  assert.equal(r.candidateCount,2);
  assert.deepEqual(r.candidates.map(x=>x.id),["g","a"]);
  assert.equal(r.incomeCategories.length,1);
  assert.equal(r.incomeCategories[0].id,"salary");
  assert.equal(JSON.stringify(f.transactionSets.get("checking")),before);
  assert.equal(r.truncated,false);
});
test("preview includes source, exact category and leaves To Budget unknown",()=>{
  const f=fixture();
  const incomeReview=summarizeIncomeCandidates(f);
  const snapshot={source:"actual-budget",readOnly:true,
    sourceKey:"a".repeat(64),month:f.month,incomeReview};
  const before=JSON.stringify(snapshot);
  const p=previewIncomeCategory(snapshot,"a","checking","salary");
  assert.equal(p.ok,true);
  assert.equal(p.amountCents,15000);
  assert.equal(p.proposedCategory,"Income");
  assert.equal(p.currentCategory,"UNCATEGORIZED");
  assert.equal(p.writeAllowed,false);
  assert.equal(p.toBudgetAfterCents,null);
  assert.equal(JSON.stringify(snapshot),before);
});
test("preview rejects wrong account, source, month and arbitrary category",()=>{
  const f=fixture(),review=summarizeIncomeCandidates(f);
  const snap={source:"actual-budget",readOnly:true,
    sourceKey:"b".repeat(64),month:f.month,incomeReview:review};
  assert.equal(previewIncomeCategory(snap,"a","off","salary").ok,false);
  assert.equal(previewIncomeCategory(snap,"a","checking","food").ok,false);
  assert.equal(previewIncomeCategory({...snap,month:"2026-09"},
    "a","checking","salary").ok,false);
  assert.equal(previewIncomeCategory({...snap,sourceKey:""},
    "a","checking","salary").ok,false);
});
test("long candidate list is capped and explicitly marked incomplete",()=>{
  const f=fixture();const many=Array.from({length:19},(_,i)=>({
    id:"t"+i,date:"2026-10-18",amount:100+i
  }));
  f.transactionSets.set("checking",many);
  const r=summarizeIncomeCandidates(f);
  assert.equal(r.candidateCount,19);
  assert.equal(r.showingCount,12);
  assert.equal(r.truncated,true);
  assert.equal(r.candidates.length,12);
});
test("income category overflow forbids an arbitrary partial target list",()=>{
  const f=fixture();
  f.budget.categoryGroups[1].categories=Array.from({length:25},(_,i)=>({
    id:"income"+i,name:"Income "+i
  }));
  const r=summarizeIncomeCandidates(f);
  assert.equal(r.categoriesOverflow,true);
  assert.equal(r.incomeCategories.length,0);
  assert.equal(previewIncomeCategory({source:"actual-budget",readOnly:true,
    sourceKey:"c".repeat(64),month:f.month,incomeReview:r},
    "a","checking","income0").ok,false);
});
test("missing optional income category names do not crash source read",()=>{
  const f=fixture();
  f.budget.categoryGroups[1].categories.push({id:"unnamed"});
  const r=summarizeIncomeCandidates(f);
  assert.deepEqual(r.incomeCategories.map(x=>x.id),["salary"]);
});
test("duplicate candidate IDs and mismatched accounts fail closed",()=>{
  const f=fixture();
  const first=f.transactionSets.get("checking")[0];
  f.transactionSets.get("checking").push({...first});
  assert.throws(()=>summarizeIncomeCandidates(f),/income-review-duplicate/);
  const g=fixture();
  g.transactionSets.get("checking")[0].account="another-account";
  assert.throws(()=>summarizeIncomeCandidates(g),/income-review-account-mismatch/);
});
test("policy code has no financial mutator or persistent storage",()=>{
  const src=readFileSync(fileURLToPath(new URL(
    "../../scripts/finance/income_categorization_preview.mjs",import.meta.url)),"utf8");
  for(const forbidden of ["@actual-app/api","setBudgetAmount(","updateTransaction(",
    "addTransactions(","writeFile(","LocalStorage","Process {","exec("])
    assert.ok(!src.includes(forbidden),forbidden);
});
