// D17 funding setup planning only. No Actual imports, IO, persistence or writes.
// An opening amount is NOT automatically a new ledger transaction and a
// deposit amount is NOT automatically available To Budget.
function parseFundingAmountCents(text) {
    const raw=String(text===null || text===undefined ? "" : text).trim();
    if(!/^\d{1,9}(?:\.\d{1,2})?$/.test(raw))return null;
    const parts=raw.split(".");
    const n=Number(parts[0])*100
        +Number((parts[1]||"").padEnd(2,"0"));
    return Number.isSafeInteger(n) && n>0 ? n : null;
}
function validFundingDate(text) {
    if(typeof text!=="string"
            || !/^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$/.test(text))
        return false;
    const year=Number(text.slice(0,4));
    const month=Number(text.slice(5,7));
    const day=Number(text.slice(8,10));
    const d=new Date(Date.UTC(year,month-1,day));
    return d.getUTCFullYear()===year
        && d.getUTCMonth()===month-1 && d.getUTCDate()===day;
}
function previewFundingSetup(snapshot,mode,accountId,date,amountText,categoryId) {
    if(!snapshot || snapshot.source!=="actual-budget"
            || snapshot.readOnly!==true || snapshot.schemaVersion!==1
            || typeof snapshot.sourceKey!=="string"
            || !/^[a-f0-9]{64}$/.test(snapshot.sourceKey)
            || !/^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])$/.test(snapshot.month)
            || !Array.isArray(snapshot.accounts)
            || !Number.isSafeInteger(snapshot.toBudgetCents))
        return {ok:false,reason:"AUTHENTICATED SOURCE UNAVAILABLE"};
    if(mode!=="opening" && mode!=="income")
        return {ok:false,reason:"SELECT A SETUP MODE"};
    const accounts=snapshot.accounts.filter(function(a){return a && a.id===accountId;});
    if(accounts.length!==1 || typeof accounts[0].name!=="string"
            || !Number.isSafeInteger(accounts[0].balanceCents))
        return {ok:false,reason:"SELECT A VALID ON-BUDGET ACCOUNT"};
    if(!validFundingDate(date)
            || (mode==="income" && !date.startsWith(snapshot.month+"-"))
            || (mode==="opening" && date>snapshot.month+"-31"))
        return {ok:false,reason:"CHECK DATE // INCOME MUST MATCH SELECTED MONTH"};
    const amountCents=parseFundingAmountCents(amountText);
    if(amountCents===null)
        return {ok:false,reason:"AMOUNT MUST BE POSITIVE USD WITH 0-2 DECIMALS"};
    let categoryName=null;
    if(mode==="income"){
        const review=snapshot.incomeReview;
        if(!review || review.readOnly!==true
                || review.month!==snapshot.month
                || review.categoriesOverflow===true
                || !Array.isArray(review.incomeCategories))
            return {ok:false,reason:"INCOME CATEGORIES UNAVAILABLE"};
        const categories=review.incomeCategories.filter(function(c){
            return c && c.id===categoryId && typeof c.name==="string";
        });
        if(categories.length!==1)
            return {ok:false,reason:"SELECT AN ACTUAL INCOME CATEGORY"};
        categoryName=categories[0].name;
    }
    return {
        ok:true,mode:mode,sourceKey:snapshot.sourceKey,
        month:snapshot.month,accountId:accountId,
        accountName:accounts[0].name,
        observedAccountBalanceCents:accounts[0].balanceCents,
        reportedToBudgetCents:snapshot.toBudgetCents,
        date:date,amountCents:amountCents,
        categoryId:mode==="income" ? categoryId : null,
        categoryName:categoryName,
        suggestedOperation:mode==="opening" ? "RECONCILE_EXISTING_ACCOUNT"
                                               : "REVIEW_NEW_INCOME_ENTRY",
        openingBalanceVerified:false,
        writeAllowed:false,saveAvailable:false,
        toBudgetAfterCents:null
    };
}
