// FinanceW Banking M4 // Provider-specific navigation over M3 MANUAL/DEMO data.
// This does not implement, invoke, or imply an authorized provider connection.
var CATALOG=[
    {id:"cashapp",name:"Cash App",features:[
        {id:"home",label:"HOME",kind:"accounts",summary:"Manual Cash App balance and account details only."},
        {id:"payments",label:"PAYMENTS",kind:"restricted",summary:"Sending, requesting and receiving payments require the official provider's authorized workflows."},
        {id:"card",label:"CARD",kind:"restricted",summary:"Cash App Card controls and sensitive card information are not available through this manual workspace."},
        {id:"stocks",label:"STOCKS",kind:"restricted",summary:"No linked brokerage holdings, investment transactions or stock trading permissions. FinanceW Market is a separate research workspace."},
        {id:"borrow",label:"BORROW",kind:"restricted",summary:"No borrowing eligibility, loan balance, due date, application or repayment access is connected."},
        {id:"savings",label:"SAVINGS",kind:"restricted",summary:"No verified Cash App savings product or savings balance is connected."},
        {id:"activity",label:"ACTIVITY",kind:"activity",summary:"Shows only entries manually added in Banking Accounts or clearly marked fictional demo activity."},
        {id:"security",label:"SECURITY",kind:"restricted",summary:"Provider login, identity, authentication, consent, card security and permissions must stay with authorized provider/Connections controls."}
    ]},
    {id:"chime",name:"Chime",features:[
        {id:"home",label:"HOME",kind:"accounts",summary:"Manual Chime account estimates, not verified balances."},
        {id:"checking",label:"CHECKING",kind:"product",productId:"chime-checking",summary:"Manually labeled Chime checking account details only."},
        {id:"savings",label:"SAVINGS",kind:"product",productId:"chime-savings",summary:"Manually labeled Chime savings account details only."},
        {id:"card",label:"CARD",kind:"restricted",summary:"Card, lock, PIN and spending controls require explicit verified provider authorization."},
        {id:"transfers",label:"TRANSFERS",kind:"restricted",summary:"Direct deposits, linked-bank transfers and other movements require provider-supported workflows."},
        {id:"credit",label:"CREDIT",kind:"restricted",summary:"Credit products and eligibility cannot be inferred from a checking account label."},
        {id:"activity",label:"ACTIVITY",kind:"activity",summary:"Manual or fictional Chime entries only, not bank-confirmed activity."},
        {id:"security",label:"SECURITY",kind:"restricted",summary:"Chime identity, login, card and consent settings remain outside this disconnected session."}
    ]},
    {id:"paypal",name:"PayPal",features:[
        {id:"home",label:"HOME",kind:"accounts",summary:"Manual PayPal wallet estimate, not a connected PayPal balance."},
        {id:"wallet",label:"WALLET",kind:"product",productId:"paypal-wallet",summary:"Manually labeled PayPal balance account details only."},
        {id:"payments",label:"PAYMENTS",kind:"restricted",summary:"Send/receive, merchant checkout and payout operations require distinct authorized provider capabilities."},
        {id:"cards",label:"CARDS",kind:"restricted",summary:"PayPal card products and their controls are not connected."},
        {id:"savings",label:"SAVINGS",kind:"restricted",summary:"No verified PayPal savings product or balance is connected."},
        {id:"paylater",label:"PAY LATER",kind:"restricted",summary:"Pay-later eligibility, obligations and applications are not available through this manual screen."},
        {id:"activity",label:"ACTIVITY",kind:"activity",summary:"Manual or fictional PayPal activity only; no merchant transactions imported."},
        {id:"security",label:"SECURITY",kind:"restricted",summary:"Sign-in, identity and consent management must use verified provider authorization."}
    ]},
    {id:"bank",name:"Other Bank",features:[
        {id:"home",label:"HOME",kind:"accounts",summary:"Generic manual bank account directory, not a banking connection."},
        {id:"checking",label:"CHECKING",kind:"product",productId:"bank-checking",summary:"Manual checking estimate only."},
        {id:"savings",label:"SAVINGS",kind:"product",productId:"bank-savings",summary:"Manual savings estimate only."},
        {id:"transfers",label:"TRANSFERS",kind:"restricted",summary:"Transfers require verified authorization for a specific financial institution and payment rail."},
        {id:"cards",label:"CARDS",kind:"restricted",summary:"No issuer-linked card management is enabled."},
        {id:"lending",label:"LENDING",kind:"restricted",summary:"Loan accounts and credit products cannot be inferred from a manual cash label."},
        {id:"activity",label:"ACTIVITY",kind:"activity",summary:"Manual or fictional bank activity only."},
        {id:"security",label:"SECURITY",kind:"restricted",summary:"Account verification, authorized login and consent are not connected."}
    ]}
];
function providers(){
    return CATALOG.map(function(p){
        return {id:p.id,name:p.name,features:p.features.map(function(f){
            return {id:f.id,label:f.label,kind:f.kind,summary:f.summary,
                productId:f.productId||null};
        })};
    });
}
function lookup(id) {
    return CATALOG.find(function(p){return p.id===id;})||null;
}
function isProviderId(id){return !!lookup(id);}
function money(cents) {
    if(!Number.isSafeInteger(cents))return "UNKNOWN";
    return (cents<0?"-$":"$")+(Math.abs(cents)/100).toFixed(2);
}
// Reusable newest-first ordering. M3 entry IDs use an increasing numeric
// suffix; plain lexical order would put entry-9 after entry-10 incorrectly.
function compareSessionActivity(a,b) {
    if(a.date!==b.date)return a.date>b.date?-1:1;
    var am=/-([1-9][0-9]*)$/.exec(a.id||"");
    var bm=/-([1-9][0-9]*)$/.exec(b.id||"");
    var ai=am?Number(am[1]):null, bi=bm?Number(bm[1]):null;
    if(Number.isSafeInteger(ai)&&Number.isSafeInteger(bi)&&ai!==bi)
        return bi-ai;
    return a.id<b.id?1:a.id>b.id?-1:0;
}
function build(providerId,snapshot,sectionId) {
    var provider=lookup(providerId);
    if(!provider)return {ok:false,error:"UNKNOWN PROVIDER"};
    if(!snapshot||snapshot.ok!==true||snapshot.connected!==false
       ||snapshot.persisted!==false||!Array.isArray(snapshot.accounts)
       ||snapshot.accounts.length>12||!["empty","manual","demo"].includes(snapshot.mode))
        return {ok:false,error:"INVALID MANUAL ACCOUNT SNAPSHOT"};
    var selected=provider.features.find(function(f){return f.id===sectionId;})
                 ||provider.features[0];
    var accounts=[];
    var seen={};
    for(var i=0;i<snapshot.accounts.length;i++){
        var row=snapshot.accounts[i];
        if(!row||typeof row.id!=="string"||seen[row.id]
           ||typeof row.providerId!=="string"
           ||typeof row.productId!=="string"
           ||typeof row.nickname!=="string"
           ||typeof row.providerName!=="string"
           ||typeof row.productName!=="string"
           ||!Number.isSafeInteger(row.transactionCount)
           ||row.transactionCount<0||row.transactionCount>300
           ||!Number.isSafeInteger(row.debitsCents)||row.debitsCents<0
           ||!Number.isSafeInteger(row.creditsCents)||row.creditsCents<0
           ||!Number.isSafeInteger(row.netChangeCents)
           ||row.creditsCents-row.debitsCents!==row.netChangeCents
           ||(row.balanceCents!==null
                &&(!Number.isSafeInteger(row.balanceCents)
                    ||Math.abs(row.balanceCents)>999999999))
           ||!Array.isArray(row.recent)||row.recent.length>12)
            return {ok:false,error:"INVALID MANUAL ACCOUNT SNAPSHOT"};
        seen[row.id]=true;
        if(row.providerId===providerId)accounts.push(row);
    }
    var known=0,subtotal=0,unknown=0,txCount=0,activity=[];
    for(var j=0;j<accounts.length;j++){
        var account=accounts[j];
        if(account.balanceCents===null)unknown++;
        else{known++;subtotal+=account.balanceCents;}
        txCount+=account.transactionCount;
        for(var k=0;k<account.recent.length;k++){
            var entry=account.recent[k];
            if(!entry||entry.accountId!==account.id
                ||typeof entry.date!=="string"
                ||typeof entry.description!=="string"
                ||!Number.isSafeInteger(entry.amountCents))
                return {ok:false,error:"INVALID ACTIVITY SNAPSHOT"};
            activity.push({id:entry.id,accountId:account.id,
                accountNickname:account.nickname,date:entry.date,
                description:entry.description,amountCents:entry.amountCents});
        }
    }
    activity.sort(compareSessionActivity);
    var listed=selected.kind==="product"
        ?accounts.filter(function(a){return a.productId===selected.productId;})
        :(selected.kind==="accounts"?accounts:[]);
    // M4c: show per-provider cash movement without treating a transfer as income
    // or a debit as an expense. Totals include the whole current M3 session;
    // the displayed recent list is deliberately a small, partial preview.
    var viewIn=0,viewOut=0,viewCount=0,preview=[],older=false;
    var viewKnown=0,viewUnknown=0,viewSubtotal=0;
    for(var n=0;n<listed.length;n++){
        var selectedAccount=listed[n];
        if(selectedAccount.balanceCents===null)viewUnknown++;
        else {viewKnown++;viewSubtotal+=selectedAccount.balanceCents;}
        viewIn+=selectedAccount.creditsCents;
        viewOut+=selectedAccount.debitsCents;
        viewCount+=selectedAccount.transactionCount;
        if(selectedAccount.transactionCount>selectedAccount.recent.length)
            older=true;
        for(var m=0;m<selectedAccount.recent.length;m++){
            var item=selectedAccount.recent[m];
            preview.push({id:item.id,accountId:selectedAccount.id,
                nickname:selectedAccount.nickname,date:item.date,
                description:item.description,amountCents:item.amountCents});
        }
    }
    if(!Number.isSafeInteger(viewIn)||!Number.isSafeInteger(viewOut)
       ||!Number.isSafeInteger(viewCount)||!Number.isSafeInteger(viewSubtotal))
        return {ok:false,error:"INVALID SESSION MOVEMENT TOTAL"};
    preview.sort(compareSessionActivity);
    var mode=snapshot.mode==="demo"?"FICTIONAL DEMO"
         :snapshot.mode==="manual"?"MANUAL SESSION":"NO MANUAL ACCOUNTS";
    var access=selected.kind==="restricted"?"PROVIDER AUTHORIZATION REQUIRED"
               :snapshot.mode==="demo"?"FICTIONAL DEMO DATA ONLY"
                :"LOCAL MANUAL DATA ONLY";
    return {ok:true,providerId:provider.id,providerName:provider.name,
        sectionId:selected.id,sectionLabel:selected.label,sectionKind:selected.kind,
        sectionSummary:selected.summary,accessLabel:access,dataLabel:mode,
        features:provider.features.map(function(f){return {id:f.id,label:f.label,
            kind:f.kind};}),accountCount:accounts.length,knownCount:known,
        unknownCount:unknown,knownSubtotalCents:subtotal,
        totalCents:accounts.length>0&&unknown===0?subtotal:null,
        transactionCount:txCount,visibleAccounts:listed,allAccounts:accounts,
        visibleKnownBalanceCount:viewKnown,visibleUnknownBalanceCount:viewUnknown,
        visibleKnownBalanceSubtotalCents:viewSubtotal,
        visibleBalanceCents:listed.length>0&&viewUnknown===0?viewSubtotal:null,
        visibleMovementInCents:viewIn,visibleMovementOutCents:viewOut,
        visibleMovementNetCents:viewIn-viewOut,visibleTransactionCount:viewCount,
        visibleRecent:preview.slice(0,4),
        visibleRecentOmitted:older||preview.length>4,
        activity: selected.kind==="activity"?activity.slice(0,24):[],
        activitySourceCount:activity.length,
        connected:false,persisted:false,canTransfer:false,
        canTrade:false,canBorrow:false,canManageCard:false};
}

 
// Filtering is deliberately limited to the bounded recent-session projection
// (at most 12 entries per account, then 24 provider entries), never full history.
function filterRecentActivity(projection,options) {
    if(!projection||projection.ok!==true||projection.sectionKind!=="activity"
       ||projection.connected!==false||projection.persisted!==false
       ||!Array.isArray(projection.activity)||!Array.isArray(projection.allAccounts))
        return {ok:false,error:"ACTIVITY SECTION REQUIRED"};
    var opts=options||{},direction=opts.direction||"all",
        accountId=opts.accountId||"",rawQuery=opts.query||"";
    if(["all","in","out"].indexOf(direction)<0||typeof accountId!=="string"
       ||typeof rawQuery!=="string"||rawQuery.length>64
       ||/[\u0000-\u001F\u007F]/.test(rawQuery))
        return {ok:false,error:"INVALID ACTIVITY FILTER"};
    if(accountId && !projection.allAccounts.some(function(a){return a.id===accountId;}))
        return {ok:false,error:"ACCOUNT IS NOT IN THIS PROVIDER"};
    var query=rawQuery.trim().toLowerCase();
    var rows=projection.activity.filter(function(entry){
        return (!accountId||entry.accountId===accountId)
            &&(direction==="all"
               ||(direction==="in"&&entry.amountCents>0)
               ||(direction==="out"&&entry.amountCents<0))
            &&(!query||entry.description.toLowerCase().indexOf(query)>=0
               ||entry.accountNickname.toLowerCase().indexOf(query)>=0);
    });
    return {ok:true,rows:rows,shownCount:rows.length,
        recentWindowCount:projection.activity.length,
        hasOlderEntries:projection.transactionCount>projection.activity.length,
        filterDirection:direction,filterAccountId:accountId};
}
