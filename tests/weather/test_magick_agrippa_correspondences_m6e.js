"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickAgrippaCorrespondencePolicy.js");
const pane=read("widgets/weather/StationMagickAgrippaCorrespondencesPane.qml");
const lenses=read("widgets/weather/StationMagickLensesPane.qml");
const subject=read("widgets/weather/StationMagickSubjectPane.qml");
const routes=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const m6d=read("widgets/weather/StationMagickPlanetaryHoursPane.qml");
const context=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),context);
const A=context;
const plain=x=>JSON.parse(JSON.stringify(x));

test("M6e is an edition-labelled seven-planet Agrippa chapter catalogue",()=>{
    assert.equal(A.FORMAT,"post-apollo.weather.magick-agrippa-m6e.v1");
    assert.equal(A.SOURCE.id,"agrippa-1651-book-i-23-29");
    assert.equal(A.SOURCE.edition,"1651 English edition");
    assert.equal(A.SOURCE.book,"Book I");
    assert.equal(A.SOURCE.textUrl,
        "https://www.esotericarchives.com/agrippa/op1.htm");
    assert.equal(A.SOURCE.scanUrl,
        "https://wellcomecollection.org/works/ftahuupv");
    assert.equal(A.PLANETS.length,7);
    assert.deepEqual(plain(A.PLANETS.map(p=>p.id)),
        ["saturn","jupiter","mars","sun","venus","mercury","moon"]);
    assert.deepEqual(plain(A.PLANETS.map(p=>p.chapter)),
        [25,26,27,23,28,29,24]);
    const seen=new Set();
    for(const planet of A.PLANETS){
        assert.ok(!seen.has(planet.id),"unique planet "+planet.id);
        seen.add(planet.id);
        for(const category of ["metals","stones","plants"]){
            assert.ok(Array.isArray(planet[category]));
            assert.ok(planet[category].length>0);
            assert.ok(planet[category].every(s=>
                typeof s==="string" && s.length>0));
        }
    }
});
test("M6e text respects Agrippa chapter-specific metals instead of one-to-one modern tables",()=>{
    assert.deepEqual(plain(A.find("sun").metals),["gold"]);
    assert.deepEqual(plain(A.find("moon").metals),["silver"]);
    assert.deepEqual(plain(A.find("saturn").metals),
        ["lead","gold (by weight)"]);
    assert.deepEqual(plain(A.find("jupiter").metals),
        ["tin","silver","gold"]);
    assert.deepEqual(plain(A.find("mars").metals),["iron","red brass"]);
    assert.deepEqual(plain(A.find("venus").metals),
        ["silver","yellow brass","red brass"]);
    assert.deepEqual(plain(A.find("mercury").metals),
        ["quicksilver","tin"]);
    assert.ok(A.find("saturn").plants.includes("rue"));
    assert.ok(A.find("jupiter").plants.includes("basil"));
    assert.ok(A.find("mars").plants.includes("garlic"));
    assert.ok(A.find("sun").plants.includes("marigold"));
    assert.ok(A.find("venus").plants.includes("vervain"));
    assert.ok(A.find("mercury").plants.includes("hazel"));
    assert.ok(A.find("moon").plants.includes("rosemary"));
});
test("M6e overlapping associations remain visible and source-labelled",()=>{
    assert.deepEqual(plain(A.shared("silver","metals")),
        ["jupiter","venus","moon"]);
    assert.deepEqual(plain(A.shared("sapphire","stones")),
        ["saturn","jupiter","venus"]);
    assert.deepEqual(plain(A.shared("red brass","metals")),
        ["mars","venus"]);
    assert.deepEqual(plain(A.matches("agate").map(x=>x.planet)),
        ["mercury"]);
    const hits=A.matches("tin");
    assert.equal(hits.length,2);
    assert.deepEqual(plain(hits.map(x=>x.planet)),["jupiter","mercury"]);
    assert.ok(hits.every(x=>x.sourceId===A.SOURCE.id));
    assert.equal(A.matches("".padEnd(81,"a")).length,0);
    assert.equal(A.matches("").length,0);
    assert.equal(A.matches(null).length,0);
    const entry=A.entry("venus","metals");
    assert.deepEqual(plain(entry.values),["silver","yellow brass","red brass"]);
    assert.equal(entry.chapter,28);
    assert.equal(entry.sourceId,A.SOURCE.id);
    entry.values.push("unsourced");
    assert.ok(!A.find("venus").metals.includes("unsourced"),
        "each inspector entry makes a non-mutating copy");
    assert.equal(A.entry("earth","metals"),null);
    assert.equal(A.entry("sun","magic"),null);
});
test("M6e seven-sector triple-band wheel and 7×3 matrix map to real entries",()=>{
    const g=A.wheel(480,260);
    assert.ok(g && g.outer>g.inner && g.band>0);
    for(let planet=0;planet<7;planet++){
        for(let cat=0;cat<3;cat++){
            const ang=-Math.PI/2+2*Math.PI*(planet+0.5)/7;
            const rad=g.inner+(cat+0.5)*g.band;
            const hit=A.pickWheel(480,260,
                g.cx+rad*Math.cos(ang),g.cy+rad*Math.sin(ang));
            assert.deepEqual(plain(hit),{
                planet:A.PLANETS[planet].id,
                category:A.CATEGORIES[cat].id
            });
        }
    }
    assert.equal(A.pickWheel(480,260,g.cx,g.cy),null);
    assert.equal(A.pickWheel(480,260,-100,-100),null);
    assert.equal(A.pickWheel(0,0,0,0),null);
    const width=420,height=220;
    for(let row=0;row<7;row++)
        for(let col=0;col<3;col++){
            const x=85+(col+0.5)*(width-88)/3;
            const y=22+(row+0.5)*(height-28)/7;
            assert.deepEqual(plain(A.matrixCell(width,height,x,y)),{
                planet:A.PLANETS[row].id,
                category:A.CATEGORIES[col].id
            });
        }
    assert.equal(A.matrixCell(width,height,20,20),null);
    assert.equal(A.matrixCell(100,90,100,90),null);
});
test("M6e remains inside accepted LENSES navigation, not an accidental GRIMOIRE replacement",()=>{
    assert.match(lenses,/property string lensView: "index"/);
    assert.match(lenses,/visible: lenses\.lensView==="index"/);
    assert.match(lenses,/label: "AGRIPPA"/);
    assert.match(lenses,/onClicked: lenses\.lensView="agrippa"/);
    assert.match(lenses,/StationMagickAgrippaCorrespondencesPane\s*\{/);
    assert.match(lenses,/onBackRequested: lenses\.lensView="index"/);
    assert.match(lenses,/path:"magick\/astrology\/charts"/);
    assert.match(lenses,/path:"magick\/lunar-solar\/moon"/);
    assert.match(lenses,/path:"magick\/grimoire\/references"/);
    assert.match(subject,/readonly property bool lensesLanding:\s*subjectRoute === "magick\/planetary\/correspondences"/);
    assert.match(subject,/id: lensesReference\s*StationMagickLensesPane/);
    assert.match(routes,/M6E ADDS AN AGRIPPA 1651 ENGLISH/);
    assert.match(routes,/"magick\/grimoire\/references": \{/);
    assert.match(routes,/NO SOURCED, EDITION-AWARE TEXT OR CORRESPONDENCE CATALOGUE/);
    assert.match(m6d,/StationMagickPlanetaryHoursPolicy\.js/);
});
test("M6e panel has real WHEEL/MATRIX selection, chapter and reference-only safety label",()=>{
    assert.match(pane,/import "StationMagickAgrippaCorrespondencePolicy\.js" as Agrippa/);
    assert.match(pane,/property string viewMode: "wheel"/);
    assert.match(pane,/readonly property var selectedEntry:/);
    assert.match(pane,/id: diagram/);
    assert.match(pane,/ctx\.arc\(g\.cx,g\.cy,r,begin,end\)/);
    assert.match(pane,/Agrippa\.pickWheel\(diagram\.width,diagram\.height,/);
    assert.match(pane,/Agrippa\.matrixCell\(diagram\.width,diagram\.height,/);
    assert.match(pane,/label: "WHEEL"/);
    assert.match(pane,/label: "MATRIX"/);
    assert.match(pane,/label: "BACK"/);
    assert.match(pane,/catalogue\.backRequested\(\)/);
    assert.match(pane,/catalogue\.citation/);
    assert.match(pane,/HISTORICAL ATTRIBUTIONS \/\/ NOT MEDICAL OR CAUSAL CLAIMS/);
    assert.match(pane,/MULTIPLE PLANETS MAY SHARE TERMS \/\/ METALS FOR REFERENCE ONLY/);
    for(const src of [source,pane,lenses]){
        for(const forbidden of ["Process {","Timer {","FileView {","XMLHttpRequest",
            "Qt.openUrlExternally","Date.now()","new WebSocket","fetch(","curl "]){
            assert.ok(!src.includes(forbidden),"unapproved actor "+forbidden);
        }
    }
});
