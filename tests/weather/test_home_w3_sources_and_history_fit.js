"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const read=p=>fs.readFileSync(path.resolve(__dirname,"../..",p),"utf8");
const navText=read("widgets/weather/StationWorkspaceNavigationPolicy.js");
const deckText=read("widgets/weather/StationHomeDeckPolicy.js");
const home=read("widgets/weather/StationHome.qml");
const surface=read("widgets/weather/StationWorkspaceSurface.qml");
const metric=read("widgets/weather/StationHomeMetricCard.qml");
const trend=read("widgets/weather/WeatherTrendInspector.qml");
const favorites=read("services/weather/WeatherHomeFavoritesPolicy.js");
const native=v=>JSON.parse(JSON.stringify(v));
const nav=vm.createContext({}),deck=vm.createContext({Math,Number,String,Array,Object,isFinite});
vm.runInContext(navText.replace(/^\.pragma library\s*$/m,""),nav);
vm.runInContext(deckText.replace(/^\.pragma library\s*$/m,""),deck);

test("W3 HOME has SOURCES last, no separate runtime/health buttons, and retains legacy bookmarks",()=>{
    const tabs=native(nav.GROUPS.home);
    assert.deepEqual(tabs.map(x=>x.label),[
        "OVERVIEW","AUTO","QUICK","SNAPSHOT","HISTORY","MAGICK","SOURCES"
    ]);
    assert.equal(tabs[tabs.length-1].path,"home/health");
    assert.equal(nav.homeSectionFor("home/health"),"sources");
    for(const legacy of ["home/runtime","home/health"]){
        assert.equal(nav.homeSectionFor(legacy),"sources");
        assert.equal(nav.selectedGroup(legacy),"sources");
        assert.equal(nav.isHomeRoute(legacy),true);
        assert.equal(deck.isRotatable(legacy),true);
    }
    assert.deepEqual(native(deck.ROTATABLE),[
        "home/auto","home/quick","home/snapshot","home/history","home/health"
    ]);
    assert.deepEqual(native(deck.normalizedFavorites([
        "home/health","home/runtime","home/health"
    ])),["home/health"]);
    assert.ok(favorites.includes('"home/runtime", "home/health"'));
    assert.ok(surface.includes("workspaceSection: surface.homeSection"));
    assert.equal((surface.match(/StationHome\s*\{/g)||[]).length,1);
});

test("W3 preserves one runtime/health owner and excludes source racks from other HOME sections",()=>{
    assert.ok(home.includes('if (workspaceSection === "overview")'));
    assert.ok(home.includes('section !== "runtime" && section !== "health"'));
    assert.ok(home.includes('if (sourcesWorkspace)'));
    assert.ok(home.includes('return section === "runtime" || section === "health"'));
    assert.equal((home.match(/StationRuntimeRack\s*\{/g)||[]).length,1);
    assert.equal((home.match(/id: sourceHealthGrid/g)||[]).length,1);
    for(const name of ["home-w3-sources-title","home-w3-sources-runtime",
                        "home-w3-sources-health"])assert.ok(home.includes('objectName: "'+name+'"'));
    assert.ok(home.includes('model: home.sourceHealthRows'));
    assert.ok(home.includes('rows: home.runtimeRows'));
    assert.ok(home.includes('return section === "history" || section === "relations"'));
    assert.ok(home.includes('return section === "quick" || section === "relations"'));
    for(const unsafe of ["FileView {","Process {","Qt.createQmlObject("])
        assert.ok(!home.includes(unsafe),unsafe);
});

test("W3 compact HISTORY keeps graphs, yesterday, 7-day summary and daily cards while disabling its scroll",()=>{
    assert.ok(home.includes('readonly property bool compactHistory:'));
    assert.ok(home.includes('interactive: !home.compactHistory'));
    assert.ok(home.includes('visible: scrollable && !home.compactHistory'));
    assert.ok(home.includes('homeContent.implicitHeight'));
    assert.ok(home.includes('objectName: "home-w3-history-relations"'));
    assert.ok(home.includes('objectName: "home-w3-history-summary-cards"'));
    assert.ok(home.includes('objectName: "home-w3-history-daily-cards"'));
    assert.ok(home.includes('Math.max(72, Math.min(108, home.height - 188))'));
    assert.ok(home.includes('height: home.compactHistory ? 58 : 104'));
    assert.ok(home.includes('height: home.compactHistory ? 35 : 66'));
    assert.ok(home.includes('home.compactHistory ? 5 : 24'));
    assert.ok(home.includes('compact: home.compactHistory'));
    assert.ok(trend.includes('property bool compact: false'));
    assert.ok(trend.includes('height: inspector.compact ? 36 : 94'));
    assert.ok(metric.includes('property bool compact: false'));
    assert.ok(metric.includes('font.pixelSize: card.compact ? 15 : 20'));
    assert.ok(home.includes('title: "RECENT HISTORY // ARCHIVED MODEL"'));
});
