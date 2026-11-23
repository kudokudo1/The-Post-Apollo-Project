import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
function load(name) {
    const s=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+name,import.meta.url),"utf8"),s);
    return s;
}
const A=load("FinanceBankingAccountsPolicy.js");
const P=load("FinanceBankingProviderPolicy.js");
const J=load("FinanceBankingSessionJournalPolicy.js");
let state=A.emptyState();
function addAccount(providerId,productId,nickname,openingText){
    const r=A.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.account.id;
}
function addEntry(accountId,description,amountText="1.00"){
    const r=A.addEntry(state,{accountId,date:"2026-11-23",description,
       direction:"in",amountText});assert.equal(r.ok,true,r.error);state=r.state;
}
const cash=addAccount("cashapp","cash-balance","Cash","100.00");
const chime=addAccount("chime","chime-checking","Checking","200.00");
const bank=addAccount("bank","bank-checking","Extra","");
const basic={fromAccountId:cash,toAccountId:chime,date:"2026-11-23",
    amountText:"20.00",description:"Home savings move"};
const before=JSON.stringify(state);
const first=A.addManualTransfer(state,basic);
assert.equal(first.ok,true,first.error);
state=first.state;
assert.equal(state.mode,"manual");
assert.equal(state.entries.length,2);
assert.equal(state.entries[0].accountId,cash);
assert.equal(state.entries[1].accountId,chime);
assert.equal(state.entries[0].amountCents,-2000);
assert.equal(state.entries[1].amountCents,2000);
assert.equal(state.entries[0].transferId,state.entries[1].transferId);
assert.equal(state.entries[0].transferSide,"out");
assert.equal(state.entries[1].transferSide,"in");
assert.equal(state.entries[0].description,state.entries[1].description);
assert.equal(state.entries[1].id,"entry-5");
assert.equal(state.nextId,6);
assert.equal(A.validState(state),true);
const snap=A.snapshot(state);
assert.equal(snap.ok,true);
assert.equal(snap.knownBalanceSubtotalCents,30000);
assert.equal(snap.accounts.find(a=>a.id===cash).balanceCents,8000);
assert.equal(snap.accounts.find(a=>a.id===chime).balanceCents,22000);
assert.equal(snap.accounts.find(a=>a.id===bank).balanceCents,null);
assert.equal(snap.combinedBalanceCents,null,"Unknown opening should remain unknown");
const transfer=A.transferPairs(state);
assert.equal(transfer.ok,true);
assert.equal(transfer.rows.length,1);
const pair=transfer.rows[0];
assert.equal(pair.fromAccountId,cash);
assert.equal(pair.toAccountId,chime);
assert.equal(pair.fromLabel,"Cash");
assert.equal(pair.toLabel,"Checking");
assert.equal(pair.date,basic.date);
assert.equal(pair.amountCents,2000);
assert.equal(pair.description,basic.description);
assert.equal(pair.transferId,first.transfer.transferId);
assert.equal(transfer.connected,false);
assert.equal(transfer.persisted,false);
const chimeView=P.build("chime",A.snapshot(state),"activity");
const cashView=P.build("cashapp",A.snapshot(state),"activity");
const chimeJournal=J.project(chimeView,state,{});
const cashJournal=J.project(cashView,state,{});
assert.equal(chimeJournal.ok,true,chimeJournal.error);
assert.equal(cashJournal.ok,true,cashJournal.error);
assert.equal(chimeJournal.rows.length,1);
assert.equal(cashJournal.rows.length,1);
assert.equal(chimeJournal.rows[0].transferId,pair.transferId);
assert.equal(chimeJournal.rows[0].transferSide,"in");
assert.equal(cashJournal.rows[0].transferSide,"out");
assert.equal(chimeJournal.rows[0].amountCents,2000);
assert.equal(cashJournal.rows[0].amountCents,-2000);
assert.equal(J.project(P.build("bank",A.snapshot(state),"activity"),state,{}).rows.length,0);
const e=state.entries[0],expected={entryId:e.id,accountId:e.accountId,
    expectedDate:e.date,expectedDescription:e.description,
    expectedAmountCents:e.amountCents};
assert.match(A.correctEntry(state,{...expected,date:e.date,description:"partial",
    direction:"out",amountText:"1.00"}).error,/PAIRED TRANSFER/);
assert.match(A.deleteEntry(state,expected).error,/PAIRED TRANSFER/);

// Any malformed pair must be rejected, both by M3 writer and read projection.
const modifications=[
    entries=>entries.slice(1),
    entries=>entries.map((e,i)=>i===0?{...e,amountCents:-1900}:e),
    entries=>entries.map((e,i)=>i===1?{...e,date:"2026-11-22"}:e),
    entries=>entries.map((e,i)=>i===1?{...e,description:"different"}:e),
    entries=>entries.map((e,i)=>i===1?{...e,transferSide:"out"}:e),
    entries=>entries.map((e,i)=>i===1?{...e,accountId:cash}:e),
    entries=>entries.map((e,i)=>i===1?{...e,transferId:"transfer-999"}:e),
    entries=>entries.map((e,i)=>i===0?{...e,transferSide:undefined}:e),
    entries=>entries.map((e,i)=>i===0?{...e,transferId:"transfer-foo"}:e),
];
for(const change of modifications) {
    const altered={...state,entries:change(state.entries)};
    assert.equal(A.validState(altered),false,JSON.stringify(altered.entries));
    assert.equal(A.addManualTransfer(altered,basic).ok,false);
    assert.equal(J.project(cashView,altered,{}).ok,false);
}
const stale={...pair,date:"2026-11-22"};
assert.equal(A.removeManualTransfer(state,stale).ok,false);
assert.equal(A.removeManualTransfer(state,{...pair,amountCents:2001}).ok,false);
assert.equal(A.removeManualTransfer(state,{...pair,toAccountId:bank}).ok,false);
assert.equal(A.removeManualTransfer(state,{...pair,transferId:"transfer-777"}).ok,false);
assert.equal(A.removeManualTransfer(state,null).ok,false);

// Check atomicity and input validation.
const snapshot=JSON.stringify(state);
for(const bad of [
    {...basic,fromAccountId:chime,toAccountId:chime},
    {...basic,fromAccountId:"acct-999"},
    {...basic,toAccountId:"acct-999"},
    {...basic,date:"2026-02-29"},
    {...basic,date:"2026-2-3"},
    {...basic,amountText:"0"},
    {...basic,amountText:"-10.00"},
    {...basic,amountText:"4.001"},
    {...basic,amountText:"10000000.00"},
    {...basic,description:"x".repeat(121)},
    {...basic,description:"\n"},
    {...basic,description:null}
]) {
    assert.equal(A.addManualTransfer(state,bad).ok,false,JSON.stringify(bad));
    assert.equal(JSON.stringify(state),snapshot,"Failed transfer must not mutate source");
}
assert.equal(A.addManualTransfer(A.emptyState(),basic).ok,false);
assert.equal(A.addManualTransfer(A.sampleDemo().state,basic).ok,false);

// Removing a pair leaves previous and subsequent ordinary entries untouched.
addEntry(bank,"Unrelated manual deposit");
const olderCount=state.entries.length,oldNextId=state.nextId;
const removed=A.removeManualTransfer(state,pair);
assert.equal(removed.ok,true,removed.error);
state=removed.state;
assert.equal(state.entries.length,olderCount-2);
assert.equal(state.entries[0].description,"Unrelated manual deposit");
assert.equal(state.nextId,oldNextId);
assert.equal(A.transferPairs(state).rows.length,0);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===cash).balanceCents,10000);
assert.equal(A.snapshot(state).accounts.find(a=>a.id===chime).balanceCents,20000);
assert.equal(A.removeManualTransfer(state,pair).ok,false);
const created=A.addManualTransfer(state,{...basic,amountText:"5.00",description:""});
assert.equal(created.ok,true,created.error);
assert.equal(created.state.entries[1].description,"MANUAL TRANSFER");
assert.equal(created.state.entries[1].transferSide,"out");
assert.equal(created.state.entries[1].id,"entry-"+oldNextId);
state=created.state;
assert.notEqual(state.entries[1].id,e.id,"Removed entry ID cannot be reused");
const rollback=A.undoLastEntry(state);
assert.equal(rollback.ok,true,rollback.error);
assert.equal(rollback.state.entries.length,state.entries.length-2);
assert.equal(A.transferPairs(rollback.state).rows.length,0);

// 299 entries cannot fit both sides; 298 can.
let full=A.emptyState(),id0,id1;
let x=A.addAccount(full,{providerId:"bank",productId:"bank-checking",nickname:"From",openingText:""});
assert.equal(x.ok,true);full=x.state;id0=x.account.id;
x=A.addAccount(full,{providerId:"bank",productId:"bank-checking",nickname:"To",openingText:""});
assert.equal(x.ok,true);full=x.state;id1=x.account.id;
for(let i=0;i<299;i++){
    const r=A.addEntry(full,{accountId:id0,date:"2026-11-23",
        description:"Entry "+i,direction:"in",amountText:"0.01"});
    assert.equal(r.ok,true,r.error);full=r.state;
}
const near={fromAccountId:id0,toAccountId:id1,date:"2026-11-23",
    amountText:"0.01",description:"Transfer"};
const beforeFull=JSON.stringify(full);
assert.equal(A.addManualTransfer(full,near).ok,false);
assert.equal(JSON.stringify(full),beforeFull);
const partly={...full,entries:full.entries.slice(0,-1)};
assert.equal(A.validState(partly),true);
const fit=A.addManualTransfer(partly,near);
assert.equal(fit.ok,true,fit.error);
assert.equal(fit.state.entries.length,300);
assert.equal(A.validState(fit.state),true);

// Date-range filters may show only one leg, but must keep its transfer label.
const ranged=J.project(P.build("cashapp",A.snapshot(first.state),"activity"),
   first.state,{fromDate:"2026-11-23",toDate:"2026-11-23",direction:"out"});
assert.equal(ranged.ok,true);
assert.equal(ranged.rows[0].transferSide,"out");
console.log("Banking M4i: atomic paired manual transfers, read-only account identity, single-leg refusal, consistency limits, demo isolation PASS");
