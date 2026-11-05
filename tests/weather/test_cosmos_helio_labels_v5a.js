"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationCosmosHelioLabelPolicy.js");
const qml=read("widgets/weather/StationCosmosHeliocentricPane.qml");
const helioSource=read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const network=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const backend=read("scripts/weather/celestial_visual_data.py");
const context=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),context);
const Labels=context;
const bounds={left:12,top:10,right:388,bottom:220};
const box=(a,b)=>a.left<b.right && a.right>b.left &&
                  a.top<b.bottom && a.bottom>b.top;
const shown=labels=>labels.map(x=>x.body);

function marker(body,x,y,opts={}){
    const label=opts.label||body.toUpperCase();
    return {body,label,x,y,offscreen:!!opts.offscreen,
            width:Math.max(6,label.length*5.7)};
}

test("V5a spreads ordinary planetary labels and keeps boxes inside plot",()=>{
    const planets=[
        marker("venus",55,100),
        marker("earth",190,90),
        marker("jupiter_barycenter",314,159,{label:"JUPITER SYS"})
    ];
    const before=JSON.stringify(planets);
    const labels=Labels.layout(planets,bounds,"","",false);
    assert.equal(labels.length,3);
    for(const label of labels) {
        assert.equal(label.visible,true);
        assert.ok(label.rect.left>=bounds.left);
        assert.ok(label.rect.top>=bounds.top);
        assert.ok(label.rect.right<=bounds.right);
        assert.ok(label.rect.bottom<=bounds.bottom);
    }
    for(let i=0;i<labels.length;i++)
        for(let j=i+1;j<labels.length;j++)
            assert.equal(box(labels[i].rect,labels[j].rect),false);
    assert.equal(JSON.stringify(planets),before,"input marker positions are immutable");
});

test("V5a prioritizes selected and hovered body as positions converge",()=>{
    const crowded=Array.from({length:10},(_,i)=>
        marker("body"+i,190+i%2*2,115+i%3*2,
            {label:"SYSTEM "+i}));
    const labels=Labels.layout(crowded,bounds,"body9","body8",false);
    assert.ok(labels.length<10,"not every overlapping label should appear");
    assert.ok(shown(labels).includes("body9"),"selected always labelled");
    assert.ok(shown(labels).includes("body8"),"hovered always labelled");
    const selected=labels.find(x=>x.body==="body9");
    assert.equal(selected.focused,true);
    assert.equal(selected.priority,100);
    assert.equal(labels.at(-1).body,"body9","selection paints above ordinary labels");
});

test("V5a HUD respects reserved compact plot space",()=>{
    const hud=Labels.plaque(bounds,true);
    assert.ok(hud);
    assert.equal(hud.left,18);
    assert.equal(hud.top,35);
    assert.equal(hud.bottom,68);
    assert.equal(Labels.plaque(bounds,false),null);
    const planets=[
        marker("mercury",65,49),
        marker("earth",235,115)
    ];
    const labels=Labels.layout(planets,bounds,"earth","",true);
    assert.ok(shown(labels).includes("earth"));
    for(const label of labels)
        assert.equal(box(label.rect,hud),false,
            "no drawn label should cover the selected JPL callout");
});

test("V5a long barycenter names and offscreen arrows stay contained",()=>{
    const longLabel="NEPTUNE SYSTEM BARYCENTER / OUT";
    const marks=[
        marker("neptune_barycenter",372,190,
            {label:longLabel,offscreen:true}),
        marker("earth",30,95)
    ];
    const output=Labels.layout(marks,bounds,"neptune_barycenter","",true);
    const label=output.find(x=>x.body==="neptune_barycenter");
    assert.ok(label);
    assert.ok(label.width<=Labels.MAX_LABEL_WIDTH);
    assert.ok(label.rect.left>=bounds.left);
    assert.ok(label.rect.right<=bounds.right);
    assert.ok(label.rect.bottom<=bounds.bottom);
    assert.equal(label.offscreen,true);
    assert.equal(label.text,longLabel);
});

test("V5a fails closed on malformed geometries rather than painting bad labels",()=>{
    assert.equal(Labels.layout(null,bounds,"","",false).length,0);
    assert.equal(Labels.layout([],bounds,"","",false).length,0);
    assert.equal(Labels.layout([marker("earth",190,110)],null,"","",false).length,0);
    assert.equal(Labels.layout([marker("earth",190,110)],
        {left:0,top:0,right:1,bottom:1},"","",false).length,0);
    assert.equal(Labels.layout([marker("earth",Infinity,110)],
        bounds,"","",false).length,0);
    assert.equal(Labels.layout(Array.from({length:13},(_,i)=>
        marker("body"+i,90+i,90)),bounds,"","",false).length,0);
});

test("V5a drawing is presentation-only; existing JPL, camera and modes remain",()=>{
    assert.match(qml,/import "StationCosmosHelioLabelPolicy\.js" as Labels/);
    assert.match(qml,/const labelItems=\[\]/);
    assert.match(qml,/Labels\.layout\(labelItems,plotBounds,/);
    assert.match(qml,/Labels\.plaque\(plotBounds,focusedPoint!==null\)/);
    assert.match(qml,/ctx\.measureText\(label\)\.width/);
    assert.match(qml,/ctx\.fillText\(item\.text,item\.x,item\.y,item\.width\)/);
    assert.match(qml,/JPL \/\/ "\+focusedPoint\.distance_au\.toFixed\(3\)/);
    assert.match(qml,/Helio\.viewportMarker\(/);
    assert.match(qml,/Helio\.visibleHit\(/);
    assert.match(qml,/Helio\.zoomAt\(/);
    assert.match(qml,/Helio\.focusPan\(/);
    assert.match(qml,/spatial\.sampleScrubbed\(originalIndex,dx\)/);
    assert.match(qml,/onDoubleClicked: function\(mouse\)/);
    assert.match(network,/compactPlot: graph\.compactMode/);
    assert.match(network,/id: compactNetworkToolbar/);
    assert.match(helioSource,/function position\(/);
    assert.match(helioSource,/function viewportMarker\(/);
    assert.match(backend,/build_solar_overview\(/);
    for(const src of [source,qml]) {
        for(const banned of ["Process {","Timer {","XMLHttpRequest",
            "Qt.callLater","new WebSocket","curl ","fetch("])
            assert.ok(!src.includes(banned),"unexpected new provider "+banned);
    }
});
