import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const code=readFileSync(new URL("../../widgets/FinanceBankingAccountsPolicy.js",import.meta.url),"utf8");
const policy=vm.createContext({Date,Set});
vm.runInContext(code,policy);
const providerIds=policy.providers().map(p=>p.id);
assert.equal(JSON.stringify(providerIds),JSON.stringify(["cashapp","chime","paypal","bank"]));
assert.equal(policy.money(-100050),"-$1000.50");
assert.equal(policy.money(null),"UNKNOWN");
for(const [value,expected] of [["0",0],["0.00",0],["125.40",12540],["-125.40",-12540],
    ["9999999.99",999999999],["0.1",10]])assert.equal(policy.parseCents(value,true),expected,value);
for(const invalid of ["","$10","1,000","1.234","1e4","NaN","00.01","-99999999.99",
    "-0.001","Infinity","  ","1\n2"])assert.equal(policy.parseCents(invalid,true),null,invalid);
assert.equal(policy.parseCents("-1.00",false),null);
assert.equal(policy.dateValid("2026-11-22"),true);
for(const invalid of ["2026-02-29","2026-13-01","2026-00-01","2026-04-31","11/22/2026",
    "2026-11-00",""])assert.equal(policy.dateValid(invalid),false,invalid);

let state=policy.emptyState();
assert.equal(policy.validState(state),true);
let stats=policy.snapshot(state);
assert.equal(stats.ok,true);
assert.equal(stats.accountCount,0);
assert.equal(stats.combinedBalanceCents,null);
assert.equal(stats.connected,false);
assert.equal(stats.persisted,false);

function create(fields) {
    const res=policy.addAccount(state,fields);
    if(res.ok)state=res.state;
    return res;
}
let invalid=policy.addAccount(state,{providerId:"cashapp",productId:"chime-checking",
    nickname:"My Chime",openingText:"100.00"});
assert.equal(invalid.ok,false);
invalid=policy.addAccount(state,{providerId:"cashapp",productId:"cash-balance",
    nickname:"\n",openingText:"100.00"});
assert.equal(invalid.ok,false);
invalid=policy.addAccount(state,{providerId:"cashapp",productId:"cash-balance",
    nickname:"Wallet",openingText:"$100"});
assert.equal(invalid.ok,false);
let first=create({providerId:"cashapp",productId:"cash-balance",
    nickname:"Spending",openingText:""});
assert.equal(first.ok,true);
assert.equal(first.account.openingCents,null);
assert.equal(state.mode,"manual");
const cashId=first.account.id;
let second=create({providerId:"chime",productId:"chime-checking",
    nickname:"Checking",openingText:"1000.00"});
assert.equal(second.ok,true);
const chimeId=second.account.id;
assert.equal(state.accounts.length,2);
assert.equal(policy.addAccount(state,{providerId:"cashapp",productId:"cash-balance",
    nickname:"spending",openingText:"10.00"}).ok,false);
assert.equal(policy.addAccount(state,{providerId:"bank",productId:"bank-savings",
    nickname:"Savings",openingText:"0.00"}).ok,true);

stats=policy.snapshot(state);
assert.equal(stats.knownBalanceCount,1);
assert.equal(stats.unknownBalanceCount,1);
assert.equal(stats.knownBalanceSubtotalCents,100000);
assert.equal(stats.combinedBalanceCents,null,"Unknown balance must never become zero");
assert.equal(stats.accounts[0].balanceCents,null);
assert.equal(stats.accounts[1].balanceCents,100000);

function entry(fields) {
    const res=policy.addEntry(state,fields);
    if(res.ok)state=res.state;
    return res;
}
let tx=entry({accountId:chimeId,date:"2026-11-22",
    description:"Groceries",direction:"out",amountText:"34.65"});
assert.equal(tx.ok,true);
assert.equal(tx.entry.amountCents,-3465);
const firstEntryId=tx.entry.id;
tx=entry({accountId:cashId,date:"2026-11-22",
    description:"Received refund",direction:"in",amountText:"50.10"});
assert.equal(tx.ok,true);
assert.equal(tx.entry.amountCents,5010);
assert.equal(tx.entry.id!==firstEntryId,true);
stats=policy.snapshot(state);
assert.equal(stats.outCents,3465);
assert.equal(stats.inCents,5010);
assert.equal(stats.accounts[1].balanceCents,96535);
assert.equal(stats.accounts[0].balanceCents,null);
assert.equal(stats.accounts[0].netChangeCents,5010);
assert.equal(stats.accounts[1].recent[0].description,"Groceries");
assert.equal(stats.transactionCount,2);
assert.equal(stats.demo,false);
for(const fields of [
    {accountId:"ghost",date:"2026-11-22",description:"No",direction:"out",amountText:"2.00"},
    {accountId:cashId,date:"2026-02-30",description:"Wrong date",direction:"out",amountText:"2.00"},
    {accountId:cashId,date:"2026-11-22",description:"",direction:"out",amountText:"2.00"},
    {accountId:cashId,date:"2026-11-22",description:"Bad amount",direction:"out",amountText:"0.00"},
    {accountId:cashId,date:"2026-11-22",description:"Bad amount",direction:"out",amountText:"-12.00"},
    {accountId:cashId,date:"2026-11-22",description:"Bad direction",direction:"transfer",amountText:"12.00"},
])assert.equal(policy.addEntry(state,fields).ok,false,JSON.stringify(fields));
assert.equal(policy.removeEmptyAccount(state,cashId).ok,false,"Cannot silently drop activity");
assert.equal(policy.sampleDemo().ok,true);
assert.equal(policy.addAccount(state,{providerId:"bank",productId:"bank-checking",nickname:"Savings",openingText:"5"}).ok,true);

const oldNext=state.nextId;
const undone=policy.undoLastEntry(state);
assert.equal(undone.ok,true);
assert.equal(undone.undone.accountId,cashId);
state=undone.state;
assert.equal(state.nextId,oldNext,"IDs must not recycle after undo");
assert.equal(policy.snapshot(state).inCents,0);
assert.equal(policy.undoLastEntry(state).ok,true);
state=policy.undoLastEntry(state).state;
const removed=policy.removeEmptyAccount(state,cashId);
assert.equal(removed.ok,true);
state=removed.state;
assert.equal(policy.snapshot(state).unknownBalanceCount,0);
assert.equal(policy.snapshot(state).combinedBalanceCents,100000);
const removed2=policy.removeEmptyAccount(state,chimeId);
assert.equal(removed2.ok,true);
assert.equal(removed2.state.mode,"empty");
assert.equal(removed2.state.accounts.length,0);
assert.equal(policy.snapshot(removed2.state).combinedBalanceCents,null);

const demo=policy.sampleDemo();
assert.equal(demo.ok,true);
assert.equal(demo.state.mode,"demo");
assert.equal(policy.snapshot(demo.state).accountCount,3);
assert.equal(policy.snapshot(demo.state).transactionCount,2);
assert.equal(policy.snapshot(demo.state).demo,true);
assert.equal(policy.addAccount(demo.state,{providerId:"chime",productId:"chime-savings",
    nickname:"No",openingText:"1.00"}).ok,false);
assert.equal(policy.addEntry(demo.state,{accountId:"demo-1",date:"2026-11-22",
    description:"Must not",direction:"in",amountText:"1.00"}).ok,false);
assert.equal(policy.undoLastEntry(demo.state).ok,false);
assert.equal(policy.removeEmptyAccount(demo.state,"demo-3").ok,false);
assert.equal(policy.validState({...demo.state,mode:"manual"}),false);
assert.equal(policy.validState({...demo.state,accounts:demo.state.accounts.concat(demo.state.accounts[0])}),false);

let cap=policy.emptyState();
for(let i=0;i<12;i++) {
    let x=policy.addAccount(cap,{providerId:"bank",productId:"bank-checking",
        nickname:"A"+i,openingText:""});
    assert.equal(x.ok,true);
    cap=x.state;
}
assert.equal(policy.addAccount(cap,{providerId:"bank",productId:"bank-checking",
    nickname:"A12",openingText:""}).ok,false);
let capped=policy.emptyState();
capped=policy.addAccount(capped,{providerId:"bank",productId:"bank-checking",
    nickname:"Regular",openingText:"1000.00"}).state;
for(let i=0;i<300;i++){
    let x=policy.addEntry(capped,{accountId:capped.accounts[0].id,date:"2026-11-22",
        description:"Manual "+i,direction:"out",amountText:"0.01"});
    assert.equal(x.ok,true,i);
    capped=x.state;
}
assert.equal(policy.snapshot(capped).outCents,300);
assert.equal(policy.snapshot(capped).accounts[0].balanceCents,99700);
assert.equal(policy.addEntry(capped,{accountId:capped.accounts[0].id,date:"2026-11-22",
    description:"301",direction:"out",amountText:"0.01"}).ok,false);

let upper=policy.addAccount(policy.emptyState(),{providerId:"chime",
    productId:"chime-checking",nickname:"Max",openingText:"9999999.99"}).state;
assert.equal(policy.addEntry(upper,{accountId:upper.accounts[0].id,date:"2026-11-22",
    description:"Overflow",direction:"in",amountText:"0.01"}).ok,false);
assert.equal(policy.validState({...upper,entries:[{id:"entry-2",accountId:"acct-1",
    date:"2026-11-22",description:"Unsafe",amountCents:0,origin:"manual"}]}),false);
// Account caps apply per account, not to legitimate combined holdings.
let combined=policy.emptyState();
for(const nickname of ["Checking A","Checking B"]) {
    const res=policy.addAccount(combined,{providerId:"bank",productId:"bank-checking",
        nickname,openingText:"9999999.99"});
    assert.equal(res.ok,true);
    combined=res.state;
}
assert.equal(policy.snapshot(combined).ok,true);
assert.equal(policy.snapshot(combined).combinedBalanceCents,1999999998);

console.log("Banking M3: manual account identities, unknown balances, USD cents, activity, undo, caps and demo isolation PASS");
