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
    var sums={},transfers=Object.create(null);
    for(var j=0;j<state.entries.length;j++) {
        var e=state.entries[j];
        if(!e||typeof e.id!=="string"||!/^(entry|demo-entry)-[1-9]\d*$/.test(e.id)
           ||entryIds[e.id]||!ids[e.accountId]||!dateValid(e.date)
           ||!safeText(e.description,120)
           ||!Number.isSafeInteger(e.amountCents)||e.amountCents===0
           ||Math.abs(e.amountCents)>MAX_CENTS||e.origin!==state.mode)
            return false;
        entryIds[e.id]=true;
        if(e.transferId!==undefined||e.transferSide!==undefined) {
            if(state.mode!=="manual"||typeof e.transferId!=="string"
               ||!/^transfer-[1-9]\d*$/.test(e.transferId)
               ||(e.transferSide!=="out"&&e.transferSide!=="in")
               ||(e.transferSide==="out"&&e.amountCents>=0)
               ||(e.transferSide==="in"&&e.amountCents<=0))
                return false;
            if(!transfers[e.transferId])transfers[e.transferId]={out:null,in:null};
            if(transfers[e.transferId][e.transferSide])return false;
            transfers[e.transferId][e.transferSide]=e;
        }
        sums[e.accountId]=(sums[e.accountId]||0)+e.amountCents;
        if(!Number.isSafeInteger(sums[e.accountId])
           ||Math.abs(sums[e.accountId])>MAX_CENTS)return false;
    }
    for(var transferId in transfers) {
        var pair=transfers[transferId];
        if(!pair.in||!pair.out
           ||pair.in.accountId===pair.out.accountId
           ||pair.in.date!==pair.out.date
           ||pair.in.description!==pair.out.description
           ||pair.in.amountCents!==-pair.out.amountCents)
            return false;
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
// M4l // Correct only a user's current manual-session account label and
// estimated opening amount. Account identity, provider/product type, linked
// transfer endpoints, transactions and monotonically increasing IDs never move.
// Blank opening is UNKNOWN, not zero. No bank statements are updated.
function correctAccountDetails(state,fields) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("MANUAL ACCOUNT SESSION REQUIRED");
    if(!fields||typeof fields.accountId!=="string")
        return resultError("SELECT AN EXISTING MANUAL ACCOUNT");
    var original=state.accounts.find(function(a){return a.id===fields.accountId;});
    if(!original||original.origin!=="manual")
        return resultError("MANUAL ACCOUNT NOT FOUND");
    if(original.providerId!==fields.expectedProviderId
       ||original.productId!==fields.expectedProductId
       ||original.nickname!==fields.expectedNickname
       ||original.openingCents!==fields.expectedOpeningCents)
        return resultError("STALE MANUAL ACCOUNT // RESELECT BEFORE CORRECTION");
    var nickname=safeText(fields.nickname,42);
    if(!nickname)return resultError("ACCOUNT NICKNAME REQUIRED (MAX 42 CHARACTERS)");
    if(state.accounts.some(function(a){return a.id!==original.id
           &&a.providerId===original.providerId
           &&a.nickname.toLowerCase()===nickname.toLowerCase();}))
        return resultError("NICKNAME ALREADY USED FOR THIS PROVIDER");
    if(typeof fields.openingText!=="string")
        return resultError("OPENING BALANCE FORMAT INVALID");
    var opening=null;
    if(fields.openingText.trim()!=="") {
        opening=parseCents(fields.openingText,true);
        if(opening===null)
            return resultError("OPENING BALANCE FORMAT INVALID");
    }
    var changed={id:original.id,providerId:original.providerId,
        productId:original.productId,nickname:nickname,
        openingCents:opening,origin:"manual"};
    var accounts=state.accounts.map(function(a){
        return a.id===original.id?changed:a;
    });
    var updated={mode:"manual",accounts:accounts,
        entries:state.entries.slice(),nextId:state.nextId};
    return validState(updated)?{ok:true,state:updated,account:changed}
        :resultError("CORRECTION EXCEEDS ACCOUNT BALANCE/AMOUNT LIMIT");
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
// M4i // A transfer here only records TWO USER-DECLARED SESSION ENTRIES.
// Never connect to a provider, send money, import statements, or classify
// either side as verified income/spending. Pair invariants are in validState().
function addManualTransfer(state,fields) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("TWO MANUAL ACCOUNTS REQUIRED");
    if(!fields||typeof fields.fromAccountId!=="string"
       ||typeof fields.toAccountId!=="string"
       ||fields.fromAccountId===fields.toAccountId)
        return resultError("SELECT TWO DIFFERENT MANUAL ACCOUNTS");
    if(state.entries.length>MAX_ENTRIES-2||state.nextId>999997)
        return resultError("TWO FREE SESSION ENTRY SLOTS REQUIRED");
    var from=state.accounts.find(function(a){return a.id===fields.fromAccountId;});
    var to=state.accounts.find(function(a){return a.id===fields.toAccountId;});
    if(!from||!to||from.origin!=="manual"||to.origin!=="manual")
        return resultError("BOTH MANUAL ACCOUNTS MUST EXIST");
    if(!dateValid(fields.date))return resultError("DATE MUST BE YYYY-MM-DD");
    var cents=parseCents(fields.amountText,false);
    if(cents===null||cents===0)return resultError("ENTER A POSITIVE TRANSFER AMOUNT");
    var description=fields.description===""?"MANUAL TRANSFER"
        :safeText(fields.description,120);
    if(!description)return resultError("DESCRIPTION MAX 120 CHARACTERS");
    var pairId="transfer-"+state.nextId;
    var out={id:"entry-"+state.nextId,accountId:from.id,date:fields.date,
        description:description,amountCents:-cents,origin:"manual",
        transferId:pairId,transferSide:"out"};
    var incoming={id:"entry-"+(state.nextId+1),accountId:to.id,date:fields.date,
        description:description,amountCents:cents,origin:"manual",
        transferId:pairId,transferSide:"in"};
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:state.entries.concat([out,incoming]),nextId:state.nextId+2};
    return validState(updated)?{ok:true,state:updated,transfer:{
        transferId:pairId,fromAccountId:from.id,toAccountId:to.id,
        date:fields.date,amountCents:cents,description:description}}
        :resultError("MANUAL TRANSFER EXCEEDS SESSION AMOUNT LIMIT");
}
function transferPairs(state) {
    if(!validState(state))return resultError("INVALID SESSION STATE");
    var accounts=Object.create(null),pairs=Object.create(null),out=[];
    for(var a=0;a<state.accounts.length;a++)
        accounts[state.accounts[a].id]=state.accounts[a];
    for(var i=0;i<state.entries.length;i++) {
        var e=state.entries[i];
        if(!e.transferId)continue;
        if(!pairs[e.transferId])pairs[e.transferId]={};
        pairs[e.transferId][e.transferSide]=e;
    }
    for(var id in pairs) {
        var pair=pairs[id],from=accounts[pair.out.accountId],
            to=accounts[pair.in.accountId];
        out.push({transferId:id,fromAccountId:from.id,toAccountId:to.id,
            fromLabel:from.nickname,toLabel:to.nickname,
            fromProviderId:from.providerId,toProviderId:to.providerId,
            date:pair.out.date,description:pair.out.description,
            amountCents:pair.in.amountCents});
    }
    out.sort(function(a,b){
        return Number(b.transferId.slice(9))-Number(a.transferId.slice(9));
    });
    return {ok:true,rows:out,connected:false,persisted:false};
}
// M4j // Correct BOTH legs in one new session snapshot. A pair's original
// account endpoints, date, memo and amount are optimistic preconditions.
// Neither leg ID nor transfer identity can be replaced by this operation.
// A correction is a local bookkeeping amendment, never an actual payment.
function correctManualTransfer(state,fields) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("MANUAL TRANSFER SESSION REQUIRED");
    if(!fields||typeof fields.transferId!=="string"
       ||!/^transfer-[1-9]\d*$/.test(fields.transferId))
        return resultError("SELECT A VALID MANUAL TRANSFER PAIR");
    var list=transferPairs(state);
    if(!list.ok)return list;
    var selected=list.rows.find(function(p){return p.transferId===fields.transferId;});
    if(!selected)return resultError("MANUAL TRANSFER PAIR NOT FOUND");
    if(selected.fromAccountId!==fields.fromAccountId
       ||selected.toAccountId!==fields.toAccountId
       ||selected.date!==fields.expectedDate
       ||selected.description!==fields.expectedDescription
       ||selected.amountCents!==fields.expectedAmountCents)
        return resultError("STALE MANUAL TRANSFER // RESELECT BEFORE CORRECTION");
    if(!dateValid(fields.date))return resultError("DATE MUST BE YYYY-MM-DD");
    var cents=parseCents(fields.amountText,false);
    if(cents===null||cents===0)
        return resultError("ENTER A POSITIVE TRANSFER AMOUNT");
    var memo=fields.description===""?"MANUAL TRANSFER"
        :safeText(fields.description,120);
    if(!memo)return resultError("DESCRIPTION MAX 120 CHARACTERS");
    var changedCount=0,entries=state.entries.map(function(e) {
        if(e.transferId!==selected.transferId)return e;
        changedCount++;
        return {id:e.id,accountId:e.accountId,date:fields.date,
            description:memo,amountCents:e.transferSide==="out"?-cents:cents,
            origin:"manual",transferId:e.transferId,transferSide:e.transferSide};
    });
    if(changedCount!==2)return resultError("INCOMPLETE MANUAL TRANSFER PAIR");
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:entries,nextId:state.nextId};
    return validState(updated)?{ok:true,state:updated,corrected:{
        transferId:selected.transferId,fromAccountId:selected.fromAccountId,
        toAccountId:selected.toAccountId,date:fields.date,
        description:memo,amountCents:cents}}
        :resultError("CORRECTION EXCEEDS SESSION AMOUNT LIMIT");
}
function removeManualTransfer(state,fields) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("MANUAL TRANSFER SESSION REQUIRED");
    if(!fields||typeof fields.transferId!=="string"
       ||!/^transfer-[1-9]\d*$/.test(fields.transferId))
        return resultError("SELECT A VALID MANUAL TRANSFER PAIR");
    var rows=transferPairs(state);
    if(!rows.ok)return rows;
    var selected=rows.rows.find(function(p){return p.transferId===fields.transferId;});
    if(!selected)return resultError("MANUAL TRANSFER PAIR NOT FOUND");
    if(selected.fromAccountId!==fields.fromAccountId
       ||selected.toAccountId!==fields.toAccountId
       ||selected.date!==fields.date
       ||selected.description!==fields.description
       ||selected.amountCents!==fields.amountCents)
        return resultError("STALE MANUAL TRANSFER // RESELECT BEFORE REMOVING");
    var entries=state.entries.filter(function(e){
        return e.transferId!==selected.transferId;
    });
    if(entries.length!==state.entries.length-2)
        return resultError("INVALID MANUAL TRANSFER PAIR");
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:entries,nextId:state.nextId};
    return validState(updated)?{ok:true,state:updated,removed:selected}
        :resultError("MANUAL TRANSFER PAIR REMOVAL REFUSED");
}
function undoLastEntry(state) {
    if(!validState(state)||state.mode!=="manual"||state.entries.length===0)
        return resultError("NO MANUAL TRANSACTION TO UNDO");
    var removed=state.entries[state.entries.length-1];
    var entries=state.entries.slice(0,-1);
    if(removed.transferId) {
        // Do not permit a one-sided rollback or a partial transfer pair.
        var other=entries[entries.length-1];
        if(!other||other.transferId!==removed.transferId)
            return resultError("PAIRED TRANSFER // REMOVE BOTH FROM BANKING OVERVIEW");
        entries=entries.slice(0,-1);
    }
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:entries,nextId:state.nextId};
    return validState(updated)?{ok:true,state:updated,undone:removed}
        :resultError("LAST ENTRY UNDO WOULD BREAK A MANUAL TRANSFER PAIR");
}
// M4f // Correct user-entered entries without recycling IDs or changing
// account ownership. Original values are required as an optimistic concurrency
// check so a stale editor cannot silently replace another edit.
function matchManualEntry(state,fields) {
    if(!validState(state)||state.mode!=="manual")
        return resultError("MANUAL SESSION REQUIRED");
    if(!fields||typeof fields.entryId!=="string"
       ||typeof fields.accountId!=="string")
        return resultError("SELECT A MANUAL ENTRY");
    var index=state.entries.findIndex(function(e){return e.id===fields.entryId;});
    if(index<0)return resultError("MANUAL ENTRY NOT FOUND");
    var entry=state.entries[index];
    if(entry.origin!=="manual"||entry.accountId!==fields.accountId)
        return resultError("MANUAL ACCOUNT/ENTRY MISMATCH");
    if(entry.transferId)
        return resultError("PAIRED TRANSFER // REMOVE BOTH FROM BANKING OVERVIEW");
    if(entry.date!==fields.expectedDate
       ||entry.description!==fields.expectedDescription
       ||entry.amountCents!==fields.expectedAmountCents)
        return resultError("STALE MANUAL ENTRY // RESELECT BEFORE CHANGING");
    return {ok:true,index:index,entry:entry};
}
function correctEntry(state,fields) {
    var match=matchManualEntry(state,fields);
    if(!match.ok)return match;
    if(!dateValid(fields.date))return resultError("DATE MUST BE YYYY-MM-DD");
    var description=safeText(fields.description,120);
    if(!description)return resultError("DESCRIPTION REQUIRED (MAX 120 CHARACTERS)");
    if(fields.direction!=="in"&&fields.direction!=="out")
        return resultError("SELECT MONEY IN OR MONEY OUT");
    var cents=parseCents(fields.amountText,false);
    if(cents===null||cents===0)return resultError("ENTER A POSITIVE AMOUNT");
    var fixed={id:match.entry.id,accountId:match.entry.accountId,
        date:fields.date,description:description,
        amountCents:fields.direction==="out"?-cents:cents,origin:"manual"};
    var entries=state.entries.slice();
    entries[match.index]=fixed;
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:entries,nextId:state.nextId};
    return validState(updated)?{ok:true,state:updated,corrected:fixed}
        :resultError("CORRECTION EXCEEDS SESSION BALANCE/AMOUNT LIMIT");
}
function deleteEntry(state,fields) {
    var match=matchManualEntry(state,fields);
    if(!match.ok)return match;
    var entries=state.entries.slice();
    entries.splice(match.index,1);
    var updated={mode:"manual",accounts:state.accounts.slice(),
        entries:entries,nextId:state.nextId};
    return validState(updated)?{ok:true,state:updated,deleted:match.entry}
        :resultError("ENTRY COULD NOT BE REMOVED");
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
    // M4k // Separate declared linked transfers from unlinked session
    // movements. Both groups are manually supplied and never verified income.
    // This derives solely from validState's validated pair identities.
    var rows=[],total=0,known=0,unknown=0,debits=0,credits=0;
    var transferIds=Object.create(null),transferLegCount=0;
    var transferInCents=0,transferOutCents=0;
    var unlinkedCount=0,unlinkedInCents=0,unlinkedOutCents=0;
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
            if(e.transferId) {
                transferIds[e.transferId]=true;
                transferLegCount++;
                if(e.amountCents<0)transferOutCents+=-e.amountCents;
                else transferInCents+=e.amountCents;
            } else {
                unlinkedCount++;
                if(e.amountCents<0)unlinkedOutCents+=-e.amountCents;
                else unlinkedInCents+=e.amountCents;
            }
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
    var transferPairCount=Object.keys(transferIds).length;
    if(!Number.isSafeInteger(total)||!Number.isSafeInteger(debits)
       ||!Number.isSafeInteger(credits)
       ||!Number.isSafeInteger(transferInCents)
       ||!Number.isSafeInteger(transferOutCents)
       ||!Number.isSafeInteger(unlinkedInCents)
       ||!Number.isSafeInteger(unlinkedOutCents)
       ||transferLegCount!==transferPairCount*2
       ||transferInCents!==transferOutCents
       ||transferInCents+unlinkedInCents!==credits
       ||transferOutCents+unlinkedOutCents!==debits
       ||transferLegCount+unlinkedCount!==state.entries.length)
        return resultError("INCONSISTENT SESSION MOVEMENT RECONCILIATION");
    return {ok:true,mode:state.mode,accounts:rows,accountCount:rows.length,
        transactionCount:state.entries.length,knownBalanceCount:known,
        unknownBalanceCount:unknown,knownBalanceSubtotalCents:total,
        combinedBalanceCents:unknown===0&&rows.length>0?total:null,
        outCents:debits,inCents:credits,
        transferPairCount:transferPairCount,
        transferLegCount:transferLegCount,
        transferVolumeCents:transferInCents,
        transferInCents:transferInCents,
        transferOutCents:transferOutCents,
        transferNetCents:transferInCents-transferOutCents,
        unlinkedCount:unlinkedCount,
        unlinkedInCents:unlinkedInCents,
        unlinkedOutCents:unlinkedOutCents,
        unlinkedNetCents:unlinkedInCents-unlinkedOutCents,
        movementScope:"ALL CURRENT MANUAL/DEMO SESSION ACCOUNTS // NOT VERIFIED INCOME OR SPENDING",
        connected:false,persisted:false,
        demo:state.mode==="demo"};
}
