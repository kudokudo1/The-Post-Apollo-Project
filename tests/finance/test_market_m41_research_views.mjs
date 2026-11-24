import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const qml=readFileSync(new URL("../../widgets/FinanceStockHistoryPane.qml",import.meta.url),"utf8");
function part(start,end) {
    const a=qml.indexOf(start),b=qml.indexOf(end,a+start.length);
    assert.ok(a>=0&&b>a,start+" / "+end);
    return qml.slice(a,b);
}
const rail=part('objectName: "marketResearchViewRail"',"Flickable {");
for(const token of ['visible: !stocks.dayMode','height: visible ? 29 : 0',
    'label: "PRICE / INTERVALS"','label: "CROSS-STOCK"',
    'stocks.selectResearchView("price")','stocks.selectResearchView("compare")',
    'width: Math.max(0,(researchRail.width-researchRail.spacing)/2)'])
    assert.ok(rail.includes(token),token);
assert.ok(qml.includes('property string researchView: "price"'));
assert.ok(qml.includes('anchors.top: researchRail.bottom'));
const selector=part('function selectResearchView(view) {','onVisibleChanged:');
const fn=selector.slice(0,selector.indexOf("\n    }")+6);
const ctx={researchView:"price",scroll:{contentY:100}};
vm.createContext(ctx);
vm.runInContext(fn,ctx);
ctx.selectResearchView("compare");
assert.equal(ctx.researchView,"compare");
assert.equal(ctx.scroll.contentY,0);
ctx.scroll.contentY=40;
ctx.selectResearchView("compare");
assert.equal(ctx.scroll.contentY,40);
ctx.selectResearchView("invalid");
assert.equal(ctx.researchView,"compare");
assert.equal(ctx.scroll.contentY,40);
ctx.selectResearchView("price");
assert.equal(ctx.researchView,"price");
assert.equal(ctx.scroll.contentY,0);
for(const forbidden of ["stockFeed","snapshot","clearPinned","clearSaved","clearStock","SelectedStep","fetch(","refresh(","Process {"])
    assert.ok(!fn.includes(forbidden),forbidden);
const cross=part('objectName: "marketResearchCrossStockSection"','objectName: "marketResearchPriceSection"');
const price=part('objectName: "marketResearchPriceSection"','text: "Historical closes are not live quotes');
assert.ok(cross.includes('visible: !stocks.dayMode && stocks.researchView === "compare"'));
assert.ok(price.includes('visible: stocks.dayMode || stocks.researchView === "price"'));
for(const section of [cross,price]) {
    assert.ok(section.includes('height: visible ? implicitHeight : 0'));
    assert.ok(!section.includes("Loader {"));
    assert.ok(!section.includes("Component.onDestruction"));
}
for(const token of ['label: "SAVE STOCK REF"','label: "CLEAR REF"',
    'objectName: "marketCrossStockComparison"','objectName: "marketCrossStockNormalizedChart"',
    'objectName: "marketCrossStockDateDetail"','objectName: "marketCrossStockLeadership"',
    'objectName: "marketCrossStockGapToggle"','objectName: "marketCrossStockGapChart"'])
    assert.ok(cross.includes(token)&&!price.includes(token),token);
for(const token of ['objectName: "marketRangeAnalysisPanel"','id: priceCanvas',
    'label: "PIN AS A"','label: "CLEAR PIN A"','label: "SAVE INTERVAL 1"',
    'objectName: "marketNormalizedIntervalChart"','id: openSelectedInDay',
    'id: backToRange','objectName: "marketMovingAverageToggle"'])
    assert.ok(price.includes(token)&&!cross.includes(token),token);
assert.ok(price.slice(price.indexOf("id: priceCanvas"),price.indexOf("onPaint:",price.indexOf("id: priceCanvas"))).includes("onVisibleChanged: { if (visible) requestPaint(); }"));
assert.ok(qml.includes("onDayModeChanged: {\n        if (scroll) scroll.contentY = 0;"));
console.log("Finance Market M41 persistent research views, compact rail, selection-preserving navigation and DAY routing: PASS");
