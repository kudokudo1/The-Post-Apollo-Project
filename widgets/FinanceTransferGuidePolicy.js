// FinanceW TG0: fictional, offline transfer guidance only. No provider API or bank permissions.
var DEMO_ACCOUNTS = [
    {id:"cashapp-demo",provider:"cashapp",name:"Cash App",fictional:true},
    {id:"chime-demo",provider:"chime",name:"Chime",fictional:true},
    {id:"paypal-demo",provider:"paypal",name:"PayPal",fictional:true},
    {id:"bank-demo",provider:"bank",name:"External Bank",fictional:true}
];

function accounts() {
    return DEMO_ACCOUNTS.map(function(a) {
        return {id:a.id,provider:a.provider,name:a.name,fictional:true,
                connectionState:"NOT CONNECTED"};
    });
}

function amountCents(text) {
    var s=String(text===undefined||text===null?"":text).trim();
    if(!/^(?:0|[1-9][0-9]{0,4})(?:\.[0-9]{1,2})?$/.test(s))return null;
    var p=s.split(".");
    var n=Number(p[0])*100+Number((p[1]||"").padEnd(2,"0"));
    return Number.isSafeInteger(n)&&n>0?n:null;
}

function moneyText(cents) {
    return Number.isSafeInteger(cents)&&cents>=0?"$"+(cents/100).toFixed(2):"UNKNOWN";
}

function transferPlan(sourceId,destinationId,amountText) {
    var source=DEMO_ACCOUNTS.find(function(a){return a.id===sourceId;});
    var destination=DEMO_ACCOUNTS.find(function(a){return a.id===destinationId;});
    var cents=amountCents(amountText);
    if(!source||!destination)return {ok:false,error:"SELECT TWO KNOWN DEMO ACCOUNTS"};
    if(source.id===destination.id)return {ok:false,error:"SOURCE AND DESTINATION MUST DIFFER"};
    if(cents===null)return {ok:false,error:"ENTER A POSITIVE DOLLAR AMOUNT (MAX 99999.99)"};
    var action="Open the source provider and check its supported linked-account transfer method.";
    var intermediated=false;
    if(source.provider==="cashapp"&&destination.provider==="chime")
        action="In Cash App, use its withdrawal/transfer feature to a Chime account or debit card already linked to Cash App, if eligible.";
    else if(source.provider==="chime"&&destination.provider==="cashapp")
        action="In Cash App, use Add Money from an eligible linked Chime debit card or bank account. Check the source before confirming.";
    else if(source.provider==="paypal"&&destination.provider==="chime")
        action="In PayPal, choose a transfer out to a linked eligible Chime bank account or debit card.";
    else if(source.provider==="chime"&&destination.provider==="paypal")
        action="In PayPal, check whether Add Money is available from a linked Chime bank account. If not, use a supported alternate route.";
    else if((source.provider==="cashapp"&&destination.provider==="paypal")||
            (source.provider==="paypal"&&destination.provider==="cashapp")) {
        action="No direct Cash App/PayPal account-to-account route is verified here. Consider a supported linked bank intermediary, treating each leg as a separate transfer.";
        intermediated=true;
    } else if(source.provider==="chime")
        action="In Chime, use Move > Transfer Money to an eligible linked external account, verifying the destination and method.";
    else if(destination.provider==="chime")
        action="Use the originating bank's external-transfer flow, or check Chime > Move > Transfer Money for a supported linked account.";
    else if(source.provider==="paypal")
        action="In PayPal, use Transfer Money to an eligible linked bank/card. Confirm the receiving account.";
    else if(source.provider==="cashapp")
        action="In Cash App, use the withdrawal/transfer option to a linked eligible bank account or debit card.";
    else if(destination.provider==="cashapp")
        action="In Cash App, use Add Money from an eligible linked external account or debit card.";
    else if(destination.provider==="paypal")
        action="In PayPal, check Add Money for an eligible linked bank. If unavailable, use a supported alternative.";
    return {
        ok:true,mode:"GUIDANCE ONLY",sourceName:source.name,
        destinationName:destination.name,amountCents:cents,amountText:moneyText(cents),
        intermediated:intermediated,connected:false,moneyMoved:false,
        providerConfirmed:false,fee:"CHECK IN PROVIDER",arrival:"CHECK IN PROVIDER",
        steps:[
            "Use only the account owner's official app or website. Never share passwords or one-time codes.",
            action,
            "Review destination, fees, limits and arrival estimate shown by the provider before authorization.",
            "Complete any transfer inside the official provider app. This guide never submits a payment.",
            "Check both account histories. Do not call a transfer complete until the provider confirms it."
        ]
    };
}

function demoActivity() {
    return [
        {id:"demo-1",account:"chime-demo",kind:"transfer_out",transferId:"demo-internal-1",amountCents:-7500},
        {id:"demo-2",account:"cashapp-demo",kind:"transfer_in",transferId:"demo-internal-1",amountCents:7500},
        {id:"demo-3",account:"cashapp-demo",kind:"expense",category:"Food",amountCents:-2500},
        {id:"demo-4",account:"chime-demo",kind:"expense",category:"Housing",amountCents:-75000},
        {id:"demo-5",account:"paypal-demo",kind:"expense",category:"Shopping",amountCents:-1999}
    ];
}

function spendingSummary(rows) {
    if(!Array.isArray(rows))return {ok:false,error:"INVALID TRANSACTION LIST"};
    var seen={},transfers={},expenses=0;
    for(var i=0;i<rows.length;++i) {
        var r=rows[i];
        if(!r||typeof r.id!=="string"||!r.id||seen[r.id]||
           !Number.isSafeInteger(r.amountCents)||r.amountCents===0)
            return {ok:false,error:"INVALID OR DUPLICATE TRANSACTION"};
        seen[r.id]=true;
        if(r.kind==="expense") {
            if(r.amountCents>=0)return {ok:false,error:"EXPENSE SIGN ERROR"};
            expenses+=-r.amountCents;
            if(!Number.isSafeInteger(expenses))return {ok:false,error:"AMOUNT OVERFLOW"};
        } else if(r.kind==="transfer_in"||r.kind==="transfer_out") {
            if(!r.transferId||typeof r.account!=="string"||
               (r.kind==="transfer_in"&&r.amountCents<=0)||
               (r.kind==="transfer_out"&&r.amountCents>=0))
                return {ok:false,error:"TRANSFER DETAILS INVALID"};
            if(!transfers[r.transferId])transfers[r.transferId]=[];
            transfers[r.transferId].push(r);
        } else return {ok:false,error:"UNKNOWN TRANSACTION KIND"};
    }
    var matched=0,review=0;
    Object.keys(transfers).forEach(function(key) {
        var t=transfers[key];
        if(t.length===2&&t[0].account!==t[1].account&&
           t[0].amountCents+t[1].amountCents===0&&t[0].kind!==t[1].kind)
            matched+=1;
        else review+=1;
    });
    return {ok:true,mode:"FICTIONAL DEMO",expensesCents:expenses,
            matchedInternalTransferPairs:matched,unmatchedTransferGroups:review,
            moneyMoved:false,connected:false};
}
