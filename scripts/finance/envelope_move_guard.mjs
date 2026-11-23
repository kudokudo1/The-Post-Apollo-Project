// FinanceW Simple M2b // isolated TWO-category write policy.
// No permissions, filesystem, Actual import, credentials or UI wiring here.
// Two API calls are NOT database-atomic. Durable recordAttempt + manual
// recovery (never replay) is the required caller-owned failure boundary.

export class EnvelopeMoveRefusal extends Error {
  constructor(code) {super(code);this.code=code;}
}
const refuse=code=>{throw new EnvelopeMoveRefusal(code);};
const keys=new Set([
  "action","requestId","sourceKey","month",
  "fromCategoryId","toCategoryId","moveCents",
  "expectedFromBudgetedCents","expectedFromAvailableCents",
  "expectedToBudgetedCents","expectedToAvailableCents",
  "expectedToBudgetCents"
]);
const limit=99999999999;
const bounded=n=>Number.isSafeInteger(n)&&Math.abs(n)<=limit;
const categoryIdOk=s=>typeof s==="string"&&/^[a-zA-Z0-9-]{4,80}$/.test(s);
const monthOk=s=>typeof s==="string"&&/^20\d{2}-(0[1-9]|1[0-2])$/.test(s);

export function validateEnvelopeMoveCommand(input) {
  if(!input || typeof input!=="object" || Array.isArray(input))
    refuse("invalid-command");
  const found=Object.keys(input);
  if(found.length!==keys.size || found.some(k=>!keys.has(k)))
    refuse("unexpected-fields");
  if(input.action!=="move-envelope")refuse("invalid-action");
  if(typeof input.requestId!=="string" || !/^[0-9a-f]{32}$/.test(input.requestId))
    refuse("invalid-request-id");
  if(typeof input.sourceKey!=="string" || !/^[0-9a-f]{64}$/.test(input.sourceKey))
    refuse("invalid-source-key");
  if(!monthOk(input.month))refuse("invalid-month");
  if(!categoryIdOk(input.fromCategoryId) || !categoryIdOk(input.toCategoryId))
    refuse("invalid-category-id");
  if(input.fromCategoryId===input.toCategoryId)
    refuse("same-category");
  if(!bounded(input.moveCents)||input.moveCents<=0)
    refuse("invalid-move-amount");
  for(const field of [
    "expectedFromBudgetedCents","expectedFromAvailableCents",
    "expectedToBudgetedCents","expectedToAvailableCents",
    "expectedToBudgetCents"
  ]) {
    if(!bounded(input[field]))refuse("invalid-financial-value");
  }
  if(input.expectedFromBudgetedCents<0||input.expectedToBudgetedCents<0)
    refuse("invalid-financial-value");
  return {...input};
}

function exactExpenseCategories(budget,id) {
  if(!budget || !Array.isArray(budget.categoryGroups))
    refuse("invalid-budget");
  const matched=[];
  for(const group of budget.categoryGroups) {
    if(!group || !Array.isArray(group.categories))
      refuse("invalid-budget");
    if(group.is_income===true)continue;
    if(group.is_income!==false && group.is_income!==undefined)
      refuse("invalid-budget");
    for(const cat of group.categories) {
      if(!cat || typeof cat.id!=="string")
        refuse("invalid-budget");
      if(cat.id===id)matched.push(cat);
    }
  }
  if(matched.length!==1)refuse("category-unavailable");
  if(!bounded(matched[0].budgeted)||!bounded(matched[0].balance)
      || matched[0].budgeted<0)
    refuse("invalid-category");
  return matched[0];
}

export function preflightEnvelopeMove(input,budget) {
  const cmd=validateEnvelopeMoveCommand(input);
  if(!budget || !bounded(budget.toBudget))
    refuse("invalid-budget");
  const from=exactExpenseCategories(budget,cmd.fromCategoryId);
  const to=exactExpenseCategories(budget,cmd.toCategoryId);
  if(from.budgeted!==cmd.expectedFromBudgetedCents
     ||from.balance!==cmd.expectedFromAvailableCents
     ||to.budgeted!==cmd.expectedToBudgetedCents
     ||to.balance!==cmd.expectedToAvailableCents
     ||budget.toBudget!==cmd.expectedToBudgetCents)
    refuse("stale-budget");
  if(cmd.moveCents>from.balance)
    refuse("insufficient-source-available");
  if(cmd.moveCents>from.budgeted)
    refuse("insufficient-source-assignment");
  const nextFromBudgeted=from.budgeted-cmd.moveCents;
  const nextToBudgeted=to.budgeted+cmd.moveCents;
  const nextFromAvailable=from.balance-cmd.moveCents;
  const nextToAvailable=to.balance+cmd.moveCents;
  if(![nextFromBudgeted,nextToBudgeted,
       nextFromAvailable,nextToAvailable].every(bounded))
    refuse("overflow");
  if(nextFromBudgeted<0||nextFromAvailable<0)
    refuse("source-would-be-negative");
  if(from.budgeted+to.budgeted!==nextFromBudgeted+nextToBudgeted
      ||from.balance+to.balance!==nextFromAvailable+nextToAvailable)
    refuse("conservation-failed");
  return {command:cmd,nextFromBudgeted,nextToBudgeted,
    nextFromAvailable,nextToAvailable,toBudgetUnchanged:budget.toBudget};
}

export async function executeEnvelopeMove({api,input,recordAttempt}) {
  if(!api||typeof api.getBudgetMonth!=="function"
      ||typeof api.setBudgetAmount!=="function"
      ||typeof api.sync!=="function"
      ||typeof recordAttempt!=="function")
    refuse("missing-write-guards");
  const cmd=validateEnvelopeMoveCommand(input);
  const before=await api.getBudgetMonth(cmd.month);
  const checked=preflightEnvelopeMove(cmd,before);

  // The outer CLI must already own the shared FinanceW lock, verify source
  // identity, check unresolved journals and hold a distinct operator permit.
  // Journal ATTEMPTED and fsync it BEFORE the first API mutation.
  await recordAttempt(cmd);

  // These are two sequential Actual API operations, not a DB transaction.
  // No retry and especially no best-effort rollback on partial failure.
  await api.setBudgetAmount(cmd.month,cmd.fromCategoryId,checked.nextFromBudgeted);
  await api.setBudgetAmount(cmd.month,cmd.toCategoryId,checked.nextToBudgeted);
  await api.sync();

  // Do not infer success from return values. A fresh sync/readback must
  // match both category assignments and both balances, with To Budget
  // unchanged. Any discrepancy means manual recovery, never retry.
  const after=await api.getBudgetMonth(cmd.month);
  if(!after||!bounded(after.toBudget)
      ||after.toBudget!==checked.toBudgetUnchanged)
    refuse("uncertain-write");
  let from,to;
  try {
    from=exactExpenseCategories(after,cmd.fromCategoryId);
    to=exactExpenseCategories(after,cmd.toCategoryId);
  } catch(error) {
    refuse("uncertain-write");
  }
  if(from.budgeted!==checked.nextFromBudgeted
      ||to.budgeted!==checked.nextToBudgeted
      ||from.balance!==checked.nextFromAvailable
      ||to.balance!==checked.nextToAvailable)
    refuse("uncertain-write");
  return {status:"committed"};
}
