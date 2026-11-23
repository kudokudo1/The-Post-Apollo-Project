import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
function load(file) {
    const scope=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+file,import.meta.url),"utf8"),scope);
    return scope;
}
const Accounts=load("FinanceBankingAccountsPolicy.js");
const Provider=load("FinanceBankingProviderPolicy.js");
const Journal=load("FinanceBankingSessionJournalPolicy.js");
let state=Accounts.emptyState();
function add(providerId,productId,nickname,openingText) {
    const r=Accounts.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.account.id;
}
function entry(accountId,date,description,direction,amountText) {
    const r=Accounts.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.entry.id;
}
const cash=add("cashapp","cash-balance","Cash Main","100.00");
const chime=add("chime","chime-checking","Checking","100.00");
const second=add("cashapp","cash-balance","Cash Reserve","");
entry(cash,"2024-02-28","Winter grocery","out","12.50");
entry(cash,"2024-02-29","Leap-day deposit","in","50.25");
entry(second,"2024-03-01","Reserve transfer","in","20.00");
entry(cash,"2024-03-15","Spring purchase","out","8.75");
entry(chime,"2024-03-15","Other provider secret","in","200.00");
entry(second,"2024-04-01","Late refund","in","11.00");
const projection=Provider.build("cashapp",Accounts.snapshot(state),"activity");
assert.equal(projection.ok,true);
const get=(options={})=>Journal.project(projection,state,options);

let all=get();
assert.equal(all.ok,true,all.error);
assert.equal(all.totalMatches,5);
assert.equal(all.matchedInCents,8125);
assert.equal(all.matchedOutCents,2125);
assert.equal(all.matchedNetCents,6000);
assert.equal(all.fromDate,"");
assert.equal(all.toDate,"");
assert.equal(all.totalsScope,"FILTERED SESSION ENTRIES // NOT VERIFIED INCOME OR SPENDING");
assert.equal(all.rows.some(x=>x.accountId===chime),false);
let leap=get({fromDate:"2024-02-29",toDate:"2024-03-01"});
assert.equal(leap.ok,true,leap.error);
assert.equal(leap.totalMatches,2);
assert.equal(leap.matchedInCents,7025);
assert.equal(leap.matchedOutCents,0);
assert.equal(leap.matchedNetCents,7025);
assert.equal(leap.rows[0].description,"Reserve transfer");
assert.equal(leap.rows[1].description,"Leap-day deposit");
let feb=get({toDate:"2024-02-29"});
assert.equal(feb.ok,true);
assert.equal(feb.totalMatches,2);
assert.equal(feb.matchedInCents,5025);
assert.equal(feb.matchedOutCents,1250);
let mar=get({fromDate:"2024-03-01",toDate:"2024-03-31"});
assert.equal(mar.ok,true);
assert.equal(mar.totalMatches,2);
assert.equal(mar.matchedInCents,2000);
assert.equal(mar.matchedOutCents,875);
assert.equal(mar.matchedNetCents,1125);
assert.equal(get({fromDate:"2024-04-01",toDate:"2024-04-01"}).rows[0].description,"Late refund");
assert.equal(get({fromDate:"2025-01-01"}).totalMatches,0);
assert.equal(get({toDate:"2023-12-31"}).totalMatches,0);
assert.equal(get({fromDate:"2025-01-01"}).matchedInCents,0);
assert.equal(get({fromDate:"2025-01-01"}).matchedOutCents,0);
assert.equal(get({fromDate:"2025-01-01"}).pageCount,1);
assert.equal(get({fromDate:"2025-01-01"}).from,0);

let combo=get({accountId:cash,fromDate:"2024-02-29",
    toDate:"2024-03-15",direction:"out",query:"purchase"});
assert.equal(combo.ok,true,combo.error);
assert.equal(combo.totalMatches,1);
assert.equal(combo.rows[0].description,"Spring purchase");
assert.equal(combo.matchedInCents,0);
assert.equal(combo.matchedOutCents,875);
assert.equal(combo.matchedNetCents,-875);
assert.equal(get({accountId:chime,fromDate:"2024-02-29"}).ok,false,
    "Filtering cannot expose another provider's account");
assert.equal(get({query:"other provider",fromDate:"2024-01-01"}).totalMatches,0);
assert.equal(get({direction:"in",fromDate:"2024-02-28",toDate:"2024-03-31"}).matchedInCents,7025);
assert.equal(get({direction:"in",fromDate:"2024-02-28",toDate:"2024-03-31"}).matchedOutCents,0);
assert.equal(get({direction:"out",fromDate:"2024-02-28",toDate:"2024-03-31"}).matchedOutCents,2125);
const previous=JSON.stringify(state);
get({fromDate:"2024-02-29",toDate:"2024-03-31",query:"Spring"});
assert.equal(JSON.stringify(state),previous,"Date filtering must never write the manual session");

for(const bad of [
  {fromDate:"2023-02-29"}, {fromDate:"2024-02-30"},
  {toDate:"2024-13-01"}, {fromDate:"2024-00-01"},
  {toDate:"2024-1-01"}, {fromDate:"2024-01-1"},
  {fromDate:"2024-01-01 "}, {fromDate:" "},
  {toDate:1}, {fromDate:null}, {toDate:[]},
  {fromDate:"2024-04-02",toDate:"2024-04-01"},
  {fromDate:"2024-04-01",toDate:"2024-03-31"},
  {fromDate:"1800-01-01"}, {toDate:"2200-01-01"},
  {fromDate:"2024-02-29\n"}, {toDate:"2024/02/29"}
]) {
    const r=get(bad);
    assert.equal(r.ok,false,JSON.stringify(bad));
    assert.match(r.error,/INVALID DATE RANGE/);
}
assert.equal(Journal.project(Provider.build("cashapp",Accounts.snapshot(state),"stocks"),state,{fromDate:"2024-02-29"}).ok,false);

// Pagination totals cover every matching entry, not only the visible page.
let large=Accounts.emptyState();
const one=Accounts.addAccount(large,{providerId:"chime",productId:"chime-checking",
    nickname:"Long journal",openingText:"500.00"});
assert.equal(one.ok,true);large=one.state;
for(let i=0;i<60;i++) {
    const month=i%2===0?"2024-03-10":"2024-04-10";
    const r=Accounts.addEntry(large,{accountId:one.account.id,date:month,
        description:"item "+i,direction:i%3===0?"in":"out",amountText:"1.00"});
    assert.equal(r.ok,true,r.error);large=r.state;
}
const bigView=Provider.build("chime",Accounts.snapshot(large),"activity");
const p0=Journal.project(bigView,large,{fromDate:"2024-03-01",toDate:"2024-03-31"});
const p1=Journal.project(bigView,large,{fromDate:"2024-03-01",toDate:"2024-03-31",page:1});
assert.equal(p0.ok,true,p0.error);
assert.equal(p0.totalMatches,30);
assert.equal(p0.rows.length,20);
assert.equal(p1.rows.length,10);
assert.equal(p1.pageCount,2);
assert.equal(p1.totalMatches,30);
assert.equal(p0.matchedInCents,1000);
assert.equal(p0.matchedOutCents,2000);
assert.equal(p1.matchedInCents,p0.matchedInCents);
assert.equal(p1.matchedOutCents,p0.matchedOutCents);
assert.equal(p1.matchedNetCents,-1000);

// Fictional demo can filter, but must retain its fictional label.
const demo=Accounts.sampleDemo();
const demoView=Provider.build("chime",Accounts.snapshot(demo.state),"activity");
const demoResult=Journal.project(demoView,demo.state,{
    fromDate:"2026-11-19",toDate:"2026-11-19"});
assert.equal(demoResult.ok,true,demoResult.error);
assert.equal(demoResult.scope,"COMPLETE FICTIONAL DEMO SESSION");
assert.equal(demoResult.matchedInCents,0);
assert.equal(demoResult.matchedOutCents,2645);
assert.equal(Accounts.addEntry(demo.state,{accountId:"demo-2",date:"2026-11-19",
    description:"no",direction:"in",amountText:"1.00"}).ok,false);
console.log("Banking M4g: inclusive date filters, leap years, combined queries, full-match money totals, pagination and demo isolation PASS");
