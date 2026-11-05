"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=filename=>fs.readFileSync(path.join(root,filename),"utf8");
const code=read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const pane=read("widgets/weather/StationCosmosHeliocentricPane.qml");
const network=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const context=vm.createContext({});
vm.runInContext(code.replace(/^\.pragma library\s*/m,""),context);
const H=context;
const scene={
    ready:true,maxAu:40,
    points:[
        {body:"neptune_barycenter",x_au:0,y_au:30,z_au:0,distance_au:30,origin:false},
        {body:"pluto_barycenter",x_au:0,y_au:-39,z_au:0,distance_au:39,origin:false},
        {body:"earth",x_au:1,y_au:0,z_au:0,distance_au:1,origin:false}
    ]
};
function assertInside(marker,box){
    assert.ok(marker);
    assert.ok(marker.x>=box.left && marker.x<=box.right,
        "marker x must be inside diagram viewport");
    assert.ok(marker.y>=box.top && marker.y<=box.bottom,
        "marker y must be inside diagram viewport");
}
test("V4e keeps the compact plot and noncompact inspector geometries distinct",()=>{
    const compact=H.viewport(400,240,true);
    const normal=H.viewport(400,240,false);
    assert.equal(compact.right,388);
    assert.equal(normal.right,268);
    assert.equal(compact.left,12);
    assert.equal(compact.bottom,220);
    assert.equal(H.viewport(20,20,true),null);
    assert.equal(H.viewport(NaN,200,true),null);
    const inCompact=H.viewportMarker(scene,{
        body:"test",x_au:0,y_au:2,z_au:0
    },400,240,3,false,4,true);
    const inNormal=H.viewportMarker(scene,{
        body:"test",x_au:0,y_au:2,z_au:0
    },400,240,3,false,4,false);
    assert.equal(inCompact.offscreen,false);
    assert.equal(inNormal.offscreen,true);
    assertInside(inNormal,normal);
});

test("V4e Neptune and Pluto stay real, with directional offscreen markers in INNER 4 AU",()=>{
    const vp=H.viewport(400,240,true);
    const neptune=scene.points[0],pluto=scene.points[1];
    const rawNeptune=H.position(scene,neptune,400,240,1,false,4);
    const rawPluto=H.position(scene,pluto,400,240,1,false,4);
    assert.ok(rawNeptune.x>vp.right);
    assert.ok(rawPluto.x<vp.left);
    const markerNeptune=H.viewportMarker(scene,neptune,400,240,1,false,4,true);
    const markerPluto=H.viewportMarker(scene,pluto,400,240,1,false,4,true);
    assert.equal(markerNeptune.offscreen,true);
    assert.equal(markerPluto.offscreen,true);
    assert.ok(Math.cos(markerNeptune.angle)>0.99);
    assert.ok(Math.cos(markerPluto.angle)<-0.99);
    assertInside(markerNeptune,vp);
    assertInside(markerPluto,vp);
    assert.equal(markerNeptune.realX,rawNeptune.x);
    assert.equal(markerPluto.realX,rawPluto.x);
    assert.equal(scene.points[0].distance_au,30);
    assert.equal(scene.points[1].distance_au,39);
    assert.equal(H.visibleHit(scene,markerNeptune.x,markerNeptune.y,
        400,240,1,false,8,4,true),"neptune_barycenter");
    assert.equal(H.visibleHit(scene,markerPluto.x,markerPluto.y,
        400,240,1,false,8,4,true),"pluto_barycenter");
});

test("V4e high zoom never projects active points or click targets beyond the viewport",()=>{
    const vp=H.viewport(400,240,true);
    for(const tilt of [false,true]){
        for(const scale of [1,1.25,2.5,5]){
            for(const pt of scene.points){
                const visual=H.viewportMarker(scene,pt,400,240,
                    scale,tilt,scene.maxAu,true);
                assertInside(visual,vp);
                assert.equal(H.visibleHit(scene,visual.x,visual.y,
                    400,240,scale,tilt,8,scene.maxAu,true),pt.body);
                const label=H.labelPosition(visual,105,400,240,true,
                    H.layout(400,240,scale).cx);
                assert.ok(label!==null);
                const painted=Math.min(105,label.maxWidth);
                assert.ok(label.x-painted/2>=vp.left-1);
                assert.ok(label.x+painted/2<=vp.right+1);
            }
        }
    }
});

test("V4e keeps long system-barycenter labels inside the actual plot",()=>{
    const marker=H.viewportMarker(scene,scene.points[0],
        400,240,1,false,4,false);
    assert.ok(marker.offscreen);
    const vp=H.viewport(400,240,false);
    for(const width of [80,135,220,400]){
        const placement=H.labelPosition(marker,width,400,240,false,156);
        assert.ok(placement!==null);
        const painted=Math.min(width,placement.maxWidth);
        assert.ok(placement.x-painted/2>=vp.left);
        assert.ok(placement.x+painted/2<=vp.right);
        assert.ok(placement.y>=vp.top&&placement.y<=vp.bottom);
    }
    assert.equal(H.labelPosition(null,80,400,240,false,156),null);
});

test("V4e is a UI-only containment patch retaining original Sun/JPL and MAGICK controls",()=>{
    assert.match(network,/compactPlot: graph\.compactMode/);
    assert.match(pane,/property bool compactPlot: false/);
    assert.match(pane,/const plotBounds=Helio\.viewport\(w,h,spatial\.compactPlot\)/);
    assert.match(pane,/ctx\.rect\(plotBounds\.left,plotBounds\.top/);
    assert.match(pane,/ctx\.clip\(\)/);
    assert.match(pane,/Helio\.viewportMarker\(/);
    assert.match(pane,/Helio\.labelPosition\(/);
    assert.match(pane,/Helio\.visibleHit\(/);
    assert.match(pane,/p\.offscreen\?" \/ OUT":""/);
    assert.match(pane,/ctx\.measureText\(label\)\.width/);
    assert.match(pane,/onClicked: spatial\.tiltView=true/);
    assert.match(pane,/onClicked: spatial\.atlasRange="inner"/);
    assert.match(pane,/onWheel: function\(wheel\)/);
    assert.match(network,/StationCosmosHeliocentricPane\s*\{/);
    assert.match(network,/compactHelioToolbar/);
    assert.match(network,/Flickable\s*\{/);
    assert.match(code,/function position\(scene,point,width,height,scale,tilt,domainAu,panX,panY\)/);
    assert.match(code,/function hit\(scene,px,py,w,h,scale,tilt,tolerance,domainAu\)/);
    for(const s of [code,pane,network]){
        for(const forbidden of ["Process {","XMLHttpRequest","new WebSocket",
            "Quickshell.Io","curl ","fetch("])
            assert.ok(!s.includes(forbidden),forbidden);
    }
});
