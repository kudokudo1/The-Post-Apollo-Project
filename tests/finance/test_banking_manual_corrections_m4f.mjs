import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
function load(name) {
    const ctx=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+name,import.meta.url),"utf8"),ctx);
    return ctx;
}
const A=load("FinanceBankingAccountsPolicy.js");
const P=load("FinanceBankingProviderPolicy.js");
const J=load("FinanceBankingSessionJournalPolicy.js");
let state=A.emptyState();
function account(providerId,productId,nickname,openingText){
    const r=A.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.account.id;
}
function entry(accountId,date,description,direction,amountText){
    const r=A.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.entry;
}
const cash=account("cashapp","cash-balance","Cash","200.00");
const chime=account("chime","chime-checking","Checking","100.00");
const old=entry(cash,"2026-11-20","old purchase","out","20.00");
const other=entry(chime,"2026-11-21","different provider","in","10.00");
const latest=entry(cash,"2026-11-22","later purchase","out","3.00");
const beforeNext=state.nextId;
const expected={entryId:old.id,accountId:cash,
    expectedDate:old.date,expectedDescription:old.description,
    expectedAmountCents:old.amountCents};
assert.equal(A.snapshot(state).accounts.find(a=>a.id===cash).balanceCents,17700);
assert.equal(J.project(P.build("cashapp",A.snapshot(state),"activity"),state,
    {query:"old purchase"}).rows.length,1);

const changed=A.correctEntry(state,{...expected,
    date:"2026-11-18",description:"corrected grocery",
    direction:"out",amountText:"7.25"});
assert.equal(changed.ok,true,changed.error);
state=changed.state;
assert.equal(state.nextId,beforeNext,"Editing must never recycle entry IDs");
assert.equal(changed.corrected.id,old.id);
assert.equal(changed.corrected.accountId,cash);
assert.equal(changed.corrected.origin,"manual");
assert.equal(changed.corrected.amountCents,-725);
assert.equal(changed.corrected.date,"2026-11-18");
assert.equal(state.entries.length,3);
assert.equal(state.entries[1].id,other.id);
assert.equal(state.entries[2].id,latest.id);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===cash).balanceCents,18975);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===chime).balanceCents,11000);
const recalc=J.project(P.build("cashapp",A.snapshot(state),"activity"),state,
    {query:"corrected grocery"});
assert.equal(recalc.ok,true);
assert.equal(recalc.totalMatches,1);
assert.equal(recalc.rows[0].id,old.id);
assert.equal(recalc.rows[0].amountCents,-725);
assert.equal(A.correctEntry(state,{...expected,
    date:"2026-11-21",description:"stale edit",direction:"in",amountText:"1.00"}).ok,false,
    "Old form snapshot must refuse after successful correction");
assert.equal(A.deleteEntry(state,expected).ok,false,
    "Stale delete must refuse after correction");
const current={entryId:old.id,accountId:cash,
    expectedDate:"2026-11-18",expectedDescription:"corrected grocery",
    expectedAmountCents:-725};
for(const bad of [
    {...current,accountId:chime},
    {...current,entryId:"entry-999"},
    {...current,expectedAmountCents:-726},
    {...current,expectedDescription:"made up"},
    {...current,expectedDate:"2026-11-19"}
]) {
    assert.equal(A.correctEntry(state,{...bad,date:"2026-11-23",
        description:"attempt",direction:"out",amountText:"1.00"}).ok,false);
    assert.equal(A.deleteEntry(state,bad).ok,false);
}
for(const fields of [
    {date:"2026-02-30",description:"invalid date",direction:"in",amountText:"1.00"},
    {date:"2026-11-22",description:"",direction:"in",amountText:"1.00"},
    {date:"2026-11-22",description:"\n",direction:"in",amountText:"1.00"},
    {date:"2026-11-22",description:"valid",direction:"in",amountText:"0.00"},
    {date:"2026-11-22",description:"valid",direction:"in",amountText:"-2.00"},
    {date:"2026-11-22",description:"valid",direction:"in",amountText:"10.000"},
    {date:"2026-11-22",description:"valid",direction:"transfer",amountText:"5.00"},
])assert.equal(A.correctEntry(state,{...current,...fields}).ok,false,
    JSON.stringify(fields));
assert.equal(A.correctEntry(state,null).ok,false);
assert.equal(A.deleteEntry(state,null).ok,false);
assert.equal(A.deleteEntry(A.emptyState(),current).ok,false);
assert.equal(A.correctEntry(A.emptyState(),{...current,date:"2026-11-22",
    description:"No",direction:"out",amountText:"1.00"}).ok,false);

// Valid direction and amount changes modify session money arithmetic only.
const credit=A.correctEntry(state,{...current,date:"2026-11-18",
    description:"corrected refund",direction:"in",amountText:"30.00"});
assert.equal(credit.ok,true,credit.error);
state=credit.state;
assert.equal(state.entries[0].amountCents,3000);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===cash).balanceCents,22700);
assert.equal(J.project(P.build("cashapp",A.snapshot(state),"activity"),state,
    {direction:"in"}).rows[0].description,"corrected refund");

const creditExpected={entryId:old.id,accountId:cash,
    expectedDate:"2026-11-18",expectedDescription:"corrected refund",
    expectedAmountCents:3000};
const removed=A.deleteEntry(state,creditExpected);
assert.equal(removed.ok,true,removed.error);
state=removed.state;
assert.equal(removed.deleted.id,old.id);
assert.equal(state.entries.length,2);
assert.equal(state.nextId,beforeNext);
assert.equal(state.entries.some(e=>e.id===old.id),false);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===cash).balanceCents,19700);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===chime).balanceCents,11000);
assert.equal(J.project(P.build("cashapp",A.snapshot(state),"activity"),state,
    {query:"corrected refund"}).totalMatches,0);
assert.equal(A.deleteEntry(state,creditExpected).ok,false);
const appended=A.addEntry(state,{accountId:cash,date:"2026-11-23",
    description:"new after delete",direction:"in",amountText:"1.00"});
assert.equal(appended.ok,true,appended.error);
assert.notEqual(appended.entry.id,old.id,"Deleted transaction IDs remain unused");
assert.equal(appended.entry.id,"entry-"+beforeNext);

// Boundary: a correction causing an invalid final balance is rejected atomically.
let near=A.emptyState();
near=A.addAccount(near,{providerId:"bank",productId:"bank-checking",
    nickname:"Upper",openingText:"9999999.00"}).state;
const e=A.addEntry(near,{accountId:near.accounts[0].id,date:"2026-11-22",
    description:"baseline",direction:"out",amountText:"1.00"}).entry;
near=A.addEntry(near,{accountId:near.accounts[0].id,date:"2026-11-22",
    description:"baseline",direction:"out",amountText:"1.00"}).state;
const prior=JSON.stringify(near);
assert.equal(A.correctEntry(near,{entryId:near.entries[0].id,
    accountId:near.accounts[0].id,expectedDate:near.entries[0].date,
    expectedDescription:near.entries[0].description,
    expectedAmountCents:near.entries[0].amountCents,date:"2026-11-22",
    description:"overflow credit",direction:"in",amountText:"10.00"}).ok,false);
assert.equal(JSON.stringify(near),prior,"Refused correction never mutates source");

// A 300-entry session can still fix an older entry without allocating a new ID.
let full=A.emptyState();
full=A.addAccount(full,{providerId:"paypal",productId:"paypal-wallet",
    nickname:"Full",openingText:"500.00"}).state;
for(let i=0;i<300;i++) {
    const r=A.addEntry(full,{accountId:full.accounts[0].id,date:"2026-11-22",
        description:"item "+i,direction:"out",amountText:"0.01"});
    assert.equal(r.ok,true,r.error);full=r.state;
}
const original=full.entries[0];
const fixed=A.correctEntry(full,{entryId:original.id,accountId:original.accountId,
    expectedDate:original.date,expectedDescription:original.description,
    expectedAmountCents:original.amountCents,date:original.date,
    description:"older corrected",direction:"out",amountText:"0.02"});
assert.equal(fixed.ok,true,fixed.error);
assert.equal(fixed.state.entries.length,300);
assert.equal(fixed.state.nextId,full.nextId);
const lastPage=J.project(P.build("paypal",A.snapshot(fixed.state),"activity"),
    fixed.state,{query:"older corrected"});
assert.equal(lastPage.totalMatches,1);
assert.equal(lastPage.rows[0].description,"older corrected");

// Demo and other providers cannot mutate a manual ledger by mislabeling origin.
const demo=A.sampleDemo();
assert.equal(demo.ok,true);
const d=demo.state.entries[0];
const dFields={entryId:d.id,accountId:d.accountId,
    expectedDate:d.date,expectedDescription:d.description,
    expectedAmountCents:d.amountCents};
assert.equal(A.deleteEntry(demo.state,dFields).ok,false);
assert.equal(A.correctEntry(demo.state,{...dFields,date:d.date,description:"No",
    direction:"out",amountText:"1.00"}).ok,false);
assert.equal(A.validState(state),true);
console.log("Banking M4f: older manual entry corrections/deletion, stale-original refusal, immutable IDs, balance math, 300 cap and demo isolation PASS");
