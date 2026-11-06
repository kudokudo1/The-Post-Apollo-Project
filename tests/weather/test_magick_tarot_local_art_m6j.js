"use strict";
// M6j: local artwork selection is a read-only user-owned source, not a
// redistributed Wild Unknown image bundle or a new network provider.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const deck=read("widgets/weather/StationMagickTarotDeckPolicy.js");
const face=read("widgets/weather/StationMagickTarotCard.qml");
const pane=read("widgets/weather/StationMagickTarotPane.qml");
const action=read("components/ActionButton.qml");
const sandbox=vm.createContext({});
vm.runInContext(deck.replace(/^\.pragma library\s*/m,""),sandbox,{timeout:1000});
const P=sandbox,plain=x=>JSON.parse(JSON.stringify(x));

test("M6j supports private PNG/JPG/JPEG/WebP without remote lookups",()=>{
    assert.deepEqual(plain(P.localArtworkCandidates(
        "/var/home/tester/My Tarot","major-the-fool")),[
        "file:///var/home/tester/My%20Tarot/major-the-fool.png",
        "file:///var/home/tester/My%20Tarot/major-the-fool.jpg",
        "file:///var/home/tester/My%20Tarot/major-the-fool.jpeg",
        "file:///var/home/tester/My%20Tarot/major-the-fool.webp"
    ]);
    assert.equal(P.localArtworkCandidates("/home/user/cards","invalid").length,0);
    assert.equal(P.localArtworkCandidates("https://example.com","cups-ace").length,0);
    assert.equal(P.localArtworkCandidates("","cups-ace").length,0);
    assert.equal(P.DECK.artworkIncluded,false);
    assert.equal(P.DECK.cardIdentityOnly,true);
    assert.match(P.DECK.artPolicy,/USER-SUPPLIED LOCAL FILES ONLY/);
});
test("M6j folder dialog converts only safe file:/// URLs to local paths",()=>{
    assert.equal(P.localFolderPath("file:///var/home/tester/My%20Tarot"),
                 "/var/home/tester/My Tarot");
    assert.equal(P.localFolderPath("file:///home/me/Tarot%20%26%20Art"),
                 "/home/me/Tarot & Art");
    for(const bad of [
        "file://server/share","http://server/art","file:///home/me/../evil",
        "file:///home/me/%2E%2E/evil","file:///home/me/%2Fother",
        "file:///home/me/%5cother","file:///home/me/a//b",
        "file:///home/me/%ZZ","file:///","file:///home/me?a",
        "file:///home/me#fragment","file:///home/me:80", "",null
    ])assert.equal(P.localFolderPath(bad),"",String(bad));
    for(const id of ["major-the-fool","cups-mother","swords-10"]){
        const chosen=P.localFolderPath("file:///var/home/user/My%20Tarot");
        assert.match(P.localArtworkCandidates(chosen,id)[0],/^file:\/\/\//);
    }
});
test("M6j image URL variant is checked only after Image.Error, source fits card",()=>{
    assert.match(face,/readonly property var localSources:/);
    assert.match(face,/Deck\.localArtworkCandidates\(localArtworkDirectory,card\.id\)/);
    assert.match(face,/property int artworkAttempt: 0/);
    assert.match(face,/onLocalSourcesChanged: artworkAttempt=0/);
    assert.match(face,/status===Image\.Error/);
    assert.match(face,/artworkAttempt\+1<face\.localSources\.length/);
    assert.match(face,/onStatusChanged:/);
    assert.match(face,/visible: face\.hasLocalArt/);
    assert.match(face,/fillMode: Image\.PreserveAspectFit/);
    assert.match(face,/IMAGE MISSING \/\/ CHECK FOLDER/);
    assert.match(face,/NO LOCAL ART FOLDER/);
    assert.doesNotMatch(face,/http:\/\/|https:\/\/|XMLHttpRequest|Qt\.openUrlExternally/);
});
test("M6j private folder browse uses no upload, scan, or persistence",()=>{
    assert.match(pane,/import QtQuick\.Dialogs/);
    assert.match(pane,/FolderDialog\s*\{\s*id: tarotArtworkPicker/);
    assert.match(pane,/Deck\.localFolderPath\(selectedFolder\)/);
    assert.match(pane,/artworkFolderInput\.text=folder/);
    assert.match(pane,/label: "BROWSE"/);
    assert.match(pane,/onClicked: tarotArtworkPicker\.open\(\)/);
    assert.match(pane,/property string localArtworkDirectory: ""/);
    assert.match(pane,/onTextChanged: tarot\.localArtworkDirectory=text/);
    assert.match(pane,/NO CARD IMAGES \/\/ BROWSE YOUR PRIVATE ART FOLDER/);
    assert.match(pane,/NO WILD UNKNOWN ART INSTALLED/);
    for(const illegal of ["Process {","FileView {","XMLHttpRequest",
       "WebEngineView","Qt.openUrlExternally","Qt.openUrlExternally(",
       "new WebSocket","writeFile","localStorage","Settings {","FileDialog {"])
        assert.ok(!pane.includes(illegal),"unexpected actor: "+illegal);
});
test("M6j only the focus CLOSE button is filled red, with original action semantics",()=>{
    const focus=pane.slice(pane.indexOf('id: tarotCardInspector'));
    const match=focus.match(/ActionButton\s*\{\s*width: 70[\s\S]*?onClicked: tarot\.inspectedDrawIndex=-1/);
    assert.ok(match);
    const btn=match[0];
    assert.match(btn,/label: "CLOSE"/);
    assert.match(btn,/accentColor: Colors\.red/);
    assert.match(btn,/idleFillColor: Colors\.red/);
    assert.match(btn,/hoverFillColor: Colors\.red/);
    assert.match(btn,/pressedFillColor: Colors\.red/);
    assert.match(btn,/idleForegroundColor: Colors\.black/);
    assert.match(btn,/onClicked: tarot\.inspectedDrawIndex=-1/);
    assert.match(action,/property color idleFillColor:/);
    assert.match(action,/property color hoverFillColor:/);
    assert.match(action,/property color pressedFillColor:/);
    assert.match(action,/property color idleForegroundColor:/);
    assert.doesNotMatch(focus,/destructive:\s*true/);
});
