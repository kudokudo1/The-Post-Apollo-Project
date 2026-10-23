import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {fileURLToPath} from "node:url";

const file=fileURLToPath(new URL("../../services/finance/FinanceFundingSetupPlan.js",import.meta.url));
const source=readFileSync(file,"utf8");
const policy=runInNewContext(source+";({parseFundingAmountCents,validFundingDate,previewFundingSetup});",{Date});
function snapshot(){
 return {schemaVersion:1,source:"actual-budget",readOnly:true,
   sourceKey:"a".repeat(64),month:"2026-10",toBudgetCents:0,
   accounts:[{id:"fictional-checking",name:"FICTIONAL Checking",balanceCents:0}],
   incomeReview:{readOnly:true,month:"2026-10",categoriesOverflow:false,
     incomeCategories:[{id:"salary",name:"Income"}]}
 };
}
function preview(mode,overrides={}){
 const s=overrides.snapshot||snapshot();
 return policy.previewFundingSetup(s,mode,
   overrides.accountId===undefined?"fictional-checking":overrides.accountId,
   overrides.date===undefined?"2026-10-20":overrides.date,
   overrides.amount===undefined?"100.25":overrides.amount,
   overrides.categoryId===undefined?"salary":overrides.categoryId);
}
test("income plan uses an existing Actual category but does not credit To Budget",()=>{
 const s=snapshot(),before=JSON.stringify(s);
 const p=preview("income",{snapshot:s});
 assert.equal(p.ok,true);
 assert.equal(p.amountCents,10025);
 assert.equal(p.categoryId,"salary");
 assert.equal(p.mode,"income");
 assert.equal(p.writeAllowed,false);
 assert.equal(p.saveAvailable,false);
 assert.equal(p.toBudgetAfterCents,null);
 assert.equal(p.reportedToBudgetCents,0);
 assert.equal(JSON.stringify(s),before);
});
test("opening balance is historical reconciliation, not a new account or transaction",()=>{
 const p=preview("opening",{date:"2020-06-01",amount:"250.00",categoryId:""});
 assert.equal(p.ok,true);
 assert.equal(p.suggestedOperation,"RECONCILE_EXISTING_ACCOUNT");
 assert.equal(p.openingBalanceVerified,false);
 assert.equal(p.categoryId,null);
 assert.equal(p.writeAllowed,false);
 assert.equal(p.toBudgetAfterCents,null);
});
test("zero, negative and malformed amounts refuse; exact positive cents accepted",()=>{
 for(const bad of ["","0","0.00","-2.00","1.234","2e3","$3.00","1000000000","Infinity"]){
   assert.equal(policy.parseFundingAmountCents(bad),null,bad);
 }
 assert.equal(policy.parseFundingAmountCents("0.01"),1);
 assert.equal(policy.parseFundingAmountCents("2.5"),250);
 assert.equal(policy.parseFundingAmountCents("999999999.99"),99999999999);
});
test("invalid calendar days and invalid years refuse",()=>{
 for(const bad of ["2026-02-30","2025-02-29","2026-00-12","2026-13-01",
  "1800-01-01","2100-01-01","2026-1-1","2026-10-00"]){
   assert.equal(policy.validFundingDate(bad),false,bad);
 }
 assert.equal(policy.validFundingDate("2024-02-29"),true);
});
test("income date must be in selected month; opening reference cannot be after month",()=>{
 assert.equal(preview("income",{date:"2026-09-30"}).ok,false);
 assert.equal(preview("income",{date:"2026-11-01"}).ok,false);
 assert.equal(preview("opening",{date:"2026-11-01"}).ok,false);
 assert.equal(preview("opening",{date:"2025-01-01"}).ok,true);
});
test("missing account, duplicate account, malformed source fail closed",()=>{
 assert.equal(preview("income",{accountId:"other"}).ok,false);
 const a=snapshot();a.accounts.push({...a.accounts[0]});
 assert.equal(preview("income",{snapshot:a}).ok,false);
 const b=snapshot();b.sourceKey="";
 assert.equal(preview("income",{snapshot:b}).ok,false);
 const c=snapshot();c.readOnly=false;
 assert.equal(preview("income",{snapshot:c}).ok,false);
});
test("income requires a complete actual source category list",()=>{
 assert.equal(preview("income",{categoryId:"fake"}).ok,false);
 const a=snapshot();a.incomeReview.categoriesOverflow=true;
 assert.equal(preview("income",{snapshot:a}).ok,false);
 const b=snapshot();b.incomeReview.month="2026-09";
 assert.equal(preview("income",{snapshot:b}).ok,false);
 const c=snapshot();c.incomeReview.incomeCategories=[];
 assert.equal(preview("income",{snapshot:c}).ok,false);
});
test("mode and amount limits prevent accidental synthetic funding",()=>{
 assert.equal(preview("unknown").ok,false);
 assert.equal(preview("income",{amount:"0"}).ok,false);
 assert.equal(preview("income",{amount:"9999999999"}).ok,false);
});
test("planning module never writes, invokes Actual or creates permission files",()=>{
 for(const bad of ["@actual-app/api","setBudgetAmount","updateTransaction",
  "createAccount","addTransactions","writeFile","LocalStorage",
  "Process {","fetch(","allocation-writes-enabled","transaction-writes-enabled"]){
   assert.equal(source.includes(bad),false,bad);
 }
});
