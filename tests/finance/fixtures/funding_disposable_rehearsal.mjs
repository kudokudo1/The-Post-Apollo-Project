// D17b disposable-budget funding rehearsal. TEST-ONLY.
// Never imported by FinanceW, Quickshell, or a production CLI.
// All money mutations refuse execution unless explicitly running in GitHub CI
// against a pre-created disposable budget on 127.0.0.1:5006.
import {validTransactionDate} from "../../../scripts/finance/transaction_guard.mjs";
export class FundingRehearsalRefusal extends Error {
  constructor(code){super(code);this.code=code;}
}
const refuse=code=>{throw new FundingRehearsalRefusal(code);};
const id=/^[a-zA-Z0-9-]{4,80}$/;
const hex=/^[0-9a-f]{32}$/;
function stableId(requestId){
  return [requestId.slice(0,8),requestId.slice(8,12),"4"+requestId.slice(13,16),
    "8"+requestId.slice(17,20),requestId.slice(20,32)].join("-");
}
function assertDisposableEnvironment(){
  if(process.env.CI!=="true" || process.env.GITHUB_ACTIONS!=="true"
     || process.env.FINANCEW_DISPOSABLE_TEST!=="yes")
    refuse("disposable-ci-only");
}
export function validateRehearsalPlan(input){
  if(!input || typeof input!=="object" || Array.isArray(input))
    refuse("invalid-plan");
  if(input.mode==="existing-account-opening")
    refuse("existing-opening-requires-bank-reconciliation");
  const mode=input.mode;
  if(mode!=="new-account-opening" && mode!=="income")refuse("invalid-mode");
  const allowed=mode==="income"
    ? ["mode","requestId","sourceKey","accountId","month","date","amountCents","categoryId","description"]
    : ["mode","requestId","sourceKey","accountName","amountCents"];
  if(Object.keys(input).some(k=>!allowed.includes(k)) || Object.keys(input).length!==allowed.length)
    refuse("unexpected-or-missing-fields");
  if(typeof input.requestId!=="string" || !hex.test(input.requestId))
    refuse("invalid-request-id");
  if(typeof input.sourceKey!=="string" || !/^[0-9a-f]{64}$/.test(input.sourceKey))
    refuse("invalid-source-key");
  if(!Number.isSafeInteger(input.amountCents) || input.amountCents<1
      || input.amountCents>99999999999)refuse("invalid-amount");
  if(mode==="income"){
    if(typeof input.accountId!=="string" || !id.test(input.accountId)
       || typeof input.categoryId!=="string" || !id.test(input.categoryId))
      refuse("invalid-id");
    if(!validTransactionDate(input.date,input.month))refuse("invalid-date");
    if(typeof input.description!=="string" || !input.description.trim()
       || input.description.trim().length>120)refuse("invalid-description");
  } else {
    if(typeof input.accountName!=="string" || !input.accountName.trim()
       || input.accountName.trim().length>80)refuse("invalid-account-name");
  }
  return {...input};
}
export async function preflightRehearsal({api,input,expectedSourceKey}){
  const plan=validateRehearsalPlan(input);
  if(plan.sourceKey!==expectedSourceKey)refuse("budget-source-changed");
  if(!api)refuse("api-unavailable");
  const accounts=await api.getAccounts();
  if(!Array.isArray(accounts))refuse("invalid-accounts");
  if(plan.mode==="new-account-opening"){
    if(accounts.some(a=>a && typeof a.name==="string"
        && a.name.trim().toLowerCase()===plan.accountName.trim().toLowerCase()))
      refuse("possible-existing-account");
    return {plan,account:null,rows:null};
  }
  const candidates=accounts.filter(a=>a && a.id===plan.accountId && !a.offbudget && !a.closed);
  if(candidates.length!==1)refuse("stale-account");
  const month=await api.getBudgetMonth(plan.month);
  if(!month || !Array.isArray(month.categoryGroups)
      || !month.categoryGroups.some(g=>g && g.is_income===true
          && Array.isArray(g.categories)
          && g.categories.some(c=>c && c.id===plan.categoryId)))
    refuse("stale-income-category");
  const rows=await api.getTransactions(plan.accountId,plan.month+"-01",plan.month+"-31");
  if(!Array.isArray(rows))refuse("invalid-transactions");
  const importedId="financew-d17b-"+plan.requestId;
  if(rows.some(r=>r && (r.imported_id===importedId
      || (r.date===plan.date && r.amount===plan.amountCents
          && (r.category===plan.categoryId || r.category_id===plan.categoryId)))))
    refuse("possible-duplicate-income");
  return {plan,account:candidates[0],rows};
}
// A read-only check to inspect uncertain writes after a crash/sync failure.
// "not-seen" is NOT permission to retry: sync may have committed elsewhere.
export async function inspectUncertainIncome({api,input}){
  const plan=validateRehearsalPlan(input);
  if(plan.mode!=="income")refuse("not-income");
  const rows=await api.getTransactions(plan.accountId,plan.month+"-01",plan.month+"-31");
  if(!Array.isArray(rows))refuse("invalid-transactions");
  const matches=rows.filter(r=>r && (r.imported_id==="financew-d17b-"+plan.requestId
    || (r.id===stableId(plan.requestId) && r.date===plan.date
      && r.amount===plan.amountCents)));
  if(matches.length>1)return {status:"ambiguous",manualReviewRequired:true};
  if(matches.length===1)return {status:"observed",manualReviewRequired:true};
  return {status:"not-seen",manualReviewRequired:true};
}
export async function executeRehearsal({api,input,expectedSourceKey,recordAttempt}){
  assertDisposableEnvironment();
  if(typeof recordAttempt!=="function")refuse("journal-required");
  const {plan}=await preflightRehearsal({api,input,expectedSourceKey});
  // This callback marks the durable attempt BEFORE Actual's first mutation.
  await recordAttempt(plan);
  if(plan.mode==="new-account-opening"){
    const accountId=await api.createAccount({
      name:plan.accountName,offbudget:false
    },plan.amountCents);
    if(typeof accountId!=="string" || !accountId)refuse("uncertain-create");
    await api.sync();
    const accounts=await api.getAccounts();
    const balance=await api.getAccountBalance(accountId);
    if(!Array.isArray(accounts) || accounts.filter(x=>x && x.id===accountId).length!==1
        || balance!==plan.amountCents)refuse("uncertain-create");
    return {status:"committed",accountId};
  }
  const transactionId=stableId(plan.requestId);
  const response=await api.addTransactions(plan.accountId,[{
    id:transactionId,date:plan.date,amount:plan.amountCents,
    category:plan.categoryId,imported_id:"financew-d17b-"+plan.requestId,
    payee_name:plan.description,cleared:false
  }],{runTransfers:false,learnCategories:false});
  if(response!=="ok" && !(Array.isArray(response)
      && response.length===1 && response[0]===transactionId))
    refuse("uncertain-income");
  await api.sync();
  const rows=await api.getTransactions(plan.accountId,plan.month+"-01",plan.month+"-31");
  if(!Array.isArray(rows) || rows.filter(t=>t && t.id===transactionId
      && t.date===plan.date && t.amount===plan.amountCents).length!==1)
    refuse("uncertain-income");
  return {status:"committed",transactionId};
}
