"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const agrippaSrc=read("widgets/weather/StationMagickAgrippaCorrespondencePolicy.js");
const atlasSrc=read("widgets/weather/StationMagickGrimoireAtlasPolicy.js");
const pane=read("widgets/weather/StationMagickGrimoireAtlasPane.qml");
const subject=read("widgets/weather/StationMagickSubjectPane.qml");
const route=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const lenses=read("widgets/weather/StationMagickLensesPane.qml");
const m6e=read("widgets/weather/StationMagickAgrippaCorrespondencesPane.qml");
const journal=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const agrippa=vm.createContext({});
const atlas=vm.createContext({});
vm.runInContext(agrippaSrc.replace(/^\.pragma library\s*/m,""),agrippa);
vm.runInContext(atlasSrc.replace(/^\.pragma library\s*/m,""),atlas);
const A=agrippa,G=atlas;
const plain=x=>JSON.parse(JSON.stringify(x));
const build=(query="",category="all",focus="")=>
    G.build(A.PLANETS,A.CATEGORIES,A.SOURCE,query,category,focus);

test("M6f indexes the original M6e source once, without copying or mutating it",()=>{
    const before=JSON.stringify({planets:A.PLANETS,categories:A.CATEGORIES,
                                 source:A.SOURCE});
    const result=build();
    assert.equal(result.ready,true,result.reason);
    assert.equal(result.format,"post-apollo.weather.magick-grimoire-atlas.m6f.v1");
    assert.equal(result.source.id,A.SOURCE.id);
    assert.equal(result.source.edition,A.SOURCE.edition);
    assert.equal(result.source.book,"Book I");
    assert.equal(result.source.textUrl,A.SOURCE.textUrl);
    assert.equal(result.total,42,"42 actually catalogued M6e term occurrences");
    assert.equal(result.visible,42);
    assert.equal(result.entries.length,42);
    assert.equal(result.rows.length,42);
    assert.equal(result.nodes.length,7);
    assert.ok(result.links.length>=4,"real shared terms produce links");
    for(const row of result.rows){
        const p=A.find(row.planet);
        assert.ok(p);
        assert.equal(row.chapter,p.chapter);
        assert.equal(row.sourceId,A.SOURCE.id);
        assert.ok(p[row.category].includes(row.term));
    }
    assert.equal(JSON.stringify({planets:A.PLANETS,categories:A.CATEGORIES,
                                 source:A.SOURCE}),before);
    result.source.id="tampered";
    assert.equal(A.SOURCE.id,"agrippa-1651-book-i-23-29",
        "source metadata remains separate from UI state");
});
test("M6f category and in-memory search do not invent synonyms or meanings",()=>{
    const silver=build("silver","metals");
    assert.equal(silver.ready,true);
    assert.equal(silver.visible,3);
    assert.deepEqual(plain(silver.rows.map(x=>x.planet)),
        ["jupiter","venus","moon"]);
    assert.ok(silver.rows.every(x=>x.term==="silver"));
    assert.equal(silver.overlaps,3);
    assert.deepEqual(plain(silver.links.map(x=>[x.from,x.to]).sort()),
        [["jupiter","venus"],["jupiter","moon"],["venus","moon"]].sort());
    assert.ok(silver.links.every(x=>x.count===1));
    const sapphire=build("  SAPPHIRE ","stones");
    assert.equal(sapphire.visible,3);
    assert.equal(sapphire.overlaps,3);
    const gold=build("gold","metals");
    assert.equal(gold.visible,3,"substring lookup sees gold by weight too");
    assert.equal(gold.overlaps,1,
        "gold (by weight) does not silently become identical to gold");
    const invent=build("diamonds","stones");
    assert.equal(invent.visible,0);
    assert.equal(invent.overlaps,0);
    assert.equal(invent.rows.length,0);
    const wrong=build("silver","plants");
    assert.equal(wrong.visible,0,"terms do not leak across categories");
    const focus=build("silver","metals","moon");
    assert.equal(focus.visible,1);
    assert.equal(focus.overlaps,3,
        "focus changes inspection, not the global source graph");
    assert.equal(focus.rows[0].chapter,24);
    assert.deepEqual(plain(focus.nodes.map(x=>x.id)),
        plain(A.PLANETS.map(x=>x.id)));
});
test("M6f never expands into unsourced corpora, arbitrary query size or invalid categories",()=>{
    const raw=build();
    assert.equal(G.build([],A.CATEGORIES,A.SOURCE,"","all","").ready,false);
    assert.equal(G.build(A.PLANETS,[],A.SOURCE,"","all","").ready,false);
    assert.equal(G.build(A.PLANETS,A.CATEGORIES,{id:"invented"},
        "","all","").ready,false);
    assert.equal(G.build(A.PLANETS,A.CATEGORIES,A.SOURCE,
        "","deities","").ready,false);
    assert.equal(G.build(A.PLANETS,A.CATEGORIES,A.SOURCE,
        "","all","pluto").ready,false);
    assert.equal(G.build(A.PLANETS,A.CATEGORIES,A.SOURCE,
        "x".repeat(81),"all","").ready,false);
    const mutate=plain(A.PLANETS);
    mutate[0].metals=[null];
    assert.equal(G.build(mutate,A.CATEGORIES,A.SOURCE,"","all","").ready,false);
    mutate[0].metals=[];
    assert.equal(G.build(mutate,A.CATEGORIES,A.SOURCE,"","all","").ready,false);
    mutate[0].metals=["lead"];
    mutate[0].chapter=99;
    assert.equal(G.build(mutate,A.CATEGORIES,A.SOURCE,"","all","").ready,false);
    assert.equal(raw.source.reference,"CHAPTERS XXIII–XXIX");
});
test("M6f pagination returns original matching source rows only",()=>{
    const data=build();
    assert.equal(G.PAGE_SIZE,5);
    assert.equal(G.pages(data,4),11);
    assert.equal(G.page(data,0,4).length,4);
    assert.equal(G.page(data,10,4).length,2);
    assert.equal(G.page(data,11,4).length,0);
    assert.equal(G.page(data,-1,4).length,0);
    assert.equal(G.pages(build("diamonds"),4),0);
    assert.deepEqual(plain(G.page(build("tin","metals"),0,5).map(x=>x.planet)),
        ["jupiter","mercury"]);
    assert.equal(G.page(null,0,4).length,0);
    assert.equal(G.pages(null,4),0);
});
test("M6f graph nodes and click picking are exact for seven real planets",()=>{
    const result=build(),w=400,h=200;
    assert.ok(G.geometry(w,h));
    for(let i=0;i<7;i++){
        const p=G.nodePoint(i,w,h);
        assert.ok(p);
        assert.equal(G.pickNode(result,w,h,p.x,p.y),
            result.nodes[i].id);
    }
    assert.equal(G.pickNode(result,w,h,0,0),"");
    assert.equal(G.pickNode(result,w,h,w/2,h/2),"");
    assert.equal(G.pickNode(result,100,100,0,0),"");
    assert.equal(G.pickNode(null,w,h,0,0),"");
    assert.equal(G.nodePoint(7,w,h),null);
    assert.equal(G.nodePoint(-1,w,h),null);
    assert.equal(G.geometry(100,100),null);
});
test("M6f source route is usable without replacing accepted LENSES or GRIMOIRE JOURNAL",()=>{
    assert.match(subject,/readonly property bool grimoireAtlasRoute:/);
    assert.match(subject,/subjectRoute === "magick\/grimoire\/references"/);
    assert.match(subject,/magickPane\.grimoireAtlasRoute\s*\?\s*grimoireAtlasReference/);
    assert.match(subject,/id: grimoireAtlasReference\s*StationMagickGrimoireAtlasPane/);
    assert.match(subject,/id: lensesReference\s*StationMagickLensesPane/);
    assert.match(lenses,/property string lensView: "index"/);
    assert.match(lenses,/StationMagickAgrippaCorrespondencesPane/);
    assert.match(lenses,/path:"magick\/grimoire\/references"/);
    assert.match(lenses,/AGRIPPA INDEX \/ READ-ONLY/);
    assert.match(route,/M6F SOURCE ATLAS INDEXES THE EXISTING M6E AGRIPPA/);
    assert.match(route,/NOT A COMPLETE GRIMOIRE, DIVINATION READING OR PERSONAL JOURNAL/);
    assert.match(journal,/"magick\/grimoire\/journal": \{/);
    assert.match(journal,/THIS ROUTE NEVER WRITES A PERSONAL RECORD/);
    assert.match(m6e,/property string viewMode: "wheel"/);
    assert.equal(route.includes('source:"cosmos/planets-stars/planet-clock",\n    note:"M6F'),false,
       "the new historical library route must not claim an astronomical source");
});
test("M6f QML delivers live search, category tabs, source result pages and graph controls",()=>{
    assert.match(pane,/import "StationMagickAgrippaCorrespondencePolicy\.js" as Agrippa/);
    assert.match(pane,/import "StationMagickGrimoireAtlasPolicy\.js" as Index/);
    assert.match(pane,/Index\.build\(\s*Agrippa\.PLANETS,Agrippa\.CATEGORIES,Agrippa\.SOURCE,/);
    assert.match(pane,/TextInput\s*\{/);
    assert.match(pane,/onTextChanged: atlas\.query=text/);
    assert.match(pane,/maximumLength: 80/);
    assert.match(pane,/\{id:"metals",label:"METALS"\}/);
    assert.match(pane,/\{id:"stones",label:"STONES"\}/);
    assert.match(pane,/\{id:"plants",label:"PLANTS"\}/);
    assert.match(pane,/id: network/);
    assert.match(pane,/Index\.nodePoint\(edge\.fromIndex,width,height\)/);
    assert.match(pane,/Index\.pickNode\(atlas\.corpus,/);
    assert.match(pane,/onClicked: atlas\.focusPlanet=modelData\.planet/);
    assert.match(pane,/Index\.page\(corpus,pageIndex,rowsPerPage\)/);
    assert.match(pane,/label: "◀ PAGE"/);
    assert.match(pane,/label: "PAGE ▶"/);
    assert.match(pane,/CH\. "\+modelData\.chapter/);
    assert.match(pane,/ONE CORPUS \/\/ AGRIPPA BOOK I \/\/ NOT A COMPLETE GRIMOIRE/);
    assert.match(pane,/HISTORICAL ATTRIBUTIONS \/ NO MEDICAL OR CAUSAL CLAIMS/);
    for(const s of [atlasSrc,pane]){
        for(const forbidden of ["Process {","Timer {","FileView {",
            "XMLHttpRequest","Qt.openUrlExternally","Date.now()",
            "new WebSocket","curl ","fetch(","localStorage",
            "writeFile","WebEngineView"]){
            assert.ok(!s.includes(forbidden),
                "unauthorized actor/storage "+forbidden);
        }
    }
});
