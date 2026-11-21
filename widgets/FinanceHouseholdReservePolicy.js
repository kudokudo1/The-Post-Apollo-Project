// FinanceW FP1j // optional, pure, read-only earmarks with a bounded reserve cushion.
// Does not alter actual modeled income, charges, goal contributions or cash.
// No file, account, provider, storage or network operations.
function refuse(reason) {
    return {ok:false,reason:reason,source:"LOCAL_MANUAL_RESERVE_ESTIMATE",
        readOnly:true,bankVerified:false,actualTransfersMade:false};
}
function idx(month) {
    if(typeof month!=="string" ||
            !/^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])$/.test(month))return null;
    return Number(month.slice(0,4))*12+Number(month.slice(5,7))-1;
}
function safe(value) {
    return Number.isSafeInteger(value) && value>=0 && value<=10000000000;
}
function fundsFor(rows,schedules) {
    if(!Array.isArray(rows) || rows.length>60 ||
       !Array.isArray(schedules) || schedules.length>60)
        return refuse("INVALID_INPUT");
    var expenses=new Map(rows.filter(function(row){
        return row && row.kind==="expense" &&
            typeof row.id==="string" && safe(row.monthlyCents);
    }).map(function(row){return [row.id,row];}));
    var billIds=new Set(schedules.filter(function(row){
        return row && row.kind==="bill_due";
    }).map(function(row){return row.expenseId;}));
    var cadences=schedules.filter(function(row){
        return row && row.kind==="bill_cadence";
    });
    if(cadences.length>60)return refuse("TOO_MANY_FUNDS");
    var ids=new Set();
    var funds=[];
    for(var i=0;i<cadences.length;i++) {
        var entry=cadences[i],expense=expenses.get(entry.expenseId);
        if(!expense || !billIds.has(entry.expenseId) ||
           !/^p-[0-9a-f]{32}$/.test(entry.id) ||
           ids.has(entry.expenseId) ||
           (entry.intervalMonths!==3 && entry.intervalMonths!==12) ||
           idx(entry.anchorMonth)===null)
            return refuse("INVALID_FUND_REFERENCE");
        ids.add(entry.expenseId);
        funds.push({id:entry.id,expenseId:entry.expenseId,title:expense.title,
            amountCents:expense.monthlyCents,
            intervalMonths:entry.intervalMonths,
            anchorMonth:entry.anchorMonth,heldCents:0,
            coreHeldCents:0,bufferHeldCents:0,bufferTargetCents:0});
    }
    return {ok:true,funds:funds};
}
// "month" includes the charge month. A full N-month cycle deposits the
// exact bill amount with integer-cent rounding and NO rounding drift.
// The start of the visible horizon assumes zero reserve, not hidden cash.
function depositFor(fund,month) {
    var offset=idx(month)-idx(fund.anchorMonth);
    if(offset<1-fund.intervalMonths)return 0;
    var phase=((offset%fund.intervalMonths)+fund.intervalMonths)
        %fund.intervalMonths;
    var base=Math.floor(fund.amountCents/fund.intervalMonths);
    return base+(phase<fund.amountCents%fund.intervalMonths?1:0);
}
function annotate(rows,schedules,projection,marginPercent) {
    // Explicit scenario choice, not a durable setting or provider preference.
    if(marginPercent===undefined)marginPercent=100;
    if(!Number.isInteger(marginPercent) ||
            [100,110,125].indexOf(marginPercent)<0)
        return refuse("INVALID_RESERVE_CUSHION");
    if(!projection || projection.ok!==true ||
       projection.source!=="LOCAL_MANUAL_TIMELINE_ONLY" ||
       projection.readOnly!==true || projection.bankVerified!==false ||
       typeof projection.contextId!=="string" ||
       idx(projection.startMonth)===null ||
       ![6,12,24].includes(projection.horizonMonths) ||
       !Array.isArray(projection.months) ||
       projection.months.length!==projection.horizonMonths)
        return refuse("TIMELINE_NOT_VERIFIED");
    var prepared=fundsFor(rows,schedules);
    if(!prepared.ok)return prepared;
    var funds=prepared.funds,months=[],byMonth={};
    for(var k=0;k<funds.length;k++) {
        // Safe integer-cent ceiling. A 100% margin gives exactly FP1i.
        funds[k].bufferTargetCents=Math.floor(
            (funds[k].amountCents*(marginPercent-100)+99)/100);
        if(!safe(funds[k].bufferTargetCents))
            return refuse("UNSAFE_RESERVE_TARGET");
    }
    var cumulativeAvailable=0,lastMonth=null;
    for(var i=0;i<projection.months.length;i++){
        var source=projection.months[i],month=source.month;
        if(idx(month)===null || idx(month)!==idx(projection.startMonth)+i ||
           !Number.isSafeInteger(source.changeCents) ||
           !Number.isSafeInteger(source.cumulativeChangeCents) ||
           !Array.isArray(source.billEvents) ||
           !Array.isArray(source.movedToEvents))
            return refuse("TIMELINE_MONTH_MISMATCH");
        var byExpense=new Map();
        var actualChargeEvents=source.billEvents.concat(source.movedToEvents);
        for(var e=0;e<actualChargeEvents.length;e++){
            var bill=actualChargeEvents[e];
            if(!bill || typeof bill.expenseId!=="string" ||
               !safe(bill.amountCents===undefined?bill.movedCents:bill.amountCents))
                return refuse("INVALID_CHARGE_EVENT");
            var amount=bill.amountCents===undefined
                ?bill.movedCents:bill.amountCents;
            byExpense.set(bill.expenseId,
                (byExpense.get(bill.expenseId)||0)+amount);
        }
        var added=0,applied=0,gap=0,bufferAddedTotal=0,details=[];
        for(var j=0;j<funds.length;j++) {
            var fund=funds[j];
            // FP1i's base deposit always continues, even after a skipped
            // charge. The optional buffer separately caps at its fixed target.
            var baseDeposit=depositFor(fund,month);
            var bufferPlan=depositFor({
                amountCents:fund.bufferTargetCents,
                intervalMonths:fund.intervalMonths,
                anchorMonth:fund.anchorMonth
            },month);
            var bufferAdded=Math.min(bufferPlan,
                Math.max(0,fund.bufferTargetCents-fund.bufferHeldCents));
            var setAside=baseDeposit+bufferAdded;
            var paid=byExpense.get(fund.expenseId)||0;
            fund.coreHeldCents+=baseDeposit;
            fund.bufferHeldCents+=bufferAdded;
            var coreUsed=Math.min(fund.coreHeldCents,paid);
            fund.coreHeldCents-=coreUsed;
            var bufferUsed=Math.min(fund.bufferHeldCents,paid-coreUsed);
            fund.bufferHeldCents-=bufferUsed;
            var used=coreUsed+bufferUsed;
            fund.heldCents=fund.coreHeldCents+fund.bufferHeldCents;
            added+=setAside;
            applied+=used;
            gap+=paid-used;
            bufferAddedTotal+=bufferAdded;
            if(![fund.coreHeldCents,fund.bufferHeldCents,fund.heldCents,
                  added,applied,gap,bufferAddedTotal].every(Number.isSafeInteger))
                return refuse("UNSAFE_RESERVE_TOTAL");
            if(setAside || paid)details.push({
                id:fund.id,title:fund.title,amountCents:fund.amountCents,
                intervalMonths:fund.intervalMonths,setAsideCents:setAside,
                bufferAddedCents:bufferAdded,
                bufferTargetCents:fund.bufferTargetCents,
                bufferUsedCents:bufferUsed,
                bufferHeldCents:fund.bufferHeldCents,
                chargeCents:paid,usedCents:used,
                unfundedCents:paid-used,heldCents:fund.heldCents
            });
        }
        var held=funds.reduce(function(sum,f){return sum+f.heldCents;},0);
        var bufferHeld=funds.reduce(function(sum,f){return sum+f.bufferHeldCents;},0);
        var availableChange=source.changeCents-added+applied;
        cumulativeAvailable+=availableChange;
        if(![added,applied,gap,held,bufferHeld,bufferAddedTotal,
             availableChange,cumulativeAvailable,
             source.cumulativeChangeCents-held].every(Number.isSafeInteger) ||
            cumulativeAvailable!==source.cumulativeChangeCents-held)
            return refuse("UNSAFE_RESERVE_TOTAL");
        var data={month:month,reserveAddedCents:added,
            reserveBufferAddedCents:bufferAddedTotal,
            reserveBufferHeldCents:bufferHeld,
            reserveUsedCents:applied,reserveBalanceCents:held,
            uncoveredPeriodicCents:gap,unreservedChangeCents:availableChange,
            cumulativeUnreservedChangeCents:cumulativeAvailable,
            details:details};
        months.push(data);
        byMonth[month]=data;
        lastMonth=month;
    }
    return {ok:true,source:"LOCAL_MANUAL_RESERVE_ESTIMATE",
        readOnly:true,bankVerified:false,actualTransfersMade:false,
        startingReserveKnown:false,startingCashKnown:false,
        simulatedStartingReserveCents:0,
        actualSavingsBalanceKnown:false,notAvailableCash:true,
        reservePolicy:"EARMARK_ONLY_NO_DUPLICATE_EXPENSE",
        reserveMarginPercent:marginPercent,
        scenarioOnly:true,persisted:false,
        monthlyReserveCount:funds.length,
        contextId:projection.contextId,startMonth:projection.startMonth,
        horizonMonths:projection.horizonMonths,lastMonth:lastMonth,
        months:months,byMonth:byMonth};
}
