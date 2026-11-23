// FinanceW Simple M3d0 // read-only M3c->M3b contract inspection.
// NO writer, process, authorization, request ID, persistence or Actual API.
// Even a passing inspection NEVER authorizes Save. The M3b writer must perform
// independent current Actual preflight after separate security acceptance.
const MAX = 99999999999;
const cents = x => Number.isSafeInteger(x) && Math.abs(x) <= MAX;
const key = x => typeof x === "string" && /^[0-9a-f]{64}$/.test(x);
const id = x => typeof x === "string" && /^[A-Za-z0-9-]{4,80}$/.test(x);
const month = x => typeof x === "string" && /^20\d{2}-(0[1-9]|1[0-2])$/.test(x);
const fail = reason => ({ok:false, canSave:false, reason});
const one = (rows, selected) => rows.filter(x => x && x.id === selected);
function dateInMonth(date, selectedMonth) {
  if (typeof date !== "string" || !/^20\d{2}-\d{2}-\d{2}$/.test(date)
      || date.slice(0,7) !== selectedMonth) return false;
  const [y,m,d] = date.split("-").map(Number);
  const check = new Date(Date.UTC(y,m-1,d));
  return check.getUTCFullYear() === y && check.getUTCMonth() === m-1
    && check.getUTCDate() === d;
}

export function inspectCategoryHandoff({snapshot,candidate,proposal} = {}) {
  if (!snapshot || snapshot.schemaVersion !== 1
      || snapshot.source !== "actual-budget" || snapshot.readOnly !== true
      || !key(snapshot.sourceKey) || !month(snapshot.month)
      || !cents(snapshot.toBudgetCents) || !Array.isArray(snapshot.accounts)
      || !Array.isArray(snapshot.categories)
      || !Array.isArray(snapshot.categoryGroups))
    return fail("authenticated-snapshot-required");

  if (!candidate || candidate.action !== "create"
      || candidate.direction !== "expense" || candidate.editing !== false
      || candidate.sourceKey !== snapshot.sourceKey
      || candidate.month !== snapshot.month
      || !id(candidate.accountId)
      || !dateInMonth(candidate.date, snapshot.month)
      || typeof candidate.description !== "string"
      || !candidate.description.trim()
      || candidate.description.trim().length > 120
      || !cents(candidate.amountCents) || candidate.amountCents >= 0)
    return fail("new-expense-candidate-required");

  if (!proposal || proposal.ok !== true || proposal.readOnly !== true
      || proposal.writeAllowed !== false || proposal.savesToActual !== false
      || proposal.sourceKey !== candidate.sourceKey
      || proposal.month !== candidate.month
      || proposal.accountId !== candidate.accountId
      || proposal.date !== candidate.date
      || proposal.description !== candidate.description.trim()
      || proposal.expenseAmountCents !== candidate.amountCents
      || !id(proposal.categoryId)
      || proposal.toBudgetAfterCents !== null)
    return fail("matching-readonly-preview-required");

  const accounts = one(snapshot.accounts,candidate.accountId);
  const categories = one(snapshot.categories,proposal.categoryId);
  if (accounts.length !== 1 || !cents(accounts[0].balanceCents))
    return fail("account-ambiguous-or-unavailable");
  if (categories.length !== 1)
    return fail("category-ambiguous-or-unavailable");
  const category = categories[0];
  const groups = one(snapshot.categoryGroups,category.groupId);
  if (groups.length !== 1)
    return fail("group-ambiguous-or-unavailable");
  const group = groups[0];
  if (!id(category.groupId) || !cents(category.budgetedCents)
      || !cents(category.availableCents) || !cents(category.spentCents)
      || typeof category.name !== "string" || !category.name.trim()
      || typeof group.name !== "string" || !group.name.trim()
      || proposal.groupId !== group.id || proposal.groupName !== group.name
      || proposal.categoryName !== category.name
      || proposal.availableBeforeCents !== category.availableCents
      || proposal.spentBeforeCents !== category.spentCents)
    return fail("preview-balances-or-identity-stale");
  const afterAvailable = category.availableCents + candidate.amountCents;
  const afterSpent = category.spentCents + candidate.amountCents;
  if (!cents(afterAvailable) || !cents(afterSpent)
      || proposal.estimatedAvailableAfterCents !== afterAvailable
      || proposal.estimatedSpentAfterCents !== afterSpent
      || proposal.estimatedOverspent !== (afterAvailable < 0))
    return fail("preview-estimate-stale");

  // Current normalizeSnapshot deliberately strips these Actual flags.
  // Never assume absent visibility flags mean visible/expense.
  if (typeof category.hidden !== "boolean"
      || typeof group.hidden !== "boolean"
      || typeof group.isIncome !== "boolean")
    return fail("category-visibility-unverified");
  if (category.hidden || group.hidden || group.isIncome)
    return fail("category-not-writable");

  // No 13-field write command: deliberately NO action/requestId/permit.
  // This is ONLY a compatibility witness for future guarded bridge review.
  return {
    ok:true, canSave:false, previewOnly:true,
    requiresFreshActualPreflight:true, requiresIndependentSecurityReview:true,
    reason:"read-only-handoff-consistent",
    witness:{
      sourceKey:snapshot.sourceKey,month:snapshot.month,
      accountId:candidate.accountId,categoryId:category.id,
      date:candidate.date,expenseAmountCents:candidate.amountCents,
      expectedCategoryBudgetedCents:category.budgetedCents,
      expectedCategoryAvailableCents:category.availableCents,
      expectedCategorySpentCents:category.spentCents,
      expectedToBudgetCents:snapshot.toBudgetCents
    }
  };
}
