"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const source=read("widgets/weather/StationMagickAspectMatrixPolicy.js");
const qml=read("widgets/weather/StationMagickCelestialInstrument.qml");
const modelSource=read("widgets/weather/StationMagickCelestialVisualPolicy.js");
const subject=read("widgets/weather/StationMagickAstrologyPane.qml");
const ctx=vm.createContext({});
vm.runInContext(source.replace(/^\.pragma library\s*/m,""),ctx);
const M=ctx;
const start=Date.UTC(2026,10,6,0,0);
const time=Array.from({length:12},(_,i)=>start+i*12*3600000);
const separation=[0,58,91,122,179,30,121,90,60,0,180,8];
const fake=()=>({
    model:{
        ready:true,frame:M.FRAME,source:"de440s.bsp",
        sampleCount:time.length,times:time.slice(),
        relationships:[{bodies:["mercury","sun"],
            samples:time.map((t,i)=>({
                unix_ms:t,longitude_separation_deg:separation[i],
                aspects:[]}))
        }]
    },
    payload:{
        format:M.FORMAT,
        query:{origin:"geocentric",position_model:"apparent",
            frame:M.FRAME,bodies:["mercury","sun"],orb_degrees:6}
    },
    view:{from:0,to:11,count:12}
});
const plain=v=>JSON.parse(JSON.stringify(v));

test("M6b matrix uses the actual five M2 reference angles and original M4 pair",()=>{
    const {model,payload,view}=fake(),copy=JSON.stringify(model);
    const data=M.build(model,payload,view,3,6);
    assert.equal(data.ready,true,data.reason);
    assert.deepEqual(plain(data.pair),["mercury","sun"]);
    assert.deepEqual(plain(data.rows.map(r=>r.angle_deg)),[0,60,90,120,180]);
    assert.equal(data.rows.length,5);
    assert.equal(data.columns.length,6);
    assert.equal(data.rows[0].cells[0].sampleIndex,0);
    assert.equal(data.rows[1].cells[0].sampleIndex,1);
    assert.equal(data.rows[1].cells[0].error_deg,2);
    assert.equal(data.rows[1].cells[0].separation_deg,58);
    assert.equal(data.rows[1].cells[0].inOrb,true);
    assert.equal(data.rows[1].cells[0].unix_ms,time[1]);
    assert.equal(data.rows[1].cells[0].strength,1-2/6);
    assert.equal(JSON.stringify(model),copy,"source untouched by display model");
});

test("M6b 24-column compact heatmap stays bounded and picks real bucket sample",()=>{
    const {model,payload,view}=fake();
    const data=M.build(model,payload,view,5,3);
    assert.equal(data.ready,true,data.reason);
    assert.deepEqual(plain(data.columns.map(c=>[c.fromIndex,c.toIndex])),
        [[0,3],[4,7],[8,11]]);
    assert.equal(data.rows[4].cells[1].sampleIndex,4);
    assert.equal(data.rows[4].cells[1].separation_deg,179);
    assert.equal(data.rows[4].cells[1].sampleCount,4);
    const g=M.geometry(400,190);
    assert.ok(g);
    const cellRect=M.cellRect(g,1,4,3);
    assert.ok(cellRect);
    const cell=M.pick(data,g,cellRect.x+cellRect.width/2,
                      cellRect.y+cellRect.height/2);
    assert.ok(cell);
    assert.equal(cell.sampleIndex,4,"click selects actual sample index");
    assert.equal(cell.unix_ms,time[4]);
    assert.equal(M.pick(data,g,g.left-1,g.top),null);
    assert.equal(M.pick(data,g,g.right,g.top),null);
    assert.equal(M.pick(data,g,g.left,g.bottom),null);
    assert.equal(M.geometry(100,90),null);
    assert.equal(M.cellRect(g,-1,0,3),null);
    assert.equal(M.cellRect(g,1,99,3),null);
});

test("M6b zero orb and far-from-angle cells never invent aspect matches",()=>{
    const {model,payload,view}=fake();
    payload.query.orb_degrees=0;
    const data=M.build(model,payload,view,3,6);
    assert.equal(data.ready,true);
    const exact=data.rows[0].cells[0];
    assert.equal(exact.error_deg,0);
    assert.equal(exact.inOrb,true);
    assert.equal(exact.strength,1);
    const miss=data.rows[1].cells[0];
    assert.equal(miss.inOrb,false);
    assert.equal(miss.strength,0);
    assert.ok(!("predictedEventTime" in miss));
    assert.ok(!("station" in miss));
    assert.ok(!("house" in data));
});

test("M6b refuses stale, malformed, and nonuniform source UTC or orb",()=>{
    function reject(change){
        const {model,payload,view}=fake();
        change(model,payload,view);
        return M.build(model,payload,view,3,6).ready;
    }
    assert.equal(reject(m=>{m.ready=false}),false);
    assert.equal(reject(m=>{m.frame="sidereal"}),false);
    assert.equal(reject((m,p)=>{p.query.frame="j2000"}),false);
    assert.equal(reject((m,p)=>{p.query.origin="heliocentric"}),false);
    assert.equal(reject((m,p)=>{p.query.position_model="geometric"}),false);
    assert.equal(reject((m,p)=>{p.query.orb_degrees=NaN}),false);
    assert.equal(reject((m,p)=>{p.query.orb_degrees=45}),false);
    assert.equal(reject((m,p)=>{p.query.bodies=["venus","sun"]}),false);
    assert.equal(reject(m=>{m.times[5]=m.times[4]}),false);
    assert.equal(reject(m=>{m.times[5]+=3600000}),false);
    assert.equal(reject(m=>{m.relationships[0].samples[4].unix_ms++}),false);
    assert.equal(reject(m=>{m.relationships[0].samples[4].longitude_separation_deg=181}),false);
    assert.equal(reject(m=>{m.relationships[0].samples[4].longitude_separation_deg=NaN}),false);
    assert.equal(reject(m=>{m.relationships=[]}),false);
    assert.equal(reject((m,p,v)=>{v.from=7;v.to=2}),false);
    assert.equal(reject((m,p,v)=>{v.to=50}),false);
    assert.equal(reject(m=>{m.sampleCount=900}),false);
    assert.equal(M.build(null,null,null,-1,6).ready,false);
});

test("M6b GUI adds secondary CURVE/MATRIX without eighth main mode or provider",()=>{
    assert.match(qml,/import "StationMagickAspectMatrixPolicy\.js" as Matrix/);
    assert.match(qml,/property string aspectPresentation: "curve"/);
    assert.match(qml,/Matrix\.build\(graphModel,visualData,/);
    assert.match(qml,/compactMode \? 24 : 40/);
    assert.match(qml,/function paintAspectMatrix\(ctx\)/);
    assert.match(qml,/instrument\.paintAspectMatrix\(ctx\)/);
    assert.match(qml,/id: aspectViewControls/);
    assert.match(qml,/id:"curve",label:"CURVE"/);
    assert.match(qml,/id:"matrix",label:"MATRIX"/);
    assert.match(qml,/onClicked: instrument\.aspectPresentation=modelData\.id/);
    assert.match(qml,/Matrix\.pick\(instrument\.aspectMatrix,/);
    assert.match(qml,/instrument\.lockedIndex=cell\.sampleIndex/);
    assert.match(qml,/BUCKET CLOSEST MEASURED SAMPLE \/\/ NO INTERPOLATION/);
    assert.match(qml,/function paintRetrograde\(ctx\)/);
    assert.match(qml,/id:"retro",label:"RETRO"/);
    assert.match(qml,/StationCosmosCelestialNetwork\s*\{/);
    assert.match(qml,/instrument\.mode === "network"/);
    assert.match(subject,/StationMagickCelestialInstrument\s*\{/);
    assert.match(modelSource,/longitude_separation_deg/);
    const mainModeArea=qml.slice(qml.indexOf('id: modeRow'),
        qml.indexOf('id: chartFrame'));
    assert.ok(!mainModeArea.includes('id:"matrix"'),"not an eighth tiny main tab");
    for(const s of [source,qml]){
        for(const forbidden of ["Process {","Timer {","XMLHttpRequest",
                                "new WebSocket","curl ","fetch("])
            assert.ok(!s.includes(forbidden),forbidden);
    }
});
