// FinanceW Banking M4e // Read-only projection of the COMPLETE current M3
// manual/demo session, bounded at 300 entries. No persistence, import,
// provider credentials, network operations or financial action execution.
var PAGE_SIZE=20;
var MAX_ENTRIES=300;
var MAX_ACCOUNTS=12;
var MAX_CENTS=999999999;
function fail(reason){return {ok:false,error:reason};}
function safeDate(text) {
    if(typeof text!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(text))return false;
    var p=text.split("-").map(Number),d=new Date(Date.UTC(p[0],p[1]-1,p[2]));
    return p[0]>=1900&&p[0]<=2100&&d.getUTCFullYear()===p[0]
        &&d.getUTCMonth()===p[1]-1&&d.getUTCDate()===p[2];
}
function safeText(value,length) {
    return typeof value==="string"&&value.trim().length>0&&value.length<=length
        &&! /[\u0000-\u001F\u007F]/.test(value);
}
function compareEntries(a,b) {
    if(a.date!==b.date)return a.date>b.date?-1:1;
    var x=/-([1-9][0-9]*)$/.exec(a.id||""),
        y=/-([1-9][0-9]*)$/.exec(b.id||"");
    var xi=x?Number(x[1]):null,yi=y?Number(y[1]):null;
    if(Number.isSafeInteger(xi)&&Number.isSafeInteger(yi)&&xi!==yi)return yi-xi;
    return a.id<b.id?1:a.id>b.id?-1:0;
}
function project(projection,session,options) {
    if(!projection||projection.ok!==true||projection.sectionKind!=="activity"
       ||projection.connected!==false||projection.persisted!==false
       ||!["cashapp","chime","paypal","bank"].includes(projection.providerId)
       ||!Array.isArray(projection.allAccounts)
       ||projection.allAccounts.length>MAX_ACCOUNTS
       ||!Number.isSafeInteger(projection.transactionCount))
        return fail("INVALID PROVIDER ACTIVITY VIEW");
    if(!session||!["empty","manual","demo"].includes(session.mode)
       ||!Array.isArray(session.accounts)||session.accounts.length>MAX_ACCOUNTS
       ||!Array.isArray(session.entries)||session.entries.length>MAX_ENTRIES
       ||!(session.mode==="empty"?
            session.accounts.length===0&&session.entries.length===0:
            session.accounts.length>0)
       ||projection.dataLabel!==(
          session.mode==="manual"?"MANUAL SESSION":
          session.mode==="demo"?"FICTIONAL DEMO":"NO MANUAL ACCOUNTS"))
        return fail("INVALID OR STALE MANUAL SESSION");
    var opts=options||{},direction=opts.direction===undefined?"all":opts.direction,
        accountId=opts.accountId===undefined?"":opts.accountId,
        rawQuery=opts.query===undefined?"":opts.query,
        fromDate=opts.fromDate===undefined?"":opts.fromDate,
        toDate=opts.toDate===undefined?"":opts.toDate,
        requested=opts.page===undefined?0:opts.page;
    if(!["all","in","out"].includes(direction)
       ||typeof accountId!=="string"||typeof rawQuery!=="string"
       ||rawQuery.length>64||/[\u0000-\u001F\u007F]/.test(rawQuery)
       ||!Number.isSafeInteger(requested)||requested<0||requested>MAX_ENTRIES)
        return fail("INVALID ACTIVITY FILTER");
    if(typeof fromDate!=="string"||typeof toDate!=="string"
       ||(fromDate!==""&&!safeDate(fromDate))
       ||(toDate!==""&&!safeDate(toDate))
       ||(fromDate!==""&&toDate!==""&&fromDate>toDate))
        return fail("INVALID DATE RANGE // USE YYYY-MM-DD AND FROM <= TO");
    var known=Object.create(null),providerAccounts=Object.create(null);
    var totalProviderAccounts=0;
    for(var i=0;i<session.accounts.length;i++) {
        var a=session.accounts[i];
        if(!a||typeof a.id!=="string"||!/^(acct|demo)-[1-9]\d*$/.test(a.id)
           ||Object.prototype.hasOwnProperty.call(known,a.id)
           ||!["cashapp","chime","paypal","bank"].includes(a.providerId)
           ||!safeText(a.nickname,42)||a.origin!==session.mode)
            return fail("INVALID MANUAL ACCOUNT IDENTITY");
        known[a.id]=a;
        if(a.providerId===projection.providerId) {
            providerAccounts[a.id]=a;
            totalProviderAccounts++;
        }
    }
    if(totalProviderAccounts!==projection.allAccounts.length)
        return fail("PROVIDER ACCOUNT VIEW MISMATCH");
    for(var j=0;j<projection.allAccounts.length;j++) {
        var view=projection.allAccounts[j];
        if(!view||!Object.prototype.hasOwnProperty.call(providerAccounts,view.id)
           ||view.providerId!==projection.providerId
           ||view.nickname!==providerAccounts[view.id].nickname
           ||view.productId!==providerAccounts[view.id].productId)
            return fail("STALE PROVIDER ACCOUNT VIEW");
    }
    if(accountId && !Object.prototype.hasOwnProperty.call(providerAccounts,accountId))
        return fail("ACCOUNT IS NOT IN THIS PROVIDER");
    // All breakdown buckets are created solely from validated provider accounts.
    // They accumulate the exact same filtered records as the provider totals.
    var breakdownById=Object.create(null),breakdown=[];
    for(var b=0;b<projection.allAccounts.length;b++) {
        var account=projection.allAccounts[b];
        var bucket={accountId:account.id,accountNickname:account.nickname,
            matchedCount:0,matchedInCents:0,matchedOutCents:0};
        breakdownById[account.id]=bucket;
        breakdown.push(bucket);
    }
    var uniqueEntries=Object.create(null),rows=[],providerCount=0;
    var matchedInCents=0,matchedOutCents=0;
    for(var k=0;k<session.entries.length;k++) {
        var e=session.entries[k];
        if(!e||typeof e.id!=="string"
           ||!/^(entry|demo-entry)-[1-9]\d*$/.test(e.id)
           ||Object.prototype.hasOwnProperty.call(uniqueEntries,e.id)
           ||typeof e.accountId!=="string"
           ||!Object.prototype.hasOwnProperty.call(known,e.accountId)
           ||!safeDate(e.date)||!safeText(e.description,120)
           ||!Number.isSafeInteger(e.amountCents)||e.amountCents===0
           ||Math.abs(e.amountCents)>MAX_CENTS||e.origin!==session.mode)
            return fail("INVALID MANUAL TRANSACTION RECORD");
        uniqueEntries[e.id]=true;
        var owned=providerAccounts[e.accountId];
        if(!owned)continue; // Never expose another provider's account activity
        providerCount++;
        if(accountId && accountId!==e.accountId)continue;
        if(fromDate!==""&&e.date<fromDate)continue;
        if(toDate!==""&&e.date>toDate)continue;
        if(direction==="in"&&e.amountCents<=0)continue;
        if(direction==="out"&&e.amountCents>=0)continue;
        var q=rawQuery.trim().toLowerCase();
        if(q && e.description.toLowerCase().indexOf(q)<0
             &&owned.nickname.toLowerCase().indexOf(q)<0)continue;
        var bucket=breakdownById[e.accountId];
        if(!bucket)return fail("INVALID PROVIDER ACTIVITY BUCKET");
        bucket.matchedCount++;
        if(e.amountCents>0) {
            matchedInCents+=e.amountCents;
            bucket.matchedInCents+=e.amountCents;
        } else {
            matchedOutCents+=-e.amountCents;
            bucket.matchedOutCents+=-e.amountCents;
        }
        rows.push({id:e.id,accountId:e.accountId,accountNickname:owned.nickname,
            date:e.date,description:e.description,amountCents:e.amountCents});
    }
    if(providerCount!==projection.transactionCount)
        return fail("STALE PROVIDER TRANSACTION COUNT");
    var accountBreakdown=[],checkIn=0,checkOut=0,checkCount=0;
    for(var t=0;t<breakdown.length;t++) {
        var item=breakdown[t];
        if(item.matchedCount===0)continue;
        if(!Number.isSafeInteger(item.matchedCount)
           ||!Number.isSafeInteger(item.matchedInCents)
           ||!Number.isSafeInteger(item.matchedOutCents))
            return fail("INVALID SESSION MOVEMENT TOTAL");
        checkCount+=item.matchedCount;
        checkIn+=item.matchedInCents;
        checkOut+=item.matchedOutCents;
        accountBreakdown.push({accountId:item.accountId,
            accountNickname:item.accountNickname,
            matchedCount:item.matchedCount,
            matchedInCents:item.matchedInCents,
            matchedOutCents:item.matchedOutCents,
            matchedNetCents:item.matchedInCents-item.matchedOutCents});
    }
    if(!Number.isSafeInteger(matchedInCents)
       ||!Number.isSafeInteger(matchedOutCents)
       ||checkCount!==rows.length
       ||checkIn!==matchedInCents||checkOut!==matchedOutCents)
        return fail("INCONSISTENT SESSION MOVEMENT TOTAL");
    rows.sort(compareEntries);
    var matchCount=rows.length,pageCount=Math.max(1,Math.ceil(matchCount/PAGE_SIZE)),
        pageIndex=Math.min(requested,pageCount-1),start=pageIndex*PAGE_SIZE,
        displayed=rows.slice(start,start+PAGE_SIZE);
    return {ok:true,rows:displayed,totalMatches:matchCount,
        providerSessionCount:providerCount,sessionEntryCount:session.entries.length,
        pageIndex:pageIndex,pageCount:pageCount,pageSize:PAGE_SIZE,
        from:matchCount?start+1:0,to:Math.min(start+PAGE_SIZE,matchCount),
        accountId:accountId,direction:direction,
        fromDate:fromDate,toDate:toDate,
        matchedInCents:matchedInCents,matchedOutCents:matchedOutCents,
        matchedNetCents:matchedInCents-matchedOutCents,
        accountBreakdown:accountBreakdown,
        totalsScope:"FILTERED SESSION ENTRIES // NOT VERIFIED INCOME OR SPENDING",
        scope:session.mode==="demo"?"COMPLETE FICTIONAL DEMO SESSION":
              "COMPLETE CURRENT MANUAL SESSION",
        connected:false,persisted:false};
}
