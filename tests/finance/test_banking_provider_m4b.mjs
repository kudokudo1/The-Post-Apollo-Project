import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

function readPolicy(path){
    const context=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+path,import.meta.url),"utf8"),context);
    return context;
}
const Accounts=readPolicy("FinanceBankingAccountsPolicy.js");
const Provider=readPolicy("FinanceBankingProviderPolicy.js");
let state=Accounts.emptyState();
function addAccount(providerId,productId,nickname,openingText){
    const r=Accounts.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);
    state=r.state;
    return r.account.id;
}
function addEntry(accountId,date,description,direction,amountText){
    const r=Accounts.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(r.ok,true,r.error);
    state=r.state;
}
const c1=addAccount("cashapp","cash-balance","CA Main","100.00");
const p1=addAccount("paypal","paypal-wallet","PayPal Wallet","200.00");
const c2=addAccount("cashapp","cash-balance","CA Backup","");
addEntry(c1,"2026-11-20","Manual grocery","out","12.50");
addEntry(c1,"2026-11-21","Manual gift received","in","6.00");
addEntry(c2,"2026-11-22","Manual lunch","out","10.00");
addEntry(p1,"2026-11-22","PayPal unrelated provider","in","20.00");
const snap=Accounts.snapshot(state);
assert.equal(snap.ok,true);
const activity=Provider.build("cashapp",snap,"activity");
assert.equal(activity.ok,true);
assert.equal(activity.accountCount,2);
assert.equal(activity.allAccounts.length,2);
assert.equal(activity.transactionCount,3);
assert.equal(activity.totalCents,null,"Unknown balance remains unknown after manual activity");
assert.equal(activity.activity.length,3);
assert.equal(activity.connected,false);
assert.equal(activity.persisted,false);
assert.equal(activity.canTransfer,false);
assert.equal(activity.canBorrow,false);
assert.equal(activity.canTrade,false);
assert.equal(activity.canManageCard,false);

function filter(direction="all",accountId="",query=""){
    return Provider.filterRecentActivity(activity,{direction,accountId,query});
}
assert.equal(filter().ok,true);
assert.equal(filter().shownCount,3);
assert.equal(filter().recentWindowCount,3);
assert.equal(filter().hasOlderEntries,false);
assert.equal(filter("in").shownCount,1);
assert.equal(filter("in").rows[0].description,"Manual gift received");
assert.equal(filter("out").shownCount,2);
assert.equal(filter("all",c1).shownCount,2);
assert.equal(filter("in",c1).shownCount,1);
assert.equal(filter("in",c2).shownCount,0);
assert.equal(filter("out",c2).rows[0].description,"Manual lunch");
assert.equal(filter("all","","GROCERY").shownCount,1,"Case-insensitive description");
assert.equal(filter("all","","CA BACKUP").shownCount,1,"Search account nickname");
assert.equal(filter("all","","unrelated").shownCount,0,"Must not see other provider");
assert.equal(filter("all","","   ").shownCount,3);
assert.equal(filter("all","","\u0001").ok,false);
assert.equal(filter("all","","a".repeat(65)).ok,false);
assert.equal(filter("lending").ok,false);
assert.equal(filter("all",p1).ok,false,"Cannot filter another provider's account");
assert.equal(Provider.filterRecentActivity(Provider.build("cashapp",snap,"stocks"),{}).ok,false);
assert.equal(Provider.filterRecentActivity(Provider.build("cashapp",snap,"home"),{}).ok,false);
assert.equal(Provider.filterRecentActivity(null,{}).ok,false);
assert.equal(Provider.filterRecentActivity({...activity,connected:true},{}).ok,false);
assert.equal(Provider.filterRecentActivity({...activity,persisted:true},{}).ok,false);
assert.equal(Provider.filterRecentActivity(activity,{accountId:42}).ok,false);
assert.equal(Provider.filterRecentActivity(activity,{query:42}).ok,false);

const before=JSON.stringify(snap);
filter("out",c1,"manual");
assert.equal(JSON.stringify(snap),before,"Projection may not write the M3 session");

const demo=Accounts.sampleDemo();
assert.equal(demo.ok,true);
const demoSnap=Accounts.snapshot(demo.state);
const demoActivity=Provider.build("chime",demoSnap,"activity");
assert.equal(demoActivity.ok,true);
assert.equal(demoActivity.accessLabel,"FICTIONAL DEMO DATA ONLY");
assert.equal(Provider.filterRecentActivity(demoActivity,{direction:"out"}).shownCount,1);
assert.equal(Accounts.addEntry(demo.state,{accountId:"demo-2",date:"2026-11-22",
    description:"Attempt demo write",direction:"in",amountText:"9.00"}).ok,false,
    "M3 source refuses demo quick entry regardless of M4 view");

// Older entries remain out of the provider projection; filtering cannot
// silently claim to search an entire transaction history.
let large=Accounts.emptyState();
const x=Accounts.addAccount(large,{providerId:"chime",productId:"chime-checking",
    nickname:"Long History",openingText:"500.00"});
assert.equal(x.ok,true);large=x.state;
for(let i=0;i<22;i++){
    const m=Accounts.addEntry(large,{accountId:x.account.id,date:"2026-11-22",
        description:"Recorded item "+i,direction:"out",amountText:"1.00"});
    assert.equal(m.ok,true,m.error);large=m.state;
}
const longActivity=Provider.build("chime",Accounts.snapshot(large),"activity");
assert.equal(longActivity.transactionCount,22);
assert.equal(longActivity.activity.length,12);
const recent=Provider.filterRecentActivity(longActivity,{query:"Recorded item"});
assert.equal(recent.ok,true);
assert.equal(recent.shownCount,12);
assert.equal(recent.recentWindowCount,12);
assert.equal(recent.hasOlderEntries,true);
assert.equal(Provider.filterRecentActivity(longActivity,{query:"Recorded item 0"}).shownCount,0);

const empty=Provider.build("bank",Accounts.snapshot(Accounts.emptyState()),"activity");
assert.equal(empty.ok,true);
assert.equal(Provider.filterRecentActivity(empty,{}).shownCount,0);
console.log("Banking M4b: provider-scoped filters, account/direction/search, 12-item window, demo refusal and no cross-provider reads PASS");
