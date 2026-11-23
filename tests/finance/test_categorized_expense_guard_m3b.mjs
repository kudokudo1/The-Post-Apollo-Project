import {test} from "node:test";
import assert from "node:assert/strict";
import {validateCategorizedExpenseCommand,preflightCategorizedExpense,
        executeCategorizedExpense,CategorizedExpenseRefusal}
  from "../../scripts/finance/categorized_expense_guard.mjs";

const accountId="fictional-checking", categoryId="fictional-groceries";
function command(overrides={}) {
  return {action:"create-categorized-expense",requestId:"a".repeat(32),
    sourceKey:"b".repeat(64),accountId,month:"2026-11",
    date:"2026-11-23",description:" Fictional Groceries ",
    amountCents:-1250,categoryId,expectedCategoryBudgetedCents:10000,
    expectedCategoryAvailableCents:7500,expectedCategorySpentCents:-2500,
    expectedToBudgetCents:12000,...overrides};
}
function budget(){
  return {toBudget:12000,categoryGroups:[
    {name:"Needs",is_income:false,categories:[
      {id:categoryId,name:"Groceries",budgeted:10000,balance:7500,spent:-2500}
    ]},
    {name:"Income",is_income:true,categories:[
      {id:"fictional-income",name:"Income",budgeted:0,balance:0,spent:0}
    ]}
  ]};
}
function mock({ack="ok",failBeforeAdd=false,failSync=false,
               wrongCategory=false,noId=false,missingImported=false,
               badAfterBudget=false}={}){
  const state={accounts:[{id:accountId,name:"Checking",offbudget:false,closed:false}],
    budget:budget(),transactions:[],events:[]};
  const api={
    async getAccounts(){state.events.push("get-accounts");return structuredClone(state.accounts);},
    async getBudgetMonth(){state.events.push("get-budget");return badAfterBudget
      &&state.transactions.length
      ? {...structuredClone(state.budget),categoryGroups:[]}
      : structuredClone(state.budget);},
    async getTransactions(){state.events.push("get-rows");return structuredClone(state.transactions);},
    async addTransactions(account,records,options){
      state.events.push("add");
      if(failBeforeAdd)throw Error("injected-add-failure");
      assert.equal(account,accountId);
      assert.deepEqual(options,{runTransfers:false,learnCategories:false});
      assert.equal(records.length,1);
      const t={...records[0],account};
      if(wrongCategory)t.category="fictional-coffee";
      if(noId)t.id="different-id";
      if(missingImported)delete t.imported_id;
      state.transactions.push(t);
      return ack;
    },
    async sync(){
      state.events.push("sync");
      if(failSync)throw Error("injected-sync-failure");
    }
  };
  return {api,recordAttempt:async()=>{state.events.push("attempted");},
    state,initial:()=>structuredClone(state)};
}
async function refusal(code,fn){
  await assert.rejects(fn,e=>e instanceof CategorizedExpenseRefusal
    &&e.code===code);
}
test("one categorized Actual create, one sync, exact category ID readback",async()=>{
  const m=mock();
  const original=command();
  const done=await executeCategorizedExpense({
    api:m.api,input:original,recordAttempt:m.recordAttempt});
  assert.equal(done.status,"committed");
  assert.equal(m.state.transactions.length,1);
  assert.equal(m.state.transactions[0].category,categoryId);
  assert.equal(m.state.transactions[0].amount,-1250);
  assert.equal(m.state.transactions[0].payee_name,"Fictional Groceries");
  assert.equal(m.state.transactions[0].imported_id,"financew-cat-"+original.requestId);
  assert.deepEqual(m.state.events,[
    "get-accounts","get-budget","get-rows","attempted",
    "add","sync","get-rows","get-budget"
  ]);
  assert.equal(m.state.budget.toBudget,12000);
});
test("rejects malformed or expanded commands before any API contact",async()=>{
  for(const bad of [
    null,[],{...command(),extra:true},
    command({action:"update"}),command({requestId:"broken"}),
    command({sourceKey:"wrong"}),command({accountId:"?"}),
    command({categoryId:"?"}),command({month:"2026-13"}),
    command({date:"2026-11-31"}),command({date:"2026-12-01"}),
    command({description:" "}),command({description:"z".repeat(121)}),
    command({amountCents:1250}),command({amountCents:0}),
    command({amountCents:-1.2}),command({amountCents:-Infinity}),
    command({amountCents:-100000000000}),command({expectedToBudgetCents:"12000"}),
    command({expectedCategorySpentCents:Infinity}),command({original:{}}),
    command({transactionId:"example"})
  ]){
    const m=mock();
    await assert.rejects(()=>executeCategorizedExpense({
      api:m.api,input:bad,recordAttempt:m.recordAttempt}),
    CategorizedExpenseRefusal);
    assert.deepEqual(m.state.events,[]);
  }
});
test("stale amounts, duplicate expense and source categories fail pre-attempt",async()=>{
  const m=mock();
  m.state.budget.categoryGroups[0].categories[0].balance=7499;
  await refusal("stale-budget",()=>executeCategorizedExpense({
    api:m.api,input:command(),recordAttempt:m.recordAttempt}));
  assert.ok(!m.state.events.includes("attempted"));
  const b=budget();b.categoryGroups[0].categories.push({
    ...b.categoryGroups[0].categories[0]
  });
  assert.throws(()=>preflightCategorizedExpense(command(),{
    accounts:[{id:accountId}],budget:b,rows:[]}),
    e=>e.code==="category-unavailable");
  const hidden=budget();
  hidden.categoryGroups[0].categories[0].hidden=true;
  assert.throws(()=>preflightCategorizedExpense(command(),{
    accounts:[{id:accountId}],budget:hidden,rows:[]}),
    e=>e.code==="hidden-category");
  const income=command({categoryId:"fictional-income",
    expectedCategoryBudgetedCents:0,expectedCategoryAvailableCents:0,
    expectedCategorySpentCents:0});
  assert.throws(()=>preflightCategorizedExpense(income,{
    accounts:[{id:accountId}],budget:budget(),rows:[]}),
    e=>e.code==="category-unavailable");
});
test("disallows closed/offbudget accounts, duplicate accounts, duplicate day+amount",()=>{
  const input=command();
  for(const accounts of [
    [],[{id:accountId,closed:true}], [{id:accountId,offbudget:true}],
    [{id:accountId},{id:accountId}]
  ])assert.throws(()=>preflightCategorizedExpense(input,{accounts,budget:budget(),rows:[]}),
    e=>e.code==="stale-account");
  const duplicate={date:input.date,amount:input.amountCents,
    category:"other",imported_id:"not-the-same"};
  assert.throws(()=>preflightCategorizedExpense(input,{
    accounts:[{id:accountId}],budget:budget(),rows:[duplicate]}),
    e=>e.code==="possible-duplicate");
  assert.throws(()=>preflightCategorizedExpense(input,{
    accounts:[{id:accountId}],budget:budget(),
    rows:[{imported_id:"financew-cat-"+input.requestId}]}),
    e=>e.code==="possible-duplicate");
});
test("preflight does not change the source budget, accounts, transactions",()=>{
  const a=[{id:accountId}],b=budget(),rows=[];
  const before=JSON.stringify({a,b,rows});
  const checked=preflightCategorizedExpense(command(),{
    accounts:a,budget:b,rows});
  assert.equal(checked.cmd.amountCents,-1250);
  assert.equal(checked.importedId,"financew-cat-"+command().requestId);
  assert.equal(JSON.stringify({a,b,rows}),before);
});
test("attempt durability failure prevents add and sync",async()=>{
  const m=mock();
  await assert.rejects(()=>executeCategorizedExpense({
    api:m.api,input:command(),recordAttempt:async()=>{
      throw Error("injected-journal-fsync-error");
    }}),/injected-journal-fsync-error/);
  assert.ok(!m.state.events.includes("add"));
  assert.ok(!m.state.events.includes("sync"));
});
test("after attempted write, failure never becomes a committed result",async()=>{
  for(const opts of [
    {failBeforeAdd:true},{failSync:true},{ack:"unexpected"},
    {wrongCategory:true},{noId:true},{missingImported:true},
    {badAfterBudget:true}
  ]){
    const m=mock(opts);
    await assert.rejects(()=>executeCategorizedExpense({
      api:m.api,input:command(),recordAttempt:m.recordAttempt}));
    assert.ok(m.state.events.includes("attempted"));
  }
});
test("matching API 'ok' and [id] accepted; unknown acknowledgments refused",async()=>{
  const req=command(),id=[
    req.requestId.slice(0,8),req.requestId.slice(8,12),
    "4"+req.requestId.slice(13,16),
    "8"+req.requestId.slice(17,20),req.requestId.slice(20,32)].join("-");
  const m=mock({ack:[id]});
  assert.equal((await executeCategorizedExpense({
    api:m.api,input:req,recordAttempt:m.recordAttempt})).status,"committed");
  const failed=mock({ack:[id,"extra"]});
  await refusal("uncertain-write",()=>executeCategorizedExpense({
    api:failed.api,input:req,recordAttempt:failed.recordAttempt}));
});
