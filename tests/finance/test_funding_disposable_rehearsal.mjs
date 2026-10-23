import {test} from "node:test";
import assert from "node:assert/strict";
import {
  FundingRehearsalRefusal,validateRehearsalPlan,preflightRehearsal,
  inspectUncertainIncome,executeRehearsal
} from "./fixtures/funding_disposable_rehearsal.mjs";
const accountId="fictional-checking",incomeId="fictional-income";
const key="f".repeat(64);
const income={
  mode:"income",requestId:"a".repeat(32),sourceKey:key,
  accountId,month:"2026-10",date:"2026-10-22",
  amountCents:2200,categoryId:incomeId,description:"FICTIONAL PAY"
};
const opening={mode:"new-account-opening",requestId:"b".repeat(32),sourceKey:key,
  accountName:"FICTIONAL New Account",amountCents:5000};
const fake=(seed=[])=>{
 const calls=[],rows=seed.map(x=>({...x}));
 const accounts=[{id:accountId,name:"FICTIONAL Checking",offbudget:false,closed:false}];
 const balances=new Map([[accountId,0]]);
 let syncError=false;
 const api={
  getAccounts:async()=>accounts,
  getBudgetMonth:async()=>({categoryGroups:[
    {is_income:true,categories:[{id:incomeId,name:"Income"}]}
  ]}),
  getTransactions:async()=>rows,
  getAccountBalance:async id=>balances.get(id),
  createAccount:async (account,initialBalance)=>{
   calls.push("create-account");
   const id="fictional-new-account-id";
   accounts.push({id,...account});
   balances.set(id,initialBalance);
   return id;
  },
  addTransactions:async (acct,txs,opts)=>{
   calls.push("add");
   assert.equal(acct,accountId);
   assert.deepEqual(opts,{runTransfers:false,learnCategories:false});
   rows.push({...txs[0],account:acct});
   return "ok";
  },
  sync:async()=>{calls.push("sync");if(syncError)throw Error("fictional-sync-interrupted");}
 };
 return {api,accounts,rows,balances,calls,breakSync:()=>{syncError=true;}};
};
const withCI=async cb=>{
 const keys=["CI","GITHUB_ACTIONS","FINANCEW_DISPOSABLE_TEST"];
 const original=keys.map(k=>process.env[k]);
 keys.forEach((k,i)=>process.env[k]=["true","true","yes"][i]);
 try{return await cb();}
 finally{keys.forEach((k,i)=>original[i]===undefined
    ?delete process.env[k]:process.env[k]=original[i]);}
};
test("no write rehearsal can run without GitHub disposable CI guard",async()=>{
 const f=fake();let attempts=0;
 const old=process.env.FINANCEW_DISPOSABLE_TEST;
 delete process.env.FINANCEW_DISPOSABLE_TEST;
 try {
  await assert.rejects(()=>executeRehearsal({api:f.api,input:income,
    expectedSourceKey:key,recordAttempt:async()=>{attempts++;}}),
    /disposable-ci-only/);
  assert.deepEqual(f.calls,[]);
  assert.equal(attempts,0);
 }finally{if(old!==undefined)process.env.FINANCEW_DISPOSABLE_TEST=old;}
});
test("existing-account opening balance is refused without bank reconciliation",()=>{
 assert.throws(()=>validateRehearsalPlan({
  mode:"existing-account-opening",...income
 }),/existing-opening-requires-bank-reconciliation/);
});
test("strict command and date/amount/category validation",()=>{
 assert.deepEqual(validateRehearsalPlan(income),income);
 for(const invalid of [
  {date:"2026-02-30"},{date:"2026-11-02"},{amountCents:0},
  {amountCents:-500},{amountCents:1.2},{categoryId:""},
  {description:" "},{requestId:"bad"},{sourceKey:"bad"},
  {extra:"must-refuse"},{mode:"create-account"}
 ])assert.throws(()=>validateRehearsalPlan({...income,...invalid}));
});
test("stale source, account and income category stop before recording",async()=>{
 const f=fake();
 await assert.rejects(()=>preflightRehearsal({api:f.api,input:income,
   expectedSourceKey:"c".repeat(64)}),/budget-source-changed/);
 await assert.rejects(()=>preflightRehearsal({api:f.api,
   input:{...income,accountId:"other-account"},expectedSourceKey:key}),/stale-account/);
 await assert.rejects(()=>preflightRehearsal({api:f.api,
   input:{...income,categoryId:"other-category"},expectedSourceKey:key}),/stale-income-category/);
 assert.deepEqual(f.calls,[]);
});
test("fake income creates once after attempt; duplicate blocks another mutation",async()=>{
 await withCI(async()=>{
  const f=fake();let attempts=0;
  const result=await executeRehearsal({api:f.api,input:income,
    expectedSourceKey:key,recordAttempt:async()=>{attempts++;}});
  assert.equal(result.status,"committed");
  assert.equal(attempts,1);
  assert.deepEqual(f.calls,["add","sync"]);
  assert.equal(f.rows.length,1);
  assert.equal(f.rows[0].amount,2200);
  assert.equal(f.rows[0].category,incomeId);
  assert.equal((await inspectUncertainIncome({api:f.api,input:income})).status,"observed");
  await assert.rejects(()=>executeRehearsal({api:f.api,
    input:{...income,requestId:"c".repeat(32)},expectedSourceKey:key,
    recordAttempt:async()=>{attempts++;}}),/possible-duplicate-income/);
  assert.equal(attempts,1);
  assert.deepEqual(f.calls,["add","sync"]);
 });
});
test("attempt journal failure prevents first Actual mutation",async()=>{
 await withCI(async()=>{
  const f=fake();
  await assert.rejects(()=>executeRehearsal({api:f.api,input:income,
    expectedSourceKey:key,recordAttempt:async()=>{throw Error("journal-unavailable");}}),
    /journal-unavailable/);
  assert.deepEqual(f.calls,[]);
 });
});
test("sync failure is uncertain; read-only inspection observes it, never auto-retries",async()=>{
 await withCI(async()=>{
  const f=fake();f.breakSync();let attempts=0;
  await assert.rejects(()=>executeRehearsal({api:f.api,input:income,
    expectedSourceKey:key,recordAttempt:async()=>{attempts++;}}),
    /fictional-sync-interrupted/);
  assert.equal(attempts,1);
  assert.deepEqual(f.calls,["add","sync"]);
  const read=await inspectUncertainIncome({api:f.api,input:income});
  assert.deepEqual(read,{status:"observed",manualReviewRequired:true});
  await assert.rejects(()=>preflightRehearsal({api:f.api,input:income,
    expectedSourceKey:key}),/possible-duplicate-income/);
 });
});
test("unobserved request never authorizes a retry",async()=>{
 const f=fake();
 assert.deepEqual(await inspectUncertainIncome({api:f.api,input:income}),
   {status:"not-seen",manualReviewRequired:true});
});
test("fresh-account opening balance uses Actual initialBalance exactly once",async()=>{
 await withCI(async()=>{
  const f=fake();let attempts=0;
  const result=await executeRehearsal({api:f.api,input:opening,
    expectedSourceKey:key,recordAttempt:async()=>{attempts++;}});
  assert.equal(result.status,"committed");
  assert.equal(attempts,1);
  assert.deepEqual(f.calls,["create-account","sync"]);
  assert.equal(f.balances.get(result.accountId),opening.amountCents);
  await assert.rejects(()=>preflightRehearsal({api:f.api,input:{
    ...opening,requestId:"e".repeat(32)},expectedSourceKey:key}),/possible-existing-account/);
 });
});
