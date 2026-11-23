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
function account(providerId,productId,nickname) {
    const r=A.addAccount(state,{providerId,productId,nickname,openingText:"100.00"});
    assert.equal(r.ok,true,r.error);
    state=r.state;return r.account.id;
}
function transfer(fromAccountId,toAccountId,date,amountText,description) {
    const r=A.addManualTransfer(state,{fromAccountId,toAccountId,
        date,amountText,description});
    assert.equal(r.ok,true,r.error);
    state=r.state;return r.transfer;
}
function entry(accountId,date,description,direction,amountText) {
    const r=A.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(r.ok,true,r.error);state=r.state;
}
function view(providerId,filters={}) {
    return J.project(P.build(providerId,A.snapshot(state),"activity"),state,filters);
}
function check(result,expect) {
    assert.equal(result.ok,true,result.error);
    for(const [key,value] of Object.entries(expect))
        assert.equal(result[key],value,key);
    const b=result.accountBreakdown;
    for(const metric of ["Count","InCents","OutCents"]) {
        const itemKey="transfer"+metric;
        const topKey="matchedTransfer"+metric;
        assert.equal(b.reduce((sum,row)=>sum+row[itemKey],0),result[topKey],
            "Per-account declared transfer reconciliation "+metric);
        assert.equal(b.reduce((sum,row)=>sum+row["unlinked"+metric],0),
            result["matchedUnlinked"+metric],
            "Per-account unlinked reconciliation "+metric);
    }
    assert.equal(result.matchedTransferCount+result.matchedUnlinkedCount,
        result.totalMatches);
    assert.equal(result.matchedTransferInCents+result.matchedUnlinkedInCents,
        result.matchedInCents);
    assert.equal(result.matchedTransferOutCents+result.matchedUnlinkedOutCents,
        result.matchedOutCents);
    return result;
}
const cash=account("cashapp","cash-balance","Cash Main");
const reserve=account("cashapp","cash-balance","Cash Reserve");
const checking=account("chime","chime-checking","Chime Checking");
const p1=transfer(cash,checking,"2026-11-21","20.00","To Chime");
const p2=transfer(reserve,cash,"2026-11-22","7.00","Reserve cash move");
entry(cash,"2026-11-23","Salary entered manually","in","5.00");
entry(checking,"2026-11-23","Store payment","out","3.00");
const before=JSON.stringify(state);
const cashAll=check(view("cashapp"),{
    totalMatches:4,matchedInCents:1200,matchedOutCents:2700,
    matchedNetCents:-1500,matchedTransferCount:3,
    matchedTransferInCents:700,matchedTransferOutCents:2700,
    matchedTransferNetCents:-2000,
    matchedUnlinkedCount:1,matchedUnlinkedInCents:500,
    matchedUnlinkedOutCents:0
});
assert.equal(cashAll.accountBreakdown.length,2);
assert.equal(cashAll.accountBreakdown[0].accountId,cash);
assert.equal(cashAll.accountBreakdown[0].matchedCount,3);
assert.equal(cashAll.accountBreakdown[0].transferCount,2);
assert.equal(cashAll.accountBreakdown[0].unlinkedCount,1);
assert.equal(cashAll.accountBreakdown[0].transferInCents,700);
assert.equal(cashAll.accountBreakdown[0].transferOutCents,2000);
assert.equal(cashAll.accountBreakdown[0].unlinkedInCents,500);
assert.equal(cashAll.accountBreakdown[1].accountId,reserve);
assert.equal(cashAll.accountBreakdown[1].transferOutCents,700);
assert.equal(cashAll.accountBreakdown[1].unlinkedCount,0);
const chimeAll=check(view("chime"),{
    totalMatches:2,matchedInCents:2000,matchedOutCents:300,
    matchedTransferCount:1,matchedTransferInCents:2000,
    matchedTransferOutCents:0,matchedUnlinkedCount:1,
    matchedUnlinkedInCents:0,matchedUnlinkedOutCents:300
});
assert.equal(chimeAll.rows.some(x=>x.transferId===p2.transferId),false,
    "No other provider's transfer row can enter Chime");
assert.equal(view("paypal").matchedTransferCount,0);
assert.equal(view("bank").matchedUnlinkedCount,0);
const cashSingle=check(view("cashapp",{accountId:cash}),{
    totalMatches:3,matchedTransferCount:2,matchedUnlinkedCount:1,
    matchedTransferInCents:700,matchedTransferOutCents:2000
});
assert.equal(cashSingle.accountBreakdown.length,1);
check(view("cashapp",{direction:"out"}),{
    totalMatches:2,matchedTransferCount:2,matchedTransferInCents:0,
    matchedTransferOutCents:2700,matchedUnlinkedCount:0
});
check(view("cashapp",{direction:"in"}),{
    totalMatches:2,matchedTransferCount:1,matchedTransferInCents:700,
    matchedUnlinkedCount:1,matchedUnlinkedInCents:500
});
check(view("cashapp",{fromDate:"2026-11-21",toDate:"2026-11-21"}),{
    totalMatches:1,matchedTransferCount:1,
    matchedTransferOutCents:2000,matchedUnlinkedCount:0
});
check(view("cashapp",{query:"salary"}),{
    totalMatches:1,matchedTransferCount:0,matchedUnlinkedCount:1,
    matchedUnlinkedInCents:500
});
check(view("cashapp",{query:"NO SUCH ENTRY"}),{
    totalMatches:0,matchedTransferCount:0,matchedUnlinkedCount:0,
    matchedTransferInCents:0,matchedUnlinkedInCents:0,
    matchedOutCents:0
});
assert.equal(view("cashapp",{accountId:checking}).ok,false,
    "Selected account must belong to viewed provider");
assert.equal(JSON.stringify(state),before,"Projection never alters source session");

// Filtering by description alone does not promote ordinary entries to a
// verified transfer: classification must rely on validated transferId.
entry(cash,"2026-11-23","I wrote transfer in the memo","in","1.00");
const named=check(view("cashapp",{query:"transfer"}),{
    totalMatches:1,matchedTransferCount:0,matchedUnlinkedCount:1,
    matchedUnlinkedInCents:100
});
assert.equal(named.rows[0].transferId,"");

// Page totals are full-filter totals: no page should silently omit money.
for(let i=0;i<22;i++)
    entry(reserve,"2026-11-23","Unlinked "+i,"out","0.01");
const page0=view("cashapp",{page:0});
const page1=view("cashapp",{page:1});
assert.equal(page0.ok,true,page0.error);
assert.equal(page1.ok,true,page1.error);
assert.equal(page0.pageCount,2);
assert.equal(page0.rows.length,20);
assert.equal(page1.rows.length,7);
assert.equal(page0.matchedTransferInCents,page1.matchedTransferInCents);
assert.equal(page0.matchedTransferOutCents,page1.matchedTransferOutCents);
assert.equal(page0.matchedUnlinkedInCents,page1.matchedUnlinkedInCents);
assert.equal(page0.matchedUnlinkedOutCents,page1.matchedUnlinkedOutCents);
assert.equal(page1.matchedUnlinkedOutCents,22);
check(page1,{totalMatches:27,matchedTransferCount:3,matchedUnlinkedCount:24});
const remove=A.removeManualTransfer(state,{...p1,
    fromAccountId:cash,toAccountId:checking});
assert.equal(remove.ok,true,remove.error);
state=remove.state;
check(view("cashapp"),{
    matchedTransferCount:2,matchedTransferInCents:700,
    matchedTransferOutCents:700
});
check(view("chime"),{
    matchedTransferCount:0,matchedUnlinkedOutCents:300
});
assert.equal(A.validState(state),true);
assert.equal(A.removeManualTransfer(state,p1).ok,false);

// Fictional demo entries remain clearly unlinked and cannot be modified.
const demo=A.sampleDemo();
const dj=J.project(P.build("chime",A.snapshot(demo.state),"activity"),demo.state,{});
assert.equal(dj.ok,true,dj.error);
assert.equal(dj.scope,"COMPLETE FICTIONAL DEMO SESSION");
assert.equal(dj.matchedTransferCount,0);
assert.equal(dj.matchedUnlinkedCount,1);
assert.equal(dj.matchedUnlinkedOutCents,2645);
assert.equal(A.addManualTransfer(demo.state,{
    fromAccountId:"demo-1",toAccountId:"demo-2",
    date:"2026-11-23",amountText:"2.00",description:"No"
}).ok,false);
console.log("Banking M4i transfer-aware summaries: filtered provider/account/page totals reconcile, cross-provider legs, unlinked classification and demo refusal PASS");
