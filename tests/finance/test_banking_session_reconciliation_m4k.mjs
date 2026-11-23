import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const scope=vm.createContext({Date});
vm.runInContext(readFileSync(new URL("../../widgets/FinanceBankingAccountsPolicy.js",import.meta.url),"utf8"),scope);
const A=scope;
let state=A.emptyState();
function account(providerId,productId,nickname,openingText) {
    const r=A.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.account.id;
}
function pair(fromAccountId,toAccountId,amountText,description,date="2026-11-23") {
    const r=A.addManualTransfer(state,{fromAccountId,toAccountId,date,amountText,description});
    assert.equal(r.ok,true,r.error);state=r.state;return r.transfer;
}
function unlinked(accountId,direction,amountText,description) {
    const r=A.addEntry(state,{accountId,date:"2026-11-23",
        description,direction,amountText});
    assert.equal(r.ok,true,r.error);state=r.state;return r.entry;
}
function check(expect) {
    const out=A.snapshot(state);
    assert.equal(out.ok,true,out.error);
    for(const [field,value] of Object.entries(expect))
        assert.equal(out[field],value,field);
    assert.equal(out.transferLegCount,out.transferPairCount*2);
    assert.equal(out.transferInCents,out.transferOutCents);
    assert.equal(out.transferNetCents,0);
    assert.equal(out.transferVolumeCents,out.transferInCents);
    assert.equal(out.transferInCents+out.unlinkedInCents,out.inCents);
    assert.equal(out.transferOutCents+out.unlinkedOutCents,out.outCents);
    assert.equal(out.transferLegCount+out.unlinkedCount,out.transactionCount);
    assert.equal(out.unlinkedNetCents,out.inCents-out.outCents);
    assert.equal(out.movementScope,
        "ALL CURRENT MANUAL/DEMO SESSION ACCOUNTS // NOT VERIFIED INCOME OR SPENDING");
    assert.equal(out.connected,false);
    assert.equal(out.persisted,false);
    return out;
}
check({accountCount:0,transactionCount:0,transferPairCount:0,
    transferVolumeCents:0,unlinkedCount:0,unlinkedNetCents:0});
const cash=account("cashapp","cash-balance","Cash Main","100.00");
const reserve=account("cashapp","cash-balance","Cash Reserve","50.00");
const chime=account("chime","chime-checking","Checking","200.00");
const paypal=account("paypal","paypal-wallet","Unknown","");
check({accountCount:4,transactionCount:0,combinedBalanceCents:null,
    unknownBalanceCount:1,transferPairCount:0,unlinkedCount:0});
const p1=pair(cash,chime,"20.00","Cross provider");
const p2=pair(reserve,cash,"7.00","Same provider");
const p3=pair(chime,paypal,"4.00","Unknown endpoint");
unlinked(cash,"in","5.00","User entered money in");
unlinked(reserve,"out","3.00","User entered money out");
unlinked(paypal,"in","10.00","Unknown opening but known entry");
const before=JSON.stringify(state);
let out=check({accountCount:4,transactionCount:9,transferPairCount:3,
    transferLegCount:6,transferVolumeCents:3100,
    transferInCents:3100,transferOutCents:3100,
    transferNetCents:0,unlinkedCount:3,
    unlinkedInCents:1500,unlinkedOutCents:300,unlinkedNetCents:1200,
    inCents:4600,outCents:3400,
    unknownBalanceCount:1,combinedBalanceCents:null,
    knownBalanceSubtotalCents:34800});
assert.equal(JSON.stringify(state),before,"Read-only reconciliation cannot mutate session");
assert.equal(out.accounts.find(a=>a.id===cash).balanceCents,9200);
assert.equal(out.accounts.find(a=>a.id===reserve).balanceCents,4000);
assert.equal(out.accounts.find(a=>a.id===chime).balanceCents,21600);
assert.equal(out.accounts.find(a=>a.id===paypal).balanceCents,null);
const fixed=A.correctManualTransfer(state,{transferId:p1.transferId,
    fromAccountId:p1.fromAccountId,toAccountId:p1.toAccountId,
    expectedDate:p1.date,expectedDescription:p1.description,
    expectedAmountCents:p1.amountCents,
    date:"2026-11-22",description:"Adjusted",amountText:"15.00"});
assert.equal(fixed.ok,true,fixed.error);state=fixed.state;
check({transferPairCount:3,transferVolumeCents:2600,
    unlinkedCount:3,unlinkedNetCents:1200,inCents:4100,outCents:2900,
    knownBalanceSubtotalCents:34800});
assert.equal(A.removeManualTransfer(state,p1).ok,false,
    "Deleting an obsolete pair snapshot must refuse");
const pairNow=A.transferPairs(state).rows.find(x=>x.transferId===p1.transferId);
assert.equal(pairNow.amountCents,1500);
assert.equal(A.removeManualTransfer(state,pairNow).ok,true);
const p2Current=A.transferPairs(state).rows.find(x=>x.transferId===p2.transferId);
const removed=A.removeManualTransfer(state,p2Current);
assert.equal(removed.ok,true,removed.error);
state=removed.state;
check({transactionCount:7,transferPairCount:2,transferLegCount:4,
    transferVolumeCents:1900,unlinkedCount:3,
    unlinkedInCents:1500,unlinkedOutCents:300,unlinkedNetCents:1200,
    inCents:3400,outCents:2200});
const p3Current=A.transferPairs(state).rows.find(x=>x.transferId===p3.transferId);
assert.equal(p3Current.amountCents,400);

// Malformed pairs fail at the validator before any misleading summary is produced.
for(const bad of [
    {...state,entries:state.entries.filter(e=>e.transferId!==p3.transferId||e.transferSide==="out")},
    {...state,entries:state.entries.map(e=>e.transferId===p3.transferId&&e.transferSide==="in"
        ?{...e,amountCents:e.amountCents+1}:e)},
    {...state,entries:state.entries.map(e=>e.transferId===p3.transferId&&e.transferSide==="in"
        ?{...e,transferId:"transfer-999"}:e)},
])assert.equal(A.snapshot(bad).ok,false,"Incomplete/mismatched transfer must not be projected");

// Full 300-entry case with two linked legs + 298 unlinked entries.
let big=A.emptyState();
let r=A.addAccount(big,{providerId:"bank",productId:"bank-checking",
    nickname:"A",openingText:"100.00"});
assert.equal(r.ok,true);big=r.state;const from=r.account.id;
r=A.addAccount(big,{providerId:"bank",productId:"bank-savings",
    nickname:"B",openingText:"100.00"});
assert.equal(r.ok,true);big=r.state;const to=r.account.id;
r=A.addManualTransfer(big,{fromAccountId:from,toAccountId:to,
    date:"2026-11-23",amountText:"0.01",description:"Pair"});
assert.equal(r.ok,true,r.error);big=r.state;
for(let i=0;i<298;i++) {
    r=A.addEntry(big,{accountId:from,date:"2026-11-23",
        description:"Regular "+i,direction:i%2===0?"in":"out",
        amountText:"0.01"});
    assert.equal(r.ok,true,r.error);big=r.state;
}
assert.equal(big.entries.length,300);
const bigOut=A.snapshot(big);
assert.equal(bigOut.ok,true,bigOut.error);
assert.equal(bigOut.transferPairCount,1);
assert.equal(bigOut.transferLegCount,2);
assert.equal(bigOut.transferVolumeCents,1);
assert.equal(bigOut.unlinkedCount,298);
assert.equal(bigOut.unlinkedInCents,149);
assert.equal(bigOut.unlinkedOutCents,149);
assert.equal(bigOut.unlinkedNetCents,0);
assert.equal(bigOut.combinedBalanceCents,20000);
assert.equal(bigOut.transactionCount,300);

// Demo records are fictional and unlinked; do not claim real transfer authority.
const demo=A.sampleDemo();
assert.equal(demo.ok,true);
const d=A.snapshot(demo.state);
assert.equal(d.ok,true,d.error);
assert.equal(d.demo,true);
assert.equal(d.transferPairCount,0);
assert.equal(d.transferVolumeCents,0);
assert.equal(d.unlinkedCount,2);
assert.equal(d.unlinkedInCents,5200);
assert.equal(d.unlinkedOutCents,2645);
assert.equal(d.unlinkedNetCents,2555);
assert.equal(d.connected,false);
assert.equal(d.persisted,false);
console.log("Banking M4k: whole-session transfer volume, paired/unlinked movement reconciliation, unknown balances, correction/removal, 300 entries and demo PASS");
