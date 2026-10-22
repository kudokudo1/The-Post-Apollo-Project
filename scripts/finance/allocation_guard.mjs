// D12: isolated finance allocation policy. No startup hooks, filesystem,
// real Actual API import, credential reads or live Quickshell wiring.
// All mutation requires caller-provided api + durable recordAttempt.
// An error after recordAttempt is UNCERTAIN, never safe to retry.
export class AllocationRefusal extends Error {
  constructor(code) {super(code);this.code=code;}
}
const reject=code=>{throw new AllocationRefusal(code);};
const keyPattern=/^[0-9a-f]{64}$/;
const requestPattern=/^[0-9a-f]{32}$/;
const categoryPattern=/^[a-zA-Z0-9-]{4,80}$/;
const monthPattern=/^20\d{2}-(0[1-9]|1[0-2])$/;
const limit=99999999999;
const allowed=new Set(["action","requestId","sourceKey","month","categoryId",
  "expectedBudgetedCents","expectedAvailableCents",
  "expectedToBudgetCents","targetBudgetedCents"]);

function integer(value) {return Number.isSafeInteger(value);}
function bounded(value) {return integer(value) && Math.abs(value)<=limit;}

export function validateAllocationCommand(input) {
  if (!input || typeof input!=="object" || Array.isArray(input))
    reject("invalid-command");
  const keys=Object.keys(input);
  if (keys.length!==allowed.size || keys.some(key=>!allowed.has(key)))
    reject("unexpected-fields");
  if (input.action!=="set-amount") reject("invalid-action");
  if (typeof input.requestId!=="string" || !requestPattern.test(input.requestId))
    reject("invalid-request-id");
  if (typeof input.sourceKey!=="string" || !keyPattern.test(input.sourceKey))
    reject("invalid-source-key");
  if (typeof input.month!=="string" || !monthPattern.test(input.month))
    reject("invalid-month");
  if (typeof input.categoryId!=="string" || !categoryPattern.test(input.categoryId))
    reject("invalid-category-id");
  if (!bounded(input.expectedBudgetedCents)
      || !bounded(input.expectedAvailableCents)
      || !bounded(input.expectedToBudgetCents)
      || !bounded(input.targetBudgetedCents)
      || input.targetBudgetedCents<0)
    reject("invalid-financial-value");
  return {...input};
}

export function preflightAllocation(input,budget) {
  const cmd=validateAllocationCommand(input);
  if (!budget || !Array.isArray(budget.categoryGroups)
      || !bounded(budget.toBudget))
    reject("invalid-budget");
  const matches=[];
  for (const group of budget.categoryGroups) {
    if (!group || !Array.isArray(group.categories))
      reject("invalid-budget");
    if (group.is_income) continue;
    for (const cat of group.categories)
      if (cat && cat.id===cmd.categoryId) matches.push(cat);
  }
  if (matches.length!==1) reject("category-unavailable");
  const cat=matches[0];
  if (!bounded(cat.budgeted) || !bounded(cat.balance))
    reject("invalid-category");
  if (cat.budgeted!==cmd.expectedBudgetedCents
      || cat.balance!==cmd.expectedAvailableCents
      || budget.toBudget!==cmd.expectedToBudgetCents)
    reject("stale-budget");
  const delta=cmd.targetBudgetedCents-cat.budgeted;
  const nextUnallocated=budget.toBudget-delta;
  const nextAvailable=cat.balance+delta;
  if (![delta,nextUnallocated,nextAvailable].every(bounded))
    reject("overflow");
  if (delta===0) reject("unchanged-allocation");
  // First-stage policy: reject both over-allocation and newly/persistently
  // negative envelopes rather than silently accepting preview warnings.
  if (nextUnallocated<0) reject("insufficient-unallocated-funds");
  if (nextAvailable<0) reject("category-would-be-overspent");
  return {command:cmd,delta,nextUnallocated,nextAvailable};
}

export async function executeAllocation({api,input,recordAttempt}) {
  if (!api || typeof api.getBudgetMonth!=="function"
      || typeof api.setBudgetAmount!=="function"
      || typeof api.sync!=="function" || typeof recordAttempt!=="function")
    reject("missing-write-guards");
  const cmd=validateAllocationCommand(input);
  const before=await api.getBudgetMonth(cmd.month);
  const checked=preflightAllocation(cmd,before);
  // Caller must have already verified source credentials, operator gate,
  // exclusive global finance journal lock, unique request and clean recovery.
  await recordAttempt(cmd);
  await api.setBudgetAmount(cmd.month,cmd.categoryId,cmd.targetBudgetedCents);
  await api.sync();
  // Source of truth is a fresh read after sync. Do not infer success from
  // transport success or the setBudgetAmount response.
  const after=await api.getBudgetMonth(cmd.month);
  if (!after || !Array.isArray(after.categoryGroups)
      || !bounded(after.toBudget))
    reject("uncertain-write");
  const matches=after.categoryGroups
    .filter(group=>group && group.is_income!==true && Array.isArray(group.categories))
    .flatMap(group=>group.categories)
    .filter(cat=>cat && cat.id===cmd.categoryId);
  if (matches.length!==1 || matches[0].budgeted!==cmd.targetBudgetedCents
      || matches[0].balance!==checked.nextAvailable
      || after.toBudget!==checked.nextUnallocated)
    reject("uncertain-write");
  return {status:"committed"};
}
