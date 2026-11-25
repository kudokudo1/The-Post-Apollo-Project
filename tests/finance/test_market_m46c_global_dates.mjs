import assert from "node:assert/strict";
import vm from "node:vm";
import {readFileSync} from "node:fs";
const read=p=>readFileSync(new URL("../../"+p,import.meta.url),"utf8");
const policy=vm.runInNewContext(read("widgets/FinanceStockModePolicy.js")+"\n({selectWindow,presetWindow,loadedGlobalDay})");
for(const [name,offset,guard] of [["FinanceGlobalPriceService.qml","dateOffset","freeAttemptAllowed"],["FinanceAlphaVantageFreeService.qml","dayOffset","availableCall"]]){
 const source=read("services/finance/"+name);
 const slice=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)+a.length));
 const funcs=slice("function applyDates(",offset==="dateOffset"?"function dateOffset(":"function loadHistory(")+slice("function loadHistory()","function validDate(");
 let reservations=0,commands=[];
 const ctx={StockModePolicy:policy,monitoring:true,loading:false,reader:{running:false,exec:argv=>commands.push(argv)},
 identity:{figi:"BBG000000001"},selectedListing:{symbol:"ASML.AS",currency:"EUR"},state:"selected",snapshot:{},presetDays:30,startDate:"2026-10-28",endDate:"2026-11-25",requestsThisRuntime:0,
 requestedOp:"",requestedIdentity:"",requestedSymbol:"",requestedCurrency:"",requestedFrom:"",requestedTo:"",sharedQuota:null,message:"",
 Quickshell:{shellPath:p=>p},validDate:d=>/^\d{4}-\d{2}-\d{2}$/.test(d),[offset]:()=> "2026-11-25",[guard]:()=>{reservations++;return true;}};
 vm.createContext(ctx);vm.runInContext(funcs,ctx);
 assert.equal(ctx.selectStartDate("2026-11-15"),true);
 assert.equal(ctx.selectEndDate("2026-11-12"),true);
 assert.equal(ctx.loadHistory(),false);assert.equal(reservations,0);assert.equal(commands.length,0);
 assert.equal(ctx.selectEndDate("2026-11-20"),true);
 assert.equal(ctx.loadHistory(),true);assert.equal(reservations,1);
 assert.deepEqual(Array.from(commands[0]).slice(-2),["2026-11-15","2026-11-20"]);
 ctx.state="selected";assert.equal(ctx.selectSingleDate("2026-11-03"),true);
 assert.equal(ctx.loadHistory(),true);assert.deepEqual(Array.from(commands[1]).slice(-2),["2026-11-03","2026-11-03"]);
 ctx.state="selected";assert.equal(ctx.selectPreset(7),true);assert.equal(ctx.startDate,"2026-11-19");
 ctx.loading=true;assert.equal(ctx.selectStartDate("2026-11-20"),false);
 ctx.loading=false;ctx.state="selected";ctx.startDate="2026-01-01";assert.equal(ctx.loadHistory(),false);assert.equal(reservations,2);
}
const empty={source:"alpha-vantage-daily-compact",readOnly:true,identityVerified:false,from:"2026-11-01",to:"2026-11-01",bars:[]};
assert.equal(policy.loadedGlobalDay({...empty,compactMayBeTruncated:true},empty.from).state,"unavailable");
assert.equal(policy.loadedGlobalDay({...empty,compactMayBeTruncated:false},empty.from).state,"no-session");
console.log("M46c exact worldwide date windows, invalid no-spend and compact DAY uncertainty: PASS");
