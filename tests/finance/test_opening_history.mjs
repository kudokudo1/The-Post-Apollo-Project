import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {summarizeOpeningHistory,takeOpeningHistory}
  from "../../scripts/finance/opening_history.mjs";

const month="2026-10";
function fixture(){
 return {
   month,
   accounts:[
     {id:"checking",name:"Fictional Checking",offbudget:false,closed:false},
     {id:"investment",name:"Off-Budget",offbudget:true,closed:false}
   ],
   categories:[{id:"initial",name:"Starting Balances"},
     {id:"income",name:"Income"}],
   transactionSets:new Map([["checking",[
     {id:"b",account:"checking",date:"2020-05-04",amount:50000,category:"initial"},
     {id:"c",account:"checking",date:"2020-06-02",amount:-5000,category:"income"},
     {id:"a",account:"checking",date:"2020-05-03",amount:1000},
     {id:"x",account:"checking",date:"2025-06-03",amount:900,transfer_id:"tr",category:"initial"}
   ]]])
 };
}
test("earliest transaction is observation, named starting balances are unverified candidates",()=>{
 const f=fixture(),original=JSON.stringify(f.transactionSets.get("checking"));
 const out=summarizeOpeningHistory(f);
 assert.equal(out.readOnly,true);
 assert.equal(out.kind,"financew-opening-history");
 assert.equal(out.scanFrom,"1900-01-01");
 assert.equal(out.openingBalancesVerified,false);
 assert.equal(out.completeness,"ledger-observation-only");
 assert.equal(out.recordsInspected,4);
 assert.equal(out.accounts.length,1);
 const a=out.accounts[0];
 assert.equal(a.firstRecordedDate,"2020-05-03");
 assert.equal(a.firstRecordedAmountCents,1000);
 assert.equal(a.startingBalanceCandidateCount,1);
 assert.equal(a.startingBalanceCandidateCents,50000);
 assert.equal(a.openingBalanceVerified,false);
 assert.equal(JSON.stringify(f.transactionSets.get("checking")),original);
});
test("missing starting balance category is NOT the same as zero starting balance",()=>{
 const f=fixture();f.categories=[];
 const out=summarizeOpeningHistory(f).accounts[0];
 assert.equal(out.startingBalanceCandidateCount,0);
 assert.equal(out.startingBalanceCandidateCents,null);
 assert.equal(out.openingBalanceVerified,false);
});
test("no ledger rows cannot verify a zero opening balance",()=>{
 const f=fixture();f.transactionSets.set("checking",[]);
 const out=summarizeOpeningHistory(f).accounts[0];
 assert.equal(out.firstRecordedDate,null);
 assert.equal(out.firstRecordedAmountCents,null);
 assert.equal(out.startingBalanceCandidateCents,null);
 assert.equal(out.openingBalanceVerified,false);
});
test("history limits, bad dates, duplicates and unsafe amounts refuse",()=>{
 const bad=(rows)=>{const f=fixture();f.transactionSets.set("checking",rows);return f;};
 const one=fixture().transactionSets.get("checking")[0];
 for(const rows of [
   [{...one,date:"1899-12-31"}],
   [{...one,date:"2026-11-02"}],
   [{...one,amount:1.5}],
   [one,one],
   Array.from({length:10001},(_,i)=>({...one,id:"t"+i}))
 ])assert.throws(()=>summarizeOpeningHistory(bad(rows)));
 const f=fixture();f.accounts.push({...f.accounts[0]});
 assert.throws(()=>summarizeOpeningHistory(f),/invalid-history-account/);
});
test("on-demand adapter calls only supported getters on active accounts",async()=>{
 const f=fixture(),names=[];
 const api={
   getAccounts:async()=>{names.push("getAccounts");return f.accounts;},
   getCategories:async()=>{names.push("getCategories");return f.categories;},
   getTransactions:async(id,start,end)=>{
     names.push("getTransactions");
     assert.equal(id,"checking");
     assert.equal(start,"1900-01-01");
     assert.equal(end,"2026-10-31");
     return f.transactionSets.get(id);
   }
 };
 const out=await takeOpeningHistory(api,month);
 assert.equal(out.accounts.length,1);
 assert.deepEqual(names,["getAccounts","getCategories","getTransactions"]);
});
test("historical inspection modules cannot mutate Actual or persist financial information",()=>{
 const files=["../../scripts/finance/opening_history.mjs",
              "../../scripts/finance/read_opening_history.mjs"];
 for(const file of files){
   const source=readFileSync(fileURLToPath(new URL(file,import.meta.url)),"utf8");
   for(const token of ["setBudgetAmount(", "updateTransaction(","createAccount(",
     "addTransactions(","importTransactions(","batchBudgetUpdates(",
     "transaction-writes-enabled","allocation-writes-enabled"])
     assert.equal(source.includes(token),false,file+" "+token);
 }
});
