import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

function policy(name) {
    const scope=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+name,import.meta.url),"utf8"),scope);
    return scope;
}
const Accounts=policy("FinanceBankingAccountsPolicy.js");
const Provider=policy("FinanceBankingProviderPolicy.js");
const Activity=policy("FinanceBankingSessionJournalPolicy.js");
const Navigation=policy("FinanceBankingActivityNavigationPolicy.js");

let state=Accounts.emptyState();
function account(providerId,productId,nickname) {
    const r=Accounts.addAccount(state,{providerId,productId,nickname,openingText:"100.00"});
    assert.equal(r.ok,true,r.error);
    state=r.state;
    return r.account.id;
}
function entry(accountId,amountText,direction,description) {
    const r=Accounts.addEntry(state,{accountId,date:"2026-11-22",
        amountText,direction,description});
    assert.equal(r.ok,true,r.error);
    state=r.state;
}
const cashA=account("cashapp","cash-balance","Wallet Alpha");
const cashB=account("cashapp","cash-balance","Wallet Beta");
const chime=account("chime","chime-checking","Checking");
const paypal=account("paypal","paypal-wallet","Wallet PayPal");
entry(cashA,"10.00","in","Alpha deposit");
entry(cashA,"3.00","out","Alpha payment");
entry(cashB,"90.00","in","Beta deposit");
entry(chime,"400.00","out","Chime payment");
entry(paypal,"15.00","in","PayPal deposit");

const unchanged=JSON.stringify(state);
const snap=Accounts.snapshot(state);
const cashHome=Provider.build("cashapp",snap,"home");
assert.equal(cashHome.ok,true,cashHome.error);
assert.equal(cashHome.providerId,"cashapp");
assert.equal(cashHome.sectionKind,"accounts");
assert.equal(Navigation.accountFilterIndex(cashHome,"cashapp",cashA),1);
assert.equal(Navigation.accountFilterIndex(cashHome,"cashapp",cashB),2);
assert.equal(Navigation.accountFilterIndex(cashHome,"cashapp",chime),-1);
assert.equal(Navigation.accountFilterIndex(cashHome,"chime",cashA),-1);
assert.equal(Navigation.accountFilterIndex(cashHome,"cashapp","acct-999"),-1);
assert.equal(Navigation.accountFilterIndex(cashHome,"cashapp",""),-1);
assert.equal(Navigation.accountFilterIndex(cashHome,"cashapp",null),-1);
assert.equal(Navigation.accountFilterIndex(null,"cashapp",cashA),-1);

const cashActivity=Provider.build("cashapp",snap,"activity");
const aIndex=Navigation.accountFilterIndex(cashActivity,"cashapp",cashA);
const bIndex=Navigation.accountFilterIndex(cashActivity,"cashapp",cashB);
assert.equal(aIndex,1);
assert.equal(bIndex,2);
let filtered=Activity.project(cashActivity,state,{
    accountId:cashActivity.allAccounts[aIndex-1].id,direction:"all",
    fromDate:"",toDate:"",query:"",page:0
});
assert.equal(filtered.ok,true,filtered.error);
assert.equal(filtered.totalMatches,2);
assert.equal(filtered.matchedInCents,1000);
assert.equal(filtered.matchedOutCents,300);
assert.equal(filtered.rows.every(x=>x.accountId===cashA),true);
assert.equal(filtered.accountBreakdown.length,1);
assert.equal(filtered.accountBreakdown[0].accountId,cashA);
filtered=Activity.project(cashActivity,state,{
    accountId:cashActivity.allAccounts[bIndex-1].id
});
assert.equal(filtered.ok,true,filtered.error);
assert.equal(filtered.totalMatches,1);
assert.equal(filtered.matchedInCents,9000);
assert.equal(filtered.matchedOutCents,0);
assert.equal(filtered.rows.every(x=>x.accountId===cashB),true);
assert.equal(filtered.accountBreakdown[0].accountNickname,"Wallet Beta");
assert.equal(Activity.project(cashActivity,state,{accountId:chime}).ok,false,
    "A foreign provider account must never enter a cash-app projection");

const chimeActivity=Provider.build("chime",snap,"activity");
assert.equal(Navigation.accountFilterIndex(chimeActivity,"chime",chime),1);
assert.equal(Navigation.accountFilterIndex(chimeActivity,"chime",cashA),-1);
const chimeResult=Activity.project(chimeActivity,state,{accountId:chime});
assert.equal(chimeResult.ok,true,chimeResult.error);
assert.equal(chimeResult.totalMatches,1);
assert.equal(chimeResult.rows[0].accountId,chime);
const paypalActivity=Provider.build("paypal",snap,"activity");
assert.equal(Navigation.accountFilterIndex(paypalActivity,"paypal",paypal),1);
assert.equal(Navigation.accountFilterIndex(paypalActivity,"paypal",cashB),-1);

const fake=(patch)=>Navigation.accountFilterIndex({...cashHome,...patch},"cashapp",cashA);
assert.equal(fake({connected:true}),-1);
assert.equal(fake({persisted:true}),-1);
assert.equal(fake({ok:false}),-1);
assert.equal(fake({providerId:"paypal"}),-1);
assert.equal(fake({allAccounts:[]}),-1);
assert.equal(fake({allAccounts:[...cashHome.allAccounts,cashHome.allAccounts[0]]}),-1,
    "Duplicated provider account ID is not an eligible navigation target");
assert.equal(fake({allAccounts:[{...cashHome.allAccounts[0],providerId:"chime"}]}),-1,
    "A single forged foreign-provider account invalidates the whole projection");
assert.equal(fake({allAccounts:[null]}),-1);
assert.equal(fake({allAccounts:[{id:"",providerId:"cashapp"}]}),-1);
assert.equal(fake({allAccounts:Array.from({length:13},(_,i)=>({
    id:"acct-"+(i+1),providerId:"cashapp"}))}),-1);
assert.equal(JSON.stringify(state),unchanged,
    "Navigation and journal filters must never write to the manual session");

// Account nicknames are mutable, but immutable account IDs remain the
// navigation reference after an M4l correction.
const original=state.accounts.find(a=>a.id===cashB);
const renamed=Accounts.correctAccountDetails(state,{
    accountId:cashB,
    expectedProviderId:original.providerId,
    expectedProductId:original.productId,
    expectedNickname:original.nickname,
    expectedOpeningCents:original.openingCents,
    nickname:"Renamed Beta",
    openingText:"100.00"
});
assert.equal(renamed.ok,true,renamed.error);
const renamedView=Provider.build("cashapp",Accounts.snapshot(renamed.state),"activity");
assert.equal(Navigation.accountFilterIndex(renamedView,"cashapp",cashB),2);
assert.equal(renamedView.allAccounts[1].nickname,"Renamed Beta");

// A fictional demo may be viewed but must remain disconnected/unwritable.
const demo=Accounts.sampleDemo();
assert.equal(demo.ok,true,demo.error);
const demoSnap=Accounts.snapshot(demo.state);
const demoView=Provider.build("chime",demoSnap,"activity");
assert.equal(demoView.ok,true,demoView.error);
const demoAccount=demoView.allAccounts[0].id;
assert.equal(Navigation.accountFilterIndex(demoView,"chime",demoAccount),1);
const demoResult=Activity.project(demoView,demo.state,{accountId:demoAccount});
assert.equal(demoResult.ok,true,demoResult.error);
assert.equal(demoResult.scope,"COMPLETE FICTIONAL DEMO SESSION");
assert.equal(demoResult.connected,false);
assert.equal(demoResult.persisted,false);

console.log("Banking M4n: selected-account Activity deep-link uses immutable IDs, correct provider indices, full-session filters, malformed-refusal and demo isolation PASS");
