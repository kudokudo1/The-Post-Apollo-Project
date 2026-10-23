// D17c funding guard. No credentials, filesystem or direct Actual imports.
// All callers must first verify operator authorization, source binding,
// shared finance lock, clean recovery ledger, and durable recordAttempt.
import {validTransactionDate} from "./transaction_guard.mjs";

export class FundingRefusal extends Error {
  constructor(code){super(code);this.code=code;}
}
const refuse=code=>{throw new FundingRefusal(code);};
const id=/^[a-zA-Z0-9-]{4,80}$/;
const hex=/^[0-9a-f]{32}$/;
const source=/^[0-9a-f]{64}$/;
const moneyLimit=99999999999;
function stableId(requestId){
  return [requestId.slice(0,8),requestId.slice(8,12),"4"+requestId.slice(13,16),
    "8"+requestId.slice(17,20),requestId.slice(20,32)].join("-");
}
export function validateFundingCommand(input){
  if(!input || typeof input!=="object" || Array.isArray(input))
    refuse("invalid-command");
  if(input.mode==="existing-account-opening")
    refuse("existing-opening-requires-reconciliation");
  if(!["income","new-account-opening"].includes(input.mode))
    refuse("invalid-mode");
  const allowed=input.mode==="income"
    ? ["mode","requestId","sourceKey","accountId","month","date",
       "amountCents","categoryId","description"]
    : ["mode","requestId","sourceKey","accountName","amountCents"];
  const keys=Object.keys(input);
  if(keys.length!==allowed.length || keys.some(k=>!allowed.includes(k)))
    refuse("unexpected-fields");
  if(typeof input.requestId!=="string" || !hex.test(input.requestId))
    refuse("invalid-request-id");
  if(typeof input.sourceKey!=="string" || !source.test(input.sourceKey))
    refuse("invalid-source-key");
  if(!Number.isSafeInteger(input.amountCents) || input.amountCents<=0
      || input.amountCents>moneyLimit)
    refuse("invalid-amount");
  if(input.mode==="income"){
    if(typeof input.accountId!=="string" || !id.test(input.accountId)
        || typeof input.categoryId!=="string" || !id.test(input.categoryId))
      refuse("invalid-id");
    if(!validTransactionDate(input.date,input.month))refuse("invalid-date");
    if(typeof input.description!=="string" || !input.description.trim()
        || input.description.trim().length>120)
      refuse("invalid-description");
  } else if(typeof input.accountName!=="string"
      || !input.accountName.trim() || input.accountName.trim().length>80)
    refuse("invalid-account-name");
  return {...input,
    ...(input.mode==="income"
      ? {description:input.description.trim()}
      : {accountName:input.accountName.trim()})};
}
export async function preflightFunding(api,input){
  const cmd=validateFundingCommand(input);
  if(!api || typeof api.getAccounts!=="function")
    refuse("api-unavailable");
  const accounts=await api.getAccounts();
  if(!Array.isArray(accounts))refuse("invalid-accounts");
  if(cmd.mode==="new-account-opening"){
    if(accounts.some(a=>a && typeof a.name==="string"
      && a.name.trim().toLowerCase()===cmd.accountName.toLowerCase()))
      refuse("possible-existing-account");
    return cmd;
  }
  if(accounts.filter(a=>a && a.id===cmd.accountId
      && !a.offbudget && !a.closed).length!==1)
    refuse("stale-account");
  const budget=await api.getBudgetMonth(cmd.month);
  if(!budget || !Array.isArray(budget.categoryGroups)
      || budget.categoryGroups.filter(g=>g && g.is_income===true
        && Array.isArray(g.categories)).flatMap(g=>g.categories)
          .filter(c=>c && c.id===cmd.categoryId).length!==1)
    refuse("stale-income-category");
  const rows=await api.getTransactions(cmd.accountId,
    cmd.month+"-01",cmd.month+"-31");
  if(!Array.isArray(rows))refuse("invalid-transactions");
  const importedId="financew-funding-"+cmd.requestId;
  if(rows.some(r=>r && (
      r.imported_id===importedId
      || r.id===stableId(cmd.requestId)
      || (r.date===cmd.date && r.amount===cmd.amountCents)
    )))refuse("possible-duplicate-income");
  return cmd;
}
export async function executeFunding({api,input,recordAttempt}){
  if(!api || typeof recordAttempt!=="function"
      || typeof api.getAccounts!=="function"
      || typeof api.sync!=="function"
      || typeof api.getAccountBalance!=="function"
      || typeof api.getBudgetMonth!=="function"
      || typeof api.getTransactions!=="function"
      || typeof api.addTransactions!=="function"
      || typeof api.createAccount!=="function")
    refuse("missing-write-guards");
  const cmd=await preflightFunding(api,input);
  // Journal attempt must be persisted BEFORE the very first mutation.
  await recordAttempt(cmd);
  if(cmd.mode==="new-account-opening"){
    const accountId=await api.createAccount({
      name:cmd.accountName,offbudget:false
    },cmd.amountCents);
    if(typeof accountId!=="string" || !accountId)
      refuse("uncertain-write");
    await api.sync();
    const after=await api.getAccounts();
    const balance=await api.getAccountBalance(accountId);
    if(!Array.isArray(after)
        || after.filter(a=>a && a.id===accountId && !a.offbudget
          && !a.closed && a.name===cmd.accountName).length!==1
        || balance!==cmd.amountCents)
      refuse("uncertain-write");
    return {status:"committed"};
  }
  const transactionId=stableId(cmd.requestId);
  const ack=await api.addTransactions(cmd.accountId,[{
    id:transactionId,date:cmd.date,amount:cmd.amountCents,
    category:cmd.categoryId,imported_id:"financew-funding-"+cmd.requestId,
    payee_name:cmd.description,cleared:false
  }],{runTransfers:false,learnCategories:false});
  if(ack!=="ok" && !(Array.isArray(ack)
      && ack.length===1 && ack[0]===transactionId))
    refuse("uncertain-write");
  await api.sync();
  const rows=await api.getTransactions(cmd.accountId,
    cmd.month+"-01",cmd.month+"-31");
  if(!Array.isArray(rows) || rows.filter(r=>r && r.id===transactionId
      && r.date===cmd.date && r.amount===cmd.amountCents
      && (r.category===cmd.categoryId || r.category_id===cmd.categoryId)
    ).length!==1)
    refuse("uncertain-write");
  return {status:"committed"};
}
