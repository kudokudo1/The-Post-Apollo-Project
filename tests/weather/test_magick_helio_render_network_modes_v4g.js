"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "../..");
const read = p => fs.readFileSync(path.join(root,p),"utf8");
const policy = read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const pane = read("widgets/weather/StationCosmosHeliocentricPane.qml");
const network = read("widgets/weather/StationCosmosCelestialNetwork.qml");
const instrument = read("widgets/weather/StationMagickCelestialInstrument.qml");
const c = vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*/m,""),c);
const P = c;

test("V4g HELIO cameraOrigin returns the ready flag consumed by Canvas.paint",()=>{
    // This exact omission caused the native blank chart. Previously the
    // helper returned {cx,cy,r} while QML immediately checked !g.ready.
    const orig=P.cameraOrigin(400,240,1,0,0);
    assert.ok(orig && orig.ready===true);
    assert.equal(orig.cx,156);
    assert.equal(orig.cy,120);
    assert.equal(orig.r,96);
    for(const scale of [0.02,0.4,1,5,160]){
        const shifted=P.cameraOrigin(400,240,scale,145,-65);
        assert.equal(shifted.ready,true,"scale="+scale);
        assert.equal(shifted.cx,301);
        assert.equal(shifted.cy,55);
        assert.ok(shifted.r>0);
    }
    assert.equal(P.cameraOrigin(0,240,1,0,0),null);
    assert.equal(P.cameraOrigin(400,240,0,0,0),null);
    assert.equal(P.cameraOrigin(400,240,1,Infinity,0),null);
    assert.equal(P.cameraOrigin(400,240,1,0,NaN),null);
    assert.match(pane,/const g=Helio\.cameraOrigin\(/);
    assert.match(pane,/if\(!g \|\| !g\.ready\)return;/);
    assert.match(policy,/return \{ready:true,cx:g\.cx\+x,cy:g\.cy\+y,r:g\.r\}/);
});

test("V4g HELIO still draws verified source points, keeps camera controls",()=>{
    assert.match(pane,/ctx\.arc\(g\.cx,g\.cy,5,0,Math\.PI\*2\)/);
    assert.match(pane,/NO VERIFIED SUN-CENTERED JPL XYZ/);
    assert.match(pane,/Helio\.viewportMarker\(/);
    assert.match(pane,/Helio\.visibleHit\(/);
    assert.match(pane,/onCameraPanXChanged: spatialCanvas\.requestPaint\(\)/);
    assert.match(pane,/onCameraPanYChanged: spatialCanvas\.requestPaint\(\)/);
    assert.match(pane,/Helio\.zoomAt\(/);
    assert.match(pane,/Helio\.focusPan\(/);
    assert.match(pane,/spatial\.sampleScrubbed\(originalIndex,dx\)/);
});

test("V4g compact NETWORK displays CHORDS and DEPTH controls, HELIO stays separate",()=>{
    assert.match(network,/id: compactNetworkToolbar/);
    assert.match(network,/visible: graph\.compactMode &&/);
    assert.match(network,/graph\.displayMode === "chords" \|\| graph\.displayMode === "depth"/);
    assert.match(network,/id: compactNetworkButtons/);
    assert.match(network,/\{id:"chords",label:"CHORDS"\}/);
    assert.match(network,/\{id:"depth",label:"DEPTH"\}/);
    assert.match(network,/onClicked: graph\.compactNetworkModeRequested\(modelData\.id\)/);
    assert.match(network,/signal compactNetworkModeRequested\(string mode\)/);
    assert.match(network,/anchors\.topMargin: compactNetworkToolbar\.visible \? 29 : 7/);
    assert.match(network,/id: depthPane/);
    assert.match(network,/visible: graph\.displayMode === "depth"/);
    // The dedicated HELIO controls and hidden full inspector are preserved.
    assert.match(network,/id: compactHelioToolbar/);
    assert.match(network,/graph\.displayMode === "heliocentric"/);
    assert.match(network,/id: inspectorFlick/);
    assert.match(network,/visible: !graph\.compactMode/);
});

test("V4g compact NETWORK selection survives HELIO tab without breaking parent binding",()=>{
    assert.match(instrument,/property string networkMode: "chords"/);
    assert.match(instrument,/displayMode: instrument\.compactMode && instrument\.mode === "helio"\s*\? "heliocentric" : instrument\.networkMode/);
    assert.match(instrument,/onCompactNetworkModeRequested: function\(mode\)/);
    assert.match(instrument,/instrument\.networkMode=mode/);
    // NETWORK has two submodes; HELIO still has its own primary tab.
    assert.match(instrument,/\{id:"network",label:"NETWORK"\}/);
    assert.match(instrument,/\{id:"helio",label:"HELIO"\}/);
    assert.match(instrument,/visible: instrument\.mode === "network"\s*\|\| \(instrument\.compactMode && instrument\.mode === "helio"\)/);
    // Never assign graph.displayMode inside compact buttons: that breaks
    // the binding to the top-level HELIO/NETWORK mode in QML.
    const toolbar=network.slice(network.indexOf("id: compactNetworkToolbar"),
        network.indexOf("// M30-G // The full inspector"));
    assert.ok(!toolbar.includes('graph.displayMode="depth"'));
    assert.ok(!toolbar.includes('graph.displayMode="chords"'));
});

test("V4g is QML presentation only, not another source provider",()=>{
    for(const file of [policy,pane,network,instrument]){
        assert.ok(!file.includes("XMLHttpRequest"));
        assert.ok(!file.includes("new WebSocket"));
    }
    for(const file of [pane,network]){
        assert.ok(!file.includes("Process {"));
        assert.ok(!file.includes("Timer {"));
    }
});
