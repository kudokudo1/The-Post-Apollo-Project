import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

function load(path) {
    const scope=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+path,import.meta.url),"utf8"),scope);
    return scope;
}
const Accounts=load("FinanceBankingAccountsPolicy.js");
const Provider=load("FinanceBankingProviderPolicy.js");
const Journal=load("FinanceBankingSessionJournalPolicy.js");
let state=Accounts.emptyState();
function account(providerId,productId,nickname,openingText) {
    const r=Accounts.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);
    state=r.state;return r.account.id;
}
function entry(accountId,date,description,direction,amountText) {
    const r=Accounts.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(r.ok,true,r.error);
    state=r.state;return r.entry;
}
const primary=account("chime","chime-checking","Chime Primary","100.00");
const savings=account("chime","chime-savings","Chime Reserve","");
const idle=account("chime","chime-checking","Chime Idle","20.00");
const paypal=account("paypal","paypal-wallet","Different Provider","20.00");
for(let i=0;i<20;i++)entry(primary,"2026-11-20","Food "+i,"out","1.00");
for(let i=0;i<5;i++)entry(savings,"2026-11-22","Deposit "+i,"in","2.00");
entry(paypal,"2026-11-22","Private PayPal transfer","in","300.00");
const initial=JSON.stringify(state);
const view=Provider.build("chime",Accounts.snapshot(state),"activity");
assert.equal(view.ok,true);
assert.equal(view.accountCount,3);
assert.equal(view.transactionCount,25);
const get=(options={})=>Journal.project(view,state,options);
const first=get(),second=get({page:1});
assert.equal(first.ok,true,first.error);
assert.equal(first.totalMatches,25);
assert.equal(first.rows.length,20);
assert.equal(first.pageCount,2);
assert.equal(second.rows.length,5);
assert.equal(first.matchedInCents,1000);
assert.equal(first.matchedOutCents,2000);
assert.equal(first.matchedNetCents,-1000);
assert.equal(first.accountBreakdown.length,2,"Idle accounts must not create fake activity");
assert.equal(second.accountBreakdown.length,2,"Account totals cover all matched pages");
assert.equal(first.accountBreakdown[0].accountId,primary);
assert.equal(first.accountBreakdown[0].accountNickname,"Chime Primary");
assert.equal(first.accountBreakdown[0].matchedCount,20);
assert.equal(first.accountBreakdown[0].matchedInCents,0);
assert.equal(first.accountBreakdown[0].matchedOutCents,2000);
assert.equal(first.accountBreakdown[0].matchedNetCents,-2000);
assert.equal(first.accountBreakdown[1].accountId,savings);
assert.equal(first.accountBreakdown[1].matchedCount,5);
assert.equal(first.accountBreakdown[1].matchedInCents,1000);
assert.equal(first.accountBreakdown[1].matchedOutCents,0);
assert.equal(first.accountBreakdown[1].matchedNetCents,1000);
assert.equal(first.accountBreakdown.some(a=>a.accountId===idle||a.accountId===paypal),false);
assert.equal(first.accountBreakdown.reduce((s,a)=>s+a.matchedCount,0),first.totalMatches);
assert.equal(first.accountBreakdown.reduce((s,a)=>s+a.matchedInCents,0),first.matchedInCents);
assert.equal(first.accountBreakdown.reduce((s,a)=>s+a.matchedOutCents,0),first.matchedOutCents);
assert.equal(first.accountBreakdown.reduce((s,a)=>s+a.matchedNetCents,0),first.matchedNetCents);
assert.equal(first.accountBreakdown.every(a=>a.matchedCount>0),true);
assert.deepEqual(JSON.parse(JSON.stringify(first.accountBreakdown)),
    JSON.parse(JSON.stringify(second.accountBreakdown)),"Paging must not change matched totals");

const march=get({fromDate:"2026-11-21",toDate:"2026-11-23"});
assert.equal(march.totalMatches,5);
assert.equal(march.accountBreakdown.length,1);
assert.equal(march.accountBreakdown[0].accountId,savings);
assert.equal(march.matchedInCents,1000);
assert.equal(march.matchedOutCents,0);
const out=get({direction:"out"});
assert.equal(out.accountBreakdown.length,1);
assert.equal(out.accountBreakdown[0].accountId,primary);
assert.equal(out.accountBreakdown[0].matchedCount,20);
const inOnly=get({direction:"in",accountId:savings,query:"DEPOSIT"});
assert.equal(inOnly.totalMatches,5);
assert.equal(inOnly.accountBreakdown.length,1);
assert.equal(inOnly.accountBreakdown[0].matchedCount,5);
assert.equal(inOnly.accountBreakdown[0].matchedInCents,1000);
const byNickname=get({query:"Chime Reserve"});
assert.equal(byNickname.accountBreakdown.length,1);
assert.equal(byNickname.accountBreakdown[0].accountId,savings);
const none=get({query:"no matching entry",fromDate:"2026-11-21"});
assert.equal(none.ok,true);
assert.equal(none.totalMatches,0);
assert.equal(none.accountBreakdown.length,0);
assert.equal(none.matchedNetCents,0);
assert.equal(get({accountId:paypal}).ok,false);
assert.equal(get({query:"Private PayPal transfer"}).accountBreakdown.length,0);
assert.equal(get({fromDate:"2026-11-29",toDate:"2026-11-20"}).ok,false);

assert.equal(JSON.stringify(state),initial,"Read-only projection must not mutate M3 session");
const badView={...view,allAccounts:view.allAccounts.map(a=>a.id===primary
    ? {...a,nickname:"Forged"}:a)};
assert.equal(Journal.project(badView,state,{}).ok,false);
const stale={...state,entries:state.entries.slice(1)};
assert.equal(Journal.project(view,stale,{}).ok,false);

// Fictional demo is readable but explicitly not connected, persisted or mutable.
const demo=Accounts.sampleDemo();
assert.equal(demo.ok,true);
const ds=Accounts.snapshot(demo.state);
const dv=Provider.build("chime",ds,"activity");
const d=Journal.project(dv,demo.state,{});
assert.equal(d.ok,true,d.error);
assert.equal(d.scope,"COMPLETE FICTIONAL DEMO SESSION");
assert.equal(d.accountBreakdown.length,1);
assert.equal(d.accountBreakdown[0].matchedCount,1);
assert.equal(d.accountBreakdown[0].matchedOutCents,2645);
assert.equal(d.accountBreakdown[0].matchedNetCents,-2645);
assert.equal(d.connected,false);
assert.equal(d.persisted,false);
assert.equal(Accounts.correctEntry(demo.state,{entryId:"demo-entry-4"}).ok,false);

const empty=Accounts.emptyState();
const e=Journal.project(Provider.build("cashapp",Accounts.snapshot(empty),"activity"),empty,{});
assert.equal(e.ok,true);
assert.equal(e.accountBreakdown.length,0);

// Many accounts must remain bounded to exactly the provider's existing rows.
let wide=Accounts.emptyState();
for(let i=0;i<12;i++) {
    let r=Accounts.addAccount(wide,{providerId:"bank",productId:"bank-checking",
        nickname:"Bank "+i,openingText:""});
    assert.equal(r.ok,true,r.error);wide=r.state;
    r=Accounts.addEntry(wide,{accountId:r.account.id,date:"2026-11-22",
        description:"transaction "+i,direction:i%2?"in":"out",amountText:"0.01"});
    assert.equal(r.ok,true,r.error);wide=r.state;
}
const wideView=Provider.build("bank",Accounts.snapshot(wide),"activity");
const wideResult=Journal.project(wideView,wide,{});
assert.equal(wideResult.ok,true,wideResult.error);
assert.equal(wideResult.accountBreakdown.length,12);
assert.equal(wideResult.accountBreakdown.reduce((n,a)=>n+a.matchedCount,0),12);
assert.equal(wideResult.accountBreakdown.reduce((n,a)=>n+a.matchedInCents,0),6);
assert.equal(wideResult.accountBreakdown.reduce((n,a)=>n+a.matchedOutCents,0),6);

console.log("Banking M4h: per-account full-filter totals, reconciliation, page invariance, 12-account cap, provider isolation and fictional scope PASS");
