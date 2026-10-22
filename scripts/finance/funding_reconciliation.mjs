// D14 pure read-only analysis of the same data fetched for FinanceW Budget.
// It never creates balances, classifies payees as income, or mutates Actual.
function addCents(a,b) {
  const sum=a+b;
  if(!Number.isSafeInteger(sum))throw new Error("invalid-funding-total");
  return sum;
}
export function summarizeFunding({month,budget,accounts,balances,transactionSets}) {
  if(typeof month!=="string" || !/^\d{4}-(0[1-9]|1[0-2])$/.test(month)
      || !budget || !Array.isArray(budget.categoryGroups)
      || !Array.isArray(accounts) || !(balances instanceof Map)
      || !(transactionSets instanceof Map))
    throw new Error("invalid-funding-input");
  let incomeCategoryActivityCents=0, incomeCategoryCount=0;
  let incomeCategoryDetailAvailable=true;
  // Actual can omit "spent" on income categories. Budget.totalIncome is a
  // separate month-level figure, never a substitute for category detail.
  const reportedIncomeCents=budget.totalIncome===undefined || budget.totalIncome===null
    ? null : budget.totalIncome;
  if(reportedIncomeCents!==null && !Number.isSafeInteger(reportedIncomeCents))
    throw new Error("invalid-funding-income-total");
  let positiveUncategorizedCents=0, positiveUncategorizedCount=0;
  let activeAccounts=0, accountBalanceCents=0;
  for(const group of budget.categoryGroups) {
    if(!group || !Array.isArray(group.categories))throw new Error("invalid-funding-group");
    if(group.is_income!==true)continue;
    for(const category of group.categories) {
      if(!category)throw new Error("invalid-funding-income");
      incomeCategoryCount++;
      if(category.spent===undefined || category.spent===null){
        // No category-level activity supplied. Unknown is not zero.
        incomeCategoryDetailAvailable=false;
      } else {
        if(!Number.isSafeInteger(category.spent))
          throw new Error("invalid-funding-income");
        incomeCategoryActivityCents=addCents(incomeCategoryActivityCents,category.spent);
      }
    }
  }
  for(const account of accounts) {
    if(!account || typeof account.id!=="string")throw new Error("invalid-funding-account");
    if(account.offbudget || account.closed)continue;
    activeAccounts++;
    const balance=balances.get(account.id);
    if(!Number.isSafeInteger(balance))throw new Error("invalid-funding-balance");
    accountBalanceCents=addCents(accountBalanceCents,balance);
    const transactions=transactionSets.get(account.id) || [];
    if(!Array.isArray(transactions))throw new Error("invalid-funding-transactions");
    for(const row of transactions) {
      if(!row || !Number.isSafeInteger(row.amount) || typeof row.date!=="string"
          || !row.date.startsWith(month+"-"))
        throw new Error("invalid-funding-transaction");
      if(row.amount<=0 || row.transfer_id || row.is_parent || row.is_child
          || row.parent_id || (Array.isArray(row.subtransactions)
             && row.subtransactions.length>0))continue;
      // Positive money can be a reimbursement or correction, NOT necessarily
      // income. Only flag items without a category for the operator to review.
      if(row.category || row.category_id)continue;
      positiveUncategorizedCents=addCents(positiveUncategorizedCents,row.amount);
      positiveUncategorizedCount++;
    }
  }
  if(!Number.isSafeInteger(budget.toBudget))throw new Error("invalid-funding-to-budget");
  return {
    month,accountCount:activeAccounts,accountBalanceCents,
    toBudgetCents:budget.toBudget,
    incomeCategoryCount,
    incomeCategoryActivityCents:incomeCategoryDetailAvailable && incomeCategoryCount>0
      ? incomeCategoryActivityCents : null,
    reportedIncomeCents,
    positiveUncategorizedCount,positiveUncategorizedCents,
    openingBalancesVerified:false,
    // This is an activity review, NOT an accounting reconciliation.
    completeness:"monthly-review-only"
  };
}
