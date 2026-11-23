// FinanceW Simple M3b // policy for NEW categorized expenses only.
// No file access or authorization. One Actual transaction create, not a
// two-step create+categorize. Any post-attempt failure is UNKNOWN / UNCERTAIN.
export class CategorizedExpenseRefusal extends Error {
  constructor(code) { super(code); this.code=code; }
}
const refuse=code=>{throw new CategorizedExpenseRefusal(code);};
const maxCents=99999999999;
const isCents=x=>Number.isSafeInteger(x)&&Math.abs(x)<=maxCents;
const idPattern=/^[A-Za-z0-9-]{4,80}$/;
const own=(o,k)=>Object.prototype.hasOwnProperty.call(o,k);
const keys=new Set([
  "action","requestId","sourceKey","accountId","month","date",
  "description","amountCents","categoryId",
  "expectedCategoryBudgetedCents","expectedCategoryAvailableCents",
  "expectedCategorySpentCents","expectedToBudgetCents"
]);
function validDate(value,month) {
  if(typeof month!=="string" || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(month)
      ||typeof value!=="string"
      ||!/^20\d{2}-(0[1-9]|1[0-2])-\d{2}$/.test(value)
      ||value.slice(0,7)!==month)return false;
  const [y,m,d]=value.split("-").map(Number);
  const parsed=new Date(Date.UTC(y,m-1,d));
  return parsed.getUTCFullYear()===y && parsed.getUTCMonth()===m-1
    && parsed.getUTCDate()===d;
}
function expenseCategory(budget,id) {
  if(!budget || !Array.isArray(budget.categoryGroups)
      ||!isCents(budget.toBudget))refuse("invalid-budget");
  const matches=[];
  for(const group of budget.categoryGroups){
    if(!group || !Array.isArray(group.categories))
      refuse("invalid-budget");
    // A new spending transaction must never target an income group.
    if(group.is_income!==true && group.is_income!==false)
      refuse("invalid-budget");
    if(group.is_income)continue;
    for(const cat of group.categories){
      if(!cat || typeof cat.id!=="string")refuse("invalid-budget");
      if(cat.id===id)matches.push({group,cat});
    }
  }
  if(matches.length!==1)refuse("category-unavailable");
  const {cat,group}=matches[0];
  if(group.hidden===true || cat.hidden===true)refuse("hidden-category");
  if(typeof cat.name!=="string" || !cat.name.trim()
      || !isCents(cat.budgeted) || !isCents(cat.balance)
      || !isCents(cat.spent))refuse("invalid-category");
  return cat;
}
function transactionId(hex) {
  return [hex.slice(0,8),hex.slice(8,12),"4"+hex.slice(13,16),
    "8"+hex.slice(17,20),hex.slice(20,32)].join("-");
}
export function validateCategorizedExpenseCommand(input) {
  if(!input || typeof input!=="object" || Array.isArray(input))
    refuse("invalid-command");
  const fields=Object.keys(input);
  if(fields.length!==keys.size || fields.some(k=>!keys.has(k)))
    refuse("unexpected-fields");
  if(input.action!=="create-categorized-expense")
    refuse("invalid-action");
  if(typeof input.requestId!=="string"
      || !/^[0-9a-f]{32}$/.test(input.requestId))
    refuse("invalid-request-id");
  if(typeof input.sourceKey!=="string"
      || !/^[0-9a-f]{64}$/.test(input.sourceKey))
    refuse("invalid-source-key");
  if(typeof input.accountId!=="string"||!idPattern.test(input.accountId))
    refuse("invalid-account-id");
  if(typeof input.categoryId!=="string"||!idPattern.test(input.categoryId))
    refuse("invalid-category-id");
  if(!validDate(input.date,input.month))refuse("invalid-date");
  if(typeof input.description!=="string"
      ||!input.description.trim()
      ||input.description.trim().length>120)
    refuse("invalid-description");
  if(!isCents(input.amountCents)||input.amountCents>=0)
    refuse("invalid-expense-amount");
  for(const field of [
    "expectedCategoryBudgetedCents","expectedCategoryAvailableCents",
    "expectedCategorySpentCents","expectedToBudgetCents"
  ])if(!isCents(input[field]))refuse("invalid-financial-value");
  return {...input,description:input.description.trim()};
}
export function preflightCategorizedExpense(input,{accounts,budget,rows}) {
  const cmd=validateCategorizedExpenseCommand(input);
  if(!Array.isArray(accounts)||!Array.isArray(rows))
    refuse("invalid-ledger");
  const matches=accounts.filter(a=>a && a.id===cmd.accountId);
  if(matches.length!==1 || matches[0].offbudget || matches[0].closed)
    refuse("stale-account");
  const cat=expenseCategory(budget,cmd.categoryId);
  if(cat.budgeted!==cmd.expectedCategoryBudgetedCents
      ||cat.balance!==cmd.expectedCategoryAvailableCents
      ||cat.spent!==cmd.expectedCategorySpentCents
      ||budget.toBudget!==cmd.expectedToBudgetCents)
    refuse("stale-budget");

  const importedId="financew-cat-"+cmd.requestId;
  if(rows.some(row=>row && (row.imported_id===importedId
      ||row.date===cmd.date&&row.amount===cmd.amountCents)))
    refuse("possible-duplicate");
  const id=transactionId(cmd.requestId);
  if(rows.some(row=>row && row.id===id))refuse("already-exists");
  return {cmd,id,importedId};
}
export async function executeCategorizedExpense({api,input,recordAttempt}) {
  const cmd=validateCategorizedExpenseCommand(input);
  for(const fn of ["getAccounts","getBudgetMonth","getTransactions",
                    "addTransactions","sync"]){
    if(!api || typeof api[fn]!=="function")
      refuse("missing-write-guards");
  }
  if(typeof recordAttempt!=="function")refuse("missing-write-guards");

  const accounts=await api.getAccounts();
  const budget=await api.getBudgetMonth(cmd.month);
  const from=cmd.month+"-01",through=cmd.month+"-31";
  const rows=await api.getTransactions(cmd.accountId,from,through);
  const checked=preflightCategorizedExpense(cmd,{accounts,budget,rows});

  // External CLI has exclusive shared FinanceW write lock, source/permit
  // check and durable ATTEMPTED journal before entering this callback.
  await recordAttempt(cmd);

  // One Actual create operation WITH the category ID, never a
  // create-uncategorized followed by a separate categorization write.
  const acknowledgment=await api.addTransactions(cmd.accountId,[{
    id:checked.id,date:cmd.date,amount:cmd.amountCents,
    category:cmd.categoryId,payee_name:cmd.description,
    imported_id:checked.importedId,cleared:false
  }],{runTransfers:false,learnCategories:false});
  if(acknowledgment!=="ok"
      && !(Array.isArray(acknowledgment)
        && acknowledgment.length===1 && acknowledgment[0]===checked.id))
    refuse("uncertain-write");
  await api.sync();
  const after=await api.getTransactions(cmd.accountId,from,through);
  if(!Array.isArray(after))refuse("uncertain-write");
  const found=after.filter(row=>row && row.id===checked.id);
  if(found.length!==1 || found[0].date!==cmd.date
      ||found[0].amount!==cmd.amountCents
      ||found[0].category!==cmd.categoryId
      ||found[0].imported_id!==checked.importedId
      ||(own(found[0],"account") && found[0].account!==cmd.accountId)
      ||found[0].transfer_id || found[0].is_parent || found[0].is_child
      ||found[0].parent_id
      ||(Array.isArray(found[0].subtransactions)
          && found[0].subtransactions.length>0))
    refuse("uncertain-write");
  // A separate budget read ensures category identity still resolves, but
  // does not invent an exact post-spending TO BUDGET figure. Actual owns
  // those authoritative recalculations.
  try {
    const afterBudget=await api.getBudgetMonth(cmd.month);
    expenseCategory(afterBudget,cmd.categoryId);
  } catch {
    refuse("uncertain-write");
  }
  return {status:"committed"};
}
