"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const deckSrc=read("widgets/weather/StationMagickTarotDeckPolicy.js");
const card=read("widgets/weather/StationMagickTarotCard.qml");
const pane=read("widgets/weather/StationMagickTarotPane.qml");
const subject=read("widgets/weather/StationMagickSubjectPane.qml");
const ctx=vm.createContext({});
vm.runInContext(deckSrc.replace(/^\.pragma library\s*/m,""),ctx);
const D=ctx;
const plain=x=>JSON.parse(JSON.stringify(x));

test("M6j returns only finite known-card local image candidate URLs",()=>{
    const before=JSON.stringify(D.CARDS);
    const folder="/var/home/example/My Tarot";
    const expected=[
      "file:///var/home/example/My%20Tarot/major-the-fool.png",
      "file:///var/home/example/My%20Tarot/major-the-fool.jpg",
      "file:///var/home/example/My%20Tarot/major-the-fool.jpeg",
      "file:///var/home/example/My%20Tarot/major-the-fool.webp"
    ];
    assert.deepEqual(plain(D.localArtworkCandidates(folder,"major-the-fool")),expected);
    assert.deepEqual(plain(D.localArtworkCandidates(
        "/home/a/folder/","wands-daughter")),[
        "file:///home/a/folder/wands-daughter.png",
        "file:///home/a/folder/wands-daughter.jpg",
        "file:///home/a/folder/wands-daughter.jpeg",
        "file:///home/a/folder/wands-daughter.webp"
    ]);
    assert.equal(D.localArtworkUrl(folder,"major-the-fool"),expected[0],
        "M6g PNG convention remains backward-compatible");
    assert.equal(D.CARDS.length,78);
    assert.equal(JSON.stringify(D.CARDS),before,"no mutation of deck identity");
});
test("M6j refuses remote artwork URLs, traversal, invalid or missing card IDs",()=>{
    for(const folder of ["", "http://example.com", "https://example.com",
            "file:///home/you/art","ftp://example.com","../tarot",
            "/home/user/../secret","/home/user\\photos",
            "/home/user\ntarot","/"]){
        assert.deepEqual(plain(D.localArtworkCandidates(folder,"major-the-fool")),[],
            "refused local folder "+folder);
    }
    for(const id of ["unknown","../../../etc/passwd","../major-the-fool",
                     "","MAJOR-THE-FOOL",null]){
        assert.deepEqual(plain(D.localArtworkCandidates("/home/user/cards",id)),[]);
    }
    assert.deepEqual(plain(D.localArtworkCandidates(null,"major-the-fool")),[]);
    assert.ok(plain(D.localArtworkCandidates("/tmp/cards","major-the-star"))
        .every(url=>url.startsWith("file:///")));
    assert.equal(deckSrc.includes("XMLHttpRequest"),false);
    assert.equal(deckSrc.includes("fetch("),false);
});
test("M6j card visibly reports missing real images, tries supported formats and preserves privacy",()=>{
    assert.match(card,/Deck\.localArtworkCandidates\(localArtworkDirectory,card\.id\)/);
    assert.match(card,/property int artworkCandidateIndex: 0/);
    assert.match(card,/onArtworkCandidatesChanged: artworkCandidateIndex=0/);
    assert.match(card,/source: face\.localSource/);
    assert.match(card,/onStatusChanged:/);
    assert.match(card,/status===Image\.Error/);
    assert.match(card,/face\.artworkCandidateIndex\+\+/);
    assert.match(card,/art\.status===Image\.Ready/);
    assert.match(card,/NO CARD IMAGES INSTALLED/);
    assert.match(card,/LOADING LOCAL IMAGE/);
    assert.match(card,/IMAGE MISSING \/\/ CHECK CARD FILE/);
    assert.match(card,/NO PHOTO/);
    assert.match(card,/PHOTO NOT LOADED/);
    assert.match(card,/LOCAL PHOTO/);
    assert.match(card,/Image\.PreserveAspectFit/);
    assert.match(card,/face\.reversed \? 180 : 0/);
    assert.ok(!card.includes("http://")&&!card.includes("https://"));
    assert.match(subject,/id: tarotReference\s*StationMagickTarotPane/);
});
test("M6j art-directory status does not falsely claim photos are loaded",()=>{
    assert.match(pane,/NO WILD UNKNOWN IMAGES \/\/ SELECT LOCAL ART FOLDER/);
    assert.match(pane,/LOCAL ART CHECK \/\/ MATCH EACH CARD ID TO PNG\/JPG\/WEBP/);
    assert.match(pane,/Yellow means folder syntax was accepted, NOT that/);
    assert.match(pane,/Deck\.localArtworkCandidates\(/);
    assert.match(pane,/artworkFolderInput/);
    assert.match(pane,/onTextChanged: tarot\.localArtworkDirectory=text/);
    assert.match(pane,/ART FILENAMES: major-the-fool\.png \/ wands-daughter\.jpg/);
    assert.match(pane,/DECK PHOTOS ARE NOT BUNDLED \/\/ READ-ONLY PRIVATE FOLDER/);
    assert.match(pane,/id: focusedCardFace/);
    assert.match(pane,/focusedCardFace\.artworkStatus/);
    assert.match(pane,/localArtworkDirectory: tarot\.localArtworkDirectory/);
    assert.match(pane,/maximumLength: 1024/);
    for(const src of [card,pane]){
        for(const forbidden of ["Process {","Timer {","FileView {",
              "XMLHttpRequest","Qt.openUrlExternally","WebEngineView",
              "new WebSocket","fetch(","writeFile","localStorage"]){
            assert.ok(!src.includes(forbidden),"unauthorized actor "+forbidden);
        }
    }
});
test("M6j enlarged-card CLOSE is solid red using canonical destructive button grammar",()=>{
    const inspector=pane.slice(pane.indexOf("id: tarotCardInspector"));
    assert.ok(inspector.length>2000);
    assert.match(inspector,/label: "CLOSE"\s*labelPixelSize: 9\s*destructive: true/);
    assert.match(inspector,/accentColor: Colors\.red/);
    assert.match(inspector,/idleFillColor: Colors\.red/);
    assert.match(inspector,/idleForegroundColor: Colors\.black/);
    assert.match(inspector,/hoverFillColor: Colors\.orange/);
    assert.match(inspector,/onClicked: tarot\.inspectedDrawIndex=-1/);
    assert.match(inspector,/label: "◀ CARD"/);
    assert.match(inspector,/label: "CARD ▶"/);
});
