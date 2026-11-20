// FinanceW FP1d: pure month-by-month projections over one local planning
// context's manually entered records. No bank, network, disk or transfer.
function refuse(reason) {
    return {ok:false,reason:reason,source:"LOCAL_MANUAL_TIMELINE_ONLY",
        readOnly:true,bankVerified:false};
}
function indexFor(month) {
    if(typeof month!=="string"
       || !/^(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])$/.test(month))
        return null;
    return Number(month.slice(0,4))*12+Number(month.slice(5,7))-1;
}
function monthFor(index) {
    var year=Math.floor(index/12),month=index-year*12+1;
    return String(year).padStart(4,"0")+"-"+String(month).padStart(2,"0");
}
function valid(row) {
    if(!row||typeof row!=="object"||Array.isArray(row))return false;
    if(typeof row.id!=="string"||!/^p-[0-9a-f]{32}$/.test(row.id)
       ||typeof row.title!=="string"||row.title.length<1||row.title.length>80
       ||["goal","income","expense"].indexOf(row.kind)<0
       ||typeof row.deadlineMonth!=="string"
       ||(row.deadlineMonth!==""&&indexFor(row.deadlineMonth)===null)
       ||(row.kind!=="goal"&&row.deadlineMonth!==""))return false;
    var monetary=["targetCents","savedCents","monthlyCents"];
    if(monetary.some(function(k){return !Number.isSafeInteger(row[k])
        ||row[k]<0||row[k]>10000000000;}))return false;
    return row.kind==="goal"
        ?row.targetCents>0&&row.savedCents<=row.targetCents
        :row.targetCents===0&&row.savedCents===0&&row.monthlyCents>0;
}
function project(rows,startMonth,horizonMonths,contextId) {
    var validContexts=["mine","shared","mom","granny","family"];
    if(typeof contextId!=="string"||validContexts.indexOf(contextId)<0)
        return refuse("UNKNOWN_CONTEXT");
    var start=indexFor(startMonth);
    if(start===null)return refuse("INVALID_START_MONTH");
    if([6,12,24].indexOf(horizonMonths)<0)
        return refuse("INVALID_HORIZON");
    if(!Array.isArray(rows)||rows.length>60||!rows.every(valid))
        return refuse("INVALID_LOCAL_RECORDS");
    var ids=rows.map(function(row){return row.id;});
    if(new Set(ids).size!==ids.length)return refuse("DUPLICATE_RECORDS");
    var incomeRows=rows.filter(function(row){return row.kind==="income";});
    if(incomeRows.length===0)return refuse("ADD_MANUAL_MONTHLY_INCOME");
    var incomes=incomeRows.reduce(function(total,row){return total+row.monthlyCents;},0);
    var costs=rows.filter(function(row){return row.kind==="expense";})
        .reduce(function(total,row){return total+row.monthlyCents;},0);
    var goals=rows.filter(function(row){return row.kind==="goal";})
        .map(function(row) {
            return {id:row.id,title:row.title,deadlineMonth:row.deadlineMonth,
                targetCents:row.targetCents,allocatedCents:row.savedCents,
                plannedMonthlyCents:row.monthlyCents};
        });
    var months=[],cumulative=0;
    var priorDeadlines=goals.filter(function(goal) {
        return goal.deadlineMonth!==""&&indexFor(goal.deadlineMonth)<start;
    }).map(function(goal) {
        return {id:goal.id,title:goal.title,deadlineMonth:goal.deadlineMonth,
            status:"PAST_TARGET",gapCents:Math.max(0,
                goal.targetCents-goal.allocatedCents)};
    });
    for(var i=0;i<horizonMonths;i++){
        var absolute=start+i,contributions=0,events=[];
        for(var j=0;j<goals.length;j++){
            var goal=goals[j];
            // Contributions are capped and are not assumed to move real cash.
            var outstanding=Math.max(0,goal.targetCents-goal.allocatedCents);
            var contribution=Math.min(outstanding,goal.plannedMonthlyCents);
            goal.allocatedCents+=contribution;
            contributions+=contribution;
            if(goal.deadlineMonth!==""&&indexFor(goal.deadlineMonth)===absolute){
                var gap=Math.max(0,goal.targetCents-goal.allocatedCents);
                events.push({id:goal.id,title:goal.title,
                    deadlineMonth:goal.deadlineMonth,
                    status:gap>0?"TARGET_SHORTFALL":"TARGET_FUNDED_IN_MODEL",
                    gapCents:gap,targetCents:goal.targetCents,
                    projectedSavedCents:goal.allocatedCents});
            }
        }
        var change=incomes-costs-contributions;
        cumulative+=change;
        if(!Number.isSafeInteger(cumulative)||!Number.isSafeInteger(contributions))
            return refuse("UNSAFE_TOTAL");
        months.push({month:monthFor(absolute),incomeCents:incomes,
            expenseCents:costs,contributionCents:contributions,
            changeCents:change,cumulativeChangeCents:cumulative,events:events});
    }
    return {ok:true,source:"LOCAL_MANUAL_TIMELINE_ONLY",readOnly:true,
        bankVerified:false,identityVerified:false,contextId:contextId,
        startMonth:startMonth,horizonMonths:horizonMonths,
        startingCashKnown:false,missingCostsPossible:true,
        futurePurchasesCharged:false,actualTransfersMade:false,
        priorDeadlines:priorDeadlines,months:months};
}
