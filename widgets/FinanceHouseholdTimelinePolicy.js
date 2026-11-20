// FinanceW FP1e: pure month-by-month manual plans with scheduled due days.
// No banking, credentials, network, disk, payments or transfers.
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
function daysIn(month) {
    var year=Number(month.slice(0,4)),mo=Number(month.slice(5,7));
    return new Date(Date.UTC(year,mo,0)).getUTCDate();
}
function validDate(date) {
    if(typeof date!=="string" || !/^(?:19|20)\d{2}-\d{2}-\d{2}$/.test(date))
        return false;
    var month=date.slice(0,7);
    if(indexFor(month)===null)return false;
    var day=Number(date.slice(8));
    return day>=1&&day<=daysIn(month);
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
function validSchedule(row) {
    if(!row||typeof row!=="object"||Array.isArray(row))return false;
    var keys=["amountCents","date","dueDay","expenseId","fundingGoalId",
        "id","kind","title"];
    var actual=Object.keys(row).sort();
    var hasSource=actual.indexOf("sourceMonth")!==-1;
    if(hasSource)keys.push("sourceMonth");
    keys.sort();
    if(actual.length!==keys.length ||
            keys.some(function(k,i){return actual[i]!==k;}))return false;
    if(typeof row.id!=="string"||!/^p-[0-9a-f]{32}$/.test(row.id)
       ||typeof row.kind!=="string")return false;
    if(hasSource && (typeof row.sourceMonth!=="string" ||
        (row.kind!=="bill_defer" && row.sourceMonth!=="")))return false;
    if(row.kind==="bill_defer")
        return hasSource && row.title==="" && row.fundingGoalId===""
            && row.amountCents===0 && row.dueDay===0
            && typeof row.expenseId==="string"
            && /^p-[0-9a-f]{32}$/.test(row.expenseId)
            && indexFor(row.sourceMonth)!==null
            && validDate(row.date) && row.date.slice(0,7)>row.sourceMonth;
    if(row.kind==="bill_due")
        return row.title===""&&row.date===""&&row.fundingGoalId===""
            &&row.amountCents===0&&typeof row.expenseId==="string"
            &&/^p-[0-9a-f]{32}$/.test(row.expenseId)
            &&Number.isInteger(row.dueDay)&&row.dueDay>=1&&row.dueDay<=31;
    if(row.kind==="bill_skip")
        return row.title===""&&row.fundingGoalId===""&&row.amountCents===0
            &&row.dueDay===0&&row.expenseId!==""&&/^p-[0-9a-f]{32}$/.test(row.expenseId)
            &&indexFor(row.date)!==null;
    if(row.kind==="purchase")
        return typeof row.title==="string"&&row.title.length>=1
            &&row.title.length<=80&&validDate(row.date)
            &&row.expenseId===""&&row.dueDay===0
            &&Number.isSafeInteger(row.amountCents)&&row.amountCents>0
            &&row.amountCents<=10000000000
            &&typeof row.fundingGoalId==="string"
            &&(row.fundingGoalId===""||/^p-[0-9a-f]{32}$/.test(row.fundingGoalId));
    return false;
}
// Explicit coverage indicator for entered records only, NEVER an assurance
// all household obligations are known. Works even with no income entered.
function coverage(rows,schedules) {
    if(!Array.isArray(rows)||rows.length>60||!rows.every(valid))
        return refuse("INVALID_LOCAL_RECORDS");
    if(!Array.isArray(schedules)||schedules.length>60
       ||!schedules.every(validSchedule))
        return refuse("INVALID_LOCAL_SCHEDULES");
    var rowIds=rows.map(function(row){return row.id;});
    var scheduleIds=schedules.map(function(row){return row.id;});
    if(new Set(rowIds).size!==rowIds.length)
        return refuse("DUPLICATE_RECORDS");
    if(new Set(scheduleIds).size!==scheduleIds.length)
        return refuse("DUPLICATE_SCHEDULES");
    var expenses=rows.filter(function(row){return row.kind==="expense";});
    var goals=rows.filter(function(row){return row.kind==="goal";});
    var income=rows.filter(function(row){return row.kind==="income";});
    var bills=schedules.filter(function(row){return row.kind==="bill_due";});
    var skips=schedules.filter(function(row){return row.kind==="bill_skip";});
    var deferrals=schedules.filter(function(row){return row.kind==="bill_defer";});
    var purchases=schedules.filter(function(row){return row.kind==="purchase";});
    var ids=bills.map(function(row){return row.expenseId;});
    if(new Set(ids).size!==ids.length)
        return refuse("DUPLICATE_BILL_SCHEDULE");
    var expenseIds=new Set(expenses.map(function(row){return row.id;}));
    var goalIds=new Set(goals.map(function(row){return row.id;}));
    if(bills.some(function(row){return !expenseIds.has(row.expenseId);})
       ||purchases.some(function(row){return row.fundingGoalId!=="" &&
                !goalIds.has(row.fundingGoalId);})
       ||skips.some(function(row){return ids.indexOf(row.expenseId)===-1;}))
        return refuse("SCHEDULE_REFERENCE_MISSING");
    var skipKeys=skips.map(function(row){return row.expenseId+"|"+row.date;});
    if(new Set(skipKeys).size!==skipKeys.length)
        return refuse("DUPLICATE_BILL_EXCEPTION");
    var deferKeys=deferrals.map(function(row){
        return row.expenseId+"|"+row.sourceMonth;
    });
    if(new Set(deferKeys).size!==deferKeys.length)
        return refuse("DUPLICATE_BILL_DEFERRAL");
    if(deferKeys.some(function(key){return skipKeys.indexOf(key)!==-1;}))
        return refuse("CONFLICTING_BILL_EXCEPTION");
    if(deferrals.some(function(row){return ids.indexOf(row.expenseId)===-1;}))
        return refuse("SCHEDULE_REFERENCE_MISSING");
    var undated=expenses.filter(function(row) {
        return ids.indexOf(row.id)===-1;
    });
    return {ok:true,source:"LOCAL_MANUAL_COVERAGE_ONLY",readOnly:true,
        bankVerified:false,identityVerified:false,
        dueDateCoverageOnly:true,allObligationsKnown:false,
        monthlyExpenseCount:expenses.length,datedExpenseCount:bills.length,
        undatedExpenseCount:undated.length,
        undatedExpenseTitles:undated.map(function(row){return row.title;}),
        manualIncomeCount:income.length,
        monthlyExceptionCount:skips.length,
        deferredPaymentCount:deferrals.length,
        plannedPurchaseCount:purchases.length};
}

// Supports the FP1d 4-argument call for inherited read-only tests.
// New FP1e callers must always provide an explicit schedules array.
function project(rows,schedules,startMonth,horizonMonths,contextId) {
    if(typeof schedules==="string" && typeof startMonth==="number"
       && typeof horizonMonths==="string" && contextId===undefined) {
        contextId=horizonMonths;
        horizonMonths=startMonth;
        startMonth=schedules;
        schedules=[];
    }
    var validContexts=["mine","shared","mom","granny","family"];
    if(typeof contextId!=="string"||validContexts.indexOf(contextId)<0)
        return refuse("UNKNOWN_CONTEXT");
    var start=indexFor(startMonth);
    if(start===null)return refuse("INVALID_START_MONTH");
    if([6,12,24].indexOf(horizonMonths)<0)
        return refuse("INVALID_HORIZON");
    var audit=coverage(rows,schedules);
    if(!audit.ok)return refuse(audit.reason);
    var incomeRows=rows.filter(function(row){return row.kind==="income";});
    if(incomeRows.length===0)return refuse("ADD_MANUAL_MONTHLY_INCOME");
    var income=incomeRows.reduce(function(total,row){return total+row.monthlyCents;},0);
    var costs=rows.filter(function(row){return row.kind==="expense";})
        .reduce(function(total,row){return total+row.monthlyCents;},0);
    var goals=rows.filter(function(row){return row.kind==="goal";})
        .map(function(row) {
            return {id:row.id,title:row.title,deadlineMonth:row.deadlineMonth,
                targetCents:row.targetCents,allocatedCents:row.savedCents,
                plannedMonthlyCents:row.monthlyCents,completedByPurchase:false};
        });
    var goalsById=new Map(goals.map(function(row){return [row.id,row];}));
    var expensesById=new Map(rows.filter(function(row){return row.kind==="expense";})
        .map(function(row){return [row.id,row];}));
    var billRows=schedules.filter(function(row){return row.kind==="bill_due";});
    var purchases=schedules.filter(function(row){return row.kind==="purchase";});
    var skipRows=schedules.filter(function(row){return row.kind==="bill_skip";});
    var deferRows=schedules.filter(function(row){return row.kind==="bill_defer";});
    purchases.sort(function(a,b) {
        return a.date.localeCompare(b.date)||a.id.localeCompare(b.id);
    });
    var months=[],cumulative=0;
    var priorDeadlines=goals.filter(function(goal) {
        return goal.deadlineMonth!==""&&indexFor(goal.deadlineMonth)<start;
    }).map(function(goal) {
        return {id:goal.id,title:goal.title,deadlineMonth:goal.deadlineMonth,
            status:"PAST_TARGET",gapCents:Math.max(0,
                goal.targetCents-goal.allocatedCents)};
    });
    var priorSchedules=purchases.filter(function(row) {
        return indexFor(row.date.slice(0,7))<start;
    }).map(function(row) {
        return {id:row.id,date:row.date,title:row.title,
            amountCents:row.amountCents,status:"PAST_PLANNED_PAYMENT"};
    });
    for(var i=0;i<horizonMonths;i++){
        var absolute=start+i,month=monthFor(absolute),contributions=0,events=[];
        for(var j=0;j<goals.length;j++){
            var goal=goals[j];
            var outstanding=goal.completedByPurchase?0:
                Math.max(0,goal.targetCents-goal.allocatedCents);
            var contribution=Math.min(outstanding,goal.plannedMonthlyCents);
            goal.allocatedCents+=contribution;
            contributions+=contribution;
            if(goal.deadlineMonth!==""&&indexFor(goal.deadlineMonth)===absolute){
                var gap=Math.max(0,goal.targetCents-goal.allocatedCents);
                events.push({id:goal.id,title:goal.title,
                    deadlineMonth:goal.deadlineMonth,
                    status:goal.completedByPurchase?"GOAL_SPENT_EARLIER"
                        :gap>0?"TARGET_SHORTFALL":"TARGET_FUNDED_IN_MODEL",
                    gapCents:gap,targetCents:goal.targetCents,
                    projectedSavedCents:goal.allocatedCents});
            }
        }
        var excluded=skipRows.filter(function(row){return row.date===month;});
        var moved=deferRows.filter(function(row){return row.sourceMonth===month;});
        var omittedIds=new Set(excluded.concat(moved).map(function(row){
            return row.expenseId;
        }));
        var exceptionEvents=excluded.map(function(row) {
            var expense=expensesById.get(row.expenseId);
            return {id:row.id,expenseId:row.expenseId,title:expense.title,
                month:month,excludedCents:expense.monthlyCents};
        });
        var movedFromEvents=moved.map(function(row){
            var expense=expensesById.get(row.expenseId);
            return {id:row.id,expenseId:row.expenseId,title:expense.title,
                sourceMonth:row.sourceMonth,targetDate:row.date,
                movedCents:expense.monthlyCents};
        });
        var currentCosts=costs-excluded.reduce(function(total,row){
            return total+expensesById.get(row.expenseId).monthlyCents;
        },0)-moved.reduce(function(total,row){
            return total+expensesById.get(row.expenseId).monthlyCents;
        },0);
        var movedToEvents=deferRows.filter(function(row){
            return row.date.slice(0,7)===month;
        }).map(function(row){
            var expense=expensesById.get(row.expenseId);
            return {id:row.id,expenseId:row.expenseId,title:expense.title,
                sourceMonth:row.sourceMonth,targetDate:row.date,
                movedCents:expense.monthlyCents};
        }).sort(function(a,b){return a.targetDate.localeCompare(b.targetDate)
            ||a.id.localeCompare(b.id);});
        var movedPaymentCents=movedToEvents.reduce(function(total,row){
            return total+row.movedCents;
        },0);
        var billEvents=billRows.filter(function(row){
            return !omittedIds.has(row.expenseId);
        }).map(function(row) {
            var expense=expensesById.get(row.expenseId);
            var day=Math.min(row.dueDay,daysIn(month));
            return {id:row.id,expenseId:row.expenseId,title:expense.title,
                dueDate:month+"-"+String(day).padStart(2,"0"),
                adjustedToMonthEnd:day!==row.dueDay,
                amountCents:expense.monthlyCents};
        }).sort(function(a,b){return a.dueDate.localeCompare(b.dueDate)
            ||a.id.localeCompare(b.id);});
        var purchaseNewCash=0,goalFunded=0,purchaseEvents=[];
        purchases.forEach(function(row) {
            if(row.date.slice(0,7)!==month)return;
            var reserved=0;
            if(row.fundingGoalId!==""){
                var funding=goalsById.get(row.fundingGoalId);
                reserved=Math.min(row.amountCents,funding.allocatedCents);
                funding.allocatedCents-=reserved;
                funding.completedByPurchase=true;
            }
            var newCash=row.amountCents-reserved;
            purchaseNewCash+=newCash;
            goalFunded+=reserved;
            purchaseEvents.push({id:row.id,title:row.title,date:row.date,
                amountCents:row.amountCents,goalFundedCents:reserved,
                newCashCents:newCash,fundingGoalId:row.fundingGoalId});
        });
        var change=income-currentCosts-contributions-purchaseNewCash-movedPaymentCents;
        cumulative+=change;
        if(![contributions,purchaseNewCash,goalFunded,movedPaymentCents,
               currentCosts,change,cumulative].every(
            Number.isSafeInteger))return refuse("UNSAFE_TOTAL");
        months.push({month:month,incomeCents:income,
            expenseCents:currentCosts,baseExpenseCents:costs,
            exceptionEvents:exceptionEvents,
            movedFromEvents:movedFromEvents,
            movedToEvents:movedToEvents,
            movedPaymentCents:movedPaymentCents,
            contributionCents:contributions,
            purchaseNewCashCents:purchaseNewCash,
            purchaseGoalFundedCents:goalFunded,
            changeCents:change,cumulativeChangeCents:cumulative,
            events:events,billEvents:billEvents,purchaseEvents:purchaseEvents});
    }
    return {ok:true,source:"LOCAL_MANUAL_TIMELINE_ONLY",readOnly:true,
        bankVerified:false,identityVerified:false,contextId:contextId,
        startMonth:startMonth,horizonMonths:horizonMonths,
        startingCashKnown:false,missingCostsPossible:true,
        futurePurchasesCharged:false,actualTransfersMade:false,
        plannedPurchaseOutflowModeled:true,
        coverage:audit,
        priorDeadlines:priorDeadlines,priorSchedules:priorSchedules,months:months};
}
