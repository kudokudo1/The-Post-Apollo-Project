// FinanceW Simple M3d2 // OFFLINE REVIEW CONTRACT, NEVER A SAVE BRIDGE.
// Pure data shaping only. No process, Actual API, filesystem, secrets,
// authorization, request ID generation, journal, or persistence.
import {inspectCategoryHandoff} from "./simple_category_handoff_readiness.mjs";

const fail=reason=>({ok:false,canSave:false,writeAllowed:false,reason});
const outputFields=Object.freeze([
  "sourceKey","accountId","month","date","description","amountCents",
  "categoryId","expectedCategoryBudgetedCents",
  "expectedCategoryAvailableCents","expectedCategorySpentCents",
  "expectedToBudgetCents"
]);

// selectedCategoryId is the current picker state, distinct from the preview
// proposal. This extra check prevents using a preview of an earlier selection.
export function prepareOfflineCategorizedReview({
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
export function recheckOfflineCategorizedReview({
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
