.pragma library

// FinanceW Simple M3d5a // QML-only mirror of the merged M3d0 and M3d2
// PURE read-only inspection. No Process, command, requestId, permit, secrets,
// trusted write authority, or network access. Do NOT wire to a financial writer.
// This is a review display for a future separately authorized Save bridge.
var inspector=(function(){
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

function inspectCategoryHandoff({snapshot,candidate,proposal} = {}) {
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

return {inspectCategoryHandoff:inspectCategoryHandoff};
})();
var offline=(function(){
// FinanceW Simple M3d2 // OFFLINE REVIEW CONTRACT, NEVER A SAVE BRIDGE.
// Pure data shaping only. No process, Actual API, filesystem, secrets,
// authorization, request ID generation, journal, or persistence.
const inspectCategoryHandoff=inspector.inspectCategoryHandoff;

const fail=reason=>({ok:false,canSave:false,writeAllowed:false,reason});
const outputFields=Object.freeze([
  "sourceKey","accountId","month","date","description","amountCents",
  "categoryId","expectedCategoryBudgetedCents",
  "expectedCategoryAvailableCents","expectedCategorySpentCents",
  "expectedToBudgetCents"
]);

// selectedCategoryId is the current picker state, distinct from the preview
// proposal. This extra check prevents using a preview of an earlier selection.
function prepareOfflineCategorizedReview({
  snapshot,candidate,proposal,selectedCategoryId
}={}) {
  if(typeof selectedCategoryId!=="string" || !selectedCategoryId
      || !proposal || selectedCategoryId!==proposal.categoryId)
    return fail("selected-category-changed");
  const checked=inspectCategoryHandoff({snapshot,candidate,proposal});
  if(!checked.ok)return fail(checked.reason);
  if(checked.canSave!==false
      || checked.requiresFreshActualPreflight!==true
      || checked.requiresIndependentSecurityReview!==true)
    return fail("preview-not-readonly");
  const w=checked.witness;
  // This is deliberately missing M3b's action and requestId; the writer
  // refuses it as a command. It is never routed to a Process or CLI.
  const previewFields={
    sourceKey:w.sourceKey,accountId:w.accountId,month:w.month,
    date:w.date,description:candidate.description.trim(),
    amountCents:w.expenseAmountCents,categoryId:w.categoryId,
    expectedCategoryBudgetedCents:w.expectedCategoryBudgetedCents,
    expectedCategoryAvailableCents:w.expectedCategoryAvailableCents,
    expectedCategorySpentCents:w.expectedCategorySpentCents,
    expectedToBudgetCents:w.expectedToBudgetCents
  };
  if(Object.keys(previewFields).length!==outputFields.length
      ||Object.keys(previewFields).some(k=>!outputFields.includes(k)))
    return fail("invalid-preview-fields");
  return {
    ok:true,kind:"m3d2-offline-review",canSave:false,writeAllowed:false,
    requiresFreshActualPreflight:true,
    requiresIndependentSecurityReview:true,
    previewFields,
    reason:"review-only-no-write-authority"
  };
}

// Recompute from fresh caller-supplied input. An older displayed review does
// not survive a changed category, source/month, account, date or amount.
function recheckOfflineCategorizedReview({
  previous,snapshot,candidate,proposal,selectedCategoryId
}={}) {
  if(!previous || previous.ok!==true
      ||previous.kind!=="m3d2-offline-review"
      ||previous.canSave!==false ||previous.writeAllowed!==false
      ||previous.requiresFreshActualPreflight!==true
      ||previous.requiresIndependentSecurityReview!==true
      ||!previous.previewFields || typeof previous.previewFields!=="object"
      ||Array.isArray(previous.previewFields))
    return fail("review-not-acceptable");
  const current=prepareOfflineCategorizedReview({
    snapshot,candidate,proposal,selectedCategoryId
  });
  if(!current.ok)return current;
  const old=previous.previewFields;
  const fresh=current.previewFields;
  if(Object.keys(old).length!==outputFields.length
      ||outputFields.some(k=>!Object.prototype.hasOwnProperty.call(old,k)
        ||old[k]!==fresh[k]))
    return fail("review-changed");
  return {
    ok:true,kind:"m3d2-offline-recheck",canSave:false,writeAllowed:false,
    requiresFreshActualPreflight:true,
    requiresIndependentSecurityReview:true,
    reason:"review-still-matches-but-save-locked"
  };
}

return {prepareOfflineCategorizedReview:prepareOfflineCategorizedReview,
        recheckOfflineCategorizedReview:recheckOfflineCategorizedReview};
})();
function prepareOfflineCategorizedReview(args) {
    return offline.prepareOfflineCategorizedReview(args);
}
function recheckOfflineCategorizedReview(args) {
    return offline.recheckOfflineCategorizedReview(args);
}
