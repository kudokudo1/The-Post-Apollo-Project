import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

function load(name) {
    const context=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+name,import.meta.url),"utf8"),context);
    return context;
}
const Accounts=load("FinanceBankingAccountsPolicy.js");
const P=load("FinanceBankingProviderPolicy.js");
const ids=P.providers().map(p=>p.id);
assert.deepEqual(Array.from(ids),["cashapp","chime","paypal","bank"]);
assert.equal(P.isProviderId("cashapp"),true);
assert.equal(P.isProviderId("chime"),true);
assert.equal(P.isProviderId("paypal"),true);
assert.equal(P.isProviderId("bank"),true);
assert.equal(P.isProviderId("fake"),false);
assert.equal(P.money(12545),"$125.45");
assert.equal(P.money(-101),"-$1.01");
assert.equal(P.money(null),"UNKNOWN");

const byId=Object.fromEntries(P.providers().map(p=>[p.id,p]));
for(const p of P.providers()){
    const featureIds=p.features.map(f=>f.id);
    assert.equal(featureIds[0],"home");
    assert.equal(new Set(featureIds).size,featureIds.length);
    assert.ok(featureIds.includes("activity"));
    assert.ok(featureIds.includes("security"));
    assert.ok(p.features.every(f=>f.summary && f.label && ["accounts","product","activity","restricted"].includes(f.kind)));
}
for(const id of ["home","payments","card","stocks","borrow","savings","activity","security"])
    assert.ok(byId.cashapp.features.some(f=>f.id===id),"Cash App "+id);
for(const id of ["checking","savings","card","transfers","credit"])
    assert.ok(byId.chime.features.some(f=>f.id===id),"Chime "+id);
for(const id of ["wallet","payments","cards","savings","paylater"])
    assert.ok(byId.paypal.features.some(f=>f.id===id),"PayPal "+id);

const empty=Accounts.snapshot(Accounts.emptyState());
assert.equal(empty.ok,true);
for(const id of ids) {
    const view=P.build(id,empty,"home");
    assert.equal(view.ok,true);
    assert.equal(view.accountCount,0);
    assert.equal(view.totalCents,null);
    assert.equal(view.connected,false);
    assert.equal(view.persisted,false);
    assert.equal(view.canTransfer,false);
    assert.equal(view.canTrade,false);
    assert.equal(view.canBorrow,false);
    assert.equal(view.canManageCard,false);
    assert.equal(view.accessLabel,"LOCAL MANUAL DATA ONLY");
}
assert.equal(P.build("fake",empty,"home").ok,false);
assert.equal(P.build("cashapp",null,"home").ok,false);
assert.equal(P.build("cashapp",{...empty,connected:true},"home").ok,false);
assert.equal(P.build("cashapp",{...empty,persisted:true},"home").ok,false);
assert.equal(P.build("cashapp",{...empty,accounts:[null]},"home").ok,false);
assert.equal(P.build("cashapp",{...empty,accounts:new Array(13).fill({})},"home").ok,false);

let state=Accounts.emptyState();
function account(providerId,productId,nickname,openingText){
    const r=Accounts.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);
    state=r.state;
    return r.account.id;
}
function entry(accountId,date,description,direction,amountText){
    const r=Accounts.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(r.ok,true,r.error);
    state=r.state;
}
const ca=account("cashapp","cash-balance","My Cash App","100.00");
const ch1=account("chime","chime-checking","Checking","250.00");
const ch2=account("chime","chime-savings","Savings","");
const pp=account("paypal","paypal-wallet","PayPal wallet","20.10");
entry(ca,"2026-11-20","Manual received","in","15.00");
entry(ch1,"2026-11-21","Manual store","out","12.00");
entry(ch2,"2026-11-22","Manual savings deposit","in","6.00");
entry(pp,"2026-11-18","Manual purchase","out","3.10");
const snap=Accounts.snapshot(state);
assert.equal(snap.ok,true);
const cash=P.build("cashapp",snap,"home");
assert.equal(cash.accountCount,1);
assert.equal(cash.totalCents,11500);
assert.equal(cash.transactionCount,1);
assert.equal(cash.visibleAccounts[0].id,ca);
assert.equal(cash.dataLabel,"MANUAL SESSION");
assert.equal(cash.accessLabel,"LOCAL MANUAL DATA ONLY");
for(const restricted of ["payments","card","stocks","borrow","savings","security"]) {
    const m=P.build("cashapp",snap,restricted);
    assert.equal(m.ok,true);
    assert.equal(m.sectionKind,"restricted",restricted);
    assert.equal(m.accessLabel,"PROVIDER AUTHORIZATION REQUIRED");
    assert.equal(m.visibleAccounts.length,0);
    assert.equal(m.activity.length,0);
    assert.equal(m.canTransfer,false);
    assert.equal(m.canTrade,false);
    assert.equal(m.canBorrow,false);
    assert.equal(m.canManageCard,false);
}
const ch=P.build("chime",snap,"home");
assert.equal(ch.accountCount,2);
assert.equal(ch.unknownCount,1);
assert.equal(ch.knownCount,1);
assert.equal(ch.knownSubtotalCents,23800);
assert.equal(ch.totalCents,null,"Unknown savings cannot be converted to $0");
assert.equal(ch.visibleAccounts.length,2);
assert.equal(P.build("chime",snap,"checking").visibleAccounts.length,1);
assert.equal(P.build("chime",snap,"checking").visibleAccounts[0].id,ch1);
assert.equal(P.build("chime",snap,"savings").visibleAccounts[0].id,ch2);
assert.equal(P.build("chime",snap,"savings").visibleAccounts[0].balanceCents,null);
assert.equal(P.build("chime",snap,"credit").sectionKind,"restricted");

const paypal=P.build("paypal",snap,"home");
assert.equal(paypal.accountCount,1);
assert.equal(paypal.totalCents,1700);
assert.equal(P.build("paypal",snap,"wallet").visibleAccounts[0].id,pp);
assert.equal(P.build("paypal",snap,"paylater").accessLabel,"PROVIDER AUTHORIZATION REQUIRED");

const activityCh=P.build("chime",snap,"activity");
assert.equal(activityCh.sectionKind,"activity");
assert.equal(activityCh.visibleAccounts.length,0);
assert.equal(activityCh.activity.length,2);
assert.equal(activityCh.activity[0].accountId,ch2);
assert.equal(activityCh.activity[1].accountId,ch1);
assert.equal(activityCh.activity[0].description,"Manual savings deposit");
assert.equal(P.build("cashapp",snap,"activity").activity.length,1);
assert.equal(P.build("paypal",snap,"activity").activity.length,1);
assert.equal(P.build("bank",snap,"activity").activity.length,0);
const beforeSnap=JSON.stringify(snap);
P.build("chime",snap,"home");
assert.equal(JSON.stringify(snap),beforeSnap,"Provider projection cannot mutate M3 source");
assert.equal(P.build("paypal",snap,"INVALID-SECTION").sectionId,"home","Unknown section must fall back to home");
const duplicate={...snap,accounts:[snap.accounts[0],snap.accounts[0]]};
assert.equal(P.build("cashapp",duplicate,"home").ok,false);

const demo=Accounts.sampleDemo();
assert.equal(demo.ok,true);
const ds=Accounts.snapshot(demo.state);
for(const id of ["cashapp","chime","paypal"]) {
    const view=P.build(id,ds,"home");
    assert.equal(view.ok,true);
    assert.equal(view.dataLabel,"FICTIONAL DEMO");
    assert.equal(view.accessLabel,"FICTIONAL DEMO DATA ONLY");
    assert.equal(view.accountCount,1);
    assert.equal(view.connected,false);
}
assert.equal(P.build("cashapp",ds,"stocks").accessLabel,"PROVIDER AUTHORIZATION REQUIRED");
assert.equal(P.build("cashapp",ds,"activity").accessLabel,"FICTIONAL DEMO DATA ONLY");
console.log("Banking M4: four providers, feature boundaries, product views, activity, unknown balances and demo isolation PASS");
