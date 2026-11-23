.pragma library

// Simple M3a: pure read-only proposed category for a NEW expense.
// The existing transaction writer does not accept categoryId. This proposal
// is NOT included in transaction save commands. No Actual API or filesystem.
var MAX_CENTS=99999999999;
function cents(n) {
    return Number.isSafeInteger(n) && Math.abs(n)<=MAX_CENTS;
}
function validMonth(value) {
    return typeof value==="string"
        && /^(19|20)\d{2}-(0[1-9]|1[0-2])$/.test(value);
}
function validDate(value,month) {
    if(typeof value!=="string"
            || !/^(19|20)\d{2}-(0[1-9]|1[0-2])-\d{2}$/.test(value)
            || value.slice(0,7)!==month)return false;
    const a=value.split("-").map(Number);
    const d=new Date(Date.UTC(a[0],a[1]-1,a[2]));
    return d.getUTCFullYear()===a[0] && d.getUTCMonth()+1===a[1]
        && d.getUTCDate()===a[2];
}
function refusal(reason) { return {ok:false,reason:reason}; }
function previewExpenseCategory(snapshot,candidate,categoryId) {
    if(!snapshot || snapshot.schemaVersion!==1
            || snapshot.source!=="actual-budget"
            || snapshot.readOnly!==true
            || typeof snapshot.sourceKey!=="string"
            || !/^[a-f0-9]{64}$/.test(snapshot.sourceKey)
            || !validMonth(snapshot.month)
            || !cents(snapshot.toBudgetCents)
            || !Array.isArray(snapshot.accounts)
            || !Array.isArray(snapshot.categories)
            || !Array.isArray(snapshot.categoryGroups))
        return refusal("AUTHENTICATED BUDGET REQUIRED");

    if(!candidate || typeof candidate!=="object" || Array.isArray(candidate)
            || candidate.action!=="create" || candidate.direction!=="expense"
            || candidate.editing===true
            || candidate.sourceKey!==snapshot.sourceKey
            || candidate.month!==snapshot.month
            || !validDate(candidate.date,snapshot.month)
            || typeof candidate.description!=="string"
            || !candidate.description.trim()
            || candidate.description.trim().length>120
            || !cents(candidate.amountCents)
            || candidate.amountCents>=0)
        return refusal("NEW EXPENSE DRAFT REQUIRED");

    if(typeof candidate.accountId!=="string" || !candidate.accountId)
        return refusal("ACCOUNT UNAVAILABLE");
    const matches=snapshot.accounts.filter(function(a) {
        return a && a.id===candidate.accountId;
    });
    if(matches.length!==1 || typeof matches[0].name!=="string"
            || !matches[0].name.trim() || !cents(matches[0].balanceCents))
        return refusal("ACCOUNT UNAVAILABLE");

    if(typeof categoryId!=="string" || !categoryId)
        return refusal("SELECT AN EXPENSE ENVELOPE");
    const categoryRows=snapshot.categories.filter(function(c){
        return c && c.id===categoryId;
    });
    if(categoryRows.length!==1)
        return refusal("CATEGORY AMBIGUOUS OR UNAVAILABLE");
    const category=categoryRows[0];
    if(typeof category.name!=="string" || !category.name.trim()
            || typeof category.groupId!=="string" || !category.groupId
            || !cents(category.availableCents)
            || !cents(category.budgetedCents)
            || !cents(category.spentCents))
        return refusal("INVALID CATEGORY BALANCE");

    const groups=snapshot.categoryGroups.filter(function(g) {
        return g && g.id===category.groupId;
    });
    if(groups.length!==1 || typeof groups[0].name!=="string"
            || !groups[0].name.trim())
        return refusal("EXPENSE GROUP AMBIGUOUS OR UNAVAILABLE");

    const estimatedAvailable=category.availableCents+candidate.amountCents;
    const estimatedSpent=category.spentCents+candidate.amountCents;
    if(!cents(estimatedAvailable) || !cents(estimatedSpent))
        return refusal("PROJECTED AMOUNT EXCEEDS SAFE RANGE");

    return {
        ok:true,readOnly:true,writeAllowed:false,savesToActual:false,
        sourceKey:snapshot.sourceKey,month:snapshot.month,
        accountId:candidate.accountId,accountName:matches[0].name,
        date:candidate.date,description:candidate.description.trim(),
        expenseAmountCents:candidate.amountCents,
        categoryId:category.id,categoryName:category.name,
        groupId:category.groupId,groupName:groups[0].name,
        availableBeforeCents:category.availableCents,
        estimatedAvailableAfterCents:estimatedAvailable,
        spentBeforeCents:category.spentCents,
        estimatedSpentAfterCents:estimatedSpent,
        estimatedOverspent:estimatedAvailable<0,
        toBudgetAfterCents:null,
        note:"ESTIMATE ONLY // ACTUAL RECALCULATES ON SAVE // NOT SAVED"
    };
}
