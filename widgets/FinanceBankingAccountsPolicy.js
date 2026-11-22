// FinanceW Banking M3 // One-person, explicitly manual or fictional session.
// No saved balances, provider calls, bank sync, transfers, profile impersonation or Actual writes.
// Product identities are CASH-LIKE only: cards, stocks and borrowing are not cash subaccounts.
var MAX_ACCOUNTS = 12;
var MAX_ENTRIES = 300;
var MAX_CENTS = 999999999;

var PROVIDERS = [
    {id:"cashapp",name:"Cash App",products:[{id:"cash-balance",name:"Cash App balance"}]},
    {id:"chime",name:"Chime",products:[{id:"chime-checking",name:"Checking"},{id:"chime-savings",name:"Savings"}]},
    {id:"paypal",name:"PayPal",products:[{id:"paypal-wallet",name:"PayPal balance"}]},
    {id:"bank",name:"Other Bank",products:[{id:"bank-checking",name:"Checking"},{id:"bank-savings",name:"Savings"}]}
];
function providers() {
    return PROVIDERS.map(function(p){return {id:p.id,name:p.name,
        products:p.products.map(function(a){return {id:a.id,name:a.name};})};});
}
function findProvider(id) {
    return PROVIDERS.find(function(p){return p.id===id;}) || null;
}
function findProduct(providerId,productId) {
    var provider=findProvider(providerId);
    return provider ? provider.products.find(function(p){return p.id===productId;})||null : null;
}
function emptyState() {
    return {mode:"empty",accounts:[],entries:[],nextId:1};
}
function money(cents) {
    if(!Number.isSafeInteger(cents))return "UNKNOWN";
    return (cents<0?"-$":"$")+(Math.abs(cents)/100).toFixed(2);
}
function parseCents(input,allowNegative) {
    if(typeof input!=="string")return null;
    var text=input.trim(),pattern=allowNegative
        ? /^(-?)(0|[1-9][0-9]{0,6})(?:\.([0-9]{1,2}))?$/
        : /^()(0|[1-9][0-9]{0,6})(?:\.([0-9]{1,2}))?$/;
    var m=pattern.exec(text);
    if(!m)return null;
    var cents=Number(m[2])*100+Number((m[3]||"").padEnd(2,"0"));
    if(!Number.isSafeInteger(cents)||cents>MAX_CENTS)return null;
    return m[1]==="-"?-cents:cents;
}
function dateValid(text) {
    if(typeof text!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(text))return false;
    var parts=text.split("-").map(Number),d=new Date(Date.UTC(parts[0],parts[1]-1,parts[2]));
    return parts[0]>=1900&&parts[0]<=2100
        &&d.getUTCFullYear()===parts[0]
        &&d.getUTCMonth()===parts[1]-1
        &&d.getUTCDate()===parts[2];
}
function safeText(input,maxLength) {
    if(typeof input!=="string")return "";
    var text=input.trim();
    if(!text||text.length>maxLength||/[\u0000-\u001F\u007F]/.test(text))
        return "";
    return text;
}
function validState(state) {
    if(!state||!["empty","manual","demo"].includes(state.mode)
       ||!Array.isArray(state.accounts)||!Array.isArray(state.entries)
       ||state.accounts.length>MAX_ACCOUNTS||state.entries.length>MAX_ENTRIES
       ||!Number.isSafeInteger(state.nextId)||state.nextId<1||state.nextId>1000000)
        return false;
    if(state.mode==="empty"&&(state.accounts.length!==0||state.entries.length!==0))
        return false;
    if(state.mode!=="empty"&&state.accounts.length===0)return false;
    var ids={},names={},entryIds={};
    for(var i=0;i<state.accounts.length;i++) {
        var a=state.accounts[i];
        if(!a||typeof a.id!=="string"||!/^(acct|demo)-[1-9]\d*$/.test(a.id)
           ||ids[a.id]||!findProduct(a.providerId,a.productId)
           ||!safeText(a.nickname,42)
           ||!(a.openingCents===null||(Number.isSafeInteger(a.openingCents)
                   &&Math.abs(a.openingCents)<=MAX_CENTS))
           ||a.origin!==state.mode)
            return false;
        ids[a.id]=a;
        var key=a.providerId+"|"+a.nickname.toLowerCase();
        if(names[key])return false;
        names[key]=true;
    }
    var sums={};
    for(var j=0;j<state.entries.length;j++) {
        var e=state.entries[j];
        if(!e||typeof e.id!=="string"||!/^(entry|demo-entry)-[1-9]\d*$/.test(e.id)
           ||entryIds[e.id]||!ids[e.accountId]||!dateValid(e.date)
           ||!safeText(e.description,120)
           ||!Number.isSafeInteger(e.amountCents)||e.amountCents===0
           ||Math.abs(e.amountCents)>MAX_CENTS||e.origin!==state.mode)
            return false;
        entryIds[e.id]=true;
        sums[e.accountId]=(sums[e.accountId]||0)+e.amountCents;
        if(!Number.isSafeInteger(sums[e.accountId])
           ||Math.abs(sums[e.accountId])>MAX_CENTS)return false;
    }
    for(var id in ids) {
        var a=ids[id];
        if(a.openingCents!==null&&Math.abs(a.openingCents+(sums[id]||0))>MAX_CENTS)
            return false;
    }
    return true;
}
function resultError(text) {return {ok:false,error:text};}
function addAccount(state,fields) {
    if(!validState(state))return resultError("INVALID SESSION STATE");
    if(state.mode==="demo")return resultError("CLEAR FICTIONAL DEMO BEFORE MANUAL ENTRY");
    if(state.accounts.length>=MAX_ACCOUNTS)return resultError("ACCOUNT LIMIT: 12");
    var provider=findProvider(fields&&fields.providerId),
        product=findProduct(fields&&fields.providerId,fields&&fields.productId),
        nickname=safeText(fields&&fields.nickname,42);
    if(!provider||!product)return resultError("SELECT A SUPPORTED CASH ACCOUNT TYPE");
    if(!nickname)return resultError("ACCOUNT NICKNAME REQUIRED (MAX 42 CHARACTERS)");
    if(state.accounts.some(function(a){return a.providerId===provider.id
                       &&a.nickname.toLowerCase()===nickname.toLowerCase();}))
        return resultError("NICKNAME ALREADY USED FOR THIS PROVIDER");
    var opening=null,raw=fields.openingText;
    if(typeof raw!=="string")return resultError("OPENING BALANCE FORMAT INVALID");
    if(raw.trim()!=="") {
        opening=parseCents(raw,true);
        if(opening===null)return resultError("OPENING BALANCE FORMAT INVALID");
    }
    var account={id:"acct-"+state.nextId,providerId:provider.id,productId:product.id,
        nickname:nickname,openingCents:opening,origin:"manual"};
    var updated={mode:"manual",accounts:state.accounts.concat([account]),
        entries:state.entries.slice(),nextId:state.nextId+1};
    return validState(updated)?{ok:true,state:updated,account:account}
        :resultError("ACCOUNT NOT ADDED // INVALID RESULT");
}
function removeEmptyAccount(state,accountId) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("MANUAL ACCOUNT REQUIRED");
    if(state.entries.some(function(e){return e.accountId===accountId;}))
        return resultError("ACCOUNT HAS TRANSACTIONS // CANNOT DELETE");
    if(!state.accounts.some(function(a){return a.id===accountId;}))
        return resultError("ACCOUNT NOT FOUND");
    var accounts=state.accounts.filter(function(a){return a.id!==accountId;});
    var updated={mode:accounts.length?"manual":"empty",accounts:accounts,
        entries:state.entries.slice(),nextId:state.nextId};
    return {ok:true,state:updated};
}
function addEntry(state,fields) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("MANUAL ACCOUNT REQUIRED");
    if(state.entries.length>=MAX_ENTRIES)return resultError("SESSION LIMIT: 300 TRANSACTIONS");
    if(!fields||!state.accounts.some(function(a){return a.id===fields.accountId;}))
        return resultError("SELECT AN EXISTING ACCOUNT");
    if(!dateValid(fields.date))return resultError("DATE MUST BE YYYY-MM-DD");
    var description=safeText(fields.description,120);
    if(!description)return resultError("DESCRIPTION REQUIRED (MAX 120 CHARACTERS)");
    if(fields.direction!=="out"&&fields.direction!=="in")
        return resultError("SELECT MONEY OUT OR MONEY IN");
    var cents=parseCents(fields.amountText,false);
    if(cents===null||cents===0)return resultError("ENTER A POSITIVE AMOUNT");
    var entry={id:"entry-"+state.nextId,accountId:fields.accountId,date:fields.date,
        description:description,amountCents:fields.direction==="out"?-cents:cents,origin:"manual"};
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:state.entries.concat([entry]),nextId:state.nextId+1};
    return validState(updated)?{ok:true,state:updated,entry:entry}
        :resultError("TRANSACTION EXCEEDS SESSION BALANCE/AMOUNT LIMIT");
}
function undoLastEntry(state) {
    if(!validState(state)||state.mode!=="manual"||state.entries.length===0)
        return resultError("NO MANUAL TRANSACTION TO UNDO");
    var removed=state.entries[state.entries.length-1];
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:state.entries.slice(0,-1),nextId:state.nextId};
    return {ok:true,state:updated,undone:removed};
}
function sampleDemo() {
    var state={mode:"demo",nextId:20,accounts:[
        {id:"demo-1",providerId:"cashapp",productId:"cash-balance",
         nickname:"Example Cash App",openingCents:12500,origin:"demo"},
        {id:"demo-2",providerId:"chime",productId:"chime-checking",
         nickname:"Example Checking",openingCents:84000,origin:"demo"},
        {id:"demo-3",providerId:"paypal",productId:"paypal-wallet",
         nickname:"Example PayPal",openingCents:3000,origin:"demo"}
    ],entries:[
        {id:"demo-entry-4",accountId:"demo-2",date:"2026-11-19",
         description:"FICTIONAL grocery purchase",amountCents:-2645,origin:"demo"},
        {id:"demo-entry-5",accountId:"demo-1",date:"2026-11-20",
         description:"FICTIONAL received payment",amountCents:5200,origin:"demo"}
    ]};
    return validState(state)?{ok:true,state:state}:resultError("INVALID DEMO FIXTURE");
}
function snapshot(state) {
    if(!validState(state))return resultError("INVALID SESSION STATE");
    var rows=[],total=0,known=0,unknown=0,debits=0,credits=0;
    for(var i=0;i<state.accounts.length;i++) {
        var account=state.accounts[i],provider=findProvider(account.providerId),
            product=findProduct(account.providerId,account.productId),
            net=0,outs=0,ins=0,activity=[];
        for(var j=0;j<state.entries.length;j++) {
            var e=state.entries[j];
            if(e.accountId!==account.id)continue;
            net+=e.amountCents;
            if(e.amountCents<0)outs+=-e.amountCents;
            else ins+=e.amountCents;
            activity.push(e);
        }
        var balance=account.openingCents===null?null:account.openingCents+net;
        if(balance!==null){known++;total+=balance;}else unknown++;
        debits+=outs;credits+=ins;
        rows.push({id:account.id,providerId:account.providerId,
            providerName:provider.name,productId:account.productId,
            productName:product.name,nickname:account.nickname,
            origin:account.origin,openingCents:account.openingCents,
            balanceCents:balance,netChangeCents:net,debitsCents:outs,
            creditsCents:ins,transactionCount:activity.length,
            recent:activity.slice(-12).reverse()});
    }
    // Each account is bounded separately; the aggregate may legitimately
    // exceed the per-account ceiling when several accounts are listed.
    if(!Number.isSafeInteger(total)||!Number.isSafeInteger(debits)
       ||!Number.isSafeInteger(credits))
        return resultError("SESSION AMOUNT LIMIT REACHED");
    return {ok:true,mode:state.mode,accounts:rows,accountCount:rows.length,
        transactionCount:state.entries.length,knownBalanceCount:known,
        unknownBalanceCount:unknown,knownBalanceSubtotalCents:total,
        combinedBalanceCents:unknown===0&&rows.length>0?total:null,
        outCents:debits,inCents:credits,connected:false,persisted:false,
        demo:state.mode==="demo"};
}
