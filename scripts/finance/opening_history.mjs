// D15: inspect the historical ledger, never infer verified opening balances.
// Pure module. No API, filesystem, network, or financial mutation operations.
const start="1900-01-01";
const maxAccounts=30;
const maxTransactionsPerAccount=10000;
function cents(n){if(!Number.isSafeInteger(n))throw Error("invalid-history-amount");return n;}
function add(a,b){const n=a+b;if(!Number.isSafeInteger(n))throw Error("history-overflow");return n;}
function normalMonth(m){return typeof m==="string" && /^(?:19|20)\d{2}-(0[1-9]|1[0-2])$/.test(m);}
function isValidDate(d){return typeof d==="string" && /^\d{4}-\d{2}-\d{2}$/.test(d);}

export function summarizeOpeningHistory({month,accounts,categories,transactionSets}) {
  if(!normalMonth(month) || !Array.isArray(accounts)
      || accounts.length>maxAccounts || !Array.isArray(categories)
      || !(transactionSets instanceof Map))
    throw Error("invalid-history-input");
  const end=month+"-31";
  const candidates=new Set(categories
    .filter(c=>c && typeof c.id==="string" && typeof c.name==="string"
        && /^starting balances?$/i.test(c.name.trim()))
    .map(c=>c.id));
  const output=[], ids=new Set();
  let recordsInspected=0;
  for(const account of accounts){
    if(!account || typeof account.id!=="string" || !account.id
        || typeof account.name!=="string" || ids.has(account.id))
      throw Error("invalid-history-account");
    ids.add(account.id);
    if(account.offbudget || account.closed)continue;
    const rows=transactionSets.get(account.id);
    if(!Array.isArray(rows) || rows.length>maxTransactionsPerAccount)
      throw Error("history-scan-limit");
    let earliest=null, candidateCount=0, candidateCents=0;
    const rowIds=new Set();
    for(const row of rows){
      if(!row || typeof row.id!=="string" || !row.id || rowIds.has(row.id)
          || !isValidDate(row.date) || row.date<start || row.date>end
          || (row.account!==undefined && row.account!==account.id))
        throw Error("invalid-history-transaction");
      rowIds.add(row.id);
      cents(row.amount);
      if(!earliest || row.date<earliest.date || (row.date===earliest.date && row.id<earliest.id))
        earliest={date:row.date,id:row.id,amount:row.amount};
      const categoryId=row.category || row.category_id || "";
      if(!row.transfer_id && !row.parent_id && !row.is_child && !row.is_parent
          && !(Array.isArray(row.subtransactions) && row.subtransactions.length)
          && candidates.has(categoryId)){
        candidateCount++;
        candidateCents=add(candidateCents,row.amount);
      }
    }
    recordsInspected=add(recordsInspected,rows.length);
    output.push({
      accountId:account.id,accountName:account.name,
      firstRecordedDate:earliest?.date || null,
      firstRecordedAmountCents:earliest?.amount ?? null,
      transactionCount:rows.length,
      startingBalanceCandidateCount:candidateCount,
      startingBalanceCandidateCents:candidateCount?candidateCents:null,
      openingBalanceVerified:false
    });
  }
  return {
    schemaVersion:1,kind:"financew-opening-history",readOnly:true,
    month,scanFrom:start,scope:"active-on-budget-accounts",
    accounts:output,recordsInspected,
    openingBalancesVerified:false,
    completeness:"ledger-observation-only"
  };
}

export async function takeOpeningHistory(api,month) {
  if(!normalMonth(month))throw Error("invalid-history-month");
  const accounts=await api.getAccounts();
  const categories=await api.getCategories();
  if(!Array.isArray(accounts)||!Array.isArray(categories)||accounts.length>maxAccounts)
    throw Error("invalid-history-shape");
  const transactionSets=new Map();
  // This API fetch only runs after an explicit user command, never polling.
  for(const account of accounts){
    if(!account || typeof account.id!=="string")throw Error("invalid-history-account");
    if(account.offbudget || account.closed)continue;
    const rows=await api.getTransactions(account.id,start,month+"-31");
    if(!Array.isArray(rows)||rows.length>maxTransactionsPerAccount)
      throw Error("history-scan-limit");
    transactionSets.set(account.id,rows);
  }
  return summarizeOpeningHistory({month,accounts,categories,transactionSets});
}
