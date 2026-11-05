"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=read("widgets/weather/StationCosmosHeliocentricPolicy.js");
const qml=read("widgets/weather/StationCosmosHeliocentricPane.qml");
const parent=read("widgets/weather/StationCosmosCelestialNetwork.qml");
const engine=read("scripts/weather/celestial_visual_data.py");
const context=vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*/m,""),context);
const H=context;
const data={
    ready:true,maxAu:40,
    points:[
        {body:"earth",x_au:1,y_au:0,z_au:0,distance_au:1,origin:false},
        {body:"neptune_barycenter",x_au:0,y_au:30,z_au:0,distance_au:30,origin:false},
        {body:"pluto_barycenter",x_au:-30,y_au:-15,z_au:2,distance_au:33.6,origin:false}
    ]
};
const close=(a,b,msg)=>assert.ok(Math.abs(a-b)<1e-7,msg+" "+a+" != "+b);

test("V4f uses a broad logarithmic camera scale without changing AU or original view",()=>{
    assert.equal(H.MIN_CAMERA_SCALE,0.02);
    assert.equal(H.MAX_CAMERA_SCALE,160);
    const original=H.layout(400,240,1);
    assert.equal(original.cx,156);
    assert.equal(original.cy,120);
    assert.equal(original.r,96);
    assert.equal(H.cameraOrigin(400,240,1,0,0).cx,156);
    for(const scale of [0.02,0.04,0.4,1,5,25,100,160]){
        const layout=H.layout(400,240,scale);
        assert.equal(layout.ready,true,"scale="+scale);
        assert.ok(layout.r>0,"scale radius="+scale);
        assert.ok(H.position(data,data.points[0],400,240,scale,false,40));
    }
    assert.equal(H.layout(400,240,0.019).ready,false);
    assert.equal(H.layout(400,240,161).ready,false);
    assert.equal(H.layout(0,240,1).ready,false);
    assert.equal(data.points[1].distance_au,30);
});

test("V4f wheel zoom locks source projection beneath cursor for TOP and TILT",()=>{
    for(const tilted of [false,true]){
        for(const start of [0.08,0.5,1,5,40]){
            for(const direction of [-1,1]){
                const panX=46.5,panY=-17.25,pt=data.points[2];
                const initial=H.position(data,pt,400,240,start,tilted,
                    40,panX,panY);
                const zoom=H.zoomAt(400,240,start,panX,panY,
                    initial.x,initial.y,direction);
                assert.ok(zoom);
                const next=H.position(data,pt,400,240,zoom.scale,
                    tilted,40,zoom.panX,zoom.panY);
                close(next.x,initial.x,"wheel must retain source X at pointer");
                close(next.y,initial.y,"wheel must retain source Y at pointer");
            }
        }
    }
    let zoom={scale:1,panX:0,panY:0};
    for(let k=0;k<70;k++)
        zoom=H.zoomAt(400,240,zoom.scale,zoom.panX,zoom.panY,200,110,1);
    assert.equal(zoom.scale,160);
    for(let k=0;k<90;k++)
        zoom=H.zoomAt(400,240,zoom.scale,zoom.panX,zoom.panY,200,110,-1);
    assert.equal(zoom.scale,0.02);
    assert.equal(H.zoomAt(400,240,1,0,0,200,120,0),null);
});

test("V4f panning shifts the whole diagram and its hit-testing in both axes",()=>{
    const pt=data.points[0],panX=125,panY=-70;
    const old=H.position(data,pt,400,240,2,false,4);
    const moved=H.position(data,pt,400,240,2,false,4,panX,panY);
    close(moved.x,old.x+panX,"panned X");
    close(moved.y,old.y+panY,"panned Y");
    const shown=H.viewportMarker(data,pt,400,240,2,false,4,true,panX,panY);
    assert.ok(shown);
    assert.equal(H.visibleHit(data,shown.x,shown.y,400,240,
        2,false,10,4,true,panX,panY),"earth");
    assert.equal(H.cameraOrigin(400,240,2,panX,panY).cx,281);
    assert.equal(H.cameraOrigin(400,240,2,panX,panY).cy,50);
});

test("V4f focus centers a source body at high zoom, even with large camera offsets",()=>{
    const scene={...data,points:[data.points[1]]};
    const body="neptune_barycenter";
    for(const compact of [true,false]){
        for(const zoom of [1,5,160]){
            const target=H.focusPan(scene,body,400,240,zoom,false,4,compact);
            assert.ok(target);
            const projected=H.position(scene,scene.points[0],400,240,
                zoom,false,4,target.panX,target.panY);
            const vp=H.viewport(400,240,compact);
            close(projected.x,(vp.left+vp.right)/2,"focus X");
            close(projected.y,(vp.top+vp.bottom)/2,"focus Y");
            const hit=H.visibleHit(scene,projected.x,projected.y,
                400,240,zoom,false,11,4,compact,target.panX,target.panY);
            assert.equal(hit,body);
        }
    }
    assert.equal(H.focusPan(scene,"missing",400,240,1,false,4,true),null);
});

test("V4f still shows clickable offscreen arrows if camera pans outside the plot",()=>{
    const scene={...data,points:[data.points[1]]};
    for(const offset of [
        {x:600,y:400},{x:-850,y:-500},{x:115000,y:0},{x:-115000,y:200}
    ]){
        const vp=H.viewport(400,240,true);
        const marker=H.viewportMarker(scene,scene.points[0],
            400,240,1,false,4,true,offset.x,offset.y);
        assert.ok(marker,"marker for displaced camera "+JSON.stringify(offset));
        assert.equal(marker.offscreen,true);
        assert.ok(marker.x>vp.left&&marker.x<vp.right);
        assert.ok(marker.y>vp.top&&marker.y<vp.bottom);
        assert.equal(H.visibleHit(scene,marker.x,marker.y,
            400,240,1,false,11,4,true,offset.x,offset.y),
            "neptune_barycenter");
    }
});

test("V4f preserves existing MAGICK interface while switching drag mode",()=>{
    assert.match(qml,/property real cameraPanX: 0/);
    assert.match(qml,/property real cameraPanY: 0/);
    assert.match(qml,/const g=Helio\.cameraOrigin\(/);
    assert.match(qml,/spatial\.cameraPanX=startPanX\+dx/);
    assert.match(qml,/spatial\.cameraPanY=startPanY\+dy/);
    assert.match(qml,/scrubTime=\(mouse\.modifiers & Qt\.ShiftModifier\)!==0/);
    assert.match(qml,/spatial\.sampleScrubbed\(originalIndex,dx\)/);
    assert.match(qml,/Helio\.zoomAt\(/);
    assert.match(qml,/wheel\.x,wheel\.y/);
    assert.match(qml,/onDoubleClicked: function\(mouse\)/);
    assert.match(qml,/Helio\.focusPan\(/);
    assert.match(qml,/else spatial\.resetCamera\(\)/);
    assert.match(qml,/Helio\.viewportMarker\(/);
    assert.match(qml,/Helio\.visibleHit\(/);
    assert.match(qml,/SHIFT\+DRAG TIME/);
    assert.match(parent,/compactPlot: graph\.compactMode/);
    assert.match(parent,/compactHelioToolbar/);
    assert.match(engine,/build_solar_overview\(/);
    for(const src of [qml,policy]){
        for(const banned of ["Process {","Timer {","XMLHttpRequest",
            "new WebSocket","Qt.callLater","curl ","fetch("])
            assert.ok(!src.includes(banned),"forbidden camera dependency "+banned);
    }
});
