"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const js=read("widgets/weather/StationMagickTarotDeckPolicy.js");
const pane=read("widgets/weather/StationMagickTarotPane.qml");
const card=read("widgets/weather/StationMagickTarotCard.qml");
const subject=read("widgets/weather/StationMagickSubjectPane.qml");
const routes=read("widgets/weather/StationMagickSubjectPanelPolicy.js");
const grimoire=read("widgets/weather/StationMagickGrimoireAtlasPane.qml");
const ctx=vm.createContext({});
vm.runInContext(js.replace(/^\.pragma library\s*/m,""),ctx);
const T=ctx;
const plain=value=>JSON.parse(JSON.stringify(value));
test("M6g 78 Wild Unknown identities, 22 major, 56 minor, four family courts",()=>{
    assert.equal(T.FORMAT,"post-apollo.weather.magick-tarot.m6g.v1");
    assert.equal(T.DECK.name,"THE WILD UNKNOWN TAROT");
    assert.equal(T.DECK.creator,"KIM KRANS");
    assert.equal(T.DECK.publisher,"HARPERONE");
    assert.equal(T.DECK.count,78);
    assert.equal(T.CARDS.length,78);
    assert.equal(T.CARDS.filter(c=>c.family==="major").length,22);
    assert.equal(T.CARDS.filter(c=>c.family!=="major").length,56);
    const ids=T.CARDS.map(c=>c.id);
    assert.equal(new Set(ids).size,78);
    assert.deepEqual(plain(T.CARDS.map(c=>c.index)),
        Array.from({length:78},(_,i)=>i));
    assert.ok(T.CARDS.every(c=>T.cardById(c.id)===c));
    assert.equal(T.cardById("not-a-card"),null);
    assert.equal(T.cardById("../foo"),null);
    assert.equal(T.DECK.artworkIncluded,false);
    assert.equal(T.DECK.guidebookTextIncluded,false);
    assert.equal(T.DECK.cardIdentityOnly,true);
});
test("M6g honors Wild Unknown's Daughter Son Mother Father court titles",()=>{
    for(const suit of ["Wands","Cups","Swords","Pentacles"]){
        const group=suit.toLowerCase();
        assert.equal(T.catalog(group).length,14);
        for(const rank of ["Daughter","Son","Mother","Father"]){
            const hit=T.cardById(group+"-"+rank.toLowerCase());
            assert.ok(hit);
            assert.equal(hit.title,rank+" of "+suit);
            assert.equal(hit.suit,suit);
        }
        for(const unsupported of ["page","knight","queen","king"])
            assert.equal(T.cardById(group+"-"+unsupported),null);
        assert.equal(T.cardById(group+"-ace").title,"Ace of "+suit);
        assert.equal(T.cardById(group+"-10").title,"10 of "+suit);
    }
    assert.equal(T.catalog("major").length,22);
    assert.equal(T.catalog("all").length,78);
    assert.equal(T.catalog("invalid").length,0);
    assert.equal(T.family("invalid"),"");
});
test("M6g uses a real without-replacement Fisher-Yates shuffle and preserves deck",()=>{
    const before=JSON.stringify(T.CARDS);
    const draw=T.draw("five",()=>0.5,false);
    assert.equal(draw.ready,true,draw.reason);
    assert.equal(draw.count,5);
    assert.equal(draw.cards.length,5);
    assert.deepEqual(plain(draw.cards.map(c=>c.position)),
        ["CONTEXT","TENSION","PERSPECTIVE","POSSIBILITY","REFLECTION"]);
    assert.equal(new Set(draw.cards.map(c=>c.id)).size,5);
    assert.ok(draw.cards.every(c=>T.cardById(c.id).title===c.title));
    assert.ok(draw.cards.every(c=>c.reversed===false));
    assert.match(draw.method,/PSEUDORANDOM/);
    assert.equal(JSON.stringify(T.CARDS),before,"shared card index is read-only");
    const allIds=new Set(T.CARDS.map(c=>c.id));
    assert.ok(draw.cards.every(c=>allIds.has(c.id)));
});
test("M6g actual injected random source affects draw and optional reversal",()=>{
    const first=T.draw("one",()=>0,false);
    const second=T.draw("one",()=>0.99999,false);
    assert.equal(first.ready,true);
    assert.equal(second.ready,true);
    assert.notEqual(first.cards[0].id,second.cards[0].id);
    const upright=T.draw("three",()=>0,false);
    const reverse=T.draw("three",()=>0.9,true);
    assert.equal(reverse.ready,true);
    assert.deepEqual(plain(reverse.cards.map(c=>c.reversed)),
        [true,true,true]);
    assert.deepEqual(plain(upright.cards.map(c=>c.position)),
        ["PAST","PRESENT","FUTURE"]);
    assert.ok(upright.cards.every(c=>!c.reversed));
    const mixed=T.draw("five",(()=>{
        let n=0;return ()=>{n++;return n%2===0?0.9:0.1;};
    })(),true);
    assert.equal(mixed.ready,true);
    assert.equal(new Set(mixed.cards.map(c=>c.id)).size,5);
    assert.ok(mixed.cards.some(c=>c.reversed));
    assert.ok(mixed.cards.some(c=>!c.reversed));
});
test("M6g refuses invalid spread, random values, and malformed reversal input",()=>{
    const invalid=[
        T.draw("unknown",()=>0.2,false),
        T.draw("three",null,false),
        T.draw("three",()=>1,false),
        T.draw("three",()=>-0.1,false),
        T.draw("three",()=>Infinity,false),
        T.draw("three",()=>NaN,false),
        T.draw("three",()=>null,false),
        T.draw("three",()=>0.3,"yes"),
        T.draw("one",(()=>{let n=0;return ()=>++n===78?1:0.5;})(),true)
    ];
    assert.ok(invalid.every(d=>d.ready===false && d.cards.length===0));
    assert.equal(T.spread("x"),null);
    assert.equal(T.spread("five").slots.length,5);
});
test("M6g local artwork resolves private absolute PNG paths only",()=>{
    assert.equal(T.localArtworkUrl("/var/home/tester/My Tarot","major-the-fool"),
        "file:///var/home/tester/My%20Tarot/major-the-fool.png");
    assert.equal(T.localArtworkUrl("/home/me/cards/","wands-daughter"),
        "file:///home/me/cards/wands-daughter.png");
    const invalid=["","https://example.com","file:///home/me",
        "ftp://host","../images","./images","/home/me/../secret",
        "/home/me\\secret","/home/me:80","/home/me\nmore","/"];
    assert.ok(invalid.every(p=>T.localArtworkUrl(p,"major-the-fool")===""));
    assert.equal(T.localArtworkUrl("/home/me/cards","../../secrets"),"");
    assert.equal(T.localArtworkUrl("/home/me/cards","unknown"),"");
    assert.equal(T.localArtworkUrl("/home/me/cards",null),"");
    assert.equal(T.DECK.artPolicy.includes("USER-SUPPLIED LOCAL FILES"),true);
});
test("M6g complete QML deck supports selection, draw, optional reversals and index",()=>{
    assert.match(pane,/import "StationMagickTarotDeckPolicy\.js" as Deck/);
    assert.match(pane,/property string viewMode: "draw"/);
    assert.match(pane,/property string spreadId: "three"/);
    assert.match(pane,/property bool reversals: false/);
    assert.match(pane,/Deck\.draw\(spreadId,Math\.random,reversals\)/);
    // M6h keeps the digital shuffle while showing CHOOSE CARD in manual mode.
    assert.match(pane,/\? "CHOOSE CARD" : "SHUFFLE \+ DRAW"/);
    assert.match(pane,/Deck\.draw\(spreadId,Math\.random,reversals\)/);
    assert.match(pane,/label: "CLEAR"/);
    assert.match(pane,/label: "INDEX"/);
    assert.match(pane,/label: "DRAW"/);
    assert.match(pane,/property string catalogGroup: "all"/);
    assert.match(pane,/readonly property var catalogEntries: Deck\.catalog\(catalogGroup\)/);
    assert.match(pane,/property string previewId: ""/);
    assert.match(pane,/onClicked: \{\s*\/\/ Choose a catalogue page\/preview/);
    assert.match(pane,/tarot\.previewId=modelData\.id/);
    assert.match(pane,/label: "◀ PREV"/);
    assert.match(pane,/label: "NEXT ▶"/);
    assert.match(pane,/StationMagickTarotCard\s*\{/);
    // M6i replaces hard-coded card dimensions with bounded viewport layout.
    assert.match(pane,/Layout\.spread\(Math\.max\(180,width-14\),height,spreadId\)/);
    assert.match(pane,/tarot\.spreadMetrics\.cardHeight/);
    assert.match(pane,/onTextChanged: tarot\.localArtworkDirectory=text/);
    assert.match(pane,/maximumLength: 1024/);
    assert.match(pane,/NO GUIDEBOOK QUOTES OR PREDICTIONS/);
    assert.match(pane,/DECK PHOTOS ARE NOT BUNDLED \/\/ READ-ONLY PRIVATE FOLDER/);
    assert.match(pane,/NO WILD UNKNOWN IMAGES \/\/ SELECT LOCAL ART FOLDER/);
});
test("M6g card front has original placeholder and OPTIONAL local-only image",()=>{
    assert.match(card,/import "StationMagickTarotDeckPolicy\.js" as Deck/);
    assert.match(card,/readonly property string localSource:/);
    assert.match(card,/Deck\.localArtworkCandidates\(localArtworkDirectory,card\.id\)/);
    assert.match(card,/onStatusChanged:/);
    assert.match(card,/NO PHOTO/);
    assert.match(card,/id: decorativeCanvas/);
    assert.match(card,/ctx\.arc\(cx,cy,radius\*/);
    assert.match(card,/source: face\.localSource/);
    assert.match(card,/visible: face\.hasLocalArt/);
    assert.match(card,/angle: face\.reversed \? 180 : 0/);
    assert.match(card,/PHOTO NOT LOADED/);
    assert.ok(!card.includes("http://") && !card.includes("https://"));
    assert.ok(!pane.includes("FileDialog") && !pane.includes("FolderDialog"));
    assert.ok(!pane.includes("upload") || pane.includes("NO UPLOAD"));
});
test("M6g TAROT route does not modify other MAGICK rooms or record a journal",()=>{
    assert.match(subject,/readonly property bool tarotRoute:/);
    assert.match(subject,/subjectRoute === "magick\/divination\/tarot"/);
    assert.match(subject,/magickPane\.tarotRoute\s*\?\s*tarotReference/);
    assert.match(subject,/id: tarotReference\s*StationMagickTarotPane/);
    assert.match(subject,/id: grimoireAtlasReference\s*StationMagickGrimoireAtlasPane/);
    assert.match(subject,/id: lensesReference\s*StationMagickLensesPane/);
    assert.match(routes,/M6G OFFERS A 78-CARD THE WILD UNKNOWN TAROT/);
    assert.match(routes,/NO COPYRIGHTED ILLUSTRATIONS OR GUIDEBOOK TEXT/);
    assert.match(routes,/NOT AN ASTRONOMICAL MEASUREMENT/);
    assert.match(routes,/THIS ROUTE NEVER WRITES A PERSONAL RECORD/);
    assert.match(grimoire,/StationMagickGrimoireAtlasPolicy\.js/);
    for(const src of [js,pane,card]){
        for(const forbidden of ["Process {","Timer {","FileView {",
            "XMLHttpRequest","Qt.openUrlExternally","WebEngineView",
            "new WebSocket","fetch(","curl ","writeFile",
            "localStorage","Date.now()"]){
            assert.ok(!src.includes(forbidden),"new actor "+forbidden);
        }
    }
});
