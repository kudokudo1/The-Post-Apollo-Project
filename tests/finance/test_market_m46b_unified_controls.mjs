import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const read=p=>readFileSync(new URL("../../widgets/"+p,import.meta.url),"utf8");
const q=read("FinanceStockHistoryPane.qml"), d=read("FinanceStockDiscoveryPane.qml");
const p=vm.runInNewContext(read("FinanceStockModePolicy.js")+"\n({loadedGlobalDay})");
const bars=[{date:"2026-11-02",price:101},{date:"2026-11-04",price:103}];
for(const source of ["eodhd-eod","alpha-vantage-daily-compact"]){
 const snapshot={source,readOnly:true,identityVerified:false,from:"2026-11-01",to:"2026-11-05",bars};
 assert.equal(p.loadedGlobalDay(snapshot,bars[0].date).close,101);
 assert.equal(p.loadedGlobalDay(snapshot,"2026-11-03").state,"invalid");
 assert.equal(p.loadedGlobalDay({...snapshot,bars:[bars[0],bars[0]]},bars[0].date).state,"invalid");
 assert.equal(p.loadedGlobalDay({...snapshot,identityVerified:true},bars[0].date).state,"invalid");
 assert.equal(p.loadedGlobalDay({...snapshot,bars:[{date:bars[0].date,price:-1}]},bars[0].date).state,"invalid");
}
const f=q.slice(q.indexOf("function openLoadedDay("),q.indexOf("readonly property string priceUnit"));
const ctx={globalHistoryActive:true,priceBars:bars,dayDate:""};
vm.createContext(ctx);vm.runInContext(f,ctx);
assert.equal(ctx.openLoadedDay(1),true);assert.equal(ctx.dayDate,bars[1].date);
assert.equal(ctx.openLoadedDay(-1),false);assert.equal(ctx.dayDate,bars[1].date);
ctx.returnToRange();assert.equal(ctx.dayDate,"");
assert.equal(ctx.priceBars,bars);
assert.ok(q.includes('property bool discoveryOpen: true'));
assert.ok(q.includes('label: "CONTROLS"'));
assert.ok(q.includes('readonly property var snapshot: globalHistory'));
assert.ok(q.includes('onQuotaRequested: stocks.openQuotaStatus()'));
assert.ok(d.includes('signal quotaRequested()'));
for(const old of ['StockModePolicy.stockItems()','stockFeed.refresh()','RETURN TO LEGACY STOCKS','label: "GLOBAL SEARCH"','stockFeed.selectIssuer(']) assert.ok(!q.includes(old),old);
console.log("M46b worldwide-only selection and actual loaded DAY/RANGE navigation: PASS");
