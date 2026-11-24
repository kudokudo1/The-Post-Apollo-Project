import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
function section(a,b) {
    const start=qml.indexOf(a),end=qml.indexOf(b,start+a.length);
    assert.ok(start>=0&&end>start,a+" / "+b);
    return qml.slice(start,end);
}
const bottom=section('objectName: "marketDayRangeRail"',"Flickable {");
assert.ok(bottom.includes("anchors.bottom: parent.bottom"));
assert.ok(bottom.includes("anchors.bottom: modeControls.top"));
assert.ok(bottom.includes("anchors.bottomMargin: visible ? 4 : 0"));
assert.ok(bottom.includes('visible: !stocks.dayMode'));
for(const label of ["DAY","RANGE","PRICE / INTERVALS","CROSS-STOCK"])
    assert.ok(bottom.includes('label: "'+label+'"'));
for(const label of ["GLOBAL SEARCH","CONTROLS","QUOTA STATUS","LOAD RANGE"])
    assert.ok(!bottom.includes('label: "'+label+'"'));
const viewport=section("Flickable {","id: body");
assert.ok(viewport.includes("anchors.top: stockCommandRail.bottom"));
assert.ok(viewport.includes("anchors.bottom: researchRail.top"));
assert.ok(viewport.includes("clip: true"));
const disclosure=section('objectName: "marketResearchControlsSection"','objectName: "marketCompactSelection"');
for(const token of ["visible: stocks.controlsExpanded","height: visible ? implicitHeight : 0",
    "id: issuers","id: rangePresets","id: dateControls",'label: "QUOTA STATUS"'])
    assert.ok(disclosure.includes(token),token);
assert.equal(disclosure.split("FinanceDateInput {").length-1,3);
assert.ok(!disclosure.includes("stockFeed.refresh()"));
const always=section('objectName: "marketCompactSelection"','objectName: "marketResearchCrossStockSection"');
for(const token of ["id: load",'stocks.stockFeed.refresh()',"id: status","stocks.stockFeed.message",
    "!stocks.controlsExpanded","stocks.historySource"])
    assert.ok(always.includes(token),token);
assert.ok(qml.includes("property bool controlsExpanded: false"));
const f=section("function toggleResearchControls() {","function selectResearchView(view) {").trim();
const ctx={controlsExpanded:false,scroll:{contentY:123}};
vm.createContext(ctx);vm.runInContext(f,ctx);
ctx.toggleResearchControls();
assert.equal(ctx.controlsExpanded,true);assert.equal(ctx.scroll.contentY,0);
ctx.scroll.contentY=45;ctx.toggleResearchControls();
assert.equal(ctx.controlsExpanded,false);assert.equal(ctx.scroll.contentY,45);
for(const forbidden of ["stockFeed","snapshot","clearPinned","clearSaved","clearStock","SelectedStep","researchView","fetch(","refresh("])
    assert.ok(!f.includes(forbidden),forbidden);
assert.ok(qml.includes('label: stocks.controlsExpanded ? "HIDE CONTROLS" : "CONTROLS"'));
assert.ok(qml.includes('visible: !!stocks.snapshot && stocks.controlsExpanded'));
assert.ok(qml.includes("stocks.rangeAnalysis !== null && stocks.controlsExpanded"));
console.log("Finance Market M42 fixed bottom mode rails, compact disclosure, reachable load and no data side effects: PASS");
