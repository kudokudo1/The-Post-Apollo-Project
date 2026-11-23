import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

function policy(file) {
    const ctx=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+file,import.meta.url),"utf8"),ctx);
    return ctx;
}
const Accounts=policy("FinanceBankingAccountsPolicy.js");
const Provider=policy("FinanceBankingProviderPolicy.js");
let state=Accounts.emptyState();
function add(providerId,productId,nickname,openingText) {
    const result=Accounts.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(result.ok,true,result.error);
    state=result.state;
    return result.account.id;
}
function entry(accountId,date,description,direction,amountText) {
    const result=Accounts.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(result.ok,true,result.error);
    state=result.state;
}
const chChecking=add("chime","chime-checking","My Checking","100.00");
const chSavings=add("chime","chime-savings","My Savings","");
const ca=add("cashapp","cash-balance","CA Main","125.00");
const pp=add("paypal","paypal-wallet","My PayPal","55.00");
entry(chChecking,"2026-11-19","manual grocery","out","11.25");
entry(chChecking,"2026-11-20","manual deposit","in","200.00");
entry(chChecking,"2026-11-21","manual transfer out","out","50.00");
entry(chSavings,"2026-11-21","manual transfer in","in","50.00");
entry(ca,"2026-11-21","fictional-looking manual debit","out","3.00");
entry(pp,"2026-11-22","provider isolation","in","25.00");
let snapshot=Accounts.snapshot(state);
assert.equal(snapshot.ok,true);

const chHome=Provider.build("chime",snapshot,"home");
assert.equal(chHome.ok,true);
assert.equal(chHome.visibleAccounts.length,2);
assert.equal(chHome.visibleTransactionCount,4);
assert.equal(chHome.visibleMovementInCents,25000);
assert.equal(chHome.visibleMovementOutCents,6125);
assert.equal(chHome.visibleMovementNetCents,18875);
assert.equal(chHome.visibleRecent.length,4);
assert.equal(chHome.visibleRecentOmitted,false);
assert.equal(chHome.totalCents,null,"Unknown savings balance must remain unknown");
assert.equal(chHome.unknownCount,1);
assert.equal(chHome.connected,false);
assert.equal(chHome.persisted,false);
assert.equal(chHome.canTransfer,false);
assert.equal(chHome.canTrade,false);
assert.equal(chHome.canBorrow,false);
assert.equal(chHome.canManageCard,false);
assert.equal(chHome.visibleRecent.every(x=>[chChecking,chSavings].includes(x.accountId)),true);
assert.equal(chHome.visibleRecent.some(x=>x.accountId===ca || x.accountId===pp),false);
assert.equal(chHome.visibleRecent[0].description,"manual transfer in");
assert.equal(chHome.visibleRecent[1].description,"manual transfer out");

const checking=Provider.build("chime",snapshot,"checking");
assert.equal(checking.ok,true);
assert.equal(checking.visibleAccounts.length,1);
assert.equal(checking.visibleAccounts[0].id,chChecking);
assert.equal(checking.visibleTransactionCount,3);
assert.equal(checking.visibleMovementInCents,20000);
assert.equal(checking.visibleMovementOutCents,6125);
assert.equal(checking.visibleMovementNetCents,13875);
assert.equal(checking.visibleKnownBalanceSubtotalCents,23875);
assert.equal(checking.visibleBalanceCents,23875);
assert.equal(checking.visibleUnknownBalanceCount,0);
assert.equal(checking.visibleRecent.length,3);
assert.equal(checking.visibleRecent.every(x=>x.accountId===chChecking),true);
assert.equal(checking.totalCents,null,"Whole provider unknown, even when one checking account is known");

const savings=Provider.build("chime",snapshot,"savings");
assert.equal(savings.visibleAccounts.length,1);
assert.equal(savings.visibleAccounts[0].id,chSavings);
assert.equal(savings.visibleMovementInCents,5000);
assert.equal(savings.visibleMovementOutCents,0);
assert.equal(savings.visibleTransactionCount,1);
assert.equal(savings.visibleBalanceCents,null);
assert.equal(savings.visibleUnknownBalanceCount,1);
assert.equal(savings.visibleRecent[0].description,"manual transfer in");

const caHome=Provider.build("cashapp",snapshot,"home");
assert.equal(caHome.visibleMovementInCents,0);
assert.equal(caHome.visibleMovementOutCents,300);
assert.equal(caHome.visibleRecent.length,1);
assert.equal(caHome.visibleRecent[0].accountId,ca);
assert.equal(Provider.build("cashapp",snapshot,"stocks").visibleAccounts.length,0);
assert.equal(Provider.build("cashapp",snapshot,"stocks").visibleRecent.length,0);
assert.equal(Provider.build("cashapp",snapshot,"stocks").visibleMovementInCents,0);
assert.equal(Provider.build("cashapp",snapshot,"stocks").accessLabel,"PROVIDER AUTHORIZATION REQUIRED");

const payWallet=Provider.build("paypal",snapshot,"wallet");
assert.equal(payWallet.visibleMovementInCents,2500);
assert.equal(payWallet.visibleMovementOutCents,0);
assert.equal(payWallet.visibleTransactionCount,1);
assert.equal(payWallet.visibleRecent[0].accountId,pp);
assert.equal(payWallet.totalCents,8000);
assert.equal(payWallet.visibleBalanceCents,8000);

const bank=Provider.build("bank",snapshot,"home");
assert.equal(bank.visibleAccounts.length,0);
assert.equal(bank.visibleRecent.length,0);
assert.equal(bank.visibleTransactionCount,0);
assert.equal(bank.visibleMovementInCents,0);
assert.equal(bank.totalCents,null);

const activity=Provider.build("chime",snapshot,"activity");
assert.equal(activity.visibleMovementInCents,0);
assert.equal(activity.visibleMovementOutCents,0);
assert.equal(activity.visibleRecent.length,0);
assert.equal(Provider.filterRecentActivity(activity,{direction:"out"}).shownCount,2);

const original=JSON.stringify(snapshot);
Provider.build("chime",snapshot,"home");
assert.equal(JSON.stringify(snapshot),original,"Must not mutate M3 source");
const tampered={...snapshot,accounts:snapshot.accounts.map(a=>a.id===chChecking
    ? {...a,creditsCents:Infinity}:a)};
assert.equal(Provider.build("chime",tampered,"home").ok,false);
const inconsistent={...snapshot,accounts:snapshot.accounts.map(a=>a.id===chChecking
    ? {...a,netChangeCents:999}:a)};
assert.equal(Provider.build("chime",inconsistent,"home").ok,false);
const badDebits={...snapshot,accounts:snapshot.accounts.map(a=>a.id===chChecking
    ? {...a,debitsCents:-10}:a)};
assert.equal(Provider.build("chime",badDebits,"home").ok,false);

// The preview is a recent window, not an entire statement or full ledger.
let many=Accounts.emptyState();
let a=Accounts.addAccount(many,{providerId:"cashapp",productId:"cash-balance",
    nickname:"Long",openingText:"200.00"});
assert.equal(a.ok,true);many=a.state;
for(let i=0;i<20;i++){
    let res=Accounts.addEntry(many,{accountId:a.account.id,date:"2026-11-22",
        description:"manual "+i,direction:"out",amountText:"1.00"});
    assert.equal(res.ok,true,res.error);many=res.state;
}
const long=Provider.build("cashapp",Accounts.snapshot(many),"home");
assert.equal(long.visibleTransactionCount,20);
assert.equal(long.visibleMovementOutCents,2000);
assert.equal(long.visibleRecent.length,4);
assert.equal(long.visibleRecentOmitted,true);
assert.equal(long.visibleRecent.some(x=>x.description==="manual 0"),false);
assert.equal(long.visibleRecent.some(x=>x.description==="manual 19"),true);
assert.equal(long.visibleRecent[0].description,"manual 19");
// Entry IDs cross one-digit to two-digit sequence numbers. Same-date
// activity must follow numeric insertion order, not string sorting.
let short=Accounts.emptyState();
const qa=Accounts.addAccount(short,{providerId:"paypal",productId:"paypal-wallet",
    nickname:"Same day",openingText:"50.00"});
assert.equal(qa.ok,true);short=qa.state;
for(let i=0;i<10;i++){
    const res=Accounts.addEntry(short,{accountId:qa.account.id,date:"2026-11-22",
        description:"item "+i,direction:"out",amountText:"1.00"});
    assert.equal(res.ok,true);short=res.state;
}
const newest=Provider.build("paypal",Accounts.snapshot(short),"home");
assert.equal(newest.visibleRecent[0].description,"item 9");
assert.equal(newest.visibleRecent[1].description,"item 8");
const act=Provider.build("paypal",Accounts.snapshot(short),"activity");
assert.equal(act.activity[0].description,"item 9");
const demo=Accounts.sampleDemo();
assert.equal(demo.ok,true);
const d=Provider.build("chime",Accounts.snapshot(demo.state),"home");
assert.equal(d.dataLabel,"FICTIONAL DEMO");
assert.equal(d.visibleTransactionCount,1);
assert.equal(d.visibleMovementOutCents,2645);
assert.equal(d.visibleMovementInCents,0);
assert.equal(d.connected,false);
console.log("Banking M4c: provider/product cash movement, unknown totals, bounded previews, demo and source isolation PASS");
