import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
const read=p=>readFileSync(new URL("../../"+p,import.meta.url),"utf8");
const q=read("widgets/FinanceStockHistoryPane.qml"),d=read("widgets/FinanceStockDiscoveryPane.qml"),e=read("widgets/FinanceGlobalPricePane.qml"),a=read("widgets/FinanceAlphaVantageFreePane.qml"),dates=read("widgets/FinanceMarketDateControls.qml");
assert.ok(q.includes("sessionActive: stocks.stocksSessionActive"));
assert.ok(q.includes("active: stocks.discoveryOpen && sessionActive"));
assert.ok(q.includes("readonly property bool stocksSessionActive: visible && sessionEnabled"));
for(const [source,id] of [[d,"discovery"],[e,"priceView"],[a,"avPane"]]){
 assert.ok(source.includes("property bool sessionActive: active"));
 assert.ok(source.includes("monitoring: "+id+".sessionActive"));
 assert.ok(source.includes("enabled: active"));
}
assert.ok(d.includes("sessionActive: discovery.sessionActive && discovery.priceOptionsOpen"));
assert.ok(e.includes("sessionActive: priceView.sessionActive && priceView.alphaOpen"));
assert.ok(d.includes("if (!sessionActive) priceOptionsOpen = false"));
assert.ok(e.includes("if (!sessionActive) alphaOpen=false"));
assert.ok(d.includes("if (!active) return;"));
assert.ok(!dates.includes("onVisibleChanged:"));
assert.ok(dates.includes("onSelectedListingChanged()"));
for(const path of ["FinanceStockDiscoveryService.qml","FinanceGlobalPriceService.qml","FinanceAlphaVantageFreeService.qml"]){
 const service=read("services/finance/"+path);
 assert.match(service,/onMonitoringChanged:\s*\{\s*if\s*\(!monitoring\)\s*clear\(\)/);
}
console.log("M46c2 presentation-only disclosure, scoped provider lifetime and DAY mode retention: PASS");
