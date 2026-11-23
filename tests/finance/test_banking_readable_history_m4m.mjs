import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const ctx=vm.createContext({Date});
vm.runInContext(readFileSync(new URL("../../widgets/FinanceBankingAccountsPolicy.js",import.meta.url),"utf8"),ctx);
const A=ctx;
let state=A.emptyState();
function account(providerId,productId,nickname,openingText) {
    const r=A.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.account.id;
}
function addEntry(accountId,description,amountText,direction="in") {
    const r=A.addEntry(state,{accountId,date:"2026-11-23",
        description,amountText,direction});
    assert.equal(r.ok,true,r.error);state=r.state;return r.entry;
}
const cash=account("cashapp","cash-balance","Cash","100.00");
const bank=account("chime","chime-checking","Checking","100.00");
let snap=A.snapshot(state);
assert.equal(snap.ok,true,snap.error);
assert.equal(snap.accounts[0].recent.length,0);
assert.equal(snap.accounts[0].transactionCount,0);
const ids=[];
for(let i=1;i<=14;i++) {
    const entry=addEntry(cash,"Activity "+i,"1.00",i%2?"in":"out");
    ids.push(entry.id);
}
const before=JSON.stringify(state);
snap=A.snapshot(state);
let row=snap.accounts.find(a=>a.id===cash);
assert.equal(row.transactionCount,14);
assert.equal(row.recent.length,12);
assert.deepEqual(Array.from(row.recent.map(x=>x.id)),ids.slice(-12).reverse());
assert.equal(row.recent[0].description,"Activity 14");
assert.equal(row.recent[11].description,"Activity 3");
assert.equal(row.recent.slice(0,3).length,3);
assert.deepEqual(Array.from(row.recent.slice(0,3).map(x=>x.description)),
    ["Activity 14","Activity 13","Activity 12"]);
assert.deepEqual(Array.from(row.recent.slice(0,12).map(x=>x.id)),
    Array.from(row.recent.map(x=>x.id)));
assert.equal(row.netChangeCents,0,"Seven in and seven out must cancel");
assert.equal(row.balanceCents,10000);
assert.equal(JSON.stringify(state),before,"Read-only preview does not mutate ledger");

const move=A.addManualTransfer(state,{fromAccountId:cash,toAccountId:bank,
    date:"2026-11-22",description:"Transfer preview",amountText:"20.00"});
assert.equal(move.ok,true,move.error);state=move.state;
snap=A.snapshot(state);row=snap.accounts.find(a=>a.id===cash);
assert.equal(row.transactionCount,15);
assert.equal(row.recent[0].transferSide,"out");
assert.equal(row.recent[0].transferId,move.transfer.transferId);
assert.equal(row.recent[0].amountCents,-2000);
assert.equal(row.recent[0].description,"Transfer preview");
assert.equal(row.recent.length,12);
assert.equal(snap.accounts.find(a=>a.id===bank).recent.length,1);
assert.equal(snap.accounts.find(a=>a.id===bank).recent[0].transferSide,"in");
assert.equal(snap.accounts.find(a=>a.id===bank).recent[0].amountCents,2000);
assert.equal(row.netChangeCents,-2000);
assert.equal(row.balanceCents,8000);

const corrected=A.correctManualTransfer(state,{
    transferId:move.transfer.transferId,
    fromAccountId:cash,toAccountId:bank,
    expectedDate:"2026-11-22",expectedDescription:"Transfer preview",
    expectedAmountCents:2000,date:"2026-11-20",
    description:"Corrected transfer",amountText:"15.00"});
assert.equal(corrected.ok,true,corrected.error);state=corrected.state;
snap=A.snapshot(state);row=snap.accounts.find(a=>a.id===cash);
assert.equal(row.recent[0].description,"Corrected transfer");
assert.equal(row.recent[0].amountCents,-1500);
assert.equal(row.balanceCents,8500);
assert.equal(snap.accounts.find(a=>a.id===bank).balanceCents,11500);
assert.equal(row.transactionCount,15);
assert.equal(row.recent.length,12);
const current=A.transferPairs(state).rows.find(p=>p.transferId===move.transfer.transferId);
const removed=A.removeManualTransfer(state,current);
assert.equal(removed.ok,true,removed.error);state=removed.state;
snap=A.snapshot(state);
row=snap.accounts.find(a=>a.id===cash);
assert.equal(row.transactionCount,14);
assert.equal(row.recent[0].description,"Activity 14");
assert.equal(row.recent.every(x=>!x.transferId),true);
assert.equal(row.balanceCents,10000);
assert.equal(snap.accounts.find(a=>a.id===bank).transactionCount,0);

// The read-only short preview is bounded even when the full session is large.
while(state.entries.length<300)
    addEntry(cash,"More "+state.entries.length,"0.01","in");
snap=A.snapshot(state);row=snap.accounts.find(a=>a.id===cash);
assert.equal(row.transactionCount,300);
assert.equal(row.recent.length,12);
assert.equal(row.recent.slice(0,3).length,3);
assert.equal(row.recent.slice(0,12).length,12);
assert.equal(A.validState(state),true);

// Demo records retain their explicit fictional origin.
const demo=A.sampleDemo();
assert.equal(demo.ok,true,demo.error);
const d=A.snapshot(demo.state);
assert.equal(d.ok,true,d.error);
assert.equal(d.demo,true);
assert.equal(d.accounts.every(a=>a.recent.every(x=>x.origin==="demo")),true);
assert.equal(d.connected,false);
assert.equal(d.persisted,false);
console.log("Banking M4m: latest-3/full-12 read-only history, count disclosure, transfers, correction/removal, 300-entry cap and fictional demo PASS");
