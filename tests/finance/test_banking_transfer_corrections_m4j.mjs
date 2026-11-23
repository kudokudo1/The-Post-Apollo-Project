import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
function load(path) {
    const s=vm.createContext({Date});
    vm.runInContext(readFileSync(new URL("../../widgets/"+path,import.meta.url),"utf8"),s);
    return s;
}
const Accounts=load("FinanceBankingAccountsPolicy.js");
const Provider=load("FinanceBankingProviderPolicy.js");
const Journal=load("FinanceBankingSessionJournalPolicy.js");
let state=Accounts.emptyState();
function account(providerId,productId,nickname,openingText) {
    const r=Accounts.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.account.id;
}
function transfer(fromAccountId,toAccountId,date,amountText,description) {
    const r=Accounts.addManualTransfer(state,{fromAccountId,toAccountId,
        date,amountText,description});
    assert.equal(r.ok,true,r.error);state=r.state;return r.transfer;
}
function journal(providerId,opts={}) {
    return Journal.project(Provider.build(providerId,Accounts.snapshot(state),"activity"),state,opts);
}
const cash=account("cashapp","cash-balance","Cash","200.00");
const chime=account("chime","chime-checking","Checking","300.00");
const paypal=account("paypal","paypal-wallet","Wallet","");
const first=transfer(cash,chime,"2026-11-20","20.00","First transfer");
const second=transfer(chime,paypal,"2026-11-21","5.00","Second transfer");
const unrelated=Accounts.addEntry(state,{
    accountId:cash,date:"2026-11-22",description:"Salary entered manually",
    direction:"in",amountText:"8.00"
});
assert.equal(unrelated.ok,true,unrelated.error);
state=unrelated.state;
const original=JSON.stringify(state),nextId=state.nextId;
const savedIds=state.entries.slice(0,2).map(e=>e.id);
const form={transferId:first.transferId,fromAccountId:cash,toAccountId:chime,
    expectedDate:first.date,expectedDescription:first.description,
    expectedAmountCents:first.amountCents};
const changed=Accounts.correctManualTransfer(state,{...form,
    date:"2026-11-18",description:"Edited transfer",
    amountText:"15.25"});
assert.equal(changed.ok,true,changed.error);
assert.equal(JSON.stringify(state),original,"Source state must remain unchanged");
state=changed.state;
assert.equal(Accounts.validState(state),true);
assert.equal(state.entries.length,5,"Both legs replaced in place, never appended");
assert.equal(state.nextId,nextId,"Correction may not recycle or allocate IDs");
assert.equal(state.entries[0].id,savedIds[0]);
assert.equal(state.entries[1].id,savedIds[1]);
assert.equal(state.entries[0].accountId,cash);
assert.equal(state.entries[1].accountId,chime);
assert.equal(state.entries[0].transferId,first.transferId);
assert.equal(state.entries[1].transferId,first.transferId);
assert.equal(state.entries[0].transferSide,"out");
assert.equal(state.entries[1].transferSide,"in");
assert.equal(state.entries[0].amountCents,-1525);
assert.equal(state.entries[1].amountCents,1525);
assert.equal(state.entries[0].date,"2026-11-18");
assert.equal(state.entries[1].date,"2026-11-18");
assert.equal(state.entries[0].description,"Edited transfer");
assert.equal(state.entries[1].description,"Edited transfer");
assert.equal(state.entries[2].transferId,second.transferId);
assert.equal(state.entries[2].amountCents,-500);
assert.equal(state.entries[3].amountCents,500);
assert.equal(state.entries[4].id,unrelated.entry.id);
assert.equal(state.entries[4].amountCents,800);
assert.equal(changed.corrected.transferId,first.transferId);
assert.equal(changed.corrected.amountCents,1525);
const view=Accounts.snapshot(state);
assert.equal(view.ok,true,view.error);
assert.equal(view.accounts.find(a=>a.id===cash).balanceCents,19275);
assert.equal(view.accounts.find(a=>a.id===chime).balanceCents,31025);
assert.equal(view.accounts.find(a=>a.id===paypal).balanceCents,null);
assert.equal(view.knownBalanceSubtotalCents,50300);
assert.equal(view.combinedBalanceCents,null);
const projected=journal("cashapp");
assert.equal(projected.ok,true,projected.error);
assert.equal(projected.matchedTransferOutCents,1525);
assert.equal(projected.matchedUnlinkedInCents,800);
assert.equal(projected.matchedNetCents,-725);
assert.equal(journal("cashapp",{toDate:"2026-11-19"}).matchedTransferOutCents,1525);
assert.equal(journal("cashapp",{fromDate:"2026-11-20"}).matchedTransferCount,0);
assert.equal(journal("chime").matchedTransferInCents,1525);
assert.equal(journal("chime").matchedTransferOutCents,500);
assert.equal(journal("paypal").matchedTransferInCents,500);

// Stale or forged originals must fail and never mutate the source.
const validSource=JSON.stringify(state);
function reject(fields) {
    const result=Accounts.correctManualTransfer(state,fields);
    assert.equal(result.ok,false,JSON.stringify(fields));
    assert.equal(JSON.stringify(state),validSource);
}
reject({...form,date:"2026-11-23",description:"stale",amountText:"2.00"});
reject({...form,fromAccountId:chime,date:"2026-11-23",description:"wrong",amountText:"2.00"});
reject({...form,toAccountId:paypal,date:"2026-11-23",description:"wrong",amountText:"2.00"});
reject({...form,transferId:second.transferId,date:"2026-11-23",description:"wrong",amountText:"2.00"});
reject({...form,expectedAmountCents:1525,date:"2026-11-23",description:"wrong",amountText:"2.00"});
reject({...form,expectedDescription:"Edited transfer",date:"2026-11-23",description:"wrong",amountText:"2.00"});
reject({...form,expectedDate:"2026-11-18",date:"2026-11-23",description:"wrong",amountText:"2.00"});
reject(null);
reject({});
reject({...form,transferId:"invalid",date:"2026-11-23",description:"bad",amountText:"1.00"});
const fresh={...form,expectedDate:"2026-11-18",
    expectedDescription:"Edited transfer",expectedAmountCents:1525};
for(const bad of [
    {date:"2026-02-29",description:"Attempt",amountText:"1.00"},
    {date:"2026-11-23",description:"Attempt",amountText:"0.00"},
    {date:"2026-11-23",description:"Attempt",amountText:"-1.00"},
    {date:"2026-11-23",description:"Attempt",amountText:"1.001"},
    {date:"2026-11-23",description:"\n",amountText:"1.00"},
    {date:"2026-11-23",description:"X".repeat(121),amountText:"1.00"},
    {date:"2026-11-23",description:null,amountText:"1.00"},
    {date:"2101-01-01",description:"Bad",amountText:"1.00"},
])reject({...fresh,...bad});
const correctedAgain=Accounts.correctManualTransfer(state,{...fresh,
    date:"2026-11-19",description:"",amountText:"16.00"});
assert.equal(correctedAgain.ok,true,correctedAgain.error);
state=correctedAgain.state;
assert.equal(state.entries[0].description,"MANUAL TRANSFER");
assert.equal(state.entries[1].description,"MANUAL TRANSFER");
assert.equal(state.entries[0].amountCents,-1600);
assert.equal(state.entries[1].amountCents,1600);
assert.equal(state.entries[0].date,"2026-11-19");
const currentPair=Accounts.transferPairs(state).rows.find(x=>x.transferId===first.transferId);
assert.equal(currentPair.fromAccountId,cash);
assert.equal(currentPair.toAccountId,chime);
assert.equal(currentPair.amountCents,1600);
assert.equal(Accounts.removeManualTransfer(state,currentPair).ok,true);
const removed=Accounts.removeManualTransfer(state,currentPair);
assert.equal(removed.ok,true,removed.error);
assert.equal(removed.state.entries.length,state.entries.length-2);
assert.equal(removed.state.entries.some(x=>x.transferId===first.transferId),false);
assert.equal(removed.state.nextId,state.nextId);

// A failed amount change exceeding a known account's allowed balance is atomic.
let capped=Accounts.emptyState();
let r=Accounts.addAccount(capped,{providerId:"bank",productId:"bank-checking",
    nickname:"At Max",openingText:"9999999.99"});
assert.equal(r.ok,true);capped=r.state;const maxId=r.account.id;
r=Accounts.addAccount(capped,{providerId:"bank",productId:"bank-checking",
    nickname:"Source",openingText:"100.00"});
assert.equal(r.ok,true);capped=r.state;const from=r.account.id;
r=Accounts.addManualTransfer(capped,{fromAccountId:from,toAccountId:maxId,
    date:"2026-11-23",description:"Small",amountText:"0.01"});
assert.equal(r.ok,false,"Known account at maximum must reject even one cent");
// Construct a valid transfer the other way, then attempt to correct it beyond cap.
r=Accounts.addManualTransfer(capped,{fromAccountId:maxId,toAccountId:from,
    date:"2026-11-23",description:"Small",amountText:"1.00"});
assert.equal(r.ok,true,r.error);capped=r.state;
const fullBefore=JSON.stringify(capped);
const raw=Accounts.transferPairs(capped).rows[0];
const over=Accounts.correctManualTransfer(capped,{
    transferId:raw.transferId,fromAccountId:raw.fromAccountId,
    toAccountId:raw.toAccountId,expectedDate:raw.date,
    expectedDescription:raw.description,expectedAmountCents:raw.amountCents,
    date:raw.date,description:"Will overflow source",
    amountText:"9999999.99"});
assert.equal(over.ok,false);
assert.equal(JSON.stringify(capped),fullBefore);

// Fully populated 300 entries must still correct in place, without growing.
let many=Accounts.emptyState();
r=Accounts.addAccount(many,{providerId:"bank",productId:"bank-checking",nickname:"A",openingText:"500.00"});
assert.equal(r.ok,true);many=r.state;const id1=r.account.id;
r=Accounts.addAccount(many,{providerId:"bank",productId:"bank-checking",nickname:"B",openingText:"500.00"});
assert.equal(r.ok,true);many=r.state;const id2=r.account.id;
r=Accounts.addManualTransfer(many,{fromAccountId:id1,toAccountId:id2,
    date:"2026-11-01",description:"First",amountText:"1.00"});
assert.equal(r.ok,true);many=r.state;const firstPair=r.transfer;
for(let i=0;i<298;i++) {
    r=Accounts.addEntry(many,{accountId:id1,date:"2026-11-23",
        description:"Regular "+i,direction:"in",amountText:"0.01"});
    assert.equal(r.ok,true,r.error);many=r.state;
}
assert.equal(many.entries.length,300);
const full=Accounts.correctManualTransfer(many,{
    transferId:firstPair.transferId,fromAccountId:id1,toAccountId:id2,
    expectedDate:firstPair.date,expectedDescription:firstPair.description,
    expectedAmountCents:firstPair.amountCents,
    date:"2026-11-02",description:"Full session edit",amountText:"2.00"});
assert.equal(full.ok,true,full.error);
assert.equal(full.state.entries.length,300);
assert.equal(full.state.nextId,many.nextId);
assert.equal(full.state.entries[0].id,many.entries[0].id);
assert.equal(full.state.entries[1].id,many.entries[1].id);
assert.equal(Accounts.validState(full.state),true);
assert.equal(Accounts.addManualTransfer(Accounts.sampleDemo().state,{fromAccountId:"demo-1",
    toAccountId:"demo-2",date:"2026-11-23",amountText:"1.00",description:"no"}).ok,false);
assert.equal(Accounts.correctManualTransfer(Accounts.sampleDemo().state,{
    transferId:firstPair.transferId,fromAccountId:id1,toAccountId:id2,
    expectedDate:firstPair.date,expectedDescription:firstPair.description,
    expectedAmountCents:firstPair.amountCents,date:"2026-11-23",
    description:"no",amountText:"1.00"}).ok,false);
console.log("Banking M4j: atomic correction of both manual transfer legs, immutable identities, stale refusal, known-balance overflow, 300-entry cap and demo protection PASS");
