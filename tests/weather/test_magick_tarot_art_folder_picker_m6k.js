"use strict";
// M6k local folder chooser: read-only path conversion, not image import.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ROOT=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
const deck=read("widgets/weather/StationMagickTarotDeckPolicy.js");
const pane=read("widgets/weather/StationMagickTarotPane.qml");
const card=read("widgets/weather/StationMagickTarotCard.qml");
const ctx=vm.createContext({});
vm.runInContext(deck.replace(/^\.pragma library\s*/,""),ctx,{timeout:1000});
const plain=x=>JSON.parse(JSON.stringify(x));
test("M6k accepts only safe local Qt FolderDialog file URLs",()=>{
    assert.equal(ctx.localFolderPath("file:///var/home/me/My%20Tarot"),
                 "/var/home/me/My Tarot");
    assert.equal(ctx.localFolderPath("file:///var/home/me/My%20Tarot/"),
                 "/var/home/me/My Tarot");
    assert.equal(ctx.localFolderPath("file:///home/me/Tarot%20%26%20Art"),
                 "/home/me/Tarot & Art");
    assert.equal(ctx.localFolderPath("file:///home/me/cards%20%F0%9F%92%9C"),
                 "/home/me/cards 💜");
    for(const unsafe of [
        null,undefined,"","file:///","file://server/share",
        "http://example.com/tarot","file:///home/me/../secret",
        "file:///home/me/%2E%2E/secret","file:///home/me/%2fetc",
        "file:///home/me/%5Cetc","file:///home/me/a//b",
        "file:///home/me/%ZZ","file:///home/me?token=secret",
        "file:///home/me#other","file:///home/me:80","file:///home/me\\evil"
    ])assert.equal(ctx.localFolderPath(unsafe),"",String(unsafe));
});
test("M6k returned folder is usable by existing local artwork candidates",()=>{
    const folder=ctx.localFolderPath("file:///var/home/me/Personal%20Tarot");
    const files=plain(ctx.localArtworkCandidates(folder,"major-the-fool"));
    assert.deepEqual(files,[
        "file:///var/home/me/Personal%20Tarot/major-the-fool.png",
        "file:///var/home/me/Personal%20Tarot/major-the-fool.jpg",
        "file:///var/home/me/Personal%20Tarot/major-the-fool.jpeg",
        "file:///var/home/me/Personal%20Tarot/major-the-fool.webp"
    ]);
    assert.equal(ctx.localArtworkCandidates(folder,"../etc").length,0);
    assert.equal(ctx.DECK.artworkIncluded,false);
});
test("M6k picker populates the original session-only artwork field",()=>{
    assert.match(pane,/import QtQuick\.Dialogs/);
    assert.match(pane,/FolderDialog\s*\{\s*id: tarotArtworkFolderPicker/);
    assert.match(pane,/Deck\.localFolderPath\(selectedFolder\)/);
    assert.match(pane,/if\(path!==""\)artworkFolderInput\.text=path/);
    assert.match(pane,/label: "BROWSE"/);
    assert.match(pane,/onClicked: tarotArtworkFolderPicker\.open\(\)/);
    assert.match(pane,/onTextChanged: tarot\.localArtworkDirectory=text/);
    assert.match(pane,/property string localArtworkDirectory: ""/);
    assert.match(pane,/width: Math\.max\(60,parent\.width-166\)/);
    assert.match(pane,/localArtworkDirectory: tarot\.localArtworkDirectory/);
    assert.match(card,/Deck\.localArtworkCandidates\(localArtworkDirectory,card\.id\)/);
    assert.match(pane,/label: "CLOSE"[\s\S]*?idleFillColor: Colors\.red/);
});
test("M6k cannot accidentally download, scan or save private images",()=>{
    for(const code of [pane,deck,card]) {
        for(const forbidden of [
            "Process {","FileView {","WebEngineView","XMLHttpRequest",
            "Qt.openUrlExternally","new WebSocket","fetch(","writeFile",
            "localStorage","Settings {","FileDialog {"
        ])assert.ok(!code.includes(forbidden),"unexpected actor "+forbidden);
    }
});
