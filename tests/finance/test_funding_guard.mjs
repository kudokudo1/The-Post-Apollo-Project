import {test} from "node:test";
import assert from "node:assert/strict";
import {validateFundingCommand,preflightFunding,executeFunding,FundingRefusal}
  from "../../scripts/finance/funding_guard.mjs";

const key="f".repeat(64),month="2026-10",accountId="fictional-checking",categoryId="fictional-income";
const income={
 mode:"income",requestId:"a".repeat(32),sourceKey:key,accountId,month,
 date:"2026-10-22",amountCents:2500,categoryId,description:"FICTIONAL INCOME"
};
const account={
 mode:"new-account-opening",requestId:"b".repeat(32),sourceKey:key,
 accountName:"FICTIONAL NEW BANK",amountCents:5000
};
function fixture(seed=[]) {
 const rows=seed.map(x=>({...x})),calls=[];
 const accounts=[{id:accountId,name:"FICTIONAL CHECKING",offbudget:false,closed:false}];
 const balances=new Map([[accountId,0]]);
 const api={
  getAccounts:async()=>accounts,
  getBudgetMonth:async()=>({categoryGroups:[
   {is_income:true,categories:[{id:categoryId,name:"Income"}]}
  ]}),
  getTransactions:async()=>rows,
  getAccountBalance:async id=>balances.get(id),
  createAccount:async (data,value)=>{
   calls.push("createAccount");
   accounts.push({id:"fictional-created-bank",...data});
   balances.set("fictional-created-bank",value);
   return "fictional-created-bank";
  },
  addTransactions:async(id,transactions,opts)=>{
   calls.push("addTransactions");
   assert.equal(id,accountId);
   assert.deepEqual(opts,{runTransfers:false,learnCategories:false});
   rows.push({...transactions[0],account:id});
   return "ok";
  },
  sync:async()=>{calls.push("sync");}
 };
 return {api,calls,rows,accounts,balances};
}
test("strict command validation and no implied opening of existing accounts",()=>{
 assert.deepEqual(validateFundingCommand(income),income);
 assert.deepEqual(validateFundingCommand(account),account);
 for(const change of [{date:"2026-02-31"},{date:"2026-09-01"},
  {categoryId:""},{amountCents:0},{amountCents:1.5},{amountCents:-10},
  {amountCents:100000000000},{requestId:"bad"},{sourceKey:"bad"},
  {description:" "},{accountId:""},{mode:"existing-account-opening"},
  {unknown:"field"}]){
   assert.throws(()=>validateFundingCommand({...income,...change}));
 }
});
test("stale account, stale income category and unrecognized account refuse",async()=>{
 const f=fixture();
 await assert.rejects(()=>preflightFunding(f.api,{...income,accountId:"other"}),/stale-account/);
 await assert.rejects(()=>preflightFunding(f.api,{...income,categoryId:"other-id"}),/stale-income-category/);
 await assert.rejects(()=>preflightFunding(f.api,{...account,accountName:"fictional checking"}),/possible-existing-account/);
 assert.deepEqual(f.calls,[]);
});
test("identical amount and date refuse duplicate even if description/category differ",async()=>{
 const f=fixture([{id:"original",date:income.date,amount:income.amountCents,category:"different"}]);
 await assert.rejects(()=>preflightFunding(f.api,income),/possible-duplicate-income/);
 assert.deepEqual(f.calls,[]);
});
test("journal error prevents any mutation",async()=>{
 const f=fixture();
 await assert.rejects(()=>executeFunding({
  api:f.api,input:income,recordAttempt:async()=>{throw Error("journal-failed");}
 }),/journal-failed/);
 assert.deepEqual(f.calls,[]);
});
test("guarded income inserts categorized transaction once and verifies result",async()=>{
 const f=fixture();let recorded=0;
 const result=await executeFunding({api:f.api,input:income,
  recordAttempt:async()=>{recorded++;}});
 assert.deepEqual(result,{status:"committed"});
 assert.equal(recorded,1);
 assert.deepEqual(f.calls,["addTransactions","sync"]);
 assert.equal(f.rows[0].category,categoryId);
 assert.equal(f.rows[0].amount,income.amountCents);
 assert.equal(f.rows[0].imported_id,"financew-funding-"+income.requestId);
 await assert.rejects(()=>executeFunding({
  api:f.api,input:{...income,requestId:"c".repeat(32)},
  recordAttempt:async()=>{recorded++;}
 }),/possible-duplicate-income/);
 assert.equal(recorded,1);
});
test("new-account initial balance is created once and existing account name blocks",async()=>{
 const f=fixture();let recorded=0;
 assert.deepEqual(await executeFunding({api:f.api,input:account,
  recordAttempt:async()=>{recorded++;}}),{status:"committed"});
 assert.deepEqual(f.calls,["createAccount","sync"]);
 assert.equal(recorded,1);
 assert.equal(f.balances.get("fictional-created-bank"),5000);
 await assert.rejects(()=>executeFunding({api:f.api,
  input:{...account,requestId:"c".repeat(32)},
  recordAttempt:async()=>{recorded++;}}),/possible-existing-account/);
 assert.equal(recorded,1);
});
test("failed sync after insertion is uncertain to caller, never retried by policy",async()=>{
 const f=fixture();
 f.api.sync=async()=>{f.calls.push("sync");throw Error("interrupted");};
 let attempts=0;
 await assert.rejects(()=>executeFunding({api:f.api,input:income,
  recordAttempt:async()=>{attempts++;}}),/interrupted/);
 assert.deepEqual(f.calls,["addTransactions","sync"]);
 assert.equal(attempts,1);
 await assert.rejects(()=>preflightFunding(f.api,income),/possible-duplicate-income/);
});
test("missing required injected methods refuse before journal",async()=>{
 const f=fixture();let attempts=0;
 delete f.api.createAccount;
 await assert.rejects(()=>executeFunding({api:f.api,input:income,
  recordAttempt:async()=>{attempts++;}}),/missing-write-guards/);
 assert.equal(attempts,0);
});
