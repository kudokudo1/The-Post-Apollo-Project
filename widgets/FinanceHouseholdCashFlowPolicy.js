// FinanceW FP1c // pure local/manual cash-flow mathematics.
// No provider, bank data, account identity, network, file IO or real transfers.
function fail(reason) {
    return {ok:false,reason:reason,source:"LOCAL_MANUAL_PLAN_ONLY"};
}
function monthIndex(month) {
    if (typeof month!=="string" ||
            !/^(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])$/.test(month))
        return null;
    return Number(month.slice(0,4))*12+Number(month.slice(5,7))-1;
}
function validRow(row) {
    if (!row || typeof row!=="object" || Array.isArray(row)) return false;
    if (["goal","expense","income"].indexOf(row.kind)<0) return false;
    if (typeof row.id!=="string" || !/^p-[0-9a-f]{32}$/.test(row.id)
            || typeof row.title!=="string"
            || row.title.length<1 || row.title.length>80
            || typeof row.deadlineMonth!=="string"
            || (row.deadlineMonth!=="" && monthIndex(row.deadlineMonth)===null))
        return false;
    if (row.kind!=="goal" && row.deadlineMonth!=="") return false;
    var values=["targetCents","savedCents","monthlyCents"];
    if (values.some(function(key) {
        return !Number.isSafeInteger(row[key])
            || row[key]<0 || row[key]>10000000000;
    })) return false;
    return row.kind==="goal"
        ? row.targetCents>0 && row.savedCents<=row.targetCents
        : row.targetCents===0 && row.savedCents===0 && row.monthlyCents>0;
}
function summarize(rows,horizonMonths) {
    if (!Array.isArray(rows) || rows.length>60 || !rows.every(validRow))
        return fail("INVALID_LOCAL_RECORDS");
    if (!Number.isInteger(horizonMonths) ||
            horizonMonths<1 || horizonMonths>360)
        return fail("INVALID_HORIZON");
    var income=0,expenses=0,contributions=0,incomeCount=0;
    rows.forEach(function(row) {
        if (row.kind==="income") {
            income+=row.monthlyCents;
            incomeCount++;
        } else if (row.kind==="expense") {
            expenses+=row.monthlyCents;
        } else if (row.savedCents<row.targetCents) {
            contributions+=row.monthlyCents;
        }
    });
    // No income record is 'unknown', not an assumed zero paycheck.
    if (incomeCount===0) return fail("ADD_MANUAL_MONTHLY_INCOME");
    var monthlyChange=income-expenses-contributions;
    return {ok:true,source:"LOCAL_MANUAL_PLAN_ONLY",readOnly:true,
        verifiedBankBalance:false,missingCostsPossible:true,
        incomeCents:income,expenseCents:expenses,
        contributionCents:contributions,monthlyChangeCents:monthlyChange,
        horizonMonths:horizonMonths,
        horizonChangeCents:monthlyChange*horizonMonths};
}
function goalStatus(row,currentMonth) {
    if (!validRow(row) || row.kind!=="goal") return fail("INVALID_GOAL");
    var remaining=row.targetCents-row.savedCents;
    var monthsAtRate=remaining===0?0:row.monthlyCents>0
        ?Math.ceil(remaining/row.monthlyCents):null;
    if (row.deadlineMonth==="") {
        return {ok:true,remainingCents:remaining,
            monthsAtRate:monthsAtRate,monthsToDeadline:null,
            requiredMonthlyCents:null,gapMonthlyCents:null};
    }
    var current=monthIndex(currentMonth);
    if (current===null) return fail("INVALID_CURRENT_MONTH");
    var remainingMonths=monthIndex(row.deadlineMonth)-current;
    if (remainingMonths<=0) {
        return {ok:true,remainingCents:remaining,
            monthsAtRate:monthsAtRate,monthsToDeadline:remainingMonths,
            requiredMonthlyCents:null,gapMonthlyCents:null};
    }
    var required=Math.ceil(remaining/remainingMonths);
    return {ok:true,remainingCents:remaining,monthsAtRate:monthsAtRate,
        monthsToDeadline:remainingMonths,requiredMonthlyCents:required,
        gapMonthlyCents:Math.max(0,required-row.monthlyCents)};
}
