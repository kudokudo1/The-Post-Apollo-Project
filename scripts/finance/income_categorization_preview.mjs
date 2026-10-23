// D16: pure read-only candidate selection and category preview.
// Positive incoming transactions are not presumed to be income.
const maxCandidates=12;
const maxCategories=24;
const monthRegex=/^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])$/;
const dateRegex=/^\d{4}-\d{2}-\d{2}$/;
function validCents(x) {return Number.isSafeInteger(x);}
function eligibleIncoming(row,month) {
  return row && Number.isSafeInteger(row.amount) && row.amount>0
    && typeof row.id==="string" && !!row.id
    && typeof row.date==="string" && dateRegex.test(row.date)
    && row.date.startsWith(month+"-")
    && !row.category && !row.category_id && !row.transfer_id
    && !row.is_parent && !row.is_child && !row.parent_id
    && !(Array.isArray(row.subtransactions) && row.subtransactions.length>0);
}
export function summarizeIncomeCandidates({month,budget,accounts,transactionSets}) {
  if(!monthRegex.test(month) || !budget || !Array.isArray(budget.categoryGroups)
      || !Array.isArray(accounts) || !(transactionSets instanceof Map))
    throw Error("income-review-invalid-source");
  const incomeCategories=[];
  const ids=new Set();
  for(const group of budget.categoryGroups) {
    if(!group || !Array.isArray(group.categories))throw Error("income-review-invalid-group");
    if(group.is_income!==true)continue;
    for(const category of group.categories) {
      // Missing optional labels do not invalidate a complete budget read.
      if(!category || typeof category.id!=="string" || !category.id
          || typeof category.name!=="string" || ids.has(category.id))
        continue;
      ids.add(category.id);
      if(category.hidden===true)continue;
      incomeCategories.push({id:category.id,name:category.name});
    }
  }
  // A truncated category list must not accidentally omit a valid target.
  const categoryOverflow=incomeCategories.length>maxCategories;
  const visibleCategories=categoryOverflow?[]:incomeCategories;
  const allCandidates=[];
  const seen=new Set();
  for(const account of accounts) {
    if(!account || typeof account.id!=="string"
        || typeof account.name!=="string")throw Error("income-review-invalid-account");
    if(account.offbudget || account.closed)continue;
    const rows=transactionSets.get(account.id)||[];
    if(!Array.isArray(rows))throw Error("income-review-invalid-transactions");
    for(const row of rows) {
      if(!eligibleIncoming(row,month))continue;
      if(row.account !== undefined && row.account!==account.id)
        throw Error("income-review-account-mismatch");
      const key=account.id+"\0"+row.id;
      if(seen.has(key))throw Error("income-review-duplicate");
      seen.add(key);
      allCandidates.push({
        id:row.id,accountId:account.id,accountName:account.name,
        date:row.date,amountCents:row.amount,currentCategory:"UNCATEGORIZED"
      });
    }
  }
  allCandidates.sort((a,b)=>b.date.localeCompare(a.date)
    || a.accountId.localeCompare(b.accountId)||a.id.localeCompare(b.id));
  return {
    month,readOnly:true,completeness:"selected-month-review",
    candidateCount:allCandidates.length,
    showingCount:Math.min(maxCandidates,allCandidates.length),
    truncated:allCandidates.length>maxCandidates,
    incomeCategories:visibleCategories,
    categoriesOverflow:categoryOverflow,
    candidates:allCandidates.slice(0,maxCandidates),
    categorizationVerified:false
  };
}
export function previewIncomeCategory(snapshot,transactionId,accountId,categoryId) {
  if(!snapshot || snapshot.readOnly!==true || snapshot.source!=="actual-budget"
      || !/^[a-f0-9]{64}$/.test(snapshot.sourceKey||"")
      || !monthRegex.test(snapshot.month)
      || !snapshot.incomeReview || snapshot.incomeReview.month!==snapshot.month
      || snapshot.incomeReview.readOnly!==true
      || snapshot.incomeReview.categoriesOverflow===true
      || !Array.isArray(snapshot.incomeReview.candidates)
      || !Array.isArray(snapshot.incomeReview.incomeCategories))
    return {ok:false,reason:"SOURCE UNAVAILABLE"};
  const c=snapshot.incomeReview.candidates.filter(x=>
    x.id===transactionId && x.accountId===accountId);
  const target=snapshot.incomeReview.incomeCategories.filter(x=>x.id===categoryId);
  if(c.length!==1 || target.length!==1 || !validCents(c[0].amountCents)
      || c[0].amountCents<=0 || c[0].currentCategory!=="UNCATEGORIZED")
    return {ok:false,reason:"SELECTION UNAVAILABLE"};
  return {
    ok:true,sourceKey:snapshot.sourceKey,month:snapshot.month,
    transactionId,accountId,categoryId,
    date:c[0].date,accountName:c[0].accountName,
    amountCents:c[0].amountCents,
    currentCategory:"UNCATEGORIZED",proposedCategory:target[0].name,
    writeAllowed:false,toBudgetAfterCents:null,
    note:"REVIEW ONLY // ACTUAL MUST RECALCULATE TO BUDGET"
  };
}
