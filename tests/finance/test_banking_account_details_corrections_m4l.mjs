import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const load=(path)=>{
    const s=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+path,import.meta.url),"utf8"),s);
    return s;
};
const A=load("FinanceBankingAccountsPolicy.js");
const P=load("FinanceBankingProviderPolicy.js");
const J=load("FinanceBankingSessionJournalPolicy.js");

let state=A.emptyState();
function add(providerId,productId,nickname,openingText) {
    const r=A.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);
    state=r.state;return r.account.id;
}
function original(id) {
    const a=state.accounts.find(x=>x.id===id);
    return {accountId:id,expectedProviderId:a.providerId,
        expectedProductId:a.productId,expectedNickname:a.nickname,
        expectedOpeningCents:a.openingCents};
}
function edit(id,nickname,openingText) {
    return A.correctAccountDetails(state,{...original(id),nickname,openingText});
}
const cash=add("cashapp","cash-balance","Cash Main","");
const check=add("chime","chime-checking","Checking","100.00");
const spare=add("chime","chime-savings","Spare","5.00");
const other=add("bank","bank-checking","Cash Main","0.00");
const pair=A.addManualTransfer(state,{fromAccountId:cash,toAccountId:check,
    date:"2026-11-20",description:"Transfer to checking",amountText:"20.00"});
assert.equal(pair.ok,true,pair.error);state=pair.state;
for(const f of [
    {accountId:cash,date:"2026-11-21",description:"Reimbursement",
        direction:"in",amountText:"10.00"},
    {accountId:check,date:"2026-11-22",description:"Payment",
        direction:"out",amountText:"2.00"}
]) {
    const r=A.addEntry(state,f);
    assert.equal(r.ok,true,r.error);state=r.state;
}
let snapshot=A.snapshot(state);
assert.equal(snapshot.ok,true);
assert.equal(snapshot.accounts.find(x=>x.id===cash).openingCents,null);
assert.equal(snapshot.accounts.find(x=>x.id===cash).balanceCents,null);
assert.equal(snapshot.accounts.find(x=>x.id===check).balanceCents,11800);
const oldState=JSON.stringify(state),oldNextId=state.nextId;
const priorIds=state.entries.map(x=>x.id);
const priorPairs=A.transferPairs(state).rows.map(x=>x.transferId);
const r1=edit(cash,"Primary Wallet","50.00");
assert.equal(r1.ok,true,r1.error);
assert.equal(JSON.stringify(state),oldState,"No mutation of source M3 state");
state=r1.state;
assert.equal(A.validState(state),true);
assert.equal(state.nextId,oldNextId);
assert.deepEqual(state.entries.map(x=>x.id),priorIds);
assert.deepEqual(A.transferPairs(state).rows.map(x=>x.transferId),priorPairs);
assert.equal(state.accounts.find(x=>x.id===cash).providerId,"cashapp");
assert.equal(state.accounts.find(x=>x.id===cash).productId,"cash-balance");
assert.equal(state.accounts.find(x=>x.id===cash).origin,"manual");
assert.equal(state.accounts.find(x=>x.id===cash).openingCents,5000);
assert.equal(state.accounts.find(x=>x.id===cash).nickname,"Primary Wallet");
assert.equal(r1.account.id,cash);
assert.equal(r1.account.openingCents,5000);
snapshot=A.snapshot(state);
assert.equal(snapshot.accounts.find(x=>x.id===cash).balanceCents,4000);
assert.equal(snapshot.accounts.find(x=>x.id===check).balanceCents,11800);
assert.equal(snapshot.accounts.find(x=>x.id===spare).balanceCents,500);
assert.equal(snapshot.accounts.find(x=>x.id===other).balanceCents,0);
assert.equal(snapshot.combinedBalanceCents,16300);
assert.equal(snapshot.transferPairCount,1);
assert.equal(snapshot.transferVolumeCents,2000);
assert.equal(snapshot.unlinkedInCents,1000);
assert.equal(snapshot.unlinkedOutCents,200);
const view=P.build("cashapp",snapshot,"activity");
assert.equal(view.ok,true,view.error);
const journal=J.project(view,state,{});
assert.equal(journal.ok,true,journal.error);
assert.equal(journal.accountBreakdown[0].accountNickname,"Primary Wallet");
assert.equal(journal.rows.every(x=>x.accountNickname==="Primary Wallet"),true);
assert.equal(journal.matchedTransferOutCents,2000);
assert.equal(journal.matchedUnlinkedInCents,1000);

// Stale editor, bad identity, nickname collision and invalid opening amounts
// must all refuse without mutating any existing transaction or account.
const unchanged=JSON.stringify(state);
const staleOriginal={accountId:cash,expectedProviderId:"cashapp",
    expectedProductId:"cash-balance",
    expectedNickname:"Cash Main",expectedOpeningCents:null};
const fields={...original(cash),nickname:"Renamed",openingText:"60.00"};
for(const bad of [
    {...fields,expectedNickname:"Cash Main"},
    {...fields,expectedOpeningCents:null},
    {...fields,expectedProductId:"chime-checking"},
    {...fields,expectedProviderId:"paypal"},
    {...fields,accountId:check},
    {...fields,accountId:"acct-999"},
    {...fields,nickname:""},
    {...fields,nickname:" \t "},
    {...fields,nickname:"x".repeat(43)},
    {...fields,nickname:"Line\nBreak"},
    {...fields,openingText:null},
    {...fields,openingText:"12.345"},
    {...fields,openingText:"$10"},
    {...fields,openingText:"-0.001"},
    {...fields,openingText:"99999999.00"},
    null,{}
]) {
    const res=A.correctAccountDetails(state,bad);
    assert.equal(res.ok,false,JSON.stringify(bad));
    assert.equal(JSON.stringify(state),unchanged,"Rejected edit must leave session unchanged");
}
assert.equal(A.correctAccountDetails(state,{...original(check),
    nickname:"SPARE",openingText:"100.00"}).ok,false,
    "Same-provider nicknames must be unique, ignoring case");
assert.equal(A.correctAccountDetails(state,{...original(check),
    nickname:"Primary Wallet",openingText:"100.00"}).ok,true,
    "Same nickname in DIFFERENT providers must be allowed");
assert.equal(A.correctAccountDetails(state,{...original(cash),
    nickname:"Primary Wallet",openingText:"50.00"}).ok,true,
    "No-op correction must remain permitted");
// Never permit fake prior data to replace the real target.
assert.equal(A.correctAccountDetails(state,{...staleOriginal,
    nickname:"Counterfeit",openingText:"10.00"}).ok,false);

// Zero and unknown are different; neither is an external balance.
const zero=A.correctAccountDetails(state,{...original(cash),
    nickname:"Primary Wallet",openingText:"0.00"});
assert.equal(zero.ok,true,zero.error);
state=zero.state;
assert.equal(state.accounts.find(x=>x.id===cash).openingCents,0);
assert.equal(A.snapshot(state).accounts.find(x=>x.id===cash).balanceCents,-1000);
const unknown=A.correctAccountDetails(state,{...original(cash),
    nickname:"Primary Wallet",openingText:""});
assert.equal(unknown.ok,true,unknown.error);state=unknown.state;
assert.equal(A.snapshot(state).accounts.find(x=>x.id===cash).openingCents,null);
assert.equal(A.snapshot(state).accounts.find(x=>x.id===cash).balanceCents,null);
assert.equal(A.snapshot(state).combinedBalanceCents,null);
assert.equal(A.snapshot(state).unknownBalanceCount,1);
const negative=A.correctAccountDetails(state,{...original(cash),
    nickname:"Primary Wallet",openingText:"-25.50"});
assert.equal(negative.ok,true,negative.error);
state=negative.state;
assert.equal(A.snapshot(state).accounts.find(x=>x.id===cash).balanceCents,-3550);

// Correction must fail if new opening + existing activity exceeds per-account cap.
let capped=A.emptyState();
let z=A.addAccount(capped,{providerId:"bank",productId:"bank-checking",
    nickname:"Maximum",openingText:"9999999.98"});
assert.equal(z.ok,true);capped=z.state;
z=A.addEntry(capped,{accountId:z.account.id,date:"2026-11-23",
    description:"One cent",direction:"in",amountText:"0.01"});
assert.equal(z.ok,true,z.error);capped=z.state;
const capOriginal=JSON.stringify(capped);
const a=capped.accounts[0];
const tooHigh=A.correctAccountDetails(capped,{
    accountId:a.id,expectedProviderId:a.providerId,
    expectedProductId:a.productId,expectedNickname:a.nickname,
    expectedOpeningCents:a.openingCents,nickname:"Maximum",
    openingText:"9999999.99"});
assert.equal(tooHigh.ok,false);
assert.equal(JSON.stringify(capped),capOriginal);

// A complete 12-account, 300-entry manual session can update a nickname
// and opening amount in place without dropping history or changing nextId.
let full=A.emptyState();
for(let i=0;i<12;i++) {
    const z=A.addAccount(full,{providerId:"bank",
        productId:i%2?"bank-savings":"bank-checking",
        nickname:"Account "+i,openingText:""});
    assert.equal(z.ok,true,z.error);full=z.state;
}
const fullId=full.accounts[0].id;
for(let i=0;i<300;i++) {
    const z=A.addEntry(full,{accountId:fullId,date:"2026-11-23",
        description:"Item "+i,direction:"in",amountText:"0.01"});
    assert.equal(z.ok,true,z.error);full=z.state;
}
assert.equal(full.entries.length,300);
const originalFull=JSON.stringify(full),fullNext=full.nextId;
z=A.correctAccountDetails(full,{
    accountId:fullId,expectedProviderId:"bank",
    expectedProductId:"bank-checking",expectedNickname:"Account 0",
    expectedOpeningCents:null,nickname:"Corrected Large",
    openingText:"10.00"});
assert.equal(z.ok,true,z.error);
assert.equal(z.state.entries.length,300);
assert.equal(z.state.nextId,fullNext);
assert.equal(z.state.accounts[0].nickname,"Corrected Large");
assert.equal(A.snapshot(z.state).accounts[0].balanceCents,1300);
assert.equal(JSON.stringify(full),originalFull);

// Demo and empty sessions cannot be edited, and account ownership never changes.
const demo=A.sampleDemo();
assert.equal(demo.ok,true);
const d=demo.state.accounts[0];
assert.equal(A.correctAccountDetails(demo.state,{
    accountId:d.id,expectedProviderId:d.providerId,
    expectedProductId:d.productId,expectedNickname:d.nickname,
    expectedOpeningCents:d.openingCents,nickname:"Unsafe",
    openingText:"1.00"}).ok,false);
assert.equal(A.correctAccountDetails(A.emptyState(),fields).ok,false);
console.log("Banking M4l: account label/opening correction, stale/refused writes, unknown versus zero, transfer continuity, provider isolation, 300 entries and demo refusal PASS");
