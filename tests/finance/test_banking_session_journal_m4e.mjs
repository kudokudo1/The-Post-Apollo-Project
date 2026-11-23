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
function addAccount(state,providerId,productId,nickname,openingText) {
    const result=A.addAccount(state,{providerId,productId,nickname,openingText});
    assert.equal(result.ok,true,result.error);
    return [result.state,result.account.id];
}
function addEntry(state,accountId,date,description,direction,amountText){
    const result=A.addEntry(state,{accountId,date,description,direction,amountText});
    assert.equal(result.ok,true,result.error);
    return result.state;
}
let state=A.emptyState(),cash,chime,paypal;
[state,cash]=addAccount(state,"cashapp","cash-balance","My Cash","200.00");
[state,chime]=addAccount(state,"chime","chime-checking","Checking","100.00");
[state,paypal]=addAccount(state,"paypal","paypal-wallet","PayPal Wallet","15.00");
for(let i=0;i<90;i++){
    state=addEntry(state,i%3===0?cash:i%3===1?chime:paypal,
        "2026-11-22",i===3?"earliest target":"Record "+i,
        i%2?"in":"out","1.00");
}
const snap=A.snapshot(state);
const ca=P.build("cashapp",snap,"activity");
assert.equal(ca.ok,true);
assert.equal(ca.transactionCount,30);
assert.equal(ca.activity.length,12,"Legacy M4b preview stays bounded");
const full=J.project(ca,state,{});
assert.equal(full.ok,true,full.error);
assert.equal(full.totalMatches,30);
assert.equal(full.providerSessionCount,30);
assert.equal(full.sessionEntryCount,90);
assert.equal(full.rows.length,20);
assert.equal(full.pageCount,2);
assert.equal(full.pageIndex,0);
assert.equal(full.from,1);
assert.equal(full.to,20);
assert.equal(full.scope,"COMPLETE CURRENT MANUAL SESSION");
assert.equal(full.connected,false);
assert.equal(full.persisted,false);
assert.equal(full.rows[0].description,"Record 87");
assert.equal(full.rows.every(x=>x.accountId===cash),true);
assert.equal(full.rows.some(x=>x.description==="Record 89"),false,"PayPal excluded");
assert.equal(full.rows.some(x=>x.description==="Record 88"),false,"Chime excluded");
const page2=J.project(ca,state,{page:1});
assert.equal(page2.ok,true);
assert.equal(page2.rows.length,10);
assert.equal(page2.from,21);
assert.equal(page2.to,30);
assert.equal(page2.rows.some(x=>x.description==="earliest target"),true,
    "Full session search can reach records omitted from M4b recent preview");
const search=J.project(ca,state,{query:"EARLIEST TARGET"});
assert.equal(search.ok,true);
assert.equal(search.totalMatches,1);
assert.equal(search.rows[0].description,"earliest target");
assert.equal(J.project(ca,state,{query:"MY CASH"}).totalMatches,30);
assert.equal(J.project(ca,state,{direction:"in"}).totalMatches,15);
assert.equal(J.project(ca,state,{direction:"out"}).totalMatches,15);
assert.equal(J.project(ca,state,{accountId:chime}).ok,false);
assert.equal(J.project(ca,state,{accountId:paypal}).ok,false);
assert.equal(J.project(ca,state,{accountId:cash}).totalMatches,30);
assert.equal(J.project(ca,state,{page:500}).ok,false);
assert.equal(J.project(ca,state,{page:2}).pageIndex,1,"Outdated page clamps to last");
assert.equal(J.project(ca,state,{page:-1}).ok,false);
assert.equal(J.project(ca,state,{page:1.5}).ok,false);
assert.equal(J.project(ca,state,{direction:"transfer"}).ok,false);
assert.equal(J.project(ca,state,{query:"A".repeat(65)}).ok,false);
assert.equal(J.project(ca,state,{query:"\n"}).ok,false);
assert.equal(J.project(ca,state,{query:12}).ok,false);
assert.equal(J.project(P.build("cashapp",snap,"stocks"),state,{}).ok,false);
assert.equal(J.project(P.build("cashapp",snap,"home"),state,{}).ok,false);
assert.equal(J.project({...ca,connected:true},state,{}).ok,false);
assert.equal(J.project({...ca,persisted:true},state,{}).ok,false);
assert.equal(J.project({...ca,transactionCount:29},state,{}).ok,false);
assert.equal(J.project({...ca,dataLabel:"FICTIONAL DEMO"},state,{}).ok,false);
assert.equal(J.project(ca,{...state,entries:state.entries.concat(state.entries[0])},{}).ok,false);
assert.equal(J.project(ca,{...state,entries:state.entries.concat({id:"entry-600",
   accountId:cash,date:"2026-02-30",description:"Invalid",amountCents:100,origin:"manual"})},{}).ok,false);
assert.equal(J.project(ca,{...state,accounts:state.accounts.filter(a=>a.id!==cash)},{}).ok,false);
assert.equal(J.project({...ca,allAccounts:[]},state,{}).ok,false);
assert.equal(J.project(ca,{...state,mode:"demo"},{}).ok,false);
assert.equal(J.project(ca,null,{}).ok,false);
assert.equal(J.project(null,state,{}).ok,false);
const before=JSON.stringify(state);
J.project(ca,state,{direction:"out",query:"Record",page:1});
assert.equal(JSON.stringify(state),before,"Read-only journal must not mutate M3 session");

// Full M3 cap: 300 rows; every page is at most 20, and there are exactly 15.
let many=A.emptyState(),id;
[many,id]=addAccount(many,"chime","chime-checking","Long Session","1000.00");
for(let i=0;i<300;i++) {
    many=addEntry(many,id,"2026-11-22","Item "+i,"out","0.01");
}
const ch=P.build("chime",A.snapshot(many),"activity");
assert.equal(ch.activity.length,12);
const p14=J.project(ch,many,{page:14});
assert.equal(p14.ok,true,p14.error);
assert.equal(p14.totalMatches,300);
assert.equal(p14.pageCount,15);
assert.equal(p14.rows.length,20);
assert.equal(p14.from,281);
assert.equal(p14.to,300);
assert.equal(p14.rows[19].description,"Item 0");
assert.equal(J.project(ch,many,{page:15}).pageIndex,14);
assert.equal(J.project(ch,many,{query:"Item 0"}).rows[0].description,"Item 0");

// Demo permits the full fictional journal, but remains clearly labeled and not writable.
const demo=A.sampleDemo();
assert.equal(demo.ok,true);
const ds=A.snapshot(demo.state);
const dc=P.build("chime",ds,"activity");
const dj=J.project(dc,demo.state,{});
assert.equal(dj.ok,true,dj.error);
assert.equal(dj.scope,"COMPLETE FICTIONAL DEMO SESSION");
assert.equal(dj.rows.length,1);
assert.equal(dj.rows[0].description,"FICTIONAL grocery purchase");
assert.equal(A.addEntry(demo.state,{accountId:"demo-2",date:"2026-11-23",
    description:"No demo edit",direction:"out",amountText:"1.00"}).ok,false);
const empty=A.emptyState();
const e=J.project(P.build("cashapp",A.snapshot(empty),"activity"),empty,{});
assert.equal(e.ok,true);
assert.equal(e.totalMatches,0);
assert.equal(e.pageCount,1);
assert.equal(e.from,0);
assert.equal(e.to,0);
assert.equal(e.rows.length,0);
console.log("Banking M4e: complete 300-entry manual session journal, 20/page, provider isolation, malformed data refusal and fictional demo PASS");
