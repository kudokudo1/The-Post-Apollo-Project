"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickTarotLayoutPolicy.js");
const qml=read("widgets/weather/StationMagickTarotPane.qml");
const card=read("widgets/weather/StationMagickTarotCard.qml");
const deckSource=read("widgets/weather/StationMagickTarotDeckPolicy.js");
const physicalSource=read("widgets/weather/StationMagickTarotPhysicalPolicy.js");
const route=read("widgets/weather/StationMagickSubjectPane.qml");
const c=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),c);
const L=c;
const plain=x=>JSON.parse(JSON.stringify(x));

test("M6i three-card layout grows with viewport instead of fixed 175px cards",()=>{
    const normal=L.spread(470,560,"three");
    const big=L.spread(650,680,"three");
    assert.equal(normal.format,L.FORMAT);
    assert.equal(normal.count,3);
    assert.equal(normal.columns,3);
    assert.equal(normal.rows,1);
    assert.ok(normal.cardHeight>175,JSON.stringify(normal));
    assert.ok(normal.slotWidth>130);
    assert.equal(normal.contentHeight,normal.cardHeight);
    assert.ok(big.cardHeight>=normal.cardHeight);
    assert.ok(big.slotWidth>normal.slotWidth);
    assert.ok(big.contentHeight<=680-229);
});

test("M6i single-card preview centers and fills a bounded source viewport",()=>{
    const layout=L.spread(470,560,"one");
    assert.equal(layout.count,1);
    assert.equal(layout.columns,1);
    assert.equal(layout.rows,1);
    assert.equal(layout.centered,true);
    assert.ok(layout.slotWidth>=230);
    assert.ok(layout.cardHeight>=290);
    assert.ok(layout.cardHeight<=560-229);
});

test("M6i five-card spread retains readable three-plus-two across widths",()=>{
    for(const [width,height] of [[270,360],[360,470],[470,560],[700,690]]){
        const v=L.spread(width,height,"five");
        assert.equal(v.count,5);
        assert.equal(v.rows,2);
        assert.equal(v.columns,3);
        assert.equal(v.gap,7);
        assert.ok(v.slotWidth>=80);
        assert.ok(v.cardHeight>=68);
        assert.ok(v.contentHeight<=Math.max(150,height-229)+0.000001,
                  JSON.stringify(v));
        assert.ok(v.slotWidth*3+v.gap*2<=width+0.000001);
    }
    const v=L.spread(470,560,"five");
    assert.ok(v.cardHeight>126,"target screenshot had five cards at 126px");
    assert.equal(L.spread(0,0,"five"),null);
    assert.equal(L.spread(500,500,"nine"),null);
    assert.equal(L.spread(NaN,500,"three"),null);
});

test("M6i index layout scales preview while paginating full source catalogue",()=>{
    const small=L.catalog(300,400);
    const medium=L.catalog(470,560);
    const large=L.catalog(700,690);
    assert.equal(small.pageSize,6);
    assert.equal(medium.pageSize,7);
    assert.equal(large.pageSize,8);
    assert.ok(medium.previewWidth>175);
    assert.ok(medium.previewHeight>240);
    assert.ok(medium.listWidth>=55);
    assert.ok(large.previewWidth>medium.previewWidth);
    assert.equal(L.catalog(110,200),null);
    assert.equal(L.catalog(Infinity,400),null);
});

test("M6i inspector chooses only actual drawn cards, never guesses a preview",()=>{
    const real={ready:true,cards:[
        {id:"wands-daughter",title:"Daughter of Wands",
         position:"PAST",reversed:false},
        {id:"cups-mother",title:"Mother of Cups",
         position:"PRESENT",reversed:true}
    ]};
    assert.equal(L.selectedCard(real,0).id,"wands-daughter");
    assert.equal(L.selectedCard(real,1).reversed,true);
    assert.equal(L.selectedCard(real,-1),null);
    assert.equal(L.selectedCard(real,2),null);
    assert.equal(L.selectedCard({ready:false,cards:real.cards},0),null);
    assert.equal(L.selectedCard({ready:true,cards:[{id:"x"}]},0),null);
    const entry=[{id:"major-the-fool",title:"The Fool"},
                 {id:"cups-mother",title:"Mother of Cups"}];
    assert.equal(L.previewByClick(entry,""),null);
    assert.equal(L.previewByClick(entry,"other"),null);
    assert.equal(L.previewByClick(entry,"cups-mother"),entry[1]);
    assert.equal(L.previewByClick([], "major-the-fool"),null);
    const inspect=L.inspect(470,560);
    assert.ok(inspect);
    assert.ok(inspect.height>300);
    assert.ok(inspect.width>=180);
    assert.equal(L.inspect(100,100),null);
});

test("M6i QML makes initial preview non-selected and requires explicit physical choice",()=>{
    assert.match(qml,/import "StationMagickTarotLayoutPolicy\.js" as Layout/);
    assert.match(qml,/readonly property var explicitlyPreviewedCard:/);
    assert.match(qml,/Layout\.previewByClick\(catalogEntries,previewId\)/);
    assert.match(qml,/if\(drawMethod!=="physical" \|\| !explicitlyPreviewedCard\)return/);
    assert.match(qml,/explicitlyPreviewedCard\.id,manualReversed/);
    assert.match(qml,/onCatalogPageChanged: previewId=""/);
    assert.match(qml,/previewId="";\s*if\(result\.state\.complete\)viewMode="draw"/);
    assert.match(qml,/selected: tarot\.previewId===modelData\.id/);
    assert.match(qml,/INDEX \/\/ PREVIEW ONLY/);
    assert.match(qml,/PREVIEW ONLY \/\/ CLICK CARD ROW TO SELECT/);
    assert.match(qml,/tarot\.explicitlyPreviewedCard!==null/);
    assert.match(qml,/Physical\.contains\(tarot\.reading,/);
});

test("M6i UI uses layout measurements and real card focus, not new providers",()=>{
    assert.match(qml,/readonly property var spreadMetrics:/);
    assert.match(qml,/readonly property var catalogMetrics:/);
    assert.match(qml,/readonly property var inspectMetrics:/);
    assert.match(qml,/property int inspectedDrawIndex: -1/);
    assert.match(qml,/onReadingChanged: inspectedDrawIndex=-1/);
    assert.match(qml,/readonly property var inspectedDrawCard:/);
    assert.match(qml,/Layout\.selectedCard\(reading,inspectedDrawIndex\)/);
    assert.match(qml,/function inspectCard\(index\)/);
    assert.match(qml,/onClicked: tarot\.inspectCard\(index\)/);
    assert.match(qml,/id: tarotCardInspector/);
    assert.match(qml,/visible: tarot\.inspectedDrawCard!==null/);
    assert.match(qml,/label: "CLOSE"/);
    assert.match(qml,/label: "◀ CARD"/);
    assert.match(qml,/label: "CARD ▶"/);
    assert.match(qml,/onClicked: tarot\.inspectedDrawIndex=-1/);
    assert.match(qml,/tarot\.spreadMetrics\.contentHeight/);
    assert.match(qml,/tarot\.spreadMetrics\.slotWidth/);
    assert.match(qml,/tarot\.catalogMetrics\.previewWidth/);
    assert.match(qml,/tarot\.catalogMetrics\.previewHeight/);
    assert.match(qml,/tarot\.inspectMetrics\.height/);
    assert.match(qml,/StationMagickTarotCard\s*\{/);
    assert.match(qml,/Deck\.draw\(spreadId,Math\.random,reversals\)/);
    assert.match(qml,/Physical\.add\(Deck\.SPREADS,Deck\.CARDS,reading,/);
    assert.match(qml,/onClicked: tarot\.addPhysicalCard\(\)/);
    assert.match(card,/font\.pixelSize: 11/);
    assert.match(card,/font\.pixelSize: 10/);
    assert.match(card,/LOCAL ART|localArtworkDirectory/);
    assert.match(route,/id: tarotReference\s*StationMagickTarotPane/);
    for(const str of [source,qml,card]){
      for(const forbidden of ["Process {","Timer {","FileView {",
        "XMLHttpRequest","Qt.openUrlExternally","WebEngineView","new WebSocket",
        "curl ","fetch(","writeFile","localStorage"]){
        assert.ok(!str.includes(forbidden),"Unexpected actor "+forbidden);
      }
    }
    assert.match(deckSource,/FISHER-YATES \/ PSEUDORANDOM MATH\.RANDOM/);
    assert.match(physicalSource,/function undo\(/);
});

