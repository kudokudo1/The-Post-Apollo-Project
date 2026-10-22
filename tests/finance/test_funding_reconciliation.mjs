import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {summarizeFunding} from "../../scripts/finance/funding_reconciliation.mjs";

function fixture() {
  return {
    month:"2026-10",
    budget:{toBudget:0,categoryGroups:[
      {is_income:true,categories:[{id:"pay",spent:50000},{id:"side",spent:5000}]},
      {is_income:false,categories:[{id:"groceries",spent:-19000}]}
    ]},
    accounts:[{id:"main",closed:false,offbudget:false},
      {id:"off",closed:false,offbudget:true},{id:"closed",closed:true}],
    balances:new Map([["main",75000],["off",1000000]]),
    transactionSets:new Map([["main",[
      {id:"salary",date:"2026-10-20",amount:50000,category:"pay"},
      {id:"unassigned",date:"2026-10-21",amount:10000},
      {id:"refund",date:"2026-10-22",amount:5000,category_id:"groceries"},
      {id:"spent",date:"2026-10-18",amount:-2200},
      {id:"transfer",date:"2026-10-18",amount:14000,transfer_id:"t"},
      {id:"split",date:"2026-10-18",amount:17000,subtransactions:[{amount:17000}]}
    ]]])
  };
}
test("month income activity and uncategorized positive items are separate facts",()=>{
  const f=fixture(),before=JSON.stringify({
    budget:f.budget,accounts:f.accounts,
    transactions:f.transactionSets.get("main")});
  const r=summarizeFunding(f);
  assert.equal(r.month,"2026-10");
  assert.equal(r.incomeCategoryCount,2);
  assert.equal(r.incomeCategoryActivityCents,55000);
  assert.equal(r.positiveUncategorizedCount,1);
  assert.equal(r.positiveUncategorizedCents,10000);
  assert.equal(r.accountBalanceCents,75000);
  assert.equal(r.toBudgetCents,0);
  assert.equal(r.openingBalancesVerified,false);
  assert.equal(r.completeness,"monthly-review-only");
  assert.equal(JSON.stringify({budget:f.budget,accounts:f.accounts,
    transactions:f.transactionSets.get("main")}),before);
});
test("uncategorized positive amounts are flags, never magically credited to To Budget",()=>{
  const f=fixture();
  f.transactionSets.get("main").push({id:"large",date:"2026-10-17",amount:25000});
  const r=summarizeFunding(f);
  assert.equal(r.positiveUncategorizedCents,35000);
  assert.equal(r.toBudgetCents,0);
  assert.equal(r.openingBalancesVerified,false);
});
test("no income category is reported, not treated as zero verified income",()=>{
  const f=fixture();f.budget.categoryGroups[0].categories=[];
  const r=summarizeFunding(f);
  assert.equal(r.incomeCategoryCount,0);
  assert.equal(r.incomeCategoryActivityCents,0);
  assert.equal(r.openingBalancesVerified,false);
});
test("split parents, transfers, categorized receipts and off-budget accounts not flagged",()=>{
  const f=fixture();
  f.transactionSets.set("main",[
    {id:"transfer",date:"2026-10-12",amount:1000,transfer_id:"x"},
    {id:"parent",date:"2026-10-12",amount:1000,is_parent:true},
    {id:"split",date:"2026-10-12",amount:1000,subtransactions:[{amount:1000}]},
    {id:"refund",date:"2026-10-12",amount:1000,category_id:"groceries"}
  ]);
  f.transactionSets.set("off",[{id:"off",date:"2026-10-12",amount:50000}]);
  const r=summarizeFunding(f);
  assert.equal(r.positiveUncategorizedCount,0);
  assert.equal(r.positiveUncategorizedCents,0);
  assert.equal(r.accountCount,1);
});
test("invalid sums and malformed transactional amounts fail closed",()=>{
  const f=fixture();
  f.budget.categoryGroups[0].categories[0].spent=0.5;
  assert.throws(()=>summarizeFunding(f),/invalid-funding-income/);
  const b=fixture();
  b.transactionSets.get("main")[1].amount=NaN;
  assert.throws(()=>summarizeFunding(b),/invalid-funding-transaction/);
  const c=fixture();
  c.budget.categoryGroups[0].categories[0].spent=Number.MAX_SAFE_INTEGER;
  assert.throws(()=>summarizeFunding(c),/invalid-funding-total/);
});
test("funding summary cannot call Actual or write files",()=>{
  const src=readFileSync(fileURLToPath(new URL(
    "../../scripts/finance/funding_reconciliation.mjs",import.meta.url)),"utf8");
  for(const forbidden of ["@actual-app/api","setBudgetAmount","writeFile",
    "fetch(","Process {","createAccount(","addTransactions(",
    "updateTransaction(","exec("])assert.equal(src.includes(forbidden),false,forbidden);
});
